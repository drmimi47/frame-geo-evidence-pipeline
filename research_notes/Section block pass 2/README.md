# Section block, pass 2 (7 November 2026)

Prototypes for the hand-over from the block (`section-block`) to the offset section (`section-dniprovska`), after the
user's notes of 7 November 2026:

1. cut the block exactly where the 2D section is cut (the pond's north dike, the jog, the crossing), not along a
   straight cut;
2. no animated height exaggeration: the block is at heights x3 from its first frame;
3. go smoothly from the block into the section, so the section no longer needs its key plan (the block shows where
   the cut was taken);
4. several prototypes to choose from.

Tests at 30 fps, 1920x1080, as the S1 tests; not the film. Everything here is new; `reports/S1-section/` is unchanged.

## The prototypes

| file | length | what it does |
|---|---|---|
| `A-trace-and-split.mp4` | 18.1 s (continuous 34.4 s) | the block, the cut traced, the rest of the block drops to a ghost and goes; each slice stays where it is and gets its own camera; the frame splits at the section's break and each half squares up to its cut |
| `B-unfold.mp4` | 17.3 s (continuous 33.6 s) | the same opening; the dike's slice swings round and slides beside the crossing's (the offset section's convention, done in the open); one camera comes down square to both |
| `C-unfold-x3.mp4` | 15.3 s (continuous 31.6 s) | B's block, then the section kept at x3 throughout (no change of scale at all); the dike's detail, larger, carries the levels |
| `*-continuous.mp4` | | the same, continued through the section to its end (the three days): each can replace `section-block` + `section-dniprovska` in the cut |
| `section-dniprovska-no-key-plan.mp4` | 21.1 s | the section alone, without the key plan, from its x3 first frame (the hand-over's target), easing to x10 |
| `section-dniprovska-no-key-plan-x3.mp4` | 19.1 s | the same at x3 throughout (C's section) |
| `section-ferosplavna-no-key-plan.mp4` | 21.1 s | Ferosplavna's section the same way (its jog ≈ 6.3 km) |
| `B-unfold-ferosplavna-continuous.mp4` | 33.6 s | B along Ferosplavna's crossing, block to section's end (the secondary variant) |
| `*-sheet.jpg` | | contact sheets, one frame from each part (times in yellow) |
| `match-check.png` | | the block's last frame (B), the section's first, and their difference |
| `towers-x10-or-true-size.png` | | the section's towers x10 (used) or at true size (not used), and the x3 hand-over scale |

Each prototype file runs from the block's first frame to about two seconds into the section's first day, so the
hand-over can be judged; the `-continuous` files go on to the section's end.

## What the block does (all three)

- **x3 from the first frame.** The region as one block (17 x 18 km, the S1 block's land), heights x3, towers and wires
  at true size on it (`HEIGHTS x3 · TOWERS AND WIRES AT TRUE SIZE`, bottom left, from the start). No growth.
- **Day A only.** 6 September 2022 (island mode), the 29 August 2022 Sentinel-2 pass (6 and 8 September clouded over,
  said in the faint credit), the reservoir and pond at the normal level, 16 m: the imagery and levels the section uses
  for its day A, so the hand-over doesn't change day. The block doesn't replay the three days (the section does).
- **The cut traced** on the land (2.2-5.2 s), as the old key plan drew it: the dike's cut (x = -3000, y 600 to 4400),
  the jog dashed, then the crossing's cut (towers 21 to 27, 500 m on at each end). One short line under the date:
  `THE CUT: THE POND'S NORTH DIKE, THEN DNIPROVSKA'S CROSSING`. This replaces the key plan.
- **Two slices.** The rest of the block drops 200 m and fades to a ghost (5.4-7.4 s), leaving the two slices the
  section is cut through, each 250 m deep behind its cut: as deep as the section draws towers from the cut, so a slice
  holds exactly what the section draws (Dniprovska's towers; Ferosplavna's row, about 350 m behind, goes with the
  rest). Their cut faces are drawn as the section draws them.
- **Into the elevation.** The camera (orthographic throughout, as the S1 block) comes down from the block's view (from
  the south-east, 39 degrees up) to level, square to the cut(s), turning about 15 degrees (A's left half 32), never
  more: no swivel. The ghost goes, then the slices' tops and sides fade, leaving only the cut faces, towers and wires:
  the section's first frame. The block lasts 12.5 s (A 13.3 s); the section's x3 frame holds 0.4 s.

### A, trace and split: nothing moves

The section is two elevations laid side by side (that is how gfilm.py drew it). A shows that literally: after the
drop, two cameras start from the same view, one turning to look due west at the dike's slice, the other west-north-west
at the crossing's; the frame splits between them (a thin seam, which ends where the section's break line is), each
half squaring up to its own cut. No slice moves; the jog (≈ 6.7 km) is simply what lies between the two views. Line:
`EACH CUT SEEN SQUARE ON, ≈ 6.7 KM LEFT OUT BETWEEN`. While the ghost is still there it doesn't line up across the
seam; that is the cost.

### B, unfold to the section: one camera

The offset section's convention made visible: the dike's slice swings round (17 degrees, the angle between the two
cuts) and slides about 6 km east-south-east to sit beside the crossing's, a gap's width short of it, exactly where the
section lays it; its empty place stays as a dark slot in the ghost (it was moved, and that shows). The crossing, its
towers and wires never move. One camera comes down square to both. Line: `THE TWO CUTS LAID SIDE BY SIDE, ≈ 6.7 KM
LEFT OUT`.

### C, unfold at x3

B's block (the same frames), handing over to a section that stays at x3: scale option (b) below.

## The scale: x3 in the block, x10 in the section

At the section's scale (6.47 m a pixel) and x3 the whole section is a hairline about 12 px thick: the land really is
that flat. Two bridges were made:

- **(a) ease, in A and B.** The hand-over is at x3, towers at true size, exactly (below). The section holds 0.6 s, then
  eases to the S1 section's x10 over 2 s (ground and water x3 to x10, towers and sag true size to x10, one eased
  parameter), the heights note counting with it (`HEIGHTS x3 · TOWERS AND WIRES AT TRUE SIZE` ... `HEIGHTS x10 · TOWERS
  AND WIRES x10`); then its labels, levels and detail fade in. This is an animated exaggeration, in 2D: it is said
  while it happens, and it happens once.
- **(b) x3 throughout, in C.** No change of scale anywhere. The section's own level lines are left out (at x3, 16 m
  and 12 m are 2 px apart); the dike's detail, at 12 times the section's scale (0.54 m a pixel), heights still x3,
  carries the levels. It reads the reservoir's loss (a band of blue going) and the towers on the dry bed, but the
  pond's fall is only legible in the detail, and 12.34 m against 12 m is a pixel or two.

**Recommendation: B with (a).**
- B over A: one space, one camera, and the offset section's convention (two cuts laid side by side, the jog left
  out) is something the viewer sees being done, with the dike's empty slot left behind; the crossing, its towers and
  wires never move. A is the purer one (nothing moves) and explains how the section was drawn, but two cameras moving
  at once read as an effect, and the ghost breaks at the seam while it lasts. If the user prefers that nothing ever
  moves, A is the one.
- (a) over (b): the section is there for the levels (the reservoir gone, the pond running down to the pumps' 12 m),
  and at x3 they only read in a detail enlarged twelve times, where 12.34 m against 12 m is still a pixel or two; the
  land's real flatness is already shown by the block and by the 0.4 s x3 frame before the ease. The ease is said while
  it happens and happens once. But it is an animated exaggeration, which the user asked to drop for the block: if that
  applies here too, C (x3 throughout) is the honest alternative, or a dissolve from the x3 drawing to the x10 one
  (not made) instead of the growth.
- Towers in the section after the ease: x10 with the ground (the S1 convention, the drawing the user has seen). At
  true size on x10 ground they look shorter than the banks (`towers-x10-or-true-size.png`), which misleads the other
  way. The heights note says which, all the time.

## The match frame

The block's faces and the section's pieces are made by the same code (`cutlib.py`: the face, the towers within 250 m,
the wires, both exaggerations), and the block's last camera is placed by the section's layout formulas (`cuts.py`):
the dike's s plus sigma is its place along the crossing, the camera's centre and height those of the layout (6.46875 m
a pixel, the world height 672 m - 60 px at the middle row). So the block's last frame is the section's first by
construction. Measured (`match-check.png`, `scripts/matchcheck.py`): B's last block frame against the section's first,
mean difference 0.146 of 255, 30 px over 20, all on the two pieces' crop-edge columns (the section crops each piece one
column short); A's (its two cameras composited at the seam), mean 0.159, 49 px over 20, the same columns; B along Ferosplavna, mean 0.146, 19 px over 20. In the
encoded B clip the step from frame 374 (block) to 375 (section) is mean 0.12 of 255, the same as any still frame. The composer switches from one to the other at that frame with no dissolve.

## Text

The user found the S1 sections "way too much text". Kept: the date (top left), at most one short line under it (the
cut; the two cuts side by side; in the section, only during a dissolve: `A DISSOLVE BETWEEN TWO DAYS' DRAWINGS, NOT AN
OBSERVATION`), the heights note (bottom left), the drawing's own labels (place names on leaders, the river's and the
pond's levels, `12 M`, `16 M`, `EARLIER REPORTS`, `≈ 6.7 KM OMITTED` at the break), and in the block the imagery's
faint credit (`... CONTAINS MODIFIED COPERNICUS SENTINEL-2 DATA`) while the imagery shows. Gone: the key plan and its
captions, the event lines, the section's course, the levels note, the detail's caption and "DETAIL BELOW", the
footnotes (their content belongs in the credits and S1-section.json). The type as the films': white capitals in
Helvetica Neue on half-opacity black boxes.

## Evidence and safety

As S1 (reports/S1-section/S1-section.json), nothing new claimed:
- imagery: Sentinel-2 L2A, 29 August 2022 08:36 UTC (Copernicus, via Microsoft Planetary Computer), as fetched,
  resampled onto the land only (never generated or upscaled); dimmed by one factor (0.78) as in S1;
- heights: FABDEM, the drained bed's inferred heights (bed.json; dotted on the cuts), x3 in the block; the pond's depth
  not published (faded); water a modelled surface at the day's level where the pass reads water;
- towers at OpenStreetMap's positions, types representative (the 3D film's models, `towers.npz`), drawn flat grey;
  every wire bare steel (each day a complete loss of off-site power, chosen so);
- what is moved is said: the slices are cut from the block at 250 m, B moves the dike's slice beside the crossing's
  (the jog left out and said, as the section's break says); A moves nothing; a dissolve says it is one;
- safety: no tower marked, numbered or pinned; the cut and the jog only (as the old key plan); no coordinates; nothing
  near the trench site or the Dniprovska substation (the block is the S1 block's area).

## The storyboard

Not edited (the user's Blender holds it). In the cut now: `section-block` (out 11 s) -> `seepage-paper` -> `section-
dniprovska`. A continuous clip can't have the paper in the middle; suggested: `water-cooling` -> `seepage-paper` ->
the chosen continuous clip (the paper's claim first, then the film's own test, as seepage-paper's "tells" says).

## Scripts (as run; Blender 5.2 headless, then PIL and ffmpeg)

- `cuts.py`: the cuts, the 2D layout as numbers, the block's timelines (pure numpy, shared).
- `cutlib.py`: the face, towers and wires of a cut at ex_g / ex_t (Blender), shared by the 2D and the 3D.
- `profile3.py`: the section's pieces (profile2.py's drawing; with ex 10 / 10 it redraws the S1 renders: mean
  difference 0.04 of 255).
- `block2.py`: the block (Blender, EEVEE): `-- XF STATE SCENE_DIR PASSES PROTO LINE OUT [--res --samples --frames]`.
- `gfilm2.py`: the section without the key plan (`jobs` writes profile3.py's jobs; `film` the section alone).
- `compose2.py`: block + section + type into one clip, the prototype cut from its start, contact sheets.
Inputs: the S1 working files (W_/E_ blocks from prep3f.py on each day's pass, states.json, the three passes from
fetch_pass.py) and a copy of the 3D scene's `scene.json` and `towers.npz` taken on 7 November 2026 (read only).

## Run log (7 November 2026)

- profile3.py checked against the S1 renders (ex 10/10): mean difference 0.04 of 255 (towers.npz has changed a little
  since 4 November).
- Block frames: B (Dniprovska) 391 frames, EEVEE, 32 samples (64 on frames with a fade), sun shadows on; A 415 frames:
  0-216 as B, 217-414 with 16 (32) samples and no sun shadows (`--no-shadows`: invisible at this scale, a third of
  the time; frame 216 both ways differs by 1 of 255 on average, dither); Ferosplavna's B 32 (64) samples, no shadows.
  All with `nice -n 10`, beside the 3D flight's look-pass render (untouched).
- A's frames 223-414 were rendered before a fix in block2.py (the seam's extents were projected through the previous
  pass's camera, `view_layer.update()` missing); the renders and the composite use the same seam, and it falls between
  the two slices in every frame checked, so they were kept. The script here has the fix.
- Speed: cutlib.Land now loads the npz arrays once (they were decompressed on every sample: the frames went from about
  a minute to a few seconds); same pixels (checked on A's frame 260: difference 0).

To make Ferosplavna's A or C, or a 60 fps final: block2.py with `PROTO`/`LINE`, gfilm2.py `jobs` + profile3.py for
the section's renders, compose2.py; the scripts' docstrings give the arguments.

## A2: A without the line at the split (8 November 2026)

The user: "another pass on section-block2-a without the vertical white line in the center". `A2-trace-and-split.mp4`
and `A2-trace-and-split-continuous.mp4`: A's own block frames and section, recomposed by compose2.py with the thin
grey line at the seam removed (nothing re-rendered). Checked against A: frames 100, 600 and 900 identical; 280 and 330
differ over 20 of 255 only in the line's columns. The split stays where it was, a hard edge where the two views meet.
The storyboard's `section-block2-a` plays A2 (config source SB2-A). The scratchpad's `section/xf/states.json` had
been cleared and was restored from reports/S1-section/scripts/states.json (the only file compose2.py reads there).

## Deleted (8 November 2026)

The user chose A2 (section-block2-a, in the cut). B, C, B along Ferosplavna (videos and sheets) and A's first version with the line were deleted at the user's request; their scripts stay here.

## A2, second pass (8 November 2026)

The user's notes on section-block2-a: the split jumped at about 8.5 s, too much text in the section, and the three
parts of the section arriving at once. `A2-trace-and-split.mp4` and `A2-trace-and-split-continuous.mp4` remade, same
length (34.4 s, so the storyboard's trim holds); the earlier pair kept in the scratchpad only.
- **The split.** A run's first frame measured its seam before the cameras had updated: frames 217 (the split's first)
  and 255 (bA0d's first) put the seam about 100 px right, and were rendered only to that seam. Both re-rendered with
  block2.py (`--frames 216:218` and `254:256`, the run's first frame thrown away; 16 samples, no shadows, as the rest of A),
  and compose2.py now takes each frame's seam as the median of the five round it, held within the 19 px each camera
  was rendered past its own. The divide moves at most 1.8 px a frame through the split. The scratchpad's `W_A.npz`,
  `E_A.npz` and the 29 August 2022 pass had been cleared: remade with prep3f.py and fetch_pass.py (the pass's image
  identical to the surviving one, difference 0).
- **Less text.** The section no longer names the cooling pond and the dike (the detail does), nor the line over the
  wires (`DNIPROVSKA · 750 KV: CUT`). The heights note stays (bottom left): it is the only place the x10 is said.
- **One part after another.** After the ease: the section's labels and the detail's dashed frame (0.9 s); then the
  detail grows out of that frame to its place below (1.6 s, eased, the pixels only scaled: the frame and the detail
  are the same stretch and heights, the detail three times larger), fading in over its first quarter-second; then the
  detail's levels and names (0.6 s). Day A's hold is shortened by as much, so day A is on screen as long as before.
  The dashed frame stays in the section.
- **No pops.** The date and the dissolve's line used to switch on and off in a single frame at each dissolve's start
  and end; they now crossfade over 0.7 s (`gfilm2.typed`). A frame-by-frame scan of the clip and of the storyboard's
  preview (each step against its neighbours, and each frame against the frames either side) flags nothing; the largest
  step is the opening fade from black. Swapped into the storyboard by refreshing its preview (`media/SB2-A.mp4`, same
  1032 frames); the .blend was not rebuilt.
