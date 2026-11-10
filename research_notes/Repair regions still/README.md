# Where crews were sent to repair the lines (5 November 2026)

This is a still for the storyboard. The user asked for it at about 5:18, beside `zo-night-after`:

> "use the same map background but render in circles (similar to the soundscape style) of where crews were dispatched
> to fix the wires ... this should not be an animation ... they dont have to be just the north and south lines."

## Files

- `repair_regions_3840.png`: the still at 3840×2160.
- `repair_regions_1920.jpg`: the same still at 1920×1080, for the storyboard.
- `repairs.yaml`: the input. Every repair found for 2022–2026, each with its dates, who did it, where the work was (in the source's own words), how precise that is, and its sources.
- `regions.json`: what was drawn. It lists each area (its line, stretch, shape, size in km and repairs), the repairs placed, the repairs left unplaced, the reports not counted as repairs, caveats and a safety check. Source shorthands are written out as URLs.
- `scripts/repair_regions.py`: the script that made the still. Run it from the project root:
  `.venv/bin/python -I "research_notes/Repair regions still/scripts/repair_regions.py"`.

## What it shows

- **The frame.** North up, 40 km wide, centred 2.5 km east and 5.2 km north of the plant.
  - The zoom-out's crossing frame, where `zo-night-after` opens, is 25 km wide. That cuts off Ferosplavna-1's run to its substation by Nikopol, where most published repairs are. So the still is zoomed out to 40 km.
  - The frame does not include Dniprovska's far end, its substation (checked in `regions.json`).
- **Areas.** 20 repairs were published with a place. They fall into 6 areas, each outlined in its own colour; the count and each repair's date are on its label. The six areas:

| Area | Repairs | What its sources say |
|---|---|---|
| Ferosplavna-1, north of the Dnipro (the river channel to its substation, 29.6 km) | 7: Jan 2023 to Sep 2026 | "the other side of the Dnipro River", "the right bank", "the northern bank", "Ukrainian-controlled territory" |
| The plant's and the thermal plant's switchyards, and the links between them (a circle 5.7 km across) | 6: Sep 2022 to Jun 2026 | repairs at the thermal plant's switchyard, and to the link between it and the plant's autotransformer (three of them under IAEA ceasefires) |
| Dniprovska, north of the Dnipro (it runs on beyond the frame) | 3: Oct 2022, Nov 2022, Nov 2025 | "on Ukrainian-controlled territory in Dnipropetrovsk oblast"; "50–60 kilometres from the plant in Ukrainian-controlled territory"; "approximately 16 kilometres from the plant" |
| Ferosplavna-1, the south bank (the thermal plant to the shore, 4.3 km) | 2: Nov 2025, Jun 2026 | "about 1.8 kilometres from the ZTPP's switchyard", "around three kilometres from the ZNPP's site perimeter", "near the ZTPP switchyard" |
| Dniprovska, the occupied side (the plant to the river channel, 7.5 km) | 1: Oct 2025 | "in an area under Russian control", "on the other side of the frontline" |
| Dniprovska, the crossing (4.5 km) | 1: Jun 2026 | "crosses high above the river", "high pylons across the Dnipro River" |

- **Unplaced repairs.** 21 more repairs or restorations had no place published, or only the Dniprovska substation, which is never shown. They are not drawn; the count at the bottom left says how many.
- **Reports not counted.** Nine reports are not counted as repairs. Some were trips or protection systems acting, some said no damage was found, and some were Rosatom's plans with no completed repair.
- **Text on the frame.** The date, legend, captions and loss count are all gone. What is left:
  - no key box (removed by the user): one faint line above the credit says the areas are drawn, not observed, each as wide as its source says; and that the + is an area's centre, not a place of work;
  - the count, bottom left, boxed (the user, 5 November 2026): every repair found, 41, from the first to the last (18 March 2022 to 7 September 2026), 20 drawn and 21 with no place published;
  - each area's count, its place in the source's terms, and each repair's date (the date its source gives for the work or the reconnection);
  - the plant's mark and three towns;
  - the credit, faint, bottom left.

## How it was made

The still reuses the zoom-out's own code and data. The zoom-out itself is not changed.

- **Background** (restyled at the user's request, 5 November 2026: "more stylized ... just the outline of the shores + river ... grey background"). Plain grey, no imagery. On it:
  - the water as Sentinel-2 saw it on 28 August 2025: the 3D survey's water mask (`imagery/c3d_2025_08/water.png`, its rule in `water.json`), resampled onto the frame, filled a shade darker and outlined; pools under about 3 ha left out;
  - where the water used to be (the user: "in a light hatch"): the reservoir as Sentinel-2 saw it on 5 June 2023, the last clear pass before the dam was destroyed. It is the 3D bed's footprint (`scenes/crossing3d/bed/bed.npz`, its pass in `bed.json` `reference`): the one body of water that held the crossing, so the plant's cooling pond and the lakes behind dikes are not part of it. Hatched light at 45° and its shore outlined faintly, both made stronger at the user's request (5 November 2026: "make the hatches more visible"). It replaces OpenStreetMap's Great Meadow outline, so the old shore is an observed one. The frame was moved 0.5 km east to sit exactly on that mask's 40 km box.
- **Centres.** A small + at each area's centre (a band's halfway along the part of its line in the frame; the switchyard circle's middle), on a dark halo, so where the areas overlap they can be told apart and counted. A centre marks the area as drawn, never a place of work, a tower or a crew (a ring round the cross was tried and dropped: it read as a gunsight).
- **Lines.** Each of the plant's lines (OpenStreetMap, `network.json`) is drawn in the film's two yellows and fades toward its end. There is no state and no glow, because the still has no date.
- **Areas along a line.** The stretch of line its sources name, widened to a band 3 km across with rounded ends.
  - The sides of the front and the banks are the unrolled film's (`unrolled.data` with the whole line): the shores of 5 June 2023, and the river channel of September 2023 taken as the front.
- **The switchyard area.** A circle round both switchyards' OpenStreetMap outlines, widened by 0.6 km.
- **Edges.** Each area is outlined in its own colour, semi-transparent, with no fill (the user, 5 November 2026: bright colourful borders, to tell the areas apart; first dashed white outlines over translucent fills that added up). The six hues are kept apart from the lines' yellows and were checked with the dataviz skill's palette validator on this grey: every pair stays apart for colour-blind viewers (ΔE ≥ 10.9) and in normal vision (≥ 17.2). Each label's leader and the area's + are in its colour too.

## Drawn, inferred, observed

- **Observed:** only the water: the river on 28 August 2025 and the reservoir on 5 June 2023 (Sentinel-2).
- **Drawn:** the lines, the areas and every mark. The key says so ("the areas are drawn, not observed").
- **Inferred: two placements.** R40 ("approximately 10 kilometres from the ZTPP 330 kV open switchyard ... Ukrainian technicians") and R37 ("approximately 16 kilometres from the plant") are drawn on their line's whole north side.
  - Both distances fall north of the river on these lines, whether measured along the line or as the crow flies.
  - Neither repair is ever drawn at its distance.
  - `regions.json` marks both as `inferred`.

## Safety check

The rule (CLAUDE.md; NEXT.md I5): where repairs were is shown only as a general region, at least about 3 km across and never finer than the source. Never a tower, a pin, coordinates or a crew's position. Never the Dniprovska substation's place or the trench site.

How the still keeps to it:
- **Smallest region: 3.0 km.** Every band is 3 km wide, and the shortest stretch is 4.3 km (Ferosplavna-1's south bank). The switchyard circle is 5.7 km across. The script refuses anything under 3 km.
- **Distances are never used as places.** No region is placed by a distance: "1.8 km from the switchyard", "13.5 km", "10 km", "16 km" and "50–60 km" are quoted and drawn as the whole bank or side.
- **No points drawn.** No tower, crew or coordinates are drawn, and `regions.json` gives stretches in metres along the line, not coordinates.
- **The substation.** The Dniprovska substation is outside the frame, and the "about 100 km north" repair (R19) is left unplaced.
- **The trench site** is not involved.

## Accumulated, as far as the sources go

- **Fewer layers ≠ fewer repairs.** An area with fewer layers means fewer repairs had a published place, not that fewer happened. 21 repairs had no place, and others may never have been reported.
- **Why the published places cluster.** The IAEA gave places mostly from late 2022, and mostly for the ceasefires from October 2025.
- **The plant's other seven lines** are drawn without areas. No completed repair of them was found after they were cut in 2022, only Rosatom's plans. That does not mean none was tried.

## Style matched

The style follows the soundscape still, `research_notes/Line sound proxies/soundscape.jpg` (Earshot idea 5), more than the footprint figure:
- thin outlines (now coloured, no fill) on a plain grey ground with only the river and the old shore outlined;
- the lines in the zoom-out's yellows;
- small white capitals on half-black boxes;
- a faint unboxed credit.

The user asked for circles. The switchyard area is a circle. The other areas are bands along their stretch of line, because their sources name a side, a bank or a stretch, not a spot. A circle there would claim more than the source says.

## Open points for the user

- **Ceasefire numbering.** The IAEA numbers its own ceasefires differently from the unrolled film (`networks.znpp.unrolled.truces`):
  - its third is the December 2025 repair of the link between the plant and the thermal plant;
  - its fourth (January 2026, Ferosplavna-1) does have a published place: about 10 km from the thermal plant's switchyard, on the frontline;
  - its fifth (February–March 2026) was the link at the thermal plant's switchyard, not Ferosplavna-1 out on the line.

  The unrolled config is unchanged.
- **Conflicting reports.** R21's dates disagree between Ukrenergo and the IAEA. R44's place disagrees between the IAEA and OECD-NEA (the IAEA, which watched the repair, is the one drawn).
- **How the sources were read.** The IAEA's updates were read through mirrors (globalsecurity.org, reliefweb.int), because iaea.org refuses automated reads. Check the key quotes against iaea.org before any caption.

## Pass 2 (8 November 2026)

The user chose ideas 1, 4, 6, 7 and 8 from the review. Made by `scripts/repair_regions_v2.py`; v1's files are kept.
Output in `v2/`: `repair_regions_v2.mp4` (8 s, 30 fps, 1920×1080, silent), the still `repair_regions_v2_3840.png` and
`repair_regions_v2_1920.jpg` (the video's last frame), `repair_regions_v2_sheet.jpg`, and `regions_v2.json` (v1's
record plus what changed).

- **One ring per repair (1).** An area's outline is its first repair. Each later repair is a ring 5 px (at 1920) further
  in, so the area as drawn is never wider than its source says. The labels give the count and the place, no dates.
- **The front (4).** The river of 28 August 2025 is taken as the front, as in the unrolled film: a drawing convention,
  not a surveyed line. The land joined to the plant without crossing water is tinted faintly and named "Occupied since
  March 2022"; the far bank is named "Ukrainian-controlled". Islands between the channels are left untinted.
- **The timeline (6).** One tick per repair at its date along the foot, in its area's colour, grey and shorter where no
  place was published. Most placed repairs fall after October 2025; most early ones have no place.
- **Fixes (7).** A dark band at the foot keeps the lines out of the footnote. The switchyards' area is blue instead of
  white, and Dniprovska north a lighter violet. All six pass the dataviz validator on this grey (all pairs: colour-blind
  ΔE 9.4, normal 16.4). The frame is 38 km wide, 2 km off the empty east, its west edge unchanged.
- **The build-up (8).** A playhead runs from February 2022 to September 2026 between 0.6 s and 6 s, linear in time.
  Each repair's tick, and for a placed one its ring (brighter for a moment), appears as the playhead passes; an area's
  label and cross come with its first repair; the count counts up. It holds from 6 s to 8 s.
- Safety: unchanged from v1 (the same regions, at least 3 km, no points; the Dniprovska substation out of the frame).

## Pass 3 (8 November 2026)

Pass 2 restyled, after Lawrence Abu Hamdan's *Air Pressure* (Earshot; first credited here to Forensic Architecture, corrected 8 November 2026) (the user's reference image). Made by
`scripts/repair_regions_v3.py`, which draws at 3840 and halves for the video so the 1 px rings stay smooth. Output in
`v3/`: `repair_regions_v3.mp4` (8 s, 30 fps, silent), the still `repair_regions_v3_3840.png` / `_1920.jpg` (the
video's last frame), `repair_regions_v3_sheet.jpg`, `regions_v3.json`. In the storyboard as `repair-regions`.

- **Map:** near-black (#1e1e1f), the occupied side a shade lighter (no colour, since the lines are now red), the water
  darker with faint grey shores, the old reservoir's hatch barely there; a black bar at the foot.
- **Rings:** all white, 1 px at 1920, 4 px apart inward. Each comes in at full white and decays toward 0.72
  (exponential, 1.6 s), so the newest are brightest and none fades to grey.
- **Lines:** red (750 kV #e8342e, 330 kV #c42c28), fading toward their ends, no glow.
- **Text:** one large sentence top right, counting up ("41 repairs to the plant's power lines since March 2022"), with
  a small line under it (with a place published, drawn · without). The area labels are small bold capitals on solid
  black boxes with the count in brackets, as in the reference; a thin leader runs to a dot marking the area. Removed:
  the river's label, Marhanets, the count box, the centres' crosses. The note and the credit sit small in the bar.

## Pass 4 (8 November 2026)

Pass 3 with the map simplified at the user's request ("the map terrain should be 1 color and where the dnieper is
should be another that is hatched"): `scripts/repair_regions_v4.py`, output in `v4/` (the same set of files). No tint
for the occupied side. The land is one colour (#262627). The Dnipro, as the reservoir held it on 5 June 2023 (the 3D
bed's footprint), is another (#0f0f10), hatched at 45° with its north and south shores outlined; today's channels (28
August 2025) are solid near-black inside it, unhatched. "Occupied" and "Ukrainian-controlled" now sit on each bank's
land. Everything else is pass 3's.

## Pass 5 (8 November 2026)

Pass 4 with no outlines on the map, only fills, and the tones closer together (the user: "just infills for the
shapes ... not so contrasty"): `scripts/repair_regions_v5.py`, output in `v5/`. The land #222223; the Dnipro of 5 June
2023 #19191a with its hatch #2c2c2e; today's channels #111112. The shores are where the fills meet.
Then, at the user's request, the text was cut down: "Occupied", "Ukrainian-controlled", Nikopol, Enerhodar and the
line under the sentence (with a place published · without) were removed, and with the sides no longer named, the front
is no longer drawn or mentioned in the note. Since the sentence counts all 41 repairs and only 20 are drawn, the note
now says that the short grey ticks are repairs with no place published, which are not drawn.

## Who repaired: options A to E (8 November 2026)

Asked by the user: make it feel more like a network of repairs, with lines from the Ukrainian or the Russian side to
each repair, depending on whether the reports say one side or both did it. Researched first (`sides/`):
`who_repaired.md` (who did each of the 41 repairs, quoted and sourced, the accounts that disagree) and
`design_precedents.md` (15 precedents for drawing a network of actors on a map). `repairs.yaml` now has per repair
`side`, `side_basis`, `worked_on`, `arranged_by`, `accounts` (where the sources disagree, both kept) and
`side_sources`. With R48 (below), 42 repairs: 27 by Ukrainian crews, 7 by the Russian side, 1 by both (R45, the crossing, June 2026: whether jointly
or each on its own stretch differs by source), 7 not said; 11 under a ceasefire the IAEA brokered (it brokered and
watched; it never repaired). Only R45 is reported as both sides' work; no other repair is described as joint.

Stills only, no animation yet, by `scripts/repair_sides.py` (pass 5's map; `sides/sides_<A-E>_1920.jpg`,
`sides/sides_sheet.jpg`, `sides/sides.json`). One vocabulary in all five: solid, that side did the work; dotted, the
sources don't say who; a small open diamond, under an IAEA-brokered ceasefire. No link starts at a place (a crew, a
tower, the Dniprovska substation or any point on the land).
- **A, the banks as the sides.** Links from the frame's top edge (Ukrainian crews) and its foot (the Russian side),
  fanning into each area. Reads at once, but a link crossing the river reads as crews crossing the front, which
  happens for the 2022 repairs by the plant's Ukrainian staff on the occupied side (R05b, R10) and for R45.
- **B, the actors in the timeline bar.** Three lanes (Ukrainian crews, the Russian side, not said); each repair a mark
  in its lane at its date (a diamond under a ceasefire), the 20 placed ones a leader rising to their area. All 41 are
  in the network, only the placed ones on the map. The most "network" of the map options.
- **C, a network diagram, no map.** Actors above (and the IAEA, dashed), the 41 repairs on a time axis, the areas and
  "no place published" below; a Lombardi-like web. No geography, so nothing can be read as a place; a second graphic.
- **D, the ceasefires as hubs.** The IAEA's seven ceasefires (and R44's, Reuters' word only) in a list column, spokes
  to the areas repaired under them, each labelled with who worked; the 31 repairs without a ceasefire faint. Only
  tells from October 2025.
- **E, the side in the rings.** Pass 5 with each ring styled by side (solid Ukrainian, dashed Russian, dash-dot both,
  dotted not said). The least change and not a network; dashed for the Russian side may read as less certain.
The three repairs the plant's channel reported that the dataset lacked, checked against the IAEA
(`sides/new_repairs_check.md`): 15-23 October 2026, a backup transformer at the thermal plant's switchyard repaired by
the Russian side under the IAEA's eighth local ceasefire, counted as **R48** (switchyard equipment, as R41 and R45b);
14 April 2026 is the dataset's R42, a protection trip with no repair (its sources added, still not counted); 8 November
2026 (today) is not counted for now as **R49**: only the plant's channel says a repair was done, and the IAEA doesn't
yet know the cause or place. The stills' axis runs to 30 November 2026 for R48 (pass 5's ends with September).
Also corrected: *Air Pressure* is by Lawrence Abu Hamdan (Earshot), not Forensic Architecture (pass 3's text above,
the scripts' and records' wording).

### Option C with the lines' own shapes (8 November 2026)

The user chose C and asked for versions that use the power lines' shapes in place of its flat time axis, as stills
(`scripts/repair_sides_c.py`; `sides/sides_C1..C4_1920.jpg`, `sides/sides_C_options_sheet.jpg`). Each repair is given
its line from `repairs.yaml`'s `line` (`sides.json` `line_of`): Ferosplavna-1 17 (the IAEA's "the 330 kV (back-up)
line" from late 2022), Dniprovska 14, the switchyards and their links 10, Kakhovska 750 kV 1 (R01). In C1-C3 a
position along a line is a date, never a place; in C4 a bead sits beside its area in date order. Every still says so.
- **C1, each line's shape as its own axis**: the lines laid flat left to right from the plant (their bends kept,
  flattened), one time scale for all, the switchyards a straight dashed axis (no one line); the actors above and the
  areas below as in C. A first try joined the two lines into one path, which put Ferosplavna-1's repairs on
  Dniprovska's shape by date: dropped.
- **C2, each line its own timeline**: the lines as OpenStreetMap has them (north up, one scale, no ground), time
  running out from the plant along each; the switchyards round a drawn ring. Crowded at the plant (most repairs are
  in 2022-23, when time is near the plant).
- **C3, time as distance from the plant**: year rings round the plant; each repair where its line crosses its date's
  ring; the switchyards on a drawn ray. Ferosplavna-1 and Dniprovska run side by side over the crossing, so repairs
  there sit close together.
- **C4, beads on the map**: pass 5's map, a bead per repair beside its area in date order, the unplaced in the bar.

Deleted by the user, 8 November 2026: A, B, D, C3 and C4 (stills, code and records). Kept: C, C1, C2 and E
(`sides/sides_sheet.jpg`); E is the one the user sees potential in.

### Prototypes beyond the lines (8 November 2026)

The user asked for still prototypes of the new ideas (`scripts/repair_sides_more.py`, `sides/proto_sheet.jpg`).
42 repairs, all with the sides as in `repairs.yaml`; each still says what is drawn.
- **E2, E3, E4: E's rings by side** (`sides_E2/E3/E4_1920.jpg`). E2 keeps every ring solid and orders them: Ukrainian
  outside, a gap, then the Russian side. E3 sets the side by brightness: white for Ukrainian, grey for the Russian side.
  E4 splits each ring: the north half for Ukrainian, the south half for the Russian side. Labels give the split by side.
- **Waiting bars** (`proto_waiting_bars_1920.jpg`): each repair a bar from when the line went down to when it came back,
  Ukrainian above the axis and the rest below. Cut dates come from each entry's `what` (`sides.json` `cut_dates`); a
  start given only to the month is faded, and a repair with no cut date is a ring. The three long waits are named.
- **Space-time stack** (`proto_spacetime_stack_1920.jpg`): pass 5's map tilted, each repair a ring over its area raised
  by its date, a year post, and the unplaced repairs in a column beside it. The tilt is a drawing, said on it.
- **Unit chart** (`proto_unit_chart_1920.jpg`): one square per repair, by side and then by line (the animation would
  move the same squares).
- **The sources' words** (`proto_sources_words_1920.jpg`): one line per repair as the source put it, with who did the
  work in bold and the English from `sides/who_repaired.md` under it. Lines too long for their column are cut with "…".
- **Punch card** (`proto_punch_card_1920.jpg`): areas × months, one mark per repair. A month with several repairs shows
  smaller marks two by two.

### The repairs in time: D3 gallery options 1-3 (9 November 2026)

The user asked for still previews of options 1, 2 and 3 of the D3 gallery proposal (4 and 5, parallel sets and a
beeswarm, to look at after). `scripts/repair_time.py` writes `time/data.json` and draws `time/time.html` (D3 7.9.0, the
unrolled film's copy) in the installed Chrome: `time/time_arcs_1920.png`, `time_calendar_1920.png`,
`time_deficit_1920.png`. None is a map, so the safety rule holds without doing anything special. The lines' states day
by day are the zoom-out's record (`networks.znpp.record`) read at the end of each day, with complete losses within a
day marked separately. Who did the work and the ceasefires come from `repairs.yaml`, and the cut dates from
`repair_sides_more.py` `CUT`. The marks are the same in all three: a dot per repair, white for Ukrainian crews, grey
for the Russian side, half and half for both, a faint ring for not said, and a ring round it for an IAEA-brokered
ceasefire.
- **1 Arcs**: each repair with a published cut date (29 of 42) is an arc from the cut to the repair. Ferosplavna-1 and
  the switchyards' links (grey) are above the axis, Dniprovska below, and the arc's width is the wait. Along the axis,
  each line's record is lit while connected and dotted where unreported. The three long waits are named (122 days,
  about 170, and 94 for Dniprovska, repaired but never reconnected).
- **2 Calendar**: one square per day, 24 February 2022 to 11 September 2026, lit by how many of the ten lines were
  connected at the end of the day. Unreported days are hatched, and a complete loss within a day is a black inset. The
  counts: 1,661 days, 7 with all ten lines, 1,302 with only one or two.
- **3 Deficit**: lines connected out of ten as a step area, with the gap up to ten shaded as lines cut off. Unreported
  days (March to December 2022) are a hatched range. Since 29 December 2022, never more than two of the ten were
  connected.

Then options 4 and 5, and calendar variations (the user, 9 November 2026: "do option 4 and 5. also do some other
variations of Calender option since i like that very much"). Same script, same marks (`time_options_sheet.jpg`,
`time_calendar_sheet.jpg`):
- **4 Parallel sets** (`time_parsets_1920.png`): each repair is a ribbon through who did the work, the year, the line,
  whether there was a ceasefire, and whether a place was published. Ribbons are shaded by who did the work.
- **5 Swarm** (`time_swarm_1920.png`): a dot per repair on its day, a row per line, nudged apart where days are close.
  Two spans are named: August to December 2022 (13 repairs), and from 18 October 2025, when 11 of the 12 repairs were
  under ceasefires.
- **5b Dots by month** (`time_dots_1920.png`): the same dots stacked by month, each underlined in its line's colour,
  over a strip of the calendar's shades for each month.
- **2b Split days** (`time_cal_split_1920.png`): the calendar with each day split, Ferosplavna-1 above and Dniprovska
  below, each lit while connected. 747 days with both, 555 with one of the two.
- **2c Every line, every day** (`time_cal_ten_1920.png`): a band per year, a row per line (all ten), a column per day.
- **2d Spiral** (`time_cal_spiral_1920.png`): the calendar's shades along a spiral, one turn per year, January at the
  top.
- **2e The days counted** (`time_cal_waffle_1920.png`): every day of the record as a square, grouped by lines connected
  (7 with all ten, 292 unreported, 747 with two, 555 with one, 60 with none), in date order within each group.

Kept from these (the user, 9 November 2026): the calendar, the split days and the days counted (the favourite, to be
worked on before it goes on the storyboard); the other stills were deleted. At the same clean-up: v2-v4's videos and
stills, the 8 November prototypes not kept (E2-E4, waiting bars, space-time stack, unit chart, sources' words, punch
card) and their sheet were deleted; their scripts and records stay.
- **2e in black and white** (`time/time_cal_waffle_bw_1920.png`, the user, 9 November 2026: "black and white (not
  yellow)"): the days counted in greys on near-black (all ten white, two light grey, one mid grey, none black with an
  edge, unreported hatched). The repair marks are outlined to show on both. Under each count are the group's first
  and last day and its repairs, and a black inset marks a complete loss restored within the day. The 42nd repair
  (23 October 2026) comes after the record's last report, and the still says it isn't shown.
- **2e in black and white, pass 2** (`time/time_cal_waffle_bw2_1920.png`, the user, 9 November 2026): only three
  marks, for repairs by Ukrainian crews, the Russian side and both (27, 6 and 1 within the record). The not-said mark,
  the ceasefire ring and the same-day loss inset are gone. A line under the key says what isn't marked: 7 repairs
  where the sources don't say who, and the 42nd, which comes after the record's last report. The dates have moved to
  the left: each row's first day sits right-aligned beside it, so time can be read down each group. The right column
  keeps the count, the label and the marked repairs.
- **bw3** (`time/time_cal_waffle_bw3_1920.png`, the user, 9 November 2026): the title says what is shown ("The plant's
  ten lines, day by day: how many were connected"), with a one-line subtitle (a square a day, a dot a repair). The
  key's marks each sit in a white square outline with no fill. The repairs whose sources don't say who did them are
  back as "unspecified" (black, ringed white): 41 marks, every repair within the record. The footer and the note on
  unmarked repairs are removed at the user's request, so the 42nd repair (23 October 2026, after the record's last
  report) is left out without a note on the still.
- **bw3 animated** (`time/repair_days_waffle.mp4`, with `_sheet.jpg`, `_last.png` and `.json`; the page's
  `cal_waffle_anim`, rendered by `repair_time.py --anim`; the user, 9 November 2026: "center the graphic ... each
  square can be animated to appear from left to right, top to bottom"; then: "show the circle mark key at the top ...
  since that is needed to understand what those marks are as the visual graphic is loaded in", "the entire
  visualization ... center aligned"; then, with a mockup: the squares moved to the centre of the frame, the dates left
  of each row, the counts right of each group's first row). The squares themselves are centred in 1920×1080: 392 px of
  ground left of the first column, 391 px right of the last (measured on the last frame). The dates sit in the gutter
  to the left; each group's count is top-aligned with its first row to the right, its words beside it, shortened to
  fit: DAYS · ALL TEN LINES; DAYS · LINES CUT, THE REPORTS DON'T SAY WHICH; DAYS · TWO LINES; DAYS · ONE LINE;
  DAYS · NO LINES: POWER LOST OR ISLAND MODE (68 px to the frame's right edge). The title's size is fitted so it spans
  the squares' width exactly (44.3 px), and the key's four items are spread across the same width, so title, key and
  squares share both edges. The block is centred vertically: 108 px above, 110 below. There is no subtitle and no
  footer. The title reads "1,661 days of war, a square for each; a dot for each repair", with the day count taken from
  the data. The key reads REPAIR BY UKRAINIAN CREWS, REPAIR BY RUSSIAN CREWS, REPAIR BY BOTH and UNSPECIFIED REPAIR.
  The motion, at 30 fps and silent, 21.4 s in all:
  - the title fades in over 0.8 s;
  - the key's four items fade in one after another from 0.9 s (0.15 s apart, done by 1.85 s), before any square;
  - from 2.2 s the squares appear one by one at a constant rate (1,661 in 12.5 s, to 14.7 s, each fading in over
    0.15 s), left to right and top to bottom, group after group, so each group's time on screen is its share of the days;
  - each row's date fades in as its row starts;
  - a group's count ticks up from its first square beside its label, and its repairs are counted once it is complete;
  - each mark pops in with its square (scale and fade, 0.25 s);
  - a 6.5 s hold from 14.85 s, with no fade-out.

  The last frame has bw3's content (41 marks). The timeline is in the json, with each group's start and end.
