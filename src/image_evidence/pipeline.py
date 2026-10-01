"""Ingestion orchestration: discover -> acquire -> extract -> classify -> infer -> index."""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
from PIL import Image

from . import __version__, acquisition, frames, geo_text, ocr, translate, visual
from .classify import Classifier, choose, make_classifier, text_categories
from .config import Config
from .derivatives import original_format, write_derivative, write_original
from .discovery import Candidate, DiscoveryError, YouTubeClient, discover, estimate_quota, source_from_api
from .inference import infer
from .layout import Library, VideoDirs, write_json
from .schema import (
    Acquisition,
    DerivedVisual,
    DiscoveryContext,
    FrameCore,
    FrameFiles,
    FrameRecord,
    FrameSourceLink,
    PipelineInfo,
    SourceVideo,
    VideoDerived,
    VideoRecord,
    frame_id_for,
    timestamped_url,
    utcnow,
    video_id_for,
)
from .scope import Verdict, check_scope, in_date_range
from .store import Repository, SQLiteRepository

log = logging.getLogger(__name__)


@dataclass
class VideoResult:
    youtube_id: str
    status: str
    acquisition: str | None = None
    reason: str | None = None
    frames: int = 0
    title: str | None = None


@dataclass
class RunReport:
    run_id: str
    started_at: datetime
    candidates: list[dict[str, Any]] = field(default_factory=list)
    results: list[VideoResult] = field(default_factory=list)


class Pipeline:
    def __init__(self, cfg: Config, repo: Repository | None = None):
        self.cfg = cfg
        self.lib = Library(cfg.library_dir).create()
        self.repo = repo or SQLiteRepository(self.lib.db_path)
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self._classifier: Classifier | None = None
        self._client: YouTubeClient | None | bool = None

    @property
    def classifier(self) -> Classifier:
        if self._classifier is None:
            self._classifier = make_classifier(self.cfg.classification)
        return self._classifier

    @property
    def client(self) -> YouTubeClient | None:
        if self._client is None:
            key = os.environ.get(self.cfg.discovery.api_key_env)
            self._client = YouTubeClient(key) if key else False
        return self._client or None

    # ------------------------------------------------------------ discovery

    def discover(self) -> list[Candidate]:
        if not self.client:
            raise DiscoveryError(f"discovery requires ${self.cfg.discovery.api_key_env} (YouTube Data API v3 key)")
        return discover(self.cfg.discovery, self.client, self.run_id)

    def run(self, *, discover_only: bool = False, force: bool = False) -> RunReport:
        report = RunReport(self.run_id, utcnow())
        log.info("run %s: estimated quota %d units", self.run_id, estimate_quota(self.cfg.discovery))
        candidates = self.discover()
        picked = self._pick(candidates, force)
        for c in candidates:
            s = source_from_api(c.api_item)
            row = {
                "youtube_id": c.youtube_id, "title": s.title, "published_at": s.published_at.isoformat(),
                "license": s.license, "duration_s": s.duration_s, "queries": sorted({ctx.query for ctx in c.contexts}),
                "picked": c.youtube_id in picked,
            }
            if c.rank:
                row |= {"score": c.rank.score, "in_area": c.rank.in_area, "places": c.rank.places, "reasons": c.rank.reasons}
            report.candidates.append(row)
        log.info("discovered %d videos, %d to ingest", len(candidates), len(picked))
        if not discover_only:
            for c in candidates:
                if c.youtube_id in picked:
                    report.results.append(self.ingest(c.youtube_id, api_item=c.api_item, contexts=c.contexts, force=force))
        self._write_report(report, discover_only)
        return report

    def _pick(self, candidates: list[Candidate], force: bool) -> set[str]:
        """The candidates to ingest, in ranked order: with a study area, only those placed in it (score >=
        focus.min_score, see focus.py) that pass the scope gate and the duration limit, the best max_ingest new ones."""
        d = self.cfg.discovery
        if not d.focus and not d.max_ingest:
            return {c.youtube_id for c in candidates}
        picked: set[str] = set()
        for c in candidates:
            if d.max_ingest and len(picked) >= d.max_ingest:
                break
            if c.rank and (not c.rank.in_area or not c.rank.on_topic or c.rank.score < d.focus.min_score):
                continue
            s = source_from_api(c.api_item)
            if not check_scope(s, self.cfg.scope.min_confidence).accepted:  # in memory; ingest checks again
                continue
            if s.duration_s and s.duration_s > self.cfg.acquisition.max_duration_s:
                continue
            done = self.lib.video(c.youtube_id).video_json
            if not force and done.exists() and VideoRecord.model_validate_json(done.read_text()).status == "processed":
                continue  # already in the library: don't spend a slot on it
            picked.add(c.youtube_id)
        return picked

    def ingest_ids(self, youtube_ids: list[str], force: bool = False) -> RunReport:
        report = RunReport(self.run_id, utcnow())
        api_items: dict[str, dict] = {}
        if self.client:
            try:
                api_items = self.client.videos(youtube_ids)
            except DiscoveryError as e:
                log.warning("YouTube API lookup failed, falling back to yt-dlp metadata: %s", e)
        for yid in youtube_ids:
            ctx = DiscoveryContext(run_id=self.run_id, query=f"manual:{yid}", rank=0)
            report.results.append(self.ingest(yid, api_item=api_items.get(yid), contexts=[ctx], force=force))
        self._write_report(report, False)
        return report

    def _write_report(self, report: RunReport, discover_only: bool) -> None:
        write_json(self.lib.runs / f"{report.run_id}.json", {
            "run_id": report.run_id,
            "started_at": report.started_at,
            "finished_at": utcnow(),
            "mode": "discover" if discover_only else "ingest",
            "pipeline_version": __version__,
            "config": self.cfg.model_dump(mode="json"),
            "candidates": report.candidates,
            "results": [r.__dict__ for r in report.results],
        })

    # ------------------------------------------------------------ per video

    def ingest(self, youtube_id: str, *, api_item: dict | None, contexts: list[DiscoveryContext], force: bool = False) -> VideoResult:
        dirs = self.lib.video(youtube_id)  # created only once the video passes the scope gate
        prior = VideoRecord.model_validate_json(dirs.video_json.read_text()) if dirs.video_json.exists() else None
        discovery = _merge_contexts(prior.discovery if prior else [], contexts)
        if prior and prior.status == "processed" and not force:
            if discovery != prior.discovery:
                prior.discovery = discovery
                self._save_video(dirs, prior)
            log.info("[%s] already processed (use --force to re-extract)", youtube_id)
            return VideoResult(youtube_id, "skipped_existing", prior.acquisition.status if prior.acquisition else None, frames=len(prior.frame_ids), title=prior.source.title)
        try:
            return self._ingest(youtube_id, dirs, api_item, discovery, force)
        except Exception as e:  # keep going with the next video; record the failure
            log.exception("[%s] failed", youtube_id)
            return VideoResult(youtube_id, "failed", reason=f"{type(e).__name__}: {e}")

    def _ingest(self, yid: str, dirs: VideoDirs, api_item: dict | None, discovery: list[DiscoveryContext], force: bool) -> VideoResult:
        log.info("[%s] metadata", yid)
        # Scope gate (Ukraine-only, published 2022..2026) runs on in-memory metadata,
        # before anything is written to disk. Checked on API metadata first to avoid a yt-dlp call.
        source: SourceVideo | None = source_from_api(api_item) if api_item else None
        verdict = check_scope(source, self.cfg.scope.min_confidence) if source else None
        if verdict and not verdict.accepted:
            return self._reject(yid, source, verdict)

        info: dict[str, Any] | None = None
        info_error: str | None = None
        try:
            info = acquisition.fetch_info(yid)
        except Exception as e:
            info_error = str(e).splitlines()[0][:300]
            log.warning("[%s] yt-dlp metadata unavailable: %s", yid, info_error)

        if source is None:
            if info is None:
                raise RuntimeError(f"no metadata from YouTube API or yt-dlp: {info_error}")
            source = acquisition.source_from_info(info)
            verdict = check_scope(source, self.cfg.scope.min_confidence)
            if not verdict.accepted:
                return self._reject(yid, source, verdict)
        elif info is not None:
            source = source.model_copy(update={"retrieved_via": (*source.retrieved_via, "yt-dlp")})
        log.info("[%s] in scope: %s", yid, verdict.reason)

        dirs.create()
        if api_item:
            write_json(dirs.raw / "youtube_api.json", api_item)
        if info is not None:
            write_json(dirs.raw / "ytdlp_info.json", info)

        video = VideoRecord(
            video_id=video_id_for(yid),
            source=source,
            discovery=discovery,
            derived=VideoDerived(text_categories=text_categories(source.title, source.tags, source.description)),
            scope=verdict.check,
        )
        video.youtube_thumbnails = acquisition.save_youtube_thumbnails(source, dirs, self.lib)

        media_path = None
        if info is None:
            video.acquisition = Acquisition(status="unavailable", policy=self.cfg.acquisition.policy, reason=info_error, tool=acquisition.TOOL)
        else:
            decision = acquisition.decide(self.cfg.acquisition, source, info)
            if decision.allowed:
                log.info("[%s] downloading (%s)", yid, decision.reason)
                video.acquisition, media_path = acquisition.download(self.cfg.acquisition, dirs, self.lib, yid)
            else:
                log.info("[%s] not downloading: %s", yid, decision.reason)
                video.acquisition, media_path = Acquisition(status=decision.status, policy=self.cfg.acquisition.policy, reason=decision.reason, tool=acquisition.TOOL), None

        self.repo.upsert_video(video)  # frames reference the video row
        if media_path:
            if force:
                self._clear_frames(dirs, video.video_id)
            video.frame_ids = self._extract(video, dirs, media_path)
            relocate_video(self.lib, self.repo, dirs.root, video=video, fetch_captions=True, translate_en=True, run_ocr=True)
            if not self.cfg.acquisition.keep_media:
                media_path.unlink()
                video.acquisition = video.acquisition.model_copy(update={"reason": "media deleted after extraction (keep_media=false); sha256 retained"})
        video.status = "processed"
        self._save_video(dirs, video)
        log.info("[%s] done: %s, %d frames", yid, video.acquisition.status, len(video.frame_ids))
        return VideoResult(yid, "processed", video.acquisition.status, video.acquisition.reason, len(video.frame_ids), source.title)

    def _reject(self, yid: str, source: SourceVideo, verdict: Verdict) -> VideoResult:
        log.info("[%s] REJECTED (out of scope): %s", yid, verdict.reason)
        return VideoResult(yid, "rejected", reason=verdict.reason, title=source.title)

    def _save_video(self, dirs: VideoDirs, video: VideoRecord) -> None:
        video.updated_at = utcnow()
        write_json(dirs.video_json, video.model_dump(mode="json"))
        self.repo.upsert_video(video)

    def _clear_frames(self, dirs: VideoDirs, video_id: str) -> None:
        for d in (dirs.originals, dirs.web, dirs.thumbs, dirs.meta):
            shutil.rmtree(d, ignore_errors=True)
            d.mkdir(parents=True)
        self.repo.delete_frames_for_video(video_id)

    def _extract(self, video: VideoRecord, dirs: VideoDirs, media_path) -> list[str]:
        ecfg, ccfg = self.cfg.extraction, self.cfg.classification
        yid = video.source.youtube_id
        probe = frames.probe(media_path)
        scanned = frames.select_candidates(media_path, ecfg, probe)
        cands = frames.prefilter(frames.thin_candidates(scanned, ecfg, limit=10**9), ecfg)
        log.info("[%s] %d candidate frames, %d after dedup (%s %dx%d @ %.3f fps, %.0fs)", yid, len(scanned), len(cands),
                 probe.codec, probe.width, probe.height, probe.fps, probe.duration)
        emb = None
        if self.classifier.provenance is None:  # no visual classifier: keep an even spread in time
            cands = frames.cap(cands, ecfg.max_frames_per_video)
            results = [([], {}) for _ in cands]
        else:  # classify previews, keep the frames that show places rather than people or interiors
            cands = frames.cap(cands, ecfg.candidate_pool)
            emb = self.classifier.embed([Image.fromarray(c.preview) for c in cands])
            results = self.classifier.classify_embeddings(emb)
            keep = choose([c.pts_time for c in cands], [r[1] for r in results], ccfg, ecfg.max_frames_per_video)
            log.info("[%s] keeping %d of %d (subject score >= %.2f; prefer %s, avoid %s)", yid, len(keep), len(cands),
                     ccfg.min_subject, "/".join(ccfg.prefer), "/".join(ccfg.avoid))
            cands, results, emb = [cands[i] for i in keep], [results[i] for i in keep], emb[keep]

        fmt = original_format(ecfg, len(cands))
        inferred = infer(video.source, video.discovery, video.scope)
        pipeline_info = PipelineInfo(version=__version__, config_digest=self.cfg.digest())
        staged: list[tuple[FrameRecord, Image.Image, int]] = []
        for i, ef in frames.decode_frames(media_path, probe, cands):
            labels, scores = results[i]
            fid = frame_id_for(yid, ef.frame_number)
            orig, sha = write_original(ef.rgb, dirs.originals / fid, fmt, ecfg)
            web = dirs.web / f"{fid}.webp"
            thumb = dirs.thumbs / f"{fid}.webp"
            write_derivative(ef.rgb, web, ecfg.web_max_px, ecfg.web_quality)
            thumb_img = write_derivative(ef.rgb, thumb, ecfg.thumb_max_px, ecfg.thumb_quality)
            core = FrameCore(
                timestamp_s=ef.timestamp_s,
                frame_number=ef.frame_number,
                fps=round(probe.fps, 6),
                width=ef.rgb.shape[1],
                height=ef.rgb.shape[0],
                selection=ef.selection,
                scene_score=ef.scene_score,
                original_format=fmt,
                sha256=sha,
                files=FrameFiles(original=self.lib.rel(orig), web=self.lib.rel(web), thumb=self.lib.rel(thumb)),
            )
            record = FrameRecord(
                frame_id=fid,
                source=FrameSourceLink(
                    video_id=video.video_id,
                    youtube_id=yid,
                    source_url=video.source.source_url,
                    timestamped_url=timestamped_url(yid, core.timestamp_s),
                    published_at=video.source.published_at,
                ),
                frame=core,
                derived=DerivedVisual(categories=labels, category_scores=scores, classifier=self.classifier.provenance, quality=ef.quality),
                inferred=inferred,
                pipeline=pipeline_info,
            )
            staged.append((record, thumb_img, i))

        # Sorting features (colour, light, season cues, camera angle, damage) + embeddings for "similar view".
        kept_emb = emb[[i for _, _, i in staged]] if emb is not None and staged else None
        feats, _ = visual.features([t for _, t, _ in staged], self.classifier if kept_emb is not None else None, kept_emb)
        for (record, _, _), fx in zip(staged, feats):
            record.derived.features = fx
            write_json(dirs.meta / f"{record.frame_id}.json", record.model_dump(mode="json"))
            self.repo.upsert_frame(record)
        if kept_emb is not None:
            rows = {r.frame_id: v for (r, _, _), v in zip(staged, kept_emb)}
            visual.save_embeddings(dirs.meta.parent / "embeddings.npz", rows, self.cfg.classification.model)
            self.repo.upsert_embeddings(self.cfg.classification.model, rows)
        return [r.frame_id for r, _, _ in staged]


def reclassify(lib: Library, repo: Repository, classifier: Classifier, youtube_id: str | None = None) -> int:
    """Re-run classification on existing frames (from their thumbnails). Only derived categories change."""
    pattern = f"{youtube_id or '*'}/frames/meta/*.json"
    metas = sorted(lib.videos.glob(pattern))
    batch = 64
    for i in range(0, len(metas), batch):
        records = [FrameRecord.model_validate_json(p.read_text()) for p in metas[i : i + batch]]
        images = [Image.open(lib.abs(r.frame.files.thumb)) for r in records]
        for path, rec, (labels, scores) in zip(metas[i : i + batch], records, classifier.classify(images)):
            rec.derived.categories = labels
            rec.derived.category_scores = scores
            rec.derived.classifier = classifier.provenance
            write_json(path, rec.model_dump(mode="json"))
            repo.upsert_frame(rec)
    return len(metas)


def rescope(lib: Library, repo: Repository, min_confidence: float, purge: bool = False) -> list[tuple[str, bool, str]]:
    """Re-run the scope gate on stored videos; refresh scope + inferred metadata. With purge, delete rejects."""
    results = []
    for video_json in sorted(lib.videos.glob("*/video.json")):
        video = VideoRecord.model_validate_json(video_json.read_text())
        verdict = check_scope(video.source, min_confidence)
        yid = video.source.youtube_id
        if not verdict.accepted:
            if purge:
                shutil.rmtree(video_json.parent)
                repo.delete_video(video.video_id)
            results.append((yid, False, verdict.reason + (" -> deleted" if purge else " (run with --purge to delete)")))
            continue
        video.scope = verdict.check
        video.updated_at = utcnow()
        write_json(video_json, video.model_dump(mode="json"))
        repo.upsert_video(video)
        relocate_video(lib, repo, video_json.parent, video=video)  # video-level + stored frame-level clues
        results.append((yid, True, verdict.reason))
    return results


def refresh_titles(lib: Library, repo: Repository, client: YouTubeClient) -> list[tuple[str, dict[str, str]]]:
    """Fetch the uploader's title localizations for stored videos (1 quota unit per 50 videos)."""
    paths = {p.parent.name: p for p in sorted(lib.videos.glob("*/video.json"))}
    items = client.videos(list(paths))
    out = []
    for yid, path in paths.items():
        if yid not in items:
            continue
        data = json.loads(path.read_text())
        data.get("derived", {}).pop("title_translation", None)  # removed field (machine translations)
        video = VideoRecord.model_validate(data)
        locs = source_from_api(items[yid]).title_localizations
        video.source = video.source.model_copy(update={"title_localizations": locs})
        video.updated_at = utcnow()
        write_json(path, video.model_dump(mode="json"))
        repo.upsert_video(video)
        out.append((yid, locs))
    return out


def translate_captions(video_dir, captions: dict | None, force: bool = False) -> int:
    """Machine-translate the captions' paragraphs into English (translate.py). Returns paragraphs written."""
    path = geo_text.english_captions_path(video_dir)
    lang = (captions or {}).get("lang") or ""
    if not captions or not captions.get("cues") or captions.get("english") or lang.startswith("en"):
        return 0
    if path.exists() and not force:
        return 0
    if not translate.available(lang):
        log.info("[%s] no local translation model for %r captions", video_dir.name, lang)
        return 0
    paras = geo_text.paragraphs(captions["cues"])
    texts = translate.to_english([t for _, _, t in paras], lang)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, {
        "lang": "en", "kind": "machine", "from": lang, "model": translate.model_name(lang), "created_at": utcnow(),
        "note": "local machine translation of raw/captions.json, one cue per paragraph; a reading aid, never matched for places",
        "cues": [[a, b, t] for (a, b, _), t in zip(paras, texts)],
    })
    return len(paras)


def relocate_video(lib: Library, repo: Repository, video_dir, *, video: VideoRecord | None = None,
                   fetch_captions: bool = False, refetch_captions: bool = False, translate_en: bool = False, retranslate: bool = False,
                   run_ocr: bool = False, force_ocr: bool = False) -> dict[str, int]:
    """Recompute every frame's inferred locations/dates: video-level candidates plus frame-level clues
    (on-screen text, description chapter, nearby speech). Optionally fetches captions (and translates
    them into English for reading) and runs OCR first."""
    video = video or VideoRecord.model_validate_json((video_dir / "video.json").read_text())
    yid = video.source.youtube_id
    captions_path = video_dir / "raw" / "captions.json"
    fetched = False
    if (fetch_captions and not captions_path.exists()) or refetch_captions:
        try:
            info = acquisition.fetch_info(yid)
            prefer = [x for x in (video.source.default_language, "uk", "ru", "en") if x]
            caps = geo_text.fetch_captions(info, prefer)
            write_json(captions_path, caps or {"lang": None, "kind": None, "cues": [], "english": None, "note": "no captions available"})
            fetched = True
        except Exception as e:  # captions are optional evidence
            log.warning("[%s] captions unavailable: %s", yid, str(e).splitlines()[0][:200])
    captions = geo_text.load_captions(captions_path)
    n_translated = 0
    if translate_en:
        try:
            n_translated = translate_captions(video_dir, captions, force=fetched or retranslate)
        except Exception as e:  # a reading aid; never blocks relocation
            log.warning("[%s] translation failed: %s", yid, str(e).splitlines()[0][:200])

    metas = sorted((video_dir / "frames" / "meta").glob("*.json"))
    records = [FrameRecord.model_validate_json(p.read_text()) for p in metas]
    n_ocr = 0
    if run_ocr and ocr.available():
        for rec in records:
            if rec.derived.ocr is None or force_ocr:
                rec.derived.ocr = ocr.read_text(lib.abs(rec.frame.files.web))
                n_ocr += 1
    vc = geo_text.video_clues(video, records, captions)
    base = infer(video.source, video.discovery, video.scope)
    n_clued = 0
    for path, rec in zip(metas, records):
        locs, dates = geo_text.frame_clues(vc, rec)
        n_clued += bool(locs)
        rec.inferred = base.model_copy(update={
            "locations": geo_text.merge(base.locations, locs),
            "capture_date": [*base.capture_date, *dates],
        })
        write_json(path, rec.model_dump(mode="json"))
        repo.upsert_frame(rec)
    return {"frames": len(records), "ocr": n_ocr, "with_frame_clues": n_clued,
            "speech_mentions": len(vc.speech), "chapters": len(vc.chapters),
            "captions": len((captions or {}).get("cues") or []), "translated": n_translated}


def analyze(lib: Library, repo: Repository, classifier: Classifier, youtube_id: str | None = None, force: bool = False) -> int:
    """Compute sorting features + embeddings for stored frames that lack them (from thumbnails)."""
    n = 0
    for video_dir in sorted(lib.videos.glob(youtube_id or "*")):
        metas = sorted((video_dir / "frames" / "meta").glob("*.json"))
        records = [FrameRecord.model_validate_json(p.read_text()) for p in metas]
        todo = [(p, r) for p, r in zip(metas, records) if force or r.derived.features is None]
        npz = video_dir / "frames" / "embeddings.npz"
        stored = visual.load_embeddings(npz)[0] if npz.exists() else {}
        for i in range(0, len(todo), 64):
            chunk = todo[i : i + 64]
            images = [Image.open(lib.abs(r.frame.files.thumb)) for _, r in chunk]
            have = hasattr(classifier, "embed") and all(r.frame_id in stored for _, r in chunk)
            # stored embeddings are reused, so re-running with new captions takes seconds
            feats, emb = visual.features(images, classifier, np.stack([stored[r.frame_id] for _, r in chunk]) if have else None)
            for (path, rec), fx in zip(chunk, feats):
                rec.derived.features = fx
                write_json(path, rec.model_dump(mode="json"))
                repo.upsert_frame(rec)
            if emb is not None:
                model = classifier.cfg.model
                rows = {rec.frame_id: v for (_, rec), v in zip(chunk, emb)}
                visual.save_embeddings(video_dir / "frames" / "embeddings.npz", rows, model)
                repo.upsert_embeddings(model, rows)
            n += len(chunk)
    return n


def reindex(lib: Library, repo: Repository) -> tuple[int, int]:
    """Rebuild the index from the canonical JSON sidecars. Returns (videos, frames).

    Videos without a passing scope check, or published outside the hard range, are skipped.
    """
    n_videos = n_frames = 0
    for video_json in sorted(lib.videos.glob("*/video.json")):
        video = VideoRecord.model_validate_json(video_json.read_text())
        if not (video.scope and video.scope.in_scope and in_date_range(video.source.published_at.date())):
            log.warning("skipping %s: not in collection scope (run `evidence rescope`)", video_json.parent.name)
            continue
        repo.upsert_video(video)
        n_videos += 1
        for meta in sorted((video_json.parent / "frames" / "meta").glob("*.json")):
            repo.upsert_frame(FrameRecord.model_validate_json(meta.read_text()))
            n_frames += 1
        if (npz := video_json.parent / "frames" / "embeddings.npz").exists():
            rows, model = visual.load_embeddings(npz)
            repo.upsert_embeddings(model, rows)
    return n_videos, n_frames


def _merge_contexts(old: list[DiscoveryContext], new: list[DiscoveryContext]) -> list[DiscoveryContext]:
    seen = {(c.run_id, c.query) for c in old}
    return [*old, *(c for c in new if (c.run_id, c.query) not in seen)]
