# frame-geo-evidence-pipeline: project guidelines

A research collection of frames from YouTube videos **about Ukraine**, **published 2022–2026**.
Pipeline: `src/image_evidence/`. Site: `src/image_evidence/web/` (served by `evidence serve`), read-only except
the Video panel, which adds videos through `/api/jobs` (`jobs.py`), the Satellite panel, which adds satellite passes and
films through `/api/satellite/jobs` and `/api/seam/films` (`satellite/`), and the Evidence panel (rename a folder, show it
in the file browser: `/api/folders`).

**What to work on next: `NEXT.md`** (the running checklist, started 2 November 2026). Read it at the start of a
session; keep it current: only what is left to do, each item deleted once done (its record goes where the work is).

## The end result (decided with the user, 25 October 2026)

The project ends in **one developed film, at most 10 minutes long**, titled **Powerlines** (one word, no subtitle;
the user): a high-quality video exploration in the manner
of computational design visualisation, showing the project's intricate parts (the ZNPP's lines, their record through
the war, the Great Meadow, the crossing, the Hum). Narrative and storytelling, graphics, data and cinematography carry
equal weight. Everything else serves it: the collection, the satellite passes, the corridor and zoom-out films, the
Scene Viewer and the site are its research and its sequences, not the deliverable.
- The 10 minutes is a ceiling, not a target. Every sequence has to earn its time; a draft that runs long is cut, not
  sped up. That is for the final film: while prototyping, the storyboard may run past 7 or 10 minutes, and its
  length isn't flagged until the story settles (the user, 4 November 2026).
- Story first: a sequence is planned by what it tells and where it sits in the whole (chapters, turns, held moments,
  silence), then by how it looks. The working outline is in `docs/znpp-heart-plan.txt` (FILM).
- Cinematography is designed, not left to defaults: camera moves, holds, pacing, sound and type are decided on
  purpose and recorded with the user's decisions.
- The evidence rules still hold on screen: every drawn fact has a source in the film's `film.json`, inferred things
  are never shown as observed, imagery is never generated, and what is synthesized or drawn (the Hum, the lines, the
  zone) is said to be. Safety (amended with the user, NEXT.md I5): where lines were damaged or repaired, or
  where crews were sent, is shown only as a general region (a stretch of line or an area at least about 3 km across,
  never finer than the source), never a tower, a pin, coordinates or a crew's position; never the Dniprovska
  substation's place or the trench site (no coordinates, no pin, dated imagery from 2024 or earlier only).
- Quality: final renders at 60 fps (tests at 30), 1920×1080 or larger, sound mixed with the picture. The sequences
  rendered so far (the zoom-out with the record, the great-meadow corridor film) are drafts toward it.
- In progress: the crossing in 3D (planned with the user, 25 October 2026): from the zone's close-up the map tilts
  into a Blender flight north between Dniprovska and Ferosplavna-1 over the water, the lines switching with the record,
  the water draining to show the tower foundations. **Read `docs/crossing-3d-plan.txt` before working on it** (its
  STATUS says where it stands; Blender 5.2 is scripted headless via `blender` on PATH, MCP for Blender optional).
  The towers are modelled by type (`scene3d/towers.py`, from photographs of these towers and published heights; the
  crossings' schemes in the config, checked against OSM): positions always OSM's, shapes representative and said so.
  Crossarms flat on top as photographed; fittings (disc strings, yokes, bundle clamps, spacers, dampers) of the kinds
  photographed, sizes typical; wires at real size, at least 0.7 px however far (geometry nodes, per point).
  The flow: dashes run along connected lines toward where the power goes, by the config's dated, sourced periods
  (`crossing3d.flow`: toward the plant since September 2022), fullest over the reservoir as surveyed, the dashes fainter
  on land and the wire unchanged (`wire_cross`, `FLOW_LAND`), paced to the user's TouchDesigner reference; a drawing
  convention, said so. The whole render is `animatic/ZNPP-last-two-lines-3D.mp4` (the variant's `title`; `3D-film` until 2 November 2026).
  The drained bed (pass 3, `scene3d/bed.py`, config `crossing3d.bed`): no elevation model of it exists, so its
  heights are inferred by the waterline method (where the water was on each clear pass after the breach, at the level
  reported then: gauges, then SWOT, Baltic +0.4 m to EGM2008), held to ICESat-2's measured ground and the 1941 sheet's
  spot heights, never out of the band the shorelines give; checked against ICESat-2 in `bed.json`. The water is a
  modelled surface at the reported level (capped once settled at the lowest level the bed was mapped at), its
  colour the passes' own, its ripples and reflections drawn: said in scene.json. Once settled the water is drawn as
  each pass saw it (the river a sheet at the reported level, the bed carved under it, inferred; pools and channels from
  the pass's own water mask, `bed.channels`). The caissons' discs are left out of the shorelines (S2 reads the concrete
  as dry ground) and take the bed round them; later passes bound the bed. The land's box (40x36 km) lets the lines run
  on as OSM has them (Dniprovska north into the haze, cut by the box and said so). The dam's day is pinned at 35 s.
  A second version flies south toward the plant, with the power (S6, the user, 4 November 2026; both kept):
  `south_record`, `ZNPP-last-two-lines-3D-south`, its own camera (`track`, camera.frames_track: a fade from white over
  the north bank, down the same axis, a curve off toward the units and a slow rise, its heading always the way it
  travels), the lines' sides swapped (states.options), and its `extras`: the plant, the thermal plant and Enerhodar
  modelled (scene3d/plant.py: OSM footprints, the published heights, else storeys or a representative height, said
  so), the land on south of the box, and the plant's other lines (`others`: the other three 750 kV and four 330 kV
  lines south into the distance, the units' feeds and the NPP-TPP links, at OSM's towers, cut at the box; states by
  the date shown; the feeds and links lit with the line feeding them, inferred and said so; no context grid).
  Scene files (the user, 2 November 2026): a whole render saves its scene as `animatic/<title>.blend` (`ZNPP-last-two-lines-3D.blend`,
  the picture only: the date, names, fade and Hum are added after Blender); `--pass blend` saves it without rendering.
  Only the configured variants' .blend files are kept and never a .blend1: prototypes come and go.
- The lines unrolled (NEXT.md I5 idea 1, the user, 4 November 2026: time "left to right, not unrolling down like a
  scroll", "only the most critical stuff"; `satellite/unrolled.py`, `unrolled_web/`, config `networks.znpp.unrolled`):
  Ferosplavna-1 and Dniprovska grow on a map, then unroll like a tape (each span turned upright from the switchyard
  out, its length kept) into upright bars: the switchyard at the bottom, the first 20 km up it (both lines go on, said
  so), the river across it (the shores of 5 June 2023, the channel after: the front, occupied below, Ukrainian-held
  above). The bars move right with the date and the frame pans with them, each line's record left behind as a ribbon
  (lit while connected, dark while cut, dotted where unreported); complete losses a tick through both, those lasting
  days a pale band; the last year at six times the scale (said once); the seven repair truces as hatched, dashed
  regions as tall as their sources say (a side, a bank, the crossing, or the whole bar where unpublished; `truce`
  refuses under 3 km), named only while held ("TRUCE 3 · NOVEMBER 2025 · THE SOUTH BANK"); a few captions at held
  moments, the count top right, one legend; then the whole record fitted to the frame. D3 7.9.0 vendored; each frame
  drawn by `draw(t)` and taken from the installed Chrome (Playwright, the `charts` extra), FFmpeg to
  `unrolled/ZNPP-last-two-lines-unrolled.mp4` with `unrolled.json` (every source) and the page as drawn. No sound yet.
- The storyboard (`storyboard/`, decided with the user, 2 November 2026): the narrative isn't locked, so the film is
  planned as a pool of shots (`config/storyboard.yaml`: each with a status, good, draft, still, missing, idea or new,
  what it tells, what it needs, where it is in `reports/`, tags; a source film or figure with `in`/`out`, else a card's
  `duration`) and cuts of it in order (`config/storyboard-cuts.yaml`, rewritten by `sync`). `evidence storyboard build`
  lays a cut out in Blender's Video Sequence Editor (`libraries/conductive-seam/storyboard/<cut>.blend`): one meta
  strip per shot named by its id and coloured by status (the films as 720p previews at 30 fps in `storyboard/media/`,
  figures as they are, cards for the rest, a label top right), the cut up to the END marker, the other shots parked
  after it (PARKED). The user rearranges by hand (drag, trim, park past END, mute, Shift-D to reuse, add a text strip
  for a new idea) and saves; `evidence storyboard sync` reads it back (order by where each starts, trims, new strips as
  shots of their own) and says what changed. A build reads back a saved rearrangement first and refuses if the cut
  file changed too (`--discard-edits` to overwrite); it never deletes a shot from the pool (a parked shot deleted in Blender is only hidden: the cut's `hidden`). Known good (the user):
  the 3D film and the zoom-out to about a minute in (to the zone, where the 3D takes over). Target about 7 minutes
  for the final; the prototype cut holds everything made so far (the user, 4 November 2026) and may run longer.
  Storyboard shots are planning, not evidence: the evidence rules apply when a shot is made.

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

6. **Evidence folders: one scope each** (decided with the user). Every folder is a library of its own. The main
   `library/` ("Ukraine collection") is always Ukraine 2022–2026 (`scope.UKRAINE`). Project folders are
   `libraries/folder-<n>/` (gitignored; named "Evidence folder <n>" until renamed, the name in `folder.json`). A folder's
   scope is fixed by the job that made it (`scope.json`: `scope.Scope`, name, whole-year range, spellings, optional
   bounding box and language, `made_by`; read by `scope.library_scope()`); a later job may save into it only for the
   same place and years within it (`jobs.resolve_folder`, else 400). Every video still passes the gate,
   against its own library's scope; `ScopeCheck.scope_name` records which. Never put another scope's video in
   `library/`, and never widen the main library's scope. Elsewhere the Ukrainian place gazetteer isn't used for
   location clues (it only finds false matches); the country-level candidate is the scope's name.
   "The Conductive Seam" (`libraries/conductive-seam/`, `jobs.ensure_seam_folder`; `folder.json` `order: 0` keeps it
   right below the main library) is Ukraine 2022–2026 for its videos and also holds satellite imagery (below).

If a rule seems wrong for a task, ask the user. Don't work around it with flags or edits.

## Satellite (The Conductive Seam, `satellite/`)

Satellite imagery along the power lines of the Zaporizhzhia power plants across the former Kakhovka reservoir, for a
film in the manner of *Best of Luck With the Wall* (decided with the user: open data only for now, a top-down
travelling shot). Areas are in `config/conductive-seam.yaml`; the test area is the 330 kV Л-243/Л-244 crossing from
the Zaporizhzhia thermal plant (Enerhodar) to the Nikopol bank (its corridor, chips and films were removed from the
folder on 19 October 2026 at the user's request: test images out of the gallery; the config area stays for scratch use). `great-meadow` (110 km, 330 kV all the way) follows that
line on along the north bank, across the river from the nuclear plant, through the Ferosplavna and Nikopolska
substations, then Л-211 back east to the Dnipro dam (Дніпро І ГЕС): the user's site is the Great Meadow and the places
round it, so the route stays there (the 750 kV line north to Dniprovska and the Enerhodar–Zaporizhzhia lines on the left
bank were looked at and not taken).
- Sources: Sentinel-2 L2A (10 m) and Landsat Collection 2 L2 (30 m) from Microsoft Planetary Computer (no key;
  `providers.py`): STAC search, then crops by the data API in lon/lat at an exact pixel size (`.npy`: bands as stored
  plus a validity mask; the cloud mask read nearest-neighbour). Reprocessed Sentinel-2 items: only the newest is kept.
- A pass's date is its acquisition time, a source fact: **any year is allowed** for satellite imagery (decided with
  the user: many years along the same path). The 2022–2026 rule is about YouTube publication and still applies to the
  folder's videos. The area gate (`fetch.check_area`): a corridor must lie inside its folder's place (Ukraine's box),
  checked before anything is written.
- A corridor is fixed once (`georef.json`, like `scope.json`): its box, its lines and one grid (linear in lon/lat, metres
  by `KX/KZ` as `scripts/scene/terrain.py`). Every pass, of any date or sensor, is stitched onto that same grid and
  laid on the corridor's reference pass (phase correlation + ECC of NIR detail on clear land, shorelines eroded away;
  only small, clear shifts applied, always recorded). Another area is a new corridor id, never an edit.
- A long corridor is fetched as tiles (`stitch.TILE`, 2048 px) and only those within `strip_m` of the line
  (`stitch.need_mask`); each tile is laid on the reference pass on its own (its shift in `pass.json` `files.tiles`).
  A pass may cover only the line's first part (`--until-km`, `derived.until_m`), e.g. a before pass just where a
  dissolve needs it; the exposed bed is then reported only where the earlier pass covers enough of the clear land.
  Lines joined through a substation (`join_m`) record each join (`georef.json` `line.joins`).
- The lines are OpenStreetMap `power=line` ways (Overpass, several servers with backoff; the reply saved verbatim):
  coordinates from a source that has its own, with provenance. Never detected from pixels (at 10–30 m wires don't show
  and a pylon is a few pixels). Leave ≥ 3.5 km of box round the line so a turned 6 km frame stays on imagery.
- Records (`satellite/schema.py`): `SatellitePass` (source: items, platform, time, cloud; derived: alignment, water,
  cloud), `SatelliteChip` (frozen link to its pass and station). Chips are the folder's images: the whole corridor,
  then a square every `chip_spacing_m` along the line. Water: NIR and SWIR reflectance under 3%; exposed bed: water in
  the last pass before 6 June 2023, not now. Display: one tone curve for every pass (`stitch.tone`, a soft shoulder so
  the drained bed's sand keeps detail).
- In the site, chips join the grid as one group per pass ahead of the videos (`service._sat_items`); text and year
  filter them; categories and image sorts don't (they aren't classified: no false labels); the Frame Sequence,
  Transcript and Route Map skip them. The panel shows the pass, place (the product's georeference), line, water,
  exposed bed, cloud, alignment and STAC links; its tally is distance along the line.
- The film's frames join the gallery too (decided with the user: "each frame of the video" into the Frame Gallery), as
  the first group of the folder (`film_frames.py`; `SatelliteIndex.films`: each corridor's newest film with frames).
  Not all 7,800: as for a video's frames, one is kept once less than half its ground is in the last kept frame
  (a zoom counts), plus the held moments by name (the plant's lines drawn, the pan's end, before and after a dissolve,
  the inset at full strength, the last hold); none in a fade, mid-dissolve or with the inset fading in. They are the
  film's frames as shown (red line, labels, captions included), WebP web and thumb in `films/<id>/frames/`, with
  `frames.json`: shot, passes and weights, camera (a viewing path), what is drawn, why kept, sha256 of the pixels.
  The panel (`app.js` `showFilmFrame`): the film's time on the tally, what is shown, along, camera, drawn, the note at
  that moment with its sources, and "Play the film from here" (`seam.js` `seamStart`).
- The film (`film.py`): hold, track along the camera path (smoothed position and heading, eased), dissolves between
  passes at held stops, hold. Pixels are only resampled (bicubic) or, in a dissolve, mixed; **never generated, filled
  or sharpened**; no data is black. `film.json` records every segment (observed or dissolve, passes and weights,
  overlays), the camera each second and the sources. Captions only on holds and dissolves; credits on the last hold.
  An area's `film:` sets its own options: `dissolve_at_km` (where the dissolves stop), `trace`, and a `profile` of
  speed and frame width by km along the line (eased between; turns are slowed to `max_turn_dps`, so a U-turn at a
  substation reads as a turn, not a spin). A dissolve beyond what a partial pass covers is refused, never filled.
  The line is drawn red (`trace_rgb`, decided with the user, so it can be followed). An area's `opening` (`opening.py`,
  decided with the user) starts the film on a plant instead of a hold: a fade from black with the plant in the middle,
  its lines drawn out from it in red and labelled, then a pan and zoom to the line's start (the thermal plant's lines
  drawn on the way), the other lines and labels fading over the track's first seconds. Lines are OpenStreetMap ways
  from `raw/osm_opening.json` (plants, switchyards and lines round them, saved verbatim, fetched once); each starts at
  the end nearest its origin. Names: the ways' own tags, else the config's label with its source (`names`). For
  great-meadow: the Zaporizhzhia NPP's four 750 kV lines (Dniprovska, Zaporizka, Pivdennodonbaska, Kakhovska; unnamed
  ways named by Bellona's map of the plant's lines and where they end) and the six 330 kV circuits from the thermal
  plant's switchyard (Л-243/Л-244 Ferosplavna 1 and 2, Л-242 Zaporizka, Л-246 Molochanska, and way 187125189 carrying
  Л-247 Melitopolska and Л-241 Kakhovska to where they part), plus the units' links and the NPP–TPP 330 kV link. Quote a
  YAML label that has a comma (a flow mapping splits at it). An area's `insets` lay a supplied
  image on the passes (Forensic Architecture's way: smaller than the frame, named in the caption; just the image, no
  frame or marks, decided with the user): the file in
  the corridor's `insets/` folder as given (sha256 in `film.json`), only cropped, scaled and placed; its `pins` tie image
  pixels to OpenStreetMap towers in the corridor's saved Overpass reply, fitted north up by least squares (each pin's
  residual recorded; more than 15 m is refused, never stretched to fit). The camera zooms in on the way to it
  (`zoom_in_m`, keeping its path and heading), holds while it fades in on the later pass, and zooms out as it fades.
  The great-meadow inset (`crossing-pylons.png`, the user's screenshot of Esri World Imagery) shows the 330 kV and
  750 kV crossing pylons at km 5.2. Its date and sensor come from Esri's own metadata at that spot (saved beside it:
  WorldView-2, 23 August 2024, Vantor), checked by matching the screenshot to Esri's imagery of the same extent
  (correlation 0.95, under 1 m apart: the pins agree with Esri's georeference). The user's coordinates for it
  (47°45'05"N 35°10'23"E) are 50 km off and weren't used.
  The last hold fades to black (`fade_out_s`, credits too; great-meadow: a 9 s hold, the last 3.5 s fading).
  Notes (`notes.py`, decided with the user): short lines under the film in the view, never burned into it, each with
  its sources (what the ZNPP is, its ten lines, the two circuits of Ferosplavna, the seizure, the outages, the dam, the
  Great Meadow, why the line matters). Placed by shot (`{shot, s, n}`) or by km along the line into `film.json`
  `notes`; `evidence satellite notes --area great-meadow` places them again without rendering. Every fact was checked
  against the sources linked (19 October 2026; the IAEA's count of complete losses of off-site power was 26 by August
  2026); add a source for any new note, and say "context from sources", never that the imagery shows it.
  When tuning, check the film's `contact.webp`.
- The zoom-out (`network.py`, `zoomout.py`; decided with the user, 21 October 2026: the site is all of the ZNPP's lines,
  not one; the push in to the surviving lines comes later). A network (`networks:` in the config, saved in
  `satellite/networks/<id>/`, apart from the corridors): every line leaving the plant's 750 kV switchyard and the
  thermal plant's 330 kV switchyard, traced through OpenStreetMap (one Overpass reply, saved verbatim) way to way to
  the substation where it ends; the config names that substation (`to`) and a trace ending anywhere else is refused,
  never drawn. Names by destination (as the IAEA and the user's reference image). Checked: Kakhovska 750 is 186 km
  officially, 185.2 km traced; the step-shaped stretches (Kakhovska 750, Л-241) are real: towers mapped at every corner.
  The film (decided with the user, 22 October 2026): north up. It opens close on the six units (2.2 km wide, centred
  on them; to be sharper with better imagery), outlined one by one and numbered (OSM `power=generator` ways, `units:`);
  then out to both switchyards while each unit's own 750 kV line (`feeds:`, OSM ways) is drawn into the plant's 750 kV
  switchyard (south-west) and the two 330 kV `links:` into the thermal plant's 330 kV switchyard (north-east), each
  switchyard outlined as they arrive, in white (the plant's inside: power made in the units, routed into the yards).
  Only then do the blue lines leave, from the switchyards. All lines leave together at one speed that builds, so
  length is when a line lands; the camera makes one eased move (log scale, never shrinking), its centre easing onto
  the plant, and the lines are held back wherever the frame hasn't room for them. The camera eases into
  `max_view_km` (172 km, decided with the user: the Dnipro and the Great Meadow framed) and stays; the lines grow on
  off the frame. A line's name rides its tip until the tip nears the frame's edge (`label_zone`), then stays at that
  point of the line while the tip goes on (decided with the user: no names off screen or in odd spots). 60 fps; the
  growth is smoothed looking back only (never ahead of the frame, no jumps), and labels and marks move at sub-pixel
  positions (`_Overlay`). The lines are two yellows (`line_rgb` by kV, decided with the user: the blues read as rivers;
  750 kV the brighter), with a lighter core and a faint glow,
  brightest where they leave the plant and fading toward their end substation (`FADE_TO` of the start, by share of
  each line's length). Every text is white capitals in Helvetica Neue on a black box at half opacity (`_boxed`,
  `BOX_A`); the plant's full name over its units gives way to a small mark before the mark appears. Sentinel-2 all
  the way out (decided with the user; `imagery_fade_km: null`): a 10 m close-up crop over a 60 m wide crop of the same
  pass (180×102 km; each layer in its own `imagery/<name>/`), in two eras (the layers' `era`, decided with the user,
  22 October 2026): the pre-war pass of 8 September 2021 (the reservoir full) until the record's date reaches the dam's
  destruction (`imagery_switch`, 6 June 2023), then a 3 s dissolve (said in the credit) to the pass of 28 August 2025;
  dimmed by one factor (`imagery_gain` 0.8) so the lines stand out. On it the rest of the 750 and 330 kV
  grid, faint, and GeoNames towns (never over a label or a line). The Great Meadow
  (`areas:`, the user's studio site) is OSM relation 1600087 (Великий Луг, natural=wetland): OSM maps it as the whole
  drained reservoir bed down to the dam, wider than the historical meadow (its upper reach); drawn as its outer shore
  only (decided with the user: the channels inside are today's, and the outline must hold for earlier states of the
  river; `_shoreline`, inlets under 1 km closed), drawn on as the frame takes it in, then a faint fill.
  Then the record (`record.py`, the network's `record:`; decided with the user, 22 October 2026): once the lines have
  landed, the date runs from 24 February 2022 and each line goes unlit when cut off and glows yellow when reconnected
  (light means power, decided with the user, 2 November 2026, the same in the 3D: connected lines lit, glowing with a
  white-hot core; cut ones unlit, the bare wire: a thin steel-grey hairline with a dark edge and no glow, `STATE_*`;
  the dark red and grey before it vanished on dark ground, read as roads and clashed with the 3D towers' red paint; a
  cut dims in `fade_off_s` 0.25 s, a reconnection swells back over `fade_on_s` 0.6 s, the Hum's swell to match),
  unlit and dotted (dots held along the line, `_dotted`; dotted means not confirmed, as the zone's dashed circle)
  where lines were cut but the reports don't say which (March to August 2022 for all, the other 330 kV lines until
  December 2022); island mode (`island`, 5–10 September 2022, checked 2 November 2026): every line cut
  while unit 6 powered the plant itself, not a complete loss (the count stays), labelled "ISLAND MODE: ONE REACTOR
  POWERS THE PLANT" under the count (in the 3D under the date) and captioned, the Hum a low note held in the middle
  (100 and 200 Hz, a design choice); the 3D starts inside it (`from_start`, its real start kept as `began`); every event a dated report with its sources (the IAEA's updates, mostly via the WNA's and OECD-NEA's
  chronologies, Energoatom, news). The IAEA names lines only from late 2022: "the 750 kV line" is Dniprovska, "the 330 kV back-up line"
  Ferosplavna-1 (Ferosplavna's two circuits part into two strands). Top left: the date, the IAEA's count of complete
  losses of off-site power (`count: derived` where the number follows from those either side), the legend, a caption
  per key event. The date shown steps from one reported change to the next (`Record.shown`, decided with the user:
  days with nothing reported are skipped, not raced through), and each state has room to breathe: every interval
  between reported changes held at least `min_hold_s` (0.7 s), a cut restored within the day shown `min_blink_s`
  (0.8 s) at its start, a complete loss within the day `loss_s` (1.8 s: a longer pause with every line off, decided
  with the user) and one lasting days `loss_hold_s` + `loss_day_s` a day up to `loss_max_s` (2.4 s + 0.12 s, up to 6 s:
  the month on diesel generators), the imagery dimmed a little more meanwhile (`loss_dim` 0.7); a captioned interval
  `caption_hold_s` (2 s), the caption staying while the date stays on its day; the rest of `run_s` (155 s) shared by the
  log of each interval's days. The record starts `wait_s` (13 s: 10 decided with the user, 3 more for the night lights) after the full chord has faded in:
  between, the lines still growing off screen grow faster (up to about 3.8x, eased in and out; film.json `time`), so
  all have landed first. The film is about 229 s (past the 3 minutes asked for earlier: the longer losses, the zone's
  moment and the night lights need it). Two camera moves after it has settled (film.json `moves`, decided with the user, 22 October 2026):
  the zone's held moment (below), and once the imagery has dissolved to the drained bed, a push in (`crossing`, 18 s,
  zooming about a point so the frame lands exactly) to a 25 km frame on the Dnipro crossing, where Dniprovska and
  Ferosplavna-1 cross the drained bed to the Nikopol bank, held to the end; the two named where they cross with their
  state ("the last 750 kV line", "the 330 kV backup line"), the other lines' names fading as the frame closes in, the
  towns on. Its imagery is a 10 m crop of the 2025 pass round the crossing (`crossing`, `centre_km`, shown below
  `fade_km` 30–44 km; a close-up is laid only where it has pixels). What the opening drew (units, titles) stays its own:
  the later moves don't bring it back; the Great Meadow's outline stays drawn but fades when close. Bottom left only the imagery's credit (pass, date, Copernicus
  attribution), no box, faint (`CREDIT_A`, decided with the user: not to draw the eye); the lines', towns' and
  record's sources are in film.json only (OpenStreetMap's ODbL asks for credit wherever the film is shown: in its
  description or end credits). The IAEA's protection zone (the record's `zone`, asked
  for by the user): proposed 6 September 2022, never agreed, set aside for actions to avoid on 30 March 2023; no
  size was ever published (Grossi: "the perimeter and the plant itself"), so it is a dashed circle round the plant's
  OSM site (1.6 km across) between those dates, labelled "proposed, never agreed" and that no size was published:
  never a radius of our own. Its day is a held moment (decided with the user: `zone.hold_s` 9 s, the date held): the
  camera closes in about the circle to an 11 km frame (its true size, faintly filled, with "the plant's lines reach 214
  km from it": the farthest point of any traced line), holds, and pulls back out while a ring of white light spreads
  from the plant, its front keeping pace with the frame (a drawn mark, said in film.json; off the lines, decided with
  the user, 2 November 2026: a light running along them read as power through lines that were all cut). The Hum (`hum.py`, decided with the user) is the film's sound: all ten lines fade in
  once the camera stops pulling back (about 40 s), so the full chord is heard before the war; then a voice per line
  on the 100 Hz hum and its harmonics with corona crackle, panned by the line's bearing, silent when cut, muffled
  where unreported, silence during complete losses (no diesel generators, removed by the user); no sounds of
  fighting. Synthesized: said in film.json `sound` and the statement, never passed off as recordings (no line on
  screen: removed by the user). The Hum beside the film as `<title>.wav` (`ZNPP-ten-lines-zoom-out.wav`). It ends on the last reported state (11 September 2026): only Ferosplavna-1 connected (Dniprovska cut
  since 24 March 2026, repaired in June, its substation too damaged to reconnect). Test renders at 30 fps
  (`--fps 30`); the final at the config's 60. The file is named by the film's `title`
  (`films/<id>/ZNPP-ten-lines-zoom-out.mp4`, film.json `files.video`; `film.mp4` without one; the user, 2 November 2026). Rendered in parts at once (`--workers`, default three in four cores;
  each layer blended only in the tiles it touches, `_blend`): a layout pass (no pixels) carries the labels' state frame to frame and starts each part from it, so the frames are those of
  one process; the parts are joined without re-encoding and the Hum muxed in. VIIRS
  Black Marble: tested 2 November 2026 (`research_notes/Night lights test/`, NEXT.md N2; `EARTHDATA_TOKEN` in `.env`,
  never printed; LAADS licence accepted by the user). Good-quality, clear-sky pixels only, never Gap_Filled; two
  satellites checked against each other; brightness is not electricity, so every dark place needs a source for why.
  In the zoom-out (the film's `night_lights`, asked for by the user, 2 November 2026: before, during, after, as the
  test's triptych): the ground at night at three held moments, each September (same season, no snow): 2021 in the full
  chord before the date appears; 2022 on 5 September, the date held (the record's `holds`); 2026 at the end, the camera
  pulling back out from the crossing to the 172 km frame and holding to the fade. The month's VNP46A3 pixels laid on the
  daylight pass dimmed to a faint map, each a block as measured, hatched grey where there is no good-quality value (an
  area, not a line); named top left under the caption with why it is dark only where a source says (2022: "the
  satellite shows where it was dark, not why"). Crops of the 172 km frame and the test's files kept in
  `libraries/conductive-seam/satellite/nightlights/blackmarble/` (`provenance.json`).

## Frame selection

The collection is about **places**: landscapes, architecture, scenery, nature, animals, and infrastructure. It is not
about people or interiors. `pipeline._extract` works in these steps:
1. One FFmpeg pass produces small previews (longest side 384px, in the video's own aspect ratio) of every candidate frame (scene changes, plus one frame every `interval_s`). Within a shot a frame is checked every `view_step_s` and kept once it shares less than `view_overlap` (0.5) of its view with the last kept frame (`selection: "camera_move"`; ORB features + a similarity transform, so a pan or flight gives a frame per new stretch of landscape while wind, water or people moving in a static shot don't count).
2. Dark frames, mostly-black frames (credits, title cards), and near-duplicates are dropped.
3. Up to `candidate_pool` previews are classified with SigLIP.
4. Frames with `subject_score` = share(`prefer`) − share(`avoid`) ≥ `min_subject` are kept, up to
   `max_frames_per_video` (100), spread over the timeline (`classify.choose`). `avoid` defaults to people, interior,
   and graphic.
5. Only the kept frames are decoded at full resolution.

Storage (decided with the user): by default only the WebP web (1600px) and thumbnail (400px) images are kept. The
downloaded video is deleted once its frames are taken (`acquisition.keep_media`, default false; its sha256 stays in
`video.json`), and no full-resolution file is written (`extraction.keep_originals`, default false). Then the frame's
`sha256` is of its decoded RGB pixels (`sha256_of: "pixels"`), and the panel links to the YouTube timestamp instead of
"Original". `evidence slim` does the same to stored videos. A slimmed frame record still names its removed original
and that file's hash (the record is immutable); the site links "Original" only while the file exists.
When tuning, check a contact sheet in a scratch library. Don't guess.

## Sorting (forensic review)

`sorting.py` orders the grid. The sorts are Place, Similar view, Camera angle, Damage, Scale, Colour, Light, Season cues,
Published, and Detail. They use `derived.features` (`visual.py`: pixel statistics plus SigLIP zero-shot camera angle,
damage and scale) and SigLIP image embeddings. The embeddings are stored in `frames/embeddings.npz` (canonical) and the
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
.venv/bin/evidence slim [--keep-originals] [--dry-run]   # delete stored downloads + full-resolution frames
.venv/bin/evidence refresh-titles                      # uploader title translations (1 unit / 50 videos)
.venv/bin/evidence satellite fetch --area enerhodar-crossing [--start 2023-07-01 --end 2023-09-30] [--sensor landsat]
.venv/bin/evidence satellite fetch --area great-meadow --start 2023-04-01 --end 2023-06-05 --until-km 9   # a partial pass
.venv/bin/evidence satellite film --area enerhodar-crossing [--passes ID ...] [--trace]   # into The Conductive Seam
.venv/bin/evidence satellite notes --area great-meadow [--film ID]   # place the config's notes on a film again
.venv/bin/evidence satellite network --network znpp [--trace-only]   # the plant's lines traced, the zoom-out film
.venv/bin/evidence satellite crossing3d [--network znpp]   # the crossing in 3D, pass 0: survey of lines, towers, water, flight path
.venv/bin/evidence satellite crossing3d --pass bed           # pass 3: the drained bed (shorelines + levels; fetches its passes once)
.venv/bin/evidence satellite crossing3d --pass animatic [--variant axis2k_record]   # pass 1: Blender animatic (headless); _record: the two lines' record seen and heard
.venv/bin/evidence satellite crossing3d --pass animatic --variant axis2k_record --seconds 40:55   # only that stretch, to test
.venv/bin/evidence satellite crossing3d --pass blend          # the 3D segments' scenes saved as .blend, not rendered
.venv/bin/evidence satellite unrolled [--fps 30] [--stills 5,34] [--seconds A:B]   # the two last lines unrolled (D3, Chrome headless)
.venv/bin/evidence storyboard [show|build|sync] [--cut storyboard]   # the film's storyboard in Blender's sequence editor
.venv/bin/evidence satellite lines --bbox W,S,E,N        # OSM power lines in a box (for a new area); --folder: scratch
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
- Frame Gallery, Frame Sequence, Transcript, Reconstruction, Route Map, Scene Viewer, The Conductive Seam, a zoom slider and the Light/Dark icon fixed at the bottom right
  (no search box there: search is typed in Sort & filter; `/` opens it),
  in that order left to right, all at 14px, on one line with equal gaps (names decided with the user). These are the views,
  one button each with exactly one on (the code calls them "grid", "timeline", "subtitles", "document", "map", "scene" and "seam";
  Scene Viewer, `scene.js`, below). The chosen view is
  remembered per browser (`localStorage.view`), so a reload stays on it (decided with the user); a first visit opens
  on the Frame Gallery, with the Video panel. The first time the gallery is drawn in a page load (hard reloads included), the
  images on screen fade in one by one in a random order across the grid over about 1.4 s (`revealGallery`,
  `REVEAL_MS`, a random transition delay each), with no flicker or flash. They first wait for each other to download
  (up to `REVEAL_WAIT_MS`), and any still arriving after that get a random delay of their own, so with nothing cached
  they still appear scattered, not top to bottom. Later re-draws (search, filters) and images below the screen fade in
  as usual, and reduced motion skips it.
  The
  slider (right is bigger) follows pinches and +/-. In the timeline and subtitles it is the same stretch as a pinch
  (`zoom.js` `stretchBy`), on a log scale over `tlRange()`; in the gallery it steps through the column counts
  (`zoom.js` `LEVELS`, `set`), fewest columns on the right, with the same snap glide as a pinch.
  Light/Dark is an icon only (a half-filled circle, no text; its tooltip says which theme it switches to). It follows the system until clicked, then is remembered per browser (`localStorage.theme`, `data-theme` on `<html>`);
- The Conductive Seam (`seam.js`, `/api/seam/films`): the satellite films, always from that folder, on a black ground.
  Under the film a thin strip says what each stretch is (observed solid, dissolve hatched, inset light) with the playhead and
  what has played filled (`.playhead`, `.done`: not `.head`, a global class that squashed it to nothing); click or
  drag to seek, Space to play, ← → 5 s. The left panel follows the playhead: the pass shown (a dissolve says it is an
  interpolation between two dates), distance along the line, the camera's position (a viewing path, not an
  observation), then the statement, passes with STAC links, provenance and `film.json`. Under the strip the film's
  notes (`.seam-note`, 15px, its sources small under it), one at a time, fading between them;
- Satellite (bottom left, between Video and Evidence, a satellite icon before the word): a form in the panel, held
  like Evidence (`satellite.js`): Area (config areas, corridors already made, or a new one: a box, then Find power
  lines), Line, Sensor, Between (dates), Max cloud, Save to The Conductive Seam; "Fetch the clearest pass"; then Film
  (passes, view width, speed, draw the line) and "Make film". Jobs wait in the same line as video jobs;
- Scene Viewer (`scene.js`, `/api/scenes`, `/api/videos/{id}/scene`): 3D reconstructions from a video's own footage,
  shown like a 3D viewer (black ground whatever the theme, a 50° view, wider than the phone's 37° to feel like standing there (`VIEW_FOV`; a camera's own view keeps its lens, eased back to 50° when walked off), orbit controls, a ring per second where the camera stood, fly
  to a camera). On load a take with an `open_t` (compose.py `open=`) starts far out and flies in, curving down behind
  the camera, to the camera at that moment, or to its `open_view` when it has one (not kept by a rebuild, which changes the take's
  coordinates; the ice pools' was lost to the rebuild with the later footage, so it flies to the camera at 4:55); a click,
  drag or scroll stops it. Previous/Next view step through a take's chosen views (`views` in scene.json, kept by a rebuild since they are moments in the video, not coordinates): for the ice pools 8, chosen against the footage so a viewer can find each in the video (walk-in 4:42, first sight 4:52, the opening view 4:55, beside the pool 5:00, across it 5:04, its end 5:08, the second pool 5:13, last look 5:28), each from `back` m behind and `rise` m above the camera at that moment, looking `look` m along its view, with a link to that moment on YouTube; without views they step through every camera. The splat is dressed for the map on the GPU (a Spark world modifier; the model itself is unchanged): its rim fades out from 0.9 to 1.45 times the take's radius (`SPLAT_FEATHER`: its splats reach about 1.4, the trees round it, the loose ones beyond), and it is always in its own colours (a far-off duotone was tried and removed by the user), with two light touches, said in the panel: its shadows a little cooler and greyer (`SPLAT_GRADE`; highlights and the ice untouched) and what lies well beyond what the view looks at hazed toward the dark land (`SPLAT_HAZE`, scaled by the view's distance). Its footprint (where its splats lie, worked out from them on load: `footprint`, `FOOT_*`) dims the land under it, in place of a round dark patch (no outline: removed by the user). W A S D move the view (forward, left, back, right, level with the ground), Q E down and up, Shift three times faster (`MOVE_KEYS`): the eye and what it looks at move together, at a speed that follows the view's distance (`MOVE_SPEED`: walking pace in the take, faster from afar); they stop the intro, and typing in a field doesn't move it. It draws only while the view moves (and briefly after), so a still view costs no GPU, and leaving it frees its WebGL context. One take at a time, each on its own (its own place and scale). Saved in `derived/scene/` (`scene.json`
  + per take a `.splat` and points `.ply`), tier `inferred` with confidence and provenance: the shape comes from the
  footage; the size is an assumption (the phone 1.5 m above the ground) and the panel says so. Built by `scripts/scene/`
  (pycolmap, every frame matched with every other, the uploader's logo masked; msplat splats on the Mac's GPU, floaters
  dropped, at most 1.2 million splats: Spark sorts them all each frame the view moves, and the full 2.5 million stuttered); floaters can be deleted by hand in SuperSplat (`scripts/scene/splat_ply.py` out to a .ply and back in, capped; delete only, never move the model, and the take's notes say so): a cleaned set belongs to one model only: the ice pools' `pools_cleaned.ply` beside it is the user's cleaning of the rebuilt take, and its notes say so ("Cleaned"; a compose.py rebuild drops that note). Only takes where the camera turns around a place work (decided with the user, after an
  attempt on the walking shots failed): for cSThxR6dXpc the two ice pools at 4:38–5:28, solved together with the later footage of the same place at 6:07–6:34
  (the left pool and the fisherman's outpost, then the pan back to the trail; compose.py `also=g@367.5@5`: every frame
  placed, against 201 of 254 before, and the user preferred it), from a 1080p download, levelled on the ice (frozen water is
  level), sized from the phone at 1.3 m (the user's notes) then ×0.75 by the user against the street map (`fit=0.75`;
  `radius=19.5`, `reach=17.2`, since the denser points give too small a radius for the splats' rim fade); a turn-around at 3:18–3:34 was tried and removed.
  Walking straight ahead gives too little to go on, and takes across a cut share no view: never join them into one
  model. Never generate (hallucinate) a scene from a single image for evidence.
  The land around a take (`scripts/scene/terrain.py` → `derived/scene/terrain.json` + `terrain_layers.webp`, tier
  `inferred`): FABDEM bare-earth heights (Copernicus GLO-30 without trees; 2011–15, so the former reservoir is flat water
  in them: the drained bed has no relief), true to size, never exaggerated (decided with the user), drawn as a map in a
  black and white, no colour (decided with the user; first a duotone of near-black and the Bandura line's pale blue): shaded by height, contours every metre, open water darkest, and where the drained bed stays wet (Sentinel-2
  moisture over six dates after the drainage: its old channels) lighter. Over it lies the Route Map's street map (`scripts/scene/osm_map.py` → `terrain_osm.webp`: OpenStreetMap, today's map, reprojected to the land's grid), in the same greys (its water darkest, roads lightest) at `LAND_MAP` strength and shaded by the relief, so it blankets the heights and shows the river channels and roads they lack; credited on the canvas, a backdrop only (nothing is read off it), kept by a terrain rebuild. `terrain.jpg` (true colour) is kept for a
  sharper photo drape near the take, still to try. On it the Bandura in blue and the walk drawn as the Route Map draws it
  (solid where filmed, dashed where a cut skips it, a dot per frame, A and B; wide lines, `Line2`; a run of cuts with only short takes between them reads as one dash, so `track.py` lists such runs as `skips` and both pages say so: the Route Map under its cuts and on the map (runs of 200 m or more), the Scene Viewer in its Lines note; how a run's skip divides between its cuts is spread evenly, a guess, and the notes say that too, e.g. after the ice pools 6:35–7:04, 4 cuts skip about 940 m with about 20 m filmed between them), fading out as the view
  comes down into the take (the splats' trees don't hide lines behind them). By default the take is placed and turned as the Route Map has it: at its estimate, its cameras'
  way first to last along the Route Map's walk over the same seconds (the footage has no compass). The ice pools are set
  by the user (`--at`, `--bearing`, with notes): at the trail's point at 6:15, turned 224.5° (first 239°, fine-tuned against the street map; kept for the rebuild), so the splat's narrow end,
  where the videographer walks in, points back to the last Bandura point; the walk plan's `ice_pits` piece then runs the
  jump at the cut at 4:28 into that end and the Route Map's frames of the take along its own camera path. The lines
  leave out only the take's own camera path, so the way in reaches the splat. On load the view starts over the whole area from the south (north up,
  so the map is never upside down), turned toward the opening view's way by at most 60° (from the south-east or
  south-west, decided with the user: no 180° spin), with the take in the middle; the land fades in as the flight starts,
  and it comes down to the take, turning the rest of the way gradually over the descent; round the take the land never
  hides the model;
- Frame Sequence (the timeline view): one row per video like a clip in an editing timeline, with no text, numbers
  or ruler: each extracted frame starts at a black vertical bar at its timestamp and runs until the next bar, with its
  image in the middle of that stretch and its edges slit-scanned out to the bars: the image's outermost columns
  stretched sideways, shading into the neighbouring frame's edge colours at the bar, so streaks blend from one image to
  the next (`edgesOf`, `shade`, `dress`: small images made in a worker, `edges.js`, ahead of time while the page is idle (`prewarm`, which also fetches the transcripts), drawn as background layers so a zoom only repaints;
  a frame wrapping onto another line is `.split`, positioned by `--cx`, `--fx0`, `--fx1`). Where the stretch is
  narrower than the image, the image's middle shows. Frames outside the current search or filters leave an empty stretch with no bar. Re-layouts reuse and move
  the existing segment elements (`segEls`) at whole-pixel edges, never rebuild them, or zooming flashes white. All videos
  share one time scale; pinch or +/- stretches time only (`zoom.js` `stretch`, re-laid out live, no transform, no snap).
  The stretch is continuous, separate from grid density, and reaches until the shortest video spans about two widths,
  so short clips with dense frames spread out too. Lines run the full page width so the strip reflows smoothly, and a
  video's height eases (`tlTick`) when it gains or loses a line, with the video under the pointer held in place.
  Strips meet edge to edge with no blur or splice effects; the only blending is the slit-scan shading into the bars. The strip is thin: each image keeps its width at the unsquashed height (`--ih`, `--ar`) but is squashed flat to the
  line height; a line grown for an opened frame is not squashed. Clicking a frame (pin) opens a slot
  in the strip for its image, whole and sharp (`web_url`, a `.seg.image` element), on the line its marker is on: the image
  never moves to another line, and the timeline only grows forward (never backwards, never a line added above). The image always
  shares a border with its marker. A frame in the left half of its line opens to the right: the slot starts at the
  marker and the strip after it slides on (onto the next line if it must). One in the right half (or whose image doesn't
  fit to the right) opens to the left: the marker stays put, the slot ends at it, and the strip before it on that line
  squeezes into the room left of the image, still in order (words show as dashes until zoomed in). Two images in one
  video never move at once (`spreadTo`): clicking another frame closes the open one at the usual speed, then opens the
  new one, and while an image is closing its video's other frames can't be clicked open (`closingIn`), so a closing slot
  never pushes a new frame onto another line. While a frame is pinned, the marker under the pointer still thickens
  (and darkens in Transcript), showing it can be opened. An opened image's side (`spread.side`) is chosen when it opens and again
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
- Transcript (the subtitles view): the filmstrip's lines, time
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
- the live count, polling `/api/stats`, in italics at the top of the Evidence and Sort & filter panels (`statsEl`, moved
  into whichever is open): "20 uploaded · 1019 images", or what the search and filters leave, "120 of 1019 images · 10
  of 20 videos" (with a Near sort, how many images are near the place);
- Sort & filter (beside Evidence, a sliders icon before the word; the button counts what is set, "Sort & filter · 2"):
  opens in the panel, held like Evidence (hovering frames shows them; Esc or the button goes back to Video; a frame
  clicked and let go comes back to it), and switches the view to the Frame Gallery, where sorting works. Top to bottom: the
  live count, a search field (the same search as the bottom one), Sort (every sort with a line on what it does, and
  "Like your image" while an image is the sort), the study-area places as "Near" sorts (one note, then the names),
  Category (any number; a frame must have every one chosen), Published on YouTube (All or one year; counts are over the
  whole folder) and Clear all (which also clears the search and the image). Every choice applies at once, so the grid
  changes beside it. The chosen sort and year are kept in hidden selects (`#filterstate`), the categories in `cats`.
  Dropping or pasting an image opens it too;
- Video (bottom left, an upload icon before the word): a form in the panel. It is the panel's resting state: open on
  load (at once, before the images arrive) and whenever nothing is selected (after a frame is unpinned, or Evidence is closed); there is no intro text.
  Opening it deselects any frame. Hovering frames (in the Frame Gallery, Frame Sequence and Transcript) shows each in its place, and moving the pointer
  off the images brings it back as it was (typed text and focus kept; the same for Evidence, except while renaming);
  clicking a frame pins it, and closing Video (its button, Esc) leaves the panel empty so hovering frames shows them. It keeps what was typed. YouTube links sit in the
  title's place ("Paste a YouTube link, links"); Search is one line like the other fields (it grows as you type), and its example cycles through ten (`SEARCH_EXAMPLES`, no "e.g.", every `EXAMPLE_MS`): drawn over the field, not as a placeholder, so the old one lifts and fades as the next rises in; under them one grid of settings, all 14px with even rows and no help text: Search, YouTube key,
  Anthropic key, Remember keys, Place (default Ukraine), Near, Published (whole years only, default 2022 – 2026), Max
  videos, Licence (Creative Commons only, or any public video) and Save to: New folder (the default, with its name
  "Evidence folder <n>" in a field below to change) or an existing folder, which fills in its place and years. For an
  existing folder a faint line says what it holds, and warns when the search doesn't fit it (nothing for a new one). After a job starts, Save to stays on its
  folder, so further searches add to the same project. Tokens: a YouTube Data API key, required for every job
  (searching and reading licences); the server has no key of its own for jobs and never falls back to `.env` or the
  environment. An Anthropic key is optional and not needed for scraping (`jobs.LLM_MODEL`
  turns the description into up to 5 searches and, for a new library, writes its spellings and box; without it the
  words are searched as typed). Tokens stay in the browser (this tab, or localStorage when "Remember" is ticked), go
  with each job, are held only in that job's memory and are blanked out of its log; never write, log or return them.
  The LLM's answer only steers the search and a new library's scope check; it is never evidence on a frame. Jobs run
  one at a time on the server and share its SigLIP model with search by image; the panel polls `/api/jobs/{id}`
  and reloads the grid as videos are added, or links to the folder when it isn't the one shown. A video saved without
  images (not downloaded) says why;
- Evidence (beside Video, a folder icon before the word): the evidence folders in the panel (no title above them),
  held like Video; closing it goes back to Video. Each row:
  its name, then its live count ("20 videos · 1019 images", refreshed while the list is open) (click the name to show that folder in the grid; the `lib` cookie, so the site shows one folder at a time; with none
  chosen yet it opens the first folder that holds images, the main one first, and remembers it), its
  place and years, where it is on disk, then Show in Finder (Open folder elsewhere) and Rename
  (the name becomes a field: Enter saves, Esc cancels). The page title is the folder's name. `/api/jobs` and
  `/api/folders` only accept JSON from this site's own origin.
The panel shows the original title in plain text (no bullet). Everything under it is secondary, in faint italics: the
uploader's own English title (`source.title_localizations`, from the API `localizations` part) when they set one,
then the channel and year.
No machine translation and no click-to-switch. `evidence refresh-titles` backfills stored videos.
An empty folder (a new project) leaves the grid blank; "No frames match" is only for a search or filter.
The grid loads every page of `/api/frames` (500 per request); never assume one page holds everything.
Use the default cursor on tiles. Clicking a tile pins it: the image opens out of its tile to fill the gallery side, whole (its own aspect, not the
tile's crop), over the page background (`zoomTo`; the panel and controls stay above it), and the panel stays on it
until it or the space around it is clicked, or Esc is pressed: it shrinks back into its tile and the Video panel
comes back. The arrow keys and the tally step through frames in place. Bottom controls are sized to their text so the gaps are equal.
Plain HTML/CSS/ES modules in `web/`, no build step. Grid density is `--cols`, set by `zoom.js`:
during a pinch the grid scales continuously (CSS transform), then on release it snaps to the nearest column count with a
FLIP glide. Inputs are ctrl+wheel, Safari gesture events, touch, and +/- keys.

Search (`search.py`) parses free text into AND-ed terms.
- Visual words and synonyms ("person", "buildings") match frame categories, not video text.
- Other words match video text and place names at word starts, including gazetteer spellings and Latin-to-Cyrillic
  transliteration.
- Multi-word queries also match the exact phrase in video text.
When adding a category label, add its common synonyms to `VISUAL_SYNONYMS`.
