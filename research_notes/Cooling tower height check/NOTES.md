# Cooling tower height check (4 November 2026)

The 3D plant (scene3d/plant.py) gives ZNPP's two cooling towers 125 m, from SkyscraperPage (b63203, b78211) only.
A tower of the same fill elsewhere (Kharkiv) is about 81 m, so the height was checked against the imagery itself.

Method: the shadow cast on a winter Sentinel-2 L2A pass (10 m, B08), from Microsoft Planetary Computer. The sun's
elevation and azimuth come from each item's STAC properties (`s2:mean_solar_zenith`, `s2:mean_solar_azimuth`).
- A profile runs from each tower's OSM centroid along the shadow's direction (sun azimuth + 180°), averaged over
  three parallel lines 10 m apart. The tip is where the profile crosses halfway from the shadow's level to the
  ground's beyond it.
- H = (tip − r_top) · tan(elevation), with r_top ≈ 26 m. The shadow's width is about 60 m, so the top is about
  0.6 of the 86 m base that OSM gives.
- Passes before June 2023 have water north of the towers, so their shadow ends can't be seen; only passes from
  2023 onward, over the drained ground, were used.
- Cross-check: the thermal plant's 320 m chimneys' shadows run off the crop's edge at the length 320 m predicts
  (about 950 m at 18.6°).

| Pass | Sun elevation | CT1 tip → H | CT2 tip → H |
|---|---|---|---|
| 2023-11-30 | 20.67° | 364 m → 128 m | 342 m → 119 m |
| 2024-01-01 | 18.50° | 412 m → 129 m | 394 m → 123 m |
| 2024-01-09 | 19.61° | 460 m → 155 m (outlier: snow or cloud shadow) | 362 m → 120 m |
| 2024-01-29 | 23.44° | 300 m → 119 m | 288 m → 114 m |
| 2024-12-14 | 18.90° | 380 m → 121 m | 374 m → 119 m |
| 2024-12-24 | 18.61° | 394 m → 124 m | 388 m → 122 m |
| 2025-01-20 | 21.11° | 332 m → 118 m | 316 m → 112 m |

Result: a median of about 120 m. The spread, 112–129 m without the outlier, comes from the 10 m pixels, the
unknown top radius and the ground's slope. This agrees with 125 m within the measurement and rules out ~81 m
(which would cast a shadow of about 265 m at 18.6°). The model keeps 125 m, now with this check as a second source.

No plumes: the 2019 and 2021 passes show the towers' plumes while the plant ran; the 2022 and later passes show none.
