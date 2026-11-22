# Final project plan — food trade, emissions and parliamentary talk

Deadline: Fri 27 Nov 23:59 (paper PDF <=6pp PNAS LaTeX, 3 slide PDF, 1/2-page reflection). Presentation Wed 2 Dec.
Group: 2 people.

## Design (Option A, Europe-restricted)
Nodes: ~29 European countries/regions covered by ParlaMint 5.0 (match to FAOSTAT country names; regions like
Catalonia/Basque/Galicia have no FAO trade data -> drop or merge into Spain).
- Network: FAOSTAT detailed trade matrix -> weighted directed country-to-country network, one layer per commodity
  group (meat, dairy, cereals, ...) and year slice (2015-2022). Needs backbone/threshold + null model (config model).
- Table: FAOSTAT Emissions_Totals (agrifood emissions), FoodBalanceSheets (food supply), per country-year.
- Text: ParlaMint-en.ana 5.0 (English machine translation, CC BY 4.0). Filter speeches on food/agriculture/climate
  (keywords AND/OR the pre-computed CAP topic; VALIDATE filter on a hand-labeled sample).

## Candidate research question (to sharpen)
Do countries that are close in the food-trade network talk about food and climate in similar ways, and does either
structure track emission profiles? Compare three groupings of the same countries: trade-network communities,
text clusters (BERTopic/LDA on filtered speech), and emission-profile clusters (table). Course hint: disagreement
between groupings is the interesting part.

## Checks the course expects
- Record encoder model + truncation/chunking rule.
- Validate sentiment (ParlaMint ships sentence-level sentiment: treat as an instrument, test on hand-read sample).
- Null models for network claims; don't read distances off t-SNE/UMAP.

## Data sources (HEAD-checked 11 Nov 2026)
- FAO Emissions_Totals_E_All_Data.zip  14 MB   https://bulks-faostat.fao.org/production/Emissions_Totals_E_All_Data.zip
- FAO FoodBalanceSheets_E_All_Data.zip 22 MB   https://bulks-faostat.fao.org/production/FoodBalanceSheets_E_All_Data.zip
- FAO Trade_DetailedTradeMatrix_E_All_Data.zip 428 MB  https://bulks-faostat.fao.org/production/Trade_DetailedTradeMatrix_E_All_Data.zip
- ParlaMint-en.ana 5.0  hdl.handle.net/11356/2006 (per-country .tgz, up to GB each; NOT yet sized)
- ParlaMint 5.0 plain text + TSV metadata hdl.handle.net/11356/2004 (smaller; likely enough)

## Schedule (today = 11 Nov)
- 11-13 Nov: download data (agree first), country matching, build trade networks, filter speeches.
- 14-17 Nov: network analysis (centrality, communities, nulls); text embeddings/topics; validation samples.
- 18 Nov (supervisor in room): bring first finding + figures.
- 19-23 Nov: join the three lenses, robustness, pick the one story.
- 24-26 Nov: write paper in Overleaf, slides, reflection; 25 Nov in room for feedback.
- 27 Nov: submit. Both members rehearse explaining every part before 2 Dec.

## FAOSTAT profile (11 Nov, notebooks/profile_faostat.py -> data/processed/)
- All 26 sovereign ParlaMint countries matched by M49 code in all three tables (no name-matching needed).
  NOT in ParlaMint: Germany, Ireland, Switzerland, Russia, ... (Germany is a major trade hub -> state as limitation).
- Emissions: CO2eq (AR5), FAO TIER 1 source, no gaps 2015-22. Has agrifood stage split: Farm gate, Food Processing,
  Food Transport, Food Retail, Household Consumption, Packaging, Waste, Land-use change. (UNFCCC source also exists; not used yet.)
- Food balance: 120 items, 2010-2023, kcal/capita/day, protein, fat, production, import/export.
- Trade: 6.6M rows scanned, 656k kept, 511 commodities, all 650 ordered pairs have trade -> the graph is COMPLETE:
  must use thresholds/backbone (e.g. top-k, disparity filter) and a null model; commodity-group layers will be sparser.
- Next: map 511 trade items to commodity groups (meat/dairy/cereals/...), build networks.

## ParlaMint 5.0 sizes (HEAD-checked 11 Nov, www.clarin.si/repository/xmlui/bitstream/handle/11356/...)
- 11356/2004 original language, per country ParlaMint-XX.tgz: 26 countries = 5.8 GB total (LV 50 MB ... GB 520 MB). NOT English.
- 11356/2006 English MT + annotation, per country ParlaMint-XX-en.ana.tgz: 26 countries = 56 GB total
  (LV 539 MB, ES 828, FI 845, BA 882, PT 1.0 GB ... GB 5.3 GB, HR 4.2, NO 4.2, RS 3.9, SI 3.5). Disk free: 87 GB.
- ParlaMint-5.0.tgz (36 MB) = sample data + scripts only.
- Unknown: whether CAP topic + sentiment are in 2004 (original) or only in .ana files -> check inside one small country first.

## Latvia pilot findings (11 Nov, data/raw/parlamint_pilot/)
- Download speed ~20 MB/s (566 MB in 27 s) -> all English .ana tgz (56 GB) ~ 47 min of transfer.
- BUT extracted, LV-en.ana grows 566 MB -> 5.2 GB (TEI.ana 2.6G, vert 1.3G, conllu 1.1G, txt 269M). Full extraction of 26
  countries ~ 0.5 TB: impossible. => stream and keep only the plain-text part:
  curl ... | tar -xz --wildcards '*ParlaMint-XX-en.txt/*'   (transfer all, store ~10%)
- ParlaMint-XX-en.txt/<year>/ contains per sitting:
  *.txt        speech_id <TAB> English text (transcriber comments in [[ ]])
  *-meta.tsv   per speech: Date, Speaker role/party/party orientation/gender/MP/minister, Topic (CAP code, e.g. Mix)
  *-ana-meta.tsv per speech and per sentence: Senti_3 (Positive/Negative/Neutral), Senti_6, Senti_n (1-5 score), Sents, Words, Names
- Topic taxonomy (CAP-based): argic, envir, energ, trade, lands, trans, ... "mixed"/"other" exist. Topic is predicted per speech by a model.
- Original-language release (11356/2004) also has Topic + speaker metadata in *-meta.tsv (not sentiment? not checked).
- Machine translation: Latvian -> English; mention in Methods.

## Trade networks v0 (11 Nov, notebooks/build_trade_networks.py -> data/processed/networks/, figures/trade_*.png)
- 9 commodity groups from CPC prefix (cereals, fruit_veg, pulses_spices, oilseeds_oils, sugar_sweets, meat, dairy_eggs,
  beverages, feed_byproducts) + all_food. Tonnes only (live animals excluded); fish not in this FAO matrix.
- Weight = importer-reported tonnes (exporter mirror fills gaps), mean/yr 2015-22. Complete graphs (94-100% dense) ->
  disparity-filter backbone (a=0.05) keeps 84-106 of ~650 edges.
- Louvain communities (seed 42) on backbone: 3-5 communities, Q = 0.15 (fruit_veg) .. 0.41 (feed). all_food: Q=0.32, 4 comms:
  {Nordic/Baltic+PL+CZ}, {Balkans+HU+IT+AT}, {ES,PT,GR,BG,TR,UA}, {FR,NL,BE,GB}. Geographically sensible.
- Layers disagree: adjusted Rand between layers 0.04-0.66 (fruit_veg and pulses most distinct from cereals/meat).
  -> candidate finding: which commodity layer's communities match political-language clusters?
- TODO: null model (configuration / strength-preserving) to test Q and ARI; stability over years; node attributes from
  emissions table (per-capita, stage split) and FBS (kcal, animal share).

## Null model + attributes v0 (11 Nov, notebooks/null_and_attributes.py -> data/processed/networks/*.csv, country_attributes.csv)
- Null = strength-preserving, geography-blind (pairs ~ out_i * in_j), 200 draws/layer, same backbone+Louvain.
  Observed Q (0.15-0.41) >> null (~0.00-0.03) in all 10 layers, p=0.005 (floor with 200 draws). z-scores are meaningless
  (null sd ~ 0). CAVEAT: this null is weak -- it has no geography, so beating it mostly says "trade is regional".
  TODO stronger null: gravity-type (distance, e.g. CEPII GeoDist) or EU/Schengen membership as covariate.
- Attributes (2015-22 means): agrifood tCO2eq/capita (1.6-9.1), livestock share of agrifood emissions, farm-gate share,
  land-use-change share, kcal/cap/day, animal share of kcal, log population.
  DATA FLAG: Latvia 'Agrifood systems' halves in 2021 (17.8->10.3 Mt in FAO series) -- check, probably land-use change.
- Communities vs attributes (eta^2, permutation p): all_food: emissions/capita 0.57 (p=.001), animal kcal share 0.50 (.001),
  livestock share 0.43 (.007). Strongest layers: oilseeds_oils (0.72) and sugar_sweets (0.71) for emissions/capita.
  Weak: fruit_veg, cereals. ~29 of 70 tests p<.05 (uncorrected; ~3.5 expected by chance; tests are correlated).
  CAVEATS: n=26, 3-5 groups (chance eta^2 ~ 0.12), communities are geographic -> confounded with wealth/region.
  TODO: Holm/BH correction, control for region/GDP (partial test), which community is high vs low, year stability.

## Cross-layer modularity (notebooks/cross_layer_modularity.py; figures/cross_layer_modularity.png)
- Q of layer A's Louvain partition on layer B's backbone; mean diagonal 0.30, mean off-diagonal 0.21 (~70% retained).
- Permutation null (labels shuffled, same sizes): 89/90 off-diagonal cells p<0.05; only meat->cereals (Q=0.04, p=0.065) not.
- Asymmetry: partitions explain feed/oilseeds/dairy networks well (Q up to 0.40) but fruit_veg network poorly under any partition (0.06-0.12).
- Contrast with ARI (0.04-0.66): groupings differ in detail, but share a common backbone (likely geography, not tested).
- Earlier null (strength-preserving): every layer Q_obs >> null (~0.00-0.03).

## Geography-aware null + region control (11 Nov, notebooks/gravity_null.py)
- Gravity null (fitted distance decay beta 0.49-0.90 and EU effect gamma -0.29..+0.21, capital-to-capital distances):
  observed Q still > null in all 10 layers (p=0.005 floor) BUT the gap shrinks a lot where distance explains structure:
  oilseeds_oils 0.37 vs 0.19, cereals 0.35 vs 0.13, meat 0.23 vs 0.12. Clear structure beyond geography+size+EU:
  feed_byproducts 0.41 vs 0.02, sugar_sweets 0.29 vs 0.01, fruit_veg 0.15 vs 0.01, dairy 0.30 vs 0.05, pulses 0.27 vs 0.04.
- Region control (North/West/South/East): REGION alone explains emissions/capita as well as trade communities
  (eta2 0.59 vs 0.57), animal-kcal share 0.54 vs 0.50, livestock share 0.54 vs 0.43. Permuting community labels within
  regions: only 8/70 tests p<.05 (3.5 expected), mostly log_population (communities split big/small economies).
  => "trade communities differ in emissions" is mostly a REGIONAL effect. Honest negative/qualified result.
- Implication: the interesting question is NOT trade-vs-emissions alone. Move to the 3-lens comparison: do countries'
  parliamentary food/climate language and trade communities agree, and where they disagree, beyond region?
- Caveats: GB treated non-EU; NO/IS EEA not EU; capital distances are proxies; 4 coarse regions with n=26.

## Exporters vs emitters (11 Nov, notebooks/exporters_vs_emitters.py -> data/processed/country_trade_emissions.csv)
- WORLDWIDE exports/imports (all partners) per country from raw FAO trade matrix, tonnes/yr 2015-22 (double counts raw+processed items).
- Absolute: exports vs farm-gate emissions rho=+0.71, but population drives both (pop vs emissions +0.84, pop vs exports +0.83);
  size removed (residuals on log pop): rho=0.00. Per capita: exports pc vs emissions pc +0.16 (ns); NET exports pc vs
  emissions pc +0.06 (ns); net exports pc vs emissions per 1000 kcal eaten +0.10 (ns).
- By commodity: meat net exports pc vs livestock emissions pc rho=+0.49 (p=.012; top DK, NL, BE, ES);
  dairy/eggs +0.42 (p=.031; EE, LV, SI, DK); cereals +0.21 (ns). => relationship is COMMODITY-SPECIFIC; aggregate tonnage hides it.
- Caveats: n=26; 3 tests in Q3 (uncorrected); NL/BE are re-export hubs; production-based emissions (not embodied in consumption);
  Latvia and Iceland farm-gate per capita very high (4.6, 5.6 t) -- likely drained organic soils, CHECK; Germany and Ireland
  (big livestock exporters) not in ParlaMint -> missing from this question.

## Meat/dairy deep dive (11 Nov, notebooks/meat_dairy_deep_dive.py; figures/netexp_vs_livestock_*.png)
Net exports per person vs livestock emissions per person (Spearman, n=26):
- meat +0.49 (perm p=.017, boot CI [+0.06,+0.79]); dairy_eggs +0.42 (p=.029, CI [+0.06,+0.68]); meat+dairy +0.58 (p=.003, CI [+0.27,+0.78]).
- Robust: leave-one-out meat+dairy +0.53..+0.64 (DK most influential); without NL/BE +0.52; each year 2015-22 +0.56..+0.60;
  enteric+manure only +0.59; controlling own animal-protein consumption +0.58; controlling region +0.64; both +0.67.
- Reading: livestock emissions per person are higher where animal-food production exceeds domestic consumption, i.e.
  production-based accounting puts the emissions of foreign consumers on exporters. Associational; partly definitional
  (surplus producers export). Dairy/eggs: note EE, LV, SI high exports; Iceland high emissions but ~0 net exports (outlier).
- Open: still 26 countries, no Germany/Ireland; meat and dairy are 2 of ~3 related tests (report meat+dairy as primary,
  pre-declare); causal claims avoided.

## Food-use profile (11 Nov, notebooks/food_use_profile.py -> data/processed/country_food_profile.csv)
- Self-sufficiency (production/domestic supply, FBS 2015-22): cereals lowest IS, NL, PT; highest BG, LV, UA (2.7-3.1).
  Meat highest DK 3.35, NL 2.6, BE 2.4; milk highest EE 1.41, LV 1.31; fruit highest GR, ES, TR; lowest IS, SE, NO.
- Clusters on SUPPLY profile (12 features): best k=2, silhouette 0.40: {BE, DK, NL} = livestock-export hubs (meat SS 2.4-3.4,
  feed-heavy, import fruit/veg) vs everyone else; k>=3 silhouette ~0.24 (weak). DIET profile (kcal shares): k=2, sil 0.27:
  {BA, RS, SI, TR, UA} cereal/veg heavy, little meat/dairy vs rest; k>=3 ~0.18 (no structure).
- Agreement with trade communities / region: ARI ~0 (-0.13..+0.15), no permutation p<0.05 (region vs supply p=.051).
  => the 'grain exporters / feed-heavy livestock / import-dependent' typology does NOT emerge as discrete clusters;
  use self-sufficiency as CONTINUOUS variables (esp. per group), not as categories.
- Candidate use: relate parliamentary attention to self-sufficiency gaps (e.g. fruit/veg SS, cereals import dependence).

## ParlaMint-en text download COMPLETE (finished 14 Nov log time; all 26 countries, no FAILED lines)
- data/raw/parlamint_en_txt/ParlaMint-XX-en.txt/<year>/  19 GB total. Italy/Slovenia stalled once each; the stall timeout in
  notebooks/fetch_parlamint_en_txt.sh retried them successfully.
- Coverage varies: e.g. FR only 2017-2022, ES 451 sittings, PL 687; AT/NO/RS/UA go back to the 1990s-2000s. Analysis window 2015-2022.
- Per sitting: .txt (speeches), -meta.tsv (speaker/party/Topic), -ana-meta.tsv (sentiment per speech/sentence).
- NEXT: parse all into one table (country, date, speaker, party, topic, sentiment, text), filter food/agri/climate speeches,
  hand-label a validation sample.

## ParlaMint skim (14 Nov; notebooks/parse_parlamint.py, skim_parlamint.py -> data/processed/parlamint/)
- 6,046,655 speeches, 928M words, 26 countries, 2015-2022 (FR 2017-22 only). index_XX.csv.gz (no text) + flagged_XX.csv.gz (text).
- First-skim keywords (NOT validated): climate in 120k speeches (2.0%), food/agri 216k (3.6%), both 24.9k (0.41%),
  livestock words 44k; topic label=Agriculture 116k. Climate-keyword speeches grow 9.1k (2015) -> 24.6k (2021).
- By country: 'both' ranges 89 (UA) .. 3109 (GB); share highest SE (2.1%), NO 1.7, IS 1.4, AT 1.3; lowest UA .05, BG .13, EE .18, TR .19.
  Substantive speeches (>=50 words) with climate+food: >=100 in 23 countries, >=300 in 21, >=1000 in only 8. Food/agri alone: >=1000 in 25.
- Topic label vs food keyword overlap partial: 76% of Agriculture-labelled speeches have a food keyword; only 40% of food-keyword
  speeches are labelled Agriculture -> the choice of filter matters; use union + measure recall on a random hand-labelled sample.
- DECISION: main text corpus = food/agriculture speeches (ample in all 26); treat climate as a DIMENSION (share, framing, sentiment)
  within it, not as a hard filter (too thin for UA, BG, EE, CZ, ...).
- Emissions intensities (FAO, 3 MB) downloaded: 14 foods (cattle/pig/chicken/sheep/goat/buffalo meat, milk, eggs, rice, cereals excl. rice).

## Three-topic split from flagged text (14 Nov; notebooks/split_topics.py -> data/processed/parlamint/topic_flags_XX.csv.gz)
- Lumped 'food' list split into AGRI (agricultur*, farm*, crop, harvest, fertili*, livestock, cattle, CAP, fisher*) and
  FOOD (food, nutrition, hunger, diet, grocer*, supermarket) from saved flagged text; CLIMATE unchanged. Substantive (>=50 words):
  agri 157k, food 83k, climate 115k. Overlaps: agri&food 37k, agri&climate 21k, food&climate 12k, all three 7.2k.
  One-topic-only: agri 107k, food 41k, climate 89k -> topics are mostly distinct; splitting was worth it.
- Countries with >=300 substantive speeches: agri 26/26, food 25, climate 25; agri&climate 20 countries; food&climate only 14.
  Thin: BA, LV (food 608, food&climate 27), ES, UA. Largest: GB, NL, NO, FR, TR.
- LIMITATION: only speeches already matched by the first lists are searchable; food-availability vocabulary (prices, shortage,
  security, imports) needs a full re-parse of raw text with a wider FOOD list.
- Cloud: user created a cloud environment; start_session could not launch it from this window -> brief saved in CLOUD_TEST_PROMPT.md.

## Cloud decision (14 Nov): stay LOCAL
- Cloud test passed (Ubuntu VM, 4 CPU, 15 GB RAM, 25 GB free; FAOSTAT rebuild + LV parse exact match) but: no push-back from the
  test session (GitHub not linked), command limit ~10 min + 30 min background (full ParlaMint transfer ~63 min needs chunking),
  ephemeral VM, 4 CPU and no GPU (slower than the laptop for embeddings). Long jobs are already done locally.
- Fixed notebooks/fetch_parlamint_en_txt.sh to pick bsdtar (--include) vs GNU tar (--wildcards). Tested on macOS only.
- Revisit only for a long unattended job: link GitHub to the environment, set network to Full, run in chunks.

## Do imports hide emissions? (14 Nov; notebooks/embodied_emissions.py -> data/processed/embodied_emissions_by_{country,food}.csv)
- Method: PBA (FAO farm-gate) - exports*own intensity + imports*exporter's intensity (FAO emissions intensities, kg CO2eq/kg).
  Foods: cattle/pig/sheep/goat/chicken/buffalo meat, hen eggs, cereals incl. rice. NOT covered: dairy products, fruit/veg, oilseeds,
  sugar, processed, fish. 0.1% of import tonnage needed imputed partner intensity.
- Result: trade-adjusted footprint differs from production-based by -39% (UA) to +73% (GR). Net importers of embodied emissions:
  GR +73%, IT +57%, PT +42%, BA +34%, SE +33%, NL +31%, NO +20%. Net exporters: UA -39, PL -36, BG -32, DK -32, LV -30, HU -28.
  Rank of kg CO2eq/person moves a lot: GR up 18 places, IT 15, SE 12; BG down 13. Spearman(PBA_pc, CBA_pc) = 0.49.
  Meat dominates: of all embodied imports (70 Mt) meat is 57 Mt, cereals 13, eggs 0.5.
- Mostly an accounting identity (sign follows net trade); import dependence vs shift only +0.33 (exports matter too).
- NOT mechanical: median ratio (import-weighted intensity / home intensity) ~1 (cereals 0.85, pig 0.93, cattle 0.96, chicken 1.01,
  sheep 1.00): countries do NOT systematically import from dirtier producers; the hidden amount comes from VOLUME, not source.
- CAVEATS: FAO intensities are farm-gate (no feed, no land-use change) -> pig/chicken look clean (median 3.6 and 0.8 kg/kg vs cattle 35);
  NL/BE re-exports valued at own intensity (NL imports = 92% of its footprint, CBA probably understated); import_dep unreliable for small/hub
  economies (SI 1.0, NL 0.9); product-weight vs carcass-weight not reconciled; 8 yr means.
- NEXT: use shift_pct and E_imp_pc as country variables in the language test (do countries with large hidden imported emissions talk
  less about agriculture/climate?).

## OPTION A chosen (14 Nov): do countries talk about what they hide? -- PRE-DECLARED before running (no peeking)
Question: does what a parliament talks about (agriculture, food, climate) track the country's position in the food system
(net trade, self-sufficiency, emissions hidden in imports)?
Text measures (per country, 2015-2022, substantive speeches >=50 words, chair speeches excluded; keyword lists from split_topics.py):
- attention_X = speeches mentioning topic X (agri / food / climate) per 10,000 substantive speeches.
- climate_in_agri = share of agriculture-keyword speeches that ALSO mention climate (framing; removes volume effects).
Country variables: net meat+dairy+eggs exports per person; food self-sufficiency (mean log2 of production/supply for cereals, veg, fruit,
meat, milk, eggs, clipped [-2,2]); shift_pct (trade-adjusted vs production-based footprint, + = importer of hidden emissions).
Controls: log population; region (North/West/South/East; permutation of x within regions).
PRIMARY hypotheses (3; Holm correction across these 3 only):
 P1  climate_in_agri  vs shift_pct              predicted NEGATIVE (hidden importers frame farming less in climate terms)
 P2  attention_agri   vs net meat+dairy exports pc  predicted POSITIVE (exporters talk about farming more)
 P3  attention_food   vs food self-sufficiency  predicted NEGATIVE (less self-sufficient -> more food talk)
Everything else is EXPLORATORY and labelled as such. Report effect sizes with bootstrap CIs, not only p-values.
Known threats: n=26; keyword measures unvalidated (hand-label 100 speeches next); corpus composition differs by country
(plenary vs committee, length of speeches); NL/BE re-exports; translation noise (machine-translated English).

## OPTION A RESULTS (14 Nov; notebooks/country_text_vs_food_system.py -> data/processed/country_text_and_food_system.csv)
PRE-DECLARED tests, n=26 countries, Holm over 3, controlled p = log pop partialled + x permuted within regions:
- P1 climate_in_agri vs shift_pct (pred. NEGATIVE): rho=+0.38 (raw p=.057), partial +0.37, controlled p=.089, Holm .27, CI [-0.06,+0.72]. WRONG DIRECTION, n.s.
- P2 attention_agri vs net animal exports pc (pred. POSITIVE): rho=-0.23, controlled p=.36. Wrong direction, n.s.
- P3 attention_food vs food self-sufficiency (pred. NEGATIVE): rho=-0.26, partial -0.28, controlled p=.11, Holm .27. Right direction, n.s.
=> NONE of the three pre-declared hypotheses is supported. CIs are wide (about +-0.35), so this is INCONCLUSIVE, not evidence of no effect.
Exploratory grid (42 cells, 6 significant vs ~2 expected): climate talk and climate_in_agri correlate with CBA_pc (trade-adjusted
footprint per person; rho +0.65 and +0.76), topic_label_agri negatively with E_imp_pc (-0.43). NOT corrected; CBA_pc likely proxies wealth/diet.
Descriptive pattern: climate_in_agri is highest in SE .29, DK .24, ES .24, AT .23, NO .22, NL .21 and lowest in UA .02, BA .04, LV .04, BG .05,
PL .06 -> a north/west vs east gradient, i.e. looks regional/economic more than food-system related.
Measurement caveats: keyword measures not yet validated; corpora differ (11.9k substantive non-chair speeches BA .. 492k GB).

## ROUND 2 (14 Nov): direct measure + country-year panel -- PRE-DECLARED before running
Honesty note: round 1 was null, and we then LOOKED at an exploratory grid (climate talk vs hidden emissions +0.42, E_imp_pc +0.35).
Round 2 hypotheses are therefore informed by seen data and are NOT a clean confirmatory test; say so in the paper.
(A) DIRECT MEASURE: talk that is specifically about outsourced / consumption-side emissions, from the raw text (full re-parse):
  direct_A terms: carbon leakage, embodied/embedded carbon|emission(s), imported emission(s)/carbon/deforestation, consumption-based,
    (carbon|climate|ecological|environmental|water|food|consumption) footprint, carbon border / border (carbon|adjustment|tax), CBAM,
    deforestation, emissions abroad/elsewhere/overseas/outside.
  direct_B: 'import*' within 12 words of emission|carbon|climate|greenhouse (only checked in speeches that already mention climate words).
  Measure: direct_share = speeches with direct_A or direct_B per 1,000 CLIMATE speeches (substantive, non-chair).
  Precision of the terms will be CHECKED BY READING a sample of matches before any test (report the false-positive rate).
  Cross-section (n=26): D1 direct_share vs shift_pct, predicted POSITIVE (countries hiding more emissions in imports talk more about
  outsourced emissions). Controlled p (log pop partialled, x permuted within region) is the primary p. Single primary test, no correction.
(B) PANEL (country-year 2015-2022, country FE + year FE, cluster bootstrap over countries, 2000 resamples):
  PP1 climate_in_agri ~ net animal-food exports pc (yearly), predicted POSITIVE (more exporting -> more climate framing; importing hides it)
  PP2 attention_agri  ~ net animal-food exports pc, predicted POSITIVE
  PP3 attention_food  ~ food self-sufficiency (yearly), predicted NEGATIVE
  Holm over PP1-PP3. Yearly hidden-emission shift is NOT available (embodied estimate is an 8-yr mean) -> net exports is the proxy.
Caveat: only ~8 years; within-country variation in trade is small; France has 6 years; ParlaMint ends mid-2022 (2022 partial).

## ROUND 2: measurement check FAILED for v1 patterns -> v2 (14 Nov; BEFORE any round-2 test was run)
Read 10 random matches per category (single reader = Claude; a teammate should re-label independently):
- IMPORT-near-climate: 0/10 on target. BUG: 'import*' matched 'important/importance' (12,420 of 16,047 matches).
- LEAK (carbon leakage, border terms): 6/10 on target; false: 'cross-border tax units', municipal 'border adjustments', 'overborder taxation'.
- FOOT (footprint terms): 3/10 about imports/consumption; 7/10 generic footprint (personal, ministers, devices).
- DEFOR: 3/10 about imported commodities; 7/10 domestic/general.
v2 changes (parse_measures.py): import forms explicit (import, imports, imported, importing, importer(s), importation); LEAK drops generic
'border tax/adjustment', keeps carbon leakage, carbon/CO2/climate border, border adjustment mechanism, CBAM; FOOT keeps consumption-based,
embodied/embedded carbon|emissions, imported emissions/carbon/deforestation, emissions abroad/elsewhere/overseas, and 'footprint' ONLY within
12 words of import*/abroad/overseas/outsourc*/supply chain/trade; DEFOR only within 15 words of import*/supply chain/soy/palm/beef/commodit*/trade/
Amazon/Brazil/Indonesia. D1 hypothesis (direct_share vs shift_pct, predicted positive) stays as pre-declared; only the measure's definition changed.
Next: re-parse, read a FRESH sample of v2 matches, and only if precision is acceptable (>=70% on target) run D1.

## ROUND 2: v2 precision check (14 Nov, fresh sample of 12 per category, seeds 101-104; single reader = Claude; BEFORE running D1)
- LEAK 12/12 on target (CBAM, carbon border adjustment, carbon leakage; mostly industry competitiveness, not food).
- FOOT 10/12 (false: 'embedded carbon' in building construction; generic 'ecological footprint of food trade').
- DEFOR ~10-11/12 (borderline: domestic government's Amazon policy).
- IMPORT-near-climate (NEAR) ~3-4/12 -> FAILS the >=70% rule: mostly ENERGY imports (oil, coal, fossil fuels), 'greenhouse' = glasshouse, 'importer'.
DECISION (per the rule set earlier): drop NEAR. direct measure v2 = speeches with LEAK or FOOT or DEFOR, per 1,000 climate speeches.
Counts are SPARSE: 1,851 matches in total with NEAR; without it ~1,000 (leak 370, foot 337, defor 539 incl. overlap). Countries with >=30 v2 matches (any type): 11 of 26
(BG, PL, DK, IS, FI, BE, NO, SE, NL, FR, GB). SI 3, RS 3, UA 5, EE 11. D1 on 26 countries will mostly rest on tiny counts -> low power; the >=30 sensitivity (n~11) has almost none.
Sensitivity (exploratory): restrict direct matches to speeches that also contain an agriculture or food keyword.

## ROUND 2 RESULTS (14 Nov; notebooks/round2_tests.py, parse_measures.py v2, yearly_food_system.py; data/processed/country_direct_measure.csv)
D1 (pre-declared; direct_share = speeches with LEAK|FOOT|DEFOR per 1,000 climate speeches, vs shift_pct, predicted positive), n=26:
  rho=-0.03, partial -0.10, controlled p=.82, CI [-0.38,+0.34]. NULL. Sensitivity >=30 matches (only 8 countries): CI [-1.0,+0.75] = uninformative.
  Exploratory (matches that also mention agri/food): rho=+0.07, p=.93. Null.
PANEL (206 country-years, 26 countries, country+year FE, cluster bootstrap over countries; std_beta in within-country SDs):
  PP1 climate_in_agri ~ net animal exports pc: +0.002 [-0.19,+0.17], p=.99.  PP2 attention_agri ~ net animal exports: +0.008 [-0.14,+0.20], p=.89.
  PP3 attention_food ~ food self-sufficiency (pred. negative): +0.068 [-0.16,+0.28], p=.54 (wrong direction, n.s.). Holm all 1.0.
  Within-country variation is tiny (net exports SD 7.7 kg/person vs 87 between; self-sufficiency 0.05 vs 0.38) -> panel speaks only to small within-country changes.
Descriptive (direct talk per 1,000 climate speeches): highest BE 26.9, FR 18.9, GB 17.2, BG 13.3 (13 matches), NL 12.8, NO 10.0, ES 8.5; lowest TR 0.4,
  HR 0.8, GR 1.0, HU 2.1 and zero in BA, RS, LV. GR (+73% hidden) and IT (+57%) are LOW; BE/FR/GB (net exporters or near zero) are HIGH.
  Matches read in the samples point to POLICY EVENTS: EU carbon border adjustment (CBAM), France's national strategy against imported deforestation,
  UK Environment Bill due-diligence on forest-risk commodities, EU deforestation regulation. Talk seems driven by policy agendas, not by exposure to hidden emissions.
CONCLUSION so far: no support for 'hidden emissions -> talk' in 4 pre-declared tests (3 round 1, 1 round 2 + 3 panel). Moderate effects (|rho|~0.3) can't be excluded at n=26;
  strong effects (|rho|>0.4) are unlikely. Direct measure too sparse for most countries (only 8 have >=30 matches).

## ANGLE B chosen (14 Nov): do countries that trade more talk alike about food & agriculture? -- PRE-DECLARED before building
(Hidden-emissions hypothesis closed: no detectable effect in 4 pre-declared tests; angle A (Ukraine shock) declined by user.)
Question: is language similarity between two parliaments, on food and agriculture, related to how intensely the two countries trade,
beyond distance, EU membership, region and source-language family?
Language measure: pool = substantive (>=50 words), non-chair speeches 2015-2022 matching the AGRI or FOOD list (split_topics.py lists; text from
flagged files, so 'livestock'/'cattle'-only speeches are missed). Random sample of up to 1,500 speeches per country (seed fixed; BA smaller).
Embedding: sentence-transformers all-MiniLM-L6-v2; max_seq_length 256 -> speeches cut into passages of <=180 words on sentence boundaries,
passage vectors averaged, then normalised (week 7 rule). Country vector = mean of its speech vectors, MINUS the global mean (removes the shared
'parliament' component). Language similarity_ij = cosine of country vectors. 26 x 26 = 325 dyads.
Trade measure: all-food trade volume, symmetrised log(1 + tonnes_ij + tonnes_ji) (worldwide tonnage not needed: use the 26-country matrix).
PRIMARY test (one): MRQAP (permute node labels jointly, 5,000 permutations) of language similarity on log trade volume, with controls:
  log distance (capitals), both-in-EU, same region, same source-language family (Germanic, Romance, Slavic, Baltic, Uralic, Greek, Turkic, other).
  Prediction: coefficient on log trade POSITIVE.
SECONDARY (exploratory, Holm over the 9 commodity layers): same regression per commodity layer.
STRUCTURE: compare three partitions of the 26 countries - language clusters (Ward on 1 - similarity, k by silhouette), trade communities (all_food Louvain),
  region, language family - by adjusted Rand index with permutation p; and within-vs-between community mean similarity, permuting trade labels within regions.
VALIDATION (course requirement), done BEFORE the tests: (1) split-half reliability: random halves of each country's speeches -> two similarity matrices ->
  correlation (Mantel); (2) read the 5 nearest language neighbours of 3 countries plus a few of their top speeches; (3) check for machine-translation artefacts:
  does similarity cluster by source-language family more than by anything else?; (4) bootstrap CI over speeches for the key correlation.
SUPPORTING (if time): BERTopic topic-share vectors per country as a second language measure (Jensen-Shannon), compare with the embedding measure.
Threats: n=26 countries; translation noise and shared MT pipeline; embeddings capture topic AND style and names; country corpora differ (plenary vs committee);
trade and language may both follow geography/politics (controls only partly handle it); all trade and text variables are time averages.

## ANGLE B RESULTS v0 (14 Nov; notebooks/b_pool_and_embed.py, b_language_network.py; data/processed/b_language_similarity.csv)
Data: 37,848 agri/food speeches (<=1,500 per country, BA 348), 159,510 passages (4.2 per speech), all-MiniLM-L6-v2 (max_seq_length 256, 384-d), 7 min on MPS.
VALIDATION (before the tests): split-half reliability r=0.99 (sampling noise is tiny; says nothing about validity). Nearest neighbours sensible: NO: DK .56, SE .55, FI .33;
 GR: ES .34, IT .34, TR .22; PL: CZ .36, HU .25, UA .25; BA: RS .44, HR .34, SI .30; GB (native English, not translated): NL .35, BE .32, DK .28 -> GB is not an outlier.
 Similarity is organised by region and source-language family: same family within +0.18 vs between -0.09 (p=.0002); same region +0.14 vs -0.10 (p=.0002).
 => cannot separate real regional discourse from machine-translation style; family/region are entered as controls.
PRIMARY (pre-declared, DSP-MRQAP, 325 dyads, R^2=0.51): language similarity ~ log trade: beta=+0.154, p=.0004 (predicted positive: YES).
 Controls: log distance -0.267 (p=.0002), same region +0.313, same language family +0.322, both EU 0.000 (p=.99). Raw Spearman trade-similarity +0.345.
SECONDARY (exploratory, Holm over 9 layers): positive in all 9; significant after Holm: beverages +.205, dairy_eggs +.164, cereals +.159, pulses +.140,
 fruit_veg +.130, oilseeds +.127, sugar +.112; not meat (+.067, p=.12) or feed (+.086, Holm .078). Layers are correlated, not independent evidence.
PARTITIONS: language clusters k=2 (silhouette .22, weak): {BE DK EE FI FR GB IS NL NO SE} vs the other 16. ARI vs trade communities +0.25 (p=.001), region +0.36,
 language family +0.21, EU -0.02 (n.s.). Within-minus-between language similarity for trade communities +0.197; permuting labels within regions p=.0006.
CAVEATS / TO DO (robustness): size control (log population product); drop fisheries speeches (Nordic similarity may be fisheries; fish is NOT in the FAO trade matrix);
 leave-one-region-out / drop Nordic block; gravity residual ('excess trade') as the trade measure; period split 2015-18 vs 2019-22; TF-IDF as alternative language measure;
 BERTopic topic profiles as a second language measure; interpret what the similarity captures (topics vs style vs names); causal direction unknown.

## ANGLE B: how much is geography? (14 Nov, EXPLORATORY, not pre-declared; notebooks/b_geography_check.py)
R^2 of language similarity across 325 pairs: distance alone .279; + same region .404; + language family .494; + EU .495; + log trade .513 (trade adds +.018 = 3.5% of the full model's R^2).
Trade alone .136. Geography + size explain 71.9% of the variation in log trade (corr(log trade, log distance) = -0.45).
Trade coefficient (standardised, DSP-MRQAP): no controls +.37; distance only +.17; + region +.15; + family+EU (pre-declared model) +.154; + population product +.35 (p=.0004);
 + lat/lon gaps +.31 (p=.002); + region-pair FE +.32 (p=.003); + COUNTRY fixed effects +.24 (p=.086, not significant at .05); region-pair + country FE +.25 (p=.092).
Excess trade (gravity residual, geography and size removed) vs similarity: +.215 (p=.0002); with geography/family controls +.186 (p=.0006).
Within vs across regions (partial Spearman, distance controlled): same-region dyads (n=80) +.38; cross-region (n=245) +.16; inside East +.54 (n=10), South +.49 (n=36), North +.28 (n=28).
READING: language similarity is mostly geography/family (R^2 ~.49 without trade). Trade has a small, positive, fairly stable independent association (beta .15-.35), stronger WITHIN regions,
 but it loses significance when each country gets its own baseline (n=26 limits power). Region and language family cannot be separated from translation style with this data.

## ANGLE B: food-system common cause + topic model (14 Nov; exploratory unless stated)
FOOD-SYSTEM CONTROL (notebooks/b_food_system_control.py): adding diet-profile and supply-profile distances (FAOSTAT food balance) as controls leaves the trade coefficient at
 +0.148 (was +0.154, -4%); the distances themselves have beta ~0 (p>.6). => explanation 'similar food systems cause both trade and talk' NOT supported with these coarse profiles.
BERTopic (notebooks/b_topics.py fit; all-MiniLM-L6-v2 vectors; UMAP 5d cosine seed 42; HDBSCAN min_cluster_size 80; outliers reassigned by embeddings; names/procedural words removed):
 87 topics on 37,848 speeches. Reading them: ~40 are food/agriculture/environment/trade topics; ~40 are general politics where a farming word appears in passing; ~15 are COUNTRY-STYLE
 topics (currency, possessive country names, party names: kuna, forints, kr, serbias, latvias, Sanchez, New Democracy, M5S, PSS...).
KEEP-LIST FIXED BEFORE ANY TRADE RESULT ON TOPICS (user agreed to proceed and to check samples by hand later):
 farming: 9 44 82 59 69 | land: 7 19 56 61 70 | animals: 3 38 26 1 71 | markets: 25 68 74 83 63 | food policy: 29 37 39 46 52 58 85 |
 env+farming: 20 23 43 6 8 5 57 84 | trade: 34 41 | climate: 0 78 73.   (40 topics). Borderline, NOT kept: 54 (production/food/meat/customs), 30 (school food), 17 (draft law agri-env), 51 (BiH).
PLANNED (exploratory): (a) repeat the pre-declared primary test with language vectors built ONLY from kept-topic speeches; (b) per-topic overlap vs trade (Holm over 40); (c) topic-profile
 similarity as a second language measure; (d) regional drivers. Sampling sheet data/processed/b_topic_samples.csv for hand review of kept AND dropped topics.

## ANGLE B: topic-level results with the fixed keep-list (14 Nov, exploratory; notebooks/b_topics.py analyze)
Kept 18,314 of 37,848 speeches (48%; 40 topics). Kept per country is uneven: BA 48/348 (too few), LV 283, TR 329, GR 507, RS 490, IS 502 ... NL 1042, DK 1026.
36 topics have >60% of their speeches from ONE country, 14 of them in the keep list (e.g. 19 UA 99% land-sale referendum, 61 HR, 70 RS, 56 PL, 39 SE, 43 DK, 59 AT, 52 FI, 46 NO, 41 GB, 85 GB,
 68 EE, 78 FI, 69 ES): even the food topics are largely NATIONAL debates.
(a) Primary model re-run on kept-topic speeches only: similarity matrix correlates r=0.94 with the all-speech one; trade beta +0.131 (p=.0008), distance -0.253, same region +0.317,
 same language family +0.371, EU +0.005 -> the trade link is NOT an artefact of off-topic general-politics speeches. R^2=.539.
(c) Topic-share overlap (Bray-Curtis, 40 topics) ~ trade + controls: trade beta +0.058 (p=.73, NOT significant); EU +0.320 (p=.038), region +0.242 (p=.0008), family +0.154 (p=.036); R^2=.18.
 Correlation of topic-overlap with embedding similarity 0.37 (all) / 0.45 (kept). => the trade-language link is NOT visible in WHICH topics countries discuss; EU membership matters for topic mix but not for embedding similarity.
(b) Per-topic overlap vs trade: none significant after Holm (all Holm p=1); smallest raw p: topic 3 animal welfare beta -0.35 (p=.03), 19 land +0.21 (p=.05); 14 of 40 betas negative.
(d) Regional over-representation (mostly single-country topics): East: 19 land (UA), 56 farmers (PL), 83 wine; North: 39 food strategy (SE), 43 nature (DK), 78 climate (FI), 68 dairy (EE);
 South: 61 and 70 agricultural land (HR, RS), 69 citrus/olive (ES), 73 disasters; West: 59 farmers (AT), 23 nitrogen (NL), 20 glyphosate, 34 trade.
Sampling sheet for HAND REVIEW: data/processed/b_topic_samples.csv (4 random speeches per topic for all 87, kept flag, empty your_label column).
OPEN: still no mechanism. Idea: topic-CONDITIONED similarity (compare countries within the same topic, e.g. 'farmers/rural development', 'food safety', 'energy/climate') to separate subject from phrasing/style.

- 21 Nov: BERTopic's own reduce_topics run (seedoils/notebooks/seso_topics_reduce.py). The 19 Nov failure was `ValueError: max_df corresponds to < documents than min_df`: reduce_topics refits the vectorizer on K topic-texts and min_df=20 > K. Fix = freeze the fitted vectorizer's vocabulary (a vocabulary from raw comments gave inf c-TF-IDF because BERTopic strips punctuation). Result (3 seeds, AMI / NPMI) default vs hand average-linkage merge: k=50 0.49/0.215 vs 0.70/0.299; k=30 0.26/0.227 vs 0.69/0.281; k=12 0.10/0.207 vs 0.53/0.264. Default merges give chimera topics (soy+Trump+estrogen; palm oil+vaccines) and at k=12 one topic holds 88% of comments, so the 5.2x politics / 3.0x vaccines result exists only under the hand merge. Outputs: seso_red_k*.csv. Page NOT changed yet (decision pending).

- 21 Nov (page v34): Figure 1b is now every BERTopic topic (no hand groups) ranked by growth, top 15 among topics with >=300 comments (topic_growth_data.py -> topic_growth dataset). Reason: tuning k until politics shows up is circular. The "How we did this" box no longer says the model finds politics at k=50; it says Figure 1a's themes are a hand choice and that BERTopic's built-in reduce_topics was less stable than our merge (AMI 0.49 vs 0.70 at k=50). Still open: Figure 1a (hand themes) and the intro facts (politics x5.2, biochem x0.57) rest on the hand grouping; the k-sweep chart/note still shows politics_ratio/vaccines_ratio columns.

- 21 Nov (page v35): the "How we did this" box under Figure 1a is now two short paragraphs (BERTopic ~130 topics, grouped by hand into 8 themes, judgment disclosed; built-in reduce_topics did not work as intended: catch-all topic, mixed topics, seed-dependent groups, probably because it joins by word closeness and every topic shares the same words). The k-sweep chart and note are removed from the page (topic_k_sweep dataset now unused).

- 21 Nov (page v38): Figure 1b is r/StopEatingSeedOils only (community selector removed; ScientificNutrition rows stay in the topic_growth dataset but are unused). Built on the user's v37 copy edits, which were re-read first.

- 21 Nov (page v39): Figure 1b shows the top 5 topics by growth (was 15) at the user's request. Rank 3 onward differ little (x3.0, 2.9, 2.85, then 2.56); three of the five are political, one (rfk) rests on 8 comments before 2024.

- 21 Nov (page v41): section "Who talks about what" moved to follow "The conversation changed in 2024"; figures renumbered in reading order (old 7,8 -> 2,3; old 2,3 -> 4,5; 4a-c -> 6a-c; 5/5b/5c -> 7/7b/7c; 6 -> 8) in the visible text and the notes list. Built on the user's v40 (caption edit kept). The niche section still uses commenter counts that the later "A much bigger crowd" section introduces.

- 21 Nov (page v45): removed the paragraph under Figure 2 ("At the end of 2023 only 40 of the 184 people in the politics niche had appeared...") and its drawing code (nnnotea). Built on the user's v44.

- 21 Nov: INDEPENDENCE CHECK of the commenter niches (notebooks/commenter_thread_network.py). The niche network is built from the 50 merged topics, so it cannot confirm BERTopic. Rebuilt the commenter network from which THREADS people comment in (2,618 commenters, 6,266 threads, same disparity filter and Louvain; modularity 0.48). Result: AMI with the topic niches only 0.058 (shuffled 0.000); thread communities track arrival year more (AMI 0.26 vs 0.02 for topic niches). Politics IS found independently: thread communities T6 (198 people) and T7 (58) have 9% and 14% of comments in the politics topic vs 2% overall (vaccines 2.3-3.6% vs 0.9%); 56% of the topic-niche "Politics" people land in T6+T7. Other niches (olive oil, condiments, eggs, labels...) do NOT re-appear: their people spread over T0-T3. Not tested: whether T6/T7 are just the 2024 arrival cohort. Page not changed.

- 21 Nov: commenter niches rebuilt on the ORIGINAL 129 topics (notebooks/commenter_topic_network_130.py; outputs commenter_topic_network_130_*). Same 2,618 commenters, one component, Louvain modularity 0.56, AMI across seeds 0.75, 12 communities. AMI with the k=50 niches 0.33. Robust: politics+vaccines+pharma form ONE community (317 people, 26% long-time, i.e. 74% newcomers; 80% of the k50 Politics niche and 64% of the Vaccines niche land there); olive oil (64% overlap); LDL/keto (70%). Not robust: condiments, eggs, bread, labels niches collapse into one big general food/shopping community (712). The permutation null is NOT valid at 129 topics (permuted backbone has ~1,500 links vs 55,748, modularity not comparable). Page not changed.

- 21 Nov (page v47): Figures 2 and 3 redrawn on the ORIGINAL ~130 topics (commenter_topic_network_130.py --export, commenter_network_datasets_130.py, niche_overlay_data_130.py, niche_network_datasets.py; k=50 outputs backed up in artifact/_k50_backup). 12 Louvain communities, everyone linked (no general core), 55,748 backbone links (denser, more haze than the 8,652-link k=50 drawing), AMI across seeds 0.75, permutation p < 0.001 for long-time share (2,000 perms). Names are ours (from over-represented topics): Shopping and everyday food 712; Politics, vaccines, pharma 317 (26% long-time); Omega-6 science 253; Arguing about evidence 247; Keto, LDL, cholesterol 209; Olive and other oils 199; Vegan, soy, land 152; Calories, weight, fasting 139; Mayo, sugar, processed food 121; Pork, canola, allergies 102; Sun, skin, inflammation 97; Infant formula, kids 70. Outcomes: hostility rose clearly (CI above 0) in omega-6, keto/LDL, calories/weight, mayo/sugar, sun/skin; downvotes rose in most; politics+vaccines+pharma CI includes 0 for hostility. Page text: shuffled-null sentence replaced (not comparable at 130 topics); added thread-network check sentence. Stale: Figure 3 outcome note uses data-generated text (ok); topic names in the older Figure-2 intro paragraph unchanged.

- 21 Nov: community-level map TEST page (seedoils/artifact/community_map.html, notebooks/community_map_data.py). 12 Louvain communities of the 129-topic backbone as circles; links = backbone links between communities relative to chance (lift 0.1-0.92; all below 1 because 64% of links are inside communities); month slider + play (circle area = people who have appeared so far); colour by growth since end of 2023 (default), share of newcomers, hostile or downvoted share from 2024. People end of 2023 -> end of 2024: Politics, vaccines 82 -> 295 (x3.6), Evidence 65 -> 188 (x2.9), Formula/kids x2.5, Vegan/soy x2.4, Olive oil x2.3, Mayo/sugar x2.3, Shopping x2.1, Weight/fasting x2.0, Sun/skin x1.9, Keto/LDL x1.8, Pork/canola x1.8, Omega-6 x1.5. Prompted by user: the cohort colouring of the person-level Figure 2 hides which community's user base grows fastest. Not on the main page.

- 21 Nov (page v48): (1) paragraph opening the niche section rewritten for the ~130-topic network (no more contrast with a "general commenter"; communities are leanings, not specialists). (2) Display layout of Figures 2 and 3 changed (notebooks/community_layout.py): same force-directed layout, but links inside a community weighted 6x, so communities no longer interleave (tightness = mean distance to own community centre / to overall centre: 0.57 at weight 1, 0.40 at 4, 0.36 at 6, 0.31 at 12). Positions are display only; communities and links unchanged. Originals before this change: artifact/_layout_backup. The 50-topic node backups (cn_nodes, nn_nodes) were deleted at the user's request; other k50 files remain in artifact/_k50_backup, and the old k=50 blobs are still stored on the artifact.
- How a commenter's topic mix is computed (answered 21 Nov): counts of the person's comments (>= 15 words, one topic each) over the ~130 topics, times log(people / (1 + people commenting in that topic)) + 1, L2-normalised; similarity = cosine; only commenters with >= 10 such comments.

- 21 Nov: REPLY NETWORK check of the 12 communities (notebooks/commenter_reply_network.py; reply_matrix_130.csv). 77,854 replies between the 2,618 commenters (all their comments). Thread-conditional expectation (partner drawn from other members in the same thread): replies staying inside the replier's community 20.4% observed vs 18.8% expected (ratio 1.09). Per community ratios 0.95-1.41 (formula/kids 1.41 on 1,636 replies, weight/fasting 1.28, olive oil 1.22, evidence 1.15, politics 1.12; mayo/sugar 0.95, pork/canola 0.99). Strongest between-community lifts only 1.10-1.15, weakest 0.76-0.87. So communities are NOT interaction groups: the page's statement "they show who occupies each niche, not that these people interact" holds. Cohort mixing (long->long 33%, new->new 34%, long->new 16%, new->long 17%) is NOT thread-controlled. Page not changed.

- 21 Nov (page v49): added "What these topics sound like" under Figure 1b (before the niche section): one Reddit-style card for each of the five fastest-growing topics. Selection rule (not hand-picked): the comment closest to the topic's embedding centre among comments of 25-90 words from 2024 onwards (comment ids ludu9kc, lwroqgt, kq2q01t, o1ifq2r, laedvx3). Text is shown as in seso_docs.csv.gz (quotes and links already removed); usernames replaced by placeholders (u/anonymous_1..5), dates are posting dates, points are the downloaded score. This is the first place the page carries verbatim comment text (earlier decision: aggregates only); the page is private unless shared.

- 21 Nov (page v50): Figure 2 title now "Louvain communities of commenters with similar topic mixes, and how they filled in"; its caption says the communities come from Louvain and the names were written by hand from the most over-represented topics (built on the user's v49 caption wording). Still uses "niche" in the section title, Figure 3 and the notes.

- 21 Nov (page v51): "niche" replaced by "community" in all visible text (section heading now "Communities of commenters"; Figure 3 note, how-we-did-this box, map note). Internal ids/variable names (s-niches, fig-niches, niches) unchanged. Visible "niche" count on the page: 0.

- 21 Nov: PEOPLE vs TOPIC vs NEWCOMERS (notebooks/people_vs_topic.py). 106,783 topic-model comments by the 2,618 commenters; newcomers (first comment 2024+) write 64% of the 2024+ comments. Variance (adj R^2): hostile topic 0.007, person 0.015, both 0.020; downvoted topic 0.020, person 0.176, both 0.181 (hostility is mostly comment-level noise; downvotes are strongly person-linked). Decomposition of the change (pts, bootstrap over people, 300): HOSTILE 5.01 -> 6.48 (+1.47 [1.05, 1.94]): old guard same topics +1.06 [0.43, 1.63], old guard topic mix +0.38 [0.23, 0.53], newcomers +0.04 [-0.37, 0.51] (old guard 6.44% vs newcomers 6.50%). DOWNVOTED 4.43 -> 8.69 (+4.26 [3.26, 5.38]): old guard same topics +0.93 [0.05, 1.78], mix +0.57 [0.36, 0.81], newcomers +2.76 [1.87, 3.69] (10.2% vs 5.9%, all within topic; their different topic mix adds +0.01). Same 418 long-time people (>= 5 comments in both periods): hostile 5.03 -> 6.22 (+1.19 [0.40, 2.08]); downvoted 4.13 -> 6.71 (+2.58 [1.57, 3.54]). Caveats: score <= 0 depends on vote dynamics and comment age; hostile classifier unchecked; no causal claim. Page NOT changed.

- 21 Nov: REPLY-EXPOSURE test (notebooks/reply_exposure.py): did newcomers change the old guard's behaviour? 243,097 comments, 97% with a GoEmotions hostile label (long + short files); 112,356 replies from 2024 between two real people (old guard wrote 29,892, newcomers 82,464). Raw hostile share of replies: old->old 6.14%, old->newcomer 6.94%, newcomer->old 6.21%, newcomer->newcomer 6.73%; reply to a hostile parent 8.77% vs 6.44%. Two-way fixed effects (replier, thread), clustered by replier, pts: A old guard: parent is a newcomer +0.66 [-0.02, +1.34]; parent hostile -0.38 [-1.86, +1.10]. B newcomers: parent newcomer +0.48 [+0.01, +0.96]; parent hostile -0.08 [-0.87, +0.71]. C old guard hostile share per +10 pts newcomer share of the thread (replier + month FE): +0.28 [+0.06, +0.51] (not controlled for thread topic). D downvoted (thread FE): replier is a newcomer +4.20 [+2.96, +5.45], reply hostile +5.22 [+4.27, +6.18], parent hostile +2.06 [+1.25, +2.87]. Reading: no evidence that a hostile parent makes a hostile reply (raw gap is people and threads); small hints that newcomer-heavy threads and newcomer parents draw slightly harsher replies; the newcomer downvote gap is not explained by measured hostility (reception). Caveats: linear probability models, many tests, thread topic not controlled in C, hostility classifier unchecked. Page not changed.

- 21 Nov: SCATTERTEXT-STYLE test page newcomers vs old guard (notebooks/newcomer_terms.py, seedoils/artifact/newcomer_terms.html). 109,880 topic-model comments from 2024: old guard 30,684 by 1,599 people, newcomers 79,196 by 14,013. Terms (uni+bigrams, counted once per comment, >= 15 distinct authors), weighted log-odds with informative Dirichlet prior (Monroe et al. 2008). 10,902 terms; 241 tilt strongly to newcomers, 523 to the old guard (|z| > 3.1). Old guard: biochemistry (pufa, linoleic acid, omega, mufa, sfa, metabolic, dha, low fat, pork, ruminant, 'brad', 'marshall' = a public nutrition figure). Newcomers: everyday and consumer words (lol, avocado oil, organic, beef tallow, olive oil, cold pressed, bought, ingredients, cook, thank, app) and politics (rfk, trump). First version counted repeats inside a comment and showed 'rape' (a few people repeating the word); fixed by counting once per comment. Not on the main page.

- 21 Nov: CRITICAL CHECK of the newcomer-vs-old-guard scattertext (notebooks/newcomer_terms_check.py, lol_and_trolling.py; the test page overstates). Per person: old guard 1,599 people, 19.2 comments each (median 4); newcomers 14,013 people, 5.7 each (median 2). Vocabularies nearly identical: cosine 0.985; 91% of terms used in >= 200 comments are within 1.5x of each other; most lopsided term 3.6x; JSD 0.0150 bits vs 0.0097 (0.0082-0.0121) when the cohort label is shuffled among authors of equal activity. 767 'strongly tilted' terms (|z| > 3.1) vs 318 (160-574) under the shuffle, so z is inflated by repeated authors. Heavy commenters only (>= 10 comments, 516 old vs 1,577 new): 620 of 8,633 terms tilted (7.2%), cosine 0.986. The biochemistry tilt survives (pufa used by 42.4% of heavy old-guard vs 24.2% of heavy newcomers; linoleic acid 29.5 vs 19.5; omega 40.1 vs 30.9) but the 'consumer' words do not (avocado oil 33.3 vs 33.4, organic 33.7 vs 33.6, lol 34.7 vs 36.8, rfk 19.4 vs 17.5): the earlier 'newcomers write about shopping/politics' reading is a light-vs-heavy artefact. 'lol': 3.4% of newcomer comments vs 2.0% (x1.66), 1,340 newcomers (9.6%) vs 256 old-guard (16.0%), top 10 people write 14.3% of newcomer lol comments; lol comments are 0.8% hostile vs 6.6% without, downvoted 13.2% vs 9.8% (newcomers); insult words idiot x1.7, idiots x2.1, moron x2.1, cope x2.3, lmfao x4.4 but all <= 0.2% of comments; troll/trolls less among newcomers; exact-duplicate comments 0.11% vs 0.14%. No strong sign of trolling. PUFA/omega-6 topics (0, 79, 96): share of comments 14.1% (2022) -> 10.1% (2023) -> 6.2% (2024) -> 6.0% (2025) -> 6.7% (2026) but 61 comments/month before 2024 -> 196/month from 2024; people writing them 604 (2023) -> 1,159 (2024); old guard's own share 11.2% -> 9.5%; newcomers 5.0%; share back to 7-8% in 2025Q3-2026Q1 as activity fell. So dilution, not abandonment; Reddit data cannot say whether new research changed anything. Page not changed.

- 21 Nov: NULL MODEL for Figure 2 (notebooks/community_null.py). Same-density null (each person keeps top-m strongest links, m=29 -> 57,412 links vs page backbone 55,748; null = topic labels shuffled among comments, keeping each person's comment count and topic totals; 20 shuffles): real modularity 0.505, 14 communities, 62.6% of links inside communities; shuffled modularity 0.151 (0.146-0.153), 8-10 communities, 30.0% inside (null networks had ~70,054 links, denser than real, which slightly favours the real one). Per-community test on the page backbone (2,000 label shuffles of the same sizes): all 12 have more inside links than random labels (p < 0.001), x1.9 (Shopping, weakest) to x23 (Formula, kids), z 18-111. The per-community test is circular (communities were optimised to be tight), so the same-density null is the real evidence. Page not changed.
- 21 Nov: HOSTILITY ROBUSTNESS (notebooks/hostility_robustness.py) for Figure 3. Page flag = max(anger, annoyance, disapproval, disgust) >= 0.5, 6.1% of the network members' comments. Flagged comments: top label disapproval 65%, annoyance 24%, disgust 6%, anger 4%; 73% of flagged have a score 0.5-0.7; 3% have a most-likely label outside the four. Alternatives (share flagged; Jaccard with page flag; overall change pts; Spearman of community level, change): threshold 0.3 13.3%, 0.46, +3.30, 0.95, 0.92; threshold 0.7 1.7%, 0.27, +0.35, 0.69, 0.83; anger or disgust >= 0.5 0.7%, 0.11, +0.27, 0.55, 0.70; disapproval only 4.0%, 0.65, +0.70, 0.86, 0.78; argmax in the four 9.5%, 0.61, +2.54, 0.95, 0.90. All definitions show an increase; levels depend on the definition. Politics, vaccines, pharma community change is negative under page (-0.23), threshold 0.7 (-0.46) and disapproval-only (-0.37) but positive under 0.3 (+1.31) and argmax (+0.95). Blinded hand-label sample (150 comments, 30 per score band 0-0.1, 0.1-0.3, 0.3-0.5, 0.5-0.7, 0.7-1.0) written to data/processed/hostility_sample_to_label.csv with key hostility_sample_key.csv; NOT labelled yet. Page not changed.

- 21 Nov (page v53): HID the sections "Both camps argue over one body of research" (s-papers) and "What the research says, and what each community says" (s-align) with the `hidden` attribute for sharing with the project partner. Visible figures renumbered 4 (emotion), 4b, 4c, 5 (was 7, 7b, 7c, 8); the hidden sections keep 4, 5, 6a-c, so TO RESTORE: remove `hidden` from the two sections and from the two notes bullets (paper conclusions labelled blind; the papers are those users cite), renumber the emotion figures back to 7/7b/7c and the commenter-subreddit figure to 8 (and the notes references 4->7, 4b->7b, 5->8), and force a redraw of the hidden charts (they were drawn at zero width). The full page before hiding is saved as seedoils/artifact/index_before_hiding_papers_v52.html. Also changed: notes bullet on sources no longer mentions r/carnivore, OpenAlex or PubMed link look-ups. Left as is (flagged to the user): page title/eyebrow ("Same papers, new crowd, harsher tone"; "Reddit and the research it cites"), the sentence about papers in the opening paragraph, the footer "OpenAlex, PubMed", and the note "the course's choice of classifier is still open".
