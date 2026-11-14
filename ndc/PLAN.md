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
