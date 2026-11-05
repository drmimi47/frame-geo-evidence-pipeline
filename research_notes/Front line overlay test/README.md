# Front line overlay test (5 November 2026)

Two storyboard stills: DeepStateMAP's occupied area over frames of the zoom-out (film-20261102-221617), to see the
idea before anything is rendered (the user: shown near the beginning, in zo-plant/zo-war, as the site's context;
never during the night lights; not always visible elsewhere).

- `front_2026-11-04.jpg`: the frame at 43.0 s (the full chord, every line landed, no date shown) with DeepStateMAP's
  map of 4 November 2026 (id 1793824024, created 2026-11-04T20:27:04Z). The lines are drawn in their pre-war state
  under today's front: two dates in one picture, fine for a storyboard idea, not for the film.
- `front_2022-09-03.jpg`: the frame at 67.0 s (the record's date 3 September 2022, the last 750 kV line cut) with
  DeepStateMAP's map of 3 September 2022 (id 1662240097, created 2022-09-03T21:21:37Z). The same date on both.

What is drawn: only the polygons DeepStateMAP names "Occupied", a faint red over the ground (22%, never over the lines
or text, which keep their own pixels) and a red edge; "Unknown status"/"Contested" a thin dashed edge. Points (attack
directions, units) are left out. Projected with the zoom-out's own plane (metres about the plant, north up) and its
camera at that second (film.json). The label: "Occupied · <date> / an assessment from open sources ·
deepstatemap.live", top right (the film's date, count and legend have the top left).

Source and licence: `raw/history_public.json` (the list of dated versions, 1,804 from 3 April 2022) and the two
`raw/history_<id>.geojson`, saved as fetched from `https://deepstatemap.live/api/history/...` on 5 November 2026.
DeepStateMAP's licence (https://deepstatemap.live/license-en.html, updated 3 September 2025): visual and text
materials with a text reference, its logo or a link may be used freely; the API is free for volunteer and charitable
work and for defending Ukraine's sovereignty, commercial use needs approval, no redistribution of the API, no
identical copies of its maps. Its map is an assessment from open sources, so it is credited as one, never shown as
observed. Its history starts on 3 April 2022: the occupation's first weeks (24 February to 2 April 2022, the plant
seized on 4 March) need another dated source or stay unmapped.

`scripts/overlay.py` makes them (`python -I overlay.py <frame.png> <geojson> <t_s> <label> <out.jpg>`, from the
project root).
