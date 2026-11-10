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

## v6: the drowning (6 November 2026)

Decided with the user (6 November 2026): a new version of the reprise, "the drowning": the same camera and the same
overcast day, with months compressed into seconds as the proposed level rises to its height. `v5/waterline_reprise.mp4`
is kept as it was.

In `v6/`:
- `drowning.mp4`: 15 s, 1920×1080, 30 fps, H.264 (CRF 16), with `drowning.wav` and `drowning_sound.json`.
- Stills: `drowning_first.png`, `drowning_rising.png` (4.3 s), `drowning_lens.png` (5.0 s, just before the lens
  crossing), `drowning_mid.png` (7.5 s, under) and `drowning_last.png`.
- `v6.json`: the level, the timeline, how the water is drawn, the passes and times, and what is drawn or inferred.
- `RESUME.md`: how to run or resume the render and the steps after it.

Storyboard material, not frames of the film. In `config/storyboard.yaml` it is the shot `drowning` (draft).

### The shot

- **0–1 s:** v5's view f by day, with the reprise's blue line and label held. So the shot can follow the reprise
  or replace it.
- **1–11 s:** a flat water surface rises from 9.0 m to 13.1 m in the scene's heights (the proposed 12.7 m Baltic,
  +0.4 m to EGM2008, as in v5). The rise is eased: it speeds up over the first 20%, runs steady, and slows over the
  last 40%.
  - 9.0 m is just under the lowest ground the view shows: the lane, 9.25 m at the camera. The channel and pools of the
    scene's own water are not in this frame.
  - The water shows first between the stems, at about 2.5 s. It climbs the plants, and the shortest go under first:
    the herbs, then the grasses and reeds. The willows' crowns stay above it. No plant is moved, toppled or hidden.
  - The blue line fades as the water reaches it.
- **5.2 s, the lens:** the level passes the eye (10.85 m). Over half a second the waterline sweeps up across the frame,
  as over a lens port. This is a drawn meniscus.
- **Then under the water:** the eye ends 2.25 m below the surface, held from 11 s to the end.
  - Below the surface, the drowned meadow fades into murk.
  - Above it, the tower, the lit wires and the willow crowns waver faintly through the surface.
- **The label** stays throughout, in v5's style: "PROPOSED LEVEL · 12.7 M · VYSHNEVSKYI & SHEVCHUK 2024 · REACHED OVER
  MONTHS · THE BED'S HEIGHTS INFERRED · DRAWN". No duration or date is shown. A rough estimate, in `v6.json` only and
  not a source, is about 3 months for 11.4 km³ at the Dnipro's mean flow.

### How the water is drawn (`scripts/composite_v6.py`)

The water is not a Blender object. It is drawn per frame in numpy from passes rendered once. Seen from a still camera,
a flat surface at height h covers exactly the pixels whose visible surface lies below h. From above, a ray going down
meets every point above h before it crosses the plane, and from below it is the same the other way round. So the
order of water and plants follows from the scene's own heights.

- **The passes** (`scripts/still_v6.py`, EEVEE, 3840×2160):
  - v5's static picture (32 samples);
  - every pixel's surface height and distance from the eye, one exact sample (1 sample, the pixel filter off,
    32-bit).

  The picture is drawn at 3840×2160 and reduced to 1080p, so the water's edge against the grass comes from 4 samples
  a pixel. The moving wires, the far birds (v5's moving pass, frames 450–899), the wires' matte and the blue line are
  v5's own passes, unchanged.
- **From above:** the look is the scene's own water material: its unlit body colour (linear 0.0176, 0.0252, 0.0176)
  under a glossy reflection of tint 0.8, mixed by half its Fresnel at IOR 1.333.
  - The reflection is traced in screen space through the picture's own surfaces. Where it leaves the picture, it shows
    the overcast sky.
  - The ripples are drawn. They drift south-west with the current, roughly toward the camera.
  - The ground shows through very shallow water.
- **From below, a drawn convention:**
  - The surfaces under the water are darkened with depth and absorbed into a green-brown murk along their distance.
  - The picture above the surface is displaced by the ripples' slopes and absorbed along the ray's path in the water.
  - Snell's window is not drawn. From 2.25 m down, a real eye looking 14° up would see the surface as a mirror almost
    everywhere but overhead.
  - The water is drawn clearer than the reservoir's was, so the tower can be seen.
- **Floating leaves and twigs** were optional and are not drawn.

### Sound (`scripts/drowning_sound_v6.py`)

The sound comes from the soundscape's own material only. `mix.py`'s functions cut, high-pass, fade, level and pan it
exactly as in the 30 s mix, with that mix's master gain. The rerun of `mix.py` reproduces `under_the_crossing.wav`
bit for bit.

- The chorus drops out as the drawn water reaches each habitat:
  - the reed birds (great reed warbler, coot, bee-eater; iNat 1950258) are gone by 3.6 s;
  - the marsh frog (iNat 997953, near Kryvyi Rih, not the bed: a guess) by 4.4 s;
  - the near thrush nightingale (iNat 1950271) at the lens crossing, 5.3 s.
- The synthesized Ferosplavna-1 line (seed 330) runs throughout. From the lens crossing it is low-passed at 380 Hz and
  6 dB quieter. That muffling is drawn.
- No new recordings. Nothing is pitched, looped or stretched.
- Credit: Oleksii Vasyliuk (CC BY), W.D. Keeper (CC BY), via iNaturalist; the line synthesized.

### Render

- The passes took 15 s (static) and 2 s (heights), plus about 10 s each to set up.
- The 450 frames took 0.7–2.2 s each, with three workers, in 4.4 min (`render.log`). The encode took 12 s.
- Test frames were looked at first, and the water under the surface was then drawn a little clearer so the tower
  reads.

### Commands (from the project root)

```sh
B=libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d/animatic/ZNPP-last-two-lines-3D-south.blend
V="research_notes/Under the crossing still"; R=<scratch dir>; V5R=<v5's render dir>; F=<frames dir>
for m in pos static; do blender -b --factory-startup "$B" -P "$V/v6/scripts/still_v6.py" -- "$V/scripts/views_v5.json" "$V/v3/plants/plants_f.npz" "$R" $m 2; done
.venv/bin/python -I "$V/v6/scripts/composite_v6.py" frames "$R" "$V5R" "$F"          # or v6/scripts/run_v6.sh, detached
.venv/bin/python -I "$V/v6/scripts/drowning_sound_v6.py" "research_notes/Speculative crossing soundscape" "$V/v6/drowning.wav" "$V/v6/drowning_sound.json"
.venv/bin/python -I "$V/v6/scripts/composite_v6.py" video "$F" "$V/v6/drowning.wav" "$V/v6/drowning.mp4"
.venv/bin/python -I "$V/v6/scripts/v6_json.py" "$R" "$V/v6/v6.json"
```

The south scene file is opened read-only and never saved.

### What is drawn or inferred (to be said wherever v6 is used)

- **Speculative and drawn:** the water, its rise, ripples, reflections and murk, the lens crossing, and the view from
  under the surface.
- **The level is a proposal** (Vyshnevskyi & Shevchuk 2024, p. 286). The bed's heights it rises through are inferred.
- **Modelled:** the plants and towers, as in v5.
- **A drawing convention:** the flow dashes.
- **A montage:** the sound. The line in it is synthesized.
- **Time is compressed:** months are drawn in 10 s.

## v7: the drowning, second pass (6 November 2026)

The user liked v6 and asked for a second pass, to replace waterline-reprise in the cut, directly after
under-the-crossing (`v5/under_the_crossing_f_day.mp4`, in 0, out 30). v6 is kept as it was.

In `v7/`:
- `drowning.mp4`: 15 s, 1920×1080, 30 fps, with `drowning.wav` and `drowning_sound.json`.
- Stills: `drowning_first.png`, `drowning_rising.png`, `drowning_near_the_lens.png`, `drowning_lens.png`,
  `drowning_under.png` and `drowning_last.png`.
- The join checks: `join_check.json`, `join_test.mp4`, `join_contact.png` and `join_diff_899_to_0.png`.
- `alt/`: a continuous pair (below).
- `v7.json`; `RESUME.md`.

In `config/storyboard.yaml` the source `drowning` now points to v7.

### What changed

- **No line and no caption.** There is no blue line, no label or key, and no opening second of the reprise.
- **The statement, kept off the picture.** It is in `v7.json` and here: "PROPOSED LEVEL · 12.7 M · VYSHNEVSKYI &
  SHEVCHUK 2024 · REACHED OVER MONTHS · THE BED'S HEIGHTS INFERRED · DRAWN", and the view under the water and its silt
  are a drawn convention. It has to be said elsewhere in the film (the shot's caption field, a card or the credits:
  the user decides), as the shot's `needs` says.
- **Seamless out of under-the-crossing.**
  - Frame 0 is the frame after the clip's last. Its moving pass (the lit wires' flow and the drawn birds) was
    rendered on by v5's own `still_v5.py`, unchanged, as frames 900–1349 of the same timeline. The dither's seed runs
    on as well.
  - Where there is no water, the picture is v5's 1080p plate itself; the water is added as a difference from v6's 2×
    plate. A few far pixels already lie under the starting level, and they take the water over the first 0.8 s.
  - Checked: v5's frame 899 against v7's frame 0 differs by a mean of 1.09 levels, and 5,872 pixels by more than 32.
    That is the same as one frame's step anywhere in the clip: v5's 898 to 899 is 1.07 and 5,345, and v7's 0 to 1 is
    1.10 and 5,953. The difference image shows only the flow dashes and a far bird.
  - `join_test.mp4` holds under-the-crossing's last 3 s and the drowning's first 3 s; the frames round the cut are in
    `join_contact.png`.
- **The rise starts at once.** It runs 0–10 s: water between the stems from about 1.5 s, the lens at 4.2 s, held
  under from 10 s to 15 s.
- **Under the water, a silty bottom (a drawn convention, to make plain that the plants die when the water returns):**
  - brown-green suspended silt, with a shorter absorption toward what lies under the surface;
  - darker toward the bottom;
  - the drowned plants dulled, darkened by up to half and greyed toward a silt colour the longer they are under. A
    pixel's time under counts from when the drawn level reached its height, in the shot's compressed time.

  The tower and the lit wires stay faintly readable through the surface. The ripples' brightness on the underside,
  which read as clouds, is down from 0.16 to 0.05.

### Sound (`scripts/drowning_sound_v7.py`)

- **What plays at under-the-crossing's end (measured):** its birds are gone by 27.5 s. The line alone then fades to
  silence over the last 2.5 s (`mix.py`'s LINE_OUT), so the clip ends in digital silence.
- **The decision:** the chorus can't drop out in the drowning, because it has already gone. So the drowning keeps that
  state: the line alone, muffled once the lens is under. Bringing birds back would be a jump in content, and would
  change under-the-crossing's own end.
- **How the line goes on:** `mix.py` is run 45 s long (TOTAL = 45, nothing else changed), and seconds 30–45 are the
  soundscape going on past its end.
- **`drowning.wav`, for the cut as it stands:**
  - It rises from silence over 2.5 s (the clip's fade mirrored). There is no jump in level at the cut, but the hum
    dips to nothing across it.
  - From the lens it is low-passed at 380 Hz, 3 dB under the open line: about −28 dBFS RMS, against about −35 in v6.
- **`alt/`, the hum unbroken through the cut:** `under_the_crossing_f_day_continuous.mp4` (v5's picture copied, its
  sound the 45 s run's first 30 s with no fade at the end) with `drowning_continuous.mp4`. The join is
  sample-continuous: `join_test_continuous.mp4` stays at −23 dBFS through the cut.
  - The line in it is a new draw of the same synthesis, since its noise is drawn for the run's length. The birds are
    the same samples. The first 27 s differ from the original by −22 dBFS RMS.
  - Using it means replacing under-the-crossing's sound in the cut. That is the user's call.
- No new recordings. Nothing is pitched, looped or stretched. The line is synthesized and its muffling drawn.

### Render

- The moving pass (Blender, `scripts/run_anim_v7.sh`, detached) took 9.5 min for 450 frames.
- The frames (`scripts/run_v7.sh`, three numpy workers) took 5 min. The 333 frames from the lens on were then drawn
  again in 6 min, with the water above the eye a little clearer (absorption up through the surface 4.8, 5.0, 3.6 m,
  from 3.4, 3.7, 2.5) so the tower stays readable.
- Each encode took about 19 s.

### Commands (from the project root)

```sh
V="research_notes/Under the crossing still"; SP=<scratch>      # R, V5 and ANIM as in v7/RESUME.md
nohup bash "$V/v7/scripts/run_anim_v7.sh" > "$V/v7/render_anim.log" 2>&1 &     # moving parts 900-1349
nohup bash "$V/v7/scripts/run_v7.sh" > "$V/v7/render.log" 2>&1 &               # frames (waits for the above)
.venv/bin/python -I "$V/v7/scripts/drowning_sound_v7.py" "research_notes/Speculative crossing soundscape" \
  "research_notes/Line sound proxies/raw/xc/XC1016141/XC1016141.mp3" "$V/v7" $SP/v7/sound
.venv/bin/python -I "$V/v7/scripts/composite_v7.py" video $SP/v7/frames "$V/v7/drowning.wav" "$V/v7/drowning.mp4"
.venv/bin/python -I "$V/v7/scripts/check_join_v7.py" $SP/proto/v5 $SP/v7/frames "$V/v7"
.venv/bin/python -I "$V/v7/scripts/v7_json.py" "$V/v7/v7.json"
```

## v8: the drowning, the plants dying (8 November 2026)

The user, after v7: "for the drawing at 8:05, the "drowning", i want to do antoher pass where the plants and stuff die
off as the water rises so at the end of the animation it will only show the tower and the powerlines in the
background instead of just the water level rising without the nature doing anything." Asked where the eye ends, the
user chose: stay put, end under the water. v7 (and v6, v5) are kept as they were.

In `v8/`:
- `drowning.mp4`: 15 s, 1920×1080, 30 fps, with `drowning.wav` (v7's, unchanged).
- `alt/drowning_continuous.mp4` with `alt/drowning_continuous.wav` (v7's): to follow
  `../v7/alt/under_the_crossing_f_day_continuous.mp4`.
- Stills: `drowning_first.png` (0 s), `drowning_dying.png` (2.5 s), `drowning_lens.png` (4.2 s),
  `drowning_under_dying.png` (5.5 s), `drowning_under_clearing.png` (8 s), `drowning_last.png` (15 s).
- `contact_sheet.png`: a frame every second.
- The join checks: `join_check.json`, `join_test.mp4`, `join_contact.png`, `join_diff_899_to_0.png`.
- `v8.json`; `RESUME.md`; `scripts/` as run.

Not in the storyboard yet.

### What changed

- **The camera is v7's**, fixed. The water, its rise, the lens crossing and the murk are v7's.
- **The plants die as the water reaches them.** Each plant starts when the drawn level reaches its base (its roots
  drowned), in the shot's compressed time. Its colour turns at once; the rest follows its kind's pace:
  - herbs and grasses first: they brown, wilt, slump and settle into the bed;
  - reeds: they brown, lose their blades, lean, break and fall, and settle;
  - shrubs and saplings next;
  - willows and poplars last: the leaves turn yellow-brown and drop, the finer twigs go, the branches stand bare,
    then the trunks lean over and settle into the bed.
  - The crowns above the surface die with their roots, seen wavering through it.
- **In view (within 60 m),** the herbs are gone by 5.4–7.7 s, the reeds by 6.9–9.4 s, the shrubs by 8.0–10.7 s and
  the trees by 9.6–12.6 s. From about 9.5 s the view reads clear, because the last stages happen in the murk.
- **The end:** murky water, the tower and the lit wires wavering through the surface, and a dark floor.
- 642 far trees on ground above the proposed level (600 m and more off) are left alive. They are not seen at the end.
- **No caption on the picture**, as v7. The statement, to be said elsewhere: "PROPOSED LEVEL · 12.7 M · VYSHNEVSKYI &
  SHEVCHUK 2024 · THE PLANTS' DYING COMPRESSED FROM YEARS · THE BED'S HEIGHTS INFERRED · DRAWN".

### How it is made

- **Why per frame.** The plants are dense and layered. Removing them per pixel against one plate without plants
  would also remove the plants behind them. So the plants change in Blender, frame by frame, and v7's compositor draws
  its water on each frame's own passes.
- **`scripts/dieoff_v8.py`** (plain numpy) gives each plant, per frame, its fall, slump, settling and four values:
  colour, leaves lost, twigs lost and the rest dissolved. Each kind has its own lag, pace and deadline. A plant
  reached late dies faster. Plants within 14 m of the eye fall away from it. Each plant's lag and pace vary a little.
- **`scripts/still_v8.py`** renders the passes per frame in the south scene, opened read-only and never saved:
  - v3's models and placement and v5's camera, unchanged;
  - each leaf, blade, card and stem gets one random number, and each stem a thickness order, as face attributes; the
    models' geometry and colours are untouched;
  - the plant material reads the four values as instancer attributes; losses are a transparency;
  - per frame: the plate (2x until frame 139, then 1x), the heights and distances (2x), and every fifth frame the lit
    wires' matte (linear between), so dying plants uncover the wires behind them.
- **`scripts/composite_v8.py`** imports v7's compositor unchanged and gives it each frame's passes. Where nothing has
  changed, the picture is v5's own plate, as in v7.
- **Checked:** frame 0's plate against v6's static plate (23 of 8.3 million values over 0.01); v8's frames 0 and 24
  are v7's exactly; v5's frame 899 to v8's frame 0 differs as v7's did (mean 1.09 levels, 5,872 pixels over 32).
  No flicker was found: the largest step is the lens crossing.
- **Under the water,** from 10.5 to 13.5 s the silt is drawn settling a little (longer absorption toward the bottom),
  and the bed is greyed further toward silt. This changed little: the bed stays a dark floor.

### Render

- The passes: 378 frames in 2 h 13 min (EEVEE, Blender 5.2.2, headless). The 2x plate took 18.5 s, the 1x plate
  14.3 s, the heights 1.3 s and each of the 77 mattes 20 s.
- The 450 frames: three numpy workers, 7 min. Each encode took about 15 s.
- A first timing cleared the view by 8.5 s, and a second left the plants green until the lens went under. The third,
  rendered here, turns them as the water reaches them.

### Sound

v7's `drowning.wav` and `alt/drowning_continuous.wav`, copied unchanged (same 15 s, same lens crossing). The dying has
no sound of its own: no sound effects.

### Commands (from the project root)

```sh
V="research_notes/Under the crossing still"; SP=<scratch>      # PD, R, V5, ANIM as in v8/RESUME.md
blender -b --factory-startup "$B" -P "$V/v8/scripts/still_v8.py" -- "$V/scripts/views_v5.json" "$V/v3/plants/plants_f.npz" $PD prep
nohup bash "$V/v8/scripts/run_v8.sh" > "$V/v8/render.log" 2>&1 &              # passes, then frames
.venv/bin/python -I "$V/v8/scripts/composite_v8.py" video $SP/v8/frames "$V/v8/drowning.wav" "$V/v8/drowning.mp4"
.venv/bin/python -I "$V/v8/scripts/check_join_v8.py" $SP/v8/in/v5 $SP/v8/frames "$V/v8" $SP/v7/frames
.venv/bin/python -I "$V/v8/scripts/v8_json.py" "$V/v8/v8.json" $PD
```

### What is drawn or inferred (to be said wherever v8 is used)

- **Speculative and drawn:** the water, its rise, ripples and murk, the lens crossing, the view from under the
  surface, and the plants' dying, its order and its pace.
- **Time is compressed from years.** As general knowledge, to be checked against a source before the film says it:
  herbs under water die in weeks, flooded willows over one to a few growing seasons, and drowned trunks often stand
  for years or decades. The trunks' disappearance is a drawing simplification, so the end can hold on the tower.
- **The level is a proposal** (Vyshnevskyi & Shevchuk 2024, p. 286). The bed's heights are inferred.
- **Modelled:** the plants and towers, as in v5. **A drawing convention:** the flow dashes.
- **The sound** is v7's montage; the line in it is synthesized.

### Seen in v8

- The plants turn while the water rises, and the willow crowns die above the surface as their roots drown.
- The view is clear from about 9.5 s, so the empty hold is about 5.5 s. That is longer than aimed for. Trim the
  out to about 12.5 s, or slow the trees and render again (about 2.3 h).
- The dying colours are fairly even: the willows go one ochre.
- The bed is barely seen under the water.

## v9: the drowning, the water already back (8 November 2026)

The user, after v8: "instead of the water rising from the bottom up i want the start of v9 to already have the water
at the full height of the river. i want this since right after under-the-crossing this v9 will play and it will be a
dramatic cut to the water already fully back." Also: less murk, so the two lines and their towers are a bit more
visible; the camera where it is; no plant physics: "all the very little plants to be gone, a few of the bigger plants
to remain with no leaves, just the stems, and the trees to remain but without any leaves and only the biggest,
strongest branches remaining (to signify that they are dead but still standing)"; and "a bird or two perched near the
top of the tallest dead tree branches so that even though the camera is under water we can tell that the top of the
tree is not". v8, v7 (and v6, v5) are kept as they were.

In `v9/`:
- `drowning.mp4`: 15 s, 1920×1080, 30 fps, with `drowning.wav` (`drowning_sound.json`).
- Stills: `drowning_first.png` (0 s), `drowning_wings.png` (7 s, the wings held out), `drowning_last.png` (15 s);
  `contact_sheet.png`, a frame every second.
- `v9.json`; `scripts/` as run.

Not in the storyboard yet.

### The shot

- **A cut straight to under the water.** The level is the proposed 13.1 m (12.7 m Baltic) from the first frame: no
  rise, no waterline over the lens. The eye is v7's (10.85 m), 2.25 m under the surface for the whole shot.
- **The plants, dead and still** (`scripts/dead_v9.py`, no physics):
  - the herbs and grasses (27,499) gone;
  - 270 of the 2,216 shrubs and 26 of the 1,204 reeds stand as bare stems: a random pick among the taller ones;
  - all 25,134 trees stand bare. Every leaf is gone, and only the thickest branches are kept: the thinnest 72% of the
    stems are dropped, 85% for the trees within 15 m, whose models have far more fine stems. Trunks rising from the
    ground are always kept;
  - all in v8's dead grey-brown, upright as they grew; under the surface they are greyed toward silt (under for years).
- **The two cormorants** (`scripts/birds_v9.py`) stand on the two tallest dead tree tops in view, 5 m above the
  surface, 33 m and 30 m from the eye, left of the 750 kV tower. Each is about 20 px tall at 1080p:
  - bird A, on a poplar (top 18.6 m), turns its head in jerks;
  - bird B, on a willow (top 18.2 m), turns its head, opens its wings at 4 s, holds them out to dry with two slow
    shakes, and folds them at 10.6–11.4 s.
  They are laid over the picture above the surface, so they waver through it with the treetops and the towers.
- **Less murk and a calmer surface** (drawn, values in `v9.json`):
  - the absorption up through the surface is about twice v7's (10 m, was 5 m), so the towers and the lit wires read;
  - the absorption toward what lies under the surface is twice v7's too (3.4 m, was 1.7 m), so the near dead trunks
    show as dark shapes;
  - the murk a little lighter;
  - the sway through the surface is 3 px (was 9 px), the short ripples' slope halved, and the blur 0.8 px (was 1.2).
- **No caption on the picture**, as v7 and v8. The statement, to be said elsewhere: "PROPOSED LEVEL · 12.7 M ·
  VYSHNEVSKYI & SHEVCHUK 2024 · THE TREES DEAD AND STANDING, THE BIRDS AND THE BED'S HEIGHTS DRAWN OR INFERRED ·
  DRAWN".

### How it is made

- **`scripts/still_v9.py`** renders the passes once in the south scene, opened read-only and never saved: v8's
  `still_v8.py` exec'd without its main (v3's models and placement, v5's camera, the losses as instancer attributes),
  every loss binary since nothing moves. Its passes: the plate (2x), heights and distances (2x), the lit wires' matte
  (1x). Its `perch` mode finds the highest points of the trees' kept stems, the birds' footing.
- **`scripts/composite_v9.py`** imports v7's compositor unchanged and draws only its under-the-surface view, at the
  fixed level, on v9's passes. The moving parts are v7's (under-the-crossing's moving pass run on, frames 900–1349), so
  the wires' flow continues from the shot before.
- **A fix:** in the picture seen up through the surface, what lies under the surface is now filled from round it. In
  v7 and v8 the stems near the eye showed a second time beside themselves, wavering, as pale hairs along them.
- **Birds:** ellipsoids (body, neck, head, white cheek, bill, tail, feet; two panels a wing) ray-traced in numpy
  through v7's camera at 16 samples a pixel, lit by the overcast sky, hidden where the scene's surfaces are nearer.

### Render

- The passes: 43 s (EEVEE, Blender 5.2.2, headless): the 2x plate 20 s, the heights 1.7 s, the matte 21 s.
- The 450 frames: three numpy workers, 5 min 20 s (2.1 s a frame). The encode took 12 s.
- Checked: no flicker (the largest step between frames, 0.61 levels, is no larger than the median, 0.57: the ripples).

### Sound (`scripts/drowning_sound_v9.py`)

The same 15 s as v7 (the soundscape run 45 s long, seconds 30–45: the synthesized line alone), muffled from the first
sample at v7's muffled level (low-passed at 380 Hz, 3 dB under the open line). In the cut, under-the-crossing plays
with its hum run on to its last sample (`v7/alt/under_the_crossing_continuous.wav`), so the line goes on from that
sample, muffled at once: the cut is heard as the hum closing over, with no gap. No sound effects for the birds.

### Commands (from the project root)

```sh
V="research_notes/Under the crossing still"; SP=<scratch>; PD=$SP/v9/render
blender -b --factory-startup "$B" -P "$V/v9/scripts/still_v9.py" -- "$V/scripts/views_v5.json" "$V/v3/plants/plants_f.npz" \
  $SP/v8/render/plants_laid.npz $PD preview 0.72                                  # the dead plants alone, no water
blender ... still_v9.py ... $PD perch 109,101                                     # the birds' footing
nohup bash "$V/v9/scripts/run_v9.sh" > "$V/v9/render.log" 2>&1 &                  # passes, then frames
.venv/bin/python -I "$V/v9/scripts/drowning_sound_v9.py" "research_notes/Speculative crossing soundscape" \
  "research_notes/Line sound proxies/raw/xc/XC1016141/XC1016141.mp3" "$V/v9" $SP/v9/sound
.venv/bin/python -I "$V/v9/scripts/composite_v9.py" video $SP/v9/frames "$V/v9/drowning.wav" "$V/v9/drowning.mp4"
.venv/bin/python -I "$V/v9/scripts/composite_v9.py" sheet $SP/v9/frames "$V/v9/contact_sheet.png" 4 1.0
.venv/bin/python -I "$V/v9/scripts/v9_json.py" "$V/v9/v9.json" $PD
```

### What is drawn or inferred (to be said wherever v9 is used)

- **Speculative and drawn:** the water at the proposed level, its ripples and murk, the view from under the surface,
  the plants' dead state and the two birds.
- **The dead state is a drawing, not a forecast.** As general knowledge, to be checked against a source before the
  film says it: drowned trunks often stand for years or decades in reservoirs, and cormorants perch on their tops.
- **The birds:** the species is sourced (great cormorants nested on these crossings' towers in 2012, Sidorenko &
  Siokhin 2016); these two birds and what they do are drawn. No colony is shown or implied at a tower.
- **The level is a proposal** (Vyshnevskyi & Shevchuk 2024, p. 286). The bed's heights are inferred.
- **The sound** is v7's montage, muffled; the line in it is synthesized.

## v10: the drowning, the water round the trees (9 November 2026)

The user, on v9: "remove the top right branch that looks like a mistake ... also remove the birds. also make it a bit
more realistic how the water will interact with the branches poking out of the water. maybe some white water/flow
around it since it is going to be interupting the water. this could also visually communicate better the height of
the water in relation to the trees since the camera is to remain not moving." v9 and earlier are kept.

In `v10/`:
- `drowning.mp4`: 15 s, 1920×1080, 30 fps, with `drowning.wav` (v9's, copied unchanged).
- Stills: `drowning_first.png` (0 s), `drowning_mid.png` (7.5 s), `drowning_last.png` (15 s); `contact_sheet.png`,
  a frame every second; `drowning_waterline_crop.png`, the near willow's waterline at 3x.
- `flicker.json`, `v10.json`; `scripts/` as run.

Not in the storyboard yet.

### What changed

- **The stray branch is gone.** The pieces floating in the sky at v9's top left were secondary branches of the near
  willows. They were kept while the primary branch they grow from was dropped. v8 ranks a model's stems by radius with
  a random share mixed in, so a thick secondary could outrank its primary. `scripts/still_v10.py` now finds each stem's
  parent from the models' geometry (a branch starts on its parent's centre line) and keeps a stem only while its
  parent is kept. The random draws are v8's, so every stem v9 kept attached stays. The near willow's crown is cleaner
  for it: no piece of any tree floats now.
- **No birds.**
- **The water round the stems** (drawn, seen from under the surface; `scripts/crossings_v10.py`,
  `scripts/composite_v10.py`):
  - where each kept stem of a standing plant within 70 m crosses the proposed level, from the plants' own geometry
    (1,154 crossings; 402 large enough and reaching the view through the surface);
  - round each one, the underside of the surface shows a thin meniscus ring, a collar of foam held against the stem
    (heavier on the upstream side), and a short wake of broken foam patches trailing downstream with v7's current
    (toward the south-west, so toward the camera and up the frame), drifting at the ripples' speed and fading over a
    few metres. The surface is more disturbed in the wake, so the picture through it sways more there;
  - foam from below is bright and fairly opaque, and absorbed by the water like everything seen through the surface;
  - sizes scale with each stem's radius; features smaller than a pixel are widened and dimmed, so they don't shimmer.
  - The waterline on each trunk now reads as a bright collar where the crisp wood under the water meets the wavering
    wood above it.
- The camera, the level, v9's murk and calm surface, the moving wires and the sound are v9's.
- **No caption on the picture.** The statement, to be said elsewhere: "PROPOSED LEVEL · 12.7 M · VYSHNEVSKYI &
  SHEVCHUK 2024 · THE TREES DEAD AND STANDING, THE WATER ROUND THEM AND THE BED'S HEIGHTS DRAWN OR INFERRED · DRAWN".

### Commands (from the project root)

```sh
V="research_notes/Under the crossing still"; SP=<scratch>; PD=$SP/v10/render
blender -b --factory-startup "$B" -P "$V/v10/scripts/still_v10.py" -- "$V/scripts/views_v5.json" "$V/v3/plants/plants_f.npz" \
  $SP/v8/render/plants_laid.npz $PD preview                                       # the dead plants alone, no water
nohup bash "$V/v10/scripts/run_v10.sh" > "$V/v10/render.log" 2>&1 &              # passes, stems, crossings, frames
.venv/bin/python -I "$V/v10/scripts/composite_v10.py" video $SP/v10/frames "$V/v10/drowning.wav" "$V/v10/drowning.mp4"
.venv/bin/python -I "$V/v10/scripts/composite_v10.py" sheet $SP/v10/frames "$V/v10/contact_sheet.png" 4 1.0
.venv/bin/python -I "$V/v10/scripts/v10_json.py" "$V/v10/v10.json" $PD
```

### What is drawn or inferred (to be said wherever v10 is used)

As v9, without the birds, and: the water's disturbance round the stems is drawn. It is placed where the modelled stems
cross the proposed level; the current's direction and speed are drawn, not measured.

## v11: the drowning, the water's surface and the foam again (9 November 2026)

The user, on v10's water round the branches: "its far too straight these lines. wouldnt they be more wavy/disrupted
due to the water waves? also, they seem to continue too far. additionally, the foam from the tree branches sticking out
of the water in the distance is too white and seems strange, perhaps adjust the coloring of them. also could you
improve the water surface so it reads more like water from under than just textures on a treadmill". v10 and earlier
are kept.

In `v11/`:
- `drowning.mp4`: 15 s, 1920×1080, 30 fps, with `drowning.wav` (v9's, copied unchanged).
- Stills: `drowning_first.png` (0 s), `drowning_mid.png` (7.5 s), `drowning_last.png` (15 s); `contact_sheet.png`,
  a frame every second; `drowning_waterline_crop.png`, the near willow's waterline at 3x.
- `flicker.json`, `v11.json`; `scripts/` as run.

Not in the storyboard yet.

### What changed (`scripts/composite_v11.py`; v10's passes and crossings as they were)

- **The surface evolves instead of sliding.** v7's two noise tiles drifted at constant speed, the "treadmill". Now the
  surface is a sum of 40 small wind waves:
  - wavelengths 6 cm to 0.9 m, the slope peaking near 0.18 m;
  - travelling within about 50 degrees of the drawn current;
  - each at its own speed, by the dispersion of capillary-gravity waves (ω² = gk + (σ/ρ)k³), so the pattern changes
    shape as it moves. At the peak the phase speed is about 0.53 m/s;
  - rougher and calmer patches drifting slowly over it (cat's paws);
  - the same RMS slope as v7's, so v9's calm surface.

  From that one field come the sway of the picture seen through the surface, the underside's soft brighter cells (where
  the surface's curvature gathers light, with no hard caustics) and the wakes' wobble. Waves shorter than a few pixels'
  footprint are filtered out, so nothing shimmers.
- **The wakes are short and broken.** They are about a quarter of v10's length and fade fast. Each wake's centre line
  meanders with a slowly evolving flow field and wobbles with the surface's slope. Its foam is cut into round patches
  by an evolving noise whose threshold rises downstream, so it splits into flecks and dissolves.
- **The collar** round each stem is irregular and boiling, half again v10's width, its width changing round the stem
  and in time.
- **The foam is not white.** From below it is a soft, pale grey-green, at most about 30% brighter than the water round
  it near the eye and no brighter far off. It thins with distance (from 6 m to 40 m), and the water absorbs it along
  the path like everything else seen through the surface. In v10 it was one bright colour at any distance.
- **Snell's window is still not drawn.** At this view almost all of the surface seen lies outside it, so in reality
  it would mirror the murk and the tower would not show. The convention is kept so the towers and the lit wires read.
  Only a hint of the mirror is drawn: the view through darkens toward the murk at grazing angles, near the horizon.
- The camera, the level, v9's murk, the stray branch fix, no birds, the moving wires and the sound are v10's.

### Render

- The 450 frames: three numpy workers, 16 min (the wave field costs about 2 s a frame more than v10). The encode took
  14 s.
- Checked: no flicker. The largest step between frames is 1.08 levels against a median of 1.03: the evolving surface,
  even throughout. v10's was 0.59 against 0.55.
- 392 of v10's 1,154 crossings are drawn: those with a large enough stem that reach the view through the surface.

### Commands (from the project root)

```sh
V="research_notes/Under the crossing still"; SP=<scratch>; PD=$SP/v10/render       # v10's passes and crossings
nohup bash "$V/v11/scripts/run_v11.sh" > "$V/v11/render.log" 2>&1 &              # the frames, about 6 s each a worker
.venv/bin/python -I "$V/v11/scripts/composite_v11.py" video $SP/v11/frames "$V/v11/drowning.wav" "$V/v11/drowning.mp4"
.venv/bin/python -I "$V/v11/scripts/composite_v11.py" sheet $SP/v11/frames "$V/v11/contact_sheet.png" 4 1.0
.venv/bin/python -I "$V/v11/scripts/v11_json.py" "$V/v11/v11.json" $PD $SP/v8/in/v5 $SP/v8/render $SP/v8/in/v7anim $SP/v11/frames
```

### What is drawn or inferred (to be said wherever v11 is used)

As v10, and: the surface's waves (their lengths, directions, slopes and the drifting rougher patches) are drawn, with a
real dispersion relation but not measured. The view up through the surface is a drawn convention (no Snell's window).

### Clean-up (9 November 2026)

At the user's request, to free space: the renders, stills and sound files of v3 and v6–v10 were deleted (251 MB). Their
scripts, records (`v*.json`, logs) and v3's plants (`v3/plants/`, which every later pass reads) are kept. Kept as
media: v4 (the first under-the-crossing film, for the record), v5 and v7/alt and v8/alt (on the storyboard), and v11
(the current drowning). The v11 render's inputs (v8's and v10's passes) are kept only in the session's temporary
folder, so retuning v11 needs those passes rendered again once that folder is gone.

## Edges: the nature sounds from the first frame to the last (9 November 2026)

The user asked for the nature sounds to be heard at once when under-the-crossing begins, and until it ends; before,
they faded in over about 2–4 s and out by 27.5 s. `edges/scripts/edges_sound.py` remakes the cut's soundscape (mix.py's
45 s run, its first 30 s). The birds' bus has no fades. The near nightingale and the reeds start at 0 s and the chorus
runs to 30 s: the same recordings at the same alignment, only longer, through seconds screen.py found clean, and each
at its old gain. The line starts at once. The master gain is the old run's, so the line's last 50 ms is −26.1 dBFS as
before and the drowning (v9's sound) still continues it; only the birds stop at the cut. The picture is v5's, copied
(`edges/under_the_crossing_f_day_edges.mp4`, `edges/edges.json`). The storyboard's under-the-crossing now plays it
(source `under-crossing-edges`); the previous version stays as `under-crossing-f-day-continuous`.

### The truer line (9 November 2026)

The user asked for the lines' crackle at full strength and the 750 and 330 kV voices apart (hum.py's `CORONA` and
`HUM_SHAPE`). mix.py's `line()` now voices Ferosplavna-1 as the Hum's own 330 kV line: its hum in the 330 kV's shape,
its corona at full strength and dry (a May morning "now" is no dated day, so no weather swell; the earlier "dewy
morning" denser crackle is dropped). Both sounds were made again from the same new 45 s run and laid under the same
pictures, copied, not re-encoded (each picture stream checked byte-identical):
- under-the-crossing: `edges/edges_sound.py` again (`edges/under_the_crossing_edges.wav`, `_f_day_edges.mp4`, `edges.json`):
  first and last 0.5 s -18.7 and -19.7 dBFS as before; the line alone in the last 50 ms -25.9 dBFS (was -26.1); peak
  -1.7 dBFS (was -5.7: the cracks' peaks; the limiter holds -1).
- the drowning: `v9/scripts/drowning_sound_v9.py` run into `v11/` (`v11/drowning.wav`, `drowning_sound.json`, the mp4
  re-muxed; `v11.json`'s sound and hashes updated): the open line -25.5 dBFS as before, muffled at 380 Hz, gain 3.4 dB
  (was 0.7: more of the new line's energy is crackle, which the muffling takes away).
- The join: the 45 s run's line alone at 28-30 s equals the edges' line times the master gain to 4.5e-5 (1.5 LSB), so
  the drowning's line still goes on from under-the-crossing's last sample; at the cut it closes over (the step 0.011,
  was 0.023), as before.
The old files are kept in the session's scratchpad.
