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
