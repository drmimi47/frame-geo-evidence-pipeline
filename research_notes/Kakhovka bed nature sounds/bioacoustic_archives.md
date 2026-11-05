# Nature sound recordings from the drained Kakhovka reservoir bed and its shores (bioacoustic and citizen-science archives)

Searched 4–5 November 2026. Reference points used throughout: the **crossing box** (the 750 kV and 330 kV lines over the
bed between Enerhodar and Marhanets, 47.50–47.62 N, 34.57–34.66 E; "km to crossing" = straight-line distance to the
nearest edge of that box) and **the bed**, taken as OpenStreetMap relation 1600087 (Великий Луг, natural=wetland), which
OSM maps as the whole drained reservoir floor (fetched from Overpass, saved in `raw/osm/rel1600087.json`; a point was
tested inside/outside its outer rings). Everything fetched is under `research_notes/Kakhovka bed nature sounds/raw/<source>/`.
Coordinates of private individuals' recordings are given to 2 decimals at most.

**Headline:** across every archive checked, there is **no publicly findable nature recording made on the bed within
~45 km of the crossing**, and **none at all from the occupied south bank** (Enerhodar, Kamianka-Dniprovska, Vodiane,
Velyka Znamianka). The closest recordings are one recordist's (Ekaterina Kormina: xeno-canto CC0, iNaturalist
"uabird" CC BY-NC) in and around Marhanets on the north bank, 2.5–8.4 km from the crossing box and 3.4–8.3 km outside
the bed's OSM outline. The only recordings **on the bed itself** are Oleksii Vasyliuk's 2026 iNaturalist set (CC BY)
at Mar'ianske and Novovorontsovka on the right bank, ~47–49 km west of the crossing; two of those are noted by the
recordist himself as containing an FPV drone or a starling imitating a drone shoot-down.

## xeno-canto: recordings in the box 47.20–47.85 N, 33.30–35.30 E (and round it)

### Takeaway
xeno-canto holds exactly **13 recordings** in the box (foreground species), all from two recordists: **7 by Ekaterina
Kormina round Marhanets (CC0)** and **6 by Rostyslav Romanyshyn in Zaporizhzhia (CC BY-NC-SA 4.0)**. Ten are from after
6 June 2023 (4 Kormina, 6 Romanyshyn); none is on the bed itself (all lie 3.4–10.4 km outside its OSM outline). XC1016141 is not alone: Kormina
has four post-drainage recordings 3.0–4.3 km from the crossing box, all CC0.

### Cited Findings
- The website box query returns "13 results from 12 species for query 'box:47.2,33.3,47.85,35.3' (foreground species
  only)" — [xeno-canto box query](https://xeno-canto.org/explore?query=box:47.2,33.3,47.85,35.3). (API v2 is retired; the
  site sits behind an Anubis bot check, so pages were read in a browser and saved in `raw/xc/`.)
- Per-record data, from each record page (coordinates as given by xeno-canto; private recordist, so 2 dp here):

| XC | Species (type) | Date, time | Place as given | Lat, lon | km to crossing | Recordist | Licence | Length, format | Background | Remarks |
|---|---|---|---|---|---|---|---|---|---|---|
| [XC1016138](https://xeno-canto.org/1016138) | Identity unknown, "Sylviidae" (song; mystery recording) | 2024-05-13, ? | Marhanets'ka city council (near Marhanets') | 47.65, 34.62 | 3.0 | Ekaterina Kormina | [CC0](https://creativecommons.org/publicdomain/zero/1.0/) | 52.9 s, mp3 mono 80 kbps | none | "Sylviidae" |
| [XC1016032](https://xeno-canto.org/1016032) | Identity unknown (aberrant; mystery) | 2025-07-14, morning | near Marhanets' | 47.66, 34.62 | 4.3 | Ekaterina Kormina | CC0 | 5.5 s, mp3 mono 80 kbps | none | "Morning. Many warblers near the river in the reeds and bushes. I saw Savi's warblers, paddyfield warblers, sedge warbler, great reed warblers and heard the common reed warbler song at the recording site." |
| [XC1016141](https://xeno-canto.org/1016141) | Thrush Nightingale *Luscinia luscinia* (song, male) | 2025-04-16, ? | near Marhanets' | 47.66, 34.60 | 4.0 | Ekaterina Kormina | CC0 | 60 s, mp3 mono 80 kbps | Eurasian Blue Tit | none |
| [XC1016134](https://xeno-canto.org/1016134) | Lesser Whitethroat *Curruca curruca* (uncertain) | 2025-04-23, ? | near Marhanets' | 47.66, 34.60 | 4.0 | Ekaterina Kormina | CC0 | 26.4 s, mp3 mono 80 kbps | none | none |
| [XC1016139](https://xeno-canto.org/1016139) | Red-backed Shrike *Lanius collurio* (song, male) | 2023-05-16, ? (**before**) | near Marhanets' | 47.66, 34.62 | 4.3 | Ekaterina Kormina | CC0 | 115.1 s, mp3 mono 80 kbps | none | none |
| [XC1016140](https://xeno-canto.org/1016140) | Bluethroat *Luscinia svecica* (song, male) | 2023-04-04, ? (**before**) | near Maksymivka | 47.69, 34.64 | 7.6 | Ekaterina Kormina | CC0 | 35.5 s, mp3 stereo 320 kbps | none | none |
| [XC1016142](https://xeno-canto.org/1016142) | Common Chiffchaff *Phylloscopus collybita* (song, male) | 2023-04-06, ? (**before**) | near Marhanets', Nikopol's'kyi district | 47.68, 34.63 | 6.6 | Ekaterina Kormina | CC0 | 9 s, mp3 stereo 320 kbps | Corn Bunting | none |
| [XC970874](https://xeno-canto.org/970874) | Eurasian Blue Tit (call, song) | 2025-01-26, 11:00 | Zaporiz'ka city council (near Zaporizhzhia) | 47.82, 35.15 | 42.8 | Rostyslav Romanyshyn | [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) | 16.8 s, mp3 stereo 320 kbps, Olympus DM-670 | Hooded Crow | none |
| [XC1050108](https://xeno-canto.org/1050108) | Hooded Crow (call, flight call) | 2025-02-12, 16:00 | near Zaporizhzhia | 47.82, 35.15 | 42.8 | Rostyslav Romanyshyn | CC BY-NC-SA 4.0 | 27.7 s, mp3 stereo | none | none |
| [XC1050116](https://xeno-canto.org/1050116) | Caspian Tern *Hydroprogne caspia* (flight call) | 2025-02-12, 16:00 | near Zaporizhzhia | 47.82, 35.15 | 42.8 | Rostyslav Romanyshyn | CC BY-NC-SA 4.0 | 29 s, mp3 stereo | Black-headed Gull, Hooded Crow | none |
| [XC1050112](https://xeno-canto.org/1050112) | Black-headed Gull (flight call) | 2025-02-12, 16:00 | near Zaporizhzhia | 47.82, 35.15 | 42.8 | Rostyslav Romanyshyn | CC BY-NC-SA 4.0 | 9.2 s, mp3 stereo | none | none |
| [XC1050100](https://xeno-canto.org/1050100) | Lesser Black-backed Gull (flight call) | 2025-02-16, 12:30 | near Zaporizhzhia | 47.83, 35.14 | 42.7 | Rostyslav Romanyshyn | CC BY-NC-SA 4.0 | 19.5 s, mp3 stereo | none | none |
| [XC1050101](https://xeno-canto.org/1050101) | Middle Spotted Woodpecker (call) | 2025-02-16, 12:30 | near Zaporizhzhia | 47.83, 35.14 | 42.7 | Rostyslav Romanyshyn | CC BY-NC-SA 4.0 | 3.2 s, mp3 stereo | none | none |

- None of the 13 lies on the bed: tested against the OSM outline, Kormina's points are 3.4–8.3 km outside it and
  Romanyshyn's 9.5–10.4 km outside it (`raw/osm/`, point-in-polygon test on relation 1600087 —
  [OSM relation 1600087](https://www.openstreetmap.org/relation/1600087)).
- Times: Kormina gives no clock time ("?"), only "Morning" in XC1016032's remarks; Romanyshyn gives 11:00–16:00 —
  [XC1016032](https://xeno-canto.org/1016032), [XC970874](https://xeno-canto.org/970874).
- No recordist remark mentions explosions, drones or fighting in any of the 13 (remarks are "None given" except
  XC1016138 and XC1016032) — record pages above.
- Just outside the box: south (46.7–47.2 N) only 3 recordings, all Common Chaffinch by Eugenia Yablonovska-Grishchenko,
  2010-05-03, "Kazachyi Lageri, Kherson region" (XC109884, XC109882, XC109849) — **before**, and by place name on the lower
  Dnipro below the dam, not the reservoir (not checked against the record coordinates) —
  [box 46.7–47.2](https://xeno-canto.org/explore?query=box:46.7,33.0,47.2,35.3), [XC109884](https://xeno-canto.org/109884).
- North edge (47.85–48.0 N, Zaporizhzhia): XC742871 (European Greenfinch, Серж, 2022-08-12) and XC817813 (Eurasian
  Scops Owl, Серж, 2023-07-19 04:30), both "Pivnichne Selyshche (near Zaporizhzhia)", and XC737719 (Scops Owl, Володимир
  Мерзлікін, 2022-07-15 23:30) — urban Zaporizhzhia, not the bed —
  [box 47.85–48.0](https://xeno-canto.org/explore?query=box:47.85,34.9,48.0,35.3), [XC817813](https://xeno-canto.org/817813).
- Place-name queries: `loc:kakhovka`, `loc:enerhodar`, `loc:kamianka`, `loc:khortytsia` return nothing in Ukraine;
  `loc:nikopol` returns only XC1016142; `loc:marhanets` the 7 Kormina recordings above — saved in `raw/xc/xc_queries.json`.
- A background-species query over the box (`also:`) returned an Internal Server Error, so recordings where a species
  appears only in the background were not searched separately (they would still be in the 13, since the box query lists
  recordings by location).

### Inferences
- Kormina's xeno-canto uploads were all made on 2025-07-14 (all 7 pages show "Uploaded 2025-07-14"),
  i.e. a batch drawn from her own archive; the same person is iNaturalist "uabird" (see next section), so xeno-canto and
  iNaturalist round Marhanets are **one recordist's work**, probably partly the same files.
- The CC0 Kormina set (XC1016141, XC1016138, XC1016134, XC1016032) is the most freely reusable local material: north
  bank, 3–4.3 km from the crossing box, after the drainage. Her remark in XC1016032 (warblers "near the river in the
  reeds") describes a reed habitat near Marhanets; whether "the river" is the new Dnipro channel or a stream in town is
  not stated, and the coordinates lie 4.7 km outside the bed outline.
- Romanyshyn's February 2025 gulls, Caspian tern and crows (CC BY-NC-SA) are winter river birds in southern Zaporizhzhia,
  ~43 km from the crossing; usable only as "the Dnipro at Zaporizhzhia", not as the bed.

### Gaps
- Exact recording times for Kormina's recordings are not given.
- xeno-canto's background-species search failed; xeno-canto API v3 (needs a key) was not used.
- Whether any of the 13 contains distant war sounds could only be judged by listening; the remarks do not say.

## iNaturalist: sound observations over the whole bed and both banks, 6 June 2023 onward

### Takeaway
The API box 47.20–47.85 N, 33.30–35.30 E holds **267 sound observations** (all dates), from 6 recordists: **vasyliuk1
(Oleksii Vasyliuk) 144, uabird (Ekaterina Kormina) 116**, and 7 others. **210 are from after 6 June 2023.** The iNaturalist
place "Former Kakhovka Reservoir" (id 216144) contains **96 sound observations, all by Vasyliuk**, all May–July 2026 at
Mar'ianske/Novovorontsovka on the right bank, ~47–49 km west of the crossing, licensed **CC BY**. Nothing at all from the
occupied south bank, from Nikopol, Pokrovske or Velyka Kostromka, or from the Great Meadow's upper reach. Only **one
amphibian** (a fire-bellied toad, before the breach) and **one insect** (a cicada, after) have sound in the box; no marsh
frog or green toad sound exists anywhere near the bed.

### Cited Findings
- Box query (sounds=true, 47.20–47.85 N, 33.30–35.30 E): total_results 267 — [iNat API](https://api.inaturalist.org/v1/observations?sounds=true&swlat=47.20&swlng=33.30&nelat=47.85&nelng=35.30&per_page=200) (saved `raw/inat/box_all_p1.json`, `_p2.json`). By year: 2020 1, 2021 1, 2022 19, 2023 45, 2024 12, 2025 21, 2026 168. Iconic taxa: Aves 265, Amphibia 1, Insecta 1.
- South extension to Nova Kakhovka (46.70–47.20 N, 33.0–35.3 E): 3 sound observations — Common Crane (timchenkostanislav33, 2024-09-21, 46.75, 34.09, Nyzhni Sirohozy district; south of the bed), **Golden Jackal *Canis aureus*** ([325174193](https://www.inaturalist.org/observations/325174193), suriadna / Nataliia Suriadna, 2025-11-04 14:10, 47.07, 33.69, Beryslav district, CC BY-NC, m4a, description "Спостереження - Лукін Сергій Сергійович", i.e. observed by Serhii Lukin), and one untaxoned record — [iNat API](https://api.inaturalist.org/v1/observations?sounds=true&swlat=46.70&swlng=33.00&nelat=47.20&nelng=35.30) (`raw/inat/south_p1.json`). The jackal point is 0.12 km outside the bed outline (right bank of the lower reach), ~82 km from the crossing.
- iNaturalist place 216144 "Former Kakhovka Reservoir" (bounding box 46.76–47.87 N, 33.36–35.38 E): 96 sound observations, all vasyliuk1; 2,689 observations of all kinds, 2,461 since 6 June 2023; top observers since then: khortytsianpd (Khortytsia National Reserve) 789, vasyliuk1 558, ivanmoysiyenko 361, eprivola 140 — [place 216144](https://www.inaturalist.org/places/216144), [sounds in place](https://api.inaturalist.org/v1/observations?sounds=true&place_id=216144). An iNat project exists: [Biodiversity of the former Kakhovka Reservoir (243888)](https://www.inaturalist.org/projects/biodiversity-of-the-former-kakhovka-reservoir).
- Recordist identities from their iNat profiles: vasyliuk1 = "Oleksii Vasyliuk" (43,548 observations); uabird = "Екатерина Кормина" (Ekaterina Kormina, 2,104) — [vasyliuk1](https://www.inaturalist.org/people/vasyliuk1), [uabird](https://www.inaturalist.org/people/uabird). Vasyliuk is a zoologist of the Ukrainian Nature Conservation Group and research associate of the Askania-Nova Biosphere Reserve, who led a four-day expedition near Novovorontsovka on the bed, reporting "безперервний спів — зараз там живе величезна кількість солов'їв та очеретянок" ("constant song: a huge number of nightingales and reed warblers live there now") and jackal, fox and polecat tracks — [Texty, 1 July 2026](https://texty.org.ua/fragments/117772/xto-zaselyv-dno-kaxovskoho-vodosxovyshcha-zooloh-opysav-tvaryn-novoho-lisu/).
- **Vasyliuk's 144 (all 2026: 13 May 64, 14 May 66, 14–16 July 14), CC BY on every sound.** Two clusters: 56 at Mar'ianske (47.55–47.56 N, 33.93–33.94 E, Apostolove district) **inside the bed outline, 0.07–0.28 km from its edge**, and 88 in and round Novovorontsovka village (47.50–47.51 N, 33.92–33.94 E), on the outline's edge (0.05 km). The Mar'ianske set is the bed's wetland and new-forest chorus: Thrush Nightingale (×7), Savi's Warbler (×5), Great Reed Warbler, Common Reed Warbler, Paddyfield Warbler, Eurasian Penduline-Tit, Bearded Reedling (Novovorontsovka edge), Eurasian Coot, Pied Avocet (×2), Little Ringed Plover, Ruddy Shelduck (×4), Western Yellow Wagtail, Corn Bunting, Common Cuckoo, Ring-necked Pheasant, Eurasian Scops-Owl, Common Hoopoe, European Bee-eater, Stonechat, Song Thrush. No clock times are recorded on any of them. Full list below — [iNat API box query](https://api.inaturalist.org/v1/observations?sounds=true&swlat=47.20&swlng=33.30&nelat=47.85&nelng=35.30&per_page=200).
- **War sounds in Vasyliuk's set, by the recordist's own notes:** [361467377](https://www.inaturalist.org/observations/361467377) (Thrush Nightingale, 2026-05-14, Mar'ianske) "На фоні фпв дрон" ("an FPV drone in the background"); [361134120](https://www.inaturalist.org/observations/361134120) (European Starling, 2026-05-13, Novovorontsovka) "Шпак повторює звуки збиття бпла" ("the starling repeats the sounds of a drone being shot down") — observation descriptions in the API reply.
- File properties, from 14 files downloaded to check (then the large WAVs deleted; two small MP3s kept in `raw/inat/audio/`): Vasyliuk's sounds are uncompressed WAV, 44.1 kHz mono, 8–93 s, recorded very quietly (median level −44 to −71 dBFS); Kormina's iNat sounds are MP3, ~20 s (e.g. the toad, stereo; the cicada, mono) — [sound files linked from each observation](https://www.inaturalist.org/observations/361467464).
- **Kormina's 116 (uabird), CC BY-NC on every sound**, 2022-06-08 to 2026-08-23, 61 after 6 June 2023 and 55 before; all on the north bank in and around Marhanets (place guesses: "Марганец" 84, "Никопольский район" 18, "Днепропетровская область" 12, "Максимовка" 2), **2.5–8.4 km from the crossing box and 3.4–8.3 km outside the bed outline**; none obscured. One spot recurs many times (her repeated location; given here only to 2 dp, 47.65, 34.62). After the drainage they include wetland and wader species recorded at 47.68–47.70 N, 34.63–34.65 E north of Marhanets: Common Sandpiper (2023-06-27), Common Redshank (2023-07-15), Little Ringed Plover (2023-08-23, 2025-08-17), Little Crake and Little Bittern (2026-05-15), Black-winged Stilt (2026-07-21), Temminck's Stint and Spotted Redshank (2026-07-29), Savi's Warbler (2026-04-15, 2026-08-23) — full list below.
- **Amphibians and insects with sound in the box:** only [154971073](https://www.inaturalist.org/observations/154971073), European Fire-bellied Toad *Bombina bombina*, uabird, 2023-04-15 11:30 (**before**), 47.65, 34.61, CC BY-NC, 20 s MP3 stereo; and [231228832](https://www.inaturalist.org/observations/231228832), the cicada *Cicadatra platyptera*, uabird, 2024-07-22 15:26 (after), 47.66, 34.62, CC BY-NC, 21 s MP3 mono, loud (median −20 dBFS). No mammal except the jackal above. Regional search (46.4–48.6 N, 32.5–36.5 E, Amphibia/Insecta/Mammalia/Reptilia with sound): 29 records, and the marsh frogs *Pelophylax ridibundus* and green toads *Bufotes viridis* among them are all far from the bed — Kryvyi Rih (wdkeeper, 2024-04-28, CC BY), Dnipro city (kateryna_dp 2025-04-16; asdub 2024-04-27; lidaok 2023-06-06), Kirovohrad oblast (medutha 2025; krystyna18653 green toads 2025-05-28), Burkuty, Kherson oblast (2021) — [iNat API](https://api.inaturalist.org/v1/observations?sounds=true&iconic_taxa=Amphibia,Insecta,Mammalia,Reptilia&swlat=46.4&swlng=32.5&nelat=48.6&nelng=36.5&per_page=200) (`raw/inat/nonbird_region.json`).
- **Occupied south bank:** zero sound observations south of 47.55 N and east of 34.2 E; in the box 47.35–47.55 N, 34.25–34.80 E (Enerhodar, Kamianka-Dniprovska, Vodiane, Velyka Znamianka) iNaturalist holds only 102 observations of any kind ever, 11 since 6 June 2023, none with sound — [iNat API](https://api.inaturalist.org/v1/observations?swlat=47.35&swlng=34.25&nelat=47.55&nelng=34.80&d1=2023-06-06) (`raw/inat/southbank_*.json`).
- **Nikopol, Pokrovske, Velyka Kostromka; the Great Meadow upper reach (Bilenke, Balabyne):** no sound observations at all (none in the box rows between 34.03 and 34.60 E, and none between 34.66 and 35.07 E) — box query above.
- **Zaporizhzhia end:** Eurasian Golden Oriole, [280989253](https://www.inaturalist.org/observations/280989253) (lary_s, 2025-05-14, 47.85, 35.08) and [390808315](https://www.inaturalist.org/observations/390808315) (eprivola, 2026-08-13, 47.85, 35.08), CC BY-NC; Scops Owls in Sotsmisto by volodymyr_merzlikin (2022-07-15, 2024-08-07, 2024-08-17, CC BY-NC-SA) — [iNat API](https://api.inaturalist.org/v1/observations?sounds=true&swlat=47.85&swlng=34.90&nelat=48.00&nelng=35.30) (`raw/inat/zap_north_p1.json`). Sholokhove area (north bank, ~42 km W of the crossing, 11 km from the bed): shvets_oksana, 4 sounds 2026 (Scops Owl, Reed Warbler, Syrian Woodpecker, Quail), CC BY-NC.

#### Full list of iNaturalist sound observations in the box

**uabird (Ekaterina Kormina), after 6 June 2023** (61)

| iNat obs | Date (time) | Taxon | Common name | Lat, lon (2 dp) | km to crossing box | Licence | Grade | Note |
|---|---|---|---|---|---|---|---|---|
| [167171951](https://www.inaturalist.org/observations/167171951) | 2023-06-13 | *Anthus trivialis* | Tree Pipit | 47.66, 34.62 | 4.5 | cc-by-nc | research |  |
| [167842794](https://www.inaturalist.org/observations/167842794) | 2023-06-15 11:56 | *Luscinia luscinia* | Thrush Nightingale | 47.66, 34.62 | 4.4 | cc-by-nc | research |  |
| [191111423](https://www.inaturalist.org/observations/191111423) | 2023-06-17 09:33 | *Curruca nisoria* | Barred Warbler | 47.67, 34.60 | 5.3 | cc-by-nc | research |  |
| [169812890](https://www.inaturalist.org/observations/169812890) | 2023-06-27 11:04 | *Actitis hypoleucos* | Common Sandpiper | 47.69, 34.64 | 8.0 | cc-by-nc | research |  |
| [172991728](https://www.inaturalist.org/observations/172991728) | 2023-07-15 09:37 | *Tringa totanus* | Common Redshank | 47.69, 34.64 | 7.3 | cc-by-nc | research |  |
| [179884457](https://www.inaturalist.org/observations/179884457) | 2023-08-23 | *Thinornis dubius* | Little Ringed Plover | 47.70, 34.65 | 8.4 | cc-by-nc | research |  |
| [187622284](https://www.inaturalist.org/observations/187622284) | 2023-10-15 | *Prunella modularis* | Dunnock | 47.68, 34.64 | 7.0 | cc-by-nc | research |  |
| [189753185](https://www.inaturalist.org/observations/189753185) | 2023-11-02 | *Turdus iliacus* | Redwing | 47.68, 34.63 | 6.4 | cc-by-nc | research |  |
| [191113953](https://www.inaturalist.org/observations/191113953) | 2023-11-15 | *Acanthis flammea* | Redpoll | 47.66, 34.62 | 4.0 | cc-by-nc | research |  |
| [196311195](https://www.inaturalist.org/observations/196311195) | 2024-01-10 | *Eremophila alpestris* | Horned Lark | 47.68, 34.64 | 7.0 | cc-by-nc | needs_id |  |
| [208942271](https://www.inaturalist.org/observations/208942271) | 2024-04-23 | *Sylvia atricapilla* | Eurasian Blackcap | 47.66, 34.60 | 4.0 | cc-by-nc | research |  |
| [211382286](https://www.inaturalist.org/observations/211382286) | 2024-04-26 | *Otus scops* | Eurasian Scops-Owl | 47.66, 34.62 | 4.4 | cc-by-nc | research |  |
| [214182804](https://www.inaturalist.org/observations/214182804) | 2024-05-07 | *Oriolus oriolus* | Eurasian Golden Oriole | 47.66, 34.62 | 4.4 | cc-by-nc | research |  |
| [215504232](https://www.inaturalist.org/observations/215504232) | 2024-05-13 | *Sylviidae* | Sylviid Warblers and Allies | 47.65, 34.62 | 3.0 | cc-by-nc | needs_id |  |
| [216994873](https://www.inaturalist.org/observations/216994873) | 2024-05-20 | *Carpodacus erythrinus* | Common Rosefinch | 47.65, 34.62 | 3.0 | cc-by-nc | research |  |
| [219674206](https://www.inaturalist.org/observations/219674206) | 2024-05-31 10:39 | *Luscinia luscinia* | Thrush Nightingale | 47.66, 34.60 | 4.0 | cc-by-nc | needs_id |  |
| [231228832](https://www.inaturalist.org/observations/231228832) | 2024-07-22 15:26 | *Cicadatra platyptera* |  | 47.66, 34.62 | 4.2 | cc-by-nc | research |  |
| [243034992](https://www.inaturalist.org/observations/243034992) | 2024-09-19 | *Ficedula parva* | Red-breasted Flycatcher | 47.66, 34.62 | 4.7 | cc-by-nc | research |  |
| [244912276](https://www.inaturalist.org/observations/244912276) | 2024-09-30 | *Anthus cervinus* | Red-throated Pipit | 47.69, 34.62 | 8.1 | cc-by-nc | research |  |
| [254486361](https://www.inaturalist.org/observations/254486361) | 2024-12-07 | *Prunella modularis* | Dunnock | 47.68, 34.64 | 7.0 | cc-by-nc | research |  |
| [256402169](https://www.inaturalist.org/observations/256402169) | 2024-12-27 10:21 | *Turdus viscivorus* | Mistle Thrush | 47.66, 34.60 | 3.9 | cc-by-nc | research |  |
| [257577859](https://www.inaturalist.org/observations/257577859) | 2025-01-05 | *Prunella modularis* | Dunnock | 47.65, 34.61 | 3.6 | cc-by-nc | research |  |
| [258293574](https://www.inaturalist.org/observations/258293574) | 2025-01-12 | *Remiz pendulinus* | Eurasian Penduline-Tit | 47.68, 34.63 | 6.6 | cc-by-nc | research |  |
| [262545849](https://www.inaturalist.org/observations/262545849) | 2025-02-21 15:30 | *Turdus iliacus* | Redwing | 47.65, 34.61 | 3.9 | cc-by-nc | research |  |
| [269590834](https://www.inaturalist.org/observations/269590834) | 2025-04-10 07:32 | *Motacilla flava* | Western Yellow Wagtail | 47.66, 34.62 | 4.2 | cc-by-nc | research |  |
| [270647912](https://www.inaturalist.org/observations/270647912) | 2025-04-15 | *Acrocephalus arundinaceus* | Great Reed Warbler | 47.68, 34.63 | 6.5 | cc-by-nc | research |  |
| [272415732](https://www.inaturalist.org/observations/272415732) | 2025-04-23 | *Curruca curruca* | Lesser Whitethroat | 47.66, 34.60 | 4.0 | cc-by-nc | needs_id |  |
| [272641487](https://www.inaturalist.org/observations/272641487) | 2025-04-24 08:16 | *Turdus merula* | Eurasian Blackbird | 47.66, 34.60 | 4.0 | cc-by-nc | needs_id |  |
| [272641581](https://www.inaturalist.org/observations/272641581) | 2025-04-24 07:05 | *Jynx torquilla* | Eurasian Wryneck | 47.66, 34.60 | 4.0 | cc-by-nc | research |  |
| [272642003](https://www.inaturalist.org/observations/272642003) | 2025-04-24 | *Ficedula albicollis* | Collared Flycatcher | 47.66, 34.60 | 4.0 | cc-by-nc | research |  |
| [272642165](https://www.inaturalist.org/observations/272642165) | 2025-04-24 | *Luscinia luscinia* | Thrush Nightingale | 47.66, 34.60 | 4.0 | cc-by-nc | needs_id |  |
| [278037726](https://www.inaturalist.org/observations/278037726) | 2025-05-03 | *Acrocephalus* | Reed Warblers | 47.66, 34.62 | 4.1 | cc-by-nc | needs_id |  |
| [278933854](https://www.inaturalist.org/observations/278933854) | 2025-05-06 | *Ficedula parva* | Red-breasted Flycatcher | 47.65, 34.62 | 3.0 | cc-by-nc | research |  |
| [278934843](https://www.inaturalist.org/observations/278934843) | 2025-05-06 | *Acrocephalus schoenobaenus* | Sedge Warbler | 47.65, 34.61 | 3.8 | cc-by-nc | research |  |
| [279970419](https://www.inaturalist.org/observations/279970419) | 2025-05-10 | *Carpodacus erythrinus* | Common Rosefinch | 47.65, 34.62 | 3.0 | cc-by-nc | research |  |
| [288107157](https://www.inaturalist.org/observations/288107157) | 2025-05-26 | *Aegithalos caudatus* | Long-tailed Tit | 47.66, 34.60 | 4.0 | cc-by-nc | research |  |
| [288106934](https://www.inaturalist.org/observations/288106934) | 2025-06-04 | *Phylloscopus collybita* | Common Chiffchaff | 47.66, 34.60 | 4.0 | cc-by-nc | research |  |
| [297826539](https://www.inaturalist.org/observations/297826539) | 2025-07-14 | *Locustella* | Locustellid Bush Warblers and Allies | 47.66, 34.62 | 4.3 | cc-by-nc | needs_id | a warbler |
| [307115104](https://www.inaturalist.org/observations/307115104) | 2025-08-10 07:05 | *Phylloscopus trochilus* | Willow Warbler | 47.66, 34.62 | 4.1 | cc-by-nc | research |  |
| [307114244](https://www.inaturalist.org/observations/307114244) | 2025-08-17 07:15 | *Thinornis dubius* | Little Ringed Plover | 47.66, 34.62 | 4.2 | cc-by-nc | research |  |
| [311221269](https://www.inaturalist.org/observations/311221269) | 2025-09-03 | *Falco subbuteo* | Eurasian Hobby | 47.66, 34.62 | 4.1 | cc-by-nc | research |  |
| [343485287](https://www.inaturalist.org/observations/343485287) | 2026-03-04 | *Turdus iliacus* | Redwing | 47.66, 34.63 | 5.0 | cc-by-nc | research |  |
| [343485557](https://www.inaturalist.org/observations/343485557) | 2026-03-17 14:33 | *Bombycilla garrulus* | Bohemian Waxwing | 47.65, 34.63 | 3.3 | cc-by-nc | research |  |
| [349935001](https://www.inaturalist.org/observations/349935001) | 2026-04-10 | *Tringa nebularia* | Common Greenshank | 47.66, 34.62 | 4.2 | cc-by-nc | research |  |
| [350476140](https://www.inaturalist.org/observations/350476140) | 2026-04-15 | *Locustella luscinioides* | Savi's Warbler | 47.66, 34.62 | 4.3 | cc-by-nc | research |  |
| [355137831](https://www.inaturalist.org/observations/355137831) | 2026-04-27 | *Ficedula hypoleuca* | European Pied Flycatcher | 47.66, 34.60 | 4.0 | cc-by-nc | research |  |
| [361726444](https://www.inaturalist.org/observations/361726444) | 2026-05-15 | *Anthus trivialis* | Tree Pipit | 47.66, 34.62 | 4.9 | cc-by-nc | research |  |
| [361727355](https://www.inaturalist.org/observations/361727355) | 2026-05-15 | *Falco vespertinus* | Red-footed Falcon | 47.68, 34.63 | 6.8 | cc-by-nc | research |  |
| [361729386](https://www.inaturalist.org/observations/361729386) | 2026-05-15 | *Schoeniclus schoeniclus* | Reed Bunting | 47.69, 34.64 | 7.3 | cc-by-nc | research |  |
| [361730408](https://www.inaturalist.org/observations/361730408) | 2026-05-15 | *Zapornia parva* | Little Crake | 47.69, 34.65 | 8.2 | cc-by-nc | research |  |
| [361730878](https://www.inaturalist.org/observations/361730878) | 2026-05-15 | *Botaurus minutus* | Little Bittern | 47.68, 34.63 | 6.5 | cc-by-nc | needs_id |  |
| [363889087](https://www.inaturalist.org/observations/363889087) | 2026-05-22 | *Phylloscopus trochilus* | Willow Warbler | 47.66, 34.62 | 4.4 | cc-by-nc | research |  |
| [365277208](https://www.inaturalist.org/observations/365277208) | 2026-05-26 04:39 | *Ficedula parva* | Red-breasted Flycatcher | 47.65, 34.62 | 3.0 | cc-by-nc | research |  |
| [367420767](https://www.inaturalist.org/observations/367420767) | 2026-06-01 | *Erithacus rubecula* | European Robin | 47.66, 34.62 | 4.9 | cc-by-nc | needs_id |  |
| [371583176](https://www.inaturalist.org/observations/371583176) | 2026-06-14 | *Phylloscopus collybita* | Common Chiffchaff | 47.66, 34.62 | 4.9 | cc-by-nc | research |  |
| [374287706](https://www.inaturalist.org/observations/374287706) | 2026-06-17 11:08 | *Coloeus monedula* | Eurasian Jackdaw | 47.66, 34.61 | 4.0 | cc-by-nc | research |  |
| [374114900](https://www.inaturalist.org/observations/374114900) | 2026-06-22 01:56 | *Otus scops* | Eurasian Scops-Owl | 47.65, 34.62 | 3.0 | cc-by-nc | research |  |
| [383645154](https://www.inaturalist.org/observations/383645154) | 2026-07-21 | *Himantopus himantopus* | Black-winged Stilt | 47.70, 34.65 | 8.4 | cc-by-nc | needs_id |  |
| [386213101](https://www.inaturalist.org/observations/386213101) | 2026-07-29 | *Calidris temminckii* | Temminck's Stint | 47.70, 34.65 | 8.3 | cc-by-nc | needs_id |  |
| [386213810](https://www.inaturalist.org/observations/386213810) | 2026-07-29 | *Tringa erythropus* | Spotted Redshank | 47.70, 34.65 | 8.4 | cc-by-nc | research |  |
| [397402851](https://www.inaturalist.org/observations/397402851) | 2026-08-23 | *Locustella luscinioides* | Savi's Warbler | 47.66, 34.62 | 4.2 | cc-by-nc | needs_id |  |

**uabird (Ekaterina Kormina), BEFORE 6 June 2023** (55)

| iNat obs | Date (time) | Taxon | Common name | Lat, lon (2 dp) | km to crossing box | Licence | Grade | Note |
|---|---|---|---|---|---|---|---|---|
| [127089544](https://www.inaturalist.org/observations/127089544) | 2022-06-08 | *Otus scops* | Eurasian Scops-Owl | 47.65, 34.62 | 3.0 | cc-by-nc | research |  |
| [121344152](https://www.inaturalist.org/observations/121344152) | 2022-06-12 | *Parus major* | Great Tit | 47.65, 34.62 | 3.0 | cc-by-nc | research |  |
| [127088883](https://www.inaturalist.org/observations/127088883) | 2022-06-12 | *Carduelis carduelis* | European Goldfinch | 47.65, 34.62 | 3.0 | cc-by-nc | research |  |
| [127089335](https://www.inaturalist.org/observations/127089335) | 2022-06-12 | *Pica pica* | Eurasian Magpie | 47.65, 34.62 | 3.0 | cc-by-nc | research |  |
| [127090018](https://www.inaturalist.org/observations/127090018) | 2022-06-12 | *Fringilla coelebs* | Common Chaffinch | 47.65, 34.62 | 3.0 | cc-by-nc | research |  |
| [127092650](https://www.inaturalist.org/observations/127092650) | 2022-07-20 | *Parus major* | Great Tit | 47.65, 34.62 | 3.0 | cc-by-nc | research |  |
| [127097774](https://www.inaturalist.org/observations/127097774) | 2022-07-20 | *Oriolus oriolus* | Eurasian Golden Oriole | 47.65, 34.62 | 3.0 | cc-by-nc | research |  |
| [127331877](https://www.inaturalist.org/observations/127331877) | 2022-07-22 | *Curruca curruca* | Lesser Whitethroat | 47.65, 34.62 | 3.0 | cc-by-nc | needs_id |  |
| [131314250](https://www.inaturalist.org/observations/131314250) | 2022-08-17 | *Corvus corax* | Common Raven | 47.65, 34.62 | 3.0 | cc-by-nc | research |  |
| [131314427](https://www.inaturalist.org/observations/131314427) | 2022-08-17 | *Chloris chloris* | European Greenfinch | 47.65, 34.62 | 3.0 | cc-by-nc | research |  |
| [138092360](https://www.inaturalist.org/observations/138092360) | 2022-10-09 | *Anthus pratensis* | Meadow Pipit | 47.66, 34.61 | 4.0 | cc-by-nc | research |  |
| [138946777](https://www.inaturalist.org/observations/138946777) | 2022-10-16 | *Fringilla coelebs* | Common Chaffinch | 47.66, 34.61 | 4.3 | cc-by-nc | research |  |
| [139850424](https://www.inaturalist.org/observations/139850424) | 2022-10-24 | *Periparus ater* | Coal Tit | 47.65, 34.62 | 3.9 | cc-by-nc | research |  |
| [139949889](https://www.inaturalist.org/observations/139949889) | 2022-10-25 | *Lanius excubitor* | Great Gray Shrike | 47.66, 34.61 | 4.0 | cc-by-nc | research |  |
| [139949999](https://www.inaturalist.org/observations/139949999) | 2022-10-25 | *Linaria cannabina* | Eurasian Linnet | 47.66, 34.62 | 4.2 | cc-by-nc | research |  |
| [141523959](https://www.inaturalist.org/observations/141523959) | 2022-11-09 | *Anser albifrons* | Greater White-fronted Goose | 47.67, 34.60 | 5.6 | cc-by-nc | research |  |
| [141524010](https://www.inaturalist.org/observations/141524010) | 2022-11-09 | *Anser albifrons* | Greater White-fronted Goose | 47.66, 34.62 | 4.4 | cc-by-nc | research |  |
| [141627407](https://www.inaturalist.org/observations/141627407) | 2022-11-10 | *Rallus aquaticus* | Water Rail | 47.65, 34.61 | 3.6 | cc-by-nc | research |  |
| [142586410](https://www.inaturalist.org/observations/142586410) | 2022-11-21 | *Erithacus rubecula* | European Robin | 47.65, 34.61 | 3.6 | cc-by-nc | research |  |
| [145687213](https://www.inaturalist.org/observations/145687213) | 2023-01-02 | *Coccothraustes coccothraustes* | Hawfinch | 47.66, 34.61 | 4.5 | cc-by-nc | research |  |
| [150133921](https://www.inaturalist.org/observations/150133921) | 2023-03-02 10:58 | *Anas crecca* | Green-winged Teal | 47.68, 34.64 | 7.0 | cc-by-nc | research |  |
| [150298052](https://www.inaturalist.org/observations/150298052) | 2023-03-05 10:03 | *Lullula arborea* | Woodlark | 47.67, 34.61 | 5.2 | cc-by-nc | needs_id |  |
| [150662419](https://www.inaturalist.org/observations/150662419) | 2023-03-09 12:28 | *Alauda arvensis* | Eurasian Skylark | 47.67, 34.63 | 6.0 | cc-by-nc | research |  |
| [151038351](https://www.inaturalist.org/observations/151038351) | 2023-03-13 14:10 | *Phylloscopus collybita* | Common Chiffchaff | 47.68, 34.64 | 7.0 | cc-by-nc | research |  |
| [151706804](https://www.inaturalist.org/observations/151706804) | 2023-03-19 13:32 | *Tachybaptus ruficollis* | Little Grebe | 47.70, 34.66 | 8.4 | cc-by-nc | research |  |
| [152234961](https://www.inaturalist.org/observations/152234961) | 2023-03-25 07:37 | *Turdus merula* | Eurasian Blackbird | 47.66, 34.62 | 4.5 | cc-by-nc | research |  |
| [152236251](https://www.inaturalist.org/observations/152236251) | 2023-03-25 07:57 | *Melanocorypha calandra* | Calandra Lark | 47.67, 34.61 | 5.3 | cc-by-nc | needs_id |  |
| [152236521](https://www.inaturalist.org/observations/152236521) | 2023-03-25 08:00 | *Alauda arvensis* | Eurasian Skylark | 47.67, 34.61 | 5.7 | cc-by-nc | research |  |
| [153430575](https://www.inaturalist.org/observations/153430575) | 2023-04-04 10:00 | *Luscinia svecica* | Bluethroat | 47.69, 34.64 | 7.6 | cc-by-nc | research |  |
| [155157931](https://www.inaturalist.org/observations/155157931) | 2023-04-06 10:40 | *Phylloscopus collybita tristis* | Siberian Chiffchaff | 47.68, 34.63 | 6.7 | cc-by-nc | research |  |
| [160040552](https://www.inaturalist.org/observations/160040552) | 2023-04-07 | *Turdus philomelos* | Song Thrush | 47.66, 34.62 | 4.5 | cc-by-nc | research |  |
| [154971073](https://www.inaturalist.org/observations/154971073) | 2023-04-15 11:30 | *Bombina bombina* | European Fire-Bellied Toad | 47.65, 34.61 | 3.6 | cc-by-nc | research |  |
| [155159095](https://www.inaturalist.org/observations/155159095) | 2023-04-16 12:23 | *Locustella luscinioides* | Savi's Warbler | 47.68, 34.60 | 6.6 | cc-by-nc | research |  |
| [162116934](https://www.inaturalist.org/observations/162116934) | 2023-04-16 | *Ficedula hypoleuca* | European Pied Flycatcher | 47.67, 34.60 | 5.9 | cc-by-nc | needs_id |  |
| [155469050](https://www.inaturalist.org/observations/155469050) | 2023-04-18 11:50 | *Curruca curruca* | Lesser Whitethroat | 47.65, 34.61 | 3.9 | cc-by-nc | research |  |
| [156241043](https://www.inaturalist.org/observations/156241043) | 2023-04-23 09:25 | *Luscinia luscinia* | Thrush Nightingale | 47.66, 34.62 | 4.4 | cc-by-nc | research |  |
| [156241430](https://www.inaturalist.org/observations/156241430) | 2023-04-23 10:35 | *Phylloscopus trochilus* | Willow Warbler | 47.68, 34.63 | 6.7 | cc-by-nc | research |  |
| [156402209](https://www.inaturalist.org/observations/156402209) | 2023-04-24 11:05 | *Curruca communis* | Greater Whitethroat | 47.68, 34.60 | 6.5 | cc-by-nc | research |  |
| [156712099](https://www.inaturalist.org/observations/156712099) | 2023-04-26 10:28 | *Tringa nebularia* | Common Greenshank | 47.66, 34.61 | 3.9 | cc-by-nc | research |  |
| [156744518](https://www.inaturalist.org/observations/156744518) | 2023-04-26 | *Luscinia megarhynchos megarhynchos* |  | 47.66, 34.60 | 4.1 | cc-by-nc | needs_id |  |
| [158501696](https://www.inaturalist.org/observations/158501696) | 2023-04-26 | *Otus scops* | Eurasian Scops-Owl | 47.66, 34.60 | 4.0 | cc-by-nc | research |  |
| [158503131](https://www.inaturalist.org/observations/158503131) | 2023-04-30 | *Melanocorypha calandra* | Calandra Lark | 47.67, 34.61 | 6.1 | cc-by-nc | research |  |
| [158692809](https://www.inaturalist.org/observations/158692809) | 2023-05-01 12:56 | *Tringa erythropus* | Spotted Redshank | 47.66, 34.61 | 3.9 | cc-by-nc | research |  |
| [158699285](https://www.inaturalist.org/observations/158699285) | 2023-05-01 | *Acrocephalus scirpaceus* | Common Reed Warbler | 47.66, 34.63 | 4.3 | cc-by-nc | research |  |
| [159393683](https://www.inaturalist.org/observations/159393683) | 2023-05-03 | *Phylloscopus sibilatrix* | Wood Warbler | 47.66, 34.62 | 4.1 | cc-by-nc | research |  |
| [159394784](https://www.inaturalist.org/observations/159394784) | 2023-05-03 | *Coturnix coturnix* | Common Quail | 47.67, 34.61 | 5.7 | cc-by-nc | research |  |
| [159625094](https://www.inaturalist.org/observations/159625094) | 2023-05-04 | *Jynx torquilla* | Eurasian Wryneck | 47.66, 34.61 | 4.6 | cc-by-nc | research |  |
| [159836681](https://www.inaturalist.org/observations/159836681) | 2023-05-05 | *Crex crex* | Corn Crake | 47.69, 34.60 | 7.4 | cc-by-nc | research |  |
| [160040320](https://www.inaturalist.org/observations/160040320) | 2023-05-06 | *Phoenicurus phoenicurus* | Common Redstart | 47.64, 34.63 | 2.5 | cc-by-nc | research |  |
| [160275414](https://www.inaturalist.org/observations/160275414) | 2023-05-07 | *Carpodacus erythrinus* | Common Rosefinch | 47.66, 34.62 | 4.1 | cc-by-nc | research |  |
| [161047105](https://www.inaturalist.org/observations/161047105) | 2023-05-11 08:02 | *Botaurus minutus minutus* | Eurasian Little Bittern | 47.66, 34.62 | 4.3 | cc-by-nc | research |  |
| [161369315](https://www.inaturalist.org/observations/161369315) | 2023-05-13 | *Sylvia atricapilla* | Eurasian Blackcap | 47.66, 34.61 | 4.4 | cc-by-nc | research |  |
| [161954802](https://www.inaturalist.org/observations/161954802) | 2023-05-16 09:04 | *Lanius collurio* | Red-backed Shrike | 47.66, 34.62 | 4.3 | cc-by-nc | research |  |
| [162456909](https://www.inaturalist.org/observations/162456909) | 2023-05-19 | *Acrocephalus palustris* | Marsh Warbler | 47.66, 34.63 | 4.2 | cc-by-nc | research |  |
| [162673451](https://www.inaturalist.org/observations/162673451) | 2023-05-20 | *Acrocephalus palustris* | Marsh Warbler | 47.66, 34.62 | 4.4 | cc-by-nc | research |  |

**vasyliuk1 (Oleksii Vasyliuk), 2026** (144)

| iNat obs | Date (time) | Taxon | Common name | Lat, lon (2 dp) | km to crossing box | Licence | Grade | Note |
|---|---|---|---|---|---|---|---|---|
| [360972571](https://www.inaturalist.org/observations/360972571) | 2026-05-13 | *Luscinia luscinia* | Thrush Nightingale | 47.51, 33.93 | 48.0 | cc-by | needs_id |  |
| [360982745](https://www.inaturalist.org/observations/360982745) | 2026-05-13 | *Luscinia luscinia* | Thrush Nightingale | 47.50, 33.93 | 48.0 | cc-by | needs_id |  |
| [361037618](https://www.inaturalist.org/observations/361037618) | 2026-05-13 | *Luscinia* | Nightingales and Allies | 47.50, 33.93 | 48.1 | cc-by | needs_id |  |
| [361076968](https://www.inaturalist.org/observations/361076968) | 2026-05-13 | *Apus apus* | Common Swift | 47.50, 33.93 | 48.3 | cc-by | research |  |
| [361077098](https://www.inaturalist.org/observations/361077098) | 2026-05-13 | *Passer domesticus* | House Sparrow | 47.50, 33.93 | 48.3 | cc-by | needs_id |  |
| [361079259](https://www.inaturalist.org/observations/361079259) | 2026-05-13 | *Passer montanus* | Eurasian Tree Sparrow | 47.50, 33.93 | 48.3 | cc-by | needs_id |  |
| [361079271](https://www.inaturalist.org/observations/361079271) | 2026-05-13 | *Streptopelia decaocto* | Eurasian Collared-Dove | 47.50, 33.93 | 48.3 | cc-by | research |  |
| [361080772](https://www.inaturalist.org/observations/361080772) | 2026-05-13 | *Dendrocopos syriacus* | Syrian Woodpecker | 47.50, 33.93 | 48.3 | cc-by | research |  |
| [361082108](https://www.inaturalist.org/observations/361082108) | 2026-05-13 | *Parus major* | Great Tit | 47.50, 33.93 | 48.3 | cc-by | needs_id |  |
| [361092146](https://www.inaturalist.org/observations/361092146) | 2026-05-13 | *Ficedula albicollis* | Collared Flycatcher | 47.51, 33.92 | 48.5 | cc-by | research |  |
| [361092417](https://www.inaturalist.org/observations/361092417) | 2026-05-13 | *Chloris chloris* | European Greenfinch | 47.51, 33.92 | 48.6 | cc-by | research |  |
| [361107231](https://www.inaturalist.org/observations/361107231) | 2026-05-13 | *Turdus merula* | Eurasian Blackbird | 47.51, 33.92 | 48.7 | cc-by | research |  |
| [361107243](https://www.inaturalist.org/observations/361107243) | 2026-05-13 | *Chloris chloris* | European Greenfinch | 47.51, 33.92 | 48.7 | cc-by | needs_id | зеленяк.гор.хатн.серп.дрізд ч |
| [361107265](https://www.inaturalist.org/observations/361107265) | 2026-05-13 | *Parus major* | Great Tit | 47.51, 33.92 | 48.7 | cc-by | needs_id |  |
| [361107335](https://www.inaturalist.org/observations/361107335) | 2026-05-13 | *Muscicapa striata* | Spotted Flycatcher | 47.51, 33.92 | 48.6 | cc-by | research |  |
| [361107351](https://www.inaturalist.org/observations/361107351) | 2026-05-13 | *Oriolus oriolus* | Eurasian Golden Oriole | 47.51, 33.93 | 48.4 | cc-by | research |  |
| [361107397](https://www.inaturalist.org/observations/361107397) | 2026-05-13 | *Passer domesticus* | House Sparrow | 47.51, 33.93 | 48.4 | cc-by | needs_id |  |
| [361107935](https://www.inaturalist.org/observations/361107935) | 2026-05-13 | *Passer domesticus* | House Sparrow | 47.51, 33.93 | 48.4 | cc-by | needs_id |  |
| [361110893](https://www.inaturalist.org/observations/361110893) | 2026-05-13 | *Lanius collurio* | Red-backed Shrike | 47.51, 33.93 | 48.2 | cc-by | research |  |
| [361111466](https://www.inaturalist.org/observations/361111466) | 2026-05-13 | *Curruca communis* | Greater Whitethroat | 47.51, 33.93 | 48.2 | cc-by | research |  |
| [361112342](https://www.inaturalist.org/observations/361112342) | 2026-05-13 | *Phasianus colchicus* | Ring-necked Pheasant | 47.51, 33.93 | 48.2 | cc-by | research |  |
| [361112369](https://www.inaturalist.org/observations/361112369) | 2026-05-13 | *Aves* | Birds | 47.51, 33.93 | 48.2 | cc-by | needs_id |  |
| [361112868](https://www.inaturalist.org/observations/361112868) | 2026-05-13 | *Cuculus canorus* | Common Cuckoo | 47.51, 33.93 | 48.2 | cc-by | research |  |
| [361113350](https://www.inaturalist.org/observations/361113350) | 2026-05-13 | *Curruca communis* | Greater Whitethroat | 47.51, 33.93 | 48.2 | cc-by | research |  |
| [361134120](https://www.inaturalist.org/observations/361134120) | 2026-05-13 | *Sturnus vulgaris* | European Starling | 47.50, 33.94 | 47.7 | cc-by | research | Шпак повторює звуки збиття бпла |
| [361153963](https://www.inaturalist.org/observations/361153963) | 2026-05-13 | *Passeriformes* | Perching Birds | 47.51, 33.93 | 48.3 | cc-by | needs_id |  |
| [361154660](https://www.inaturalist.org/observations/361154660) | 2026-05-13 | *Fringilla coelebs* | Common Chaffinch | 47.51, 33.93 | 48.3 | cc-by | needs_id |  |
| [361156705](https://www.inaturalist.org/observations/361156705) | 2026-05-13 | *Dendrocopos syriacus* | Syrian Woodpecker | 47.51, 33.93 | 48.4 | cc-by | research |  |
| [361156832](https://www.inaturalist.org/observations/361156832) | 2026-05-13 | *Tadorna ferruginea* | Ruddy Shelduck | 47.51, 33.93 | 48.2 | cc-by | research |  |
| [361158153](https://www.inaturalist.org/observations/361158153) | 2026-05-13 | *Acrocephalus arundinaceus* | Great Reed Warbler | 47.51, 33.93 | 48.2 | cc-by | research |  |
| [361159099](https://www.inaturalist.org/observations/361159099) | 2026-05-13 | *Hirundo rustica* | Barn Swallow | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [361161207](https://www.inaturalist.org/observations/361161207) | 2026-05-13 | *Chloris chloris* | European Greenfinch | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [361169982](https://www.inaturalist.org/observations/361169982) | 2026-05-13 | *Acrocephalus arundinaceus* | Great Reed Warbler | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [361170797](https://www.inaturalist.org/observations/361170797) | 2026-05-13 | *Acrocephalus arundinaceus* | Great Reed Warbler | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [361196808](https://www.inaturalist.org/observations/361196808) | 2026-05-13 | *Fringilla coelebs* | Common Chaffinch | 47.51, 33.92 | 48.7 | cc-by | needs_id |  |
| [361196968](https://www.inaturalist.org/observations/361196968) | 2026-05-13 | *Turdus merula* | Eurasian Blackbird | 47.51, 33.92 | 48.7 | cc-by | research |  |
| [361197154](https://www.inaturalist.org/observations/361197154) | 2026-05-13 | *Chloris chloris* | European Greenfinch | 47.51, 33.92 | 48.7 | cc-by | research |  |
| [361197483](https://www.inaturalist.org/observations/361197483) | 2026-05-13 | *Aves* | Birds | 47.51, 33.93 | 48.4 | cc-by | needs_id |  |
| [361197615](https://www.inaturalist.org/observations/361197615) | 2026-05-13 | *Linaria cannabina* | Eurasian Linnet | 47.51, 33.93 | 48.4 | cc-by | research |  |
| [361197735](https://www.inaturalist.org/observations/361197735) | 2026-05-13 | *Oriolus oriolus* | Eurasian Golden Oriole | 47.51, 33.93 | 48.4 | cc-by | research |  |
| [361197806](https://www.inaturalist.org/observations/361197806) | 2026-05-13 | *Fringilla coelebs* | Common Chaffinch | 47.51, 33.93 | 48.4 | cc-by | needs_id |  |
| [361198282](https://www.inaturalist.org/observations/361198282) | 2026-05-13 | *Passer* | True Sparrows | 47.51, 33.93 | 48.4 | cc-by | needs_id |  |
| [361198549](https://www.inaturalist.org/observations/361198549) | 2026-05-13 | *Passeriformes* | Perching Birds | 47.51, 33.93 | 48.2 | cc-by | needs_id |  |
| [361198637](https://www.inaturalist.org/observations/361198637) | 2026-05-13 | *Curruca communis* | Greater Whitethroat | 47.51, 33.93 | 48.2 | cc-by | research |  |
| [361198765](https://www.inaturalist.org/observations/361198765) | 2026-05-13 | *Chloris chloris* | European Greenfinch | 47.51, 33.93 | 48.2 | cc-by | research |  |
| [361199188](https://www.inaturalist.org/observations/361199188) | 2026-05-13 | *Jynx torquilla* | Eurasian Wryneck | 47.51, 33.93 | 48.2 | cc-by | research |  |
| [361199408](https://www.inaturalist.org/observations/361199408) | 2026-05-13 | *Passeriformes* | Perching Birds | 47.50, 33.94 | 47.7 | cc-by | needs_id |  |
| [361199567](https://www.inaturalist.org/observations/361199567) | 2026-05-13 | *Passeriformes* | Perching Birds | 47.50, 33.94 | 47.7 | cc-by | needs_id |  |
| [361199708](https://www.inaturalist.org/observations/361199708) | 2026-05-13 | *Passeriformes* | Perching Birds | 47.50, 33.94 | 47.7 | cc-by | needs_id |  |
| [361199943](https://www.inaturalist.org/observations/361199943) | 2026-05-13 | *Ficedula albicollis* | Collared Flycatcher | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [361200042](https://www.inaturalist.org/observations/361200042) | 2026-05-13 | *Chloris chloris* | European Greenfinch | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [361200337](https://www.inaturalist.org/observations/361200337) | 2026-05-13 | *Acrocephalus arundinaceus* | Great Reed Warbler | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [361200407](https://www.inaturalist.org/observations/361200407) | 2026-05-13 | *Parus major* | Great Tit | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [361200960](https://www.inaturalist.org/observations/361200960) | 2026-05-13 | *Acrocephalus arundinaceus* | Great Reed Warbler | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [361201052](https://www.inaturalist.org/observations/361201052) | 2026-05-13 | *Turdus merula* | Eurasian Blackbird | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [361201135](https://www.inaturalist.org/observations/361201135) | 2026-05-13 | *Parus major* | Great Tit | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [361201265](https://www.inaturalist.org/observations/361201265) | 2026-05-13 | *Turdus merula* | Eurasian Blackbird | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [361201406](https://www.inaturalist.org/observations/361201406) | 2026-05-13 | *Chloris chloris* | European Greenfinch | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [361201578](https://www.inaturalist.org/observations/361201578) | 2026-05-13 | *Streptopelia decaocto* | Eurasian Collared-Dove | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [361201631](https://www.inaturalist.org/observations/361201631) | 2026-05-13 | *Passeriformes* | Perching Birds | 47.51, 33.93 | 48.3 | cc-by | needs_id |  |
| [361201700](https://www.inaturalist.org/observations/361201700) | 2026-05-13 | *Hirundo rustica* | Barn Swallow | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [361201801](https://www.inaturalist.org/observations/361201801) | 2026-05-13 | *Tadorna ferruginea* | Ruddy Shelduck | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [361202093](https://www.inaturalist.org/observations/361202093) | 2026-05-13 | *Panurus biarmicus* | Bearded Reedling | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [361202177](https://www.inaturalist.org/observations/361202177) | 2026-05-13 | *Hirundo rustica* | Barn Swallow | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [361330316](https://www.inaturalist.org/observations/361330316) | 2026-05-14 | *Linaria cannabina* | Eurasian Linnet | 47.50, 33.93 | 48.3 | cc-by | research |  |
| [361360422](https://www.inaturalist.org/observations/361360422) | 2026-05-14 | *Columbidae* | Pigeons and Doves | 47.50, 33.93 | 48.3 | cc-by | needs_id |  |
| [361360789](https://www.inaturalist.org/observations/361360789) | 2026-05-14 | *Locustella luscinioides* | Savi's Warbler | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361455843](https://www.inaturalist.org/observations/361455843) | 2026-05-14 | *Luscinia luscinia* | Thrush Nightingale | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361456200](https://www.inaturalist.org/observations/361456200) | 2026-05-14 | *Acrocephalus scirpaceus* | Common Reed Warbler | 47.55, 33.93 | 47.7 | cc-by | research |  |
| [361456461](https://www.inaturalist.org/observations/361456461) | 2026-05-14 | *Fulica atra* | Eurasian Coot | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361456705](https://www.inaturalist.org/observations/361456705) | 2026-05-14 | *Luscinia luscinia* | Thrush Nightingale | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361466662](https://www.inaturalist.org/observations/361466662) | 2026-05-14 | *Upupa epops* | Common Hoopoe | 47.55, 33.93 | 47.9 | cc-by | research |  |
| [361466711](https://www.inaturalist.org/observations/361466711) | 2026-05-14 | *Cyanistes caeruleus* | Eurasian Blue Tit | 47.55, 33.93 | 47.9 | cc-by | research |  |
| [361466739](https://www.inaturalist.org/observations/361466739) | 2026-05-14 | *Merops apiaster* | European Bee-eater | 47.55, 33.94 | 47.4 | cc-by | research |  |
| [361466803](https://www.inaturalist.org/observations/361466803) | 2026-05-14 | *Hirundo rustica* | Barn Swallow | 47.56, 33.93 | 47.8 | cc-by | research |  |
| [361466862](https://www.inaturalist.org/observations/361466862) | 2026-05-14 | *Thinornis dubius* | Little Ringed Plover | 47.56, 33.93 | 47.9 | cc-by | needs_id |  |
| [361466912](https://www.inaturalist.org/observations/361466912) | 2026-05-14 | *Emberiza calandra* | Corn Bunting | 47.56, 33.93 | 47.9 | cc-by | research |  |
| [361466968](https://www.inaturalist.org/observations/361466968) | 2026-05-14 | *Emberiza calandra* | Corn Bunting | 47.56, 33.93 | 48.0 | cc-by | research |  |
| [361467056](https://www.inaturalist.org/observations/361467056) | 2026-05-14 | *Emberiza calandra* | Corn Bunting | 47.56, 33.93 | 47.9 | cc-by | research |  |
| [361467211](https://www.inaturalist.org/observations/361467211) | 2026-05-14 | *Remiz pendulinus* | Eurasian Penduline-Tit | 47.56, 33.93 | 48.0 | cc-by | research |  |
| [361467233](https://www.inaturalist.org/observations/361467233) | 2026-05-14 | *Recurvirostra avosetta* | Pied Avocet | 47.56, 33.93 | 48.0 | cc-by | needs_id |  |
| [361467290](https://www.inaturalist.org/observations/361467290) | 2026-05-14 | *Locustella luscinioides* | Savi's Warbler | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361467339](https://www.inaturalist.org/observations/361467339) | 2026-05-14 | *Passeriformes* | Perching Birds | 47.55, 33.93 | 47.8 | cc-by | needs_id |  |
| [361467377](https://www.inaturalist.org/observations/361467377) | 2026-05-14 | *Luscinia luscinia* | Thrush Nightingale | 47.55, 33.93 | 47.8 | cc-by | research | На фоні фпв дрон |
| [361467416](https://www.inaturalist.org/observations/361467416) | 2026-05-14 | *Locustella luscinioides* | Savi's Warbler | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361467464](https://www.inaturalist.org/observations/361467464) | 2026-05-14 | *Acrocephalus agricola* | Paddyfield Warbler | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361467520](https://www.inaturalist.org/observations/361467520) | 2026-05-14 | *Otus scops* | Eurasian Scops-Owl | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361637446](https://www.inaturalist.org/observations/361637446) | 2026-05-14 | *Luscinia luscinia* | Thrush Nightingale | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361637495](https://www.inaturalist.org/observations/361637495) | 2026-05-14 | *Phasianus colchicus* | Ring-necked Pheasant | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361637589](https://www.inaturalist.org/observations/361637589) | 2026-05-14 | *Remiz pendulinus* | Eurasian Penduline-Tit | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361637622](https://www.inaturalist.org/observations/361637622) | 2026-05-14 | *Chloris chloris* | European Greenfinch | 47.55, 33.93 | 47.8 | cc-by | needs_id |  |
| [361637665](https://www.inaturalist.org/observations/361637665) | 2026-05-14 | *Motacilla flava* | Western Yellow Wagtail | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361637680](https://www.inaturalist.org/observations/361637680) | 2026-05-14 | *Fulica atra* | Eurasian Coot | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361637701](https://www.inaturalist.org/observations/361637701) | 2026-05-14 | *Acrocephalus arundinaceus* | Great Reed Warbler | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361637893](https://www.inaturalist.org/observations/361637893) | 2026-05-14 | *Luscinia luscinia* | Thrush Nightingale | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361637914](https://www.inaturalist.org/observations/361637914) | 2026-05-14 | *Phasianus colchicus* | Ring-necked Pheasant | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361637998](https://www.inaturalist.org/observations/361637998) | 2026-05-14 | *Cuculus canorus* | Common Cuckoo | 47.56, 33.93 | 48.0 | cc-by | research |  |
| [361638030](https://www.inaturalist.org/observations/361638030) | 2026-05-14 | *Motacilla flava* | Western Yellow Wagtail | 47.56, 33.93 | 48.0 | cc-by | research |  |
| [361638096](https://www.inaturalist.org/observations/361638096) | 2026-05-14 | *Luscinia luscinia* | Thrush Nightingale | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361638134](https://www.inaturalist.org/observations/361638134) | 2026-05-14 | *Acrocephalus arundinaceus* | Great Reed Warbler | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361638222](https://www.inaturalist.org/observations/361638222) | 2026-05-14 | *Motacilla flava* | Western Yellow Wagtail | 47.56, 33.93 | 47.9 | cc-by | research |  |
| [361638295](https://www.inaturalist.org/observations/361638295) | 2026-05-14 | *Tadorna ferruginea* | Ruddy Shelduck | 47.56, 33.93 | 47.9 | cc-by | needs_id |  |
| [361638383](https://www.inaturalist.org/observations/361638383) | 2026-05-14 | *Apus apus* | Common Swift | 47.56, 33.93 | 47.8 | cc-by | research |  |
| [361638398](https://www.inaturalist.org/observations/361638398) | 2026-05-14 | *Tadorna ferruginea* | Ruddy Shelduck | 47.56, 33.93 | 47.8 | cc-by | needs_id |  |
| [361638502](https://www.inaturalist.org/observations/361638502) | 2026-05-14 | *Cuculus canorus* | Common Cuckoo | 47.55, 33.93 | 47.7 | cc-by | research |  |
| [361638636](https://www.inaturalist.org/observations/361638636) | 2026-05-14 | *Passer domesticus* | House Sparrow | 47.50, 33.93 | 48.3 | cc-by | research |  |
| [361638651](https://www.inaturalist.org/observations/361638651) | 2026-05-14 | *Passer montanus* | Eurasian Tree Sparrow | 47.50, 33.93 | 48.3 | cc-by | research |  |
| [361638677](https://www.inaturalist.org/observations/361638677) | 2026-05-14 | *Apus apus* | Common Swift | 47.50, 33.93 | 48.3 | cc-by | research |  |
| [361638710](https://www.inaturalist.org/observations/361638710) | 2026-05-14 | *Streptopelia decaocto* | Eurasian Collared-Dove | 47.50, 33.93 | 48.3 | cc-by | research |  |
| [361638798](https://www.inaturalist.org/observations/361638798) | 2026-05-14 | *Chloris chloris* | European Greenfinch | 47.50, 33.93 | 48.3 | cc-by | research |  |
| [361638845](https://www.inaturalist.org/observations/361638845) | 2026-05-14 | *Linaria cannabina* | Eurasian Linnet | 47.50, 33.93 | 48.3 | cc-by | research |  |
| [361638892](https://www.inaturalist.org/observations/361638892) | 2026-05-14 | *Carduelis carduelis* | European Goldfinch | 47.50, 33.93 | 48.3 | cc-by | research |  |
| [361638941](https://www.inaturalist.org/observations/361638941) | 2026-05-14 | *Chloris chloris* | European Greenfinch | 47.50, 33.93 | 48.3 | cc-by | research |  |
| [361639005](https://www.inaturalist.org/observations/361639005) | 2026-05-14 | *Cuculus canorus* | Common Cuckoo | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361639062](https://www.inaturalist.org/observations/361639062) | 2026-05-14 | *Acrocephalus scirpaceus* | Common Reed Warbler | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361639097](https://www.inaturalist.org/observations/361639097) | 2026-05-14 | *Luscinia luscinia* | Thrush Nightingale | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361639110](https://www.inaturalist.org/observations/361639110) | 2026-05-14 | *Acrocephalus arundinaceus* | Great Reed Warbler | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361639168](https://www.inaturalist.org/observations/361639168) | 2026-05-14 | *Tadorna ferruginea* | Ruddy Shelduck | 47.56, 33.93 | 48.0 | cc-by | research |  |
| [361639188](https://www.inaturalist.org/observations/361639188) | 2026-05-14 | *Remiz pendulinus* | Eurasian Penduline-Tit | 47.56, 33.93 | 48.0 | cc-by | research |  |
| [361639215](https://www.inaturalist.org/observations/361639215) | 2026-05-14 | *Recurvirostra avosetta* | Pied Avocet | 47.56, 33.93 | 48.0 | cc-by | needs_id |  |
| [361639340](https://www.inaturalist.org/observations/361639340) | 2026-05-14 | *Phasianus colchicus* | Ring-necked Pheasant | 47.56, 33.93 | 48.0 | cc-by | research |  |
| [361639413](https://www.inaturalist.org/observations/361639413) | 2026-05-14 | *Locustella luscinioides* | Savi's Warbler | 47.55, 33.94 | 47.4 | cc-by | research |  |
| [361639437](https://www.inaturalist.org/observations/361639437) | 2026-05-14 | *Acrocephalus arundinaceus* | Great Reed Warbler | 47.55, 33.94 | 47.4 | cc-by | research |  |
| [361639473](https://www.inaturalist.org/observations/361639473) | 2026-05-14 | *Fulica atra* | Eurasian Coot | 47.55, 33.94 | 47.4 | cc-by | research |  |
| [361639503](https://www.inaturalist.org/observations/361639503) | 2026-05-14 | *Passeriformes* | Perching Birds | 47.55, 33.94 | 47.4 | cc-by | needs_id |  |
| [361639531](https://www.inaturalist.org/observations/361639531) | 2026-05-14 | *Phasianus colchicus* | Ring-necked Pheasant | 47.55, 33.94 | 47.4 | cc-by | research |  |
| [361639581](https://www.inaturalist.org/observations/361639581) | 2026-05-14 | *Motacilla alba* | White Wagtail | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361639603](https://www.inaturalist.org/observations/361639603) | 2026-05-14 | *Locustella luscinioides* | Savi's Warbler | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361639622](https://www.inaturalist.org/observations/361639622) | 2026-05-14 | *Saxicola rubicola* | European Stonechat | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [361639663](https://www.inaturalist.org/observations/361639663) | 2026-05-14 | *Turdus philomelos* | Song Thrush | 47.55, 33.93 | 47.8 | cc-by | research |  |
| [381300535](https://www.inaturalist.org/observations/381300535) | 2026-07-14 | *Hirundo rustica rustica* | White-bellied Barn Swallow | 47.51, 33.93 | 47.9 | cc-by | needs_id |  |
| [381300833](https://www.inaturalist.org/observations/381300833) | 2026-07-14 | *Cuculus canorus* | Common Cuckoo | 47.51, 33.93 | 48.2 | cc-by | research |  |
| [381300910](https://www.inaturalist.org/observations/381300910) | 2026-07-14 | *Phasianus colchicus* | Ring-necked Pheasant | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [381474963](https://www.inaturalist.org/observations/381474963) | 2026-07-14 | *Sylvia atricapilla* | Eurasian Blackcap | 47.51, 33.93 | 47.9 | cc-by | research |  |
| [381475063](https://www.inaturalist.org/observations/381475063) | 2026-07-14 | *Oriolus oriolus* | Eurasian Golden Oriole | 47.51, 33.93 | 48.2 | cc-by | research |  |
| [381475149](https://www.inaturalist.org/observations/381475149) | 2026-07-14 | *Oriolus oriolus* | Eurasian Golden Oriole | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [381475202](https://www.inaturalist.org/observations/381475202) | 2026-07-14 | *Turdus merula* | Eurasian Blackbird | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [381735481](https://www.inaturalist.org/observations/381735481) | 2026-07-15 | *Chloris chloris* | European Greenfinch | 47.51, 33.93 | 48.3 | cc-by | research |  |
| [381824666](https://www.inaturalist.org/observations/381824666) | 2026-07-16 | *Otus scops* | Eurasian Scops-Owl | 47.50, 33.92 | 49.1 | cc-by | research |  |
| [382020268](https://www.inaturalist.org/observations/382020268) | 2026-07-16 | *Apus apus* | Common Swift | 47.50, 33.93 | 48.4 | cc-by | needs_id |  |
| [382337946](https://www.inaturalist.org/observations/382337946) | 2026-07-16 | *Muscicapa striata* | Spotted Flycatcher | 47.50, 33.93 | 48.4 | cc-by | needs_id |  |
| [382338011](https://www.inaturalist.org/observations/382338011) | 2026-07-16 | *Streptopelia decaocto* | Eurasian Collared-Dove | 47.50, 33.93 | 48.4 | cc-by | research |  |
| [382484182](https://www.inaturalist.org/observations/382484182) | 2026-07-16 | *Oriolus oriolus* | Eurasian Golden Oriole | 47.50, 33.93 | 48.4 | cc-by | research |  |
| [382484263](https://www.inaturalist.org/observations/382484263) | 2026-07-16 | *Passer domesticus* | House Sparrow | 47.50, 33.93 | 48.4 | cc-by | needs_id |  |

**Other recordists in the box** (7)

| iNat obs | Date (time) | Taxon | Common name | Lat, lon (2 dp) | km to crossing box | Licence | Grade | Note |
|---|---|---|---|---|---|---|---|---|
| [40816876](https://www.inaturalist.org/observations/40816876) | 2020-03-27 17:08 | *Chloris chloris* | European Greenfinch | 47.83, 35.17 | 44.8 | cc-by-nc | research |  |
| [72272230](https://www.inaturalist.org/observations/72272230) | 2021-03-28 15:43 | *Haliaeetus albicilla* | White-tailed Eagle | 47.46, 33.93 | 48.4 | cc-by-nc | research |  |
| [280989253](https://www.inaturalist.org/observations/280989253) | 2025-05-14 | *Oriolus oriolus* | Eurasian Golden Oriole | 47.85, 35.08 | 40.2 | cc-by-nc | research |  |
| [353828021](https://www.inaturalist.org/observations/353828021) | 2026-04-25 22:56 | *Otus scops* | Eurasian Scops-Owl | 47.69, 34.02 | 41.9 | cc-by-nc | research |  |
| [381272794](https://www.inaturalist.org/observations/381272794) | 2026-07-14 06:45 | *Acrocephalus scirpaceus* | Common Reed Warbler | 47.68, 34.03 | 41.1 | cc-by-nc | research |  |
| [382228990](https://www.inaturalist.org/observations/382228990) | 2026-07-17 13:04 | *Dendrocopos syriacus* | Syrian Woodpecker | 47.69, 34.02 | 42.0 | cc-by-nc | research |  |
| [384453904](https://www.inaturalist.org/observations/384453904) | 2026-07-24 06:37 | *Coturnix coturnix* | Common Quail | 47.66, 34.02 | 41.5 | cc-by-nc | research |  |


### Inferences
- The 13–14 May 2026 Vasyliuk sessions are probably the four-day Novovorontsovka expedition Texty reported on 1 July
  2026 (same village, same "nightingales and reed warblers"); the article gives no dates, so this is a match by place
  and content only.
- A crude level check of 9 Vasyliuk files (not listening) found low-frequency-dominated stretches (over 70% of energy
  below 300 Hz) in [361455843](https://www.inaturalist.org/observations/361455843) (Thrush Nightingale), [361466862](https://www.inaturalist.org/observations/361466862) (Little Ringed Plover) and [361639622](https://www.inaturalist.org/observations/361639622) (Stonechat), and loud low-frequency events
  in [361467233](https://www.inaturalist.org/observations/361467233) (Pied Avocet, ~45 s, 35 dB over the file's median, 96% below 300 Hz) and [361467464](https://www.inaturalist.org/observations/361467464) (Paddyfield Warbler, ~44 s,
  48 dB over median). These could be wind, handling, vehicles, or distant explosions: they must be listened to before
  use. Given one file has a drone noted, the whole 13–14 May set (a frontline area under drone attack) should be
  listened through before any is blended.
- Vasyliuk's CC BY licence (commercial use allowed with attribution) makes his bed recordings the most reusable "on the
  bed" material; Kormina's iNat sounds are CC BY-NC (non-commercial only), while her xeno-canto uploads are CC0.
- Coverage is extremely biased: two recordists produce 260 of 267 sounds; the nearest-to-crossing material is one
  birder's home area; the occupied south bank and the bed floor near the plant (front line) have no recordings at all.
  Absence of a species' sound in the archives says nothing about its absence on the bed.

### Gaps
- iNaturalist sounds have no duration in the API; durations were measured only for the 14 files downloaded.
- Obscured observations show randomised public coordinates; none of the 267 was obscured, but obscured observations
  whose true position is on the bed and public position outside the box would be missed.
- Clock times are missing for all of Vasyliuk's and many of Kormina's observations.
- Whether the strong low-frequency events are war sounds could not be determined without listening.

## Macaulay Library / eBird, Freesound, Observation.org / UkrBIN, aporee and other archives and sound maps

### Takeaway
None of these holds a nature recording on the bed or within ~40 km of the crossing. Macaulay has 7 audio assets in
Zaporizhzhia oblast (none on the bed), none in the bed box from Dnipropetrovsk or Kherson oblasts since July 2023;
Freesound returns no results for any local place name; radio aporee has 3 points in the whole region, all in Kryvyi Rih;
the University of Birmingham's war soundscape exhibition has two Zaporizhzhia recordings, one a Shahed attack.

### Cited Findings
- **Macaulay Library** (audio, by eBird region, via the site's own search API in a browser; `raw/macaulay/`): UA-23
  Zaporizhzhia oblast has 7 audio assets in total — 6 by Vladimir Katsyba at "Ukrainka" (47.91, 35.37; 2024-04-08 to
  2025-09-16; east of Zaporizhzhia, off the reservoir) and asset 467639851, Eurasian Scops-Owl by Володимир Мерзлікін,
  2022-07-15 23:30, Zaporizhzhia (47.87, 35.11) — [ML search UA-23](https://search.macaulaylibrary.org/catalog?regionCode=UA-23&mediaType=audio&sort=obs_date_desc), [ML 467639851](https://macaulaylibrary.org/asset/467639851).
  UA-12 Dnipropetrovsk: the 600 newest audio assets (2023-07-21 to 2026-10-10) all lie north of 47.94 N (mostly "African
  Googre" in Dnipro city), none near Nikopol or Marhanets — [ML search UA-12](https://search.macaulaylibrary.org/catalog?regionCode=UA-12&mediaType=audio&sort=obs_date_desc).
  UA-65 Kherson: 32 assets, all 2017–2021, all at 46.13–46.57 N (Askania-Nova, lakes in the south), none on the
  reservoir — [ML search UA-65](https://search.macaulaylibrary.org/catalog?regionCode=UA-65&mediaType=audio&sort=obs_date_desc). The API gives licenceId "LICENSE4" for these (Macaulay's own terms; no CC licence shown).
- **Freesound:** site searches for Kakhovka, Nikopol, Enerhodar, Zaporizhzhia, Zaporozhye, Marhanets, Khortytsia,
  Kherson, Каховка, Запоріжжя, Нікополь all return "No results... Please try another search"; "Dnipro river" returns one
  sound, "Birds and fly at the big river.wav" (yaremaandhimey, 11 August 2018, CC0, 1:32 WAV), recorded at Rzhyshchiv,
  Kyiv oblast — **not local** — [Freesound search](https://freesound.org/search/?q=Zaporizhzhia), [sound 436676](https://freesound.org/people/yaremaandhimey/sounds/436676/). The geotag map endpoint is not open to scripts, so a map check was not possible.
- **radio aporee ::: maps:** of 68,505 locations in the map's own location list, only 3 fall in 46.6–48.0 N,
  32.8–35.5 E, all "Dzerzhyns'kyi district, Kryvyi Rih" (loc 23943, 23933, 23932) — [aporee maps](https://aporee.org/maps/?loc=47.5,34.4,8) (list from `/api/maps/getAllLocations`, read in the browser).
- **Observation.org:** the public API's around-point query accepts only a 7-day window and ≤10 km radius (longer
  windows return "Value is not valid"), and the last 7 days near Marhanets returned 0 — [Observation.org API](https://observation.org/api/v1/observations/around-point/?lat=47.62&lng=34.60&days=7&radius=10000). An archive search needs a login; not done.
- **University of Birmingham soundscape exhibition** (Janine Natalya Clark; 43 recordings by Ukrainian participants;
  no licence stated): Zaporizhzhia entries are "A frightening evening walk" (11 November 2024, 21:56: "A Shahed drone
  attack. A dog barks throughout the recording.") — **exclude** — and "At home with my cat and her kittens" (12 November
  2024, indoors). Its "Dnipro River" recordings (mallards, tits, crows; waves and raven song) are labelled "Central
  Ukraine", not local — [exhibition sounds](https://rethinking-transitional-justice.bham.ac.uk/sounds/exhibition/sounds/), [Birmingham news, 20 March 2025](https://www.birmingham.ac.uk/news/2025/a-new-online-exhibition-immerses-users-in-the-sounds-of-the-russia-ukraine-war).
  Its research dataset holds transcripts only, closed access — [edata.bham.ac.uk/1381](https://edata.bham.ac.uk/1381/).
- **"How the World Sounds... Ukraine"** (Synelnykov, Filatov; Zaporizhzhia episode, YouTube) features Zaporizhstal's
  industrial sounds and visits Khortytsia, but no nature recordings are described and no licence given — [Metinvest Media](https://metinvest.media/en/page/zvuki-zaporzhstal-hortic-ta-znahdok-dnprovih-porogv).
- A web search for acoustic monitoring (AudioMoth, BirdNET) of the Kakhovka bed found nothing specific to it —
  [search results incl. AudioMoth dataset](https://datadryad.org/stash/dataset/doi:10.5061%2Fdryad.369n9).

### Inferences
- The archives' silence near the crossing reflects access, not nature: the bed between Marhanets and Enerhodar is the
  front line (the river channel), and the south bank is occupied; citizen-science recording there is effectively
  impossible since 2022.
- For a "local" bed sound, the honest options are Vasyliuk's CC BY bed recordings (~48 km away, same reservoir, same new
  willow-and-reed habitat), labelled with their place, or Kormina's CC0/CC BY-NC north-bank recordings (3–8 km),
  labelled as the Marhanets shore, not the bed.

### Gaps
- UkrBIN (ukrbin.com) could not be searched (the search page returned nothing to a script); it is mostly photographs.
- The Tierstimmenarchiv (Berlin) and the British Library Sound Archive were not searched directly; web searches found
  no Kakhovka/Dnipro-reservoir holdings.
- Macaulay Dnipropetrovsk assets older than July 2023 (the "before" period) were not all read (the 600 newest only).
- Freesound's map (geotag) was not checked; only text search.
- No published BirdNET or passive acoustic monitoring dataset from the bed was found.

## Closest to the crossing, and what can be blended with the Hum

### Takeaway
For the Enerhodar crossing specifically, the closest real recordings are Kormina's north-bank set at Marhanets (2.5–8.4
km); XC1016138 and iNat 215504232 (a Sylviid song, 2024-05-13, same spot) are probably the same recording. Best candidates to blend: **XC1016141** (thrush nightingale, CC0, 60 s, 4.0 km), **XC1016138** (Sylviid song, CC0,
53 s, 3.0 km), the **cicada** (iNat 231228832, CC BY-NC, 21 s, 4.2 km, a continuous buzz that sits naturally beside a
line hum), and from the bed itself (48 km away) Vasyliuk's CC BY reed-bed chorus at Mar'ianske, excluding the two
recordings with drone notes and after listening through the rest.

### Cited Findings
- Closest post-drainage recordings, all Ekaterina Kormina, north bank: [XC1016138](https://xeno-canto.org/1016138) 3.0 km (2024-05-13, CC0); iNat [215504232](https://www.inaturalist.org/observations/215504232), [216994873](https://www.inaturalist.org/observations/216994873), [278933854](https://www.inaturalist.org/observations/278933854), [279970419](https://www.inaturalist.org/observations/279970419), [365277208](https://www.inaturalist.org/observations/365277208) (Red-breasted Flycatcher, 2026-05-26 04:39), [374114900](https://www.inaturalist.org/observations/374114900) (Scops-Owl, 2026-06-22 01:56) at 3.0 km (CC BY-NC); [XC1016141](https://xeno-canto.org/1016141) and [XC1016134](https://xeno-canto.org/1016134) 4.0 km (CC0); [XC1016032](https://xeno-canto.org/1016032) 4.3 km (CC0) — tables above.
- Licence terms: CC0 waives all rights ([CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)); CC BY-NC
  allows reuse with credit, non-commercial only (iNaturalist default for sounds); CC BY-NC-SA adds share-alike
  ([CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)); CC BY allows any use with credit.
- Recordist-noted war sounds (exclude): iNat [361467377](https://www.inaturalist.org/observations/361467377) (FPV drone) and [361134120](https://www.inaturalist.org/observations/361134120) (starling imitating a drone shoot-down); Birmingham "A frightening evening walk", Zaporizhzhia (Shahed attack) — sources above.

### Inferences
- Short clips (5–30 s, many under 20 s) suit layering or looping under the Hum; the 60–115 s ones (XC1016141, XC1016139,
  Vasyliuk's 60–93 s WAVs) can carry a held moment. Vasyliuk's WAVs are clean format-wise but very low-level and need
  gain (raising their noise floor).
- On screen, a recording must be named by its own place and date (e.g. "Thrush nightingale, Marhanets, 16 April 2025,
  Ekaterina Kormina, xeno-canto XC1016141, CC0"), never placed at the crossing; Vasyliuk's bed recordings are "the
  former reservoir bed at Mar'ianske, ~48 km downstream".
- The "before" recordings (Kormina's 55 iNat sounds June 2022 – May 2023, XC1016139/1016140/1016142, the fire-bellied
  toad of 15 April 2023) are from the reservoir's shore while it still held water (though drawn down); they could voice
  "before" only with that said.

### Gaps
- No recording was listened to; every "usable" judgement needs a listening pass for distant explosions, artillery,
  drones, engines and voices.
- No frog chorus from the bed or near the crossing exists in these archives; if one is wanted, it would have to be asked
  of Kormina or Vasyliuk directly (both active recordists in the area) or recorded.
