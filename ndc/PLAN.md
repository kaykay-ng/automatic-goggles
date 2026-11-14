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
