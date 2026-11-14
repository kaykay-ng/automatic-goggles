# NDC project: how countries talk about climate goals vs their actual emissions (started 14 Nov 2026)
Deadline unchanged: paper + slides + reflection Fri 27 Nov 23:59; presentation Wed 2 Dec. 2 people. Earlier food/parliament project is committed in the parent repo (PLAN.md).

## Data (all from the Climate Watch public API, no key; saved under ndc/data/raw/, gitignored; rebuild with the scripts in ndc/notebooks/)
- NDC content: GET https://www.climatewatchdata.org/api/v1/ndcs?page=1&per_page=1 returns ALL countries in one 57 MB JSON: 673 indicators (structured + text),
  198 countries, 216 sectors. Parsed by ndc/notebooks/parse_ndc.py -> ndc_indicators_long.csv (385,775 rows), ndc_text_long.csv (26,775 text rows >=150 chars).
  Document rounds: indc (2015), first_ndc, revised_first_ndc, second_ndc (2020-21), third_ndc (2025; 158 countries have '2025 NDC Submission': 156 submitted, 1 withdrawn, 1 non-party).
  Text volume: median 54k characters per country across rounds (min 5k, max 242k); 197 countries have text. => text changes ACROSS ROUNDS can be studied.
- Emissions: GET .../api/v1/data/historical_emissions?source_ids[]=274&gas_ids[]=553&sector_ids[]=...  (Climate Watch, All GHG, MtCO2e). fetch_emissions.py ->
  emissions_cw_long.csv: 199 locations incl. WORLD, 1990-2023, 13 sectors (total excl/incl LULUCF, energy, industrial processes, agriculture, waste, LULUCF, energy sub-sectors).
  NDC countries and emissions countries overlap on all 198. Other sources in the API for robustness: PIK (275), GCP CO2 (278), UNFCCC (276, 277).
- Not yet fetched: full NDC PDFs from the UNFCCC registry (more text, heavier parsing); income group / UNFCCC bloc membership / population / GDP (needed as controls and as edges).

## Candidate edges (nodes = ~158-198 countries), to be compared on the SAME nodes
writes alike (NDC text embedding similarity) | emits alike (sector profile / trajectory similarity) | pledges alike (indicator similarity) |
focuses alike (bipartite country-sector projection) | trades with (FAOSTAT-type trade) | negotiates together (UNFCCC bloc membership).
## Candidate questions (NOT yet pre-declared; choose first)
Q1 does NDC language follow actual emission structure or bloc/region/income templates?  Q2 say vs do: ambition language/targets vs emission trend since 2015.
Q3 which edge definition best explains the language network?  Q4 how does NDC text change across rounds, and do changes track emission trends?
Threats: summaries not full documents; early submitters self-select; targets for 2035 cannot yet be checked; NDC rounds differ across countries.

## Additions (14 Nov)
- DATA FINDING: text by round (countries with >=150-char text; median chars/country): indc 193 (5.6k), first_ndc 195 (12.2k), revised_first_ndc 158 (22.7k), second_ndc 82 (9.3k), third_ndc (2025) 102 (10.2k).
  The 2025 round has structured indicators for 158 countries but text for only ~100, and its 2035 outcomes cannot be checked yet => SAY-vs-DO needs the 2015-2021 pledges (first/revised first NDC) vs emissions 2015-2023.
- CONTROLS: World Bank API reachable (income level, region, population, GDP per capita; not yet fetched). UNFCCC bloc membership is NOT in the Climate Watch API (only group codes AOSIS, BASIC, UMBRELLA, AILAC, BRICS, OECD, SIDS, ANNEXI with no member lists) -> need a trustworthy list (UN/UNFCCC pages) or use EU/OECD/region/income only.
- NEW EDGE TYPE (user idea): 'feels alike' = similarity of World Happiness Report variables (ladder score; six explanatory factors: GDP per capita, social support, healthy life expectancy, freedom, generosity, corruption).
  Source: WHR Figure 2.1 Excel (2011-2024, ~140-150 countries) or Our World in Data Cantril ladder CSV (ladder only). NOT yet downloaded. Expected: happiness similarity ~ income/region similarity (strong confound).
  Use as one more layer: does climate-talk similarity (NDC) track happiness similarity beyond income, region and emissions structure?

## DESIGN v1, PRE-DECLARED before any test (14 Nov). User approved: main corpus = first NDC (2015-16 pledges), downloads of WHR 2026 + World Bank.
Data now in place: first_ndc text for 195 countries (median 1,597 words, ~12 passages); emissions 1990-2023 (13 sectors); World Bank income/region/pop/GDP pc/capital lat-lon (217);
 World Happiness Report 2026 (Figure 2.1 data, 3-year averages 2023-25: ladder + six 'explained by' factors; 146 countries matched to ISO3; North Cyprus, Somaliland, Taiwan unmatched).
VALIDATION (done first): (1) 29 first_ndc texts are IDENTICAL (cosine>0.98): the 27 EU member states + EUU + GBR (the EU's joint INDC) -> collapse into ONE node 'EUU' (emissions = sum of the 27
 members, income/region/coords = EU values). (2) neighbours sensible: FJI -> TON, VUT, SLB; IND -> LKA, NPL, BGD, BTN; NGA -> SSD, BEN, SDN; USA -> KOR, EUU, JPN, GBR; CHN -> VNM, LAO.
 (3) split-half reliability across passages r=0.66 (mean; range .63-.69): moderate, similarity is noisy. (4) LENGTH ARTEFACT: Spearman(n_words, mean similarity to others) = +0.75.
 => length enters every model as a control (log product of word counts); robustness: equal-sized passage subsamples.
NODES: countries with first_ndc text AND emissions AND World Bank controls, EU collapsed (~165). DYAD MATRICES:
 L language similarity = cosine of centred first_ndc country vectors.  M emission-profile similarity = minus Euclidean distance (standardised) between 2015 profiles
 [energy, industrial processes, agriculture, waste shares of total excl. LULUCF; LULUCF/total excl. LULUCF clipped to [-1,1]].  Hh happiness similarity = minus Euclidean distance (standardised)
 over ladder + six factors (nodes with WHR data only).
 Controls: |log GDPpc gap|, same World Bank region, same income group, log capital-to-capital distance, log population product, log product of word counts.
PRIMARY TESTS (DSP-MRQAP: Dekker double semi-partialling with node-label permutation of the response, 5,000 permutations; standardised coefficients):
 H1 L ~ M + controls; prediction POSITIVE (countries with similar emission structure write similar NDCs).
 H2 (nodes with happiness): L ~ M + Hh + controls; the coefficient on Hh is the test, TWO-SIDED, single test (does happiness similarity add anything beyond income, region and emissions?).
 H3 SAY vs DO (country level): for each sector s in {energy, agriculture, land_forest, waste, industry}: Spearman between NDC text emphasis (mentions per 10,000 words) and the actual 2015 emission share
   of s (industry compared with industrial processes; land_forest compared with LULUCF/total), partial on log words and log GDPpc; predicted POSITIVE; Holm over the 5 sectors.
EXPLORATORY (labelled): extra layers (pledge-indicator similarity, trade), other rounds (revised_first_ndc, third_ndc), equal-passage subsamples, per-sector breakdowns, changes between rounds.
THREATS: short texts (noise, attenuation), EU/UK collapse, node-level income confound, happiness confounded by income, mixed vintages inside 'first_ndc', countries without text excluded,
 text is Climate Watch's extracts of the NDC documents not the full PDFs, sector words are keyword counts.

## RESULTS of the pre-declared tests (14 Nov; ndc/notebooks/ndc_tests.py; first_ndc, 154 nodes after EU collapse, 11,781 dyads)
Dropped for missing emissions/controls: COK CUB ERI LIE MCO MHL NIU PRK PSE SMR SSD VAT VEN. Language similarity (centred cosine) mean -0.005, sd 0.144.
H1  L ~ emission-profile similarity + controls (R^2=.240): emission_similarity beta=+0.039 (p=.0006; predicted POSITIVE: yes but TINY; raw Spearman +0.10).
    Dominant: same_region +0.248, log_distance -0.245, income_gap -0.119; same_income_group +0.028, log_pop_product -0.024, log_words_product +0.045.
H2  nodes with happiness 111 (dyads 6,105): happiness_similarity beta=+0.002 (p=.91, TWO-SIDED): NO added information. Raw Spearman(L, happiness)=+0.24 but happiness similarity vs income gap = -0.63
    (happiness similarity is mostly an income/development map). Emission similarity in this subset +0.064 (p=.0004); R^2 .288 with and without happiness.
H3  say vs do (partial rho controlling log words + log GDPpc; one-sided; Holm over 5): energy +0.15 (Holm .115), industry +0.19 (Holm .048), agriculture +0.10 (raw +0.42! mostly length/income; Holm .130),
    waste +0.12 (.130), land_forest +0.14 (.130). Only industry passes Holm. => NDC sector emphasis follows actual emissions only weakly.
READING: NDC language similarity is organised by REGION, DISTANCE and INCOME GAP; emission structure adds a tiny amount; happiness adds nothing beyond income. Attenuation caveat: split-half
 reliability of the language measure is only .66, so true effects of emission similarity may be somewhat larger; with 11.8k dyads even tiny effects reach p<.001, so report effect sizes.

## LANGUAGE NETWORK + EDGE-LAYER COMPARISON (14 Nov; set before running; exploratory except the first claim)
Network: nodes = the 154 countries of ndc_tests.py (EU collapsed). Language edges: each country linked to its k=5 most similar countries (centred cosine of first_ndc vectors), union of directions,
weights = similarity. Communities: Louvain (networkx, weight=similarity, seed 42, resolution 1).
PRIMARY structural claim (pre-declared): language communities agree with World Bank REGION more than chance (ARI, 5,000 label permutations). Also report agreement with income group and with
 emission-profile clusters (Ward on the standardised 2015 profile, k by silhouette 3-6).
Significance of community structure: observed Louvain modularity vs 200 degree-preserving rewired graphs (double-edge swaps, unweighted).
Stability: k in {3,5,8,10,15}; 20 Louvain seeds; other NDC rounds (revised_first_ndc, third_ndc) on common countries.
ALTERNATING THE EDGES (comparative): same nodes, k=5 nearest-neighbour graphs built from (i) language, (ii) emission-profile similarity, (iii) income similarity (|log GDPpc gap|),
 (iv) geography (capital distance). Compare their Louvain partitions (ARI matrix) and their edge overlap (Jaccard of edge sets). Happiness layer on the 111 nodes with WHR data as a side comparison.
Figures: ndc/figures/language_network.png (coloured by language community and by region).

## RESULTS: language network, communities, edge layers (14 Nov; ndc/notebooks/ndc_network.py; ndc/figures/language_network.png; data/processed/ndc_language_communities.csv)
Language kNN network (k=5, first_ndc): 154 nodes, 518 edges, mean degree 6.7, 1 component. Louvain: 7 communities (sizes 27, 26, 25, 24, 23, 18, 11), weighted Q=0.635.
 Null: unweighted Q 0.600 vs 0.351+-0.009 in 200 degree-preserving rewired graphs (p=.005, the floor with 200 draws).
Communities (by membership): West/Central Africa (BEN BFA CIV CMR COD COG ...), South/East Asia (AFG BGD BTN CHN IDN IND KHM LAO LKA ...), Europe/OECD-like (EUU AUS JPN KOR CHE ISL USA ...), East/Southern Africa
 (AGO BDI BWA ETH KEN ...), small islands (ATG BHS BLZ BRB DMA FJI GRD JAM KIR MDV MUS ... plus CAN), Latin America (ARG BOL CHL ... 18/18 LAC), Gulf/Middle East (ARE BHR IRQ ISR JOR KWT ... 11/11 MENA).
PRIMARY (pre-declared): communities vs World Bank region ARI=+0.398, p=.0002 (region partition alone reaches Q=.541 on the language network vs Louvain's .635); vs income group ARI=+0.098; vs emission clusters (Ward k=5) ARI=+0.040.
Stability: k in {3,8,10,15}: ARI vs k=5 +0.54, +0.84, +0.66, +0.65; 20 seeds: 7-8 communities, mean pairwise ARI 0.78; other rounds vs first_ndc partition: revised +0.38, third +0.49, indc +0.37 (vs region .29 / .41 / .31).
Alternating edges (k=5 kNN on same nodes; ARI of Louvain partitions): language-geography +0.44; language-emissions +0.04; language-income +0.05; emissions-income +0.02; geography-income +0.03.
 Edge-set Jaccard: language-geography 0.22; all others <=0.05. Happiness layer (111 nodes): ARI with language +0.23, income +0.26, geography +0.18.
CHECK: source-language artefact ruled out as far as detectable: all 195 first_ndc texts are English by stop-word detection (Climate Watch stores English). Drafting style/translation of the English could still carry regional signal.
READING: NDC language is organised into regional and 'bloc-like' communities (e.g. small islands, Gulf states, francophone Africa), nearly independent of emission structure and income. TO DO: UNFCCC bloc membership (AOSIS, LDC, G77, Arab Group, ...)
 needs a trustworthy list; say-vs-do on emission TRENDS; figure polish; paper outline.

## WORD PLOT for H1 (14 Nov; ndc/notebooks/ndc_wordplot.py, ndc/figures/wordplot_agri_vs_energy.png, data/processed/ndc_wordplot_agri_vs_energy.csv; descriptive, NOT a test)
Groups from 2015 emission shares: agriculture-heavy (agri share >= 0.37, energy share below top tercile) 52 countries vs energy-heavy (energy share >= 0.74, agri below top tercile) 52 countries.
Score = Monroe-Colaresi-Quinn log-odds with informative Dirichlet prior, z-scored; 2,742 terms (>=5 countries, >=8 uses). A first version had the colour scale reversed vs the legend; fixed.
Most agriculture-heavy terms: agriculture 8.0, agricultural 7.2, adaptation 7.2, livestock 5.9, climate 5.9, management 5.3, million 4.9, implementation 4.9, national adaptation 4.8, usd 4.6, resilient 4.6, napa 4.6, communities 4.6, rural 4.3, gender 4.0.
Most energy-heavy terms: gas -9.9, emissions -9.8, greenhouse -8.6, sea -7.9, target -7.7, greenhouse gas -7.7, sea level -7.0, islands -6.9, energy -6.8, rise -6.2, oil -5.8, states -5.6, fuel -5.1, industrial -4.9, energy efficiency -4.8.
CONFOUND: the two groups differ in income: agriculture-heavy = 20 low + 22 lower-middle + 7 upper-middle + 3 high; energy-heavy = 23 high + 22 upper-middle + 7 lower-middle. Word differences (adaptation, NAPA, USD, communities,
 gender vs emissions, targets, energy, oil, sea level/islands) therefore mix emission structure with development level and small-island status. Consistent with H1 being tiny once income gap is controlled.

## SAY vs DO: did countries keep their pledges? (14 Nov; ndc/notebooks/ndc_pledge_check.py) -- definitions set BEFORE computing
Checkable pledges only: first NDC with structured type 'Base year target' AND a quantified reduction in the 'GHG target' text, NOT relative to a BAU/baseline scenario, base year 1990-2015, target year 2020-2030.
 61 countries have a base-year type; 58 parse; checks of 18 random parses found problems fixed in v2: EU members all carry the joint pledge (-40% vs 1990 by 2030, 'EU and its 28 Member States') -> ONE entry 'EUU'
 evaluated on EU28 emissions (27 members + GBR); BAU-relative pledges (e.g. ZMB) excluded; fiscal-year base years (JPN FY2013) accepted; 'not exceed X% of YEAR level' means a (100-X)% reduction (UKR, TJK).
 NOT checkable here: BAU/baseline-scenario pledges (the largest group, ~290 rows), intensity pledges, fixed-level pledges (net/gross definitions), countries without a quantified base-year pledge.
Actual emissions: Climate Watch All GHG, 'Total excluding LULUCF' (primary), 'Total including LULUCF' (sensitivity), to 2023.
Pledge year = 2015 (first NDC). Lower bound of a range is the pledged reduction r (sensitivity: midpoint). E_target = E_base * (1 - r).
PROGRESS MEASURES: (1) target_met_2023 = E_2023 <= E_target. (2) on_track: E_2023 <= linear path from E_2015 to E_target at the target year, evaluated at 2023 (ahead of schedule).
 (3) gap_remaining = (E_2023 - E_target)/E_base (share of base-year emissions still to cut; negative = overshoot of the target).
 (4) required_pace = annual cut needed from 2023 to the target year vs actual_pace = average annual change 2015-2023 (both as % of E_base).
HYPOTHESES (declared): H4 'ambitious pledges are not kept better': Spearman between pledged reduction r and progress share is NOT positive (selection of already-decarbonising countries into pledges is the competing story).
 H5 high-income countries are more often on track than low/middle-income. Exploratory: relation between the language measures (sector emphasis, similarity communities) and keeping the pledge.
LIMITS: base-year pledges are mostly rich countries (1990 base) = non-random 'checkable' subset; LULUCF treatment varies by country; pledges often cover specific gases/sectors; emissions data are modelled estimates;
 2023 is mid-way to 2030 so 'not on track yet' is not 'failed'; revised/2025 NDCs replaced some pledges.

## SAY vs DO RESULTS (14 Nov; ndc/notebooks/ndc_pledge_check.py compute; ndc/figures/pledge_vs_emissions.png; data/processed/ndc_pledge_progress.csv, ndc_pledges_parsed.csv)
Parser fixes after reading all 27 texts: RUS 'reduction ... to 70 percent relative to the 1990 level' = 30% reduction (was parsed as 70%); sector-only pledges (PLW energy, COK/TUV electricity) excluded;
 tiny emitters (base-year emissions < 1 Mt: DMA FSM GRD LIE MHL) excluded (rule added AFTER seeing results); MNE kept but flagged: Climate Watch 1990 ~1 Mt vs its own pledge text 5.2 Mt (data mismatch).
CHECKABLE = base-year, economy-wide, non-BAU, quantified pledges in the first NDC: 24 (EU once); MAIN SET 19 (base-year emissions >= 1 Mt). Of 193 first NDCs, ~85% are NOT checkable this way (BAU 75, intensity 11, fixed level 6, other 40).
MAIN SET: target already met by 2023: 5; on track (ahead of the straight line 2015 -> target): 7; behind: 12.
 ALREADY MET AT THE TIME OF THE PLEDGE (E_2015 <= target): AZE BWA KAZ MDA SRB UKR (mostly post-Soviet collapse before 2015; BWA and KAZ have since risen back above the target).
 13 pledges needed real cuts after 2015: ahead of path: GNQ (after a 2007 peak; needed only 3.5%), EUU (needs 22.3% from 2015 level, achieved 17.8%), JPN (21.1 vs 16.3). Behind: ISL 37.6 vs 15.5, CHE 44.4 vs 14.3, NOR 45.2 vs 13.1,
 NZL 27.7 vs 9.2, USA 18.8 vs 7.4 (target year 2025), CAN 31.7 vs 0.5, AUS 32.3 vs -3.9, BRA 48.8 vs -4.9 (target 2025), MNE (data problem), RUS 3.0 vs -12.2. Emissions ROSE since 2015 in AUS, BRA, MNE, RUS.
Sensitivity: including LULUCF changes on-track status for EUU, MDA, RUS (3 of 19); using the midpoint of ranges changes none.
H4 (pre-declared): pledged reduction vs progress share rho=-0.09 (p=.77, n=13): ambitious pledges are NOT kept better. H5: on track high income 2/10 vs others 5/9 (Fisher p=.17): no support for 'rich countries more on track' (driven by the already-met post-Soviet group).
CONTEXT (non-checkable pledge types, emission change 2015->2023, EU members excluded): BAU (n=75) median +13.5%, 83% growing; fixed level (n=6) +19.9%, all growing; intensity (n=11) +12.1%, 64% growing; base-year (n=30) 0.0%, 43% growing; other (n=40) +10.4%.
LIMITS: 2023 is not 2030 ('behind' is not 'failed'); many pledges have since been revised; modelled emissions; LULUCF treatment varies by country; small n; checkable subset is rich/post-Soviet.
IDEA (not done): the 2020 pledges ('pledges' source, 73 countries) include 'Projected baseline emissions in target year' -> BAU pledges can be checked for target year 2020 (2020 is the COVID dip: also check 2019).

## 2020 PLEDGES (Copenhagen/Cancun round; document 'pledges', 73 countries): FINISHED-outcome check -- rules set BEFORE computing (14 Nov)
Structured fields: types Base year 18, BAU 11, fixed level 3, intensity 2, 'Not applicable' 39 (actions/NAMAs only). 'Projected baseline emissions in target year' is EMPTY for all 73 (my earlier suggestion that it would unlock BAU checks was WRONG);
 BAU projections are not in the texts either (e.g. BRA gives only '36.1-38.9% below projected emissions') -> the 11 BAU pledges (BRA CHL IDN ISR KGZ KOR MEX PNG SGP THA ZAF) CANNOT be checked here.
CHECKABLE (hand-extracted from the pledge text; the UNCONDITIONAL or LOWER-BOUND figure is the pledge): AUS 5% vs 2000 (conditional 15-25%); BLR 5% vs 1990 (5-10%); CAN 17% vs 2005; CHE 20% vs 1990 (conditional 30%);
 EUU 20% vs 1990 on EU28 emissions (conditional 30%); ISL 30% vs 1990 (stated, in a joint effort with the EU); JPN 3.8% vs 2005; KAZ 15% vs 1990; MDA 25% vs 1990; NOR 30% vs 1990 (conditional 40%); NZL 5% vs 1990;
 RUS 15% vs 1990 (15-25%); UKR 20% vs 1990; USA 17% vs 2005. Excluded as tiny emitters (<1 Mt): ATG LIE MCO MHL (MHL is also CO2-only). Intensity pledges: CHN CO2 per GDP -40% (lower bound of 40-45%) vs 2005;
 IND emissions intensity of GDP excluding agriculture -20% (lower bound of 20-25%) vs 2005; GDP = World Bank constant-2015-US$ GDP.
MEASURE: target level = E_base * (1 - r); outcome = total GHG excl. LULUCF (Climate Watch) in 2019 and 2020 (2020 = target year but a COVID dip; 2019 = last pre-COVID year); sensitivity incl. LULUCF.
 met = E_year <= target. A reader should re-check my hand extraction against the 'Pledge content' texts (data in ndc_indicators_long.csv, document 'pledges').
HYPOTHESES (declared): H6 more than half of checkable 2020 pledges were met in 2020. H7 COVID helped: more pledges are met in 2020 than in 2019 (paired comparison).

## 2020 PLEDGES RESULTS (14 Nov; ndc/notebooks/ndc_pledge2020.py; ndc/figures/pledge2020_vs_outcome.png; data/processed/ndc_pledge2020_outcomes.csv)
GDP for the intensity pledges: the World Bank API timed out (3 x 60 s and 2 x 120 s); used the Our World in Data copy of NY.GDP.MKTP.KD (constant 2015 US$) in ndc/data/raw/owid_gdp.csv. China's intensity uses Climate Watch CO2 (total excl. LULUCF).
ABSOLUTE pledges (14; total GHG excl. LULUCF), change vs base year in 2019 / 2020 vs pledge: UKR -73.0/-74.1 vs -20 met; MDA -66.2/-67.6 vs -25 met; BLR -35.6/-37.3 vs -5 met; EUU(EU28) -27.7/-33.6 vs -20 met; RUS -23.6/-26.1 vs -15 met;
 ISL -16.7/-21.9 vs -30 missed; CHE -14.1/-18.6 vs -20 missed (near); USA -9.5/-17.7 vs -17 (met in 2020 ONLY); JPN -9.6/-13.9 vs -3.8 met; KAZ -13.8/-12.7 vs -15 missed (near); AUS -0.2/-6.8 vs -5 (met in 2020 ONLY);
 CAN +6.3/-2.2 vs -17 missed; NOR +2.7/-0.9 vs -30 missed; NZL +14.6/+10.6 vs -5 missed.
INTENSITY: CHN CO2/GDP -42.6/-43.3 vs -40 met (both years); IND GHG excl. agriculture/GDP -19.9/-20.8 vs -20 (met in 2020 only, by a hair).
H6: met in 2020: 8/14 absolute (+2/2 intensity) = 10/16. H7: met in 2019: 6/14; in 2020: 8/14; COVID-assisted (met only in 2020): AUS, USA (+IND on intensity); none met in 2019 but not 2020.
 Median distance to target (% of base-year emissions): +3.0 in 2019, -1.2 in 2020. Incl. LULUCF: only USA's verdict changes (7/14 met).
 Of the 10 met: 4 are post-Soviet pledges set below an already-collapsed 1990 base (UKR MDA BLR RUS: met with no effort), 2-3 owe the result to COVID (USA, AUS, IND) => about 3-4 of 16 look genuinely policy-driven (EUU, JPN, CHN).
 Counts not captured: Kyoto flexibility mechanisms / purchased units (CHE, NOR, ISL, MCO mention them), LULUCF accounting rules, base-year revisions.
TWO PLEDGES, same countries (13): met 2020 pledge AND on track for the 2015-NDC target: EUU JPN MDA UKR (4); met 2020 but NOT on track: AUS RUS USA (3); missed 2020 AND not on track: CAN CHE ISL KAZ NOR NZL (6). No country that missed 2020 is on track now (0/6).
NOT CHECKABLE: the 11 BAU pledges of 2020 (BRA CHL IDN ISR KGZ KOR MEX PNG SGP THA ZAF) have no BAU numbers in the data.

## EU MEMBER STATES, unpacking the joint pledge (14 Nov; user wanted the nuance behind 'EUU'; EXPLORATORY/descriptive)
The EU's first NDC (-40% vs 1990 by 2030) and its 2020 pledge (-20% vs 1990) are COLLECTIVE; member states have differentiated national targets (effort sharing for non-ETS sectors; the ETS cap is EU-wide) that are NOT in our data and that I will not type from memory.
So comparing each member with the EU-wide benchmark is DESCRIPTIVE: it shows who delivered the reduction, not who 'broke' a national commitment.
Data: Climate Watch total GHG excl. LULUCF per member (27 members + GBR, which was in the EU28 for the 2015 NDC), 1990-2023. Measures per member: % change 1990 -> 2019 and 2020; cut 2015 -> 2023 vs the 22.3% cut from the 2015 EU level needed
 for -40% by 2030; each member's contribution (Mt) to the EU28 change 1990 -> 2019.

## EU MEMBER-STATE RESULTS (14 Nov; ndc/notebooks/ndc_eu_members.py; ndc/figures/eu_members_decomposition.png; data/processed/eu_members_pledge_decomposition.csv)
EU28 (27 members + GBR): 1990 5,361 Mt -> 2019 3,876 (-27.7%) -> 2020 3,558 (-33.6%) vs the -20% 2020 pledge; 2015 4,141 -> 2023 3,406 = 17.8% cut vs 22.3% needed by 2030 (11.9% by 2023 on a straight line => ahead).
 EU27 without the UK: 1990 4,596 -> 2019 3,433 (-25.3%), 2020 -31.3%; 2015 3,642 -> 2023 3,022 = 17.0% cut. UK = 12.0% of EU28 emissions in 2015.
WHO DELIVERED (1990 -> 2019): DEU -383 Mt (26% of the net EU28 cut), GBR -321 (22%), ROU -129 (9%), POL -110 (7%), FRA -89 (6%); top 3 = 56%; members that INCREASED added 38 Mt (ESP +25, IRL, PRT, CYP).
SPREAD per member 1990 -> 2019: EST -68% ... CYP +60%, median -22%. Only 15/28 members are individually below -20% in 2019 (21/28 in 2020 incl. COVID). Above their 1990 level in 2019: CYP, ESP, IRL, PRT (AUT -0.3%).
WHEN THE CUTS HAPPENED (share of each member's 1990->2019 cut already done by 2000): LVA 106%, LTU 103%, HRV 93%, BGR 88%, ROU 84%, EST 82%, POL 79%, SVK 72%, HUN 64%, CZE 59%, DEU 44%, GBR 21%, FIN 8%, SWE 3%, DNK -2%.
 => the big percentage cuts of the Baltic/Eastern members are the early-1990s economic collapse (same pre-collapse-baseline effect as UKR, MDA, BLR, RUS); post-2000 policy-driven cuts: UK, Denmark, Sweden, Finland (and part of Germany).
2030 PACE (straight line: 11.9% cut by 2023): 16/28 at or above (EST NLD FIN LUX DEU BGR GBR PRT GRC DNK CZE ESP BEL SWE FRA AUT); 12 below: ITA 11.8, IRL 10.8, SVN 10.3, HUN 10.0, LVA 9.4, POL 8.9, ROU 7.6, SVK 7.1, LTU 4.5, CYP -3.0, HRV -4.7, MLT -15.0.
 A first version compared members with the FULL 22.3% instead of 11.9% (wrong benchmark: made only 7 look on pace); caught and fixed before use.
CAVEATS: national targets differ under effort sharing (not in our data and NOT entered from memory); Climate Watch excl. LULUCF; per-member 'meeting the EU-wide target' is descriptive, not a legal test; UK counted because it was in the EU28 for the 2015 NDC.

## LTS and PARLIAMENT: do parliaments discuss HOW the long-term goal will be reached? (14 Nov; user's question; term lists fixed BEFORE counting)
Data check: 20 of 26 ParlaMint countries have an LTS record in Climate Watch (13 indicators; text only ~800-1,900 chars: a summary paragraph) and 22 have a net-zero target year. The LTS record has NO detailed pathway; it has structured flags
 (Net-zero Target; Reliance on Technological Carbon Removal; Target Type; Quantified Long-term Emissions Goal; Submission Date). The pathway detail would need the FULL LTS documents from the UNFCCC LTS portal (not fetched).
PARLIAMENT SIDE (saved climate-keyword speeches, flagged_XX.csv.gz, text included; substantive >=50 words, non-chair, 2015-2022):
 GOAL-TALK = speech matches: climate/carbon neutral*, net zero, zero-emission*, 2050, long-term climate strategy/goal/target, decarbonis*, climate target/goal(s), Paris agreement/goals.
 MEANS-TALK categories (a goal speech 'discusses how' if it ALSO matches >=1 category): energy (renewable, wind, solar, photovoltaic, nuclear, hydropower, biomass, biogas, geothermal, energy transition, electrification, energy efficiency, coal phase-out),
  transport (electric vehicle(s), EV, charging, public transport, railway, cycling, combustion engine, electromobility), buildings (heat pump, insulation, renovation, retrofit, district heating),
  industry (hydrogen, carbon capture, CCS, CCUS, steel, cement), agri_land (agricultur*, livestock, methane, forest*, afforestation, reforestation, peat, land use),
  instruments (carbon price/pricing/tax, emissions trading, ETS, carbon border), finance_social (just transition, jobs, affordab*, households, subsid*, investment, funding), removals (carbon removal, negative emissions, direct air capture, sequestration).
 Precision of the lists is UNVERIFIED until samples are read; counts below are a feasibility check, not a test.
FIRST PASS TOO LOOSE (14 Nov): with the lists above 75% of 19,515 'goal' speeches also had a 'means' term, because finance_social (46%: investment, jobs, households, funding) and generic words are not 'how', and 'Paris agreement' brings in ratification speeches.
 Samples read: BA 2016 and BG 2016 'goal' speeches are ratification procedures. => STRICT v2 (fixed before counting): GOAL = climate/carbon neutral*, neutrality, net zero, long-term climate strategy/goal/target, or '2050' in a sentence that also has climate/emission/carbon/neutral/greenhouse.
 MEANS = SPECIFIC means only (energy sources/efficiency/coal phase-out, electric vehicles/charging/public transport/railway, heat pumps/insulation/renovation/district heating, hydrogen/CCS/steel/cement, afforestation/reforestation/peat/methane/livestock,
 carbon price/tax/emissions trading/ETS/carbon border, carbon removal) AND within +-300 characters of a goal term. finance_social and generic agriculture/forest words dropped.
STRICT v2 FIRST RUN HAD TWO BUGS (14 Nov): (1) the means table had a different row index than the speech table, so 'goal AND means' came out ~1% (47 of 8,931); fixed. (2) the goal list matched 'technological/military/judicial neutrality' and '2050' in population/migration forecasts
 (read in the goal-only samples); fixed: bare 'neutrality' removed; '2050' now only within 80 characters of reduc*/neutral*/zero/emission(s)/carbon/greenhouse/decarbonis*.

## LTS and PARLIAMENT: first strict counts (14 Nov; ndc/notebooks/lts_parliament_means.py; data/processed/lts_parliament_means_counts.csv; PRELIMINARY, precision from my own reading of samples only)
8,105 strict goal-talk speeches (substantive, non-chair, climate-keyword speeches 2015-2022) in 26 parliaments: GB 3,520; FI 511; FR 465; BE 451; SE 422; NL 383; NO 360; EE 273; DK 244; PT 212; HU 195; AT 147; HR 133; PL 125; GR 123; SI 120; IT 119; ES 63; CZ 57; IS 43; RS 36; TR 35; BG 32; LV 30; UA 6; BA 0.
34% (2,750) name a SPECIFIC means within +-300 characters of the goal statement. By country (n>=100): HU .49, FR .39, BE .37, SE .37, IT .37, PL .36, HR .33, GB .33, FI .32, EE .30, DK .27, NL .27, GR .26, NO .24; small n: CZ .49, BG .47, TR .46, ES .44, RS .44, IS .14, LV .07.
Means named near goals (share of goal speeches): energy 23%, industry 6%, transport 5%, buildings 3%, instruments (carbon price/ETS) 2%, land/methane 1%, removals 1%.
Reading ~10+8 samples: GOAL+MEANS mostly genuine (ES building renovation for 2050; EE electrification and electric cars; FR hydrogen aircraft; IS carbon price and carbon removal; RS building energy efficiency; CZ biomethane); a few doubtful (LV 2020).
 GOAL-only samples are genuine goal-talk but include means outside my lists (DK green fuels/Power-to-X; IT fossil fuels) => the means share is an UNDERCOUNT; also much goal-talk concerns the EU, other countries (TR on China), a court ruling (IT), or a city (LV Riga), not the nation's own LTS.
 => the lists measure 'a specific means is mentioned near a long-term goal', NOT 'the nation's LTS pathway is discussed'. That needs (a) the full LTS documents (UNFCCC portal PDFs, not fetched) and (b) separating national from EU/other-country talk.

## LTS full documents: FETCH BLOCKED (14 Nov)
23 LTS PDFs for the 20 parliament countries are linked from Climate Watch (unfccc.int/sites/default/files/resource/...). All requests return HTTP 200 with a 212-byte Incapsula (Imperva) JavaScript challenge page instead of the PDF -> the portal blocks scripted clients.
Bypassing bot detection is not appropriate, so no PDFs were fetched; the empty files I created were deleted. Hand-download list with target file names: ndc/lts_download_list.md (user downloads in a normal browser into ndc/data/raw/lts_pdfs/ as CC_n.pdf).
Fallback if not downloaded: only the Climate Watch LTS summaries (~800-1,900 chars/country) + structured flags are available, which cannot support a pathway-level comparison.

## LTS vs PARLIAMENT, PATHWAY COMPARISON: plan fixed BEFORE the PDFs arrive (14 Nov; user will download the 23 PDFs by hand into ndc/data/raw/lts_pdfs/ as listed in ndc/lts_download_list.md)
Step 1 (ndc/notebooks/lts_extract.py, ready, self-tested on a local PDF): extract text, language flag (BE is French), pages, characters per page (flags scanned PDFs), and a profile of 9 shared categories per document:
 energy, transport, buildings, industry, agriculture, land_forest, waste, instruments, removals (mentions per 10,000 words; lists in the script). Where a country has 2 documents use the one submitted closest to, and before, the end of 2022 (CZ_2, GB_1, UA_2; the others have one).
Step 2 (to write once PDFs are in; SAME category lists): parliament profile = for each country, the share of means-mentions per category inside +-300 characters of strict long-term-goal statements (strict goal list in lts_parliament_means.py), and as a second view the same per 10,000 words over ALL climate speeches.
Step 3 PRE-DECLARED tests (n up to 20 countries; exploratory unless marked):
 P-A (primary): across countries, for each category, Spearman between its share in the LTS profile and its share in the parliament profile; summarise by the median rho over the 9 categories (positive = parliaments talk about the sectors their strategies stress).
   Null: permute country labels of the parliament profiles (5,000x) and take the median rho each time.
 P-B: within-country alignment: Spearman between the 9-category LTS vector and the parliament vector for each country; report the median over countries against the permuted-partner null (parliament vector from another country).
 P-C: sector 'gap': categories heavily emphasised in the LTS but rare in parliament (and the reverse) -> list for the paper (descriptive).
 Hand-check: read ~20 goal-window excerpts for 3 countries to check precision of the shared lists (agriculture/land lists are broad here: 'forest', 'farm' etc. match more than the narrow lists used for the earlier 34% figure).
Limits: n<=20; PDFs differ in kind (a short LTS, a 300-page strategy, a climate programme such as DK's); parliament talk covers EU/other countries too; machine-translated English on the parliament side vs original English documents; documents are policy texts, parliament is debate.

## LTS extraction RESULT (14 Nov): 23 PDFs in place and extracted (ndc/notebooks/lts_extract.py; data/processed/lts_profiles.csv, lts_text/). None are scanned (>=1,575 chars/page).
BE_1 is French and ES_1 is SPANISH (tiny counts with English lists) -> EXCLUDED from the quantitative comparison (parliament side is machine-translated English; lists are English). 21 English documents for 18 countries.
Document used per country (plan): CZ_2 (2018 summary, 18 pages), GB_1 (2021 Net Zero Strategy, 368 pages), UA_2 (2018 strategy); BA_1 is the 2020-2030 adaptation and low-emission development strategy (not a 2050 LTS); DK_1 is the Climate Programme 2020.
Parliament-side minimum for the goal-window profile: >=30 strict goal speeches (excludes BA 0, UA 6).

## LTS PATHWAY vs PARLIAMENT RESULTS (14 Nov; ndc/notebooks/lts_vs_parliament.py; ndc/figures/lts_vs_parliament.png; data/processed/lts_vs_parliament_profiles.csv, parliament_category_profiles.csv)
Countries: 18 with an English LTS profile; 16 with >=30 strict goal speeches (AT CZ DK FI FR GB HU IS LV NL NO PT RS SE SI TR); UA (6) and BA (0) excluded from the goal-window view.
Mean theme shares (LTS | parliament goal windows | all climate speeches): energy .21|.41|.24; transport .06|.09|.08; buildings .08|.05|.06; industry .13|.12|.10; agriculture .12|.09|.18; land_forest .16|.07|.09; waste .11|.08|.06; instruments .08|.08|.19; removals .04|.015|.004.
P-A (primary view, goal windows, n=16): across-country rho per theme: land_forest +0.63, transport +0.48, industry +0.28, energy +0.27, removals +0.26, buildings +0.23, agriculture +0.07, waste +0.03, instruments 0.00; MEDIAN +0.26 vs permuted null 0.00 (sd .11), one-sided p=.012.
 Second view (all climate speeches, n=18): median +0.40, p=.0002 (energy +.57, waste +.60, transport +.49, land_forest +.49, removals +.40).
P-B within-country (goal windows): own LTS vs own parliament median rho +0.51 vs +0.33 against OTHER countries' parliaments; own better in 15/16; permutation p=.014. Per country: CZ .73, DK .70, PT .68, GB .67, TR .58, SE .55, AT .52, NL .51, HU .51, FI .50, RS .50, NO .48, SI .48, FR .32, LV .23, IS .16.
 Second view: own +0.52 vs +0.38; 14/18; p=.006.
P-C gaps (log2 LTS share / parliament share): removals +2.27, land_forest +1.72, waste +1.10, buildings +1.07, agriculture +0.85, industry +0.65, instruments -0.17, transport -0.32, energy -0.78.
HAND-CHECK (18 goal windows read: FI, GB, NL): matched themes mostly relevant (biomass, peat, emissions trading; electrification, cycling, railway; nuclear; coal; public transport), some weak ('building' in building-safety talk, generic 'electricity', 'tax');
 6 of 18 windows matched no theme at all (consistent with ~1/3 naming a means). Lists are broad: 'instruments' includes generic tax/subsidy words (inflates the all-speeches view: .19), 'energy' includes electricity/coal.
CAVEATS: n=16-18; profiles are compositional (energy dominates); alignment can reflect shared national circumstances (forests in FI, IS) as much as parliaments following the strategy; document types differ (DK programme, CZ 18-page summary, GB 368 pages);
 parliament text is machine-translated; BE (French) and ES (Spanish) strategies not analysed; not separated: talk about EU/other countries.

## TRANSLATING THE SPANISH AND FRENCH STRATEGIES (user suggestion, 14 Nov; NOT yet run, awaiting OK for the model download)
Confirmed: ES_1 is Spanish (es stop-words 0.39, en 0.001) and BE_1 French (fr 0.31, en 0.002). Plan: machine-translate to English with the OPUS-MT models Helsinki-NLP/opus-mt-es-en (312 MB) and opus-mt-fr-en (301 MB), Apache-2.0, from Hugging Face --
 the SAME model family ParlaMint used for the parliament speeches, so both sides carry comparable translation noise. Needs `sentencepiece` (small) in .venv-nlp. ~81k words (ES 24k, BE 57k) -> a few thousand sentences, minutes on the Mac GPU.
Method: rejoin PDF line breaks into sentences, translate sentence by sentence, save to ndc/data/processed/lts_text_translated/, re-run the same 9-theme profile, read ~6 translated passages per document, and report results WITH and WITHOUT ES/BE as a sensitivity check (n goes 16 -> 18 in the goal-window view).
Caveat: machine translation can blur theme words (e.g. 'renovacion' -> 'renovation' is fine, 'eolica' -> 'wind' is fine, but idioms and headings can be garbled).

## TRANSLATED ES/BE INCLUDED (14 Nov; ndc/notebooks/lts_translate.py, lts_vs_parliament.py --with-translated; data/processed/lts_text_translated/, lts_vs_parliament_profiles_with_translated.csv, ndc/figures/lts_vs_parliament_with_translated.png)
Models downloaded: Helsinki-NLP/opus-mt-es-en (312 MB) and opus-mt-fr-en (301 MB), plus sentencepiece and sacremoses. ES_1: 790 sentences -> 21,689 English words; BE_1: 1,826 sentences -> 48,390 words (headings under 25 characters dropped); ~3 min each on the Mac GPU.
Quality check: 6 random pairs per document read: fluent, theme words preserved (forest sinks, decarbonisation, renewables, electrification, CCS, heat/buildings); 0 sentences still look untranslated; one minor error (a date order: 'generate 2040 2 million jobs').
RESULTS with ES and BE (n=18 goal-window view, n=20 all-speeches view) vs WITHOUT (n=16 / 18): STABLE.
 P-A goal windows: median rho +0.26 (p=.007) [was +0.26, p=.012]; per theme: land_forest +.64, transport +.48, industry +.38, removals +.33, energy +.26, buildings +.25, instruments +.18, waste +.05, agriculture 0.00.
 P-B goal windows: own +0.51 vs others +0.34, own better in 16/18, p=.008 [was +0.51 vs +0.33, 15/16, p=.014]; ES own rho +0.57, BE +0.33.
 All climate speeches: P-A median +0.44 (p=.0002) [was +0.40]; P-B own +0.50 vs +0.37, 17/20, p=.004; ES +0.40, BE +0.43.
 P-C gaps almost unchanged: removals +2.23, land_forest +2.02, waste +1.21, buildings +0.98, agriculture +0.85, industry +0.54, instruments -0.32, transport -0.35, energy -0.73.

## ROUND 3 HYPOTHESES (overnight run, user asked for new questions; 2-hour cap, started 21:19 on 14 Nov). PRE-DECLARED before any of these numbers were computed.
Shared setup: nodes and EU collapse from ndc_common.py (first NDC, 154 nodes). Emission trend = annualised % change of total GHG excl. LULUCF (Climate Watch).
 PRIMARY window 2015->2019 (before COVID); SECONDARY 2015->2023. Tiny emitters (<1 Mt in 2015) excluded from trend tests (same rule as the pledge check).
H8 FIRM vs HEDGED WORDING -> DELIVERY. Do countries whose first NDC is written in firm language cut (or slow) emissions more than countries writing in hedged language?
 Firm terms (regex, case-insensitive): commit/commits/committed/commitment; unconditional(ly); binding; net zero / carbon neutral* / climate neutral*; economy-wide; absolute; 'will (reduce|achieve|cut|limit)'.
 Hedged terms: conditional (not 'unconditional'); subject to; provided that; international (support|finance|assistance|funding); business as usual / BAU; depend(s|ent|ing) on.
 Firmness = log((firm+1)/(hedged+1)). Test: partial Spearman of firmness with the 2015-19 trend, controlling log GDP per capita and the 2005-15 trend. ONE-SIDED, predicted NEGATIVE.
 Expected confound: hedging tracks poverty (conditional on finance) and poorer countries' emissions grow; the GDP control is meant for this. Hand-check: 10 random firm and 10 hedged matches.
H9 CONVERGENCE ACROSS ROUNDS. Do pledges become more alike over time (shared templates after the Paris rulebook)?
 To avoid Climate Watch's changing field set, re-embed each round using ONLY the 36 text fields present in all of indc, first_ndc, revised_first_ndc and third_ndc; countries present in all four rounds; EU joint texts collapsed per round.
 Statistic: mean pairwise raw cosine per round. PRIMARY contrast third_ndc minus first_ndc, ONE-SIDED predicted POSITIVE; 2,000 bootstrap resamples of countries.
 Secondary (two-sided): regional clustering = mean within-region minus between-region similarity; does it shrink from first to third?
 Threat: field fill rates and text lengths change between rounds; report median words per round.
H10 LANGUAGE NEIGHBOURS SHARE TRAJECTORIES (network test). On the k=5 language kNN network, is a country's 2015-19 trend correlated with the mean trend of its language neighbours?
 Statistic: Pearson r(own trend, neighbour mean trend), trends winsorised at the 2.5/97.5 percentiles. NULL 1: trends shuffled across all nodes. NULL 2 (PRIMARY): trends shuffled WITHIN World Bank region,
 so region-level similarity is kept and only within-region neighbour choice is tested. 5,000 permutations, ONE-SIDED positive. Comparison (descriptive): same statistic on the geography kNN network.
EXPLORATORY (labelled): pledge type (GHG target type field) vs trend; firmness vs being on track among the 13 checkable pledges; repeat H8 on 2015-23.

## ROUND 3 RESULTS (14 Nov evening; ndc/notebooks/ndc_round3.py, ndc_convergence.py, ndc_diffusion.py; data/processed/round3_firmness.csv, round3_h8_handcheck.csv)
Trend sample 135 of 154 nodes (19 tiny island emitters <1 Mt dropped).
H8 FIRM vs HEDGED WORDING: SUPPORTED, MODEST. Partial Spearman (ctl log GDPpc, 2005-15 trend) firmness vs 2015-19 trend = -0.18, one-sided p=.020; 2015-23: -0.18, p=.017.
 Robust to adding log words (-0.18) and region dummies (-0.20). Same sign in every income group (rho -0.19 to -0.39). Firm-rate alone -0.12, hedged-rate alone +0.09 (both halves contribute).
 HAND-CHECK (10 each): hedged matches 10/10 genuine (BAU baselines, finance conditions); firm matches only ~5/10 (misses: 'absolute emissions' as a ranking, 'commitments under Article 4.1', 'does not establish commitments', 'shown its commitment to combat climate change'). The firm list is noisy, so the effect is likely understated, but the claim should rest on the hedged side.
 Reading: countries whose pledges are hedged (conditional, BAU-relative) grew emissions faster even compared with countries of similar income and similar prior trend. Not causal: hedging may simply mark countries that EXPECTED growth.
 EXPLORATORY: 2015-19 median trend by pledge type: base-year +0.1%/yr (n=19), BAU-scenario +2.2 (58), intensity +2.1 (9), fixed level +1.9 (6), no GHG target +1.3 (31); confounded by income.
 EXPLORATORY: among the checkable pledges, on-track ones are NOT firmer (+0.29 vs +0.51; n=7 vs 15).
H9 CONVERGENCE: SUPPORTED. 36 shared fields, 78 countries in all four rounds. Mean pairwise cosine indc .620, first .622, revised .701, third .716; third minus first +0.093 [95% CI +0.067, +0.119], p=.0005.
 Holds among the 33 countries whose text length changed <1.5x (.660 -> .717). Regional clustering unchanged (+0.066 -> +0.062, diff -0.004 [-0.032, +0.018]): pledges grow alike everywhere, regions stay distinct.
 Caveats: 78 early third-round submitters only; Climate Watch's summaries are written by the same team (house style could converge); indc and first_ndc texts are mostly identical for these fields.
EXPLORATORY idea diffusion (77 countries, shared fields; % mentioning in first -> revised -> third NDC): Article 6/carbon markets 6 -> 56 -> 86%; methane 26 -> 39 -> 51; 1.5 degrees 9 -> 22 -> 35; gender 13 -> 34 -> 34;
 electric vehicles 1 -> 21 -> 30; net zero 1 -> 25 -> 29; circular economy 0 -> 12 -> 22; hydrogen 0 -> 8 -> 14; loss and damage 3 -> 4 -> 12; just transition 0 -> 1 -> 10.
 Neighbour exposure (did adopters have language neighbours that adopted earlier? within-region permutation): only Article 6 (adopters .47 vs .23, p=.001, survives Holm over 12); net zero .28 vs .17 (p=.14); others null.
 Article 6 caveat: the 'international market mechanisms' field may simply be filled more often in later rounds.
H10 LANGUAGE NEIGHBOURS SHARE TRAJECTORIES: WEAK. r(own trend, language-neighbour mean) = +0.19; shuffle-all p=.037; within-region p=.047 (borderline).
 Comparison: geography neighbours +0.25 (within-region p=.013), emission-profile neighbours +0.15 (p=.07). Reading: trajectories cluster geographically; writing alike adds little beyond being near.

## ROUND 4 (overnight, user said "do all of that"; started 21:30 on 14 Nov, 2-hour cap). PRE-DECLARED before computing.
H8b FIRM LIST v2 (replaces v1 after the hand-check found ~5/10 precision). Drop 'absolute' and noun/generic 'commitment(s)'. Firm v2:
 'commit(s|ted) to'; 'commitment to (reduc|achiev|limit|cut)'; unconditional(ly); binding; net zero / carbon neutral* / climate neutral*; economy-wide; 'will (reduce|achieve|cut|limit)'. Hedged list unchanged.
 Same test as H8 (partial Spearman with 2015-19 trend, ctl log GDPpc + 2005-15 trend, one-sided negative). Hand-check 10 new firm matches. v1 result kept on record.
H11 DID PLEDGES FIRM UP? Firmness v2 computed per round on the 36 shared fields (as in H9), countries present in first_ndc and third_ndc.
 PRIMARY: firmness rises from first to third NDC (paired Wilcoxon, one-sided). Descriptive: Spearman of first vs third firmness (persistence); change by first-NDC tercile,
 reported WITH the warning that regression to the mean alone makes low starters rise, so 'hedgers firmed up most' is NOT tested as a claim.
 EXPLORATORY: change in firmness (first->third) vs 2015-23 trend.
H12 HEDGING BEYOND INCOME PEERS: stricter version of H8 that does not assume a linear income effect. Statistic: Spearman(firmness v2, residual of 2015-19 trend after the 2005-15 trend);
 NULL: firmness shuffled WITHIN strata of income group x World Bank region (strata with <2 countries kept fixed), 5,000 permutations, one-sided negative. (Close cousin of H8: a robustness test, not new evidence.)
H13 PARLIAMENT CLIMATE ATTENTION vs EMISSIONS (ParlaMint, ~26 parliaments, 2015-2022; data/processed/parlamint/index_XX.csv.gz has every speech, so the denominator exists).
 Speeches: >=50 words, not chairperson. Climate attention = share of speeches with >=1 climate keyword (the existing broad list: climate, greenhouse, global warming, carbon, emission(s), decarbonis*, net zero, fossil fuel(s)), per country, averaged over years 2015-2019 that have data.
 PRIMARY: Spearman(attention 2015-19, emission trend 2015-19), partial on log GDPpc, ONE-SIDED negative (more attention, faster decline). n is small (~26): low power, report effect size.
 SECONDARY (two-sided): change in attention (mean 2020-22 minus mean 2015-17) vs trend 2017-2022.
 Expected confound: rich northern parliaments both talk more and cut more; the GDP control and EU membership (descriptive split) address this only partly.

## ROUND 4 RESULTS (14 Nov night; ndc/notebooks/ndc_round4.py, parliament_attention.py; data/processed/round4_*.csv, parliament_attention_vs_trend.csv, parliament_climate_attention_by_year.csv)
H8b firm list v2: STILL SUPPORTED, slightly weaker. Partial rho -0.16 (one-sided p=.034) for 2015-19; -0.17 (p=.027) for 2015-23. 39 of 135 countries have 0 firm-v2 matches.
 Hand-check of 10 firm-v2 matches: ~6/10 genuine (unconditional, 'committed to reducing', Canada's economy-wide target); 'economy-wide' is the weak term (also describes economic impacts or emission totals), 'binding' can refer to the global agreement.
 v1 -> v2 changes nothing qualitatively; the claim still rests mostly on the hedged list (10/10).
H12 within income x region strata (19 strata): Spearman(firmness v2, trend residual) -0.17 vs null mean -0.06, one-sided p=.064: NOT significant at .05.
 Reading: part of the H8 association is between-stratum (who is in which income/region group); within peers the sign holds but the evidence is weak.
H11 DID PLEDGES FIRM UP: SUPPORTED, MODEST. 95 countries (36 shared fields): median firmness first -0.61 -> revised -0.41 -> third -0.32; firmer in 53/95 (6 unchanged); paired Wilcoxon one-sided p=.019.
 Persistence first vs third low (Spearman +0.23): a country's hedging in 2015 says little about its hedging in 2025. Tercile changes not reported as a finding (regression to the mean).
 EXPLORATORY: change in firmness vs 2015-23 emission trend: Spearman +0.03 (n=79): firming up is not linked to emission outcomes.
H13 PARLIAMENT ATTENTION vs EMISSIONS: NOT SUPPORTED. 26 parliaments. Climate attention (share of speeches with a climate word) 2015-19 ranges from 0.6% (BIH) to 11% (NOR).
 Raw Spearman with 2015-19 trend -0.29, but attention tracks income (+0.73) and after log GDPpc the partial is -0.06 (p=.40). Secondary: change in attention vs 2017-22 trend partial -0.14 (two-sided p=.50).
 Descriptive: attention more than doubled (median 2.2% of speeches in 2015-17 -> 5.2% in 2020-22), rising in 24/26 parliaments.
 Reading: richer parliaments talk more about climate and richer countries cut more; talk adds nothing beyond wealth. Low power (n=26).

## PAPER GROUNDWORK (14 Nov night)
Figures at PNAS widths: ndc/figures/paper/fig1-fig4 (PDF + PNG) from ndc/notebooks/paper_figures.py (reads saved CSVs only; diffusion table now saved by ndc_diffusion.py to ndc_idea_diffusion.csv).
Numbers sheet: ndc/NUMBERS.md (every citable number -> script -> file; CSV-checked vs log-only marked).
CORRECTION: 'only 13 checkable first-NDC pledges' (said in the 14 Nov evening summary and PAPER_PLAN.md) was wrong: 19 checkable in the main set (24 before dropping <1 Mt), 13 of them needed real cuts after 2015. PAPER_PLAN.md fixed.
