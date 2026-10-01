# frame-geo-evidence-pipeline

This pipeline ingests visual evidence from YouTube:

1. It finds videos published 2022–2026 through the **official YouTube Data API v3**.
2. It uses **yt-dlp** to save metadata and, where policy permits, the source media.
3. It extracts timestamped frames with **FFmpeg/OpenCV**.
4. It tags each frame with categories (multi-label) using **SigLIP**.
5. It writes normalized JSON for every frame, keeping confidence and provenance on every value that isn't a plain fact.

The **source object** is a YouTube video. The **research object** is a timestamped frame.

## Scope (hard limits)

- **Ukraine only.** Before anything is downloaded or stored, each video must pass a Ukraine-relevance check (`scope.py`). The check combines several signals:
  - the uploader's geotag, which rejects the video if it's outside Ukraine;
  - Ukrainian places named in the title, tags or description (English, Ukrainian and Russian spellings);
  - Ukrainian-language text.

  Language alone is not enough to pass. The result and its evidence are stored in `video.json` → `scope`.
- **YouTube publication date 2022-01-01 to 2026-12-31.** The config refuses wider ranges, and every ingest path rejects videos published outside them.
- **Content may be older than 2022.** The date limit applies only to the upload date. Capture date is always inferred: publication is only an upper bound, and pre-2022 hints (year mentions, "archive", "до війни") become low-confidence candidates.
- Rejected videos leave no files and appear only in `library/runs/*.json`. `evidence rescope --purge` re-checks the library and deletes anything that no longer passes.

See `CLAUDE.md` for the full guidelines.

## Quick start

Requirements: Python ≥ 3.11, `ffmpeg`/`ffprobe`, and a JS runtime (`node` or `deno`). yt-dlp needs the JS runtime to read YouTube's player.

```sh
brew install ffmpeg uv
uv venv --python 3.12 && uv pip install -e ".[classify,api,dev]"   # [classify] pulls torch; optional
source .venv/bin/activate
evidence doctor                                   # checks tools, API key, classifier

cp .env.example .env                              # then set YOUTUBE_API_KEY=... in .env
evidence discover -c config/example.yaml          # dry run: list candidates only
evidence ingest   -c config/example.yaml          # full pipeline

evidence ingest-video https://youtu.be/<id> -c config/example.yaml   # one known video
evidence search "old town" --category ruins --year 2023
evidence show  yt_<id>_f0000300
evidence related yt_<id>_f0000300
evidence reindex --fresh                          # rebuild SQLite from JSON sidecars
evidence reclassify                               # re-run categories after changing labels/threshold
evidence rescope --purge                          # re-check scope; delete out-of-scope videos
evidence serve                                    # image grid at http://127.0.0.1:8000  (API docs at /docs)
```

The first classified run downloads the SigLIP model (about 3.5 GB). Use `--classifier none` to skip classification.

## Output

```
library/
  evidence.db                        SQLite index (derived; rebuildable)
  runs/<run_id>.json                 config snapshot, candidates, per-video results
  videos/<youtube_id>/
    video.json                       normalized VideoRecord
    raw/youtube_api.json             verbatim Data API videos.list item
    raw/ytdlp_info.json              verbatim yt-dlp info dict
    media/<youtube_id>.mp4           source media (only where permitted)
    thumbnails/youtube_*.jpg         YouTube-provided thumbnails
    frames/original/<frame_id>.png   original-quality frame (PNG; high-quality JPEG past lossless_max_frames)
    frames/web/<frame_id>.webp       ≤1600px derivative
    frames/thumb/<frame_id>.webp     ≤400px grid thumbnail
    frames/meta/<frame_id>.json      normalized FrameRecord
```

The JSON files are the canonical record. The database is an index built from them.

## Metadata model (`src/image_evidence/schema.py`)

Each frame record has three tiers, and the tier is part of the field path:

| tier | what it holds | examples |
|---|---|---|
| `source` | What YouTube reports (Data API / yt-dlp) | `published_at`, title, tags, license, `claimed_recording_date`, `claimed_recording_location` |
| `derived` | Values computed from the frame's pixels | `categories[]` (label, confidence, provenance), raw `category_scores`, sharpness, brightness, dHash |
| `inferred` | Claims about the real world, each with `confidence` and `provenance` | `locations[]` (ranked candidates), `capture_date[]` |

Rules the code enforces:

- **Publication date is not capture date.** `source.published_at` comes from YouTube. `inferred.capture_date` stores publication only as an upper bound (`latest`). A point value appears only when the uploader set `recordingDetails.recordingDate`, and it is labeled as that claim.
- **Unknown coordinates are null. The pipeline never guesses them.** Latitude and longitude come only from the uploader's YouTube geotag. When a video was found through a location query (such as "Kyiv"), the record gets `place_name="Kyiv"` with confidence 0.2 and null coordinates. The `latitude`/`longitude` in the config are used only for the API geo-filter and are never written onto frames.
- **Confidences are coarse priors, not probabilities.** Inferred-location confidences are hand-set per method. Category confidences are relative shares from a softmax across all labels, not calibrated probabilities.
- **The frame → source link is immutable.** `FrameRecord.source` and `.frame` are frozen pydantic models. A SQLite trigger rejects any UPDATE to `video_id`, `timestamp_s`, `frame_number`, `published_at`, etc. Frame IDs are deterministic: `yt_<youtube_id>_f<frame_number:07d>`.
- **Frame numbers are exact.** `frame_number = round(timestamp_s × fps)`. Extracted frames were checked to be pixel-identical to FFmpeg `select=eq(n,N)`.
- **Video-level text categories are kept apart from visual ones.** Title and tag keyword matches go in `video.derived.text_categories`. They are never mixed into frame categories.

## Pipeline stages

| stage | module | notes |
|---|---|---|
| discovery | `discovery.py` | Expands locations × category terms × year windows. `search.list` costs 100 quota units per call (default quota is 10k/day). `evidence discover` prints an estimate. |
| acquisition | `acquisition.py` | `policy`: `none` / `creative_commons` (default: Data API `status.license == creativeCommon`) / `public`. Never uses cookies or login. Never bypasses age gates, DRM, or geo-blocks. Private, live, and age-restricted videos are recorded as `unavailable`. |
| extraction | `frames.py` | Pass 1 runs a downscaled FFmpeg decode and selects `scene > threshold` OR every `interval_s`. Pass 2 decodes the chosen frames at full resolution. OpenCV then drops near-black frames and dHash near-duplicates. Output is capped at `max_frames_per_video`. |
| derivatives | `derivatives.py` | Lossless PNG original, plus WebP web and thumbnail copies. |
| classification | `classify.py` | Zero-shot SigLIP (`so400m-patch14-384`). Each label gets a share from a softmax across all labels plus a hidden "other" label; every label with at least `threshold` (0.15) share is kept, so a frame can have several. Raw sigmoid scores were too prompt-sensitive to threshold. Default labels: architecture, landscape, street, urban, aerial, drone, infrastructure, industrial, ruins, reconstruction, plus utility labels people, wildlife and graphic for filtering out non-evidence frames. Labels and prompts can be changed in config; prompts work best as concrete captions. |
| scope | `scope.py` | Hard gate: Ukraine relevance + publication 2022–2026, checked before any file is written. |
| inference | `inference.py` | Location candidates (geotag, query context, places named in metadata, country) and capture-date bounds and hints, each with provenance. |
| storage | `store/` | `Repository` protocol, implemented for SQLite. `schema_postgres.sql` is the PostGIS target: implement the protocol for Postgres, then run `evidence reindex`. |
| read API + page | `service.py`, `api.py`, `web/index.html` | `EvidenceService` provides search (text/category/year, with facets), frame detail, and related frames (geo proximity → same inferred place → same video). FastAPI endpoints: `/api/frames`, `/api/frames/{id}`, `/api/frames/{id}/related`, `/api/videos`, and `/media/videos/...`. `/` serves a bare-bones page (`web/`: index.html, style.css, app.js, zoom.js): grids grouped by video, filters, a lightbox with metadata, and Apple Photos-style density steps (trackpad pinch, touch pinch, +/− keys, slider). |

The future frontend should use only `service.py`/`api.py`. It never imports ingestion code.

## Known limitations

- yt-dlp no longer exposes YouTube's license field. Without Data API metadata (`ingest-video` with no API key), the license is `unknown` and the `creative_commons` policy won't download. Use `--policy public` only when you have confirmed you may use the video.
- Few uploaders geotag their videos, so most frames will have a `place_name` from query context but no coordinates. Related-by-proximity then falls back to the same place, then the same video. Real geolocation (visual place recognition, OCR of signage, manual annotation) is future work. It fits into `inferred.locations` as another provenance method.
- Category scores are relative, not calibrated. Tune `classification.threshold` and the prompts on your own footage, then run `evidence reclassify` (no re-download or re-extraction).

## Tests

```sh
pytest     # offline: synthetic FFmpeg video, stubbed YouTube calls, SQLite, service
```
