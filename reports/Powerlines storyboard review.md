# Powerlines storyboard review

A review of the storyboard as it stood on 5 November 2026 (`storyboard.blend`, 10:09 with the end titles, 9:30
before them), read as someone new to the project would meet it: what the film says, in what order, how it feels, and
what should change before the presentation. At the user's request the changes that the storyboard can carry were then
made in it (8:17 before the credits; the last section says what was done and what still needs a render).

How it was read: three frames from every one of the 55 strips (cut and parked) were rendered from the .blend and laid
out as contact sheets (`libraries/conductive-seam/storyboard/review/`, kept out of the public repo since they hold
third-party frames). Every card was read as written; every shot's intent was checked against the pool
(`config/storyboard.yaml`), the outline (`docs/znpp-heart-plan.txt`), the story decision (NEXT.md N1) and the night
lights findings (N2).

## The verdict in one paragraph

The material is strong and the ethic is right: a satellite record that never invents, a 3D model that says what it
infers, a share of power drawn to scale, a sound that says it is synthesized, no sounds of fighting. What a newcomer
lacks is a line through it. The cut tells the story's end three times (at 2:00, 2:44 and 6:08), runs the record
forward twice, never shows why these two lines out of ten, and closes on 47 seconds of black cards after the film's
own last word. The fixes are mostly order and grammar, not new material: run time forward once, single out the two
lines early, keep the end for the end, and let fewer, better cards speak.

## What the film is trying to say

The decided story (N1, "A, the margin") is: **the plant's lines, built to carry its power out, now carry a trickle
in, and what they bring is time.** The margin wears thin on every side at once: lines cut 26 times, seven truces for a
single span, diesel, a cooling pond sinking toward its pumps, a reservoir gone. The water is the turn: the dam's
destruction moves the story from the lines to the ground. The ending is open: raise the water and drown a new forest,
or leave it and keep the plant without a river. One line of ten is left.

Every shot needed for that story is already in the cut. The problem is the order in which a viewer meets them.

## The cut as a newcomer meets it

| Time | What is on screen | What a newcomer understands | What goes wrong |
|---|---|---|---|
| 0:00–0:29 | Found footage of towers, small to large, the crossing over full water; POWERLINES | Power lines, somewhere, mattering | Good cold open. Silent. Rights uncleared |
| 0:29–1:19 | The plant's units outlined, ten lines leave and land; the full chord; "more than a fifth of Ukraine's electricity" | This plant feeds a country, through ten lines | The chord, the sound every later silence is measured against, plays 4.2 s before a black card cuts it |
| 1:19–1:46 | The record from 24 February 2022; the occupied area in red; the protection zone | The plant is seized, the lines go dark, the front is the river | The red shows the front, but nothing singles out the two lines that cross it: the question "why these two?" is never answered |
| 1:46–2:00 | "Occupied, shut down, still cooled"; the share bar | The plant now draws power in, almost nothing | "The last two lines" is said before any two lines have been shown |
| 2:00–2:44 | 11 September 2026 at the crossing over a drained bed; then night in 2026, 2021, 2022; the triptych; the monthly chart; "one line of ten remained" | The end: the reservoir is gone, the region is dark, one line is left | The dam's destruction (2023) is shown as already done, two minutes before the film tells it. The film's last line is spent at 2:44. Three day-to-night flips in 30 s |
| 2:49–3:36 | A 750 kV line singing in fog; "what they bring is time"; the countdown; the tower to scale; seven truces | Lines are loud even when they carry little; the plant lives on borrowed time | The fog's argument ("almost nothing carried, yet the full voice") was written to follow the share bar; the night chapter now separates them |
| 3:36–6:08 | The 3D flight south between the two lines, October 2022 to September 2026: full water, the drain, the bed, the plant | The two lines named at last; the water leaves; the record runs to the end | The record is told a second time, in full, after its ending has already been shown. 2:32 long: 27% of the film before the credits |
| 6:08–7:40 | The wells; the pond sinking; the paper's seepage claim; the section; the block | The plant's water is going | The claim is shown, but the film never says what its own test found (a slow fall, not a leak). 12.27 m on the card, 12.34 m in the section. The block repeats the section's three days |
| 7:40–8:52 | Raise the water? The forest; under the crossing (speculative); the proposed level drawn; "its future is tied to the water" | A choice between the forest and the reactor | Strong. `water-last` is written as the film's closing reflection |
| 8:52–9:30 | Three things before a restart; who wants the water back; another way, from the river | More considerations | Five cards in a row (47 s) after the closing reflection: the film ends twice and fades out on text |

### Time, as the viewer experiences it

24 Feb 2022 → Sep 2022 → **Sep 2026** → Sep 2021 → Sep 2022 → **Sep 2026** → (autumn 2021, elsewhere) → Oct 2022 →
Jun 2023 → **Sep 2026** → 2023–2026 again → the future.

A documentary can loop in time on purpose (a cold open on the end, then back), but only once, and then it says so.
Here the loops are a side effect of where pieces were cut from the zoom-out film, and each one spends a reveal: the
drained bed, the dark region and "one line of ten" all arrive before the story has earned them.

## The ten things that need to change, and why

### 1. Keep the end for the end

`zo-night-after` (11 September 2026, the crossing over the drained bed, the region dark) and `brief-7` ("By September
2026, one line of ten remained") are the film's ending. At 2:00–2:49 they pre-empt the dam, the 3D flight's drain and
the record's last state. **Why it matters:** the 3D flight is the film's centrepiece, and its turn (the water drains
under the lines) only lands if the viewer hasn't already seen the bed dry. "One line of ten" is the rhyme the outline
built the ending around. **Fix:** move the night chapter to after the flight (the flight ends at the plant on
11 September 2026; `zo-night-after` begins on that same date at the crossing and pulls back to the region at night),
and keep `brief-7` as the last card before the byline.

### 2. Show why these two lines

The presentation's first feedback was "why do we care about the power lines?" and the film's answer is these two: of
ten lines, the two that still cross the reservoir to Ukrainian-held ground, because the river is the front. The cut
shows the occupied area at 1:35 but nothing on it picks out the two lines; they are first singled out at 2:00 (in the
wrong chronology) and first named clearly at 3:36 in the 3D's corner labels. **Fix:** make `front-2022` do what you
asked of it: the two lines drawn bright over the red, crossing the river to the unshaded bank, labelled once ("the
two lines that cross the front"). A graphic change, not a new shot.

### 3. The night lights must not say the lines turned the lights off

You asked for the night lights further down "so that the impact of the powerlines being off is more impactful." That
is the reading to guard against. The findings (N2) say the opposite: the north bank went dark in March 2022 because of
wartime light discipline across government-held Ukraine (Dnipro too, far from the front), Enerhodar in 2024 after
strikes on its own supply, the occupied south in 2026 after strikes on its substations. None of it is the ZNPP's lines.
Edited right after the lines go dark, the dark region will read as their effect. **Fix:** keep the chapter as one
contained study, after the flight, and put the one honest sentence on screen ("the darkness is the war on the
region's grid; the satellite shows where it was dark, not why"). The study's real forensic finding is the night of
8–9 September 2022, when Enerhodar went dark and the plant stayed lit on its own reactor (island mode, the IAEA's
"complete black-out" of the town): the one night where the lights and the plant's power are actually linked, by a
source. That still (`nl-sep2022`) is parked and too small to read; remade as a graphic it is worth more than the
triptych, which repeats the three nights shown just before it. Also trim each zoom-out piece to its night hold:
today the chapter flips day, night, day three times in 30 seconds.

### 4. Fewer black cards, and each one doing one job

Fifteen cards fill 2:19 of the 9:30 (24%). They speak in four different voices in the same white-on-black form:
- the film's own stanzas ("What they bring is time"; "Its future is tied to the water");
- sourced facts ("16.65 in June 2023… 12.27 in October 2026");
- other people's words ("To flood this place again would be another crime");
- lists (restart-watch's three conditions).

A viewer can't tell the film's voice from a citation. In forensic film (Forensic Architecture, Josh Begley) the facts
sit on the evidence: a caption on the satellite frame, a number on the section, where the eye already is. The black
card is kept for the few sentences that turn the story. **Fix:** keep about six cards as stanzas (`one-fifth`,
`brief-2`, `brief-3`, `brief-5`, `water-last`, `brief-7`). Move the numbers onto the pictures they describe (the
pond's levels onto the section, the fuel and wells onto the 3D's last hold or the night chapter). Merge
`water-wells` with `water-pond`, and `water-voices` with `water-river`.

### 5. Silence means blackout: the cards are silent

In this film's grammar, silence has one meaning: the Hum goes silent when every line is cut (a complete loss of
off-site power). In the storyboard every card is silent, so every card plays as a blackout. **Fix, a decision to make
once:** under each card, the Hum holds the state of the record at that point (one or two voices, quiet); true silence
is kept for the losses.

### 6. Let the full chord be heard

The outline calls the full chord "the baseline every later silence is measured against." It plays 4.2 s, then a
black card. **Fix:** set "more than a fifth of Ukraine's electricity" as a caption over the settled frame, not a card,
and re-render the zoom-out without its two night holds (N2's render option) so the chord can run about 10 s
unbroken.

### 7. The water chapter needs its conclusion on screen

The seepage figure is the most forensic beat in the film: a published claim ("many places where seepage is taking
place") followed by the film's own test. But the test's result is never said. As cut, the viewer sees the claim, then
a section, and is left to infer that the paper was right. **Fix:** one caption on the section: what the passes show
(the pond falling toward the pumps' 12 m, the rate a slow fall, not a sudden loss). Fix the number:
`water-pond` says 12.27 m (October 2026, HUR), the section 12.34 m on its 2026 day; give the section's date on
screen or end the card on the section's figure. The pool's own advice for `section-block` holds: it repeats the
section's three days, so open with its first 11 s (the region opened in 3D), then the claim, then the section.

### 8. Say the question and the method once

You deleted the research question and the method card. Both had problems (my wording), but the film still needs
what they did: a viewer must know within the first minute what is observed (satellite passes, the IAEA's record),
what is drawn (lines, zone, flow) and what is inferred or speculative (the bed's heights, the 3D models, the scene
under the crossing). The labels exist on individual shots, but without the rule stated once they read as small print.
**Fix:** one line, over `zo-plant` as the units are outlined, rather than another black card.

### 9. Let the human absence be stated, once

No one who mends the lines, runs the plant or lives under the lines appears, and that is right for a film about a
place no one can reach. But the absence should be said, not just felt. `the-gap` ("Repaired by: 'technicians'",
IAEA, 8 November 2025) does it in three words, and it is parked. **Fix:** put it right after `brief-5` ("…so that a
crew could mend a single span of wire"). `water-voices` is the only place people speak; keep its two voices, one on
each side of the choice.

### 10. Make the graphics one family and readable

At 720p the zoom-out and 3D read well. The research figures don't yet:
- `nl-monthly-chart`: a light-grey matplotlib chart in a film of black grounds;
- `share`, `tower-elevation`: type too small to read in the time on screen;
- the section: hairlines on near-black;
- `seepage-paper`: the quote at the foot is unreadable at 720p.

These are drafts (the pool says so), but they decide whether the film reads as a forensic visualisation or as a slide
deck. **Fix:** one graphic language for all of them: black ground, white capitals, the lines' two yellows, one size of
caption.

## Length

The length that matters is before the credits (about 7 minutes preferred, 10 works). The user's cut is 9:30; the
proposal is 8:44. Most of the rest is in two places:
- **The 3D flight: 2:32.** A re-render at a quicker pace through the bed (about 30 s saved) is better than trimming
  it, since trims make its record's dates jump.
- **The cards: 2:19.** Merging two pairs and moving the numbers onto pictures saves about 40 s.

With those, the proposal comes to about 7:30. Further candidates if needed: `fog-crackle` to 10 s,
`under-the-crossing` to 24 s, the night chapter's three pieces trimmed to their holds.

## The intent of each kind of material

| Kind | Shots | What it is for | How it reads now |
|---|---|---|---|
| The zoom-out | `zo-*` | The spine of evidence: where, what, and the dated record, every state sourced | Clear and confident; the best-made material. Cut into pieces, it loses the continuity that made the record legible |
| The 3D flight | `3d-south-*` | Experience: being between the two lines over four years, the water leaving under them. Inferred heights, said so | Immersive and the right centrepiece; too long relative to the rest; it repeats the record the zoom-out already told |
| Sections and block | `section-*` | Measurement: the levels side by side, at one scale | The most "computational design" sequence; dark and thin at preview size; its result needs saying |
| Found footage and recordings | `tower-cut`, `fog-crackle` | Other people's views and sounds of these lines; the human scale | Good and honest (recorded elsewhere, said so); rights uncleared |
| Research stills | `front-2022`, `share`, `tower-elevation`, `seepage-paper`, `nl-*` | Single facts, held | Uneven style; several unreadable at their length |
| The speculative scene | `under-the-crossing`, `waterline-reprise` | A proposal, not evidence: what the bed under the line might be now, and what the raised water would cover | The film's most beautiful moment; labelled speculative; earns its place at the end |
| Cards | 15 | Stanzas, facts, quotes and lists | Too many, in one form for four voices (item 4) |

## Tone: tasteful, informative, forensic

What already works:
- **The evidence rules:** nothing generated, the drawn and inferred said to be.
- **Restraint:** no fighting sounds, no damage spectacle, safety-regions only.
- **Proportion:** the share drawn to scale (a sliver on an empty bar says more than a number).
- **The sound as argument:** a line carrying 11 MW sings as loud as one carrying a gigawatt.

The risks, beyond the ones above:
- **Alarm.** `brief-4`'s "a countdown begins" is sourced, but N1's own caution applies: this is a margin wearing thin
  (days to weeks), not hours to disaster. Keep the countdown's length on screen ("the longest loss lasted a month") so
  it doesn't read as a thriller.
- **Whose sources.** Energoatom is a party, and so is HUR (the card says so). The occupied area is an open-source
  assessment (DeepStateMAP; the frame says so). Keep saying it.
- **Beauty.** The speculative scene is lovely, which is right for an ending about what the ground could be. It needs
  its label on screen as it begins, not only in the credits.
- **Ending on uncertainty.** `water-river`'s "The choice has not been made" is an excellent last line for the water,
  and `brief-7` is the right last line for the film. Today both are competing with three other cards.

## The set-aside shots (parked, past END)

Low priority, as you said. Rated by what each would add if time allowed:

| Shot | Value | Where it would go |
|---|---|---|
| `the-gap` ("Repaired by: 'technicians'") | **High**, 8 s | After `brief-5` (item 9); in the proposal |
| `nl-sep2022` (the town dark, the plant lit, 8–9 Sep 2022) | **High** once remade | The night chapter's forensic core (item 3) |
| `fig-crossing` (the two lines over the water, 2023 pass) | Medium | Its job is better done on `front-2022` (item 2); its drained bed spoils the dam if shown early |
| `diesel` ("eighteen days on diesel… little more than a week of fuel") | Medium | The sharpest fact for the countdown; could replace `brief-4`'s second sentence |
| `unrolled-*` (the two lines unrolled, the whole record) | Medium | The clearest data visualisation of the record, but it is the record a third time; `unrolled-overview` (14 s, the whole record at once) could replace part of the 3D's middle |
| `fig-truces` (seven truces on a timeline) | Low | Overlaps the unrolled and the 3D |
| `nikopol-cannot-hear`, `weather`, `proxy-330` | Low | A sound essay of their own; a talk, not this film |
| `nl-monthly-maps`, `zo-record-begins` | Drop | Repeat the chart and the zoom-out |
| `restart-watch` (parked in the proposal) | Medium | The most forensic list in the film ("monitored, not words and rumours"), but it overlaps `water-wells`; fold its pumping-station line in there, or let it follow the section |

## The proposed order

First built beside the user's cut as `proposal.blend` (8:44), then made the storyboard itself (below). Order and why:

| | Shots | Why |
|---|---|---|
| Opening | `tower-cut`, `title` | Unchanged |
| The plant before | `zo-plant`, `zo-chord`, `one-fifth` | Unchanged (item 6 for later) |
| The war | `zo-war`, `front-2022`, `zo-zone` | Unchanged; `front-2022` to carry the two lines (item 2) |
| Power in | `brief-2`, `share`, `fog-crackle` (14 s), `brief-3` | Share and fog back together: almost nothing carried, the full voice, then "what they bring is time" |
| The countdown | `brief-4`, `brief-5`, **`the-gap`**, `tower-elevation`, the 3D flight | The truces, then who mends them, then the tower they climb, then four years between the two lines |
| At night | `zo-night-after`, `zo-night-2021`, `zo-night-2022`, `nl-monthly-chart` | After the flight reaches 11 September 2026: after, before, during, the plant one of the last lights on |
| The water | `water-wells`, `water-pond`, `section-block` (11 s), `seepage-paper`, `section-dniprovska` | How the plant is kept alive, then its water going; the region opened, the claim, the test |
| What next | `water-dam`, `forest-or-reactor`, `water-voices`, `water-river` | The proposal, what it would drown, the two voices, "the choice has not been made" |
| The end | `under-the-crossing`, `waterline-reprise`, `water-last`, `brief-7` | The speculative scene, the level drawn, the film's reflection, one line of ten |
| End titles | `byline`, `credits`, `credits-record`, `credits-footage` | Unchanged |

Parked in the proposal: `restart-watch` and `nl-triptych` (both repeat what sits next to them). Time runs forward once
(2022 to 2026 in the record and the flight; the night chapter's look back is framed as a look back), the end is kept
for the end, and the cut is 8:44 before the credits.

## For the presentation

The film in five sentences:
1. Ten power lines leave the Zaporizhzhia plant; before the war they carried more than a fifth of Ukraine's electricity.
2. Since its seizure the plant makes nothing, and the lines carry a trickle back in to keep its fuel cool: what they
   bring is time.
3. Twenty-six times every line was lost; seven times the war paused so a crew could mend one span.
4. When the dam was destroyed, the reservoir under the last two lines drained, and the plant's own water began to go.
5. Raise the water again and a new forest drowns; leave it, and the plant has no river: the choice hasn't been made,
   and one line of ten is left.

What the project investigates, as open questions for the room (each already in the research, none settled):
- **The margin.** How long can a shut-down plant live on one line and diesel, as both wear down at once?
- **The water.** Is the cooling pond leaking (the paper) or falling slowly (the film's passes)? What level stops its
  pumps?
- **The dark.** Why did Enerhodar go dark in 2024, before the rest of the occupied south?
- **The ground.** What is the bed now? No one has recorded at the crossing since the breach. The bed's heights are
  inferred, and the frog in the soundscape was recorded 97 km away.
- **The people.** Who mends the lines? The record names no one.
- **The choice.** Water or forest, restart or not, and who decides for a plant on occupied ground?

Before any public screening, rights: the found footage (`tower-cut`), the 750 kV fog recording (Ted3871), the paper's
Figure 11 (Taylor & Francis), DeepStateMAP's map, and FABDEM's non-commercial licence.

## Made in the storyboard (5 November 2026)

At the user's request, the proposed order went into `storyboard.blend`, with what the storyboard can carry:
- **Order:** the proposed order above. `the-gap` is back; `restart-watch` and `nl-triptych` are parked.
- **Trims:** `fog-crackle` to 14 s; `section-block` to its first 11 s; the 2021 and 2022 night pieces to their nights
  only (45–51 s and 69–75 s of the zoom-out), so the chapter no longer flips day to night.
- **Two merged cards** from the four, every fact and source theirs:
  - `water-cooling` (the wells and the pond) replaces `water-wells` and `water-pond`;
  - `water-choice` (the two voices, another way, "the choice has not been made") replaces `water-voices` and
    `water-river`. The four originals are parked.
- **Captions on the picture** (a new `caption` in the pool, drawn in the films' caption style):
  - the method over `zo-plant` (item 8; removed by the user the same day);
  - the two lines that cross the river over `front-2022` (item 2, until the graphic is made);
  - that the dark isn't the lines' over `zo-night-after` (item 3);
  - the section's result over `section-dniprovska` (item 7);
  - "speculative" over `under-the-crossing`.
  - The user removed all five captions the same day; the `caption` field stays in the build for later use, unused.
- **Length:** 8:17 before the credits.

Still to do, because each needs a render or a decision rather than an edit (NEXT.md N1):
- the two lines drawn on `front-2022`;
- the zoom-out without its night holds, so the chord runs longer;
- a quicker 3D flight over the bed;
- `nl-sep2022` remade;
- one graphic family for the figures;
- the Hum under the cards;
- the pond's 12.27 m against the section's 12.34 m.

