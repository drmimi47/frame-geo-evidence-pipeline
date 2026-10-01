"""Read-only HTTP API over EvidenceService (requires the [api] extra)."""

from __future__ import annotations

from pathlib import Path

import hashlib
import io
import threading

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .layout import Library
from .service import EvidenceService
from .store import SQLiteRepository


def create_app(library_dir: Path, study_areas: list | None = None) -> FastAPI:
    from .focus import study_places

    lib = Library(library_dir)
    repo = SQLiteRepository(lib.db_path)
    svc = EvidenceService(repo, media_base="/media/", study_places=study_places(study_areas or []))
    app = FastAPI(title="image-evidence API", version="0.1.0")

    @app.get("/api/study-places")
    def study_places_list():
        """The study areas' places, for the Sort menu's "Near ..." entries."""
        return [{"sort": f"near:{name}", "name": name} for name in svc.study_places]

    @app.get("/api/frames")
    def search(
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
        return svc.search(q, category, year, video, min_confidence, limit, offset, sort, image)

    # Search by image: the upload is embedded with the same SigLIP model as the library's frames and
    # kept in memory only (never written to the library). The model loads on first use (~20 s).
    embedder: dict = {}
    lock = threading.Lock()

    @app.post("/api/query-image")
    async def query_image(request: Request):
        from PIL import Image, UnidentifiedImageError

        body = await request.body()
        if not body or len(body) > 25_000_000:
            raise HTTPException(400, "send one image up to 25 MB as the request body")
        try:
            img = Image.open(io.BytesIO(body)).convert("RGB")
        except UnidentifiedImageError:
            raise HTTPException(400, "not an image")
        img.thumbnail((400, 400))  # same scale as the stored thumbnails the library was embedded from
        key = hashlib.sha1(body).hexdigest()[:16]
        if key not in svc.query_images:
            with lock:
                if "clf" not in embedder:
                    from .classify import SiglipClassifier, classify_available
                    from .config import ClassificationConfig

                    model = repo.embedding_model()
                    if not model or not classify_available():
                        raise HTTPException(503, "no image embeddings in this library (run `evidence analyze`)")
                    embedder["clf"] = SiglipClassifier(ClassificationConfig(model=model))
                svc.query_images[key] = embedder["clf"].embed([img])[0]
        return {"id": key}

    @app.get("/api/stats")
    def stats():
        return svc.stats()

    @app.get("/api/frames/{frame_id}")
    def frame(frame_id: str):
        if (f := svc.frame(frame_id)) is None:
            raise HTTPException(404, "frame not found")
        return f

    @app.get("/api/frames/{frame_id}/related")
    def related(frame_id: str, radius_km: float = 5.0, limit: int = 24):
        return svc.related(frame_id, radius_km, limit)

    @app.get("/api/videos")
    def videos(limit: int = 100, offset: int = 0):
        return svc.videos(limit, offset)

    @app.get("/api/videos/{video_id}")
    def video(video_id: str):
        if (v := svc.video(video_id)) is None:
            raise HTTPException(404, "video not found")
        return v

    @app.get("/api/videos/{video_id}/subtitles")
    def subtitles(video_id: str):
        from . import geo_text

        v = repo.get_video(video_id)
        if v is None:
            raise HTTPException(404, "video not found")
        video_dir = lib.videos / v.source.youtube_id
        captions = geo_text.load_captions(video_dir / "raw" / "captions.json")
        return {"video_id": video_id, "fetched": captions is not None,
                **geo_text.subtitles(v, captions, geo_text.english_captions(video_dir, captions))}

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

    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "web"), name="static")
    app.mount("/media/videos", StaticFiles(directory=lib.videos), name="media")
    return app
