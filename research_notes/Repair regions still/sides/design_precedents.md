# Who repaired the lines: design precedents for a network of actors and repairs (8 November 2026)

These are research notes for the next pass of `repair-regions` (v5: `../v5/repair_regions_v5_1920.jpg`). It is one
graphic of about 8 seconds: white rings round 6 coarse regions on a near-black map, red lines, and a timeline at the
foot. The user's idea is to add lines from the Ukrainian side or the Russian side to each repair, depending on whether
the reports say one side did the work or both did (the IAEA-brokered truces, where each side repaired its own part).

Nothing in the project was changed. Precedents are described as far as the pages could be checked. Anything not
confirmed is marked *(unverified)*.

## 0. Before the precedents: what the data allows

### Who did the work, from `repairs.yaml`

This is a hand count of the `who` field, so recount it before any caption.

| Who the sources say | Placed (20) | Unplaced (21) | All (41) |
|---|---|---|---|
| Ukrainian (Ukrenergo crews, "Ukrainian technicians / engineers / specialists"; R15 only implied) | 6 | about 10 | about 16 |
| Both sides ("technicians on both sides of the frontline", "specialists from both Ukraine and Russia") | 3 (R35f, R35d, R45) | 0 | 3 |
| Russian side only (R41: "Rosatom's repair crews", one Russian outlet; the IAEA doesn't say) | 1 | 0 | 1 |
| Not stated ("technicians", "engineers", or nothing) | 10 | about 11 | about 21 |

So the honest picture is mostly Ukrainian links, three shared ones, one single-source Russian link, and about half
with no actor at all.

- A design that draws two symmetrical sides will look balanced. The data is not balanced, and the graphic must not
  imply that it is.
- "Not stated" is the biggest class. It needs a visual form of its own, not just the absence of a line.

### Ceasefires aren't the same as "both sides did this repair"

Several switchyard repairs were made under IAEA ceasefires, but the record says "not stated" or just "Technicians"
for who worked on them.

- A truce is an arrangement between both sides, brokered by a third party. It is not proof that both sides' crews
  worked on that repair.
- R35f and R35d are one truce: work on Ferosplavna-1's Ukrainian-held stretch and Dniprovska's occupied stretch. The
  IAEA says "technicians on both sides of the frontline" without saying who worked where. It is an inference, though a
  strong one, that the occupied side's crew were the Russian-installed management's. The record marks R35d "who worked
  on this side not stated".
- The safe reading: one "both sides (IAEA)" link to the truce as a whole, not a Ukrainian link to one region and a
  Russian link to the other.

Three relations therefore need visibly different marks:

1. **Did the work** (a crew or operator named).
2. **Brokered or monitored** (the IAEA).
3. **Unknown who.**

### Where the actors' ends may sit

This follows from CLAUDE.md and NEXT.md I5.

- An actor's end of a line may not be a crew's position, a substation's place (never Dniprovska's) or a pin.
- It can be:
  - a **side of the front** (allowed as a region: "the Ukrainian-controlled side", "the occupied side");
  - an **edge of the frame**;
  - a **node off the map** (in the foot bar, a margin column, or a legend).
- "Origins that are abstract, not geographic" is the main design problem, and most precedents below are about it.

### A correction to the README's attribution

*Air Pressure* is by **Earshot** (Lawrence Abu Hamdan's investigative agency), not Forensic Architecture. Abu Hamdan
has worked with Forensic Architecture, and the website was designed and programmed by Moritz Ebeling. See
[airpressure.info/about](https://airpressure.info/about). The README's pass 3 says "Forensic Architecture's *Air
Pressure*". That is worth fixing in the credits and notes.

---

## 1. Earshot: *Air Pressure* / AirPressure.info (2021–22)

**Links:** [airpressure.info](https://airpressure.info) ·
[about](https://airpressure.info/about) ·
[L'Orient-Le Jour on the platform](https://today.lorientlejour.com/article/1302855/22111-israeli-military-aircraft-have-violated-lebanese-airspace-since-2007.html) ·
[Middle East Eye](https://www.middleeasteye.net/news/lebanon-israel-air-incursions-massive-scale-detailed) ·
the sister work *Air Conditioning* at the [12th Berlin Biennale](https://12.berlinbiennale.de/artists/lawrence-abu-hamdan/)

**What it is.** A database and map of about 22,000 Israeli military overflights of Lebanon, 2007–2021. It was built by
hand-transcribing the radar records in Lebanon's letters to the UN Security Council, which give each violation's time,
duration, aircraft type and route.

**Technique.**
- Every route is drawn as a looping trace. Reviewers describe the aggregate as "overlapping circles that covered most
  of the country" and "a cluster of loops".
- The density of the loops is the argument.
- A typical route enters over the southern border (most often over Kfar Kila), circles, and leaves over the sea at
  Naqoura. So each trace starts where it enters the frame, not at an airbase.
- Month and year filters show one stretch at a time. The sister installation works by accumulation: one centimetre per
  day over fifteen years.

**Uncertainty.** The routes are only as fine as the source letters, which name places and regions, not coordinates.
That is the same kind of coarse, text-named geography as the repair records. *(unverified: exactly how the site
interpolates between named places)*

**For this graphic.**
- The strongest permission it gives: **an actor's line can begin at the edge of the frame or at a border, not at a
  base.** Overflights enter "over the southern border". A Ukrainian crew's link can likewise enter "from the
  Ukrainian-controlled side", a whole side, not a depot.
- Its rings-of-routes style is already the v3–v5 look. The precedent supports keeping links thin, white or near-white,
  and many-layered, so the accumulation reads as density, not as a diagram.

## 2. Mark Lombardi: *Narrative Structures* (1994–2000)

**Links:** [Wikipedia, with images](https://en.wikipedia.org/wiki/Mark_Lombardi) ·
[Cabinet, Spring 2001, Lombardi's own notes](https://cabinetmagazine.org/issues/2/lombardi.php) ·
[Robert Hobbs, *Global Networks* (PDF)](https://www.gwern.net/doc/history/2003-hobbs-marklombardiglobalnetworks.pdf) ·
[NPR, 2003](https://www.npr.org/2003/11/01/1487185/the-conspiracy-art-of-mark-lombardi)

**What it is.** Pencil drawings of networks of finance and politics (BCCI, Iran-Contra, Harken Energy), every link
taken from public records.

**Technique.**
- Names sit on large arcs and circles. Lines between them carry a legend of relation types, such as "some type of
  influence or control", "sale or transfer of an asset" and "flow of money, loans or credits".
- Lombardi's notes speak of "radiating arrows and broken lines" for hierarchy and the movement of funds, and red for
  legal actions (lawsuits, indictments).
- Several drawings are laid on a timeline: years run left to right and names arc off it.
- Stacked parallel lines set the time frame.

**Uncertainty.** The method is strict sourcing: if it isn't in the record, it isn't drawn. Relation *types* are kept
apart in the legend. That is the move needed here: "did the work" vs "brokered" vs "reported only by one side's media".

**For this graphic.**
- A **small legend of relation types, drawn as line styles, not colours**:
  - solid: did the work, named;
  - double: both sides, under a truce;
  - thin arc to a third node: brokered by the IAEA;
  - dotted: who not stated.
- The timeline-anchored layout fits the existing foot bar. Actors can sit *on the timeline's band*, with arcs rising
  from it to the regions on the map. Lombardi's arcs are what such links should look like: wide, graceful curves, never
  straight spokes that read as trajectories.
- Lombardi's red-for-legal-action suggests a single accent colour for the one class that needs flagging. Here that
  might be the single-source Russian claim.

## 3. Forensic Architecture: the Ayotzinapa platform (2017)

**Links:** [FA investigation page](https://forensic-architecture.org/investigation/the-enforced-disappearance-of-the-ayotzinapa-students) ·
[openDemocracy walkthrough](https://www.opendemocracy.net/ayotzinapa-platform-what-happened-to-43-dis/) ·
[ICA: the actor timelines mural](https://www.ica.art/exhibitions/forensic-architecture-counter-investigations/recent-investigations/the-enforced-disappearance-of-the-43-ayotzinapa-students) ·
[Intercept report via PV Angels](https://www.pvangels.com/news-mexico/183419/new-platform-reveals-cracks-in-ayotzinapa-story)

**What it is.** An interactive map and timeline of thousands of events and hundreds of actors (students, police,
military, cartel members) on the night of 26–27 September 2014, with communications between actors. It was built with
Centro Prodh and EAAF.

**Technique.**
- Actors are filters and **lanes**. The exhibition mural plots each actor group's timeline in parallel.
- Communications are coloured lines between actors.
- **Events with a time but no location appear on the timeline only, not on the map.**

**Uncertainty.** "No location" is treated as a legitimate state of an event, shown in the time view, never forced
onto the map.

**For this graphic.** This is the precedent for the **21 unplaced repairs**.
- They already live as grey ticks in the foot bar. Give them their actor links *within the bar*: a short link from the
  Ukrainian lane to a grey tick, a dotted stub for "not stated".
- They then take part in the network without ever touching the map.
- The map shows where (coarsely, when published). The bar shows who and when for all 41.

## 4. Forensic Architecture: Timemap and Pattrn (2014–2018)

**Links:** [Timemap on GitHub](https://github.com/forensic-architecture/timemap) ·
[release note](https://engineering.forensic-architecture.org/timemap-release) ·
[FA: Timemap for cartographic platforms](https://forensic-architecture.org/investigation/timemap-for-cartographic-platforms)

**What it is.** FA's open tool for events in time and space: a map coupled to a zoomable timeline, with events tagged
by category and drawn in a style per category. It was used for Ilovaisk, among others.

**Technique.**
- The map and timeline are brushed together.
- Categories are encoded by colour and shape, and "narratives" step through selected events in order.

**Uncertainty.** Events carry their source. Location precision is a property of the event, and coarse events are
drawn as areas or left off the map.

**For this graphic.**
- The "narrative" mode is the 8-second sequence: step through repairs in time, with each one lighting its region
  (where placed), its tick and its actor link at once.
- It argues for the **map and the bar as one coupled system**: the actor's link joins the bar to the map, rather than
  the map hosting the actors.

## 5. Forensic Oceanography with SITU Research: *The Left-to-Die Boat* (2012)

**Links:** [FA investigation page](https://forensic-architecture.org/investigation/the-left-to-die-boat) ·
[SITU Research project](https://situ.nyc/research/projects/forensic-oceanography-report) ·
[drift map (PDF, GISTI)](https://www.gisti.org/IMG/pdf/carte_forensic_oceanography_2012_map_of_the_boat_drift_trajectory.pdf) ·
[full report (FIDH PDF)](https://www.fidh.org/IMG/pdf/fo-report.pdf)

**What it is.** The drift of a migrant boat inside NATO's surveillance area in 2011. The map attributes responsibility
to the vessels and states that were present.

**Technique.**
- **Responsibility is spatial but not point-like.** The argument rests on areas of surveillance and jurisdiction
  (NATO's maritime zone, search-and-rescue regions).
- Vessels are shown where AIS and satellite radar put them, with stated detection limits: radar only finds ships over
  about 50 m.

**Uncertainty.**
- Detection thresholds are printed.
- Actors are named only as far as the evidence goes ("a military ship", not a named one, where unidentified).

**For this graphic.**
- The model for **actors as areas of jurisdiction**: "the Ukrainian-controlled side" and "the occupied side" are each
  a responsibility zone, as NATO's area was.
- A link "from the Ukrainian side" can rise out of the *whole* north-bank tint (or a band along the frame edge on that
  side), never out of a point.
- It also models the wording: name an actor only as far as the source does ("Ukrenergo crews", "technicians on both
  sides", "a Russian outlet says Rosatom's crews").

## 6. Moritz Stefaner, Dario Taraborelli, Giovanni Luca Ciampaglia: *Notabilia* (2011)

**Links:** [Truth & Beauty project page](https://truth-and-beauty.net/projects/notabilia) ·
[Taraborelli's notes](https://nitens.org/w/notabilia/) ·
[FlowingData](https://flowingdata.com/2011/01/11/visualizing-deletion-discussions-on-wikipedia) ·
[Vice](https://www.vice.com/en/article/infographic-explores-deletion-discussions-on-wikipedia)

**What it is.** The 100 longest Wikipedia "Articles for Deletion" debates. Each debate is a thread from a common origin
at the bottom centre, made of one segment per vote. Keep votes bend it left (green) and delete votes bend it right
(red), so a debate's path is its history.

**Technique.**
- **Direction is abstract, not geographic.** Left and right mean the two sides of a dispute.
- Each item grows segment by segment over time.
- The aggregate is a fan of curves whose spread shows how contested the debates were.

**Uncertainty.** Neutral or mixed votes give straighter paths, so ambiguity is visible as a lack of bend.

**For this graphic.** The closest answer to "lines from one side or the other" that needs **no geographic origin**.
- Each repair's link is a short curved stroke from its ring (or its tick) that **leans** toward one side of the frame:
  - Ukrainian: leans one way;
  - Russian side: leans the other;
  - both: splits into a fork;
  - not stated: rises straight up, grey or dotted, and stops short.
- In the foot bar this could be a fan of small strokes over the ticks: a "Notabilia" of the 41.
- Direction carries meaning without saying where anyone stood.
- Keep the sides' conventional orientation consistent with the map, Ukrainian-held north, so it isn't contradicted.

## 7. Charles Joseph Minard: Napoleon's Russian campaign (1869)

**Links:** [Edward Tufte on Minard](https://www.edwardtufte.com/?p=677) ·
[Michael Friendly's Minard biography (PDF)](https://www.datavis.ca/milestones/uploads/files/minard/biography.pdf) ·
[Esri, *Mapping Time*, sample page (PDF)](https://esri.com/content/dam/esrisites/en-us/esri-press/book-pages/sample-page/mapping-time-illustrated-minards-map-napoleons-russian-campaign-1812.pdf) ·
[Popular Science](https://www.popsci.com/greatest-infographic-history/)

**What it is.** A flow map: band width is the army's size, tan for the advance and black for the retreat. A temperature
chart along the foot is tied to the retreat by vertical leaders.

**Technique.**
- Two tones for two directions or sides.
- A secondary time-series in a strip below the map, joined to the map by thin vertical lines.

**Uncertainty.** None explicit. It shows that a two-tone, one-accent system stays legible at very high density.

**For this graphic.**
- The **map-above, chart-below, with vertical leaders** structure is exactly v5's foot bar.
- Minard's leaders from the temperature line up to the retreat are the model for links from the bar's actor lanes up
  to the regions. They are vertical or near-vertical, so they read as "this event belongs to that place", not as
  movement across the land.
- Two tones: the lines are red, so the two sides can't be red and white. Use **white vs a cool grey, or white vs
  hatched**, and keep red for the power lines.

## 8. Hive plots and bipartite layouts (Martin Krzywinski et al., 2012)

**Links:** [hiveplot (BCGSC)](https://mk.bcgsc.ca/linnet) ·
[the paper, *Briefings in Bioinformatics* (PDF)](https://salsa.lezzo.org/bparodi/UniTO/raw/branch/master/anno3/avrc/bbr069.pdf) ·
[ggraph's hive layout](https://ggraph.data-imaginist.com/reference/layout_tbl_graph_hive.html)

**What it is.** A network layout where nodes sit on a few fixed radial axes, by rule (type on the axis, a property
along it). Edges are curves between axes.

**Technique.**
- The layout is **deterministic and meaningful**: position means something, unlike force-directed "hairballs".
- The ggraph documentation advises no more than three axes.

**Uncertainty.** Not addressed, but a fixed layout makes absence visible: an empty stretch of an axis is a fact.

**For this graphic.** An alternative ending shot (the "whole record fitted to the frame"), or a margin diagram.
- Three axes:
  - the Ukrainian grid operator and crews;
  - the plant's Russian-installed management and Rosatom;
  - the IAEA (brokered or monitored).
- The 41 repairs sit on a time axis.
- Each repair is joined to the axes its sources name. Unknown-who repairs sit on the time axis with **no edge**, so the
  gaps show.
- It is abstract enough that no actor has a position. It's a cut-away from the map, though, so it may suit the end
  hold more than the 8-second build.

## 9. PeaceRep: the PA-X peace agreements actor network

**Links:** [PA-X introduction](https://peacerep.org/publication/introducing-pa-x-a-new-peace-agreement-database-and-dataset/) ·
[actor tracker, example: Ethiopia](https://pax.peaceagreements.org/tracker/ethiopia/actors) ·
[Iraq](https://www.peaceagreements.org/tracker/iraq/actors/) ·
[agreement timelines](https://messy-timeline.onrender.com/)

**What it is.** More than 2,000 peace and ceasefire agreements, 1990–2024. The actor network graphs link agreements
(navy squares) to actors (circles coloured by type). **Edges are grey for a party signatory and orange for a third
party** (mediator or guarantor).

**Technique.** A bipartite graph of agreement and actor, where **the edge style carries the role**, not the node.

**Uncertainty.** Roles are only those on the signed text, so the database records what was signed, not who did what
on the ground.

**For this graphic.** The vocabulary for the **IAEA truces**.
- A truce is an "agreement" node (it could be a small hatched rectangle on the timeline, as the unrolled film already
  hatches the truces).
- The two sides are linked to it as parties (the plain line style). The IAEA is linked as a third party (a distinct
  style: thinner, or dashed).
- The repair ring is then linked to the truce, not straight to the sides.
- This captures "each side repaired its part, under an arrangement brokered by a third party" without claiming which
  crew worked where.

## 10. Alluvial and Sankey diagrams over time (Rosvall and Bergstrom, 2010)

**Links:** [*Mapping change in large networks* (arXiv)](https://arxiv.org/abs/0812.1242) ·
[the higher-order extension, *Applied Network Science* 2023](https://link.springer.com/article/10.1007/s41109-023-00572-5)

**What it is.** Streams whose height is the volume in each category, flowing between time slices, splitting and
merging.

**Technique.** Categories as stacked streams over time. Membership changes show as ribbons crossing.

**Uncertainty.** An "unclassified" stream can be drawn like any other. Its size is then a visible fact.

**For this graphic.** A modest form fits the foot bar: three thin streams (Ukrainian, both, not stated) whose
thickness accumulates with each repair.
- The "not stated" stream will be about as thick as the Ukrainian one. Saying that plainly is the honest headline
  ("about half of the repairs were never attributed").
- It also handles the one Russian-only claim as a hairline, its weakness visible.
- It could replace the tick row at the end hold.

## 11. Edge bundling and flow-map layout (Holten and van Wijk, 2009, and successors)

**Links:** [*Force-Directed Edge Bundling for Graph Visualization*](https://diglib.eg.org/handle/10.1111/v28i3pp0983-0990) ·
[*Composite Flow Maps* (Cornel et al., Eurographics 2016, PDF)](https://www.cg.tuwien.ac.at/research/publications/2016/Cornel2016CFM/Cornel2016CFM-paper.pdf) ·
[Anita Graser, edge bundling for flow maps](https://anitagraser.com/2017/10/08/movement-data-in-gis-8-edge-bundling-for-flow-maps) ·
[*Force Directed Flow Map Layout* (2014)](https://scitepress.org/Documents/2014/47446/)

**What it is.** Edges attract each other like springs and merge into bundles. Flow maps draw origin–destination flows
as trees from one source.

**Technique.**
- Many links from one origin share a trunk and split near their ends.
- Flow trees (one source to many sinks) are the standard form.

**Uncertainty.** Bundling **adds** visual meaning (shared routes) that isn't in the data, and the papers say so.

**For this graphic.**
- If links leave a margin anchor or a side band, bundle them into **one trunk per actor** that splits to the regions.
  Twenty links then read as three or four calm strokes, which suits "white lines on dark".
- **Caution:** a bundled trunk across the river looks like a route crews took. Keep the trunks off the land: in the
  foot bar or the frame margin, or rising vertically like Minard's leaders. Say "drawn" in the note, as the areas are.

## 12. Laura Kurgan and the Center for Spatial Research, Columbia

**Links:** [*Conflict Urbanism: Aleppo*, urban destruction](https://aleppo.c4sr.columbia.edu/urban-destruction/index.html) ·
[its remote-sensing notes](https://aleppo.c4sr.columbia.edu/remote-sensing.html) ·
[*EXIT* (with Diller Scofidio + Renfro, Hansen, Rubin; DS+R page)](https://dsrny.com/project/exit) ·
[Stewart Smith on *EXIT*](https://www.stewartsmith.io/work/exit) ·
[*Million Dollar Blocks* at MoMA](https://www.moma.org/collection/works/110423)

**What it is.**
- *Conflict Urbanism: Aleppo* layers UN damage data on imagery and states its gaps outright: imagery pairs sometimes 5
  days apart, sometimes 900, and thresholds for "significant" change.
- *EXIT* (2008, updated 2015) is an animated, timed data film on migration from more than 100 sources, shown as a
  panorama. Flows run between abstracted places.
- *Million Dollar Blocks* shifted the unit of the map from crime locations to where public money goes.

**Technique.**
- Gaps and thresholds are part of the content, not footnotes.
- The unit of mapping is chosen to make an argument without exposing individuals.
- In *EXIT*, animated arcs grow over time and data and sound are timed together.

**Uncertainty.** Kurgan's book *Close Up at a Distance* is a long argument about what a map's apparent precision hides.

**For this graphic.**
- *Million Dollar Blocks* is the clearest precedent for the safety rule: **change the unit** from crew to side or
  operator so individuals are never exposed.
- *EXIT*'s growing arcs are a reference for how links appear over the 8 seconds.
- Aleppo argues for one plain sentence on screen about what isn't known (who did half the repairs), not only a
  footnote.

## 13. Domain precedents: ZNPP line maps (Bellona, Al Jazeera, Greenpeace and NYT)

**Links:** [Bellona map of the plant's lines](https://bellona.org/?p=38075) ·
[Bellona Russian-language digest](https://etc.bellona.org/?p=111035) ·
[Al Jazeera, Mapping the Zaporizhzhia NPP (Sept 2022)](https://www.aljazeera.com/news/2022/9/4/infographic-ukraines-zaporizhzhia-nuclear-power-plant) ·
[Greenpeace Ukraine, *Powerline Zaporizhzhya NPP*](https://www.greenpeace.de/publikationen/Powerline_Zaporizhzhya_NPP.pdf) ·
[Kyiv Independent on the NYT and Greenpeace power-line story (May 2025)](https://kyivindependent.com/russia-builds-power-lines-to-connect-occupied-zaporizhzhia-nuclear-plant-to-its-grid-nyt-reports) ·
[Reuters explainer, Aug 2022 (via investing.com)](https://investing.com/news/commodities-news/explainerzaporizhzhias-power-lines-ramparts-against-nuclear-meltdown-2880279)

**What they are.**
- Bellona's map: four 750 kV lines in blue and six 330 kV lines in yellow, with the **alleged damaged section of
  Dniprovska circled in red**.
- Al Jazeera: a 2022 explainer graphic.
- Greenpeace and the NYT: satellite-verified maps of Russia's new line toward the plant.

**Technique.**
- Conventional news cartography.
- Damage is marked as a circled section, not a point. That is close in spirit to the bands here, but drawn as a
  ring, not to a stated size.

**Uncertainty.** "Alleged" in the caption. None of these maps shows **who** repaired anything, as far as found. That
is the gap this graphic fills.

**For this graphic.**
- Bellona's circled section shows the audience already reads a ring round a stretch as "somewhere along here".
- None of them draws actors, so there's no house style to follow or avoid. A dedicated NYT or Reuters graphic of the
  lines wasn't found online. *(unverified: such graphics may exist behind paywalls)*

## 14. Mediated arrangements: the Black Sea Grain Initiative's Joint Coordination Centre (2022–23)

**Links:** [UN JCC page](https://www.un.org/fr/node/185720) ·
[Wikipedia](https://en.wikipedia.org/wiki/Black_Sea_Grain_Initiative) ·
[JCC data on HDX](https://data.humdata.org/organization/jcc)

**What it is.** A four-party centre in Istanbul (Russia, Ukraine, Türkiye, the UN as secretariat) that set the
corridor and ran joint inspections. It is the best-known Ukraine-war precedent for **a third party making both sides'
work possible**. No good diagram of it was found; the press drew ship routes, not the arrangement.

**For this graphic.**
- The IAEA truces are the same structure on a small scale. Draw the IAEA as **a node off the map**, a small mark in
  the foot bar or the margin, never on the plant: the IAEA team is on site, and placing them would be a position.
- Thin "brokered" links run from it to each truce, and the truce's repair gets its "did the work" links from the
  sides.
- The JCC shows that the arrangement can be the protagonist without any geography.

## 15. Smaller references: craft, honesty and absence

- **Slate's *Middle East Friendship Chart* (2014, Syria update 2015).**
  [2014](https://www.slate.com/blogs/the_world_/2014/07/17/the_middle_east_friendship_chart.html) ·
  [2015](https://www.slate.com/blogs/the_slatest/2015/10/06/syrian_conflict_relationships_explained.html)
  - An actor-by-actor matrix with three states, the third being **"it's complicated"**.
  - The useful idea is giving "complicated" or "unknown" a named state. The matrix form doesn't suit an 8-second map
    shot.
- **Mimi Onuoha, *The Library of Missing Datasets*.**
  [mimionuoha.com/omission](https://mimionuoha.com/omission)
  - Absence presented as an object, with its own label and place.
  - It argues for the 21 "who not stated" repairs having a *visible* form (a stub, a hatched tick), not just being
    left out.
- **MacEachren et al., *Visual Semiotics & Uncertainty Visualization* (IEEE TVCG 2012).**
  [paper (PDF)](https://geography.wisc.edu/cartography/projects/publications/MacEachrenEtAl_2012_TVCG.pdf)
  - Users found fuzziness, location, value (lightness) and arrangement (for example dash patterns) intuitive for
    uncertainty, and saturation much less so. *(from a summary of the paper; check the paper itself)*
  - This supports **dashing or dotting (arrangement) and lighter grey (value)** for "who not stated", and argues
    against a desaturated colour.
  - The project already uses dotted to mean "unreported or unconfirmed" (the zoom-out and the unrolled film), so
    dotted for "who not stated" is consistent across the film.
- **Giorgia Lupi / Accurat (now Pentagram): visual essays for *La Lettura*.**
  [Pentagram](https://www.pentagram.com/work/la-lettura/story) ·
  [giorgialupi.com](https://giorgialupi.com/lalettura)
  - Layered "info-spatial" compositions: a primary map or shape with secondary data in glyphs and margins, and a
    short drawn legend.
  - The relevant idea is the **legend as a drawn sentence** and secondary layers kept around the edge of the main
    image. *(no specific uncertainty convention verified)*
- **Federica Fragapane, *The Stories Behind a Line*.**
  [Medium](https://medium.com/@frcfr/the-stories-behind-a-line-73a1bb247978) ·
  [IIB Awards](https://informationisbeautifulawards.com/showcase/2497)
  - Asylum seekers' routes, with dotted lines in different patterns for the means of transport, and red dots where a
    narrator shared more.
  - Her line patterns encode **kind of relation, not certainty**. That is a warning: if dotted means "who not stated"
    here, no other line pattern may mean anything else.
- **Kiln, Moritz Stefaner (beyond *Notabilia*), SITU Research, Bellingcat.**
  - No specific actor-and-repair map was found to cite. Bellingcat's network work, such as GRU unit 29155, is
    published mostly as text and photo links, not reusable graphics.
  - SITU's relevant contribution is *The Left-to-Die Boat* (§5).
  - Eyal Weizman's writing (*Forensic Architecture: Violence at the Threshold of Detectability*, 2017) gives the
    framing: the threshold of detectability. Here the published place and the named actor are both thresholds, and
    the graphic should show where each repair falls below them.

---

## Techniques for "unknown who", honestly

The unknown has to be visible, not just undrawn. Choose one rule and keep it everywhere.

| Option | Reads as | For | Against |
|---|---|---|---|
| **No link at all** (ring or tick only) | nothing known | the plainest, no invented mark | at 8 s the absence isn't noticed. Pair it with a count ("21 with no actor published") |
| **Dotted stub** rising from the ring or tick and stopping short of any anchor | "someone did this; not said who" | the project's dotted already means "not confirmed"; MacEachren's "arrangement" | the stub's direction must be neutral (straight up or along the bar), or it implies a side |
| **Grey link to a "not stated" node** | unknown as an actor | symmetrical with the others, countable | it turns ignorance into a participant; three nodes look like three parties |
| **Hatched or hollow tick** in the bar (Ayotzinapa: time only) | known when, not who or where | it composes with the existing grey ticks: grey = no place, hatched = no actor | two kinds of absence on one tick need a clear key |

**Recommended:** a dotted stub for "who not stated", plus the count.
- No anchor node for "unknown".
- The one single-source Russian claim (R41) is drawn as a link but marked as one side's media only (a hairline, or a
  small "RU media" tag on the anchor). The IAEA didn't confirm it.

## Techniques for time

- **Draw on as it happens.** Each link grows from its actor anchor to its ring or tick at the moment the playhead
  passes the date, over about 0.25–0.4 s, eased out. *EXIT*'s and *Notabilia*'s growth, and the zoom-out's lines,
  which already grow.
- **Flash, then decay to a residue.** Follow the rings' rule (full white, decaying to 0.72 over 1.6 s), with links
  decaying further, to about 0.25.
  - The end state then shows the accumulated weave (who, how often) without the links outshining the regions.
  - Fading links out entirely would lose the accumulation, which is the point of the shot.
- **Bunching.** Most placed repairs fall after October 2025, so links will arrive in a burst near the end.
  - Bundled trunks (§11) and Minard-style vertical leaders (§7) keep the burst readable.
  - Stagger links that fall on the same day by about 2–3 frames. Say nothing about it on screen: it's within a day.
- **Count by side, beside the main sentence**, counting up as links land: "16 by Ukrainian crews · 3 by both sides
  under IAEA truces · 1 claimed by Russian media · 21 not said". This is the honest summary at the hold.

---

## The five most applicable techniques

1. **Actors as anchors off the map, in the foot bar or the margins, with leaders rising to the regions** (Minard's
   leaders, Lombardi's timeline arcs, FA's coupled map and timeline).
   - Put the actors as two or three short lanes or marks in the existing black bar: Ukrainian operator and crews; the
     plant's Russian-installed management and Rosatom; the IAEA as a small third-party mark.
   - Each repair's link rises from its actor's lane at its date, through its tick, up to its region.
   - No actor has a place on the land. The bar already holds the time.
2. **Unplaced repairs linked inside the bar only** (FA Ayotzinapa: events with time but no place stay on the
   timeline).
   - The 21 get their actor links between lane and tick and never touch the map. The network is then complete (41)
     while the map stays honest (20).
3. **Direction as side, Notabilia-style.** Where links must stay near the map, each repair's stroke *leans* toward its
   side's edge of the frame (Ukrainian-held north, occupied south), with a fork for both and a straight dotted stub for
   unknown.
   - A side of the front is an allowed region (Earshot's "entered over the southern border" is the same move). It is
     never a point.
4. **Role carried by line style, PA-X-style, with the truce as its own node.**
   - Line styles: solid = did the work, named; the IAEA's thinner or dashed "brokered" link to the truce; the repair
     linked to its truce.
   - "Each side repaired its part" is then shown without assigning crews to regions (R35f/R35d).
   - Colours stay out of it: the lines are red, the rings white.
5. **Unknown made visible but not personified:** a dotted stub plus a running count.
   - Dotted already means "not confirmed" in the zoom-out and the unrolled film. MacEachren's results favour
     arrangement and value over saturation.
   - The count by side at the hold says plainly that about half the repairs have no published actor.

### Pitfalls to avoid

- Lines that start at a point on the land: a depot, a substation, the plant's gate. That is a position, and against
  the rule.
- Bundled trunks that cross the river on the map. They read as routes crews took.
- A symmetrical two-sided layout that suggests balance. The record is 16 : 3 : 1 : 21.
- Colouring the sides red and blue. Red is the power lines, and blue was rejected in the zoom-out for reading as rivers.
- Treating "under an IAEA ceasefire" as "both sides worked on this repair".

## Sources

All are linked in place above. The main ones:

- https://airpressure.info/about
- https://today.lorientlejour.com/article/1302855/22111-israeli-military-aircraft-have-violated-lebanese-airspace-since-2007.html
- https://12.berlinbiennale.de/artists/lawrence-abu-hamdan/
- https://en.wikipedia.org/wiki/Mark_Lombardi
- https://cabinetmagazine.org/issues/2/lombardi.php
- https://forensic-architecture.org/investigation/the-enforced-disappearance-of-the-ayotzinapa-students
- https://www.opendemocracy.net/ayotzinapa-platform-what-happened-to-43-dis/
- https://github.com/forensic-architecture/timemap
- https://forensic-architecture.org/investigation/the-left-to-die-boat
- https://situ.nyc/research/projects/forensic-oceanography-report
- https://truth-and-beauty.net/projects/notabilia
- https://www.edwardtufte.com/?p=677
- https://mk.bcgsc.ca/linnet
- https://peacerep.org/publication/introducing-pa-x-a-new-peace-agreement-database-and-dataset/
- https://arxiv.org/abs/0812.1242
- https://diglib.eg.org/handle/10.1111/v28i3pp0983-0990
- https://aleppo.c4sr.columbia.edu/urban-destruction/index.html
- https://dsrny.com/project/exit
- https://bellona.org/?p=38075
- https://www.aljazeera.com/news/2022/9/4/infographic-ukraines-zaporizhzhia-nuclear-power-plant
- https://www.un.org/fr/node/185720
- https://www.slate.com/blogs/the_world_/2014/07/17/the_middle_east_friendship_chart.html
- https://mimionuoha.com/omission
- https://geography.wisc.edu/cartography/projects/publications/MacEachrenEtAl_2012_TVCG.pdf
- https://www.pentagram.com/work/la-lettura/story
- https://medium.com/@frcfr/the-stories-behind-a-line-73a1bb247978
