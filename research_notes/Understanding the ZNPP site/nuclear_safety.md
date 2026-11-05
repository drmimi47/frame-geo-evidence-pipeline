# Nuclear-safety physics of the occupied ZNPP (2022 – October 2026): why it needs outside power, how much, and what happens without it

Researched 29 October 2026. Source levels used below:
- **[IAEA]**: the IAEA's own statements, or those statements as reported by WNN, the WNA, OECD-NEA or NucNet. iaea.org returned HTTP 402 to the fetch tool, so the IAEA updates were read through these secondary sources.
- **[operator]**: Energoatom (Ukraine) or Rosatom and the Russian-appointed management. These are party claims.
- **[estimate]**: an outside analyst (Bellona, academics).
- **[snippet]**: known only from a search-result snippet, not from a page that was fetched and read.

---

## 1. Plant basics and the state of each unit since September 2022

### Takeaway
The plant has six pressurised-water reactors of about 1,000 MWe each, roughly 6,000 MWe in total, and before the war it supplied about a fifth of Ukraine's electricity. No unit has generated power to the grid since September 2022. Units 4, 5 and 6 at different times ran "hot" (in hot shutdown) to make steam and district heat for Enerhodar. Every unit has been in cold shutdown since mid-April 2024. Spent fuel sits in six pools inside the containments and in an open-air dry cask yard.

### Cited Findings
- The plant has six PWRs rated at 950 MW each (the usual figure is 6 × 1,000 MWe, so 6,000 MWe in all). It "once supplied about a fifth of Ukraine's electricity" — [IEEE Spectrum, P. Fairley, 4 May 2025](https://spectrum.ieee.org/amp/zaporizhzhia-nuclear-power-plant-2671872736)
- The design is a VVER-1000/V-320. This is standard reference data; I did not re-verify it on a fetched page this session — [WNA country profile](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy) (the profile covers the plant; the V-320 label is not a quote from it)
- On 4 March 2022, when the plant was seized, Unit 4 was the only unit generating. Unit 1 was in a maintenance outage, Units 5 and 6 were in reserve at low power, and Units 2 and 3 were being shut down under control — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
- Energoatom shut down Unit 6, the last one operating, on 11 September 2022 and put it into cold shutdown — [The Conversation, N. Meshkati (USC), 13 Sept 2022](https://theconversation.com/cold-shutdown-reduces-risk-of-disaster-at-zaporizhzhia-nuclear-plant-but-combat-around-spent-fuel-still-poses-a-threat-190516)
- On 8 June 2023, just after the Kakhovka dam was destroyed, Ukraine's regulator SNRIU ordered all six units limited to cold shutdown — [OECD-NEA status page](https://oecd-nea.org/jcms/pl_66130/ukraine-current-status-of-nuclear-power-installations); [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
- Rosatom nonetheless kept one or two units in hot shutdown for steam and heat [IAEA]:
  - 30 Sept 2023: Unit 4 went back to hot shutdown and Unit 6, which had been making steam, went to cold shutdown.
  - 13 Oct 2023: Unit 5 was brought to hot shutdown "to supply hot water and district heating over winter". Unit 4 was already in hot shutdown, producing steam for processing liquid radioactive waste and heat for Enerhodar.
  - 15 Apr 2024: the IAEA reported all six units in cold shutdown after the heating season ended. — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
- "The last unit entered cold shutdown in April 2024" — [WNN, 7 Aug 2026](https://world-nuclear-news.org/articles/water-levels-to-be-increased-in-zaporizhzhias-used-fuel-ponds)
- ZNPP was "the first plant to remain in hot shutdown for months", which the article says broke its licence. Hot reactors melt down faster if cooling fails, so the hot-shutdown period raised the accident risk — [IEEE Spectrum, May 2025](https://spectrum.ieee.org/amp/zaporizhzhia-nuclear-power-plant-2671872736)
- 2 Nov 2024: Unit 1 went back to cold shutdown after a leaking impulse line was repaired — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy); [OECD-NEA](https://oecd-nea.org/jcms/pl_66130/ukraine-current-status-of-nuclear-power-installations)
- Lasting shutdown damage reported:
  - Leaks of boric acid from the primary circuit into the steam generators (Unit 5, late 2023) — [Edwin Lyman (UCS) on X, citing Energoatom](https://x.com/NucSafetyUCS/status/1727321463953162263) [operator, via expert]
  - Steam-generator leaks "in half of the units", and boric acid crystallising in the circuits — [IEEE Spectrum](https://spectrum.ieee.org/amp/zaporizhzhia-nuclear-power-plant-2671872736)
- **Spent fuel.** There are six spent-fuel pools, one inside each unit's containment. A 2017 Ukrainian report to the IAEA says the pool racks were re-racked more densely ("compacted") to hold more fuel, which means more heat per pool — [Meshkati, The Conversation](https://theconversation.com/cold-shutdown-reduces-risk-of-disaster-at-zaporizhzhia-nuclear-plant-but-combat-around-spent-fuel-still-poses-a-threat-190516)
- **Dry storage.** Casks are designed to keep fuel contained for at least 50 years with no water or coolant. They stand outside any containment and were designed for an airliner crash, but "it is not clear whether artillery shelling and aerial bombardment" could crack them — [Meshkati](https://theconversation.com/cold-shutdown-reduces-risk-of-disaster-at-zaporizhzhia-nuclear-plant-but-combat-around-spent-fuel-still-poses-a-threat-190516). The yard is surrounded by a 30 cm thick, 6 m high concrete wall — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
- **Cask counts** (all [snippet], and they conflict):
  - The design is for more than 9,000 assemblies in 380 ventilated casks of 144 t each. An older count says 167 casks were installed; the system has run since August 2004 — [power-technology.com](https://www.power-technology.com/projects/zaporizhye-nuclear-power-plant/)
  - "174 casks, each containing 24 assemblies" — [TEI Times](https://teitimes.com/post/russia-fires-rockets-at-zaporizhzhia-nuclear-power-plant) (undated, original source unknown)
  - A US DOE/PNNL page says 24 or 25 assemblies per cask — [PNNL](https://insp.pnnl.gov/-reports-technology-transporter.htm)
- In 2022 shelling damaged walls, a roof and windows near the dry storage yard, with "no visible damage to the containers" — [Kyiv Independent, citing IAEA](https://kyivindependent.com/uncategorized/iaea-chief-shelling-at-zaporizhzhia-plant-caused-no-immediate-threat-to-nuclear-safety) [snippet]
- Rostekhnadzor (Russia's regulator) issued a 25-year licence for the dry storage facility on 22 Oct 2025 — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
- **Staff:**
  - About 11,500 before the war — [OECD-NEA](https://oecd-nea.org/jcms/pl_66130/ukraine-current-status-of-nuclear-power-installations)
  - About 3,000 (IAEA estimate, 19 Jan 2023) — same source
  - 4,500 employed by the Russian operating entity (1 Feb 2024) — same source

### Inferences
- "All units in cold shutdown" holds without exception only from mid-April 2024. Between September 2022 and April 2024, one or two units (4, 5, and Unit 6 briefly) were kept in hot shutdown at times. That is the period when the meltdown margin was shortest, measured in hours to about a day rather than weeks.
- The film should keep the reactors' fuel and the pools' fuel apart. Since 2024 the pools and the dry casks probably hold most of the site's radioactive inventory.

### Gaps
- I found no reliable current count of dry-storage casks, nor a count of assemblies in each pool. Figures of 167 and 174 casks circulate, neither dated nor sourced. To settle it: the IAEA Board reports, or Energoatom.
- Whether every core is still loaded with fuel (rather than offloaded to the pools) was not confirmed for each unit in the sources read.
- The exact pre-war share of electricity: "about a fifth" (IEEE); "almost half of Ukraine's nuclear output" is commonly quoted but I did not verify it.

---

## 2. What off-site power is used for in cold shutdown, and how much

### Takeaway
A plant in cold shutdown makes nothing but still consumes power. It runs the pumps that carry decay heat out of the cores and the spent-fuel pools to the essential service water and sprinkler ponds, the pumps on the groundwater wells, ventilation, instruments and control, lighting and communications, and keeps the safety systems ready. The best published figure for this load comes from the 2025 blackout: eight diesel generators supplied **about 20–22 MW**, roughly **0.35% of the plant's 6,000 MWe output**. In that sense the plant is a small customer, not a power station.

### Cited Findings
- Even in shutdown, power is needed to remove residual heat and for site services: pumps, valves, controls, monitoring, water management, lighting, communications and ventilation — [Anantam IAS explainer](https://anantamias.com/current-affairs/zaporizhzhia-offsite-power-nuclear-safety/) [snippet; low-tier source, but consistent with the IAEA]
- In cold shutdown "the primary cooling pumps need not run at the same level, so less power is needed for cooling". The pools' cooling pumps "need much less electricity", and the spent-fuel cooling system "could tolerate a brief electricity outage" — [Meshkati](https://theconversation.com/cold-shutdown-reduces-risk-of-disaster-at-zaporizhzhia-nuclear-plant-but-combat-around-spent-fuel-still-poses-a-threat-190516)
- The units "still need a constant electricity supply to cool residual reactor core activity and spent fuel pools" — [NucNet, 24 Sept 2025](https://www.nucnet.org/news/zaporizhzhia-plant-suffers-fresh-blackout-emergency-generators-activated-9-3-2025)
- **The number:** on 7 Oct 2025, in the month-long blackout, 8 EDGs were supplying "a total power output of 20-22 megawatts" for cooling and other safety functions, with 12 more on standby [IAEA via NEA] — [OECD-NEA](https://oecd-nea.org/jcms/pl_66130/ukraine-current-status-of-nuclear-power-installations)
- Bellona says that reconnecting to Russia's grid would in the first instance only supply "the few megawatts needed for safety systems" — [Bellona, 2 Oct 2025](https://bellona.org/news/nuclear-issues/2025-10-is-the-zaporizhzhia-nuclear-plants-longest-blackout-a-scheme-for-russia-to-siphon-off-its-power) [estimate]
- Energoatom: "Even in cold shutdown, a blackout would threaten control of the safety systems and the spent fuel pools" — [Euromaidan Press, 7 Sept 2026](https://euromaidanpress.com/2026/09/07/russia-burns-occupied-zaporizhzhia-nuclear-plants-last-resort-generators-as-everyday-power-ukraine-says/) [operator; snippet]
- Seven pillars, pillar 4: "there must be a secure off-site power supply from the grid for all nuclear sites". The 2022 report recommended that "off-site power supply line redundancy as designed should be re-established and available at any time" — [NEI Magazine](https://www.neimagazine.com/news/iaea-issues-report-on-zaporozhzhia-and-addresses-un-security-council-9988384/); [GlobalSecurity, IAEA text](https://www.globalsecurity.org/wmd/library/news/ukraine/2022/09/ukraine-220907-iaea02.htm) [snippet]

### Inferences
- 20–22 MW ÷ 6,000 MW ≈ 0.35%. The lines the film shows (750 kV, 330 kV) were built to carry gigawatts out of the plant. Today they carry a few tens of megawatts in. That reversal of direction is accurate and makes a strong image. The project's "flow toward the plant since September 2022" convention matches it.
- The 20–22 MW is what the diesels delivered to essential loads only. Normal house load on grid power, with non-essential systems and the town's needs, is probably higher. Say "about 20 MW to keep it safe", not "the plant uses 20 MW".

### Gaps
- I found no IAEA or Energoatom figure for the plant's normal house load in cold shutdown on grid power, nor the rating of each EDG.

---

## 3. Decay heat now, and how much time there is if all cooling is lost

### Takeaway
Fission stopped long ago. The heat that remains comes from radioactive decay and falls steeply over time. Four years after shutdown it is tiny compared with a working reactor:
- Bellona estimates under **0.8 MW per reactor core** and under **2.5 MW per unit including its pool**. A reactor running at power produces about 3,000 MW of heat.
- The IAEA says that in a total blackout it would "take considerably longer before nuclear fuel could be damaged or potentially melt" than at an operating reactor.
- The outside estimate of the time margin with no cooling at all is **at least two to three weeks** (Bellona). At Fukushima it was **hours**.

### Cited Findings
- The IAEA (2026): "The plant has been in shutdown since September 2022, meaning there is significantly less decay heat to remove through cooling than would be the case at an operating reactor. As a result, in the event of a complete station blackout, it would take considerably longer before nuclear fuel could be damaged or potentially melt." — attributed to [IAEA Update 365](https://www.iaea.org/newscenter/pressreleases/update-365-iaea-director-general-statement-on-situation-in-ukraine) [IAEA; snippet: the page could not be fetched]
- Bellona (Dmitry Gorchakov, 2 Oct 2025, using data from Bellona's 2024 restart report): "current residual heat output per reactor does not exceed 800 kilowatts". Total heat generation per unit, pool included, is "no more than 2.5 megawatts" (called conservative). If all cooling failed, the water already in the buildings would cool the fuel by evaporation for "at least two to three weeks" — [Bellona](https://bellona.org/news/nuclear-issues/2025-10-is-the-zaporizhzhia-nuclear-plants-longest-blackout-a-scheme-for-russia-to-siphon-off-its-power) [estimate]
- A Ukrainian expert, quoted after an earlier blackout: "due to the low level of residual heat generation after a long shutdown … there is a certain time reserve for restoring power without transitioning to critical parameters" — [UNN](https://unn.ua/en/news/13th-blackout-at-znpp-expert-explained-the-threat-and-named-the-main-risks-to-the-plants-safety) [snippet]
- The Bulletin of the Atomic Scientists (Feb 2023): decay heat drops sharply within months of shutdown, so the grace period is "measured in days rather than hours" — [Bulletin](https://thebulletin.org/2023/02/one-year-later-new-dangers-threaten-ukraines-embattled-zaporizhzhia-nuclear-plant/) [snippet]
- Edwin Lyman (UCS), early in the war: if cooling were interrupted there might be "a day or two before the spent fuel began to overheat and degrade" — quoted in [The Conversation, "dirty bomb waiting to happen"](https://theconversation.com/the-zaporizhzhia-nuclear-power-plant-is-a-dirty-bomb-waiting-to-happen-a-nuclear-expert-explains-209236) [snippet; this dates from 2022–23, when decay heat was much higher]
- **August 2026 measure:** operators began raising the water level in the spent-fuel pools of all six units, with IAEA staff observing, so as to "increase the time available before water could begin to boil off" in a prolonged blackout that exhausts the diesel. No resulting margin was published — [WNN, 7 Aug 2026](https://world-nuclear-news.org/articles/water-levels-to-be-increased-in-zaporizhzhias-used-fuel-ponds) [IAEA]
- In September 2026, to stretch its fuel, the plant ran cooling pumps on and off with only two generators running. Grossi said no nuclear plant should have to cut back essential cooling to save diesel — [Euromaidan Press, 7 Sept 2026](https://euromaidanpress.com/2026/09/07/russia-burns-occupied-zaporizhzhia-nuclear-plants-last-resort-generators-as-everyday-power-ukraine-says/) [snippet]; [ANS Nuclear Newswire, 9 Sept 2026](https://www.ans.org/news/2026-09-09/article-8377/zaporizhzhia-restores-offsite-power-following-iaeabrokered-local-ceasefire/)

### Inferences (my own order-of-magnitude checks; label them as such if used)
- **Decay heat after about 4 years.** I used the textbook Way–Wigner approximation, P/P₀ ≈ 0.0622 [t^−0.2 − (t+T)^−0.2], with t ≈ 4 years since shutdown and T ≈ 1 year of operation. It gives about 7×10⁻⁵ of full thermal power, about **0.2 MW** for a 3,000 MWt core. The formula is known to underestimate at long times because it leaves out actinide decay. Bellona's "≤ 0.8 MW" is the same order and deliberately conservative.
- **The same reactor one hour after a shutdown from full power** produces about 1–1.5% of 3,000 MWt, i.e. **about 30–45 MW**. That is roughly 50–200 times more heat than now, which is why Fukushima's cores melted within hours to a day.
- **Pool illustration.** The pool volume is unknown (see Gaps); I assumed 1,000 m³ of water and 1 MW of heat:
  - Heating it from 30 °C to 100 °C takes about 3.4 days.
  - Boiling it then removes about 38 t of water a day.
  - So it takes weeks, not hours, before fuel would uncover.
  - This is consistent with Bellona's "two to three weeks" and with the IAEA's decision to raise pool levels to gain time.
- **What this means for the claim.** A "meltdown within hours of a blackout" is not physically plausible at ZNPP in 2025–26. The real danger in a long station blackout (no grid and no diesel) is a slow heat-up and boil-off over days to weeks. If it went on long enough with no water added, fuel could still be damaged and radioactivity released, most plausibly from the pools.

### Gaps
- No official IAEA number in days for the time to boiling or to fuel damage was found. iaea.org could not be fetched, so the exact wording in Updates 300–370 was not checked.
- Pool water volumes, pool inventories and how loaded each core is are not public in the sources read.

---

## 4. Diesel generators: how many, how many days, and what if they fail

### Takeaway
The site has **20 emergency diesel generators**: three per unit (18) plus two "bunkerized" units. There are also several mobile diesel generators, about six of them added after Fukushima, with more delivered in 2022 and 2024. The legal minimum stock is **10 days of fuel**, and stocks have ranged from about 10 to 20 days. Running the plant on diesel has stopped being a rare emergency and become routine:
- 23 Sept–23 Oct 2025: one month on diesel.
- 20 Aug–7 Sept 2026: 18 days on diesel, during which the fuel fell to the 10-day minimum.

If the diesels failed or ran dry, the plant would be in a station blackout. That is the scenario every safety layer exists to prevent.

### Cited Findings
- **The fleet:**
  - Each reactor has three EDGs, and "one generator can keep a reactor and its spent fuel safe for ten days". There are also two "bunkerized" diesel generators and one mobile diesel generator per unit — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
  - The plant "originally had 20 EDGs for six reactors, plus six mobile diesel generators added after Fukushima" (27 Mar 2025). Three new mobile generators arrived on 18 Dec 2024 — [OECD-NEA](https://oecd-nea.org/jcms/pl_66130/ukraine-current-status-of-nuclear-power-installations)
  - Late 2024: three new mobile DGs were seen next to the turbine buildings, and seven mobile units delivered in late 2022 had been disconnected — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
- **Fuel stock:**
  - 9 Mar 2023: all 20 EDGs started; 15 days of fuel on site — [OECD-NEA](https://oecd-nea.org/jcms/pl_66130/ukraine-current-status-of-nuclear-power-installations)
  - 11 Jul 2024: 1,300 m³ of diesel, "at least 10 days", "the minimum regulatory requirement in Ukraine" — same source
  - After 4 Jul 2025: 20 days of fuel on site — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
  - Sept 2025: tanks recently filled for about 20 days — [NucNet, 24 Sept 2025](https://www.nucnet.org/news/zaporizhzhia-plant-suffers-fresh-blackout-emergency-generators-activated-9-3-2025)
  - Russian officials told the IAEA "at least 20 days" — [Bellona](https://bellona.org/news/nuclear-issues/2025-10-is-the-zaporizhzhia-nuclear-plants-longest-blackout-a-scheme-for-russia-to-siphon-off-its-power) [operator, via IAEA]
- **The month-long blackout, 23 Sept–23 Oct 2025** [IAEA]:
  - At 16:56 local time on 23 Sept the last line (750 kV Dniprovska) was cut. It was the 10th complete loss of off-site power. The plant had been on that single line for nearly five months, since the 330 kV backup was lost on 7 May 2025 — [NucNet](https://www.nucnet.org/news/zaporizhzhia-plant-suffers-fresh-blackout-emergency-generators-activated-9-3-2025); [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
  - All 18 EDGs started, then were cut to 7 for essential loads to save fuel (WNA). Bellona and the NEA report 8 running at times: 8 on 30 Sept, and 8 supplying 20–22 MW on 7 Oct — [Bellona](https://bellona.org/news/nuclear-issues/2025-10-is-the-zaporizhzhia-nuclear-plants-longest-blackout-a-scheme-for-russia-to-siphon-off-its-power); [OECD-NEA](https://oecd-nea.org/jcms/pl_66130/ukraine-current-status-of-nuclear-power-installations)
  - On 23 Oct 2025 Dniprovska was repaired under an IAEA-brokered local ceasefire. It "lasted almost exactly a month", the longest complete loss there — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
- **The 26th loss, 20 Aug–7 Sept 2026** [IAEA]:
  - Ferosplavna-1 was cut on 20 Aug. All available EDGs started and seven kept running — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
  - On 28/29 Aug there was about 10 days of diesel, "the minimum regulatory requirement". The last delivery had been in March 2026, and a May delivery was delayed — [OECD-NEA](https://oecd-nea.org/jcms/pl_66130/ukraine-current-status-of-nuclear-power-installations)
  - In early September the plant went from four generators down to two — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
  - Several dozen tonnes of diesel arrived on 27–28 Aug, but Grossi later warned of a possible "station blackout within days" without power or more fuel — [Armscontrol.org, Sept 2026](https://www.armscontrol.org/act/2026-09/news/outages-rising-zaporizhzhia-power-plant) [snippet]; [Al Jazeera, 29 Aug 2026](https://www.aljazeera.com/news/2026/8/29/ukrainian-nuclear-power-plant-without-external-power-for-over-a-week)
  - Power came back the evening of 7 Sept 2026 after Ferosplavna-1 was repaired under the seventh IAEA-brokered local ceasefire (some sources number it differently) — [ANS](https://www.ans.org/news/2026-09-09/article-8377/zaporizhzhia-restores-offsite-power-following-iaeabrokered-local-ceasefire/); [ANVS (Dutch regulator), 11 Sept 2026](https://english.autoriteitnvs.nl/latest/news/2026/09/11/power-supply-to-zaporizhzhia-nuclear-power-plant-restored)
- 25 Sept 2026: under a revised strategy, only 4 of the 20 EDGs would start automatically on a loss of off-site power, and 2 EDGs were under maintenance. Diesel supply was "increasingly pressing" with winter coming — [OECD-NEA](https://oecd-nea.org/jcms/pl_66130/ukraine-current-status-of-nuclear-power-installations) [IAEA via NEA]
- Ukraine (Energoatom) says Russia is burning the plant's "last-resort generators as everyday power" — [Euromaidan Press, 7 Sept 2026](https://euromaidanpress.com/2026/09/07/russia-burns-occupied-zaporizhzhia-nuclear-plants-last-resort-generators-as-everyday-power-ukraine-says/) [operator; snippet]
- **Counts:**
  - 26 complete losses since February 2022, 14 of them since April 2026, with Energoatom's count differing by one — [OECD-NEA](https://oecd-nea.org/jcms/pl_66130/ukraine-current-status-of-nuclear-power-installations)
  - The WNA's chronology numbers the September 2025 loss as the 10th, which implies 16 losses between December 2025 and August 2026 — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
- Lines: Dniprovska (750 kV) has been disconnected since 24 Mar 2026. It was repaired by 26 June 2026 but cannot come back into service because a substation more than 100 km to the north-west was damaged in May — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy); [WNN, 7 Aug 2026](https://world-nuclear-news.org/articles/water-levels-to-be-increased-in-zaporizhzhias-used-fuel-ponds)

### Inferences
- Diesels are the third layer of power supply. The first two are the four 750 kV and the 330 kV lines as designed, and, normally, the plant powering itself from its own running units. Diesels are designed for short emergencies, not months. Running them for weeks wears them out and creates a fuel-delivery problem across a front line.
- The danger therefore runs in sequence: grid lost, then diesels running, then diesel fuel or the machines failing, then station blackout, then a slow heat-up over days to weeks. An accident needs every layer to fail and to stay failed long enough. The war has made each layer weaker at the same time.

### Gaps
- Rating per EDG (MW) not found.
- Whether the "4 auto-start" strategy of September 2026 is still in force on 29 Oct 2026 not confirmed.

---

## 5. Is "meltdown" realistic now? Expert views, Fukushima, and the more realistic risks

### Takeaway
The student's framing ("power must come in from the Ukrainian grid to prevent a meltdown") is **right in principle but overstated in its timing and certainty, and partly wrong about "Ukrainian"**:
- **Right:** without power the pumps stop. Without cooling the fuel, cores and above all the pools would slowly heat up. Off-site power is the IAEA's pillar 4. A prolonged station blackout could end in fuel damage and a release.
- **Overstated:** four years into cold shutdown, nothing would happen within hours, and Fukushima is not the right picture. There would be days to weeks to restore power or add water, for example from fire trucks or mobile pumps. The diesels have bridged a full month. Most experts call meltdown now a low-probability outcome that needs several failures in a row.
- **"From the Ukrainian grid":** for now, the only lines physically connected run to the Ukrainian-held bank. Russia has told the IAEA it plans to connect the plant to its own grid. The physics only needs power, not Ukrainian power.

The more realistic risks are:
- a slow boil-off in the pools during a long blackout;
- shelling of the open-air dry casks or the pools, which would be a localised "dirty bomb" type release, not a reactor explosion;
- the degradation of equipment and staff;
- above all, **a Russian restart**, which would bring back the high heat, short time margins and large water needs of an operating plant.

### Cited Findings
- Cold shutdown "all but eliminated the risk of a nuclear meltdown", though fighting could still release radioactive material. Radioactivity released from damaged spent-fuel pools "could be even greater than from a meltdown at the reactor itself" — [Meshkati, The Conversation, Sept 2022](https://theconversation.com/cold-shutdown-reduces-risk-of-disaster-at-zaporizhzhia-nuclear-plant-but-combat-around-spent-fuel-still-poses-a-threat-190516) [snippet]. The fetched text of the same article also says an operating reactor without cooling would melt down and "set off a catastrophic chain reaction". That is an inaccurate phrase: melted fuel does not cause a nuclear explosion. Do not repeat it.
- "Dirty bomb" framing for the pools and casks — [The Conversation, 2023](https://theconversation.com/the-zaporizhzhia-nuclear-power-plant-is-a-dirty-bomb-waiting-to-happen-a-nuclear-expert-explains-209236)
- The IAEA's point that cold shutdown leaves more time ("considerably longer before fuel could be damaged or potentially melt") — see §3, [Update 365](https://www.iaea.org/newscenter/pressreleases/update-365-iaea-director-general-statement-on-situation-in-ukraine) [snippet]
- Grossi on the blackouts in September 2025: "deeply concerning", and they "pose a real risk to nuclear safety and increase the likelihood of a nuclear accident" — [NucNet](https://www.nucnet.org/news/zaporizhzhia-plant-suffers-fresh-blackout-emergency-generators-activated-9-3-2025). In August 2026: "deeply concerning and clearly not sustainable"; "With each new day of the conflict, the risks to nuclear safety and security are not decreasing, on the contrary" — [WNN](https://world-nuclear-news.org/articles/water-levels-to-be-increased-in-zaporizhzhias-used-fuel-ponds)
- Hot shutdown, as in 2022–April 2024, raised the risk because hot reactors melt faster after cooling fails — [IEEE Spectrum](https://spectrum.ieee.org/amp/zaporizhzhia-nuclear-power-plant-2671872736). A Substack estimate of "meltdown in less than 24 h" in hot shutdown — [malcontentnews](https://malcontentnews.substack.com/p/ukraines-zaporizhzhia-nuclear-power) [snippet; low-quality source, not for citation]
- Equipment ageing in long shutdown:
  - The coolant can fall below 35 °C, which raises the loads on pipes and steam-generator tubes.
  - Boric acid crystallises in the circuits.
  - Steam-generator leaks in half the units.
  - Former IAEA safety official Aybars Gürpinar warns that pumping groundwater could cause settlement, tilting buildings and possibly jamming control rods. Rosatom says no subsidence has been observed.
  — [IEEE Spectrum, May 2025](https://spectrum.ieee.org/amp/zaporizhzhia-nuclear-power-plant-2671872736)
- Staff fell from about 11,500 to about 3,000–4,500 — [OECD-NEA](https://oecd-nea.org/jcms/pl_66130/ukraine-current-status-of-nuclear-power-installations)
- **Grid-switch thesis:** Bellona asks whether the 2025 blackout was a step towards reconnecting the plant to Russia's grid. Russia reportedly told the IAEA in June 2025, by diplomatic note, that it had such a plan — [Bellona, 2 Oct 2025](https://bellona.org/news/nuclear-issues/2025-10-is-the-zaporizhzhia-nuclear-plants-longest-blackout-a-scheme-for-russia-to-siphon-off-its-power) [estimate, citing the IAEA]
- **Fukushima comparison** (general physics, no single URL fetched): in March 2011, Units 1–3 lost all AC power within about an hour of scramming from full power, with decay heat at about 1–1.5% of full power. The cores melted within hours to about three days. The Unit 4 pool, with fuel offloaded months earlier, was the great worry but did not boil dry — [Wikipedia, Fukushima Daiichi Units 4–6](https://en.wikipedia.org/wiki/Fukushima_Daiichi_units_4,_5_and_6) [snippet]

### Inferences
- For narration, lines like these are accurate and confident:
  - "Years into cold shutdown the reactors give off a few hundred kilowatts of heat each, not thousands of megawatts. A blackout today would not mean a meltdown within hours. It would start a countdown measured in days to weeks."
  - "The danger is in the sequence: the last line lost, then the diesels, then the fuel for them."
- Avoid saying "the power stops a meltdown" as if it were imminent. Better: "outside power is the first line of defence; every time it is cut the plant falls back on its last".
- The Hum and the film's "silence during complete losses" are true to the physics: the plant does not stop, but it falls to a narrower, more fragile layer of safety.

### Gaps
- I did not reach the current statements of Edwin Lyman/UCS or of SNRIU on the 2025–26 risk. Only Lyman's early-war "day or two" for the pools and his 2023 note on Unit 5 were found.
- I found no peer-reviewed paper (Nuclear Engineering and Design, Science & Global Security) with a ZNPP-specific heat-up calculation in this session.

---

## 6. Cooling water after the Kakhovka dam

### Takeaway
After the dam was destroyed on 6 June 2023, the plant lost its supply from the reservoir. It now cools its shut-down units from **11 groundwater wells (about 250 m³/h)** feeding the sprinkler ponds, with the large cooling pond in reserve. The pond's level has fallen from 16.7 m to about 13.5 m (August 2025). That is enough for cold shutdown. A restart would need water at a scale of tens of thousands of m³/h. The IAEA says there is "no way" to restart without a new water supply, and Rosatom has started a floating pumping station of up to 80,000 m³/h.

### Cited Findings
- 6 Jun 2023: onsite backup water was estimated as "sufficient for up to several months" — [OECD-NEA](https://oecd-nea.org/jcms/pl_66130/ukraine-current-status-of-nuclear-power-installations)
- July 2023: the levels of the pond and discharge channel were "relatively stable", falling 1–2 cm a day — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
- **Wells:**
  - 22 Aug 2023: the first well supplied about 20 m³/h.
  - 15 Sep 2023: nine wells supplied about 200 m³/h.
  — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
  - 29 Sep 2023: an eleventh well brought supply to about 250 m³/h, the rate needed to keep the sprinkler ponds up for the reactors and pools — [OECD-NEA](https://oecd-nea.org/jcms/pl_66130/ukraine-current-status-of-nuclear-power-installations)
- **Pond level (Baltic metres):**
  - 15.61 m (8 Apr 2024)
  - 14.34 m (23 Sep 2024)
  - 14.11 m (22 Mar 2025)
  - 13.54 m (11 Aug 2025), "over 3.2 metres lower" than before the dam was destroyed. The pond would become the main source only if the wells failed.
  — [OECD-NEA](https://oecd-nea.org/jcms/pl_66130/ukraine-current-status-of-nuclear-power-installations)
- Late Aug 2025: the IAEA was refused access to a dam that holds the service-water channel at about 14 m, roughly 2 m above the pumps' cut-off — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
- **Restart water:**
  - The IAEA calls the wells an interim fix. A restart needs water pumped from the Dnipro. The plant told the IAEA of a pumping station to feed the pond from the Dnipro, location undecided, to be built after the fighting ends — [IAEA Update 296](https://www.iaea.org/newscenter/pressreleases/update-296-iaea-director-general-statement-on-situation-in-ukraine) [snippet]; [Reuters via Yahoo, "No way to restart … at present"](https://www.yahoo.com/news/no-way-restart-zaporizhzhia-nuclear-150202866.html) [snippet]
  - Rosatom's Likhachev said construction had begun on a floating modular pumping station of up to 80,000 m³/h, with a phased restart only once military threats are removed — [WNN](https://www.world-nuclear-news.org/articles/zaporizhzhia-security-restart-and-us-fuel-discussed-in-iaea-russian-talks) [operator; snippet]
  - Rosatom's ZNPP director Chernichuk: restart produces "thousands of times as much heat", so cooling water comes first, and Rosatom plans to use the Dnipro — [IEEE Spectrum](https://spectrum.ieee.org/amp/zaporizhzhia-nuclear-power-plant-2671872736) [operator]
- Greenpeace: running reactors needs far more water than the pond holds — [Greenpeace Ukraine](https://www.greenpeace.org/ukraine/en/news/3301/greenpeace-urges-iaea-to-prevent-russian-restart-of-zaporizhzhia-reactors/) [advocacy]
- June 2023: the IAEA encouraged installing an external boiler so that all units could go to cold shutdown, in place of heating Enerhodar with reactor steam — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)

### Inferences
- 250 m³/h for cold shutdown against an 80,000 m³/h pumping station for a restart is a ratio of about 300×. It is a simple, sourced way to show that "keeping it safe" and "running it" are different worlds. It also ties the plant's future to the drained reservoir the film flies over.

### Gaps
- No IAEA statement after early 2025 on the pumping station's progress or on water enough for one unit was found. Pond levels after August 2025 were not found.

---

## 7. Russia's restart plans and licences, and what a restart would change

### Takeaway
Rostekhnadzor has issued Russian licences:
- dry storage, 22 Oct 2025, 25 years;
- Unit 1, December 2025, 10 years;
- Unit 2, 18 Feb 2026, 10 years.

Unit 6 has been applied for, and Units 3–5 are planned for application by the end of 2026. Rosatom names Units 2 and 6 as the first to restart, with all six licensed by 2027, but says there will be no restart while the conflict lasts. Ukraine and the IAEA reject a restart under occupation. A restart would multiply the heat several thousand times and bring back the hours-scale margins, and it would require high-voltage export lines, presumably into the Russian-controlled grid.

### Cited Findings
- **Licences:**
  - Unit 1, ten-year operating licence, December 2025 — [Interfax](https://interfax.com/newsroom/top-stories/115419/); [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
  - Unit 2, 18 Feb 2026 — [WNN](https://www.world-nuclear-news.org/articles/russian-regulator-issues-operating-licence-for-second-zaporizhzhia-unit); [Interfax](https://interfax.com/newsroom/top-stories/116233/)
  - Dry storage, 22 Oct 2025 (25 years) — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
- Rostekhnadzor completed a two-week pre-licensing inspection on 20 June 2025 — [OECD-NEA](https://oecd-nea.org/jcms/pl_66130/ukraine-current-status-of-nuclear-power-installations)
- Unit 6 has been applied for, and Units 3, 4 and 5 are to be applied for by the end of 2026. Ukrainian permits issued before 30 Sept 2022 stay valid until replaced, with full compliance with Russian rules due by 2028 — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
- **Timeline claims:**
  - 4 Apr 2025: the Russian-appointed director said all six would hold Russian licences by end-2027, with Units 2 and 6 restarting first. Energoatom called a restart technically impossible in the plant's state.
  - Jan 2025: a restart depends on hostilities ending and on security guarantees.
  - Feb 2026: Rosatom says no restart while the conflict continues.
  — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy) [operator]
- Likhachev, on the Unit 1 licence: it "allows us to consider the resumption of electricity generation in the future", which "will require the unconditional fulfillment of all safety and security conditions" — [Nuklearna Perspektiva, 25 Dec 2025](https://nuklearnaperspektiva.com/index.php/2025/12/25/zaporizhzhia-nuclear-power-plant-receives-russian-operating-license-unit-1-ready-for-ten-year-operation/) [operator]
- Energoatom: by restarting a unit Russia "risks nuclear catastrophe" — [Energoatom](https://energoatom.com.ua/en/news/perezapuskom-energobloka-zaporizkoyi-aes-rosiia-stvoriuje-rizik-iadernoyi-katastrofi) [operator]
- The IAEA and Rosatom agree a restart is "impossible … under current conditions" — [Greenpeace Ukraine](https://www.greenpeace.org/ukraine/en/news/1319/iaea-and-rosatom-agree-restart-of-zaporizhzhia-nuclear-plant-impossible-under-current-conditions-russian-nuclear-blackmail-continues-says-greenpeace-cee/) [snippet; advocacy reporting the IAEA]
- A restart would take new steam generators (over $1 bn per unit, made only in Russia), sanctioned Western equipment, licensing, staff and grid links. Balakan, former adviser to Energoatom: at best a year for one unit, even under full Ukrainian control — [IEEE Spectrum](https://spectrum.ieee.org/amp/zaporizhzhia-nuclear-power-plant-2671872736)
- The restart path also needs the transmission lines expanded — [Bellona](https://bellona.org/news/nuclear-issues/2025-10-is-the-zaporizhzhia-nuclear-plants-longest-blackout-a-scheme-for-russia-to-siphon-off-its-power)

### Inferences
- What a restart changes in physics:
  - Heat per core goes from under 1 MW to about 3,000 MWt.
  - Decay heat after any trip goes back to tens of MW.
  - The time to fuel damage after losing cooling falls from weeks back to hours.
  - Cooling water needed rises by about 300× (§6).
  - The power lines would again carry about 1 GW per unit out of the plant, into whichever grid they connect to.
- That is why "hostage" applies to both directions of the lines: in, for safety, today; out, for value, if Russia restarts.

### Gaps
- No confirmation found of a licence for Unit 6 or of any restart activity after February 2026 (as of 29 Oct 2026).

---

## 8. Glossary (for narration)

### Takeaway
Short, accurate definitions. The IAEA's "seven pillars" (2022) and "five principles" (2023) are the official frame for the plant's safety in war.

### Cited Findings
- **Cold shutdown:** reactor subcritical (control rods in, boron in the coolant), the coolant system at atmospheric pressure and below 93 °C (200 °F; NRC definition). On VVER practice the threshold is usually below about 70 °C (unverified here) — [Meshkati](https://theconversation.com/cold-shutdown-reduces-risk-of-disaster-at-zaporizhzhia-nuclear-plant-but-combat-around-spent-fuel-still-poses-a-threat-190516)
- **Hot shutdown:** reactor subcritical but the primary circuit kept hot and pressurised (about 260–280 °C on a VVER; my figure, not from a source read here). At ZNPP it was used to make steam for Enerhodar's heating and for processing radioactive waste — [WNA](https://world-nuclear.org/information-library/country-profiles/countries-t-z/ukraine-russia-war-and-nuclear-energy)
- **Decay (residual) heat:** heat from the radioactive decay of fission products after fission stops. It is about 6–7% of full power at the moment of shutdown, about 1% after hours, and falls to fractions of a per mille after years (textbook; see the §3 inferences). At ZNPP it is now under 0.8 MW per core (Bellona estimate) — [Bellona](https://bellona.org/news/nuclear-issues/2025-10-is-the-zaporizhzhia-nuclear-plants-longest-blackout-a-scheme-for-russia-to-siphon-off-its-power)
- **Loss of off-site power (LOOP):** all grid connections lost. The plant's on-site sources (diesels) take over. The IAEA counted 26 complete losses at ZNPP by 20 Aug 2026 — [OECD-NEA](https://oecd-nea.org/jcms/pl_66130/ukraine-current-status-of-nuclear-power-installations)
- **Station blackout (SBO):** loss of off-site power *and* of the on-site emergency AC sources (diesels), leaving only batteries. It is what Grossi warned of in August–September 2026 "within days" — [Al Jazeera](https://www.aljazeera.com/news/2026/8/29/ukrainian-nuclear-power-plant-without-external-power-for-over-a-week); [Armscontrol.org](https://www.armscontrol.org/act/2026-09/news/outages-rising-zaporizhzhia-power-plant) [snippet]
- **Defence in depth:** independent, layered safety provisions (grid lines, then diesels, then mobile diesels and pumps, then water inventory, then containment), so that no single failure leads to harm. Standard IAEA concept; I did not fetch an IAEA URL for it in this session.
- **The IAEA's seven pillars (2022)** — [GlobalSecurity, IAEA text, 7 Sept 2022](https://www.globalsecurity.org/wmd/library/news/ukraine/2022/09/ukraine-220907-iaea02.htm); [NEI Magazine](https://www.neimagazine.com/news/iaea-issues-report-on-zaporozhzhia-and-addresses-un-security-council-9988384/) [snippet]:
  1. physical integrity of the facilities;
  2. safety and security systems working;
  3. staff able to work without undue pressure;
  4. secure off-site power from the grid;
  5. uninterrupted logistics and supply chains;
  6. radiation monitoring and emergency preparedness;
  7. reliable communication with the regulator.
- **The IAEA's five principles for ZNPP** (Grossi to the UN Security Council, 30 May 2023) — [NEI Magazine, 1 June 2023](https://www.neimagazine.com/news/iaea-chief-unveils-vital-guidelines-to-prevent-nuclear-accident-at-zaporizhia-npp-10905039/):
  1. "There should be no attack of any kind from or against the plant" (reactors, spent fuel storage, infrastructure, staff);
  2. no heavy weapons or troops based there;
  3. "Off-site power to the plant should not be put at risk";
  4. essential systems "should be protected from attacks or acts of sabotage";
  5. no action that undermines these principles.
- The IAEA Support and Assistance Mission (ISAMZ) has been on site since 1 Sept 2022 — [NEI Magazine](https://www.neimagazine.com/news/iaea-chief-unveils-vital-guidelines-to-prevent-nuclear-accident-at-zaporizhia-npp-10905039/)

### Inferences
- Principle 3 and pillar 4 make the film's subject, the last two lines, one of the IAEA's own named conditions for safety, not only the film's metaphor.

### Gaps
- An IAEA primary URL for the defence-in-depth definition was not fetched. The VVER cold- and hot-shutdown temperatures are from general knowledge and should be checked before they are put on screen.
