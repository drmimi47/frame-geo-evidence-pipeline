# Under the crossing: prototype still (5 November 2026)

The user picked idea 1 for the picture of `under-the-crossing` (the 30 s speculative soundscape,
`../Speculative crossing soundscape/`): lying on the bed under the wire, looking up. These are two test frames to
change before a full render: `still_dawn.png` and `still_day.png` (1920×1080, EEVEE). The birds are heard, not shown.
This is storyboard material, not a frame of the film.

- **Scene:** the south flight's saved scene (`ZNPP-last-two-lines-3D-south.blend`, opened read-only and never saved)
  at frame 4001, the last reported state on 11 September 2026. Ferosplavna-1 is connected (lit, with flow dashes),
  Dniprovska is cut (the grey hairlines on the right), the 2025 ground, and the water at its settled level. The
  towers are modelled by type, at OSM's positions, as in the 3D film.
- **Camera:** 1.6 m above the bed, 150 m south-west of Ferosplavna-1's crossing tower 20 (the first caisson off the
  south bank), looking 55° (north-east) along the span, 18° up, with a 20 mm lens. It is still. This is the one spot
  where the 2025 pass shows open water ahead, so the tower stands clear of the trees. The wires' 0.7 px floor is
  rescaled to the lens.
- **Trees (modelled, representative, to be said so):** the self-seeded white willow (Salix alba, S. × rubens) and
  black poplar of the drained bed, 22% poplar. The shapes are procedural (stems, branches, leaves), at three levels
  of detail by distance. Heights: willows 4–9 m (mean 6.4), poplars 6.5–9.5 m. Sources: about 7 m in 2025 (Kuzemko,
  Hmarochos, 3 September 2025), the largest about 9 m by spring 2026 (TSN, 7 June 2026), "a 5-metre forest"
  (Frontliner, 13 August 2026). The tower is 100 m, so the forest is about a tenth of it.
- **Where the trees stand:** only where the 28 August 2025 pass's pixel is vegetation (its green at least its red,
  darker than 115/255, not water by its own mask). None within 26 m of a caisson, and an 8 m clearing round the
  camera. One about every 4 m out to 160 m, about every 6.5 m beyond, with 12% left out at random. 5,580 trees in
  all (`trees.json`, `trees.npz`). The positions are a pattern drawn from 10 m pixels, not individual trees.
- **Grass:** tufts in the foreground, representative.
- **Light:** the scene's own flat shading, with two versions:
  - *day*: the film's overcast haze;
  - *dawn*: a drawn gradient sky with a sun glow, at a mid-May sunrise (azimuth 57°, 6° up: nearly behind the
    tower from here, so it stands backlit), with the haze warmed.

  Both are drawn, not observed.
- **Scripts:**
  1. `python -I scripts/place_trees.py trees.npz trees.json 3729 4757 150 235` (tower x y, distance, bearing from
     the tower to the camera);
  2. `blender -b --factory-startup <south.blend> -P scripts/still.py -- trees.npz <out> day dawn` (about 25 s a
     frame).

Seen so far:
- The near-left willows' leaves still read a little like confetti.
- The water is flat and brownish (it is the film's modelled surface).
- The foreground right is open, because the 2025 pass shows open ground there.

## v3: denser, layered growth and six views to compare (5 November 2026)

The user, after seeing the two stills above: "add more trees, vegetation, different types of plants, etc. should
really look like nature is growing. generate other views so i can compare too." The new stills are in `v3/`
(`<view>_<light>.png`, 1920×1080, EEVEE). `v3/contact.jpg` shows them all, labelled. `still_dawn.png` and
`still_day.png` above are kept as they were. Storyboard material, not a frame of the film. Nothing here comes from an
AI image tool: every plant is a procedural numpy model (`scripts/plants.py`) placed by rule (`scripts/place_plants.py`)
and rendered in the film's own scene (`scripts/still_v3.py`).

### The plant mix and its sources

Only species that the sources record on the drained Kakhovka bed are modelled. Their shapes are representative
(modelled, said so), not drawn from photographs of individual plants.

| Family (code) | Species | Source on the bed | Height used |
|---|---|---|---|
| 0 white willow | Salix alba, S. × rubens | UNCG (22 Aug 2023); The Revelator (12 Nov 2024); Kuzemko et al. 2025, Table S1; Kherson Online (12 Oct 2026) | 4–9 m, mean 6.4 (sources, below) |
| 1 black poplar | Populus nigra (22% of trees in thickets, more on sand) | the same | 6.5–9.5 m (sources) |
| 2 saplings | young willow and poplar, the understorey | saplings 20 per m² (Kyiv Independent, 7 Jun 2024), up to 60 per m² (Vasyliuk, via Nikopol News and Texty); "tree, shrub, herb and moss layers" (Moisiienko, Oct 2026) | 1.4–4 m, typical |
| 3 false indigo | Amorpha fruticosa | Kuzemko et al. 2025 (sands); common on the old shores (Didukh, via Glavcom and Suspilne) | 1.2–2.6 m, typical |
| 4 tamarisk | Tamarix ramosissima | Kuzemko et al. 2025 (willow and poplar thickets) | 1.6–3.6 m, typical |
| 5 common reed | Phragmites australis | Kuzemko et al. 2025 (marshy); "marshy areas, reeds" (Interfax, 11 May 2026) | 2–3.6 m, typical |
| 6 cattail | Typha angustifolia, T. latifolia | Kuzemko et al. 2025 (marshy) | 1.5–2.4 m, typical |
| 7 tall grasses | Phalaris arundinacea, Calamagrostis epigejos, Echinochloa crus-galli | Kuzemko et al. 2025 | 0.6–1.5 m, typical |
| 8 broad-leaved herbs | Xanthium orientale, Chenopodium album (and Amaranthus, Bidens frondosa) | Kuzemko et al. 2025 (sands, muddy ground) | 0.5–1.5 m, typical |
| 9 wormwood | Artemisia absinthium, A. vulgaris | Kuzemko et al. 2025 (muddy ground) | 0.9–1.9 m, typical |
| 10 flowering herbs | Lythrum salicaria, Melilotus albus, Epilobium hirsutum | Kuzemko et al. 2025 | 0.7–1.6 m, typical |
| 11 dry stalks | Erigeron canadensis and the year's dead herbs | Kuzemko et al. 2025 | 0.5–1.4 m, typical |
| 12 low grasses | Carex spp. and low grasses | Kuzemko et al. 2025 | 0.2–0.7 m, typical |

- **Tree heights (sourced):** about 7 m in 2025 (Kuzemko, Hmarochos, 3 Sep 2025); a mean over 5 m (Institute of
  Botany, via Bukinfo); the largest about 9 m by spring 2026 (TSN, 7 Jun 2026); 9 m measured in October 2026
  (Kherson Online, 12 Oct 2026); "a 5-metre forest" (Frontliner, 13 Aug 2026). Trunks are wrist-thick, and
  density has fallen by at most half as the trees grow (Texty, 28 May 2026).
- **Other heights:** every other height is a typical value for the species from general floras, not measured on the
  bed, and the stills never present it as measured.
- **Kuzemko et al. 2025:** Ukrainian Botanical Journal 82(5), supplement Table S1
  (https://ukrbotj.co.ua/suppl/ukrbotj82-05-488-S1.pdf; surveys of 30 Jun 2023, 19 Oct 2023 and 21–22 May 2024).
  It lists 147 taxa by habitat, transcribed in `v3/sources/kuzemko2025_table_S1.tsv`. Where a species is typical of
  a habitat in general floodplains rather than recorded in that habitat on this bed, its habitat is called
  typical.
- **Not modelled:** Salix triandra, S. viminalis and Ambrosia. The sources looked at don't record the willows on the
  bed, and they record Ambrosia only as "present but few" (Vgoru, 6 Jan 2024).
- **The models:** procedural stems, branches and leaves.
  - Willows have narrow lance leaves (7.5–12 cm, 0.14–0.2 as wide as long) on drooping twigs, which fixes the
    confetti look of the first still.
  - Poplars have hanging, rhombic-deltoid leaves (6.5–9.5 cm) with rounded shoulders and a drawn-out tip, drawn as
    a 12-triangle fan, in duller greens.
  - Reeds have plumes, and cattails have their brown spikes.
  - Herbs and grasses are ribbons and small leaf cards.
  - Each family has 4 variants and up to 3 levels of detail: 112 prototypes, about 2 million triangles, instanced
    by Geometry Nodes.
  - The crowns are darkened inside, a drawn occlusion: the plants are emission-shaded by the scene's fixed sun
    direction and hazed by distance, like the rest of the 3D film, and cast no shadows.

### How each layer is placed (`scripts/place_plants.py`)

- **Habitat:** read from the Sentinel-2 pass of 28 August 2025, the scene's own ground, using its 10 m bands and its
  own water mask.
  - water: the pass's mask; nothing is placed on it.
  - reed: not water, GNDVI 0.35 or more, within 30 m of water.
  - woody: GNDVI 0.6 or more and NDMI 0.18 or more.
  - herbs: GNDVI 0.35–0.6.
  - sand: GNDVI 0.2–0.35.
  - bare: GNDVI under 0.2.

  Each plant reads the habitat at its own spot jittered by about 4 m, so the pixel edges blur.
- **The first still's rule was wrong.** Its RGB rule (green at least red, darker than 115) put trees on wet or
  bare sand: GNDVI 0.05–0.25 at its near trees. The new rule leaves that ground open. This is why view a, at the
  first still's spot, now has no trees near it.
- **Layers:** each layer is a jittered grid round the camera. Spacing grows with distance and the level of detail
  falls. A plant is kept at each point with a chance set by habitat, and its family is drawn from that layer's mix
  for the habitat.
  - **Canopy** (willow 75–85%, poplar 15–40%):
    - spacing 3.3 m to 22 m, 3.6–4 m to 160 m, 6 m to 800 m, 9 m to 2.5 km;
    - chance 0.95 in woody, 0.07 in herbs, 0.06 in reed, 0.02 on sand.
  - **Understorey:**
    - saplings, Amorpha and Tamarix;
    - spacing 1.5 m to 30 m, 2.4 m to 150 m;
    - chance 0.6 in woody, 0.16 in herbs, 0.1 on sand;
    - Amorpha and Tamarix mostly on sand and herb ground.
  - **Marsh:**
    - spacing 0.85 m to 25 m, 1.5 m to 220 m;
    - chance 0.85 on reed ground: 80% Phragmites, 20% Typha;
    - Typha only within 10 m of water, otherwise Phragmites;
    - a few reed patches in meadows and thickets.
  - **Herbs:**
    - spacing 0.5 m to 25 m, 1.15 m to 120 m;
    - chance 0.9 in herbs, 0.5 on sand, 0.32–0.35 under trees and in reeds, 0.08 on bare ground;
    - mixed by habitat (sand: grasses and Xanthium; meadows: all herb families).
  - **Low grass:** spacing 0.38 m to 30 m, 0.85 m to 70 m.
  - The layers end at those distances, and beyond them the canopy alone carries the view.
- **Rules for every view:**
  - nothing within 26 m of a caisson;
  - only low grass within `clear_m` of the camera, and nothing taller than the eye within `clear_tall_m`;
  - beyond 20 m, plants only within `cone_deg` of the heading.
- **The gap (b, e, f):** a narrow wedge toward the tower is kept free of trees, shrubs and reeds; for e ("all"),
  only low grass is left in it. This is a framing choice, so the tower can be seen. It is said so here and must be
  said wherever a still is used.
- **On the ground:** `still_v3.py` sets each plant on the scene's own ground by casting a ray straight down.
  - A plant whose ray meets the modelled water or a caisson first is dropped.
  - Wires, earth wires, glow and fittings are passed through: the cast is repeated from 0.6 m below the hit, up to
    80 times (under the lit span a ray can meet more than 8 of them).
  - `v3/render_log_*.json` says how many plants were kept and dropped, and what each dropped ray met.
- **Positions:** a pattern drawn from 10 m pixels, not individual plants.

### The views

Positions are in the scene's own metres (x east, y north from its origin, as `views.json`). Heading is a compass
bearing, pitch is up from level, and the lens is on a 36 mm wide sensor. The wires' 0.7 px floor is rescaled to each
lens. All six are at dawn; b, d and f also by day.

| View | Position (m) | Eye | Heading | Pitch | Lens | Where, what |
|---|---|---|---|---|---|---|
| a | 3606, 4671 | 1.6 m | 55° | 18° | 20 mm | The first still's spot, on the sand bar 150 m south-west of tower 20, looking along the span. Bare sand in the 2025 pass, so only sparse herbs near. |
| b | 3812, 4782 | 1.6 m | 253° | 30° | 16 mm | Inside the forest's edge 90 m east-north-east of tower 20, looking up at it over the reeds through a gap in the young willows (gap 11°, 3–95 m). |
| c | 3905, 5080 | 1.3 m | 10° | 10° | 24 mm | In the reeds and cattails at the channel's edge, looking along the lit span across the water to towers 21 and 22. |
| d | 3992, 5674 | 0.45 m | 17° | 62° | 14 mm | Lying on the bed under the span between towers 21 and 22, looking up at the wires through the crowns. |
| e | 4572, 5568 | 1.7 m | 345° | 4° | 16 mm | Low at the water's edge on a sand bank east of a pool, wide: the forest line across the water, Ferosplavna's lit span running off left toward tower 22 (out of frame), and Dniprovska's cut tower 24 small in the middle (gap "all" 40°, 0–10 m). |
| f | 4355, 6870 | 1.6 m | 22° | 14° | 18 mm | A meadow lane through the willows 190 m south of tower 23, under the lit span, toward the tower (gap 7°, 3–200 m). |

The cameras stand on ground (the eye height is above the scene's ground there, `camera_ground_m` in
`v3/plants/plants_<id>.json`). No coordinates or pins are drawn on any image.

### Render times

On this Mac (EEVEE, 32 samples, 1920×1080), from `v3/render_log_*.json`. Preparing a view (scatter and rays) takes
5–68 s, and each light renders in 20–45 s, well under the 2 minutes a frame aimed for. The plants cast no shadows: with
shadows on, view d took 138 s and e 421 s, and EEVEE reported "Shadow buffer full".

| View | Plants kept (dropped: met first) | Prepare | Dawn | Day |
|---|---|---|---|---|
| a | 10,852 (8: water) | 4.9 s | 21.1 s | |
| b | 18,946 (36: water) | 5.1 s | 44.5 s | 42.7 s |
| c | 43,829 (0) | 8.3 s | 20.1 s | |
| d | 65,612 (0) | 14.8 s | 39.9 s | 40.9 s |
| e | 88,383 (2: water) | 15.3 s | 30.3 s | |
| f | 56,053 (0) | 68.3 s | 38.1 s | 33.1 s |

The plants counted are those inside the camera's cone and bands. The canopy beyond about 160 m is coarse sprays
(LOD 2), and the herbs and grasses end at 120 and 70 m.

### Commands (from the project root)

```sh
S="research_notes/Under the crossing still"
B=libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d/animatic/ZNPP-last-two-lines-3D-south.blend
.venv/bin/python -I "$S/scripts/place_plants.py" "$S/scripts/views.json" "$S/v3/plants" [a b ...]     # placement
blender -b --factory-startup "$B" -P "$S/scripts/still_v3.py" -- "$S/scripts/views.json" "$S/v3/plants" "$S/v3" dawn,day b d f
blender -b --factory-startup "$B" -P "$S/scripts/still_v3.py" -- "$S/scripts/views.json" "$S/v3/plants" "$S/v3" dawn a c e
blender -b --factory-startup "$B" -P "$S/scripts/still_v3.py" -- specimens <out.png> [families]       # a sheet of the models
.venv/bin/python -I "$S/scripts/contact.py" "$S/scripts/views.json" "$S/v3" "$S/v3/contact.jpg"
```

The .blend is opened read-only and never saved, so no .blend1 is written.

### What is drawn or modelled (to be said wherever these are used)

- **The plants are modelled.** The species are from the sources, and the shapes are representative. Tree heights
  are sourced; other heights are typical, not measured.
- **Where they stand is inferred.** It is a pattern from a 10 m pass of 28 August 2025, a year before the record's
  date shown. The growth since then is not observed, beyond the sources' heights.
- **The gaps toward the towers are a framing choice.**
- **The rest is drawn or modelled, as in the 3D film:**
  - the dawn sky and sun glow are drawn;
  - the water is the film's modelled surface;
  - the towers are modelled by type at OSM's positions;
  - the bed's heights are inferred (`bed.json`).
- **The record state and the sun disagree.** The record state is that of 11 September 2026 (Ferosplavna-1 lit,
  Dniprovska cut), but the dawn sun is a mid-May sunrise, chosen to backlight the towers. The plants are drawn in
  summer leaf.

### Seen in v3

- **f works best for the shot:** dense, layered meadow (Lythrum, reed plumes, tall grasses, willows) in the lane,
  tower 23 at its end with the lit span overhead: nature grown in, the tower over it. b is the strongest "100 m
  over the trees": tower 20 above young willows and poplars. d is the closest to idea 1 (lying under the wire,
  looking up), but no tower is in it.
- **a is sparse:** the first still's spot is bare sand in the 2025 pass, so with the corrected rule only herbs grow
  there and the forest is a far line.
- **e's ground:** the low grass on the sand bank reads as tufts on dark ground.
- **The gaps:** in b, e and f the gaps toward the towers are framing choices.
- **The dawn sky** shows faint diagonal bands in places (f, top right). The first still's gradient shows something
  similar; the cause was not found.
- **Close up, the leaves are flat cards.** The poplars read as poplars now, but no plant has its own shading or
  translucency: they are emission-shaded like the rest of the film.

## v4: f on the line's axis, symmetric, with distant birds, 30 s (5 November 2026)

The user picked f and asked for it again as the 30 s shot: "the powerline shown in option f should be at the center of
the frame with the camera adjusted so that the cables are symmetrical in frame and not tilted. should feel as if the
center of attention is still the powerline tower and the cables with the nature/wildlife growing un-maintened all
around it. also add more trees closer to the base of the tower in the distance. i like the types of trees shown in
option d so perhaps use those. the composition of the final f version's nature should be somewhat symmetrical. please
render the video to the length of the "under-the-crossing". also animate birds flying in the distance to give a
broader sense of immersion."

In `v4/`: `under_the_crossing_f.mp4` (30 s, 1920×1080, 30 fps, H.264, with the soundscape
`../Speculative crossing soundscape/under_the_crossing.wav`), its first, middle and last frames (`f_v4_first.png`,
`f_v4_mid.png`, `f_v4_last.png`), and `v4.json` (camera, plants by family and origin, the caisson clearance, the
mirroring rule, the birds with their paths and sources, the render's settings and times). Storyboard material, not a
frame of the film.

### What changed and why

- **Camera, on the axis.** It stands on the vertical plane through the centres of Ferosplavna-1's towers 22 and 23,
  190 m short of tower 23 (about where f stood, 205 m off it and to one side), and looks along the span: heading
  17.04° (the bearing from 22 to 23), pitch 15° up, roll 0, an 18 mm lens, the eye 1.6 m above the meadow. It does
  not move. The tower and its wires are symmetric about the tower's axis (measured on the wire curves: the phases at
  ±7.5 m, ±11 m and ±9.5 m on both towers, the lattice ±12.2 m), so tower 23 stands on the frame's vertical centre line
  and the six lit conductors come down from the top of the frame on either side of it, like a one-point perspective.
  Tower 24 stands straight behind it, inside its lattice. Dniprovska's cut line and its tower 24 fall on the right,
  small and grey, partly behind the willows. They are left where they are.
- **The plants, mirrored.** The left of the axis is placed by the v3 rule (`place_plants.py`, from the 28 August 2025
  pass). The right is that side mirrored across the axis and jittered, so it reads as grown rather than cloned. The
  jitter moves each plant by up to 3 m (sigma 0.25 m plus 2% of its distance), scales its height by 0.88 to 1.12
  within its family's range, gives it a new rotation and variant, swaps 12% of plants to a kindred family and leaves
  5% out. **The symmetry is a framing choice.** On the right it does not follow the pass: some mirrored plants stand
  where the pass shows water, reed or sand (`v4.json`, `habitat_of_the_2025_pass_at_their_spots`).
- **A young forest round tower 23's base**, of the d trees: white willow (4–9 m) and black poplar (6.5–9.5 m), the
  heights as sourced. They stand from 23.5 m to 115 m from the caisson's centre, one about every 3.4 m. The concrete is
  22.5 m in radius, so the trees come to within 1 m of its edge. v3 kept everything 26 m from a caisson; v4 uses 23.5 m
  for every caisson. In front of the caisson, within 10 m of the axis, only the meadow grows, so its base shows. From
  10 m to 16 m off the axis there are saplings and shrubs, and the trees start beyond that. Trees out to 420 m have
  twigs and leaf sprays (LOD 1, as the mid-distance trees in d), and those within 40 m have full leaves.
  **This forest is composed, not observed**: 1,069 of its 2,306 plants (46%) stand where the pass does not show
  woody ground, as do 5,297 of the 13,211 willows and poplars that are mirrored or composed (`v4.json`).
- **Kept lower round the axis, a framing choice.** As in f, there are no trees, shrubs or reeds within 6° of the
  axis from 3 m to 150 m out. Within 20° of it, from 4 m out to the base, nothing grows taller than 1.45 m, so the
  young forest at the base shows over the meadow. The meadow plants the user liked in f stay in the foreground on both
  sides: loosestrife spikes, grass and reed plumes, and a willow at each edge of the frame.
- **Birds, drawn.** 16 birds in five groups at different distances and speeds, all in the open sky either side of the
  line. They keep at least 28 px from every wire and tower in the frame: checked frame by frame against the lines'
  projected wires and the towers' boxes, with no frame near them (`birds_v4.py check`).
  - **European bee-eaters** (heard in the soundscape's reeds layer; Vasyliuk, Mar'ianske, on the bed, 14 May 2026): a
    loose group of five on the left (1–12 s) and three on the right (16–25 s), 52–82 m off, in flurries of quick
    wingbeats between glides. Each group enters from behind the edge willows and leaves the same way.
  - **Great cormorants** (1,240 nests on six towers of these crossings in 2012, Sidorenko & Siokhin 2016; nothing
    counted since): a slow line of six, 240–480 m off, crossing the left sky from 5 s, then turning away and
    descending toward the far treeline. They are drawn far off and never at a tower, so no colony is shown or
    implied.
  - **Caspian gulls** (nested on the crossing in 2012, the same survey): one gliding a slow loop in the upper right,
    160–210 m off (6–22 s), and one far gull, 420–470 m off, from 11 s to the end.

  The birds are flat silhouettes, 3–9 px across, tinted toward the dawn haze with distance. Their shapes, sizes,
  wingbeats, speeds and paths are representative, and their paths are composed for the frame.
- **The flow runs.** The scene keys each line material's "flow time" frame by frame. Here an unkeyed twin takes over
  its links and is set to (4001 − 1) / 30 + K / 30 s at frame K, so the dashes run at the film's own pace. Everything
  else is held at frame 4001: 11 September 2026, Ferosplavna-1 connected, Dniprovska cut.
- **The light** is v3's dawn, as the user saw it in f, which fits the soundscape's May morning. The sky is v3's
  gradient and sun glow, now drawn per pixel in float with a dither of one 8-bit step. **The faint "diagonal bands"
  were not EEVEE's**: a world-only render matches the same sky computed in numpy to within 2 levels. They came from
  the colour ramp's linear interpolation, whose kinks at its stops show as faint Mach bands, and the 90° lens curves
  them across the sky so they look diagonal. v4 passes a monotone cubic through the same stops and colours (C1, level
  at both ends), which removes them. The colours between the stops differ from v3's by 1.7 levels on average, at most
  18.

### How it was rendered (EEVEE, 32 samples, 1920×1080, 30 fps: a test, as the project's rules say; the final would be 60)

A full frame with the plants takes about 20 s, so 900 frames would take 5 h. Most of that cost does not change from
frame to frame, so the shot is rendered in passes and composited (`still_v4.py`, `composite_v4.py`):

1. **The static picture, once** (13 s): everything except the moving parts, film-transparent.
2. **The moving parts, per frame**, in one animation render: the lit wires, their glow and fittings, and the birds,
   over nothing. This takes 1.4 s a frame, 21 min in all.
3. **A matte, once** (8 s): the moving wires' footprint drawn flat, with every other object (all the plants included)
   as a holdout, divided by the same footprint drawn alone. The wires are static geometry and only their shading
   moves, so this matte gives how much of each of their pixels stays in view. The birds are occluded by the static
   picture's alpha: their paths keep clear of everything that could stand behind them.
4. **The composite**, in float: the moving parts × the matte, over the static picture, over the sky. It is then
   turned to sRGB (the scene's view transform is Standard) with the dither, and piped to FFmpeg with the soundscape.

The whole run took 23 min of rendering (setup included) plus the encode, against about 5 h frame by frame.
**Checked against full renders** of frames 0, 450 and 899 (everything in one render): the mean difference is 0.012
of 255 levels. 0.05% of the pixels differ by more than 8 levels, and 63–96 pixels by more than 32 (at most 101), all
at the insulator strings where a dash passes through them. At full size the composite and the full render look the
same.

### Commands (from the project root)

```sh
S="research_notes/Under the crossing still"
B=libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d/animatic/ZNPP-last-two-lines-3D-south.blend
R=<a scratch folder for the passes>
.venv/bin/python -I "$S/scripts/place_v4.py" "$S/scripts/views_v4.json" "$S/v4/plants" f4         # placement
for m in mask static matte; do                                                                   # the passes once
  blender -b --factory-startup "$B" -P "$S/scripts/still_v4.py" -- "$S/scripts/views_v4.json" "$S/v4/plants/plants_f4.npz" "$R" $m
done
blender -b --factory-startup "$B" -P "$S/scripts/still_v4.py" -- "$S/scripts/views_v4.json" "$S/v4/plants/plants_f4.npz" "$R" anim 0:900
blender -b --factory-startup "$B" -P "$S/scripts/still_v4.py" -- "$S/scripts/views_v4.json" "$S/v4/plants/plants_f4.npz" "$R" full 0,450,899   # to check
.venv/bin/python -I "$S/scripts/birds_v4.py" check "$R/mask.npy" "$S/v4/f_v4_mid.png" "$R/birds_check.png"
.venv/bin/python -I "$S/scripts/composite_v4.py" compare "$R/full_0450.exr" "$R" 450 "$R/diff_0450.png"
.venv/bin/python -I "$S/scripts/composite_v4.py" frame "$R" 450 "$S/v4/f_v4_mid.png"                   # (0: first, 899: last)
.venv/bin/python -I "$S/scripts/composite_v4.py" video "$R" "research_notes/Speculative crossing soundscape/under_the_crossing.wav" "$S/v4/under_the_crossing_f.mp4"
.venv/bin/python -I "$S/scripts/v4_json.py" "$S/scripts/views_v4.json" "$S/v4/plants/plants_f4.json" "$R" "$R/birds_check.json" "$R/diff_0450.json" "$S/v4/under_the_crossing_f_encode.json" "$S/v4/v4.json"
```

`still_v4.py` uses v3's functions and models (`still_v3.py`, `plants.py`) unchanged, so the v3 commands above still
run as before. The .blend is opened read-only and never saved, so no .blend1 is written.

### What is drawn or modelled (to be said wherever v4 is used)

- **Modelled:** the plants, with representative shapes; species from the sources; tree heights sourced, other
  heights typical.
- **Composed, not observed:**
  - the right of the frame (the left mirrored);
  - the young forest round tower 23;
  - the lane and the lower growth along the axis.
- **Drawn:** the birds; the dawn sky, sun glow and warmed haze; the flow dashes (the film's convention).
- **As in the 3D film:** the towers are modelled by type at OSM's positions, and the bed's heights are inferred.
- **The sun and the record disagree:** a mid-May sunrise over the record state of 11 September 2026.
- **No sound effects:** the birds on screen are not the birds heard. The soundscape is its own montage, said to be
  one, and has no sound of wings.

### Seen in v4

- Tower 23 is the centre: the lit wires converge on it from the top, and it rises from a low band of young willows and
  poplars round its caisson.
- At 80–300 m those trees are only about 20–60 px tall, so they read as a young forest line rather than as trees in d's
  detail. A closer camera would make them larger, but would also change f's framing.
- The middle of the meadow is now open and low (the lower-growth wedge). That reads as a clearing, but f's dense
  middle ground is gone. The plumes and willows frame it at the sides.
- The birds are subtle: dark specks, with a light grey gull, and their wingbeats show only on a large screen.
- The plants are still. There is no wind.

## v5: back to v3's f by day, 30 s, and the waterline reprise (5 November 2026)

The user, after seeing v4: "actually seeing the f video i prefer the composition of the original "f day" still frame
shown in the composite/collage image. please re-render the video so it is like the origial "f day" proposal. key
changes: should be during the day and also render that seperate short (option 2.) where a shot of the "f day" is shown
wit the water line appearing as a reprise after the cards describe what could happen if the water level is restored."

In `v5/` (v4 kept as it was):
- `under_the_crossing_f_day.mp4`: 30 s, 1920×1080, 30 fps, with the soundscape
  `../Speculative crossing soundscape/under_the_crossing.wav`. Its first, middle and last frames are
  `f_day_v5_first.png`, `f_day_v5_mid.png` and `f_day_v5_last.png`.
- `waterline_reprise.mp4`: 9 s, with `waterline_reprise.wav` and `waterline_reprise_sound.json`. Its stills are
  `waterline_reprise_plain.png`, `waterline_reprise_fading.png`, `waterline_reprise_held.png`, and
  `waterline_reprise_held_detail.png` (the caisson and the meadow, enlarged 2×).
- `v5.json`: the camera, plants, birds, render method and times, the datum conversion, the level in scene units, what
  the line is drawn on, and what is drawn or inferred.

Storyboard material, not frames of the film.

### The 30 s shot

- **Exactly v3's f.** It uses v3's camera from `scripts/views.json`: (4355, 6870), heading 22°, pitch 14°, an 18 mm
  lens, the eye 1.6 m above ground at 9.25 m. It uses v3's plants unchanged (`v3/plants/plants_f.npz`, 56,053 plants).
  There is no mirroring, no base forest and no lower-growth wedge.
- **The film's day light.** That means its fixed sun, its haze and its overcast world, one flat colour (EEVEE's world
  render: sRGB 207, 213, 218).
- **The first frame matches `v3/f_day.png`.** The mean difference is 1.1 levels, the dither's noise, and the largest
  is 20. 150 px differ by more than 8, at the flow dashes and plant edges.
  - The first attempt was 4 levels off on every plant. The cause was the plants object's name: v4 called it
    "plants f4", and the name seeds each plant's Object Info random brightness. It is now named after the view,
    "plants f" as in v3 (`still_v4.py`, still "plants f4" for v4).
- **The flow dashes run**, and the rest stays at frame 4001's state, as in v4.
- **The birds** are v4's species and flight. Their paths are composed again for this framing (`scripts/birds_v5.py`),
  all in the open sky right of the span: 14 birds in five groups.
  - Bee-eaters at about 1–11 s and again at 16–24 s.
  - A Caspian gull wheeling at 160–210 m (4–19 s) and a far gull from 13 s.
  - Five cormorants far off (280–560 m) from 7 s, turning away.
  - The paths were checked frame by frame against this view's wires and towers (28 px margin): no frame is near them.
  - They are tinted toward the day haze with distance.

### The reprise (`waterline-reprise`)

The same view is held 9 s.
- **0–2 s:** plain.
- **2–4 s:** a blue line, about 7 px wide, fades in, with a small label in the film's style: white capitals,
  Helvetica Neue 16 px, on a black box at half opacity, bottom left, clear of the tower and wires. A short stroke of the
  line's blue comes before the text, as its key. It reads "PROPOSED LEVEL · 12.7 M · VYSHNEVSKYI & SHEVCHUK 2024 ·
  THE BED'S HEIGHTS INFERRED".
- **Then it holds.**

The flow keeps running. The picture's moving parts are the 30 s shot's frames 630–899, which hold only the far
cormorants and gull. Those were checked to stay clear of the line.

- **The level.** 12.7 m Baltic is the dead-volume level that Vyshnevskyi & Shevchuk (2024, p. 286) propose for a
  temporary dam. The reports also give it as IAEA Update 162's figure. The config cites Update 163 for a measured
  12.7 m on 8 June 2023 (Update 162: 14.03 m on 7 June). This was not checked again here.
- **The datum.** The scene's z is FABDEM's metres above EGM2008. Baltic levels are raised by +0.4 m
  (`config/conductive-seam.yaml` `crossing3d.bed` `baltic_m`, as the bed's levels are). So the line is at **13.1 m in
  scene units**.
- **The eye is under the level.** The ground at the camera is 9.25 m and the eye 10.85 m, so the eye is **2.25 m below
  the proposed level**: at that level this view would be under water. The camera is not moved. So the level's plane
  lies above the eye, and the line falls above the horizon, on whatever stands taller than it:
  - a clean line round the foot of tower 23's caisson, about 0.5 m above the ground there;
  - a broken line of short dashes across the stems of the reeds, grasses and young willows near the horizon (the
    plane seen from below);
  - patches across the leaves of the near willow crown at the top left, where they lie at the level.
  - It is not on the tower or the wires, which stand above it on the caisson.
- **How it is drawn: a contour, not water.** `still_v5.py contour` draws every surface flat black except a band where
  |world z − 13.1| < h.
  - h = the eye distance × 36 mm / 18 mm / 1920 px × 3.5 px × max(sin(slope), 0.15), at least 1 mm. That makes it
    about 7 px wide on screen.
  - The 0.15 floor keeps a leaf or flat ground lying at the level to a thin band rather than lighting it whole. A first
    try without it lit whole willow leaves, which read like glints.
  - The band's red channel is the matte. The line is a saturated mid blue, sRGB (40, 110, 230), opaque, over a 1 px
    darker edge, sRGB (12, 34, 80), so it reads on pale ground. It is laid on the static picture, under the moving
    wires (nearer wires pass in front of it).
  - The user asked for it "thicker and blue so it stands out" (5 November 2026). The first version was white, about
    2 px wide, at 0.9, and hard to see. Blue reads as water; red is the film's colour for a traced line.
  - Across the reed stems it stays a row of dashes: the stems are thin, and the line is only where they cross the
    level.
  - No surface, fill or tint is drawn.
- **Inferred × proposed.** The level is a proposal. The bed's heights under the meadow are inferred (FABDEM shows the
  old reservoir as flat water; the bed's relief is the waterline method's, `scene3d/bed.py`), and the plants it
  crosses are modelled.
- **The sound** is a stretch of the shot's own soundscape (`scripts/reprise_sound.py`): seconds 13.5–22.5 of its 30 s,
  with only two of its parts.
  - The line: Ferosplavna-1, synthesized as `mix.py` does (seed 330, the same window).
  - The near thrush nightingale: iNat sound 1950271, Oleksii Vasyliuk, Mar'ianske, 14 May 2026, CC BY, recording
    seconds 14.5–23.5.
  - Both are made by `mix.py`'s own functions at its levels and with its master gain. `mix.py` was rerun to read the
    gain, and the rerun reproduces `under_the_crossing.wav` bit for bit.
  - Faded in over 1 s and out over 1.5 s, and limited at −1 dBFS. No new recordings; never pitched, looped or
    stretched.

### How it was rendered (EEVEE, 32 samples, 1920×1080, 30 fps: a test)

- The passes and their compositing are v4's, run by `still_v5.py`, with the flat day sky in `composite_v5.py`.
- Render times:
  - the static picture, 22 s;
  - the matte, 6 s;
  - the moving parts, 1.7 s a frame (26 min for 900, partly while other renders ran);
  - the waterline pass, under 1 s;
  - each full check frame, 27–35 s.
- The composite against full renders of frames 0, 450 and 899 differs by a mean of 0.016 levels. The largest
  difference is 111, at a few insulator strings, as in v4. Encoding took 2 min for the 30 s shot and 50 s for the
  reprise.

### Commands (from the project root)

```sh
B=libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d/animatic/ZNPP-last-two-lines-3D-south.blend
S="research_notes/Under the crossing still/scripts"; R=<scratch dir>
for m in mask static matte contour world "full 0,450,899" "anim 0:900"; do      # (bash: $m split into mode and args)
  blender -b --factory-startup "$B" -P "$S/still_v5.py" -- "$S/views_v5.json" "$S/../v3/plants/plants_f.npz" "$R" $m
done
.venv/bin/python -I "$S/birds_v5.py" check "$R/mask.npy" "research_notes/Under the crossing still/v3/f_day.png" "$R/birds_check.png"
.venv/bin/python -I "$S/composite_v5.py" video "$R" "research_notes/Speculative crossing soundscape/under_the_crossing.wav" \
  "research_notes/Under the crossing still/v5/under_the_crossing_f_day.mp4"
.venv/bin/python -I "$S/reprise_sound.py" "research_notes/Speculative crossing soundscape" \
  "research_notes/Line sound proxies/raw/xc/XC1016141/XC1016141.mp3" "$R" "research_notes/Under the crossing still/v5/waterline_reprise.wav" \
  "research_notes/Under the crossing still/v5/waterline_reprise_sound.json"
.venv/bin/python -I "$S/composite_v5.py" reprise "$R" "research_notes/Under the crossing still/v5/waterline_reprise.wav" \
  "research_notes/Under the crossing still/v5/waterline_reprise.mp4" 630 "research_notes/Under the crossing still/v5/waterline_reprise"
.venv/bin/python -I "$S/v5_json.py" "$R" "research_notes/Under the crossing still/v5/v5.json"
```

The south scene file is opened read-only and never saved.

### What is drawn or modelled (to be said wherever v5 is used)

- **Modelled:** the plants (placed by v3's rule from the 28 August 2025 pass, the lane toward the tower kept open) and
  the towers, wires and fittings (positions OpenStreetMap's, shapes representative).
- **A drawing convention:** the flow dashes, at the record's state of 11 September 2026.
- **Drawn:** the birds (their paths composed).
- **A montage:** the sound; the line in it is synthesized.
- **The waterline** is a proposed level drawn on inferred heights and modelled plants, as a line, never as water. In
  the reprise, the eye is 2.25 m under that level.
