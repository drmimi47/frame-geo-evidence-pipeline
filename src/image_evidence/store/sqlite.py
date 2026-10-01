"""SQLite implementation of the Repository interface."""

from __future__ import annotations

import math

import numpy as np
import re
import sqlite3
import threading
from functools import lru_cache, wraps
from importlib import resources
from pathlib import Path

from ..schema import FrameRecord, VideoRecord
from ..search import parse_query, phrase_pattern
from .base import FrameQuery, NearbyFrame, SearchPage

EARTH_RADIUS_KM = 6371.0088


@lru_cache(maxsize=256)
def _compiled(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.IGNORECASE)


def _regexp(pattern: str, value: str | None) -> bool:
    """SQLite REGEXP operator (Unicode-aware, unlike LIKE, which only folds ASCII case)."""
    return value is not None and _compiled(pattern).search(value) is not None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _serialized(fn):
    @wraps(fn)
    def run(self, *args, **kwargs):
        with self._lock:
            return fn(self, *args, **kwargs)
    return run


class SQLiteRepository:
    # One connection is shared by the API's worker threads; sqlite3 connections are not safe for
    # concurrent use ("bad parameter or other API misuse"), so every public method holds a lock.
    def __init__(self, path: Path):
        self._lock = threading.RLock()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.create_function("regexp", 2, _regexp, deterministic=True)
        self.conn.executescript(resources.files(__package__).joinpath("schema_sqlite.sql").read_text())

    def close(self) -> None:
        self.conn.close()

    # ---------------------------------------------------------------- writes

    def upsert_video(self, v: VideoRecord) -> None:
        s = v.source
        with self.conn:
            self.conn.execute(
                """INSERT INTO videos (video_id, youtube_id, source_url, title, channel_title, description, tags,
                       published_at, published_year, duration_s, license, acquisition_status, status, record_json, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(video_id) DO UPDATE SET
                       title=excluded.title, channel_title=excluded.channel_title, description=excluded.description,
                       tags=excluded.tags, duration_s=excluded.duration_s, license=excluded.license,
                       acquisition_status=excluded.acquisition_status, status=excluded.status,
                       record_json=excluded.record_json, updated_at=excluded.updated_at""",
                (
                    v.video_id, s.youtube_id, s.source_url, s.title, s.channel_title, s.description, " | ".join(s.tags),
                    s.published_at.isoformat(), s.published_at.year, s.duration_s, s.license,
                    v.acquisition.status if v.acquisition else None, v.status, v.model_dump_json(), v.updated_at.isoformat(),
                ),
            )

    def upsert_frame(self, f: FrameRecord) -> None:
        src, core = f.source, f.frame
        with self.conn:
            self.conn.execute(
                """INSERT INTO frames (frame_id, video_id, youtube_id, source_url, published_at, published_year,
                       timestamp_s, frame_number, width, height, original_path, web_path, thumb_path, sha256, record_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(frame_id) DO UPDATE SET
                       video_id=excluded.video_id, youtube_id=excluded.youtube_id, source_url=excluded.source_url,
                       published_at=excluded.published_at, timestamp_s=excluded.timestamp_s,
                       frame_number=excluded.frame_number, width=excluded.width, height=excluded.height,
                       original_path=excluded.original_path,
                       web_path=excluded.web_path, thumb_path=excluded.thumb_path, sha256=excluded.sha256,
                       record_json=excluded.record_json""",
                (
                    f.frame_id, src.video_id, src.youtube_id, src.source_url, src.published_at.isoformat(),
                    src.published_at.year, core.timestamp_s, core.frame_number, core.width, core.height,
                    core.files.original, core.files.web, core.files.thumb, core.sha256, f.model_dump_json(),
                ),
            )
            self.conn.execute("DELETE FROM frame_categories WHERE frame_id=?", (f.frame_id,))
            self.conn.executemany(
                "INSERT INTO frame_categories (frame_id, label, confidence, method, model) VALUES (?,?,?,?,?)",
                [(f.frame_id, c.label, c.confidence, c.provenance.method, c.provenance.model) for c in f.derived.categories],
            )
            self.conn.execute("DELETE FROM frame_locations WHERE frame_id=?", (f.frame_id,))
            self.conn.executemany(
                "INSERT INTO frame_locations (frame_id, rank, latitude, longitude, place_name, confidence, method) VALUES (?,?,?,?,?,?,?)",
                [
                    (f.frame_id, i, loc.latitude, loc.longitude, loc.place_name, loc.confidence, loc.provenance.method)
                    for i, loc in enumerate(f.inferred.locations)
                ],
            )

    def upsert_embeddings(self, model: str, rows: dict[str, "np.ndarray"]) -> None:
        with self.conn:
            self.conn.executemany(
                "INSERT OR REPLACE INTO frame_embeddings(frame_id, model, vec) VALUES (?,?,?)",
                [(fid, model, np.asarray(v, np.float16).tobytes()) for fid, v in rows.items()],
            )

    def embedding_model(self) -> str | None:
        row = self.conn.execute("SELECT model FROM frame_embeddings LIMIT 1").fetchone()
        return row[0] if row else None

    def get_embeddings(self, frame_ids: list[str]) -> dict[str, "np.ndarray"]:
        out = {}
        for i in range(0, len(frame_ids), 500):
            chunk = frame_ids[i : i + 500]
            q = f"SELECT frame_id, vec FROM frame_embeddings WHERE frame_id IN ({','.join('?' * len(chunk))})"
            for fid, vec in self.conn.execute(q, chunk):
                out[fid] = np.frombuffer(vec, np.float16).astype(np.float32)
        return out

    def delete_frames_for_video(self, video_id: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM frames WHERE video_id=?", (video_id,))

    def delete_video(self, video_id: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM frames WHERE video_id=?", (video_id,))
            self.conn.execute("DELETE FROM videos WHERE video_id=?", (video_id,))

    # ----------------------------------------------------------------- reads

    def get_video(self, video_id: str) -> VideoRecord | None:
        row = self.conn.execute("SELECT record_json FROM videos WHERE video_id=?", (video_id,)).fetchone()
        return VideoRecord.model_validate_json(row[0]) if row else None

    def get_frame(self, frame_id: str) -> FrameRecord | None:
        row = self.conn.execute("SELECT record_json FROM frames WHERE frame_id=?", (frame_id,)).fetchone()
        return FrameRecord.model_validate_json(row[0]) if row else None

    def get_frames(self, frame_ids: list[str]) -> list[FrameRecord]:
        if not frame_ids:
            return []
        marks = ",".join("?" * len(frame_ids))
        rows = {r[0]: r[1] for r in self.conn.execute(f"SELECT frame_id, record_json FROM frames WHERE frame_id IN ({marks})", frame_ids)}
        return [FrameRecord.model_validate_json(rows[i]) for i in frame_ids if i in rows]

    def list_videos(self, limit: int = 100, offset: int = 0) -> list[VideoRecord]:
        rows = self.conn.execute("SELECT record_json FROM videos ORDER BY published_at DESC LIMIT ? OFFSET ?", (limit, offset))
        return [VideoRecord.model_validate_json(r[0]) for r in rows]

    def _where(self, q: FrameQuery) -> tuple[str, list]:
        clauses, params = [], []
        if q.text:
            labels = {r[0] for r in self.conn.execute("SELECT DISTINCT label FROM frame_categories")}
            text_sql = """(v.title || ' ' || COALESCE(v.tags, '') || ' ' || COALESCE(v.description, '') || ' '
                           || COALESCE(v.channel_title, ''))"""
            term_clauses, term_params = [], []
            for term in parse_query(q.text, labels):
                if term.categories:
                    marks = ",".join("?" * len(term.categories))
                    term_clauses.append(f"EXISTS (SELECT 1 FROM frame_categories c WHERE c.frame_id=f.frame_id AND c.label IN ({marks}) AND c.confidence>=?)")
                    term_params += [*term.categories, q.min_confidence]
                else:
                    term_clauses.append(f"""({text_sql} REGEXP ?
                        OR EXISTS (SELECT 1 FROM frame_locations l WHERE l.frame_id=f.frame_id AND l.place_name REGEXP ?))""")
                    term_params += [term.pattern, term.pattern]
            all_terms = " AND ".join(term_clauses) or "1"
            if phrase := phrase_pattern(q.text):
                clauses.append(f"(({all_terms}) OR {text_sql} REGEXP ?)")
                params += [*term_params, phrase]
            elif term_clauses:
                clauses.append(f"({all_terms})")
                params += term_params
        for cat in q.categories:
            clauses.append("EXISTS (SELECT 1 FROM frame_categories c WHERE c.frame_id=f.frame_id AND c.label=? AND c.confidence>=?)")
            params += [cat, q.min_confidence]
        if q.year is not None:
            clauses.append("f.published_year=?")
            params.append(q.year)
        if q.youtube_id:
            clauses.append("f.youtube_id=?")
            params.append(q.youtube_id)
        if q.has_coordinates is not None:
            clauses.append(("" if q.has_coordinates else "NOT ") + "EXISTS (SELECT 1 FROM frame_locations l WHERE l.frame_id=f.frame_id AND l.latitude IS NOT NULL)")
        if q.bbox:
            clauses.append("EXISTS (SELECT 1 FROM frame_locations l WHERE l.frame_id=f.frame_id AND l.longitude BETWEEN ? AND ? AND l.latitude BETWEEN ? AND ?)")
            params += [q.bbox[0], q.bbox[2], q.bbox[1], q.bbox[3]]
        return ("WHERE " + " AND ".join(clauses)) if clauses else "", params

    def search_frames(self, q: FrameQuery) -> SearchPage:
        where, params = self._where(q)
        base = f"FROM frames f JOIN videos v ON v.video_id=f.video_id {where}"
        total = self.conn.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]
        ids = [r[0] for r in self.conn.execute(
            f"SELECT f.frame_id {base} ORDER BY f.published_at DESC, f.video_id, f.timestamp_s LIMIT ? OFFSET ?",
            [*params, q.limit, q.offset],
        )]
        facets = {
            "category": {r[0]: r[1] for r in self.conn.execute(
                f"SELECT c.label, COUNT(DISTINCT c.frame_id) FROM frame_categories c WHERE c.frame_id IN (SELECT f.frame_id {base}) "
                "AND c.confidence>=? GROUP BY c.label ORDER BY 2 DESC", [*params, q.min_confidence])},
            "year": {str(r[0]): r[1] for r in self.conn.execute(
                f"SELECT f.published_year, COUNT(*) {base} GROUP BY f.published_year ORDER BY 1", params)},
        }
        return SearchPage(ids, total, facets)

    def frames_near(self, lat: float, lon: float, radius_km: float, limit: int = 50) -> list[NearbyFrame]:
        dlat = radius_km / 111.0
        dlon = radius_km / max(1e-6, 111.0 * math.cos(math.radians(lat)))
        rows = self.conn.execute(
            """SELECT frame_id, MIN(rank) AS rank, latitude, longitude FROM frame_locations
               WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ? GROUP BY frame_id""",
            (lat - dlat, lat + dlat, lon - dlon, lon + dlon),
        )
        hits = [NearbyFrame(r["frame_id"], round(haversine_km(lat, lon, r["latitude"], r["longitude"]), 3)) for r in rows]
        return sorted((h for h in hits if h.distance_km <= radius_km), key=lambda h: h.distance_km)[:limit]

    def frames_at_place(self, place_name: str, limit: int = 50) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT frame_id FROM frame_locations WHERE place_name = ? COLLATE NOCASE LIMIT ?", (place_name, limit)
        )
        return [r[0] for r in rows]


for _name, _fn in list(vars(SQLiteRepository).items()):
    if callable(_fn) and not _name.startswith("_"):
        setattr(SQLiteRepository, _name, _serialized(_fn))
