# VIIRS Black Marble night lights for the ZNPP film: feasibility, honest use, pitfalls, alternatives

Researched 29 October 2026. Every claim has a URL. "(snippet)" marks a claim seen only in a search-result summary, not on a fetched page. "(CMR query)" marks facts from a small metadata query I ran against NASA's public CMR catalogue (no data downloaded). "(own calculation)" marks arithmetic I did, not a published figure.

## 1. The products, resolution, overpass, access and formats (which tile covers the site?)

### Takeaway
Black Marble is mature, free and well documented. The product a film needs is the monthly VNP46A3/VJ146A3 for trends and the daily VNP46A2/VJ146A2 for single nights. All of them come as HDF5 tiles of 10° x 10° at 15 arc-seconds (about 310 m E-W x 463 m N-S at 47.5° N), and **one tile, h21v04 (40–50° N, 30–40° E), covers every city on the list.** Access needs a free Earthdata token; Google Earth Engine also carries the daily product. **Urgent: delivery of new Suomi NPP (VNP46) data ends on 1 November 2026, three days from now.** Anything after that date has to come from NOAA-20 (VJ146).

### Cited Findings
**Product suite and versions**
- Suite: VNP46A1 (daily at-sensor top-of-atmosphere radiance, 26 layers including radiance, solar, lunar and sensor angles, cloud mask, moon phase and illumination fraction); VNP46A2 (daily moonlight-adjusted NTL); VNP46A3 (monthly) and VNP46A4 (yearly) composites; the NOAA-20/JPSS-1 equivalents are VJ146A1–A4. Data start January 2012 for SNPP and January 2018 for NOAA-20. — [Black Marble User Guide, Collection 2.0, Oct 2024](https://www.earthdata.nasa.gov/s3fs-public/2025-05/BlackMarbleUserGuide_Collection2.0.pdf)
- VNP46 runs from 19 January 2012 and VJ146 from 5 January 2018. VJ246 (NOAA-21) is "in development". "As of Aug. 25, 2025, VNP and VJ1 are Collection 2. Collection 1 processing has been terminated." Near-real-time products are delivered "within a three-hour window". The format is HDF-EOS5. — [NASA Earthdata, Black Marble project page](https://www.earthdata.nasa.gov/data/projects/black-marble)
- **Suomi NPP end:** the Black Marble page says "Delivery of new Suomi NPP data ceases on Nov. 2, 2026. Users should transition to alternative products." — [NASA Earthdata, Black Marble](https://www.earthdata.nasa.gov/data/projects/black-marble). A separate Earthdata alert gives **13:00 UTC on 1 November 2026**, announced by NOAA NESDIS on 3 August 2026, "subject to change", and points users to NOAA-20/NOAA-21. — [Earthdata alert (snippet)](https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-data-product-delivery-cease-november-1-2026). The two NASA pages differ by a day.
- The algorithm corrects for atmosphere, terrain, lunar BRDF, thermal and stray light. — [User Guide C2.0](https://www.earthdata.nasa.gov/s3fs-public/2025-05/BlackMarbleUserGuide_Collection2.0.pdf)

**Resolution and grid**
- Grid: 15 arc-second linear lat/lon. Tiles are "approximately 10°×10°". Filename convention: `VNP46A1.A2018001.h08v05.002.2023184124809.h5` = product, acquisition date (A-YYYYDDD), tile hXXvYY, collection 002, production date, HDF5. — [User Guide C2.0](https://www.earthdata.nasa.gov/s3fs-public/2025-05/BlackMarbleUserGuide_Collection2.0.pdf)
- The underlying DNB pixel is 750 m. The guide's key performance metrics give spatial resolution as 742 m (threshold) and 500 m (breakthrough), geolocation uncertainty 133 m / 50 m / 20 m (threshold / breakthrough / goal), detection limit Lmin 3.0 / 0.5 / 0.25 nW·cm⁻²·sr⁻¹, and stray-light error 0.45 / 0.25 / <0.1 nW·cm⁻²·sr⁻¹. — [User Guide C2.0, Table 14](https://www.earthdata.nasa.gov/s3fs-public/2025-05/BlackMarbleUserGuide_Collection2.0.pdf); [Earthdata Black Marble page ("750 m")](https://www.earthdata.nasa.gov/data/projects/black-marble)
- Earth Engine lists `NASA/VIIRS/002/VNP46A2` at 500 m, daily, 2012-01-19 to 2026-10-25. Bands: DNB_BRDF_Corrected_NTL, Gap_Filled_DNB_BRDF_Corrected_NTL, DNB_Lunar_Irradiance, Latest_High_Quality_Retrieval, Mandatory_Quality_Flag, Snow_Flag, QF_Cloud_Mask (bitmask: cloud confidence in bits 6–7, snow/ice in bit 10, etc.). — [Google Earth Engine catalog, VNP46A2](https://developers.google.com/earth-engine/datasets/catalog/NASA_VIIRS_002_VNP46A2)
- **Tile h21v04 covers the site** (CMR query, 29 Oct 2026): every Black Marble granule found for the point 47.5° N, 34.6° E is tile h21v04, with polygon 40–50° N, 30–40° E. That box includes Kryvyi Rih (about 33.4° E) and Dnipro (about 35.0° E). The latest granules on 29 Oct 2026 were VNP46A1 25 Oct 2026 (38.4 MB); VNP46A2 18 Oct 2026 (23.7 MB); VJ146A2 19 Oct 2026 (27.4 MB); VNP46A3 and VJ146A3 September 2026 (75.2 MB and 69.5 MB); VNP46A4 and VJ146A4 year 2025 (114.4 MB and 108.5 MB). Example: `VJ146A3.A2026244.h21v04.002.2026291120146.h5` at `https://data.laadsdaac.earthdatacloud.nasa.gov/prod-lads/VJ146A3/...` — [NASA CMR granule search (CMR query)](https://cmr.earthdata.nasa.gov/search/granules.json?short_name=VJ146A3&version=2&point=34.6,47.5&sort_key=-start_date&page_size=2)
- The guide's own example metadata confirms the vertical numbering: a v04 tile has NorthBoundingCoord = 50. — [User Guide C2.0](https://www.earthdata.nasa.gov/s3fs-public/2025-05/BlackMarbleUserGuide_Collection2.0.pdf)

**Overpass time**
- Suomi NPP's VIIRS passes over any location at roughly 01:30 and 13:30 local time. — [NASA Earth Observatory, "Into the Black" (snippet)](https://earthobservatory.nasa.gov/features/IntotheBlack/page3.php); [SSEC UW-Madison (snippet)](https://www.ssec.wisc.edu/media/fromorbit/december2012/page1.html)

**Quality flags (Collection 2)**
- VNP46A2 Mandatory_Quality_Flag: 0 high quality; 1 poor (outlier, possible cloud); **2 poor (high solar zenith angle 102–108°)**; 3 lunar eclipse; 4 aurora; 5 glint; 255 no retrieval. Fill values occur when the solar zenith angle is below 102°, "the nighttime cut-off used in the code". Snow_Flag: 0 no snow/ice, 1 snow/ice. — [User Guide C2.0, Tables 9–10](https://www.earthdata.nasa.gov/s3fs-public/2025-05/BlackMarbleUserGuide_Collection2.0.pdf). Earth Engine's page still lists the older 0/1/2/255 flag meanings. — [GEE catalog](https://developers.google.com/earth-engine/datasets/catalog/NASA_VIIRS_002_VNP46A2)
- **Gap-filling:** when the gap-filling routine is used, the Latest_High_Quality_Retrieval layer reports how many days old the last good observation is (0–254 days). — [User Guide C2.0](https://www.earthdata.nasa.gov/s3fs-public/2025-05/BlackMarbleUserGuide_Collection2.0.pdf)
- **Monthly and yearly composites (A3/A4):** built from daily corrected radiance. Outliers outside Q1−1.5·IQR to Q3+1.5·IQR are dropped, and the rest averaged. Composite values below 0.5 nW·cm⁻²·sr⁻¹ are set to zero. There are 28 layers: composites, counts, quality and standard deviation for near-nadir (view zenith 0–20°), off-nadir (40–60°) and all angles, each for snow-free and snow-covered periods. "Artificial lights derived from VIIRS DNB data show a strong angular effect … particularly across dense urban centers where NTL radiance at nadir can be significantly higher than off-nadir." — [User Guide C2.0](https://www.earthdata.nasa.gov/s3fs-public/2025-05/BlackMarbleUserGuide_Collection2.0.pdf)
- Monthly quality flags (as documented by the World Bank R package): 0 good, more than 3 observations; 1 poor, 3 or fewer observations; 2 gap-filled from historical data. — [blackmarbler R manual (snippet)](https://worldbank.r-universe.dev/blackmarbler/doc/manual.html)

**Access tools**
- blackmarblepy (World Bank, MIT plus World Bank IGO Rider): `pip install blackmarblepy`. It needs a NASA Earthdata personal access token (env `BLACKMARBLE_TOKEN` or `token=`). It downloads HDF5 tiles, mosaics them, georeferences them and returns an `xarray.Dataset`. Example: `bm.raster(gdf, product_id=Product.VNP46A2, date_range=...)`. It also does zonal statistics (exactextract) and plots. — [GitHub worldbank/blackmarblepy](https://github.com/worldbank/blackmarblepy)
- R twin blackmarbler documents VNP46A1–A4 and a quality-flag removal option. — [blackmarbler docs](https://worldbank.github.io/blackmarbler/index.html); [World Bank Data Blog](https://blogs.worldbank.org/en/opendata/illuminating-insights-harnessing-nasas-black-marble-r-and-python-packages)

### Inferences
- **Pixel size at 47.5° N (own calculation):** 15″ = 1/240°. N-S ≈ 111.3 km / 240 ≈ 464 m; E-W ≈ 464 m x cos 47.5° ≈ 313 m. The underlying sensor footprint, though, is about 742 m, so the effective resolution is coarser than the grid. Two lit things less than about 1 km apart blur together.
- **Volume (own calculation):** monthly A3 for Jan 2021–Sep 2026 is about 69 tiles x 75 MB ≈ 5 GB. Daily A2 for the same period is about 2,100 x 24 MB ≈ 50 GB per satellite, all for one tile. Earth Engine avoids the download by doing the clipping server-side. For the pipeline, blackmarblepy with a small GeoDataFrame still downloads whole tiles.
- **Local time vs overpass (own calculation):** 01:30 local *solar* time at 34.6° E is about 23:10 UTC, which is 01:10 Kyiv winter time and 02:10 Kyiv summer time. Occupied Enerhodar runs on Moscow time (UTC+3 year-round), so the same pass is 02:10 on its clocks all year. NOAA-20 flies in the same orbit about 50 minutes apart from SNPP, so its pass falls at a different time of night. (The 50-minute offset is not verified this session; check it before relying on it.)
- **Recommendation:** use VJ146 (NOAA-20) as the primary series. It runs through 2018–present and will continue after SNPP ends, so the film's series will not stop on 1 November 2026. SNPP can cross-check 2012–2017 history.

### Gaps
- Could not open the LAADS product pages (connection refused or timed out). Tile size in pixels (2400 x 2400) is not confirmed from a fetched page. It follows from 10° / 15″ = 2400.
- NOAA-20 vs SNPP exact local overpass offset not verified this session.

## 2. Pitfalls at 47.5° N and in wartime Ukraine

### Takeaway
The physical pitfalls (moon, cloud, snow, summer twilight, view angle, gap-filling) are all manageable with the quality layers. The human pitfalls are not: deliberate light-masking, curfews, energy-saving street-light cuts, rolling outages, flight from the area, and the occupation's separate grid all change the lights. The dimming is real, but it does not say why. The 01:30 overpass falls inside curfew and masking hours.

### Cited Findings
**Physical**
- NASA's Ukraine analysis lists moonlight, clouds, air pollution, snow cover, seasonal vegetation and satellite position as things that distort raw images. The team calibrates for them and filters non-electric stray light. — [NASA Earth Observatory, "Tracking Night Lights in Ukraine", 30 Jun 2022](https://science.nasa.gov/earth/earth-observatory/tracking-night-lights-in-ukraine-150002)
- Colorado School of Mines EOG's nightly war imagery had to adjust colour stretches on 17 March 2022 "to reduce the effect of moonlit terrain". Cloud blocked or diffused city lights on many nights. Brovary's glow on 24 Feb was attributed to light scattered by clouds. A reported Chornobyl NPP loss of power on 9 March 2022 "could not be confirmed because of thick cloud". — [EOG, Russia-Ukraine War as Seen by DNB](https://eogdata.mines.edu/products/special_topics/russia_ukraine_war.html)
- Independent analyst: "lots of clouds, and light from the Moon causes some images to be much brighter than others". Flickering lights are probably fires or military activity (his guess). — [Christopher Wolfram, Nighttime Lights in Ukraine (snippet)](https://christopherwolfram.com/projects/ukraine-nightlights/)
- Snow raises surface reflectance and scatters light, so the composites are split into snow-free and snow-covered layers. — [User Guide C2.0](https://www.earthdata.nasa.gov/s3fs-public/2025-05/BlackMarbleUserGuide_Collection2.0.pdf)
- **Summer twilight:** Collection 2 discards solar zenith below 102° and flags 102–108° as poor quality (flag 2). — [User Guide C2.0](https://www.earthdata.nasa.gov/s3fs-public/2025-05/BlackMarbleUserGuide_Collection2.0.pdf). A NASA forum answer about VNP46A2 said filtering at SZA < 108° "might result in black outs in high latitude regions during summer solstice". — [Earthdata Forum (snippet; page unreachable)](https://forum.earthdata.nasa.gov/viewtopic.php?p=13116)
- **Gap-filled radiance may be stale:** gap-filled pixels carry the last good value, and their age is in Latest_High_Quality_Retrieval (up to 254 days). — [User Guide C2.0](https://www.earthdata.nasa.gov/s3fs-public/2025-05/BlackMarbleUserGuide_Collection2.0.pdf)
- Angular effect: dense urban cores look brighter at nadir than off-nadir, so comparisons between nights need the same angle class. — [User Guide C2.0](https://www.earthdata.nasa.gov/s3fs-public/2025-05/BlackMarbleUserGuide_Collection2.0.pdf)

**Human / wartime**
- NASA: "Many areas remain dark, which may reflect a lack of power or deliberate choices to keep lights off"; some outdoor lighting "intentionally dimmed, removed, or shut off". — [NASA Earth Observatory 2022](https://science.nasa.gov/earth/earth-observatory/tracking-night-lights-in-ukraine-150002)
- **Nikopol** has been under a "full blackout" (повне затемнення) regime since 13 December 2023. All outdoor lighting is off. Indoor light is allowed only if masked (dense curtains, shutters). The regime also covers five other communities. Announced by Nikopol city council. — [ZN.ua, 18 Dec 2023](https://zn.ua/war/v-nikopole-vveli-rezhim-polnoho-zatmenija.html)
- Kharkiv had little or no street lighting for over a year until March 2023. Kyiv minimised evening street lighting from October 2022 for energy saving and masked its centre and strategic sites. Chernivtsi switched street lights off from 00:00 to 04:00 during curfew. — [Gwara Media](https://gwaramedia.com/en/kharkiv-to-light-streets-for-the-first-time-since-invasion/); [Hromadske](https://hromadske.ua/en/posts/dark-times-how-kyiv-lives-with-lights-off-photos); [UNN](https://unn.com.ua/en/news/street-lighting-will-be-cut-off-in-chernivtsi-due-to-russian-attacks) (all snippet)
- NPR / Payne Institute (April 2025): the dimming combines streetlights turned off, power plants destroyed, and people leaving. The data shown do not separate these causes. — [Payne Institute repost of NPR, 5 Apr 2025](https://payneinstitute.mines.edu/?p=38041); [NPR](https://www.npr.org/2025/04/05/nx-s1-5299206/ukraine-war-night-darkness)
- Bloomberg 2025: many cities have regained some night-light intensity, but residents may keep lights off for fear of attack. — [Bloomberg graphics (snippet)](https://www.bloomberg.com/graphics/2025-ukraine-rebuilds-energy-grid-as-russia-war-continues/)
- **Nikopol district's own outages:** strikes on 5 August (year per article) cut power to nearly 55,000 customers in the Nikopol area. Marhanets was among the communities hit. — [Censor.net (snippet)](https://censor.net/en/news/4017059/russian-attacks-leave-55-000-customers-without-power-in-nikopol-district). Shelling repeatedly destroyed Nikopol's and Marhanets's power lines, e.g. 6 Dec 2022. — [Ukrainska Pravda](https://www.pravda.com.ua/eng/news/2022/12/06/7379447/); [Ukrinform (snippet)](https://ukrinform.net/rubric-ato/3646671-russians-shell-marhanets-with-grad-mlrs-power-line-damaged.html)

### Inferences
- **Summer at 47.5° N (own calculation, spherical sun geometry):** at 01:30 local solar time the solar zenith angle stays above 108° from mid-July to late May. From about 30 May to 14 July it falls to 106–108°. Those near-nadir pixels are retrieved but flagged 2 (poor), never filled. The Collection 1 "<108° → blackout" caveat is therefore softened in Collection 2: summer data exist, but the user guide marks them poor quality. Off-nadir pixels are seen up to about an hour later in local solar time. At 02:30 the SZA drops below 102° from 8 June to 4 July, so some off-nadir pixels are filled. **Practical rule: don't build any claim on June–July single nights; treat June–July monthly composites as weaker.**
- **The dam night, 6 June 2023:** the SNPP pass at about 02:10 Kyiv summer time comes before the breach reported for about 02:50 local (breach time from the project's own record, not checked here). SZA is about 107° (flag 2). The dam's own lights were presumably masked in wartime. **VIIRS is very unlikely to show anything about the dam's destruction that night.** The drained reservoir is better shown by Sentinel-2, which the film already does.
- **Use DNB_BRDF-Corrected_NTL with Mandatory_Quality_Flag = 0 and a clear cloud mask, never the gap-filled layer, for any dated event.** A gap-filled pixel on a cloudy night after a blackout can show the lights from before it.
- **01:30 is the darkest hour of wartime policy:** curfews (typically 23:00/00:00–05:00) and light-masking regimes are in force at the overpass. In Ukrainian-held towns, VIIRS at 01:30 measures masking discipline and population at least as much as power supply. Nikopol's full blackout since December 2023 makes it **unusable as an indicator of grid supply**.

### Gaps
- No source found for the exact curfew hours in Nikopol, Marhanets or Zaporizhzhia city over time, or for when masking began there (Nikopol's order dated Dec 2023 is the only one found).
- No source found on the occupation authorities' street-lighting or masking policy in Enerhodar or Kamianka-Dniprovska.

## 3. Can a change in lights be attributed to the ZNPP's capture or to cuts of its lines?

### Takeaway
**No, not directly, and no published analysis tries to.** Cities draw power from the wider grid, not from the plant. The ZNPP's line cuts are about the plant *receiving* off-site power for its own safety systems; it has generated nothing for the grid since September 2022. The one place where the plant and local lights are tied is **Enerhodar**: its electricity, water and district heat depended on the plant, the TPP and local substations. The documented events there (6–7 Sept 2022, the 2022 heating crisis) are candidates for a dated before/after, but nobody has published that measurement.

### Cited Findings
- The ZNPP stopped producing electricity for the grid in September 2022. Its reactors went to hot shutdown to make steam for the site and **district heating for Enerhodar**, "where many plant staff live" (IAEA via search). Later reports say Enerhodar was heated in the 2024–25 season without any unit in hot shutdown. — [IAEA (snippet)](https://www.iaea.org/node/129727); [NEI Magazine, "Energodar faces winter without ZNPP" (snippet)](https://www.neimagazine.com/news/energodar-faces-winter-without-znpp/)
- **6 Sept 2022:** after an explosion "electricity and water supply disappeared simultaneously in Enerhodar" (Mayor Dmytro Orlov, in exile). **7 Sept 2022:** shelling damaged the Luch substation; 1–2 neighbourhoods of Enerhodar remained without electricity. — [Euromaidan Press, 7 Sep 2022](https://euromaidanpress.com/2022/09/07/blackout-in-enerhodar-city-zaporizhzhia-obl-after-russias-recent-shelling-enerhodar-mayor/); [Ukrainska Pravda, 7 Sep 2022](https://www.pravda.com.ua/eng/news/2022/09/07/7366411/)
- Oct–Nov 2022: Ukrainian officials warned Enerhodar faced winter without heating. On 2 Nov 2022 a Ukrainian outlet reported the plant had restored heat. On 3 Nov a Russian-side report said heating stopped because of a power outage on the Ukrainian side. The two sides' accounts conflict. — [Ukrainska Pravda, 2 Nov 2022](https://www.pravda.com.ua/eng/news/2022/11/02/7374641/); [Interfax, 3 Nov 2022 (snippet)](https://interfax.com/newsroom/top-stories/84590/); [Ukrainska Pravda, 23 Oct 2022 (snippet)](https://www.pravda.com.ua/eng/news/2022/10/23/7373135)
- Later outages in occupied Enerhodar from drone strikes are reported, e.g. [bluewin (snippet)](https://www.bluewin.ch/en/news/international/occupied-enerhodar-without-electricity-after-kiev-drone-strikes-li.2415929), [NV (snippet)](https://english.nv.ua/nation/enerhodar-explosion-reported-during-ukraine-war-50268365.html).
- Greenpeace Ukraine with McKenzie Intelligence Services used daytime satellite imagery of the lines (not night lights). They found no sign of major damage to the 750 kV line. They also report Russian construction of about 201 km of new grid lines since December 2024, and that damage blamed on a 4 June (2026) drone attack on the Ferosplavna 330 kV line was already there before. Advocacy-linked; Russia disputes it. — [Greenpeace Ukraine](https://www.greenpeace.org/ukraine/en/news/4460/the-750-kv-power-line-at-zaporizhzhya-nuclear-power-plant-shows-no-signs-of-major-damage-new-satellite-investigation-by-greenpeace/); [Al Jazeera, 17 Sep 2026](https://www.aljazeera.com/news/2026/9/17/russia-sabotaging-power-supply-lines-at-zaporizhzhia-plant-greenpeace)
- Night-light studies attribute dimming to a mix of causes they cannot separate: masking, grid damage and population loss. — [Payne/NPR 2025](https://payneinstitute.mines.edu/?p=38041); [NASA EO 2022](https://science.nasa.gov/earth/earth-observatory/tracking-night-lights-in-ukraine-150002)

### Inferences
- **Nikopol / Marhanets** (Ukrainian-held, across the water): their dark nights reflect nationwide strikes on generation and transmission, daily shelling of local lines, a formal full-blackout regime, and people leaving. The ZNPP's capture contributes only in the general sense that Ukraine lost about 6 GW of capacity. A line from "ZNPP line cut" to "Nikopol dark" would be false causality.
- **Enerhodar** is the only town where a link to the plant is physically plausible. It sits about 3–5 km from the plant, is fed through the TPP/ZNPP switchyards and local substations, and got its heat from the plant. Even there, VIIRS cannot tell a substation hit from a plant event, and occupation lighting policy is unknown.
- What can honestly be said is co-occurrence, not cause: "On the nights when the IAEA reported the plant cut off, Enerhodar's lights were X". That works only if the specific night was clear, moonless or corrected, flag 0, and not gap-filled. Most of the plant's complete losses of off-site power lasted hours and could fall between overpasses; only those spanning about 01:30 local could show at all.

### Gaps
- No published measurement of Enerhodar's night lights around 6–7 Sept 2022 or any complete loss of off-site power. **A test is cheap:** VNP46A2 h21v04 for 1–15 Sept 2022 is about 15 x 24 MB. Check flags first; early September has a short night and moonlight (full moon about 10 Sept 2022, not verified here).
- Which substations feed Enerhodar, and whether the town loses power when the ZNPP loses off-site power, is not established in sources found here.

## 4. Existing analyses of Ukraine's night lights in the war (any on Enerhodar, Nikopol, Zaporizhzhia or the ZNPP?)

### Takeaway
There is a large literature on national and oblast-level dimming and a newsroom tradition of before/after maps. **I found nothing that measures Enerhodar, Nikopol, Marhanets or the ZNPP site specifically.** The most relevant narrative finding is the occupied vs. Ukrainian-held contrast: through 2024 the occupied territories kept their lights, some brighter, while Ukrainian-held areas went dark. In July–August 2026 that reversed in the occupied south (Melitopol, Berdiansk, Crimea) after Ukrainian drone strikes on power nodes.

### Cited Findings
- NASA Earth Observatory (30 Jun 2022): Black Marble team (Ranjay Shrestha, GSFC), best cloud-free nights each month, Kyiv Jan/Mar/May 2022 composites. Lights fell sharply in March, then slowly recovered, especially round Kyiv. Eastern Ukraine kept losing lights. Zaporizhzhia not mentioned. — [NASA EO](https://science.nasa.gov/earth/earth-observatory/tracking-night-lights-in-ukraine-150002)
- EOG / Payne Institute (Colorado School of Mines): nightly DNB vs previous monthly cloud-free composite (red = lost, green = new, blue = cloud), 23 Feb–19 Mar 2022, Kyiv region plus country views of 25 Feb and 5 Mar 2022. VIIRS Nightfire used for fires from 7 Mar. Nothing on the south. — [EOG war page](https://eogdata.mines.edu/products/special_topics/russia_ukraine_war.html); [CNN, 3 Mar 2022](https://edition.cnn.com/interactive/2022/03/world/ukraine-satellite-images)
- Elvidge et al. (EOG, Jan 2023) compared Sep/Oct/Nov 2022 VIIRS: "most of the 2021 lighting features have been lost in the Ukraine in 2022", with lights left in central Kyiv and Lviv. — [Mines repository (snippet)](https://repository.mines.edu/server/api/core/bitstreams/88143434-8e44-45c0-9f6c-8082c2797bf4/content)
- Zhizhin, Elvidge, Ghosh, "Map of Darkness: How Nighttime Lights Trace the Impact of War in Ukraine" (ICA Abstracts 7, 2024), from the Payne study "Mapping of Dimmed Nighttime Lights in Ukraine During the War". Uses the 2021 VIIRS NTL to locate pre-war lights. Interactive map of dimming 2012–2023. — [ICA Abstracts](https://ica-abs.copernicus.org/articles/7/192/2024/); [Payne Institute](https://payneinstitute.mines.edu/?p=30568); [Payne, "Prolonged Dimming"](https://payneinstitute.mines.edu/?p=28172)
- Applied Sciences (Dec 2022), "Multi-Scale Dynamic Analysis of the Russian–Ukrainian Conflict from the Perspective of Night-Time Lights": more than 60% of city night lights lost. Lights recovered fastest in pro-Russian areas, then Russian-controlled areas, slowest in active-conflict areas. — [doi:10.3390/app122412998 (snippet)](https://doi.org/10.3390/app122412998)
- Huang et al., Frontiers in Environmental Science 11 (2023): lit area −53.97% and total DN −53.18% one week into the war, with a model linking NTL to UNHCR refugee counts. — [Frontiers, doi:10.3389/fenvs.2023.1055100](https://www.frontiersin.org/journals/environmental-science/articles/10.3389/fenvs.2023.1055100/text)
- Other: Kyiv light pixels −65.2% Feb→Mar 2022 (Eur. J. Remote Sensing 2024); about −56% national NTL intensity, Dec 2021–Apr 2022 (IEEE JSTARS 2024). — [DOAJ EJRS (snippet)](https://doaj.org/article/4cb272e639aa49ae8b689a604fb86e85); [DOAJ JSTARS (snippet)](https://doaj.org/article/412fdc02b60d48babbb39ea293acc731)
- **Texty.org.ua, 4 Sep 2026:** VIIRS NTL for July–August 2025 vs July–August 2026 (red = lost, blue = new). Blackouts in Melitopol, Berdiansk, Dzhankoi, Yevpatoria, Feodosia, Kerch and the southern Crimean coast, including villages and roads. Donetsk got brighter. It is "the first time since the full-scale invasion" that occupied territories have worse electricity than Ukrainian-controlled ones. The article recalls its 2024 analysis (2021 vs 2024): occupied areas had not lost lighting, some had brightened, while Ukrainian-held areas went dark. Linked to the USF's claim (22 Aug 2026) of 267 power nodes disabled since 1 July. **Enerhodar and the ZNPP are not mentioned.** — [Texty.org.ua](https://texty.org.ua/articles/118222/usf-disabled-267-power-nodes-in-occupied-territories-blackouts-visible-from-space/)
- Pre-war baseline: 2012→2019, the southern coasts of Odesa, Kherson and Zaporizhzhia oblasts were "flooded with light", and Melitopol modernised 86–87% of its street lights. — [Texty.org.ua, 23 Feb 2021](https://texty.org.ua/articles/105292/light-and-darkness-how-illumination-changed-during-war-free-ukraine-and-occupied-territories/)
- RFE/RL used night images to show the Donbas's depopulation. — [RFE/RL The Hub (snippet)](https://thehub.rferl.org/a/ukraine-war-russia-invasion-night-satellite-images-depopulation-donbas/33800934.html)
- November 2022 strikes: NASA Worldview imagery of the night of 23–24 Nov 2022 was widely published. — [TSN (snippet)](https://tsn.ua/en/amp/ato/ukraine-in-blackout-was-photographed-from-space-after-russian-strikes-2229334.html); [Babel (snippet)](https://babel.ua/en/news/87453-the-mass-media-published-satellite-images-of-the-blackout-in-ukraine-on-thursday-night). VoxUkraine fact-checked a fake "2025 blackout" satellite image as false (page returned 403; claim from snippet only). — [VoxUkraine (snippet)](https://voxukraine.org/en/false-a-satellite-image-of-ukraine-during-blackouts-in-2025)

### Inferences
- The occupied-vs-held contrast is documented by a reputable data newsroom (Texty) and fits the film's geography exactly: the left bank (Enerhodar, Kamianka-Dniprovska, Vasylivka) is occupied and the right bank (Nikopol, Marhanets) is held, across the drained reservoir. It is a contrast the film can **observe and attribute to sources** without claiming causes.
- The fake-image fact-check is a warning that night-light maps of Ukraine circulate falsely. Every frame needs product, date and processing on screen or in film.json.

### Gaps
- No analysis found of Enerhodar, Nikopol, Marhanets, Kamianka-Dniprovska or Vasylivka specifically. No NASA EO feature found specifically on the November 2022 strikes (only Worldview imagery reported in news).
- Could not retrieve the Li Xi / Román / Zhao papers named in the brief this session. The Applied Sciences 2022 paper is the closest found (authors not verified).

## 5. Can VIIRS see the ZNPP site itself dim during complete losses of off-site power?

### Takeaway
Almost certainly not reliably, and no analysis has attempted it. The site (about 1 x 1.5 km) is 2–3 effective DNB footprints. It sits next to the TPP and about 3–5 km from Enerhodar, so their light blends together. During a loss of off-site power, diesel generators carry the safety loads and some site lighting may stay on. Losses lasting hours rarely span the 01:30 pass. Any one night is also exposed to moon, cloud and flagging.

### Cited Findings
- Effective DNB resolution: 742 m threshold, 500 m breakthrough; geolocation uncertainty 133 m threshold. — [User Guide C2.0, Table 14](https://www.earthdata.nasa.gov/s3fs-public/2025-05/BlackMarbleUserGuide_Collection2.0.pdf)
- Detection limit 0.5–3.0 nW·cm⁻²·sr⁻¹ (breakthrough–threshold). Composites zero out anything below 0.5. — [User Guide C2.0](https://www.earthdata.nasa.gov/s3fs-public/2025-05/BlackMarbleUserGuide_Collection2.0.pdf)
- The only nuclear-site night-light check found: EOG flagged Chornobyl NPP's reported power loss on 9 March 2022 but "could not confirm" it because of thick cloud (restoration reported 10 March). — [EOG war page](https://eogdata.mines.edu/products/special_topics/russia_ukraine_war.html)
- During complete losses of off-site power the ZNPP runs on diesel generators. — [Liga.net (snippet)](https://biz.liga.net/en/energy/news/occupied-znpp-is-in-blackout-again-it-is-running-on-generators)

### Inferences
- A defensible test would use VNP46A2/VJ146A2 DNB_BRDF-Corrected_NTL, flag 0, clear cloud mask, snow-free, near-nadir. Compare the 3x3 pixels on the plant with a control (the TPP, Enerhodar) on loss nights against nights before and after. A null result is the likely outcome and is itself honest. The film could say "at this resolution the plant cannot be told apart from its town".
- **Recommendation: do not put "the plant went dark" on screen from VIIRS.** The project's own record of reported cuts is the right evidence for the plant's power state.

### Gaps
- No published attempt found. No source on how much of the site's outdoor lighting stays on during diesel operation.

## 6. Narrative value: what can the lights honestly tell, and what must be said on screen?

### Takeaway
Black Marble is worth a short sequence (well under a minute) as **context**, not as evidence about the plant. Honest stories it can carry, with sources:
1. **The country goes dark:** national dimming in March 2022 and winter 2022–23, from published analyses.
2. **Two banks:** the occupied left bank lit while the Ukrainian-held right bank stays dark, through 2024 (Texty), then the occupied south's own blackouts in summer 2026.
3. **Enerhodar**, the plant's town, as one dated close-up, if a clean night exists.

It cannot carry "the plant's line cuts darkened the cities".

### Cited Findings
- Darkness has many causes: masking, damage, depopulation. — [NASA EO 2022](https://science.nasa.gov/earth/earth-observatory/tracking-night-lights-in-ukraine-150002); [Payne/NPR 2025](https://payneinstitute.mines.edu/?p=38041)
- Nikopol's lights are switched off by order (full blackout since 13 Dec 2023). — [ZN.ua](https://zn.ua/war/v-nikopole-vveli-rezhim-polnoho-zatmenija.html)
- Occupied territories kept or gained light through 2024, and the occupied south lost it in July–August 2026. — [Texty.org.ua, 4 Sep 2026](https://texty.org.ua/articles/118222/usf-disabled-267-power-nodes-in-occupied-territories-blackouts-visible-from-space/)
- Lights recovered faster in Russian-controlled than in conflict areas. — [Applied Sciences 2022 (snippet)](https://doi.org/10.3390/app122412998)

### Inferences (suggested wording and rules)
- **On screen:** "Night lights, NASA Black Marble (NOAA-20 VIIRS), monthly composite, [month year], 01:30 local." Then: "Darkness here can mean a cut, a curfew, lights switched off for safety, or people gone. The satellite cannot tell which." For Nikopol add: "Since December 2023 Nikopol's outdoor lights are off by order." This matches the project's rule that inferred things are never shown as observed.
- **Never** cut from a line going dark in the record to a town going dark without a stated source tying the two. Use the IAEA record for the plant and the lights only for the region.
- Compare like with like: same month across years (e.g. January 2022 vs January 2023), same angle class, snow-free layer. Avoid June–July.
- Visual treatment: Black Marble is radiance on a 0.5 km grid. Show it as a grid of light, upsampled only by nearest-neighbour or bicubic as the film does for Sentinel-2, never "sharpened". That fits the project's "never generated, filled or sharpened" rule. **The gap-filled layer counts as "filled" under that rule and should be avoided.**
- The 172 km frame of the zoom-out is the natural scale for night lights. At 0.46 km pixels it is about 370 pixels across, so a 1920 px frame is upscaled about 5x, which reads as a coarse but honest grid. A 25 km crossing frame would be only about 54 pixels across: too coarse.

### Gaps
- Whether a clean (flag 0, clear, low-moon) night exists close to a key event (6 Sept 2022, 23 Nov 2022, any complete loss of off-site power) has not been checked. The check needs the token and a few daily tiles.

## 7. Alternatives and complements

### Takeaway
For sharper night images, **SDGSAT-1's Glimmer Imager (10 m pan / 40 m colour) is the best open option**. It is free to registered scientists (20-image quota, more by proposal), but imaging is tasked and sparse, so coverage of Enerhodar/Nikopol must be searched. ISS astronaut night photos are free but rare and unscheduled. DMSP gives pre-2012 history at about 2.7 km. VIIRS Nightfire (EOG) or Sentinel-2/Landsat SWIR suit fires. **The project's own record of the lines' cuts and reconnections remains the primary, best-sourced visual for the plant.**

### Cited Findings
- SDGSAT-1 (CBAS, China): Glimmer Imager 10 m panchromatic and 40 m RGB. Free to the global scientific community through the SDGSAT-1 Open Science Program since September 2022 (sdgsat.ac.cn). More than 450,000 images shared with scientists in 106 countries. — [CAS news, Sep 2022 (snippet)](https://english.cas.cn/newsroom/news/202209/t20220923_320728.shtml); [Remote Sensing 16:4298 (snippet)](https://mdpi-res.com/d_attachment/remotesensing/remotesensing-16-04298/article_deploy/remotesensing-16-04298.pdf); [CBAS presentation, UN (snippet)](https://sdgs.un.org/sites/default/files/2025-07/CBAS%20Presentation_Mr.%20Sun%20Zhongchang_CBAS.pdf); [WMO OSCAR](https://space.oscar.wmo.int/satellites/view/sdgsat_1)
- SDGSAT-1 access: register at sdgsat.ac.cn; default quota 20 images; larger quotas need a research proposal; GIU usually delivered as L4A. — [CBAS SDGSAT-1 User Manual (snippet)](https://sdgs.un.org/sites/default/files/2025-08/CBAS%20SDGSAT-1%20User%20Manual.pdf)
- ISS night photography: NASA's Gateway to Astronaut Photography of Earth is the official archive (eol.jsc.nasa.gov). Night images of Kyiv exist (Randolph Bresnik); none of Dnipro/Zaporizhzhia found in the search. — [Kyiv Post (snippet)](https://archive.kyivpost.com/lifestyle/nasa-astronaut-posts-spectacular-picture-kyiv-space.html)
- EOG's VIIRS Nightfire (VNF) detects fires and heat signatures, used in the 2022 war imagery. — [EOG war page](https://eogdata.mines.edu/products/special_topics/russia_ukraine_war.html)
- Daytime satellite evidence of the lines themselves (Greenpeace/MIS) is a better complement for the line story than night lights. — [Greenpeace Ukraine](https://www.greenpeace.org/ukraine/en/news/4460/the-750-kv-power-line-at-zaporizhzhya-nuclear-power-plant-shows-no-signs-of-major-damage-new-satellite-investigation-by-greenpeace/)

### Inferences
- **SDGSAT-1:** at 10 m, Enerhodar's street grid, the plant's site lighting and the TPP would separate. If any GIU scenes of 47.5° N 34.6° E exist (it images on schedule, roughly every 11 days by design; not verified here), a pre-war vs wartime pair would be far more telling than VIIRS. Check the archive (quota permitting), the licence terms for showing in a film, and that a Chinese state satellite's data source is stated on screen.
- **Jilin-1 and Luojia-1:** both are commercial or experimental, with sparse archives, and need licences. Luojia-1 (about 130 m, launched 2018) is likely no longer operating. Neither was verified this session, so treat them as low priority.
- **DMSP-OLS:** useful only for a pre-2012 "lights of the Soviet-built grid" history at coarse resolution (not verified this session).
- **Fires:** VIIRS active fire (VNP14) or EOG Nightfire, and Sentinel-2 SWIR (already in the pipeline via Planetary Computer), show shelling fires near Nikopol/Enerhodar better than DNB radiance.
- **Bottom line for the film:** use Black Marble as one quiet regional beat (the river as a border between light and dark), clearly labelled, ideally from VJ146A3 monthly composites. Keep the plant's own story in the IAEA-sourced record already built. Get the Earthdata token now if wanted: the token is free; the VNP46 stream ends 1–2 November 2026, but VJ146 continues.

### Gaps
- SDGSAT-1 redistribution and licence terms for film use were not found (the sdgsat.ac.cn policy page was not retrieved).
- No verified ISS night photo of the Zaporizhzhia region; the Gateway needs a direct search.
- Jilin-1, Luojia-1 and DMSP specifics were not verified this session.
