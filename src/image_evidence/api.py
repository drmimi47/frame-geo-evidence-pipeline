"""HTTP API over EvidenceService (requires the [api] extra).

Read-only over the libraries, except /api/jobs (the site's Video panel adds videos through it, jobs.py),
/api/folders (rename, show in Finder), and /api/satellite/jobs and /api/seam/films (the Satellite panel adds passes and
renders films into "The Conductive Seam": satellite/). Each evidence folder is a library: the main one (`library/`, Ukraine
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


def create_app(library_dir: Path, study_areas: list | None = None, seam_config: Path | None = None) -> FastAPI:
    from .focus import study_places
    from .jobs import JobRequest, Jobs, list_libraries, next_folder, rename_folder, scope_label
    from .satellite.store import SatelliteIndex

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
                                  has_file=lambda rel, lib=lib: lib.abs(rel).is_file(), satellite=SatelliteIndex(lib.root))
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
        """Videos with an inferred camera path (`inferred/track.json`, made by `evidence track`): the Route Map."""
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

    # Scene Viewer: a 3D reconstruction made from a video's own footage (`derived/scene/scene.json` beside its files)
    SCENE_FILES = {".json", ".ply", ".spz", ".splat", ".ksplat", ".jpg", ".webp"}

    def scene_dir(x, video_id: str) -> tuple[Path, object]:
        v = x.repo.get_video(video_id)
        if v is None:
            raise HTTPException(404, "video not found")
        return x.lib.videos / v.source.youtube_id / "derived" / "scene", v

    @app.get("/api/scenes")
    def scenes(request: Request):
        """Videos with a 3D reconstruction: the Scene Viewer."""
        x = ctx(request)
        return [{"video_id": v.video_id, "youtube_id": v.source.youtube_id, "title": v.source.title}
                for v in x.repo.list_videos(1000, 0)
                if (x.lib.videos / v.source.youtube_id / "derived" / "scene" / "scene.json").exists()]

    @app.get("/api/videos/{video_id}/scene")
    def scene(request: Request, video_id: str):
        import json

        d, v = scene_dir(ctx(request), video_id)
        if not (d / "scene.json").exists():
            raise HTTPException(404, "no reconstruction for this video")
        return {**json.loads((d / "scene.json").read_text()), "title": v.source.title,
                "channel_title": v.source.channel_title, "published_at": v.source.published_at.isoformat(),
                "source_url": v.source.source_url, "base_url": f"/api/videos/{video_id}/scene/",
                # the land around a take (scripts/scene/terrain.py), when it was built
                "terrain": "terrain.json" if (d / "terrain.json").exists() else None}

    @app.get("/api/videos/{video_id}/scene/{name}")
    def scene_file(request: Request, video_id: str, name: str):
        d, _ = scene_dir(ctx(request), video_id)
        f = d / name
        if "/" in name or name.startswith(".") or f.suffix not in SCENE_FILES or not f.is_file():
            raise HTTPException(404, "no such file")
        return FileResponse(f, headers={"Cache-Control": "no-cache"})

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
                        "videos": st["videos"], "frames": st["frames"], "passes": st.get("passes", 0), "current": x["slug"] == current})
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

    # ------------------------------------------------------------ Satellite panel, The Conductive Seam view

    from datetime import date

    from .jobs import ensure_seam_folder, folder_title
    from .satellite import SEAM_SLUG
    from .satellite import corridor as sat_corridor
    from .satellite import fetch as sat_fetch
    from .satellite import film as sat_film
    from .satellite import store as sat_store
    from .satellite.providers import SENSORS
    from .scope import UKRAINE, library_scope

    seam_root = main_root.parent / "libraries" / SEAM_SLUG
    lines_cache: dict[str, list] = {}

    def seam_cfg():
        return sat_fetch.SeamConfig.load(seam_config)

    def corridors_of(root: Path) -> list[dict]:
        out = []
        for cid in sat_store.corridor_ids(root):
            g = sat_store.read_georef(root, cid)
            out.append({"corridor_id": cid, "name": g["name"], "bbox": g["grid"]["bbox"], "line": g["line"]["label"],
                        "length_m": g["line"]["length_m"], "grid": g["grid"],
                        "passes": [{"pass_id": p.pass_id, "title": sat_store.pass_title(p), "sensor": p.source.sensor,
                                    "acquired_at": p.source.acquired_at.isoformat(), "cloud_share": p.derived.cloud_share}
                                   for p in sat_store.read_passes(root, cid)]})
        return out

    @app.get("/api/satellite/setup")
    def satellite_setup():
        cfg = seam_cfg()
        have = (seam_root / "scope.json").is_file()
        return {
            "folder": {"slug": SEAM_SLUG, "title": folder_title(seam_root, False) if have else "The Conductive Seam", "exists": have},
            "areas": [{"id": a.corridor_id, "name": a.name, "bbox": list(a.bbox), "lines": a.lines, "note": a.note}
                      for a in cfg.areas.values()],
            "corridors": corridors_of(seam_root) if have else [],
            "sensors": [{"name": x.name, "label": x.label, "first_year": x.first_year, "gsd_m": x.gsd_m} for x in SENSORS.values()],
            "fetch": {k: str(v) for k, v in cfg.fetch.items()}, "film": cfg.film,
        }

    @app.get("/api/satellite/lines")
    def satellite_lines(bbox: str):
        """The power lines in a box (OpenStreetMap, for choosing a new corridor's line); cached while the server runs."""
        try:
            box = tuple(float(x) for x in bbox.split(","))
            assert len(box) == 4 and box[0] < box[2] and box[1] < box[3] and (box[2] - box[0]) * (box[3] - box[1]) <= 0.5
        except (ValueError, AssertionError):
            raise HTTPException(400, "a box is west,south,east,north, at most about 0.5 square degrees")
        key = ",".join(f"{x:.4f}" for x in box)
        if key not in lines_cache:
            import httpx

            try:
                lines_cache[key] = sat_corridor.choices(sat_corridor.fetch_power(box, httpx.Client(), rounds=2))
            except RuntimeError as e:
                raise HTTPException(503, str(e))
        return lines_cache[key]

    def area_for(d: dict, cfg) -> "sat_fetch.Area":
        v = d.get("area")
        if isinstance(v, dict):  # a new corridor: an id, a name, a box and lines
            return sat_fetch.Area.from_dict(str(v.get("corridor_id") or ""), v)
        return sat_fetch.area_named(seam_root, cfg, str(v or ""))

    def seam_job(kind: str, work) -> dict:
        root = ensure_seam_folder(main_root)
        library(SEAM_SLUG)  # (listed and opened)
        return jobs.start_task(kind, SEAM_SLUG, folder_title(root, False), scope_label(library_scope(root)), work).public()

    @app.post("/api/satellite/jobs")
    async def satellite_job(request: Request):
        same_site(request)
        d = await request.json()
        cfg = seam_cfg()
        try:
            area = area_for(d, cfg)
            sensor = str(d.get("sensor") or cfg.fetch.get("sensor") or "sentinel-2")
            if sensor not in SENSORS:
                raise ValueError("choose Sentinel-2 or Landsat")
            start = date.fromisoformat(str(d.get("start") or cfg.fetch.get("start") or "2023-07-01"))
            end = date.fromisoformat(str(d.get("end") or cfg.fetch.get("end") or "2023-09-30"))
            max_cloud = min(100.0, max(0.0, float(d.get("max_cloud") or cfg.fetch.get("max_cloud") or 5)))
            until_km = float(d["until_km"]) if d.get("until_km") else None
            # the area gate before the job is queued (and again in it), so a refused area never makes the folder
            if sat_store.read_georef(seam_root, area.corridor_id) is None:
                sat_fetch.check_area(library_scope(seam_root) if (seam_root / "scope.json").is_file() else UKRAINE, area.bbox)
        except (ValueError, TypeError, KeyError) as e:
            raise HTTPException(400, str(e))

        def work(job):
            job.results.append(sat_fetch.run(seam_root, library_scope(seam_root), area, sensor, start, end, max_cloud,
                                             until_km=until_km))
        return seam_job("satellite", work)

    @app.post("/api/seam/films")
    async def film_job(request: Request):
        same_site(request)
        d = await request.json()
        cid = str(d.get("corridor_id") or "")
        if sat_store.read_georef(seam_root, cid) is None:
            raise HTTPException(400, "fetch a pass for this corridor first")
        passes = [str(x) for x in d.get("passes") or []] or None
        options = {k: v for k, v in (d.get("options") or {}).items() if k in sat_film.DEFAULTS}

        def work(job):
            cfg = seam_cfg()
            area = cfg.areas.get(cid)
            f = sat_film.render(seam_root, cid, passes, {**cfg.film, **(area.film if area else {}), **options})
            job.results.append({"status": "processed", "title": f"Film, {f['duration_s']:.0f} s, {len(f['passes'])} pass"
                                + ("" if len(f["passes"]) == 1 else "es"), "film_id": f["film_id"], "corridor_id": cid})
        return seam_job("film", work)

    def film_urls(f: dict) -> dict:
        base = f"/api/seam/films/{f['corridor_id']}/{f['film_id']}/"
        return {**f, "urls": {k: base + v for k, v in f["files"].items()}}

    @app.get("/api/seam/films")
    def seam_films():
        """Every film of The Conductive Seam, newest first (whichever folder the grid shows)."""
        return [film_urls(f) for f in sat_store.films(seam_root)] if seam_root.is_dir() else []

    @app.get("/api/seam/films/{corridor_id}/{film_id}/{name}")
    def seam_film_file(corridor_id: str, film_id: str, name: str):
        base = (seam_root / "satellite" / "corridors").resolve()
        f = (base / corridor_id / "films" / film_id / name).resolve()
        if not f.is_relative_to(base) or name not in ("film.mp4", "poster.webp", "contact.webp", "film.json") or not f.is_file():
            raise HTTPException(404, "no such file")
        return FileResponse(f, headers={"Cache-Control": "no-cache"})  # (byte ranges: video seeking)

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
        served = (x.lib.videos.resolve(), (x.lib.root / "satellite").resolve())  # (not evidence.db, scope.json, ...)
        if not any(f.is_relative_to(d) for d in served) or not f.is_file():
            raise HTTPException(404)
        return FileResponse(f)

    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "web"), name="static")
    app.mount("/media/videos", StaticFiles(directory=Library(main_root).create().videos), name="media")
    return app


def _null():
    from .classify import NullClassifier

    return NullClassifier()
