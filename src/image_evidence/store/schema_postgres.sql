-- PostgreSQL/PostGIS target schema (not yet used by code). Mirrors schema_sqlite.sql.
-- Migration path: implement store.base.Repository for Postgres, then run
-- `evidence reindex` against it -- JSON sidecars are the canonical source.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE videos (
    video_id            TEXT PRIMARY KEY,
    youtube_id          TEXT NOT NULL UNIQUE,
    source_url          TEXT NOT NULL,
    title               TEXT NOT NULL,
    channel_title       TEXT,
    description         TEXT,
    tags                TEXT[],
    published_at        TIMESTAMPTZ NOT NULL,
    published_year      INTEGER GENERATED ALWAYS AS (EXTRACT(YEAR FROM published_at AT TIME ZONE 'UTC')) STORED,
    duration_s          DOUBLE PRECISION,
    license             TEXT,
    acquisition_status  TEXT,
    status              TEXT NOT NULL,
    record              JSONB NOT NULL,
    updated_at          TIMESTAMPTZ NOT NULL,
    search              TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(description,'') || ' ' || coalesce(channel_title,''))
    ) STORED
);
CREATE INDEX videos_search ON videos USING GIN (search);

CREATE TABLE frames (
    frame_id        TEXT PRIMARY KEY,
    video_id        TEXT NOT NULL REFERENCES videos(video_id),
    youtube_id      TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    published_at    TIMESTAMPTZ NOT NULL,
    published_year  INTEGER NOT NULL,
    timestamp_s     DOUBLE PRECISION NOT NULL,
    frame_number    INTEGER NOT NULL,
    width           INTEGER NOT NULL,
    height          INTEGER NOT NULL,
    original_path   TEXT NOT NULL,
    web_path        TEXT NOT NULL,
    thumb_path      TEXT NOT NULL,
    sha256          TEXT NOT NULL,
    record          JSONB NOT NULL,
    UNIQUE (video_id, frame_number)
);

CREATE FUNCTION frames_source_immutable() RETURNS trigger AS $$
BEGIN
    IF (OLD.video_id, OLD.youtube_id, OLD.source_url, OLD.published_at, OLD.timestamp_s,
        OLD.frame_number, OLD.width, OLD.height, OLD.original_path)
       IS DISTINCT FROM
       (NEW.video_id, NEW.youtube_id, NEW.source_url, NEW.published_at, NEW.timestamp_s,
        NEW.frame_number, NEW.width, NEW.height, NEW.original_path) THEN
        RAISE EXCEPTION 'frame source link is immutable';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER frames_source_immutable BEFORE UPDATE ON frames
    FOR EACH ROW EXECUTE FUNCTION frames_source_immutable();

CREATE TABLE frame_categories (
    frame_id    TEXT NOT NULL REFERENCES frames(frame_id) ON DELETE CASCADE,
    label       TEXT NOT NULL,
    confidence  REAL NOT NULL,
    method      TEXT NOT NULL,
    model       TEXT,
    PRIMARY KEY (frame_id, label, method)
);
CREATE INDEX frame_categories_label ON frame_categories(label, confidence);

CREATE TABLE frame_locations (
    frame_id    TEXT NOT NULL REFERENCES frames(frame_id) ON DELETE CASCADE,
    rank        INTEGER NOT NULL,
    geom        geography(Point, 4326),   -- NULL when coordinates are unknown
    place_name  TEXT,
    confidence  REAL NOT NULL,
    method      TEXT NOT NULL,
    PRIMARY KEY (frame_id, rank)
);
CREATE INDEX frame_locations_geom ON frame_locations USING GIST (geom);
-- related-by-proximity: ORDER BY geom <-> ST_MakePoint(lon, lat)::geography, or ST_DWithin(geom, point, meters)
