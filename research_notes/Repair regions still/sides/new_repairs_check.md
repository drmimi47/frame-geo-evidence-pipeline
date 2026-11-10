# Three repairs from the plant's channel, checked (8 November 2026)

The three repairs `who_repaired.md` lists as reported by the Russian-installed plant administration's Telegram channel
(@znppofficial) and missing from `../repairs.yaml` ("Open questions"), checked against the IAEA, Ukrainian and Western
sources. No project file was changed apart from this note.

**How it was read.** Only WebFetch and WebSearch were used. Some sites refused, and none of those refusals was worked
around: globalsecurity.org (403 on every IAEA mirror page this time), reliefweb.int (403), iaea.org (402), x.com (402),
suspilne.media, gazeta.ua, mezha.net, energoatom.com.ua and komersant.ua (403). The IAEA's own words below therefore come
from outlets quoting them: Energy Jobline's reprint of Update 347, UNN's and NucNet's quotes of Update 371, Reuters, The
Moscow Times and TASS for the 8 November X post, and the OECD-NEA chronology (read). Update 372 is quoted from search
snippets of iaea.org's own page; its page was not read (marked "(snippet)").

The channel was read at `t.me/s/znppofficial`. Its pages show times in UTC with no dates. Dates are taken from the
sources that match the posts: post 1728 is the outage the IAEA puts on 14 April, and post 1880, the post before 1881,
is the 4 November holiday.

---

## 1. 14 April 2026: Ferosplavna-1 "restored with the grid organisation"

**Verdict: not a line repair.** It was a trip of about 90 minutes, which the IAEA confirms. The IAEA puts the cause in
the link between the thermal plant's 330 kV switchyard and the plant's autotransformer. No source describes a repair,
not even the channel: it says the supply scheme was "restored", not repaired. This is the start of the event the dataset
already has as **R42** in `not_counted` ("14-26 April 2026: repeated trips on the link ... no repair described"). It
should not be counted. Add its sources to R42 rather than giving it a new entry. If an id is wanted, R47 goes in
`not_counted`.

- **Was the line cut, when and why?** Yes, in the early hours of Tuesday 14 April, for about 90 minutes.
  - IAEA Update 347 (17 April): "the same Ferosplavna-1 backup power line was disconnected for approximately 90 minutes".
    The plant told the IAEA that "the disconnection was caused by a problem with the interconnection power line" sending
    power "between the 330 kV open switchyard at the Zaporizhzhya Thermal Power Plant" and the autotransformer. The IAEA
    "is awaiting the results from the ZNPP's investigation into both events" (the second being 16 April).
  - OECD-NEA, entry of 14 April: "lost all off-site power for the 13th time during the conflict".
  - Plant channel, post 1728: the line tripped «В результате действия автоматической защиты» ("as a result of automatic
    protection acting"). The word «ремонт» ("repair") appears in neither post.
  - Post 1729: «совместно с представителями сетевой организации» ... «успешно восстановлена схема электроснабжения»
    ("together with representatives of the grid organisation ... the supply scheme was successfully restored"). Which
    grid organisation is not said. "Scheme restored" is switching the line back in, not mending it.
  - Energoatom, via Glavred: «В результаті некомпетентних дій загарбників на тимчасово окупованій території ЗАЕС
    опинилася в режимі блекауту» ("through the incompetent actions of the invaders on the temporarily occupied
    territory, the ZNPP was blacked out"); «Через півтори години зовнішнє електропостачання ЗАЕС було відновлено» ("after
    an hour and a half, the ZNPP's external power was restored"). It names no repair and no crew.
- **Where was the fault?** The link between the two switchyards, on the occupied side. The IAEA says so, the plant
  reported it to the IAEA, and Energoatom's "on the temporarily occupied territory" agrees. Had it been counted, it
  would go in `switchyards`.
- **Who?** No one repaired anything. The switching was done by the plant's staff with "the grid organisation" (the
  channel), with no affiliation given.

```yaml
# not_counted: replace R42's entry with this (the same event, two more sources and the channel's wording)
  - {id: R42, why: "14-26 April 2026: repeated trips on the link between the thermal plant's switchyard and the plant's autotransformer, the first on 14 April (about 90 minutes, 'caused by a problem with the interconnection power line', IAEA Update 347); the plant's channel says only that the supply scheme was 'restored' with the grid organisation's representatives after an automatic-protection trip, and Energoatom blames the occupiers; no repair described by anyone", side: unknown, arranged_by: null, side_basis: null, sources: ["GS 2026/04/ukraine-260417-iaea01.htm (IAEA Update 347; read via https://news.energyjobline.com/?p=48318, the GS mirror refused)", "https://t.me/znppofficial/1728", "https://t.me/znppofficial/1729", "https://glavred.net/energy/amp-ugroza-dlya-vsey-evropy-zaes-poltora-chasa-byla-v-blekaute-10756565.html (Energoatom via Glavred, 14 Apr 2026)", "https://oecd-nea.org/jcms/pl_66130/ukraine-current-status-of-nuclear-power-installations (OECD-NEA, entry of 14 Apr 2026)"]}
```

---

## 2. 15-23 October 2026: Rosatom's repair at the thermal plant under a ceasefire

**Verdict: confirmed by the IAEA. It was the IAEA's eighth local ceasefire.** What was repaired is switchyard equipment,
not a line: a backup transformer at the thermal plant's 330 kV switchyard (the IAEA's "330 kV distribution
substation"), which links Ferosplavna-1 to the plant. It is counted, like R41 and R45b (switchyard equipment and links,
`switchyards`). Ferosplavna-1 itself was not cut. There was no complete loss between 7 September and 8 November: the
IAEA's count went from 26 to 27 only on 8 November.

- **The damage:** IAEA, via Ukrinform (3 October): drone strikes on 19, 20 and 27 September damaged transformers at the
  Zaporizhzhya Thermal Power Plant, "of vital importance for supplying off-site power to the ZNPP". Grossi was
  "negotiating a new localized ceasefire with both sides". The channel, post 1859: «повреждено оборудование Запорожской
  ТЭС» ("equipment at the Zaporizhzhia TPP damaged") in the last ten days of September.
- **The ceasefire:** It began on the morning of Thursday 15 October. Update 371, via UNN (16 October): "A new local
  ceasefire came into effect this morning", "the eighth temporary ceasefire brokered by the IAEA", "will allow repairs
  to be carried out on equipment at a 330-kilovolt (kV) distribution substation". NucNet (16 October): "a backup
  transformer" "damaged by military activity near the Zaporizhzhya thermal power plant", repaired to strengthen the
  connection to the "Ferosplavna-1 330 kV offsite power line". One search summary dates the start to 16 October; UNN
  and the channel both say 15 October, a Thursday.
- **Completion:** Update 372 (23 October) (snippet): repair work on electrical equipment near the ZNPP was
  "successfully completed" under the eighth localized ceasefire, despite continued military activity. "Activities were
  briefly interrupted on 20 October while the team and site personnel took shelter as a precaution." The channel, post
  1866: «Ремонт оборудования Запорожской ТЭС успешно завершён» ("the repair of the Zaporizhzhia TPP's equipment
  successfully completed"); «Для безопасного проведения ремонта 15 октября был введён режим тишины» ("for the repair
  to be done safely a ceasefire was brought in on 15 October").
- **Who did the work?** The Russian side.
  - Likhachev (Rosatom), forwarded in post 1862: «Наши специалисты сейчас выходят и начинают ремонт технологического
    оборудования» ("our specialists are going out now and starting the repair of the equipment").
  - The IAEA's "site personnel" (Update 372, snippet) are the plant's staff, under Rosatom since October 2022.
  - No Ukrainian source claims the work. The Ukrainian outlets found (Ukrinform, Glavcom, 24tv, 1news.zp.ua) report
    only the IAEA's statements.
- **Who arranged it?** The IAEA brokered the ceasefire (IAEA, Ukrinform, NucNet). The channel, post 1866, says
  «организованный совместными усилиями Госкорпорации «Росатом», МИД России и Минобороны России при содействии МАГАТЭ»
  ("organised jointly by Rosatom, Russia's MFA and Defence Ministry, with the IAEA's help"). This matches the earlier
  truces, where Russian sources name themselves as co-organisers.

```yaml
# repairs: placed (switchyards), after R45b
  - id: R48
    line: "the thermal plant's 330 kV switchyard (a backup transformer linking Ferosplavna-1 to the plant)"
    region: switchyards
    when: 2026-10-23
    what: "Transformers at the thermal plant damaged by drone strikes on 19, 20 and 27 September 2026 (the line stayed in service); a backup transformer repaired under the IAEA's eighth local ceasefire, from the morning of 15 October, briefly interrupted on 20 October, completed 23 October"
    who: "'site personnel' (IAEA Update 372, snippet); «Наши специалисты» ('our specialists', Likhachev, Rosatom)"
    place: "'equipment at a 330-kilovolt (kV) distribution substation' (IAEA Update 371, via UNN); 'a backup transformer ... damaged by military activity near the Zaporizhzhya thermal power plant' (NucNet); «электротехническом оборудовании Запорожской ТЭС» ('electrical equipment at the Zaporizhzhia TPP', the plant's channel)"
    granularity: facility
    side: russian
    arranged_by: "IAEA's 8th local ceasefire, 15-23 Oct 2026 (Russian sources add Rosatom, Russia's MFA and Defence Ministry)"
    side_basis: stated
    note: "Switchyard equipment, not a line: counted as R41 and R45b are. Who did the work is stated by Russian sources only (Likhachev: «Наши специалисты сейчас выходят и начинают ремонт технологического оборудования»); the IAEA's 'site personnel' agrees; no Ukrainian claim found. Not in the unrolled film's truces (config unchanged)."
    sources:
      - "https://www.ukrinform.net/rubric-economy/4170677-iaea-reports-damage-to-transformers-near-zaporizhzhia-npp-seeks-truce-for-repairs.html (Ukrinform, the IAEA's statement, 3 Oct 2026)"
      - "https://unn.ua/en/news/a-local-ceasefire-has-taken-effect-near-the-zaporizhzhia-nuclear-power-plant-iaea (UNN, IAEA Update 371, 16 Oct 2026)"
      - "https://www.nucnet.org/news/eighth-localised-ceasefire-begins-as-iaea-renews-warnings-on-zaporizhzhya-10-5-2026 (NucNet, 16 Oct 2026)"
      - "https://www.iaea.org/newscenter/pressreleases/update-372-iaea-director-general-statement-on-situation-in-ukraine (IAEA Update 372, 23 Oct 2026; snippet: iaea.org refused, 402)"
      - "https://t.me/znppofficial/1862 (Likhachev, forwarded)"
      - "https://t.me/znppofficial/1866"
```

---

## 3. 8 November 2026 (today): Ferosplavna-1 back "after repair work"

**Verdict: only the plant's channel says a repair was done.** The outage and the reconnection are confirmed by the IAEA
(the loss), Reuters, Energoatom and Ukrinform (the reconnection at 17:41). None of them describes a repair, gives the
place of the fault or names a crew. The IAEA says "the cause and location of the latest disconnection are not yet
known". Keep it out of the count for now, as `not_counted` R49 (like R18 and R43), and look again after the IAEA's next
update, which usually gives the cause and place.

- **The loss:** 02:36 Kyiv time (Energoatom).
  - Energoatom (Telegram 28737): «8 листопада о 02:36 Запорізька атомна електростанція втратила живлення» ("on 8
    November at 02:36 the ZNPP lost power"); «Спроба автоматичного повторного ввімкнення лінії виявилася неуспішною»
    ("the attempt to reclose the line automatically failed"). A failed reclose points to a lasting fault, not a
    transient one; that reading is mine.
  - IAEA (X post, quoted by Reuters, The Moscow Times and TASS): it lost "its only remaining external power line,
    Ferosplavna-1, early on Sunday morning"; "It is the 27th such event during the conflict"; "The cause and location of
    the latest disconnection are not yet known."
  - Plant channel, post 1881: the line «отключена действием защиты вследствие повреждения» ("tripped by its protection
    because of damage").
- **The reconnection:** 17:41 Kyiv time.
  - Energoatom (Telegram 28742): «О 17:41 увімкнено лінію електропередачі 330 кВ «Феросплавна-1»» ("at 17:41 the 330 kV
    Ferosplavna-1 line was switched on"). The wording is passive, with no repair and no crew.
  - Ukrinform's and DSnews's headlines and leads: "Ukrainian energy workers have restored operation of the Ferosplavna-1
    power line" / «Українські енергетики відновили зовнішнє живлення» ("Ukrainian energy workers restored external
    power"), attributed to Energoatom. That is a restoration of supply; no repair is described.
  - Plant channel, post 1882: «После проведения ремонтно-восстановительных работ введена в работу линия электропередачи
    330 кВ «Ферросплавная-1»» ("after repair and restoration work, the 330 kV Ferosplavna-1 line was put into service").
    No crew and no place.
- **Where?** No source says. If a later source places the damage, use the coarsest region it supports.
- **Who?** Unknown. The channel claims repair work but not who did it. The Ukrainian side claims the restoration in
  headlines only.

```yaml
# not_counted (for now; promote to repairs if the IAEA's next update describes a repair and its place)
  - {id: R49, why: "8 November 2026: Ferosplavna-1 lost at 02:36 (the 27th complete loss by the IAEA's count; 'The cause and location of the latest disconnection are not yet known', IAEA), automatic reclose failed (Energoatom), switched on at 17:41; only the plant's channel says «После проведения ремонтно-восстановительных работ» ('after repair and restoration work'), naming no crew or place; Energoatom and Ukrinform report the reconnection ('Ukrainian energy workers have restored operation of the line', Ukrinform) without describing a repair", side: unknown, arranged_by: null, side_basis: null, sources: ["https://t.me/znppofficial/1881", "https://t.me/znppofficial/1882", "https://t.me/energoatom_ua/28737", "https://t.me/energoatom_ua/28742", "https://www.ukrinform.net/rubric-economy/4182723-ukrainian-energy-workers-restore-external-power-supply-to-znpp.html (Ukrinform, 8 Nov 2026)", "https://theprint.in/world/power-restored-to-zaporizhzhia-nuclear-plant-iaea-says/3093800/ (Reuters, 8 Nov 2026)", "https://www.themoscowtimes.com/2026/11/08/zaporizhzhia-nuclear-plant-relying-on-generators-again-after-losing-internal-power-supply-a94202 (The Moscow Times, the IAEA's X post, 8 Nov 2026)"]}
```

---

## The IAEA's count of local ceasefires

**Seven becomes eight.** The IAEA itself calls the ceasefire of 15-23 October 2026 "the eighth temporary ceasefire
brokered by the IAEA" (Update 371, via UNN), and its 3 October statement already called the one it was seeking the
eighth. Neither 14 April nor 8 November had a ceasefire.

The unrolled film's `truces` (config `networks.znpp.unrolled.truces`) count seven and leave out the IAEA's third (R39,
December 2025). The October 2026 ceasefire is not among them either. Whether to draw it is left to the user; the config
is unchanged.

## For `who_repaired.md` (not edited)

- The table gets R48 (russian, stated, the IAEA's 8th). The counts become 42 repairs, 7 of them Russian (4 stated: R35d,
  R39, R41, R48).
- The pattern holds: Russia names its own crews only for ceasefire work on the occupied side.
- Under open questions, R49 replaces the three items: settle where and who once the IAEA reports the cause.
- The caveat in `repairs.yaml` about the IAEA's numbering could add that its eighth (R48) is not among the unrolled
  film's truces.
