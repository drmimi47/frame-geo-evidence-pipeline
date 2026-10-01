# image-evidence-pipeline: project guidelines

A research collection of frames from YouTube videos **about Ukraine**, **published 2022–2026**.
Pipeline: `src/image_evidence/`. Read-only site: `src/image_evidence/web/` (served by `evidence serve`).

## Collection scope (hard rules, never relax silently)

1. **Ukraine only.** A video enters the library only if `scope.check_scope()` accepts it:
   Ukraine relevance from the uploader geotag, gazetteer matches in title/tags/description,
   and Ukrainian-language text (noisy-OR, `scope.min_confidence` ≥ 0.5). Language alone is not enough.
   A geotag outside Ukraine rejects the video.
2. **YouTube publication date 2022-01-01..2026-12-31** (`scope.HARD_START/HARD_END`). This applies
   to discovery config (validated at load), `ingest`, `ingest-video`, `reindex`, and `rescope`.
3. **The gate runs before anything is written.** Rejected videos leave no files in `library/videos/`
   and no rows in the index. They appear only as `rejected` in `library/runs/*.json`.
4. **Publication date ≠ capture date.** Footage published in range may show events before 2022
   (archival clips, re-uploads). That is allowed and must never be "fixed" by rejecting the video
   or by labeling frames with the publication year as their capture date. Capture date is
   `inferred.capture_date`: publication is only the upper bound. Pre-2022 hints (year mentions,
   "archive", "до війни", …) are low-confidence candidates with provenance.
5. **Test and demo data must also be in scope.** Don't ingest out-of-scope videos into `library/`,
   even temporarily. For offline tests use the synthetic FFmpeg video and stubbed API items in `tests/`,
   and give stubs Ukrainian metadata. Use a scratch `--library` path for anything else.

If a rule seems wrong for a task, ask the user. Don't work around it with flags or edits.

## Frame selection

The collection is about **places**: landscapes, architecture, scenery, nature, animals, and infrastructure. It is not
about people or interiors. `pipeline._extract` works in these steps:
1. One FFmpeg pass produces small previews (longest side 384px, in the video's own aspect ratio) of every candidate frame (scene changes, plus one frame every `interval_s`).
2. Dark frames, mostly-black frames (credits, title cards), and near-duplicates are dropped.
3. Up to `candidate_pool` previews are classified with SigLIP.
4. Frames with `subject_score` = share(`prefer`) − share(`avoid`) ≥ `min_subject` are kept, up to
   `max_frames_per_video` (100), spread over the timeline (`classify.choose`). `avoid` defaults to people, interior,
   and graphic.
5. Only the kept frames are decoded at full resolution.
When tuning, check a contact sheet in a scratch library. Don't guess.

## Sorting (forensic review)

`sorting.py` orders the grid. The sorts are Place, Similar view, Camera angle, Damage, Colour, Light, Season cues,
Published, and Detail. They use `derived.features` (`visual.py`: pixel statistics plus SigLIP zero-shot camera angle and
damage) and SigLIP image embeddings. The embeddings are stored in `frames/embeddings.npz` (canonical) and the
`frame_embeddings` table. Ingest computes them. For older frames run `evidence analyze`.
- Every sort returns a `sort_group` (consecutive runs are laid out as one block, with no labels in the grid) and a
  `sort_note` shown in the panel.
- Notes describe cues ("season cues", "inferred place"). They never state a date or a filming location as fact.

## Frame-level location clues (`geo_text.py`, `places.py`, `ocr.py`)

Each frame's `inferred.locations` holds the video-level candidates plus clues tied to its timestamp:
- On-screen text: Apple Vision OCR, stored in `derived.ocr`. The channel's own logo words are ignored. Repeated
  lower-thirds such as "Запорізька обл." or "вересень 2023" are kept on purpose.
- The description chapter the frame falls in.
- Speech from YouTube captions within ±45 s, saved in `raw/captions.json`.
- On-screen years and month-year labels become frame-level capture-date candidates.

Place matching:
- `places.py` uses the curated `scope.GAZETTEER` plus about 10k GeoNames settlements (`data/ua_places.tsv.gz`, CC BY 4.0,
  rebuilt by `scripts/build_gazetteer.py`).
- It matches real Ukrainian and Russian case forms of each name.
- Lower-case and speech text only match cities of 50k or more, or places the video's metadata names.
- Small places must be written as proper nouns.
- When a false match shows up, add the word to `_COMMON`. Don't loosen the rules.

Geotags and running it:
- An uploader geotag more than 60 km from every place the video names is down-weighted to 0.3, because it is often the newsroom's
  city.
- Ingest runs this step automatically. For stored videos, run `evidence relocate`.
- `rescope` recomputes from stored OCR and captions without refetching.

Decided with the user for future work (not built yet): coordinates may also come from sources that have their own
coordinates, such as a matched geotagged reference photo or an OSM feature, always with provenance. They must never
come from a place name alone.

## Metadata rules

- Three tiers: `source` (YouTube says), `derived` (computed from pixels), `inferred` (claims about
  the world; always `confidence` + `provenance`). Never present inferred values as fact in the UI or API.
- Coordinates only from a source that supplies them (uploader geotag). Place names found in text,
  query locations, and the country-level "Ukraine" candidate have `latitude/longitude = null`.
  Never geocode a place name onto a frame.
- Inferred confidence is never 1.0 (scope confidence is capped at 0.95).
- The frame → source link (`FrameRecord.source`, `.frame`) is immutable (frozen models + SQLite trigger).
- JSON sidecars under `library/videos/` are canonical. `evidence.db` is a rebuildable index.

## Commands

```sh
.venv/bin/evidence doctor
.venv/bin/evidence discover -c config/example.yaml     # dry run; ~100 quota units per search
.venv/bin/evidence discover -c config/forensic-aerial.yaml   # drone/aerial footage of named places
.venv/bin/evidence ingest   -c config/example.yaml
.venv/bin/evidence ingest-video <url|id>                # still gated by scope
.venv/bin/evidence rescope [--purge]                    # re-check stored videos; purge deletes rejects
.venv/bin/evidence reclassify                           # re-run categories only
.venv/bin/evidence analyze [--force]                    # sorting features + embeddings for stored frames
.venv/bin/evidence relocate [--offline]                 # frame-level place clues: OCR, chapters, captions
.venv/bin/evidence reindex --fresh
.venv/bin/evidence refresh-titles                      # uploader title translations (1 unit / 50 videos)
.venv/bin/evidence serve                                # http://127.0.0.1:8000
.venv/bin/pytest -q
```

The YouTube API key goes in `./.env` as `YOUTUBE_API_KEY=...` (gitignored). Never print it or commit it.

## Website

Keep it minimal (loose reference: mos.nyc). No header and no dashboards. The layout is:
- a fixed left panel that shows the hovered or tapped frame: video, channel and year, a timeline tally
  (one tick per extracted frame, proportional to the video's duration, with a playhead you can scrub),
  frame info, and inferred metadata with notes;
- a numbered grid on the right, grouped by video. It holds only images and frame numbers: no video titles or other text;
- Sort, Clear all, filters and search fixed at the bottom right, in that order left to right, all at 14px (no density slider);
- search by image: "By image" (or drop or paste an image) orders the grid by SigLIP similarity to it. The upload is
  only kept in server memory (`/api/query-image`), never written to the library;
- a live count at the bottom left (videos analysed, images; "x of y" when filtered), polling `/api/stats`.
Clicking the panel title switches all titles between the original and the title YouTube shows an English-language
viewer. That is the uploader's own English title (`source.title_localizations`, from the API `localizations` part),
or the original when they set none. No machine translation. `evidence refresh-titles` backfills stored videos.
The grid loads every page of `/api/frames` (500 per request); never assume one page holds everything.
Use the default cursor on tiles. Clicking a tile pins it: the other tiles dim and the panel stays on it until it is
clicked again, empty space is clicked, or Esc is pressed. Bottom controls are sized to their text so the gaps are equal.
Plain HTML/CSS/ES modules in `web/`, no build step. Grid density is `--cols`, set by `zoom.js`:
during a pinch the grid scales continuously (CSS transform), then on release it snaps to the nearest column count with a
FLIP glide. Inputs are ctrl+wheel, Safari gesture events, touch, and +/- keys.

Search (`search.py`) parses free text into AND-ed terms.
- Visual words and synonyms ("person", "buildings") match frame categories, not video text.
- Other words match video text and place names at word starts, including gazetteer spellings and Latin-to-Cyrillic
  transliteration.
- Multi-word queries also match the exact phrase in video text.
When adding a category label, add its common synonyms to `VISUAL_SYNONYMS`.
