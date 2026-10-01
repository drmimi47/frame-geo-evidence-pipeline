# frame-geo-evidence-pipeline

A research collection of frames from YouTube videos **about Ukraine, published 2022–2026**, chosen for
**places** (landscape, architecture, infrastructure, damage), not people. Each frame is stored with its exact
source link plus location and date clues, and every clue carries a confidence and provenance.

Full rules and design notes are in [`CLAUDE.md`](CLAUDE.md).

## Scope (hard limits)

- **Ukraine only.** `scope.check_scope()` gates every video before anything is written. It checks the uploader
  geotag, Ukrainian places named in the metadata, and Ukrainian-language text; language alone is not enough.
- **Published 2022-01-01..2026-12-31** on YouTube. Footage may be older: capture date is always *inferred*,
  and publication is only its upper bound.
- Rejected videos leave no files and appear only in `library/runs/*.json`.

## Setup

Requires Python ≥ 3.11, `ffmpeg`, and `node` or `deno` (used by yt-dlp).

```sh
brew install ffmpeg uv
uv venv --python 3.12 && uv pip install -e ".[classify,api,ocr,dev]"   # classify = torch + SigLIP (~3.5 GB model)
cp .env.example .env            # set YOUTUBE_API_KEY=...
.venv/bin/evidence doctor
```

## Usage

```sh
evidence discover -c config/example.yaml          # dry run (~100 API quota units per search)
evidence discover -c config/dnipro-kakhovka.yaml --why   # study area: ranked candidates
evidence ingest   -c config/example.yaml          # discover → download → frames → classify → index
evidence ingest-video <url|id>                    # one video, still scope-gated
evidence serve                                    # http://127.0.0.1:8000  (API docs at /docs)
```

Maintenance (no re-download):

| command | does |
|---|---|
| `analyze [--force]` | sorting features + SigLIP embeddings |
| `relocate [--offline]` | frame-level place clues from OCR, chapters, captions (+ English translation) |
| `reclassify` | re-run categories after changing labels or thresholds |
| `rescope [--purge]` | re-check scope; `--purge` deletes videos that no longer pass |
| `refresh-titles` | uploader's English titles |
| `reindex --fresh` | rebuild `evidence.db` from the JSON sidecars |
| `search`, `show`, `related` | query frames from the terminal |

## How it works

1. **Discovery**: the YouTube Data API v3 (`discovery.py`), optionally ranked by a study area (`focus.py`).
2. **Acquisition**: yt-dlp (`acquisition.py`), no cookies or logins. The default policy downloads only
   Creative Commons media.
3. **Frame selection**: FFmpeg previews, then dark and duplicate frames are dropped, then SigLIP keeps up to 100
   frames per video that show places rather than people, interiors, or graphics (`pipeline.py`, `classify.py`).
4. **Location and date clues**: a gazetteer of about 10k places (`places.py`), on-screen text via Apple Vision OCR
   (`ocr.py`), description chapters, and captions within ±45 s (`geo_text.py`).
5. **Sorting**: place, visual similarity, camera angle, damage, colour, light, season cues, published date,
   detail, and "near <study place>" (`sorting.py`, `visual.py`).

## Data model

```
library/
  evidence.db                      SQLite index (rebuildable)
  runs/<run_id>.json               config snapshot, candidates, accepted/rejected
  videos/<youtube_id>/
    video.json                     VideoRecord
    raw/                           verbatim API / yt-dlp / captions
    frames/{original,web,thumb}/   PNG original, WebP derivatives
    frames/meta/<frame_id>.json    FrameRecord (canonical)
    frames/embeddings.npz          SigLIP embeddings
```

Every record has three tiers: **`source`** (what YouTube reports), **`derived`** (computed from pixels), and
**`inferred`** (claims about the world, each with `confidence` < 1 and `provenance`).
- Coordinates come only from an uploader geotag. A place name is never geocoded onto a frame.
- The frame → source link is immutable (frozen models plus a SQLite trigger).

## Web viewer

`evidence serve` runs a minimal read-only site: a frame panel on the left and a numbered image grid on the right.
- **Timeline** shows each video as a filmstrip. **Subtitles** places each spoken word at its time, with place names
  and land words emphasised.
- You can also sort, filter, search text, and search by image (drop or paste an image).
- Pinch or `+`/`−` to zoom. Click a frame to pin it; Esc to unpin.

## Tests

```sh
.venv/bin/pytest -q    # offline: synthetic FFmpeg video, stubbed YouTube calls
```

## Limitations

- yt-dlp doesn't expose the licence, so without an API key the `creative_commons` policy won't download.
- Few uploaders geotag, so most location candidates are place names without coordinates.
- Category scores are relative softmax shares, not calibrated probabilities.
