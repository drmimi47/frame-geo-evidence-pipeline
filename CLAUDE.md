# frame-geo-evidence-pipeline: project guidelines

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
- "Near <place>" sorts (an optgroup at the end of Sort): one per place of the study areas in `config/*.yaml`
  (`discovery.focus`, or the `-c` config's; `/api/study-places`). Frames whose inferred locations put them at the
  place (≤ 3 km) come first, then near it (≤ the area's `radius_km`), then the rest. Distances use the uploader
  geotag, else the gazetteer position of the named place, never stored; oblasts and regions without a position
  (Velykyi Luh) are never near anything. The bottom-left count says how many images are near it, or that none are.
- Notes describe cues ("season cues", "inferred place"). They never state a date or a filming location as fact.

## Frame-level location clues (`geo_text.py`, `places.py`, `ocr.py`)

Each frame's `inferred.locations` holds the video-level candidates plus clues tied to its timestamp:
- On-screen text: Apple Vision OCR, stored in `derived.ocr`. The channel's own logo words are ignored. Repeated
  lower-thirds such as "Запорізька обл." or "вересень 2023" are kept on purpose.
- The description chapter the frame falls in.
- Speech from YouTube captions within ±45 s, saved in `raw/captions.json`: the track of what is spoken (manual,
  else auto-captions), plus the uploader's English subtitles when there are any. The text comes through yt-dlp: the
  Data API lists caption tracks but only lets a video's owner download them, and YouTube's auto-translation is
  rate-limited (HTTP 429), so it isn't used.
- English for reading: the uploader's English subtitles, else a local machine translation (`translate.py`, opus-mt,
  sentence by sentence) in `derived/captions_en.json`, always labelled as such. Place names are matched in the
  original only, never in a translation (it mangles them: "Нікополь" → "Nicopolis").
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

## Study areas (`discovery.focus`, `focus.py`)

A config can name a study area: gazetteer places plus a radius (`config/dnipro-kakhovka.yaml`: the Dnipro from
Zaporizhzhia to the former Kakhovka reservoir). Discovery then also searches for videos geotagged inside it, scores every
candidate from its API metadata by how well it can be placed there, and ingests only the best `max_ingest` new ones.
- Points: uploader geotag inside the area; the area's settlements named in title, location description,
  description or tags (small places count more than big cities); coordinates or map links; chapters naming places;
  uploader captions; topic words. Lost points: the title names a place elsewhere, or more places elsewhere than inside.
- A video is taken only if it is in the area and on topic: its text names a place there or uses a topic word. A geotag
  alone is where the uploader is (pedicure clips, newsrooms), not what the video shows.
- A name shared by places inside and outside the area (Novopavlivka, Lviv) counts only next to an unshared one.
- The score is search context in `library/runs/*.json`, never evidence: nothing from it reaches a frame, and the
  gazetteer coordinates are only used for distances. The scope gate still runs on every video.
- When a place word matches falsely, add it to `places._COMMON`, as for frame clues.

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
.venv/bin/evidence discover -c config/dnipro-kakhovka.yaml --why   # study area: ranked candidates (* = would be ingested)
.venv/bin/evidence ingest   -c config/example.yaml
.venv/bin/evidence ingest-video <url|id>                # still gated by scope
.venv/bin/evidence rescope [--purge]                    # re-check stored videos; purge deletes rejects
.venv/bin/evidence reclassify                           # re-run categories only
.venv/bin/evidence analyze [--force]                    # sorting features + embeddings for stored frames
.venv/bin/evidence relocate [--offline]                 # frame-level place clues: OCR, chapters, captions (+ English translation)
.venv/bin/evidence relocate --refetch-captions          # fetch captions again; --retranslate, --no-translate
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
- Light/Dark, Timeline, Subtitles, Sort & filter, Search and (timeline and subtitles only) a zoom slider fixed at
  the bottom right, in that order left to right, all at 14px, on one line with equal gaps (no grid density slider).
  Sort & filter opens a small panel above it with Sort, Category, Year and Clear all (which also clears the search and
  the image); the button counts what is set ("Sort & filter · 2"). Click outside or Esc closes it. The
  slider is the same stretch as a pinch (`zoom.js` `stretchBy`), on a log scale over `tlRange()`, and follows pinches and +/-.
  Light/Dark follows the system until clicked, then is remembered per browser (`localStorage.theme`, `data-theme` on `<html>`);
- Timeline view (toggle, remembered per browser): one row per video like a clip in an editing timeline, with no text, numbers
  or ruler: a filmstrip where each extracted frame starts at a black vertical bar at its timestamp and repeats until the
  next bar. Frames outside the current search or filters leave an empty stretch with no bar. Re-layouts reuse and move
  the existing segment elements (`segEls`) at whole-pixel edges, never rebuild them, or zooming flashes white. All videos
  share one time scale; pinch or +/- stretches time only (`zoom.js` `stretch`, re-laid out live, no transform, no snap).
  The stretch is continuous, separate from grid density, and reaches until the shortest video spans about two widths,
  so short clips with dense frames spread out too. Lines run the full page width so the strip reflows smoothly, and a
  video's height eases (`tlTick`) when it gains or loses a line, with the video under the pointer held in place.
  Strips meet edge to edge with no blur, fade or splice effects. The strip is thin: each image keeps its width at the
  unsquashed height (`--ih`, `--ar`) but is squashed flat to the line height; a line grown for an opened frame is not squashed. Clicking a frame (pin) opens a slot
  in the strip for its image, whole and sharp (`web_url`, a `.seg.image` element), on the line its marker is on: the image
  never moves to another line, and the timeline only grows forward (never backwards, never a line added above). The image always
  shares a border with its marker. A frame in the left half of its line opens to the right: the slot starts at the
  marker and the strip after it slides on (onto the next line if it must). One in the right half (or whose image doesn't
  fit to the right) opens to the left: the marker stays put, the slot ends at it, and the strip before it on that line
  squeezes into the room left of the image, still in order (words show as dashes until zoomed in). Two images in one
  video never move at once (`spreadTo`): clicking another frame closes the open one at the usual speed, then opens the
  new one, and while an image is closing its video's other frames can't be clicked open (`closingIn`), so a closing slot
  never pushes a new frame onto another line. While a frame is pinned, the marker under the pointer still thickens
  (and darkens in Subtitles), showing it can be opened. An opened image's side (`spread.side`) is chosen when it opens and again
  when a zoom stops, by the same rule (where its marker ended up), never during a zoom; a change of side closes the old
  slot as the new one opens while the image glides in. Where a side has less room than the image needs, it is shown smaller.
  While zooming (pinch, slider or +/-) opened images stay exactly where they are on screen (`holdImages`: fixed, letting
  the pointer through so the zoom keeps the frame under it in place) while the timeline zooms under them and their slots
  move with their markers; when the zoom stops (pinch end, slider let go, keys idle) each glides into its slot, on whichever side of its marker now fits
  (`releaseImages`, `SETTLE_MS`, ease-out: it starts moving at once and slows into place,
  no wind-up, bounce or pulse; it heads for its final size, never its slot's in-between size, with its edge going
  straight to its marker). Lines ease to new heights (`easing`).
  Nothing is drawn under the image: words stop before it (`r.holes`), so what was said nearest it stays in view. Only its line grows taller; the
  rest of the strip stays at track height, centred. It closes the same way on unpin. Nothing runs off screen: a video longer than the page
  width wraps onto more lines below, like text. Hover, pin and the panel work as in the grid;
- Subtitles (a timeline mode; the toggle switches the timeline between images and subtitles): the same lines, time
  scale, markers and spread, with the words instead of the images. Every word sits where it is spoken (caption word
  times, `raw/captions.json` `word_times`; `/api/videos/{id}/subtitles`), the English on a grey row below, spread over
  each phrase. A word without room is a dash as long as its room, so zoomed out a video reads as a line of speech with
  its pauses and pinching spreads the words until they read. Three levels, so the eye lands on what can place the footage:
  place names bold (heavy dash); words about the land black (medium dash): water, terrain, roads, directions, distances
  and a number with its unit (`spatial.py`, about 3% of the words); the rest faint. The English row (italic) gets the
  same three levels from `spatial.py`'s English list, for reading only: a place is marked there only when the original
  or the metadata names it (`geo_text.EN_NAMES` holds exonyms and the translation's manglings, e.g. Dnieper, Cahokia),
  and nothing from the English ever becomes a location clue.
  When a common word lights up too often, remove it from `spatial.py` rather than loosening the endings. Search terms marked.
  Priority (`WORD_PRIORITY`, on by default): place names, land words and search matches show as text first, claiming
  room over the words said just after them (which step aside); a priority word right after another moves along to
  follow it (up to `NUDGE_PX`) so phrases read whole, and one at a line's end ends there or starts the next line (else it
  blinks to a dash at the zooms that put it at the edge). Claims are worked out over every line of the video, so a line
  looks the same whichever lines are drawn with it (scrolling never changes it). Other words show only once they fit
  before the next word or claim.
  `localStorage.wordPriority = "off"` in the browser console brings back the plain rule for comparison.
  Drawn on a canvas inside each line within a screen's height of view (pooled; reading width wraps onto 1000+ lines),
  so the words scroll with their line: never on a screen-fixed canvas redrawn on scroll, which trails the page. Its stretch is
  kept apart from the images' (`subtitleZoom`) and reaches reading width (`READ_PPS`). An opened frame shows its image
  once. No note above the lines; the panel names each video's source (auto-captions,
  uploader's English, or machine translation);
- search by image: drop or paste an image anywhere (no button or file picker) to order the grid by SigLIP similarity
  to it, shown as the sort "Like your image". The upload is only kept in server memory (`/api/query-image`), never
  written to the library;
- a live count at the bottom left (videos analysed, images; "x of y" when filtered), polling `/api/stats`.
The panel shows the original title in plain text (no bullet). Everything under it is secondary, in faint italics: the
uploader's own English title (`source.title_localizations`, from the API `localizations` part) when they set one,
then the channel and year.
No machine translation and no click-to-switch. `evidence refresh-titles` backfills stored videos.
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
