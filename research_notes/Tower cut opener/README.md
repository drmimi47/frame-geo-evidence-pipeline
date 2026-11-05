# Tower cut opener (prototype)

`tower_cut.mp4`: 24.0 s (24.03 s), 1920×1080, 30 fps, H.264, **silent** (no audio stream). It fades in from black over
2 s, then makes 25 hard cuts through other people's footage of the power lines round the former Kakhovka reservoir:
Kamianka-Dniprovska, Velyka Znamianka, Nikopol, Enerhodar, the Great Meadow's edge, and the Zaporizhzhia plant's
330 and 750 kV lines. It ends on the Dnipro crossing over full water: a 750 kV crossing tower on its caisson, filmed
from the shore with the thermal plant's chimneys behind it, then the user's photograph of both crossings side by side.
In every frame the pole or tower stands at the same place on screen. Only the world around it changes: September 2021
dashcam, May 2024 in the Nikopol district, grey 2026, autumn woods under a 330 kV tower, rapeseed in flower under the
plant's 330 kV towers, the plant's cooling pond behind the 750 kV towers, and the full reservoir under the crossing
towers.

The order runs from small to large:

| Class (estimated by eye) | Frames | Source videos |
|---|---|---|
| Distribution, 0.4–10 kV | 13 | Road dashcam ×2, Thickets (Nikopol), Суспільне Дніпро, Новинарня |
| 35 kV | 1 | Road |
| 35–110 kV lattice | 2 | Road |
| 330 kV | 5 | Mihail Kalahnikov (Enerhodar, walking under the line) ×4; Валерий Петренко (the plant's 330 kV towers whole) |
| 750 kV | 2 | Media Poglyad (Energoatom's footage of the ZNPP 750 kV lines) |
| The crossing (750 kV, then both) | 2 | Валерий Петренко, t8TkQAs8X3U at 172 s (found footage); `supplied/crossing_user_1.png` (supplied by the user, source unknown) |

The holds start at 3.4 s (the fade takes the first 2 s of it). They quicken to 0.3 s through the poles and slow again
through the 330 kV towers. The plant's 750 kV towers get 0.95 s and 1.2 s, the filmed crossing tower 2.4 s, and the
last photograph 4 s.

**The crossing towers: real footage found in round 3, and one supplied photograph.** The first two rounds found no
footage of the crossing towers close enough to hold (Nikopol views of the plant across the bed, FavZds0hYzo at 25 s
and Kcg9_e-g-W0 at 783 s, show no tower at that resolution). The API search of round 3 found **t8TkQAs8X3U**, "ОГО! 330
и 750 кВ" by Валерий Петренко (311 subscribers; published 29 June 2023; standard licence; gate: in, Ukraine relevance
0.88 from "Каховское водохранилище" in its tags and description). Its description reads "ОРУ 330 и ОРУ 750 ЗАЭС. Также
переходы через Каховское водохранилище ВЛ 330 кВ и 750 кВ": the plant's 330 and 750 kV switchyards, and the 330 and
750 kV crossings of the Kakhovka reservoir. At 170–180 s it pans along the crossing from the shore: towers on caissons
in open water, the thermal plant's chimneys on the far shore behind them, and the plant's cooling towers coming into
view at the end of the pan. The reservoir is full, so it was filmed before 6 June 2023; the date it was filmed is not
given. Its end card reads "г. Одесса, июнь 2023" and thanks Bobkov Yu. B. for help gathering the material, so the
footage may be his. **t8T_172** is the frame used: by eye a 750 kV crossing tower (one long crossarm at the top
carrying three phases, an earth-wire peak, a short second arm), its base marked where the legs meet the caisson, as
for the photograph, and upscaled 1.36×. As asked, it takes `crossing_user_2`'s place before `crossing_user_1`;
`crossing_user_2` is left out but kept, for the user to decide. A 330 kV crossing tower on its caisson is in the same
pan (180 s), but too small in the frame (it would need 2.3×).

On 5 November 2026 the user supplied two photographs, saved in `supplied/`:
- `crossing_user_2.png` (998×824, sha256 8b98bb0f…). A tall crossing tower on a square caisson, others receding over
  water to a forested shore. By eye it is of the **750 kV** crossing's type: one long crossarm carrying three phases,
  with a short earth-wire peak above it. The 750 kV crossing towers are 126 m with the crossbar at 113 m (SkyscraperPage
  no. 23, `scene3d/towers.py`). Its caisson is square, though, while the Kakhovka crossing's are round ribbed drums
  (Esri WorldView-2, 2024). So whether this photo shows this crossing is **unconfirmed**.
- `crossing_user_1.png` (1520×1134, sha256 8f7cacc4…). The tower in front stands on a round caisson. By eye it is the
  **330 kV** crossing's type: three crossarm levels with a phase at each end (six phases, a double circuit). That fits
  the 100 m towers with crossbars at 92, 81 and 70 m (SkyscraperPage no. 19) and Ferosplavna's two circuits. The line
  receding left is the same type. The two towers on the right, each with one crossarm and three phases, are of the
  750 kV crossing's type: both crossings side by side, as at the Kakhovka reservoir. It is still the ending.

Both photographs show the reservoir full, so they were taken before 6 June 2023. Their source and date are unknown. The
user had earlier linked Wikimapia's page of the crossing (https://wikimapia.org/18910322/Dnipro-river-crossing-powerline-750kV),
and they may come from there; that is unconfirmed. **Their rights are unknown and must be cleared.** They are not
YouTube videos, so the scope gate doesn't apply to them. They are used as given: cropped by nothing, moved by one
similarity transform each, and upscaled 1.38× (user_2, now left out) and 1.31× (user_1).

Files:
- `tower_cut.mp4`: the opener.
- `tower_cut_contact.jpg`: every frame as placed, in order, with its key, class and hold.
- `tower_cut_contact_before.jpg`: the same for the cut before round 3 (26 frames, 23.5 s), to compare.
  `tower_cut_contact_round1.jpg`: the first version (30 frames, before the photographs and the raised heights).
- `tower_cut.json`: per frame:
  - video id, URL with timestamp, channel, publication date, licence, title and scope gate (for the two photographs:
    the file, its sha256 and its provenance, with rights unknown)
  - class estimate and how it was made
  - marks, transform (matrix, scale, rotation, target height), crop and hold
  - why it was chosen
  - sha256 of the source frame's pixels
  - capture date (null) with a note, and a capture hint where one exists
- `marks.json`:
  - the marks, layout, crops, classes and holds
  - the left-out candidates and why
  - the marks are made by eye from grid images and are for alignment only. They are not evidence and locate nothing.
- `candidates.jpg`: every candidate grouped by class, with the left-out ones struck through.
- `supplied/`: the user's two photographs of the crossing, as given (rights unknown).
- `gate.json` … `gate5.json`: the scope gate's verdict and metadata for every video checked (`gate5.json`: round 3).
- `search/`: the round-1 searches (`*.query`, and `*.jsonl` results as yt-dlp gave them).
- `discovery2.yaml`, `discover2.log`: round 3's API discovery (the config, and its output with the API key redacted
  from the request URLs); its candidates are in `library/runs/20261105T084443Z.json`.
- `meta/`: each video's yt-dlp metadata.
- `scan/`: the SigLIP prefilter scores. These are search aids, not evidence.
- `downloads/<id>/`: the downloaded videos, video stream only, one new folder each. They take about 19 GB and are
  gitignored along with `library/`.
- `frames/`: the full-resolution source frames used.
- `library/`: the scratch library from the first, abandoned ingest attempt. It holds only two videos (YODjwXFjnyg,
  3coe3Z-2TLg), both in scope.
- `discovery.yaml`: that attempt's config.

## Rules followed

- **Scope gate.** Every video passed `scope.check_scope()` against Ukraine 2022–2026 before anything was downloaded.
  This is the same call `ingest` makes, run on yt-dlp metadata. Rounds 1–2: 75 videos were gated, 69 in and 6 out.
  Five were out because they were published before 2022 (2013, 2016, 2019, 2020 and 2021), and one because its
  metadata was unavailable. Many more were pre-2022 in the search listings and never gated: the Novoklimov CC BY
  crossing videos (2011–2020) and Ukrenergo's crossing video yd6nkeCuomc (2015). Round 3: 41 gated, 29 in and 12 out
  (11 with no Ukraine signal at all, among them most of the generic 330 kV videos, which are Russian or Belarusian,
  and both CC finds; one, iLEi740tx4s, at relevance 0.40). The API's own discovery gate (dates, licence listing) ran
  first; nothing it found was written to `library/` beyond the run file in the scratch library.
- **No ingest.** Nothing went into `library/` or `libraries/`; everything is in this folder.
- **Untrusted downloads.** Each download is in its own new, empty folder, the scripts live in `scripts/`, and every
  Python run that reads a download uses `-I`.
- **Pixels.** Pixels are only cropped and moved by one similarity transform per frame (shift, uniform scale,
  rotation). Shrinking uses area averaging and everything else is bicubic. Nothing is generated, filled, inpainted or
  sharpened, and the canvas is black where the frame doesn't reach.
- **No text and no marks.** Hard cuts, with one fade from black at the start.
- **Crops.** These overlays are cropped off:
  - the dashcam's GARMIN date line and the car's bonnet (Road)
  - Суспільне's logo and oblast label
  - Новинарня's logo
  - the news banner and plant/oblast labels on the 750 kV frames, which also cuts those towers' bases at the
    banner's top edge (`base_cut`)
- **Nothing damaged, no crews.** No damage, smoke, military, faces or interiors as subjects. People appear only as
  specks in the distance; a passer-by was cropped off one frame. Repair crews at a pole (a4m6eQmiFv0 at 2586 s) were
  left out because crews' positions are never shown. Nothing is drawn, named or pinned, so no tower is located.
- **Dates.** Publication date is not capture date: `capture_date` is null throughout. Hints are given where they
  exist. The Road dashcams' own date line reads 12/09/2021, so those clips are likely pre-war. The filmed crossing
  shows the reservoir full, so it predates 6 June 2023, though it was published after.

## Alignment

The cut uses a **fixed base line, with the height growing by class**:
- Every tower's base sits on y = 990, on the centre line x = 960. Where a base can't be seen, the mark is the point
  where the tower's axis leaves the frame or the crop.
- Its top sits straight above the base, at a height set by its class: distribution 680 px, 35 kV and 35–110 kV 720,
  330 kV 840, 750 kV 900, the crossing towers 960 (from y = 30 to the base line).

I chose this over one fixed top height. The poles in dashcam frames are 200–700 px tall, and raising them to a 750 kV
tower's height would upscale them three to four times and lose the sense of scale the order is about. The first draft
grew the height smoothly over the whole sequence instead of by class, which upscaled the last small poles 3.4×. This
draft steps up only at each class.

The heights were then raised from 560/610/690/820/900 to the ones above, because at the lower heights the frames read as
small windows in black. Tall poles had to shrink to 0.55–0.65× to fit; they now shrink only to 0.67–0.79×, and every
frame fills more of the canvas. The cost is upscaling the poles that are small in their frames. Six of them
(7C1 432, 30, 447, 693, 691, XZz 321) would have needed 2.4–3.1×, so they were left out. The largest upscale left is
2.23× (XZz_264), with 2.17× and 2.10× on the two 35–110 kV lattice towers. The filmed crossing tower is upscaled
1.36×, the plant's 330 kV towers (t8T_118) 1.05×, and the photograph 1.31×. The before and after contact strips were
compared.

**Iterations:**
1. The first draft grew the height smoothly over the order. Changed to steps by class.
2. A passer-by cropped off one frame.
3. Spring Nikopol frames (Thickets) and a Nikopol pole with the plant behind it (Новинарня) added, for more change of
   season and place.
4. Holds lengthened to reach 22 s.
5. The user's two crossing photographs added as the ending; the plant's 750 kV towers shortened to 0.95 s and 1.2 s;
   the class heights raised and six over-small poles dropped, as above (23.5 s, 26 frames).
6. Round 3 (API search): the drained-bed frames UYf_233 and UYf_235 dropped (razor wire, below); the plant's 330 kV
   towers seen whole (t8T_118) added after the close views; the filmed crossing tower (t8T_172) in place of
   `crossing_user_2`; holds retuned (24.0 s, 25 frames).

t8T_118 is a 4:3 frame with its tower left of centre, so the canvas is black on its left (about 280 px); t8T_172
leaves a thin black strip (about 20 px) on the left. Both are by the rule (black where the frame doesn't reach).

On the contact strip the bases and tops stay put within each class. Steeply tilted towers seen from below
(3co_299, 3co_216) are rotated upright, which leaves black wedges at the corners.

## Searches and quota

### Round 3 (5 November 2026): YouTube Data API

**20 searches, about 2,000 quota units** (100 each), through the project's own discovery (`.venv/bin/evidence
discover -c discovery2.yaml`, a dry run into the scratch library), at 50 results each, any licence, relevance language
Ukrainian. 17 text searches and 3 geotag searches over the study area round Enerhodar, Kamianka-Dniprovska, Vodiane,
Nikopol and Marhanets (10 km radius: ЛЕП, дрон, рибалка). Results per search:

| Search | Results |
|---|---|
| переход ЛЕП через Днепр | 43 |
| опори ЛЕП в Каховському водосховищі | 1 |
| ЛЕП 750 Енергодар | 8 |
| рыбалка Каменка-Днепровская опоры ЛЕП | 1 |
| Нікополь дрон опори ЛЕП | 0 |
| дно Каховського водосховища ЛЕП | 0 |
| Kakhovka reservoir power line towers drone | 4 |
| опоры ЛЭП в Каховском водохранилище рыбалка | 0 |
| Водяне Каховське водосховище дрон | 1 |
| Марганець опори ЛЕП | 2 |
| Энергодар ЛЭП 750 кВ | 14 |
| высоковольтная линия зима Запорожская область | 1 |
| лінія 330 кВ опора | 50 |
| ЛЭП 110 кВ опора поле Запорожье | 0 |
| Каменка-Днепровская водохранилище лодка | 9 |
| Нікополь Великий Луг дрон | 17 |
| переходные опоры ЛЭП Днепр Никополь | 0 |
| geotag: ЛЕП | 1 |
| geotag: дрон | 50 |
| geotag: рибалка | 21 |

214 candidates; 108 not already checked. Most were FPV-drone and shelling news, which were skipped by title. 41 were
gated (above) and the 29 in were downloaded and scanned:
- Enerhodar drone archives by ANDRUHA_SMILE PRODUCTION (11 videos, 2020–2022 footage published 2022–2023, among them
  winter, a January sunset and a CC BY one, 1TZSWeY0BXw): the town, the canal, the reservoir and the thermal plant's
  chimneys, but no tower close enough to hold. Veisj23cCNk (the reservoir at Enerhodar from a drone, 5.5 min) shows
  the water and shore, not the crossing.
- Fishing and boats (Kamianka-Dniprovska ice fishing, February 2022; autumn and summer fishing; a sailing trip):
  no towers in view.
- The drained bed (Nikopol shore in June 2023 and July 2025, the bed overgrown in 2023–2024, a paraglider, news
  items): wooden posts and a fence at most, no power line to hold. No replacement for the UYf poles was found.
- **t8TkQAs8X3U** (Валерий Петренко): the find. The plant's 330 and 750 kV switchyards, the lines leaving them, and
  the crossings from the shore. Two frames used (t8T_118, t8T_172).
- j7oyKBkYAM0 (ДТЕК Київські регіональні електромережі): a crew replacing towers in the Kyiv region; a worker in
  frame, and far from the reservoir. Not used.

**Creative Commons:** three CC BY finds: 1TZSWeY0BXw (in scope, Enerhodar from a drone, no usable tower),
0Wcql4hifiM and IYn4RL1gBB0 (330 kV hum recordings, both out of scope: no Ukraine signal). No CC frame is in the cut.

### Rounds 1–2

The task's budget was about 12 searches through the YouTube Data API at about 100 units each. In practice **no API
quota was used**: `.env` holds no `YOUTUBE_API_KEY`, only a comment and the Earthdata token. Searches were run through
yt-dlp (`ytsearch30:`, and the results page sorted newest first) at no quota cost, and I ran more of them than the
budget allowed. 24 searches returned results and one (q14) returned none; one more failed on an apostrophe and was
dropped. The terms were in Ukrainian, Russian and English (`search/*.query`):
- ЛЕП Енергодар / Нікополь / Марганець
- опори ЛЕП Каховське водосховище
- дно Каховського водосховища дрон
- перехід ЛЕП через Дніпро
- лінія 750 кВ Запорізька
- опора ЛЕП 330 кВ
- Великий Луг дрон
- переходні опори ЛЕП дно…
- опоры ЛЭП дно Каховского водохранилища
- Энергодар опоры ЛЭП
- power lines Kakhovka reservoir drone
- newest-first runs of the place names

From the 69 videos that passed the gate, those that looked useful were downloaded (68 succeeded; gifdlRybvbg failed
with HTTP 403). Each was scanned with SigLIP zero-shot (tower/pole against people/graphic/damage) as a prefilter, and
every candidate was then looked at by eye. The GPU was busy with a Blender render, so the scan ran on the CPU with
`google/siglip-base-patch16-224`. The main library's stored embeddings were scored read-only, which found
ZUXsmHCUVg4.

Martial law matters here. Footage of energy infrastructure published in 2022–2026 is scarce, likely because filming
and publishing it is restricted, and most of the usable footage is a pre-war dashcam drive published in 2023.

## How to re-run

From the repository root:

```sh
B="research_notes/Tower cut opener"
.venv/bin/python -I "$B/scripts/gate_download.py" "$B/meta" "$B/downloads" "$B/gate5.json" <video ids>   # gate, then download
cd "$B/scripts"
SCAN_MODEL=google/siglip-base-patch16-224 SCAN_CPU=4 ../../../.venv/bin/python -I scan.py ../downloads <scratch> ../scan
../../../.venv/bin/python -I review_sheet.py ../scan <scratch> <out-prefix> [per_video] [min_score] [ids]
../../../.venv/bin/python -I tiles.py ../downloads <id> <step> <out-prefix> [start end]
../../../.venv/bin/python -I mark_tool.py extract|grid|check ...      # mark top and base by eye
../../../.venv/bin/python -I render.py .. [--fps 30] [--only-contact]  # tower_cut.mp4, contact strip, tower_cut.json
../../../.venv/bin/python -I candidates_sheet.py ..                    # candidates.jpg
```

To change the cut, edit `marks.json`: the order of `frames`, `hold_s`, `crop` and `layout.heights`. Then run
`render.py` again. Frames with `left_out` are skipped.

## Left out, and why

These are listed in `marks.json` (`left_out`) and struck through in `candidates.jpg`:
- **Base or top hidden.** Lattice towers whose foot is behind trees or whose top is out of frame: XZz 735, 774, 782
  and 790. Also a concrete pole in bushes with a car in front (XZz 764).
- **Duplicates and small poles.** Near-duplicates and small, distant poles, including the six dropped when the heights
  were raised (they would have needed more than about 2.2× upscaling).
- **Damage and people.**
  - a street with shell-damaged roofs (a4m6 2472)
  - people walking (a4m6 762)
  - a repair crew in a bucket truck (a4m6 2586)
  - interviews throughout
- **News stills.** The 750 kV switchyard under the news title (td0 15.5 s).
- **Whole videos.**
  - YODjwXFjnyg: Google Street View captures, third-party imagery and not the uploader's own views.
  - 6t-iCW6WLVs: shrapnel damage throughout.
  - 34nya5SYO7Q (Pavlik.tv): a Russian channel, possibly filmed on the occupied side.
  - 9-EN9bhRYwE: a felled tower.
  - Kcg9_e-g-W0 after 787 s: FPV-drone strike footage.
  - News and talk videos without towers.

## Open questions

- **Rights.**
  - The 24 video frames all come from **standard-licence** videos, so none of them is CC (round 3's CC finds are
    above: none usable). Only two CC BY videos passed the
    gate (09-egWW-a9w from Суспільне Запоріжжя, and xYW0h3uW3vE), and neither shows a tower.
  - Using these clips needs the uploaders' permission: Road, Thickets, Mihail Kalahnikov, Новинарня, Суспільне Дніпро,
    Media Poglyad and Валерий Петренко (whose end card credits help from Bobkov Yu. B., so the footage may be his).
  - The 750 kV footage is Energoatom's inside Media Poglyad's news item, so it needs **Energoatom's** permission too.
  - Short, transformed quotation may fall under fair use or "quotation" exceptions, but that is for the user and a
    lawyer to decide, not this prototype.
  - The crossing photograph's source, author and rights are **unknown** (and the left-out `crossing_user_2`'s): find
    the author (Wikimapia's page of the crossing is the lead) and clear them before any use.
- **Channels.**
  - Mihail Kalahnikov filmed in Enerhodar in autumn 2022, under occupation.
  - Валерий Петренко's video is Russian-language and published in June 2023 with the end card "г. Одесса"; the
    footage of the plant's switchyards (filmed from the fence) predates the breach and may be pre-war.
  - These are private people, not occupation authorities or state media, but the user may want to check.
- **The UYf frames (the user's question).** UYf_233 and UYf_235 (UYfx16Vju1g, Ярик Важничий, the drained bed on
  9 June 2023) were looked at at full resolution. What hangs over the bed is a coil of concertina (razor) wire strung
  between two posts, with dark balls and hooks hung on wires below it: a barrier or obstacle, fortification-like, not a
  power line. The small distribution poles stand in front of it. Both frames are left out (`marks.json`), and no
  other view of poles on the drained bed was found to replace them.
- **Missing classes.**
  - No close, clear 110–150 kV tower whose base can be seen.
  - The 330 kV towers are now seen whole (t8T_118), but close; none from far off. No 750 kV tower seen whole
    from a distance either, other than the crossing.
  - The crossing is filmed (t8T_172) and photographed, both with full water. Footage of the towers standing in the
    drained bed after June 2023 (a Nikopol or Marhanets drone hobbyist) would bring the ending into the war years;
    none was found.
  - Season and year: still mostly summer. Winter footage was found (Enerhodar, Kamianka-Dniprovska ice fishing) but
    with no tower in it.
- **Look.**
  - Tall poles still shrink (Kcg_038, a4m_714, a4m_1326 to 0.67–0.76×), so their frames leave black around them, and
    the window's size and shape changes with each cut. That is the rule (black where the frame doesn't reach).
  - The 750 kV frames come from news footage, softer than the rest.
- **Sound.** Left silent as asked. One option is the Hum entering on the crossing.
- **Downloads.** About 19 GB in `downloads/` (98 folders), kept to re-render. Delete them once the frames are settled
  (`frames/` keeps the source frames used).
