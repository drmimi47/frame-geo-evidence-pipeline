# Which side repaired each of the ZNPP's lines, 2022-2026

Researched 8 November 2026 for a map that links "the Ukrainian side" and/or "the Russian side" to each repair in
`../repairs.yaml` (41 counted, R01..R46). Inputs: `../repairs.yaml`, `../v5/regions_v5.json` (`repairs[].who`), and the
seven truces in `config/conductive-seam.yaml` (`networks.znpp.unrolled.truces`). No project file was changed.

**Sources.** The IAEA's updates (read in full through the globalsecurity.org mirror, `GS` below:
`https://www.globalsecurity.org/wmd/library/news/ukraine/` + the path; iaea.org refuses automated reads, and reliefweb
returned 403 this time). Ukrainian: Ukrenergo, Energoatom, the Ministry of Energy (kmu.gov.ua) and the outlets carrying
them (Ukrinform, Interfax-Ukraine, Espreso, Mind.ua, Kyiv Post, Babel, Fakty). Russian: the Russian-installed plant
administration's official Telegram channel **@znppofficial ("ЗАЭС. Официально")**, read through its whole public
history (October 2022 to 8 November 2026) and cited as `t.me/znppofficial/<post>`, plus RIA, Interfax.ru, Izvestia,
Vedomosti, OSN and www1.ru. Western: AP/Al Jazeera, Reuters, WNN, ANS, NEI. Blocked and not worked around:
pravda.com.ua, energoatom.com.ua, suspilne.media, reliefweb, tass.ru (empty pages). Energoatom's archive is the likeliest
place to fill the 2022-2023 gaps.

**Safety.** Places are given only as a side of the front, a bank, the crossing or the switchyards area. The sources'
distances, tower numbers and the Dniprovska substation's place are left out on purpose; where a placement rests on a
distance, the table says "a distance (not used)".

**Terms.**
- **side**: who did the work. *ukrainian* = Ukrenergo, Energoatom, or the plant's or thermal plant's Ukrainian staff;
  *russian* = the plant's staff under Rosatom (from October 2022), Rosatom or Atomenergoremont crews, Rosseti, Russian
  military deminers; *both* = both sides worked on one repair; *unknown* = no source says.
- **confidence**: *stated* = a source names who did it; *implied* = the organisation's own "we restored", or the IAEA's
  wording points to one side without naming it; *inferred* = my reading from the place alone.
- **arranged_by**: the IAEA's local ceasefires are numbered as the IAEA numbers them. The IAEA's first ceasefire set two
  zones (Dniprovska and Ferosplavna-1, October 2025); the unrolled film's truces 1 and 2 are those two zones. The IAEA's
  third (December 2025, R39) isn't among the unrolled film's seven truces, so from January 2026 the numbering below is
  the IAEA's: its 4th is the film's truce 4, and so on.

## Table

| id | date | line | side | arranged_by | which bank | confidence | key quote | source URL |
|---|---|---|---|---|---|---|---|---|
| R01 | 2022-03-18 | 750 kV ZNPP-Kakhovska (the dataset's unnamed line) | ukrainian (Ukrenergo crews) | none stated | not stated; the line runs south-west over the left bank, much of it occupied or contested by then (inferred, unverified) | stated | «Ремонтники НЕК «Укренерго» відновили високовольтну лінію 750 кВ Запорізька АЕС – Каховська» ("Ukrenergo's repair crews restored the 750 kV ZNPP-Kakhovska line"); IAEA: "Ukrainian engineers had repaired and reconnected one of three previously disconnected power lines" | https://www.kmu.gov.ua/news/19-bereznya-situaciya-v-energetici-stanom-na-1200 ; GS 2022/03/ukraine-220319-iaea01.htm |
| R02 | 2022-08-10 | a line from the thermal plant | unknown | none stated | the switchyards area, occupied (inferred from the line) | unknown | "Ukraine informed the IAEA about the restoration of a power line that can be used to supply the ZNPP with electricity from a nearby thermal power plant" | GS 2022/08/ukraine-220810-iaea01.htm |
| R03 | 2022-08-22 | the line to the thermal plant | unknown | none stated | the switchyards area, occupied (inferred) | unknown | "a disconnection of the power line linking this plant to the ZNPP lasting several hours before it was restored later the same day" | GS 2022/08/ukraine-220823-iaea01.htm |
| R04 | 2022-08-25 | Dniprovska and another main line | ukrainian (Ukrenergo) | none stated | not stated | stated | «НЕК "Укренерго" відновила роботу двох пошкоджених унаслідок обстрілів російських військових магістральних ліній» ("Ukrenergo restored two main lines damaged by Russian shelling") | https://interfax.com.ua/news/economic/854657.html |
| R05a | 2022-09-10/12 | a 330 kV reserve line; a 750/330 kV line | ukrainian (the plant's Ukrainian staff, then under occupation) | none stated | occupied side: through the thermal plant's switchyard (inferred) | implied | "plant operators and engineers have been able to restore one of the reserve power lines, in very challenging circumstances" (IAEA Update 100); the plant was "held by Russian forces but operated by Ukrainian staff" (Update 102) | GS 2022/09/ukraine-220911-iaea01.htm ; GS 2022/09/ukraine-220913-iaea01.htm |
| R05b | 2022-09-13 | the plant's 150 kV back-up line (the thermal plant's switchyard repaired) | ukrainian ("Ukrainian engineers", working under occupation) | none stated | the switchyards area, occupied (inferred from the place) | stated (who), inferred (side of the front) | "Ukrainian engineers have made further headway in repairing vital power infrastructure in the vicinity of the Zaporizhzhya Nuclear Power Plant" | GS 2022/09/ukraine-220913-iaea01.htm |
| R06 | 2022-09-16 | Dniprovska | ukrainian (engineers using Energoatom's spare parts) | none stated | not stated | implied | "engineers repaired one of the four main external power lines ... Energoatom said it had delivered spare parts for the repair of the ZNPP's power lines" | GS 2022/09/ukraine-220917-iaea01.htm |
| R07 | 2022-10-09 | Dniprovska | ukrainian (Ukrainian specialists; "the grid operator") | none stated | Ukrainian-held, north bank (stated) | stated | «Українські фахівці відремонтували та ввели в роботу високовольтну лінію зв'язку 750 кВ ЗАЕС - Дніпровська» ("Ukrainian specialists repaired and reconnected the line"), damaged «на підконтрольній Україні території» ("on Ukrainian-controlled territory"); IAEA: "it will be repaired by the grid operator" | https://espreso.tv/fakhivtsi-polagodili-visokovoltnu-liniyu-elektroperedachi-zaes-dniprovska-poshkodzhenu-rosiyanami ; GS 2022/10/ukraine-221009-iaea01.htm |
| R08 | 2022-10-12 | Dniprovska (its substation) | ukrainian (Ukrainian specialists, per Energoatom) | none stated | Ukrainian-held (inferred; place never shown) | stated (seen only in a search snippet of Energoatom) | «Українські фахівці знайшли технічне рішення, як відновити роботу лінії зв'язку» ("Ukrainian specialists found a technical solution to restore the line") | GS 2022/10/ukraine-221012-iaea01.htm (the Energoatom page, on thepage.ua, was blocked) |
| R09 | 2022-10-18 | Dniprovska (its substation) | ukrainian | none stated | Ukrainian-held (inferred; place never shown) | inferred | no repairer named; the plant's staff told the IAEA that power was back | https://www.radiosvoboda.org/a/news-grossi-elektropostachannia-zaes/32090725.html |
| R10 | 2022-10-14 | the links between the plant and the thermal plant's switchyard | ukrainian ("Ukrainian engineers", nine days after Rosatom claimed the plant) | none stated | the switchyards area, occupied (inferred) | implied | "Ukrainian engineers have managed to restore back-up power ... two of the ZNPP's back-up power lines - connecting it to the thermal power plant switchyards - have been repaired" | GS 2022/10/ukraine-221014-iaea01.htm |
| R11 | 2022-11-04 | Dniprovska | ukrainian | none stated | Ukrainian-held (stated) | inferred (who), stated (where) | "both sustaining physical damage ... in Ukrainian-controlled territory"; «фахівці відремонтували обидві зовнішні лінії» ("specialists repaired both external lines") | GS 2022/11/ukraine-221105-iaea01.htm ; https://espreso.tv/zaes-pidednali-do-energosistemi-ukraini |
| R11b | 2022-11-04 | the 330 kV back-up line | ukrainian | none stated | Ukrainian-held (stated) | inferred (who), stated (where) | as R11 | GS 2022/11/ukraine-221105-iaea01.htm |
| R12 | 2022-12-14 | the 330 kV line | unknown | none stated | not stated | unknown | "now restored" (no repairer) | https://oecd-nea.org/jcms/pl_66130/ukraine-current-status-of-nuclear-power-installations |
| R13 | 2023-01-06 | Ferosplavna-1 | ukrainian | none stated | north bank, Ukrainian-held (stated: "the other side of the Dnipro River") | inferred (who) | "damage on the other side of the Dnipro River ... work to repair the line is already under way" | GS 2022/12/ukraine-221230-iaea01.htm ; GS 2023/01/ukraine-230107-iaea01.htm |
| R15 | 2023-07-01 | Ferosplavna-1 | ukrainian (Ukrenergo) | none stated | north (right) bank, Ukrainian-held (stated) | implied | IAEA: "Ukraine saying military action is preventing its experts from safely accessing the location situated in territory it controls"; «Укренерго вкотре повернуло в роботу одну з ліній» ("Ukrenergo once again returned one of the lines to service") | GS 2023/04/ukraine-230413-iaea01.htm ; https://espreso.tv/zaporizku-aes-upershe-za-4-misyatsi-pidklyuchili-do-rezervnoi-lep-u-magate-prokomentuvali |
| R16 | 2023-03-09 | Dniprovska | ukrainian (Ukrenergo) | none stated | Ukrainian-held (inferred: the repair waited on Ukraine's military) | implied | «Щойно буде можливість і дозвіл військових, одразу розпочнеться відновлення» ("as soon as there is an opportunity and the military's permission, the repair starts") | https://mind.ua/news/20254503-ukrenergo-rozpochne-vidnovlennya-perebitoyi-rosiyanami-lep-do-zaes-za-pershoyi-mozhlivosti |
| R17 | 2023-05-22 | Dniprovska | ukrainian (Ukrenergo) | none stated | Ukrainian-held (inferred: "the Dnipro region") | stated | «"Укренерго" доклало максимум зусиль і відновило живлення атомної станції від української енергосистеми» ("Ukrenergo did its utmost and restored the plant's supply") | https://armyinform.com.ua/2023/05/22/vidnovleno-elektrozhyvlennya-zaporizkoyi-aes/ |
| R19 | 2023-11-26 | Dniprovska | ukrainian (Ukrainian specialists) | none stated | Ukrainian-held (inferred from Energoatom's wording: a distance, not used) | stated | «Пошкоджену лінію 750 кВ українські фахівці відремонтували о 20:52» ("Ukrainian specialists repaired the damaged 750 kV line at 20:52") | https://interfax.com.ua/news/general/950384.html |
| R20 | 2023-12 (by 15 Dec) | the 330 kV line | ukrainian (Ukrenergo) | none stated | Ukrainian-held (inferred: the attack on Dnipropetrovsk region) | implied | Ukrinform, 2 Dec: "Ukrenergo has restored a high-voltage line" (it names the 750 kV line; the 330 kV line, damaged in the same attack, was "repaired and restored this week" per IAEA Update 202, who not said) | https://ukrinform.net/rubric-economy/3794856-ukrenergo-restores-highvoltage-line-supplying-electricity-to-zaporizhzhia-npp.html ; GS 2023/12/ukraine-231215-iaea01.htm |
| R21 | 2024-03-14 | Ferosplavna-1 | ukrainian (Ukrenergo crews) | none stated | north bank, Ukrainian-held (stated: "the other side of the Dnipro river"; run with the Nikopol district military administration) | stated | «Ремонтні бригади НЕК «Укренерго» відновили надійність енергоживлення Запорізької АЕС»; «Військові пускають наших хлопців працювати лише на 2-2,5 години» ("the military let our men work only 2-2.5 hours") | https://www.ukrinform.ua/rubric-economy/3839888-remontni-brigadi-vidnovili-nadijnist-energozivlenna-zaes-ukrenergo.html ; GS 2024/02/ukraine-240221-iaea02.htm |
| R23 | 2024-04-06 | the 330 kV back-up line (ZTPP-Ferosplavna) | ukrainian (Ukrainian specialists; Ukrenergo crews) | none stated | not stated | stated | «зусиллями українських фахівців» ("through the efforts of Ukrainian specialists") | https://espreso.tv/viyna-z-rosiyeyu-energetiki-pidednali-zaporizku-aes-do-drugoi-linii-zhivlennya-vona-bula-na-remonti-vnaslidok-obstriliv-rf |
| R25 | 2024-08-23 | Ferosplavna-1 | ukrainian (Ukrenergo crews) | none stated | Ukrainian-held (inferred: waited on Ukraine's military) | stated | «Ремонтні бригади чекали дозволу військовослужбовців» ("the repair crews waited for the soldiers' permission") | https://www.kyivpost.com/uk/post/37878 |
| R26 | 2024-10-02 | the 330 kV line | ukrainian (Ukrenergo crews) | none stated | Ukrainian-held (inferred: waited on permission) | stated | «Ремонтні бригади понад добу чекали дозволу для того, щоб почати ремонт» ("the repair crews waited more than a day for permission to start") | https://espreso.tv/viyna-z-rosiyeyu-energetiki-ukrenergo-vidnovili-liniyu-zhivlennya-zaes |
| R27 | 2024-10-22 | Ferosplavna-1 | ukrainian (Ukrenergo crews) | none stated | north bank, Ukrainian-held (stated: "the other side of the Dnipro River") | stated | «Ремонтні бригади НЕК "Укренерго" відновили лінію живлення Запорізької атомної електростанції» ("Ukrenergo's crews restored the line") | https://www.ukrinform.ua/rubric-economy/3918910-energetiki-vidnovili-robotu-linii-zivlenna-zaes-minenergo.html ; GS 2024/10/ukraine-241024-iaea01.htm |
| R29 | 2024-12-01 | the 330 kV line | ukrainian (Ukrenergo, "energy workers") | none stated | Ukrainian-held (inferred: waited on permission) | stated | «Енергетики почали відновлювальні роботи одразу після дозволів від військових» ("energy workers started repairs right after the military's permission") | https://www.kyivpost.com/uk/post/43157 |
| R30 | 2024-12-31 | the 750 kV line's voltage stabiliser | unknown | none stated | "an open switchyard outside the plant", which one not said | unknown | "the voltage stabilizer ... located in an open switchyard outside the plant, was being repaired" | GS 2024/12/ukraine-241205-iaea01.htm ; GS 2025/01/ukraine-250117-iaea01.htm |
| R32 | 2025-02-27 | the 330 kV line | unknown | none stated | not stated | unknown | "once again available after it was lost for around a week earlier in February due to unspecified military activities" | GS 2025/02/ukraine-250227-iaea01.htm |
| R33 | 2025-03-21 | the link from the thermal plant's 330 kV switchyard to the plant's 750 kV switchyard | russian | none stated | the switchyards area, occupied (inferred from the place) | inferred | plant channel: «Линия введена по итогам проведенных восстановительных работ» ("the line was put in after restoration work"), no crew named; IAEA: reconnected "after the connection was cut as a result of damage to the ZTPP switchyard" | https://t.me/znppofficial/1418 ; GS 2025/03/ukraine-250327-iaea01.htm |
| R34 | 2025-07-04 | Dniprovska | ukrainian (Ukrenergo specialists) | none stated | not stated | stated | «Фахівці НЕК "Укренерго" відновили роботу високовольтної лінії» ("Ukrenergo's specialists restored the line"); plant channel: only «введена в работу» ("in service"), no credit claimed | https://interfax.com.ua/news/general/1085237.html |
| R35d | 2025-10-23 | Dniprovska | russian (repaired: the plant's staff with Rosseti, Russian military deminers); reconnected by the Ukrainian grid operator | IAEA's 1st local ceasefire, its Dniprovska zone, 18-23 Oct 2025 (unrolled truce 1) | occupied side (stated by AP; IAEA: "the other side of the frontline") | stated (Russian sources); disputed implicitly by Ukraine (see notes) | «Персонал Запорожской АЭС совместно со специалистами компании «Россети» приступил к ремонтно-восстановительным работам» ("the ZNPP's staff with Rosseti specialists began repair work"); IAEA: "to enable their respective expert teams to conduct repairs"; "energised by the Ukrainian grid operator" | https://t.me/znppofficial/1603 ; https://t.me/znppofficial/1608 ; GS 2025/10/ukraine-251018-iaea01.htm ; GS 2025/10/ukraine-251023-iaea01.htm |
| R35f | 2025-10-18 (work began; reconnected 8 Nov after R36) | Ferosplavna-1 | ukrainian | IAEA's 1st local ceasefire, its Ferosplavna-1 zone, from 18 Oct 2025 (unrolled truce 2) | Ukrainian-held (stated by AP) | implied | Ministry of Energy: «Українські фахівці відновлюють лінії електропостачання, які живлять Запорізьку атомну електростанцію» ("Ukrainian specialists are restoring the lines that feed the ZNPP"); IAEA: "temporary ceasefire zones around two specific locations on opposite sides of the frontline, to enable their respective expert teams to conduct repairs" | https://www.kyivpost.com/uk/post/62436 ; https://www.aljazeera.com/news/2025/10/18/zaporizhzhia-nuclear-plant-repairs-begin-in-ukraine-as-ceasefire-zones-set ; GS 2025/10/ukraine-251018-iaea01.htm |
| R36 | 2025-11-08 | Ferosplavna-1 | russian | IAEA's 2nd local ceasefire, 7-8 Nov 2025 (unrolled truce 3) | south bank, occupied (inferred from a distance, not used; the IAEA's team at the plant watched) | inferred | IAEA: "Technicians repaired a damaged cable ... with an IAEA team monitoring their work"; "so that their technicians could work without risking their own lives"; no crew named on either side | GS 2025/11/ukraine-251108-iaea01.htm ; https://mind.ua/news/20297101-zaes-znovu-pidklyuchili-do-rezervnogo-zhivlennya ; https://t.me/znppofficial/1612 |
| R37 | 2025-11-19 | Dniprovska | unknown | none reported | dataset: north side (inferred from a distance, not used) | unknown | IAEA: "Following repairs carried out [some distance] from the plant, the line was restored"; plant channel: a trip of «автоматической защиты», then «введена в работу» (no repair mentioned) | GS 2025/11/ukraine-251119-iaea01.htm ; https://t.me/znppofficial/1614 ; https://t.me/znppofficial/1615 |
| R39 | 2025-12-29 | the link between the thermal plant's switchyard and the plant's autotransformer | russian (the plant's specialists with Rosseti) | IAEA's 3rd local ceasefire, 28-29 Dec 2025 (not among the unrolled film's truces) | the switchyards area, occupied | stated | «Ремонтные мероприятия проводились совместными усилиями специалистов ЗАЭС и компании «Россети». Весь процесс проходил в присутствии инспекторов ... МАГАТЭ» ("the repair was done by the ZNPP's and Rosseti's specialists together, in the presence of IAEA inspectors"); IAEA Update 333: "Following an investigation conducted by the ZNPP ... the ZNPP is still investigating ways to repair the line" | https://t.me/znppofficial/1652 ; https://interfax.com/newsroom/top-stories/115498/ ; GS 2025/12/ukraine-251219-iaea01.htm ; GS 2025/12/ukraine-251230-iaea01.htm |
| R40 | 2026-01-19 | Ferosplavna-1 | ukrainian (Ukrainian technicians of the grid operator) | IAEA's 4th local ceasefire, 17-19 Jan 2026 (unrolled truce 4); an IAEA team sent from Vienna to the site | Ukrainian-held (inferred: Ukrainian technicians; the IAEA says only "on the frontline") | stated (Ukrainian, Western, IAEA and Russian sources agree) | IAEA: "the repairs conducted on the frontline by Ukrainian technicians"; Profile.ru: «Украинская ремонтная бригада выполняет восстановление линии» ("a Ukrainian repair crew is restoring the line") | GS 2026/01/ukraine-260109-iaea01.htm ; GS 2026/01/ukraine-260122-iaea01.htm ; https://profile.ru/news/politics/na-rezervnoj-lep-ferrosplavnaya-1-dlya-snabzheniya-zaporozhskoj-aes-nachali-remontnye-raboty-1809327/ ; https://kyivindependent.com/ukrainian-crew-begins-crucial-repairs-on-zaporizhzhia-nuclear-plant-backup-line |
| R41 | 2026-03-05 | the link from the thermal plant's switchyard to the plant's autotransformer (for Ferosplavna-1) | russian (Rosatom specialists) | IAEA's 5th local ceasefire, 27 Feb-5 Mar 2026 (unrolled truce 5) | the switchyards area, occupied | stated (Russian sources); one Ukrainian outlet disagrees (see notes) | «Специалисты Госкорпорации «Росатом» начали ремонтно-восстановительные работы на открытом распределительном устройстве Запорожской ТЭС» ("Rosatom specialists began repair work at the thermal plant's open switchyard") | https://t.me/znppofficial/1693 ; https://t.me/znppofficial/1699 ; GS 2026/03/ukraine-260306-iaea01.htm |
| R44 | 2026-06-13 | Ferosplavna-1 | unknown | IAEA-brokered ceasefire per Reuters (not counted by the IAEA as a ceasefire of its own) | disputed: near the thermal plant's switchyard (IAEA, occupied) or a substation across the river (Reuters, OECD-NEA, Ukrainian-held) | unknown | IAEA: "An IAEA team observed the repair activities on 13 June"; Reuters: "repairs were due to take place under a localized ceasefire agreed between Russia and Ukraine and brokered by the IAEA"; Energoatom: only "power engineers" | GS 2026/06/ukraine-260619-iaea01.htm ; https://www.arabnews.com/node/2646734/world ; https://ukrinform.net/rubric-economy/4133516-zaporizhzhia-npp-emerges-from-blackout.html |
| R45 | 2026-06-21/26 | Dniprovska | both (each side on its own stretch, implied by the IAEA; Kyiv Post's Ukrainian edition says "jointly") | IAEA's 6th local ceasefire, 5-26 Jun 2026 (unrolled truce 6); IAEA teams on both banks | the crossing (both banks) | stated (both took part); joint or separate differs by source | IAEA: "the IAEA team based at the ZNPP observed the activities on the plant side of the frontline, while another Agency team was deployed on the opposite side of the Dnipro River"; Ukrinform: "technical specialists from both sides"; Rosatom: «с российской стороны инфраструктура полностью восстановлена» ("on the Russian side the infrastructure is fully restored") | GS 2026/06/ukraine-260626-iaea01.htm ; https://ukrinform.net/rubric-economy/4130748-iaea-secures-ceasefire-for-repairs-to-power-line-supplying-znpp.html ; https://www.kyivpost.com/uk/post/77568 ; https://t.me/znppofficial/1810 ; https://www.osnmedia.ru/obshhestvo/rosatom-dneprovskaya-lep-k-zaes-otremontirovana/ |
| R45b | 2026-06-26 | the thermal plant's switchyard and the back-up link for Ferosplavna-1 | russian | IAEA's 6th local ceasefire (as R45) | the switchyards area, occupied | inferred | IAEA: "At the ZTPP, repairs were completed both on switchyard equipment and on a back-up transmission line connecting the Ferosplavna-1 line to the plant" (no crew named; no Russian or Ukrainian claim found) | GS 2026/06/ukraine-260626-iaea01.htm |
| R46 | 2026-09-07 | Ferosplavna-1 | ukrainian (Ukrainian technicians; they also reconnected the line) | IAEA's 7th local ceasefire, 5-7 Sep 2026 (unrolled truce 7) | north bank, Ukrainian-held (stated) | stated | IAEA: "The repairs, carried out by Ukrainian technicians and monitored by the IAEA"; Energoatom: «Саме українські фахівці ... виконали потрібні роботи» ("it was Ukrainian specialists who did the work") | GS 2026/09/ukraine-260905-iaea01.htm ; https://fakty.com.ua/ua/ukraine/20260908-zaes-pidklyuchyly-do-energosystemy-ukrayiny-stantsiya-bula-znestrumlena-z-20-serpnya/ ; https://www.world-nuclear-news.org/articles/zaporizhzhia-reconnected-to-external-power-after-18-days |

## Summary

**Counts (41 repairs).**

| side | stated | implied | inferred | total |
|---|---|---|---|---|
| ukrainian | 16: R01 R04 R05b R07 R08 R17 R19 R21 R23 R25 R26 R27 R29 R34 R40 R46 | 7: R05a R06 R10 R15 R16 R20 R35f | 4: R09 R11 R11b R13 | **27** |
| russian | 3: R35d R39 R41 | 0 | 3: R33 R36 R45b | **6** |
| both | 1: R45 | | | **1** |
| unknown | | | | **7**: R02 R03 R12 R30 R32 R37 R44 |

- **Well sourced, the source naming the crew:** Ukrainian, 16 (Ukrenergo or "Ukrainian specialists" in the
  organisations' own statements, plus the IAEA for R40 and R46). Russian, 3 (the plant's own channel names the plant's
  staff, Rosseti or Rosatom). Both, 1 (R45).
- **A caveat for the map:** R05a, R05b and R10 (September-October 2022) were the plant's or the thermal plant's
  Ukrainian staff working on the occupied side, before or just after Rosatom took the plant (decree of 5 October 2022).
  The IAEA calls them "Ukrainian engineers". A link from "the Ukrainian side" is true to who did the work; it is not
  the side of the front they worked on.
- **Pattern:** from 2023 to September 2025 every repair with a named crew was Ukrainian, on the Ukrainian-held side
  (several waited on Ukraine's military for permission). Russia named its own crews only once the IAEA's ceasefires
  began (October 2025), and only for work on the occupied side: Dniprovska in October 2025, the switchyard link in
  December 2025 and March 2026, its own stretch of the crossing in June 2026. Before that the plant's channel reported
  reconnections without saying who did the work.
- **Arranged by:** the IAEA, for all seven truces and its third, uncounted by the film (December 2025). Ukrainian and
  Western sources say "brokered" or "mediated". Russian sources add the Russian MFA, Defence Ministry, Rosgvardia,
  Rostekhnadzor and Rosatom as co-organisers. No Ukrainian official claimed to have arranged one. Before October 2025 no
  repair had a ceasefire; Ukrainian crews worked in short windows the Ukrainian military allowed.
- **The IAEA's role:** brokered every ceasefire. Its team at the plant monitored the occupied-side work (October
  2025, November and December 2025, March 2026). A team sent from Vienna monitored the Ukrainian side in January 2026.
  In June 2026 there were two teams, one on each bank. It also observed the demining. It never did repairs itself.

**Who repaired vs who reconnected.**
- R35d: Russian crews repaired; the Ukrainian grid operator energised the line (IAEA Update 323).
- R45: repaired by both, never reconnected. The IAEA says the line's substation was too damaged. Rosatom says
  «напряжение так и не подано украинской стороной» ("the Ukrainian side has still not put voltage on the line")
  (https://t.me/znppofficial/1810).
- R46: Ukrainian technicians both repaired and reconnected.
- 2023-2025: Ukrainian crews repaired; the plant's channel reported the same reconnections in its own name without
  claiming the repair.

**Disagreements between the accounts.**
1. **R35d.** Ukraine's Ministry of Energy counts it as the 42nd restoration «українськими енергетиками» ("by Ukrainian
   energy workers") (https://www.kmu.gov.ua/news/svitlana-hrynchuk-enerhetyky-vidnovyly-zhyvlennia-zaporizkoi-aes-ta-vyvely-stantsiiu-z-desiatoho-blekautu).
   The plant's channel and TASS credit the plant's staff and Rosseti, with the Defence Ministry providing security. No
   Ukrainian source says Ukrainian crews crossed the front. Before the truce, Ukrenergo said the line was intact "on the
   territory controlled by Ukraine". The Ukrainian claim most likely means the reconnection, not the repair.
2. **R41.** Kyiv Post (English, 27 February) says "carried out by a Ukrainian technical team"
   (https://www.kyivpost.com/amp/post/70915). The plant's channel names Rosatom's specialists at the thermal plant's
   switchyard, which is where the IAEA puts the damage. Kyiv Post's own Ukrainian edition doesn't say whose specialists
   (https://www.kyivpost.com/uk/post/71636). Russian is the better-supported account.
3. **R45, joint or separate.** Kyiv Post's Ukrainian edition: «українські фахівці спільно з представниками окупаційної
   адміністрації» ("Ukrainian specialists jointly with representatives of the occupation administration"). The IAEA's
   two teams, one per bank, point to each side working its own stretch. Rosatom claims only "the Russian side" and calls
   it its own. Ukrenergo, Energoatom and the ministry didn't say who worked where. Also: Rosatom accused Ukraine of a
   drone strike on its deminers during the truce (Al Jazeera, 5 June 2026). The repair date varies in the Russian
   sources: the channel says 21 June, Likhachev 22 June, and an Interfax piece "23 July", probably an error.
4. **R21.** Ukrenergo announced the line repaired on 24-25 February 2024. The plant's channel answered
   «Информация «Укрэнерго» о вводе в работу ... «Феросплавная-1» не соответствует действительности» ("Ukrenergo's
   information about Ferosplavna-1 being put into service is untrue") (https://t.me/znppofficial/885). The IAEA and
   Energoatom have the line back on 14 March. Ukrenergo crews did the repair either way.
5. **R37.** The IAEA says "following repairs"; the plant's channel says the line tripped on its own protection and was
   switched back in, with no repair.
6. **R44, where.** The IAEA says near the thermal plant's switchyard (occupied); Reuters and OECD-NEA say a substation
   across the river (Ukrainian-held). Who repaired is unknown either way.
7. **R18 (not counted).** Karchaa (Rosenergoatom) said the fault was «на территории, подконтрольной киевскому режиму»
   ("on territory controlled by the Kyiv regime") and questioned «квалификации тех, кто этот ремонт осуществляет» ("the
   skill of those who do this repair") (https://iz.ru/1557247/2023-08-10/zaporozhskaia-aes-vnov-ostalas-bez-energopitaniia-ot-osnovnoi-lep).
   The IAEA put the fault on the southern bank. Neither names a repairer.

**R14: did Russia complete a repair on the plant's other, cut lines into occupied territory?** No, as far as the
sources go. This confirms the dataset.
- IAEA Update 151 (22 March 2023): "Rosatom is working to restore three 330 kV lines at the thermal power plant
  switchyard into the grid system in currently Russian-controlled territory. The ISAMZ team has not been able to verify
  this information." (GS 2023/03/ukraine-230322-iaea01.htm)
- IAEA Update 155 (28 April 2023): a transformer was brought in "to replace the damaged 'Kakhovka' node in the ZNPP open
  switchyard ... This line is linked to the currently Russian-controlled electrical grid, to the south of the ZNPP site."
  (GS 2023/04/ukraine-230428-iaea01.htm)
- The plant's channel, July 2023: the plant's 750/330 kV autotransformer was replaced by its electrical shop and
  Atomenergoremont (https://t.me/znppofficial/411). That is equipment inside the plant, not a line reconnected.
- No IAEA update read, and no post in the channel's whole history, reports any of the Kakhovska, Zaporizka or
  Pivdennodonbaska 750 kV lines, or the thermal plant's other 330 kV lines, back in service. Russian statements on the
  Russian grid are all in the future tense (Likhachev, December 2024: «вновь будет подключена к сетям» ("will be
  connected to the grid again"), https://t.me/znppofficial/1321). Through 2026 the channel itself says the plant
  depends on a single line fed from the Ukrainian-held bank
  («станция все так же фактически зависит лишь от одной линии», "the plant still in effect depends on one line only",
  https://t.me/znppofficial/1829).
- The lines Russia was reported building toward the plant from the occupied south-east in 2025 (Greenpeace, NYT) are
  reported as unfinished. The IAEA had "no additional information" on them, and no Russian claim of completion was found.

## Open questions

- **Repairs not in `repairs.yaml`** that the plant's channel reports:
  - 14 April 2026: «Специалистами станции совместно с представителями сетевой организации успешно восстановлена схема
    электроснабжения» ("the plant's specialists, with the grid organisation's representatives, restored the supply
    scheme") over Ferosplavna-1, without a ceasefire (https://t.me/znppofficial/1729; cf. R42, not counted).
  - 15-23 October 2026: Rosatom's specialists repaired thermal-plant equipment under a ceasefire organised by «Росатом,
    МИД России и Минобороны России при содействии МАГАТЭ» ("Rosatom, Russia's MFA and Defence Ministry, with the IAEA's
    help") (https://t.me/znppofficial/1862, https://t.me/znppofficial/1866). Possibly an eighth IAEA ceasefire; check
    the IAEA.
  - 8 November 2026 (today): Ferosplavna-1 back the same day «после проведения ремонтно-восстановительных работ»
    ("after repair and restoration work"), no crew named (https://t.me/znppofficial/1882). Ukrinform's sidebar also
    shows "Ukrainian energy workers restore external power supply to ZNPP" on this date, unverified.
  - R43 (6 June 2026, not counted): the plant's channel says «Специалисты восстановили работоспособность линии»
    ("specialists restored the line") (https://t.me/znppofficial/1778), but the damage was at the Nikopolska
    substation on the Ukrainian-held side (OECD-NEA). Who repaired is open.
- R02, R03, R06, R12, R13 (2022 to January 2023): Energoatom's own archive (blocked) is the likeliest source for who.
- R36: Russia names nobody for the 8 November 2025 south-bank repair, and neither does Ukraine. Is it worth reading
  TASS, whose pages came back empty, before the map draws it as Russian (inferred)?
- R44: settle where before drawing a side.
- R20: the dataset says 330 kV. Ukrinform's 2 December 2023 item is the 750 kV line's restoration after the same
  attack; who repaired the 330 kV line that week isn't stated.
- R32 and R33 are confirmed in the IAEA's 2025 updates (Updates 278 and 282, read). They are not the 2026 sequence they
  resemble (R41).
- The unrolled film's truces leave out the IAEA's third ceasefire (R39, December 2025), already noted in
  `../repairs.yaml` caveats. A map of sides would add a Russian-side link there.

## Added after this note (8 November 2026)

`new_repairs_check.md` checked the three repairs listed above against the IAEA. One is counted: **R48** (15-23 October
2026, the thermal plant's switchyard, russian, stated by Rosatom, under the IAEA's eighth local ceasefire). With it the
dataset has 42 repairs: ukrainian 27, russian 7 (stated 4: R35d, R39, R41, R48), both 1, unknown 7. 14 April 2026 is R42
(not counted, no repair); 8 November 2026 is R49 (not counted until the IAEA gives its cause and place).
