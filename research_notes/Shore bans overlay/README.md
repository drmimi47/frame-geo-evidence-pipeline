# Shore bans overlay (5 November 2026)

A storyboard still, `shore_bans.jpg` (shot `shore-bans`, before `soundscape`), asked for by the user: how the Enerhodar
side is closed off, with the other bans on residents round the crossing for context. Its sources, quotes and their
status are in `restrictions.md`. Storyboard material, not a frame of the film.

- Ground: the zoom-out's pass of 28 August 2025 (the 10 m crops `c3d_2025_08` and `c3s_2025_08` feathered over the
  60 m `wide_s2`), only resampled and dimmed (0.62), 56 km wide, north up, no date shown.
- Occupied: DeepStateMAP's map of 4 November 2026 (`../Front line overlay test/raw/history_1793824024.geojson`), as
  the front line overlay test draws it. Its occupied edge runs along the south bank's old shore, not the river.
- Enerhodar's 500 m (TASS, 1 August 2024: the administration "once again" reminding residents; the administration's
  own post not found): a band 500 m inland of the reservoir's shore before the breach (OSM relation 1600087's outer
  edge, as the film draws it), inside OSM's Enerhodar hromada (relation 12207507) and the occupied area: 10.8 km²
  drawn. **Two readings of ours, said on the still: which shore (no source says) and which area (not stated).** The
  hromada reaches barely into the bed, so the ban on crossing is said in the key, not drawn.
- Balitsky's 15 km (Epiphany services without parishioners, January 2025 and 2026): a dashed edge 15 km from the old
  shore over the occupied land. A limit on gatherings, not on movement; in this frame it shows only at the bottom.
- Nikopol district's order 34 (25 March 2022, still cited in 2024 and April 2026): no distance given, so only the
  north bank's old shore dashed, inside OSM's Nikopol raion (relation 1738037), never a band of our own.
- Towns: Enerhodar and Kamianka-Dniprovska (in the May 2023 "temporary relocation" of 18 settlements); Nikopol and
  Marhanets (compulsory evacuation from May 2026 of almost 100 streets and one street, none named); Vyshchetarasivka
  (all residents, July 2026). GeoNames points, Kamianka-Dniprovska from OSM (node 337675581). The 2026 orders' quotes
  are to be reopened before any screening (`restrictions.md`).
- Left out: curfews and the checkpoints (one line in the key); the Kherson 15 km zone and the upstream Kushuhum and
  Dolynska bans (outside the frame).

`raw/osm_enerhodar/` holds the Overpass replies as fetched (`boundaries.json`: the hromada and the two raions with
geometry; `tags.json`; `places.json`). `scripts/bans.py` makes the still:
`python -I "research_notes/Shore bans overlay/scripts/bans.py" <deepstate.geojson> <boundaries.json> <out.jpg> <out.json>`
from the project root (it imports `zoomout._shoreline`, so the project's venv).
