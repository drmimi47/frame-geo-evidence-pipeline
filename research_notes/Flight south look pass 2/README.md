# Flight south, look pass 2 (7 November 2026)

A new variant, `south_look2`, beside the approved `south_record` and `south_look1` (decided with the user, 7 November
2026: a second improved render, this time for geometry). It keeps everything of south_look1 (camera path and motion,
record, timing, sound, fades, sky, water, grade) and adds: (1) vegetation, (2) more detailed towers, (3) finer
fittings on the lines. Output, beside the others:
`libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d/animatic/ZNPP-last-two-lines-3D-south-look2.mp4`
(.wav, .blend, _contact.webp). How to follow, pause and resume the render: RESUME.md.

## How it is built (options of the variant; the approved films render as before)

- Config: `crossing3d.animatic.variants.south_look2` in config/conductive-seam.yaml: a copy of `south_look1` with its
  own `title` and, under `look:`, `vegetation: {seed: 7, spacing: 1.0, gain: 0.8, lod_m: [350, 1200],
  thin_m: [1500, 4500, 0.35], cone_cos: 0.6, min_scale: 0.03}` and `detail: true`. Nothing shared was changed.
- New: `scene3d/vegetation.py` (placement, growth), `scene3d/plants.py` (the procedural plant models, from
  research_notes/Under the crossing still/scripts/plants.py, plus `crown`, a 46-triangle far level of detail).
- `scene3d/export.py`: `_vegetation` (cached in vegetation.json/.npz by the seed, spacing, track and towers) and
  `_detail` (towers_detail.npz; refused if any attachment point differs from the approved towers'); scene.json
  `look.south_look2.vegetation` and `.detail` carry the statements and sources.
- `scene3d/build.py`: `vegetation()` (geometry-nodes instancing, a keyed "veg day"), `_plant_material()`, and
  towers_detail.npz in place of towers.npz when `look.detail`. Every option off by default.
- `scene3d/look.py`: the per-frame `veg_day` (days from 6 June 2023) when `look.vegetation`.
- `scene3d/towers.py`: `build_types(detail=False)`, `fittings(..., detail=False)`, `DETAIL_STATEMENT`.
- tests/test_vegetation.py (6 tests). The whole suite passes (172 passed, 1 skipped).
- Checked that the approved films are unchanged: after export with the new code, towers.npz, camera_south_record.json
  and camera_south_look1.json are byte-identical. south_look1's frame 1201 rendered with the new code is identical to
  the frame in the film (0 difference); frame 2251 differs on 0.03% of its pixels by at most 9 levels (mean 0.004),
  EEVEE's sampling noise, not a change.

## 1. Vegetation: done

- The drained bed, after June 2023: the under-the-crossing stills' habitat rule (`place_plants.py`) on each later
  10 m pass that has its bands (Sentinel-2, 19 August 2023, 23 August 2024, 28 August 2025): water (the pass's mask),
  reed (GNDVI 0.35 or more within 30 m of water), woody (GNDVI 0.6 or more and NDMI 0.18 or more), herbs, sand, bare.
  Three layers (canopy, understorey, marsh) on jittered grids. A plant appears with the first pass whose habitat
  brings it and is dropped if any later pass shows its spot as water or bare; its family comes from the last pass
  (white willow, black poplar, willow and poplar saplings, Amorpha, Tamarix, common reed, cattail; the species from
  Kuzemko et al. 2025).
- Growth by the date shown, never popping: trees follow the sources' heights (bare in June 2023; about 7 m in 2025,
  Kuzemko via Hmarochos and the Institute of Botany; to about 9 m by 2026, TSN and Kherson Online), the 2023-24 heights
  interpolated (said so); each 2025 tree's height drawn from willow 4-7 m (mean 6.4) or poplar 5-7 m; a later cohort
  starts later on the same curve. Shrubs and reeds grow over their first season. Each plant fades in (grows from
  nothing) over the 40 days before the pass it first shows on.
- Banks: OpenStreetMap's woods, scrub and tree rows (natural=wood|scrub|tree_row, landuse=forest; one Overpass reply
  saved verbatim, raw/osm_vegetation.json, ODbL) where the 2025 pass shows vegetation (GNDVI 0.4 or more, not water);
  trees 10-16 m (typical, not measured), shown at every date. Fields and herbs stay the imagery.
- Left out: within 1.5 km of the units, the cooling pond (found in the 2025 pass, 7.7 km²) and 500 m round it (no
  new detail there), within 30 m of a tower. The Dniprovska substation is outside the box.
- Density by lateral distance from the camera's track (canopy every 4 m within 400 m, then 6.5, 9.5 and 14 m out to
  4 km, the band edges blended over 150 m so no seam shows; understorey and reeds only within 700 m). In Blender:
  three levels of detail for trees (jittered at 350 m and 1200 m so changes don't sweep as rings), thinned from
  1.5 km to 35% at 4.5 km, culled behind the camera and outside a 53° cone, and below 3% of full size.
  785,090 points; 10-25 thousand drawn at a time.
- Look: each face's own colour shaded by the scene's fixed sun, each plant slightly lighter or darker, hazed like the
  rest, no shadows (as the land). `gain` 0.8 (from 1.0: far woods read about 25% brighter than the imagery's forest
  at the same spot; at 0.8 they are close, the haze taking the rest).
- Statement (scene.json `look.south_look2.vegetation.statement`): the plants are modelled and representative; where
  they stand is inferred, a pattern drawn by rule from the dated passes; their growth follows the sourced heights.

## 2. Towers: done

`towers.build_types(detail=True)`: the same types, heights, positions and attachment points (checked, and refused at
export if any differs), with more of what Novoklimov's 2011 photographs of these crossings show (b13, b15, b16, b29,
b30, b38-b40, b46): built-up legs (two angles back to back), a redundant horizontal and sub-diagonals in the faces'
wide panels, square-in-square plan bracing and gusset plates at the girts, walkway decks on the railed crossarms, a
ladder up one leg of the crossing towers, the small railed bracket under the 750 kV suspension towers' main arm, glass
discs with ribbed skirts. The 330 kV crossing tower goes from 35k to 106k faces. **No aviation markers**: none show on
the photographs of these crossings. Member sizes and spacing are representative (said in `DETAIL_STATEMENT`).
At 960x540 the extra members are barely visible (contact sheets/v1_towers_43s.png); they are for the final resolution.

## 3. Power lines: done (what was missing)

Already there in look1: the 750 kV fivefold bundles (0.6 m pentagon), 330 kV pairs, spacers every 55/65 m,
Stockbridge dampers, earth wires, the sag. Added with `detail`: 750 kV spacer-dampers with a hub and an arm to each
sub-conductor's clamp, bell-weighted dampers. The record's conventions (lit = connected, yellow glow; cut = dark bare
wire; dotted = unreported) and the 0.7 px floor are untouched (the wires are the same arrays as towers.npz).

## Look-dev (contact sheets/)

- look1_film_16.jpg: 16 frames of the finished look1 film (1-151 s).
- stills_v1_bed.jpg: look1 (left) and look2 (right) at 55, 60, 65 and 71 s over the drained bed (gain 1.0).
- stills_v2.jpg: the render's settings (gain 0.8) at 12, 20, 43, 55, 65, 71, 75 and 120 s.
- v1_crop_71s.png: a 2x crop at 71 s: reeds along the water, willows and saplings scattered over the sand.
- vegetation_map.jpg: the placement from above (points by family).
- scripts/: sheet.py (the comparison), vis.py (how many plants pass the culling at a frame), veg_map.py.

## Seen, for the main session

- In look1 (and so in look2; not this pass's subject): the river after the breach is a flat olive sheet with no
  detail (55-65 s fill most of the frame with it), and at 60 s the water's edge is stair-stepped (the 20 m mesh or
  the water mask's pixels). The ground near the camera is soft (10 m imagery from 70 m up) and smeared by motion blur.
- The plants are honest to the passes: the track crosses mostly sand and herbs, so the bed reads as scattered
  saplings and shrubs with reeds along the water and woods in patches, not a continuous forest. Herbs (most of the
  green) are left to the imagery.
- A dense wood shows on the drained bed east of the plant at the end (120 s, right of the cooling towers), outside
  the exclusions; it is woody in the 2025 pass.

## Deleted (8 November 2026)

The render (frames, .mp4, .wav, .blend, contact sheet) and its storyboard preview were deleted at the user's request once look pass 3 went into the cut. The variant `south_look2` stays in the config; it can be rendered again from it.
