-- SQLite index schema. Kept close to portable SQL; see schema_postgres.sql for the
-- PostGIS equivalent. Full records live in record_json; columns exist for querying.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS videos (
    video_id            TEXT PRIMARY KEY,
    youtube_id          TEXT NOT NULL UNIQUE,
    source_url          TEXT NOT NULL,
    title               TEXT NOT NULL,
    channel_title       TEXT,
    description         TEXT,
    tags                TEXT,              -- ' | ' joined, for text search
    published_at        TEXT NOT NULL,     -- ISO-8601 UTC, YouTube publication time
    published_year      INTEGER NOT NULL,
    duration_s          REAL,
    license             TEXT,
    acquisition_status  TEXT,
    status              TEXT NOT NULL,
    record_json         TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS frames (
    frame_id        TEXT PRIMARY KEY,
    video_id        TEXT NOT NULL REFERENCES videos(video_id),
    youtube_id      TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    published_at    TEXT NOT NULL,
    published_year  INTEGER NOT NULL,
    timestamp_s     REAL NOT NULL,
    frame_number    INTEGER NOT NULL,
    width           INTEGER NOT NULL,
    height          INTEGER NOT NULL,
    original_path   TEXT NOT NULL,
    web_path        TEXT NOT NULL,
    thumb_path      TEXT NOT NULL,
    sha256          TEXT NOT NULL,
    record_json     TEXT NOT NULL,
    UNIQUE (video_id, frame_number)
);
CREATE INDEX IF NOT EXISTS frames_video ON frames(video_id, timestamp_s);

-- SigLIP image embeddings (float16), for "similar view" ordering. Canonical copy: frames/embeddings.npz.
CREATE TABLE IF NOT EXISTS frame_embeddings (
    frame_id    TEXT PRIMARY KEY REFERENCES frames(frame_id) ON DELETE CASCADE,
    model       TEXT NOT NULL,
    vec         BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS frames_year ON frames(published_year);

-- The frame -> source relationship is immutable once written.
CREATE TRIGGER IF NOT EXISTS frames_source_immutable
BEFORE UPDATE ON frames
WHEN OLD.video_id IS NOT NEW.video_id
  OR OLD.youtube_id IS NOT NEW.youtube_id
  OR OLD.source_url IS NOT NEW.source_url
  OR OLD.published_at IS NOT NEW.published_at
  OR OLD.timestamp_s IS NOT NEW.timestamp_s
  OR OLD.frame_number IS NOT NEW.frame_number
  OR OLD.width IS NOT NEW.width
  OR OLD.height IS NOT NEW.height
  OR OLD.original_path IS NOT NEW.original_path
BEGIN
    SELECT RAISE(ABORT, 'frame source link is immutable');
END;

-- Derived: visual categories (multi-label).
CREATE TABLE IF NOT EXISTS frame_categories (
    frame_id    TEXT NOT NULL REFERENCES frames(frame_id) ON DELETE CASCADE,
    label       TEXT NOT NULL,
    confidence  REAL NOT NULL,
    method      TEXT NOT NULL,
    model       TEXT,
    PRIMARY KEY (frame_id, label, method)
);
CREATE INDEX IF NOT EXISTS frame_categories_label ON frame_categories(label, confidence);

-- Inferred: candidate locations. latitude/longitude are NULL when unknown.
CREATE TABLE IF NOT EXISTS frame_locations (
    frame_id    TEXT NOT NULL REFERENCES frames(frame_id) ON DELETE CASCADE,
    rank        INTEGER NOT NULL,
    latitude    REAL,
    longitude   REAL,
    place_name  TEXT,
    confidence  REAL NOT NULL,
    method      TEXT NOT NULL,
    PRIMARY KEY (frame_id, rank),
    CHECK ((latitude IS NULL) = (longitude IS NULL))
);
CREATE INDEX IF NOT EXISTS frame_locations_latlon ON frame_locations(latitude, longitude);
CREATE INDEX IF NOT EXISTS frame_locations_place ON frame_locations(place_name);
