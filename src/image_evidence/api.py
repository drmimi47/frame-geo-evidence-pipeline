"""HTTP API over EvidenceService (requires the [api] extra).

Read-only over the libraries, except /api/jobs (the site's Video panel adds videos through it, jobs.py) and
/api/folders (rename, show in Finder). Each evidence folder is a library: the main one (`library/`, Ukraine
2022..2026) or a project folder in `libraries/`; the `lib` cookie picks which one the site shows (none: the main one).
"""

from __future__ import annotations

import hashlib
import io
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .layout import Library
from .service import EvidenceService
from .store import SQLiteRepository


@dataclass
class _Lib:
    slug: str
    lib: Library
    repo: SQLiteRepository
    svc: EvidenceService
    scope: object


def create_app(library_dir: Path, study_areas: list | None = None) -> FastAPI:
    from .focus import study_places
    from .jobs import JobRequest, Jobs, list_libraries, next_folder, rename_folder, scope_label

    main_root = Path(library_dir)
    places = study_places(study_areas or [])
    app = FastAPI(title="image-evidence API", version="0.1.0")
    opened: dict[str, _Lib] = {}

    def library(slug: str) -> _Lib | None:
        if slug not in opened:
            known = {x["slug"]: x for x in list_libraries(main_root)}
            if slug not in known:
                return None
            x = known[slug]
            lib = Library(x["root"]).create()
            repo = SQLiteRepository(lib.db_path)
            base = f"/media/lib/{slug}/" if slug else "/media/"
            # the study areas are places in Ukraine: their "Near ..." sorts belong to the main library
            svc = EvidenceService(repo, media_base=base, study_places=places if not slug else {},
                                  has_file=lambda rel, lib=lib: lib.abs(rel).is_file())
            opened[slug] = _Lib(slug, lib, repo, svc, x["scope"])
        return opened[slug]

    def first_with_images() -> str:
        """With no folder chosen yet, the site opens the first folder that holds images (the main one first)."""
        for x in list_libraries(main_root):
            if library(x["slug"]).svc.stats()["frames"]:
                return x["slug"]
        return ""

    def ctx(request: Request) -> _Lib:
        slug = request.cookies.get("lib")
        return (library(slug) if slug is not None else None) or library(first_with_images())

    # One SigLIP model for search by image and for jobs (it is ~3.5 GB): loaded on first use (~20 s).
    models: dict = {}
    model_lock = threading.Lock()

    def siglip(model: str | None = None):
        from .classify import SiglipClassifier, classify_available
        from .config import ClassificationConfig

        cfg = ClassificationConfig(model=model) if model else ClassificationConfig()
        with model_lock:
            if cfg.model not in models:
                if not classify_available():
                    return None
                models[cfg.model] = SiglipClassifier(cfg)
            return models[cfg.model]

    def job_done(job) -> None:
        if (x := opened.get(job.library)) is not None:
            x.svc._videos.clear()  # new videos: forget cached lookups

    jobs = Jobs(main_root, classifier=lambda: siglip() or _null(), on_done=job_done)

    @app.get("/api/study-places")
    def study_places_list(request: Request):
        """The study areas' places, for the Sort menu's "Near ..." entries."""
        return [{"sort": f"near:{name}", "name": name} for name in ctx(request).svc.study_places]

    @app.get("/api/frames")
    def search(
        request: Request,
        q: str | None = None,
        category: list[str] = Query(default=[]),
        year: int | None = None,
        video: str | None = None,
        min_confidence: float = 0.0,
        limit: int = 60,
        offset: int = 0,
        sort: str = "video",
        image: str | None = None,
    ):
        return ctx(request).svc.search(q, category, year, video, min_confidence, limit, offset, sort, image)

    # Search by image: the upload is embedded with the same SigLIP model as the library's frames and
    # kept in memory only (never written to the library).
    @app.post("/api/query-image")
    async def query_image(request: Request):
        from PIL import Image, UnidentifiedImageError

        x = ctx(request)
        body = await request.body()
        if not body or len(body) > 25_000_000:
            raise HTTPException(400, "send one image up to 25 MB as the request body")
        try:
            img = Image.open(io.BytesIO(body)).convert("RGB")
        except UnidentifiedImageError:
            raise HTTPException(400, "not an image")
        img.thumbnail((400, 400))  # same scale as the stored thumbnails the library was embedded from
        key = hashlib.sha1(body).hexdigest()[:16]
        if key not in x.svc.query_images:
            model = x.repo.embedding_model()
            clf = siglip(model) if model else None
            if clf is None:
                raise HTTPException(503, "no image embeddings in this library (run `evidence analyze`)")
            x.svc.query_images[key] = clf.embed([img])[0]
        return {"id": key}

    @app.get("/api/stats")
    def stats(request: Request):
        return ctx(request).svc.stats()

    @app.get("/api/frames/{frame_id}")
    def frame(request: Request, frame_id: str):
        if (f := ctx(request).svc.frame(frame_id)) is None:
            raise HTTPException(404, "frame not found")
        return f

    @app.get("/api/frames/{frame_id}/related")
    def related(request: Request, frame_id: str, radius_km: float = 5.0, limit: int = 24):
        return ctx(request).svc.related(frame_id, radius_km, limit)

    @app.get("/api/videos")
    def videos(request: Request, limit: int = 100, offset: int = 0):
        return ctx(request).svc.videos(limit, offset)

    @app.get("/api/videos/{video_id}")
    def video(request: Request, video_id: str):
        if (v := ctx(request).svc.video(video_id)) is None:
            raise HTTPException(404, "video not found")
        return v

    @app.get("/api/videos/{video_id}/subtitles")
    def subtitles(request: Request, video_id: str):
        from . import geo_text

        x = ctx(request)
        v = x.repo.get_video(video_id)
        if v is None:
            raise HTTPException(404, "video not found")
        video_dir = x.lib.videos / v.source.youtube_id
        captions = geo_text.load_captions(video_dir / "raw" / "captions.json")
        return {"video_id": video_id, "fetched": captions is not None,
                **geo_text.subtitles(v, captions, geo_text.english_captions(video_dir, captions))}

    @app.get("/api/tracks")
    def tracks(request: Request):
        """Videos with an inferred camera path (`inferred/track.json`, made by `evidence track`): the Temporal Map."""
        from .track import track_path

        x = ctx(request)
        out = []
        for v in x.repo.list_videos(1000, 0):
            p = track_path(x.lib.videos / v.source.youtube_id)
            if p.exists():
                out.append({"video_id": v.video_id, "youtube_id": v.source.youtube_id, "title": v.source.title})
        return out

    @app.get("/api/videos/{video_id}/track")
    def track(request: Request, video_id: str):
        import json

        from .track import track_path

        x = ctx(request)
        v = x.repo.get_video(video_id)
        if v is None:
            raise HTTPException(404, "video not found")
        p = track_path(x.lib.videos / v.source.youtube_id)
        if not p.exists():
            raise HTTPException(404, "no inferred track for this video")
        t = json.loads(p.read_text())
        frames = {f.frame_id: f for f in x.repo.get_frames([f["frame_id"] for f in t["frames"]])}
        for f in t["frames"]:
            if rec := frames.get(f["frame_id"]):
                s = x.svc.summary(rec)
                f["thumb_url"], f["web_url"] = s["thumb_url"], s["web_url"]
        return {**t, "title": v.source.title, "channel_title": v.source.channel_title,
                "published_at": v.source.published_at.isoformat(), "duration_s": v.source.duration_s,
                "source_url": v.source.source_url}

    # ------------------------------------------------------------ Video panel

    def same_site(request: Request) -> None:
        """Only this site may change things: JSON bodies need a CORS preflight, which this server never grants,
        and a browser's Origin must be this host."""
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            raise HTTPException(415, "send JSON")
        origin = request.headers.get("origin")
        if origin and origin.split("://", 1)[-1] != request.headers.get("host"):
            raise HTTPException(403, "only this site can do that")

    def shown_path(root: Path) -> str:
        root = root.resolve()
        for base, label in ((Path.cwd(), ""), (Path.home(), "~/")):
            if root.is_relative_to(base):
                return label + root.relative_to(base).as_posix()
        return str(root)

    @app.get("/api/folders")
    def folders(request: Request):
        """The evidence folders (each a library), with where they are on disk and what they hold."""
        current = ctx(request).slug
        out = []
        for x in list_libraries(main_root):
            st = library(x["slug"]).svc.stats()
            sc = x["scope"]
            out.append({"slug": x["slug"], "title": x["title"], "scope": scope_label(sc), "place": sc.name,
                        "start": sc.start.year, "end": sc.end.year, "path": shown_path(x["root"]),
                        "videos": st["videos"], "frames": st["frames"], "current": x["slug"] == current})
        slug, title = next_folder(main_root)
        return {"folders": out, "next": {"slug": slug, "title": title}}

    @app.post("/api/folders/rename")
    async def rename(request: Request):
        same_site(request)
        d = await request.json()
        try:
            return {"title": rename_folder(main_root, str(d.get("slug") or ""), str(d.get("title") or ""))}
        except ValueError as e:
            raise HTTPException(400, str(e))

    @app.post("/api/folders/reveal")
    async def reveal(request: Request):
        """Open the folder in the computer's file browser (the server runs on this computer)."""
        same_site(request)
        x = library(str((await request.json()).get("slug") or ""))
        if x is None:
            raise HTTPException(404, "no such folder")
        cmd = {"darwin": ["open"], "win32": ["explorer"]}.get(sys.platform, ["xdg-open"])
        subprocess.Popen([*cmd, str(x.lib.root.resolve())], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"ok": True}

    @app.get("/api/ingest/setup")
    def ingest_setup():
        from .jobs import LLM_MODEL

        return {"llm_model": LLM_MODEL}

    @app.post("/api/jobs")
    async def start_job(request: Request):
        same_site(request)
        try:
            return jobs.start(JobRequest.parse(await request.json())).public()
        except (ValueError, TypeError) as e:
            raise HTTPException(400, str(e))

    @app.get("/api/jobs")
    def job_list():
        return [j.public() for j in list(jobs.jobs.values())[-10:]]

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str):
        if (j := jobs.get(job_id)) is None:
            raise HTTPException(404, "no such job")
        return j.public()

    # The site's own files are revalidated on every load (cheap: an ETag check), so after an edit the
    # browser never mixes a new app.js with a stale cached module.
    @app.middleware("http")
    async def revalidate_site(request: Request, call_next):
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(Path(__file__).parent / "web" / "index.html")

    @app.get("/media/lib/{slug}/{path:path}", include_in_schema=False)
    def other_media(slug: str, path: str):
        x = library(slug) if slug else None
        if x is None:
            raise HTTPException(404)
        f = (x.lib.root / path).resolve()
        if not f.is_relative_to(x.lib.videos.resolve()) or not f.is_file():
            raise HTTPException(404)
        return FileResponse(f)

    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "web"), name="static")
    app.mount("/media/videos", StaticFiles(directory=Library(main_root).create().videos), name="media")
    return app


def _null():
    from .classify import NullClassifier

    return NullClassifier()
