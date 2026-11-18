# Ultra-processed food: the backbone of what is on the shelves (started 15 Nov 2026)

Origin: Data Is Plural idea "the backbone of ultra-processed food" (GroceryDB, DIP 2025.01.29), widened to the whole world with Open Food Facts at the user's request.
The partner is exploring a different idea (agri-environmental policies spreading along food-trade links, DIP 2024.03.20). The group writes ONE paper with ONE story, so the two need to be reconciled or one chosen.

## Data
- Open Food Facts food export, downloaded 15 Nov 2026 from https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz (1,536,486,783 bytes, tab-separated, gzip),
  saved to upf/data/raw/off/ (gitignored). Chosen over the 8.05 GB Parquet export because it streams with pandas and needs no new packages.
  Licence: Open Database License (ODbL); contents DbCL; images CC-BY-SA. Attribution required in any public use: "Contains data from Open Food Facts, available under the Open Database License".
  Share-alike: an adapted database we publish must also be ODbL.
- Caveats known before looking: crowdsourced, so country coverage is uneven; the NOVA group (1-4, 4 = ultra-processed) is COMPUTED by Open Food Facts from ingredients and additives with rules, so it is a given label, not our measurement.

## Candidate text layers (not yet downloaded)
1. National food-based dietary guidelines, FAO pages (~100 countries, English profiles; checked: Denmark page describes the 2021 'good for health and climate' guidelines). Story: do governments warn against what fills their shelves?
2. Health and marketing claims on the packs (labels_tags in Open Food Facts itself).
3. ParlaMint food speeches (already on disk, Europe only).
4. OpenAlex abstracts on ultra-processed food. 5. EurLex food-additive regulations.

## Log
- 15 Nov: download started; first step is a coverage profile (upf/notebooks/off_profile.py) before any hypothesis is written.
- 15 Nov: download complete (1,536,486,783 bytes, gzip test OK). Profile (upf/notebooks/off_profile.py; upf/data/processed/off_country_coverage.csv, off_columns.txt):
  4,914,430 product rows, 211 columns; all needed fields present (ingredients_text, ingredients_tags, nova_group, countries_tags, categories_tags, labels_tags, additives_tags, origins/manufacturing places, nutriscore).
  NOVA present for 1,188,312 products (24%): NOVA 4 757,549; 3 219,996; 1 142,342; 2 68,425.
  Countries with >= 1,000 NOVA-labelled products: 51; >= 5,000: 27. Largest: France 344,618; United States 395,733; Germany 116,667; UK 58,541; Spain 54,441; Italy 39,669.
  Share NOVA 4 among labelled products ranges from .47 (Italy) and .53 (Spain) to .70 (US), .76 (Norway), .85 (Thailand). CAUTION: this is the share of what VOLUNTEERS SCANNED, not of what people buy.
  Ingredient tags: in the first ~2.4M rows, 91-100% of ingredient tags are in the shared English taxonomy for FR, DE, US, ES, PL, JP; lower for BR (.78) and TH (.62).
  Tags include parent categories (e.g. sugar -> disaccharide -> added-sugar): for a network, keep the most specific ingredient or collapse the hierarchy, otherwise links are inflated.
- 15 Nov: FAO food-based dietary guidelines downloaded (upf/notebooks/fao_fbdg_fetch.py; 100 country pages, one every 2 s, robots.txt allows the paths; raw HTML in upf/data/raw/fao_fbdg/, gitignored; parsed to upf/data/processed/fao_fbdg.csv).
  98 of 100 pages have a messages section ('Messages' or 'Recommendations'); missing: Saudi Arabia, Turkey. Median words: messages 127, whole page 385 (short texts).
  Latest guideline year: median 2015, range 1991 to (a parsing artefact: 2029; check). Two pages without a year.
  Overlap with Open Food Facts: 97 of 100 matched to a country tag; with >= 1,000 NOVA-labelled products: 38 countries; >= 5,000: 24. NOVA 4 share among them .47 (Italy) to .85 (Thailand).
  TO CHECK: Bolivia (3,851) and Argentina (3,853) have near-identical NOVA counts -- possible tagging artefact.
- User's proposed story (15 Nov): how many products on each country's shelves are ultra-processed, and how that deviates from the national dietary guidelines. Design options discussed in chat; not yet decided or pre-declared.
- User point (15 Nov): in countries with a big eating-out / street-food culture (e.g. Thailand), packaged products on shelves are not indicative of regular eating habits.
  Consequences for the design: (1) the claim is about the PACKAGED-FOOD AISLE vs official advice, not about diets; (2) add a whole-diet layer from FAOSTAT food balance sheets
  (supply by food group incl. food eaten out; no processing information; supply is not intake) to compare with what guidelines push/limit; (3) flag high eating-out countries
  and report results with and without them (no eating-out dataset in hand, so that flag would be a stated judgement unless a source is found).
- 15 Nov: User: the guideline comparison is circular (supply follows demand) -> PARKED; explore the supermarket data first: ingredient network + centrality.
  EXPLORATORY ingredient network (upf/notebooks/off_extract.py, ingredient_network.py; data/processed/ingredient_nodes*.csv, ingredient_backbone_edges.txt):
  1,052,132 products with NOVA + English-taxonomy ingredients (79k dropped as untranslated). Parent tags inferred from data (P in >= 99.5% of T's products, P >= 1.2x as common): 587 parents; median tags 22 -> 12.
  Nodes: 1,221 ingredients in >= 1,000 products; disparity backbone 52,916 of 601,266 edges; 5 Louvain communities (modularity .20):
   savoury/condiment (salt, water, garlic, onion, sunflower oil, spice); sweet-industrial (sugar, citric acid, flavouring, colour, corn syrup, modified starch); bakery/chocolate
   (wheat flour, soya lecithin, cocoa butter, emulsifier, glucose syrup, milk powder, palm oil); FORTIFIED FLOUR (folate, thiamin mononitrate, riboflavin E101, reduced iron, yeast -- the US enriched-flour mandate, i.e. the US share of the data shows up as a community); dairy/fermentation (cultures, milk, enzymes, whey, rennet).
  Most central (eigenvector): sugar, salt, water, citric acid, wheat flour, natural flavouring, soya lecithin, dextrose. Bridges (betweenness): salt .72, water .37, sugar .30.
  Central in the NOVA-4 network but not in NOVA 1-3: emulsifiers (E471, soya lecithin), modified starches, glucose/corn syrup, maltodextrin, dextrose, flavourings, colour, palm oil, skimmed milk powder, cocoa butter, E412/E415 gums.
  CAVEATS: (a) centrality here mostly tracks frequency (salt, sugar, water); a frequency-normalised view or null model is needed; (b) CIRCULARITY: NOVA 4 is assigned by Open Food Facts FROM marker ingredients
  (flavourings, emulsifiers, colours, modified starch...), so markers being central in NOVA 4 restates the definition (their NOVA-4 share is 1.00); the informative part is which NON-marker ingredients travel with them and the community structure;
  (c) parent removal is incomplete: near-synonyms remain (sugar/disaccharide/added-sugar, wheat-flour/cereal-flour, folate/folic-acid) and function-class tags (colour, emulsifier, preservative, flavouring). Fix next: Open Food Facts' own ingredient taxonomy, or merge mutual pairs.
  Figure not drawn yet (waiting for the tag fix).
- User idea (15 Nov): EMOTION OF FOOD with the NRC Emotion Lexicon (EmoLex v0.92, 14,182 English words, 8 emotions + 2 sentiments, crowdsourced; Mohammad & Turney 2013). Terms: non-commercial research or educational use; ethics statement to read before use.
  Course fit: Week 7 covers lexicon-based sentiment (LabMT, VADER, emotion), so a published lexicon is in scope (unlike the ad-hoc word lists dropped earlier). Text source still open.
- 15 Nov: EMOTION OF FOOD, text = product names (user's choice). upf/notebooks/off_names.py -> off_names_en.csv.gz (gitignored): 488,366 NOVA-labelled products sold in US/UK/CA/AU/IE/NZ
  with a mostly-ASCII name; NOVA 1 48,822 / 2 14,695 / 3 83,122 / 4 341,727; names are short (median 4 words) and often start with the brand ('Meijer, frozen concentrate, pink lemonade') -> strip brands before scoring.
  NRC EmoLex download (https://saifmohammad.com/WebDocs/Lexicons/NRC-Emotion-Lexicon.zip, 25,878,449 bytes) needs the user's OK: terms = non-commercial research/education, cite Mohammad & Turney (2010, 2013),
  NO REDISTRIBUTION -> keep in upf/data/raw/nrc/ (gitignored; our GitHub repo is public). Not downloaded yet.
- User idea (15 Nov): UKRAINE WAR AND FOOD PRICES -- who was hit hardest relative to where food is produced/exported; winners and losers.
  Data: WFP Global Food Prices on HDX (https://data.humdata.org/dataset/global-wfp-food-prices): 98 countries, ~3,000 markets, staples (maize, rice, beans, fish, sugar...), monthly, 1990 to 15 Nov 2026, 40 resource files. Not downloaded.
  Network: FAOSTAT trade (on disk, to 2023): 2021 import exposure to Russia/Ukraine (wheat, maize, sunflower oil); who replaced Ukrainian exports 2022-23 (rewiring of the wheat network; winners = suppliers whose share rose).
  Caveat: WFP markets are mostly low/middle-income countries, so no overlap with ParlaMint (Europe). Text layer still open (candidates: UN General Debate 2022 speeches, ReliefWeb reports, FEWS NET reports -- availability not yet checked).
- 15 Nov: NRC EmoLex downloaded (25,878,449 bytes) to upf/data/raw/nrc/ (gitignored; git check-ignore confirmed; emotion_top_words.csv also gitignored because it lists lexicon word-emotion pairs).
  EXPLORATORY emotion scoring of product names (upf/notebooks/name_emotions.py; emotion_by_nova.csv, emotion_within_category.csv): 30% of names contain an emotion word, but the FOOD-WORD TRAP dominates:
  chocolate/cream/sweet -> joy, anticipation, trust; chicken -> fear; lemon/sour/fat -> disgust; dark -> sadness. With all words NOVA-4 names look twice as 'joyful' (.18 vs .09 for NOVA 1) purely because they are chocolate and cream products.
  Without food words (ingredient names; category names were too broad because they contain marketing words): emotion words appear in only 1-9% of names and within-category NOVA-4 vs NOVA 1-3 differences are tiny (+0.1 to +0.7 points),
  except 'positive' words, which are LESS common on NOVA-4 names (-4.1 points, higher in only 13/49 categories) -- largely 'organic' and similar words on less processed products.
  Are names marketing text at all? 89% of name tokens (brand removed) are ingredient or category words; random samples read as plain descriptions ('Onion Bagel', 'Long grain brown rice').
  Marketing-like words exist but are rare (homestyle 1,378, simply 758, fancy 654, supreme 554, ultimate 356, signature 305, inspired 344 among 1.9M tokens). generic_name exists for only 2.9% of products;
  packaging_text is recycling information; labels are structured claims (organic, gluten-free, no added sugar). READING: Open Food Facts has no real marketing copy, so emotion-in-names measures which foods products are, not how they are sold.
  The closest marketing signal is the claims (labels) field -- structured, not emotional.
- 15 Nov: GroceryDB checked (github.com/Barabasi-Lab/GroceryDB, data/ folder; read file headers in the browser, nothing downloaded):
  GroceryDB_foods.csv (~50,600 rows): name, store (Walmart/Target/Whole Foods), harmonised category, brand, FPro processing score (+ class), price, price per calorie, package weight, 12 nutrients.
  GroceryDB_data_uncurated.csv (~54,600 rows): name, full ingredient list, category, subcategory. NO marketing descriptions either; names are retail titles with brand and pack size.
  What it adds: (1) FPro is a MACHINE-LEARNED score from the nutrient profile, not rule-based from marker ingredients like NOVA -> an ingredient network judged against FPro is much less circular;
  (2) price and price per calorie by store -> 'are ultra-processed calories cheaper, and do stores differ?'. Not a source for emotion/marketing text.
  Marketing/consumer text would need another source (candidate, NOT verified here: Amazon Reviews 2023 grocery category from McAuley Lab with product descriptions and reviews).
- 15 Nov: GroceryDB DOWNLOADED (MIT licence) to upf/data/raw/grocerydb/ (gitignored): GroceryDB_foods.csv (11,255,593 B), GroceryDB_data_uncurated.csv (20,643,966 B), GroceryDB_IgFPro.csv (433,838 B; per-ingredient product counts and mean FPro),
  UpdatedProductIngredients_11_15.zip (16,122,734 B -> one 325 MB JSON: per product name, store, URL, original_ID and a PARSED INGREDIENT TREE with general_name, ingredient_type (ingredient/additive), additive_id, order, sub-ingredients).
  Profile: 50,468 foods (Target 17,854; Walmart 16,823; Whole Foods 15,791), 53 categories; FPro mean .73 (quartiles .61/.78/.91); median FPro Target .86, Walmart .81, Whole Foods .72; price per calorie for 25,921; 46,890 foods have an ingredient list.
  The parsed ingredient trees with general names solve the parent-tag problem met in Open Food Facts.
- 15 Nov: AMAZON REVIEWS 2023 (McAuley Lab; amazon-reviews-2023.github.io) checked, NOT downloaded. Grocery_and_Gourmet_Food: 7.0M users, 603.2K items, 14.3M ratings, 579.5M review tokens, 462.8M metadata tokens; May 1996 - Sep 2023.
  Files: reviews jsonl.gz 1,630,860,152 B; meta jsonl.gz 324,346,561 B. Reviews: rating, title, text, helpful votes, verified purchase, (hashed) user_id, timestamp, asin/parent_asin.
  Meta: title, FEATURES (bullet points) and DESCRIPTION = real marketing copy, price, store, categories, details (may include UPC -> possible barcode link to Open Food Facts / GroceryDB; coverage unknown), bought_together.
  Code repository MIT; no explicit data licence found on the site; Hugging Face copy not gated. Cite Hou et al. 2024 (arXiv:2403.03952).
- 15 Nov: TESCO LONDON 'Area-level grocery purchases' (figshare 7796666; CC BY 4.0; published 2020): per area (LSOA, MSOA, ward, borough) and month of 2015 + year, 202 columns: average product nutrients, energy density,
  fractions of 17 food categories (beer, dairy, eggs, fats & oils, fish, fruit & veg, grains, red meat, poultry, readymade, sauces, soft drinks, spirits, sweets, tea & coffee, water, wine), diversity (entropy), plus census information.
  NOTE: AREA-level aggregates, not consumers; demographics are census figures for areas. Bipartite areas x 17 categories is thin on one side; a similarity network of areas (cosine of category profiles) vs demographics/space is the natural network. No text. Not downloaded.
- 15 Nov: AMAZON grocery DOWNLOADED to upf/data/raw/amazon/ (gitignored; gzip OK): reviews 1,630,860,152 B, meta 324,346,561 B. Profile (upf/notebooks/amazon_profile.py; amazon_profile.txt; amazon_meta_compact.csv.gz gitignored):
  603,274 items; features (marketing bullets) for 72% (median 41 words), description for 63% (median 47 words); price 37%; categories 89%; 'bought_together' EMPTY (0.0%) -> no co-purchase network from that field.
  UPC in 'details' for 339,849 items (56%) = the barcode link ('ISBN for groceries'); 75,933 items match an Open Food Facts product with NOVA (NOVA 1 7,337 / 2 1,537 / 3 14,923 / 4 52,136); 81% of matched items have marketing text.
  Reviews: 14,318,520 (92% verified purchases); ratings 1:1.86M 2:0.70M 3:0.90M 4:1.26M 5:9.61M; median 17 words; mostly 2013-2023; reviews on matched items: 2,519,089.
  MATCH CHECK (20 random matched items read side by side): ~17/20 the same product; ~3 same brand but a different variant (Amazon groups flavours under one parent item with one UPC), e.g. Yupik Inca berries vs Yupik hazelnuts.

## STORY v1: "Sold on joy?" -- PRE-DECLARED 15 Nov, before any emotion score, topic model or network was computed on the Amazon text (user: "Yes, draft it").
Partner alignment still pending (the partner explores agri-environmental policy diffusion); the paper has one story, so this needs their agreement.

NUT GRAF (hypothesis form; rewrite with findings later):
 Ultra-processed foods dominate America's online grocery aisle. Matching about 76,000 Amazon grocery products to their ingredient records by barcode, we ask whether ultra-processed food
 is sold with a different emotional language than less processed food in the same aisle, whether shoppers' reviews deliver the emotions the marketing promises, and whether the people
 who review ultra-processed products form their own cluster in the network of shoppers.

DATA AND UNITS
 Products = Amazon grocery items whose UPC matches an Open Food Facts product with a NOVA group (75,933 found); one row per parent item (drop duplicates); NOVA 4 vs NOVA 1-3.
 Marketing text = Amazon 'features' + 'description' (NOT the title). Reviews = all reviews of matched items (about 2.5M). Category = Open Food Facts main category (harmonised), for within-category comparisons.
 HIGH-CONFIDENCE subset (robustness): the Open Food Facts brand (first brand, >= 3 letters) appears in the Amazon title or store field (the match check found ~3/20 same-brand-other-flavour pairs).

MEASURES (course tools only)
 Emotion: NRC Word-Emotion Association Lexicon (Week 7 lexicon method): per document, share of words associated with each emotion (8 emotions + positive/negative).
  PRIMARY score excludes food words (tokens of Open Food Facts ingredient names, as in name_emotions.py) because e.g. 'chocolate' is tagged joy; sensitivity: all words.
 Topics: BERTopic on MiniLM embeddings of marketing text (week 7 recipe), topics named by reading their words; cosine similarity between a product's marketing text and its reviews.
 Networks: (i) shopper network = products linked by shared reviewers (reviewers with 2-50 reviews among matched products), edge weight = shared reviewers, disparity backbone; (ii) the ingredient network already built.

HYPOTHESES (within-category comparisons: categories with >= 100 NOVA-4 and >= 100 NOVA 1-3 products; statistic = product-weighted mean of within-category differences;
 p from 5,000 permutations of NOVA labels WITHIN category; Holm over H1-H4)
 H1 SOLD ON JOY: NOVA-4 marketing copy has a HIGHER share of joy + anticipation words than NOVA 1-3 copy in the same category. One-sided.
 H2 SOLD ON TRUST: the share of trust words differs between NOVA-4 and NOVA 1-3 copy in the same category. Two-sided (no direction predicted).
 H3 PROMISE vs EXPERIENCE: the gap (joy+anticipation share in marketing minus the same share in that product's reviews) is LARGER for NOVA-4 products. One-sided.
 H4 ULTRA-PROCESSED SHOPPERS: on the shopper network, NOVA assortativity (NOVA 4 vs 1-3 as node label) is POSITIVE and above a null that shuffles labels within category (keeps the network and the category mix). One-sided.
DESCRIPTIVE (labelled exploratory): marketing topics by NOVA; emotion profile of ingredient-network communities; price per product by NOVA.
ROBUSTNESS (pre-set): high-confidence match subset; one product per brand (brand boilerplate repeats); all-words emotion score; NOVA gradient 1-2-3-4.
LIMITS to state: reviewers are not all buyers and Amazon is not the whole market; NOVA is assigned by rules; lexicon emotions are word associations, not felt emotions; the lexicon is not redistributed.
- AMENDMENT A1 (15 Nov, user suggestion; written WHILE the H1-H4 run was in progress and BEFORE its output was read):
  measure MARKETING language by VALENCE (and arousal) with the NRC VAD Lexicon v2.1 (Mohammad 2025, arXiv:2503.23547; >55k terms, scores 0-1 by best-worst scaling; non-commercial research use; not redistributed),
  and REVIEWS by EMOTIONS (EmoLex, as already computed). Not yet downloaded (needs the user's OK on the same kind of terms).
  New tests once downloaded (same within-category design, 5,000 permutations, food words excluded as primary):
  A1-H1 NOVA-4 marketing copy has HIGHER mean valence than NOVA 1-3 copy (one-sided); A1-H1b arousal differs (two-sided).
  A1-H3 promise vs experience on ONE scale: (mean valence of marketing words) minus (mean valence of review words) is LARGER for NOVA 4 (one-sided).
  Reviews by emotion: EmoLex shares per emotion, NOVA 4 vs 1-3 within category (descriptive profile, Holm over 8 emotions if tested).
  The original H1-H4 results are reported in full as pre-declared; A1 is an added, pre-declared measurement, not a replacement chosen after seeing results.

## STORY v1 RESULTS: pre-declared H1-H4 (15 Nov; upf/notebooks/sold_on_joy.py; upf/data/processed/sold_on_joy_results.txt)
Samples: 75,933 matched products; marketing text >= 10 words 61,397; + >= 5 reviews 38,308. Within-category tests use the 25 (H1/H2) and 12 (H3) categories with >= 100 products on both sides.
 Mean per 100 marketing words (no food words), NOVA 1/2/3/4: joy+anticipation 4.24/3.64/4.05/4.48; trust 3.83/3.49/3.67/3.78; reviews joy+anticipation 5.83/5.79/5.94/5.95.
H1 SOLD ON JOY: +0.34 joy/anticipation words per 100 marketing words for NOVA 4 within category (29,852 products), p=.0002, Holm .0008: SUPPORTED, small (about 8% more than NOVA 1-3).
 ROBUSTNESS MIXED: high-confidence matches -0.004 per 100 (p=.52, 12,396 products) -> GONE; one product per brand +0.59 (p=.001, 1,834) -> holds; all words +0.72 (p<.001) -> stronger.
H2 TRUST: +0.08 per 100, two-sided p=.051, Holm .10: NOT SUPPORTED (high-confidence subset: -0.13, p=.02, opposite sign).
H3 PROMISE vs EXPERIENCE (EmoLex version): +0.09 per 100, p=.11: NOT SUPPORTED (one per brand +0.35, p=.07; all words +0.26, p=.001).
H4 ULTRA-PROCESSED SHOPPERS: NOVA assortativity on the shopper backbone +0.279 vs null (labels shuffled within category) +0.004, p=.0002, Holm .0008: SUPPORTED, large. 3,672 products, 11,766 backbone edges of 2.85M co-review pairs.
 Holds on high-confidence matches (+0.272 vs +0.001, p=.0005).
 CAVEAT NOT YET TESTED: the same brand's variants are often reviewed together and share a NOVA group, so brand could drive part of the assortativity; also Open Food Facts main category is coarse. Needs a follow-up (e.g. drop same-brand edges / shuffle within brand) before it is a finding.

## STORY v1 RESULTS (15 Nov; upf/notebooks/sold_on_joy.py; upf/data/processed/sold_on_joy_results.txt). First run was cut off when the session ended; rerun completed. Reported in full as pre-declared.
Sample: 75,933 matched products; marketing text >= 10 words 61,397; marketing + >= 5 reviews 38,308. Within-category tests use 25 categories (H1, H2; 29,852 products) and 12 (H3; 13,483).
 Means per 100 words (no food words), NOVA 1/2/3/4: joy+anticipation in marketing 4.24/3.64/4.05/4.48; trust in marketing 3.83/3.49/3.67/3.78; joy+anticipation in reviews 5.83/5.79/5.94/5.95.
H1 SOLD ON JOY: +0.34 per 100 words (NOVA 4 higher within category), p=.0002, Holm .0008 -> SUPPORTED in the main sample, but SMALL (about +8%) and NOT ROBUST:
 high-confidence matches -0.00 (p=.52, 12,396 products); one product per brand +0.59 (p=.001, 1,834); all words incl. food +0.72 (p<.001). Gradient NOVA 1-4: 4.42/3.75/4.25/4.66.
H2 SOLD ON TRUST: +0.08 per 100 words, p=.051, Holm .10 -> NOT SIGNIFICANT; high-confidence subset goes the other way (-0.13, p=.02).
H3 PROMISE vs EXPERIENCE: +0.09, p=.11 -> NOT SUPPORTED. Descriptive surprise: the gap is NEGATIVE at every NOVA level (-0.7 to -1.4 per 100 words): reviews contain MORE joy/anticipation words than the marketing copy.
H4 ULTRA-PROCESSED SHOPPERS: NOVA assortativity +0.279 on the shopper backbone (3,672 products, 11,766 edges of 2,854,237) vs within-category null +0.004, p=.0002, Holm .0008 -> STRONGLY SUPPORTED;
 high-confidence matches +0.272 (p=.0005). EXPLORATORY check (not pre-declared; brand loyalty could create it): 12% of backbone edges are same-brand, 11% same-category;
 different-brand edges only +0.223 (null +0.004); different brand AND different category +0.188 (null +0.002); both p=.001 (1,000 perms). Not brand loyalty.
READING: the network result is the finding; the emotion-in-marketing result is small and fragile, trust and promise-vs-experience are null. Candidate new nut graf (to discuss):
 'Shoppers sort themselves by processing level: people who review ultra-processed groceries on Amazon mostly review other ultra-processed groceries, across brands and aisles,
 while the emotional language used to sell them differs only slightly from that of less processed food.'
LIMITS: reviewers are not all buyers; the backbone keeps a small, active part of the shopper network (3,672 of ~76k products); NOVA is rule-based; ~15% of matches are a different variant (robust in the high-confidence subset for H4, not for H1).

## AMENDMENT A1 RESULTS (15 Nov; upf/notebooks/sold_on_joy_vad.py; upf/data/processed/sold_on_joy_vad_results.txt; VAD v2.1 scale -1..1, food words excluded)
Means NOVA 1/2/3/4: marketing valence .268/.250/.262/.277; marketing arousal -.140/-.139/-.128/-.120; review valence .231/.235/.226/.225.
A1-H1 marketing valence higher for NOVA 4: +0.0135 within category (29,822 products, 25 categories), p=.0002, Holm .0006: SUPPORTED (small: about 5% of the mean).
 Robust: high-confidence +0.0062 (p=.001); one per brand +0.0125 (p=.004); all words +0.0109 (p<.001).
A1-H1b marketing arousal differs: +0.0099 (more aroused/exciting wording for NOVA 4), p=.0002, Holm .0006.
A1-H3 promise vs experience (marketing valence minus review valence) larger for NOVA 4: +0.0087 (13,467 products, 12 categories), p=.0002, Holm .0006: SUPPORTED.
 Robust: high-confidence +0.0072 (p=.002); one per brand +0.0090 (p=.07, n=1,168); all words +0.0058 (p<.001). Gradient of the gap NOVA 1/2/3/4: .038/.019/.036/.052.
Reviews by emotion (EmoLex, NOVA 4 minus 1-3 within category, per 100 review words; Holm over 8): MORE anger +.058, anticipation +.094, disgust +.041, fear +.045 (all Holm <= .006); LESS trust -.108 (Holm .004);
 joy +.048 (Holm .18), sadness +.030 (Holm .10), surprise -.005 (n.s.).
READING: ultra-processed food is marketed in slightly more pleasant and more exciting words than less processed food in the same category, while its reviews are no more pleasant, carry less trust
 and a little more anger, disgust and fear; the promise-experience gap is larger. All effects are SMALL in absolute size; the EmoLex joy measure (H1) was fragile, the valence measure is robust.
TO DO before this is a finding: read samples of review passages driving anger/disgust/fear/trust for NOVA 4 (check they are not food words or artefacts such as 'hot', 'bitter');
 H4 brand confound (drop same-brand edges or shuffle within brand); report effect sizes in plain units.

## CHECKS (15 Nov; upf/notebooks/soj_checks.py). Note: a forked session ('Course final project (fork)') worked in this folder and committed 21660d1 (its own write-up of H1-H4 + an exploratory brand check); only PLAN.md touched.
H4 BRAND CHECK (brand = Open Food Facts first brand, else Amazon store): backbone 11,766 edges / 3,672 products; 16% same-brand edges, 11% same-category.
 all edges, null within category +0.279 (null +0.004); null shuffled WITHIN BRAND +0.279 (null +0.012); different-brand edges only +0.208 (null +0.002); different brand AND category +0.179 (null +0.001); all p=.0005 (2,000 perms).
 -> The shopper clustering is NOT brand loyalty; it survives across brands and aisles. (Agrees with the fork's numbers: +0.223 / +0.188.) H4 stands as the main finding.
REVIEW EMOTION WORDS READ (25% sample of matched reviews: 12.6M NOVA-4 and 6.3M NOVA 1-3 tokens):
 ANGER/DISGUST/FEAR excess in NOVA-4 reviews is driven largely by 'treat' (6.9 vs 3.3 per 10,000 words), which EmoLex tags with anger, disgust and fear but reviewers use POSITIVELY
 ('a great outdoor treat', 'our favorite morning treat') -> LEXICON ARTEFACT; roughly most of the disgust and fear excess and over half of the anger excess (pooled rates, rough).
 Also 'broken' (cookies arriving broken = shipping damage, not the food) and 'bear' (gummy bears), 'batter' (food words outside the ingredient vocabulary).
 Genuine complaint words ARE somewhat more frequent in NOVA-4 reviews: bad 11.0/9.6, disappointed 7.9/6.6, horrible 3.5/2.5, terrible 3.8/2.9, awful 3.2/2.3, gross 2.7/1.8, disgusting 2.3/1.5, nasty 2.0/1.3, waste 3.5/2.8
 (some negated: 'not bad', 'you will not be disappointed').
 TRUST deficit in NOVA-4 reviews: about half artefact ('food' 12.1/15.2, 'ground' 0.8/2.3 as in ground pepper, 'grit', 'seal', 'cap' = packaging), half genuine praise words (excellent 10.0/14.1, wonderful 5.7/7.4, clean 1.0/2.4, top, recommend).
 -> The EmoLex review-emotion results must NOT be reported as 'more anger, disgust and fear'. Defensible reading: slightly more complaint words and slightly less strong praise for ultra-processed products, partly about delivery damage.
 Not yet checked the same way: which words drive the MARKETING valence difference (A1-H1) and the valence gap (A1-H3).
VALENCE WORDS READ (soj_checks.py valence; contribution c_w = valence_w x (share in NOVA 4 - share in NOVA 1-3), sums to the pooled difference):
 MARKETING pooled difference +0.0167 (NOVA 4 +0.286 vs NOVA 1-3 +0.269; within-category estimate was +0.0135).
  Pushing NOVA 4 UP: (a) FOOD-TYPE words outside the ingredient vocabulary: candy +.0031, cookies +.0012, creamy +.0010, breakfast +.0008, dessert +.0007, dinner +.0007 (about 45% of the difference = 'what the food is');
  (b) PLEASURE / FUN / CONVENIENCE words: flavor +.0030, delicious +.0020, enjoy +.0016, perfect +.0014, easy +.0011, fun +.0010, love +.0009, taste, favorite, tasty, kids, colors, real.
  Pushing NOVA 4 DOWN = words more common on less processed products: HEALTH / PURITY / CERTIFICATION: organic -.0042, food -.0024, certified -.0017, ingredient -.0015, healthy -.0012, best, pure, health, verified.
 REVIEWS pooled valence is the SAME (+0.2071 vs +0.2066): NOVA-4 reviews use more flavor, candy, love, favorite, yummy, kids; NOVA 1-3 reviews more great, healthy, excellent, organic, good, best.
 -> READING: the valence gap is real but half of it is food type; the substantive contrast is NOT 'more positive' but WHICH positive: ultra-processed copy sells PLEASURE, fun and convenience;
  less processed copy sells HEALTH, PURITY and CERTIFICATION; reviews mirror that split (pleasure words vs quality/health praise). Next: a log-odds word plot (Monroe et al., as in ndc_wordplot.py) of marketing NOVA 4 vs NOVA 1-3 to show it directly.

## CORRECTION (15 Nov): H4 NULL MODEL WAS WRONG IN THE FIRST RUN
Bug: the 'shuffle within category / within brand' permutation took np.lexsort((random, group)) and applied it to products that were NOT sorted by group, so labels were in fact shuffled across ALL products
 (a plain full shuffle). H1-H3 used a sorted table and are correct. Fixed with sold_on_joy.shuffle_within() (tested: each group keeps its own label counts). The fork's exploratory brand nulls (+0.004/+0.002) came from the same code and are wrong too.
CORRECTED H4 (pre-declared null = labels shuffled within Open Food Facts category, 5,000 perms): observed +0.279 vs null mean +0.091, p=.0002 (Holm unchanged, <= .0008). High-confidence matches +0.272 vs +0.085, p=.0005.
CORRECTED BRAND CHECK (2,000 perms each): null within BRAND +0.200 (observed +0.279, p=.0005); different-brand edges only +0.208 vs within-category null +0.073; different brand AND category +0.179 vs +0.060 (both p=.0005).
READING (revised): category mix explains about a third of the clustering (null .09) and brand portfolios explain most of it (null .20: brands tend to be all-ultra-processed or all-not, and shoppers move between
 similar brands); there is still clustering beyond both (+0.08 above the brand null, +0.12-0.13 above the category null on cross-brand links). The finding survives, but it is SMALLER and largely a brand-level sorting.
WORD PLOT (15 Nov; upf/notebooks/marketing_wordplot.py; upf/figures/marketing_wordplot.png; data/processed/marketing_wordplot.csv; descriptive):
 Monroe log-odds with informative prior, z-scored; marketing copy (features + description); CATEGORY-BALANCED (25 categories, larger side downsampled; 10,349 products per side); document counts; brand/store/pack-size words removed; 2,194 words in >= 30 products.
 Most NOVA 1-3 words: gmo -16.9, non -14.8, certified -14.0, usda -12.5, verified -10.2, additives -9.7, virgin, harvested, chemicals, slowly, batches, nutrients, milled, refined, soil, pesticides, earthy
  -> PURITY / CERTIFICATION / CRAFT / ORIGIN, often stated as absences ('non-GMO', 'no additives', 'no chemicals').
 Most NOVA 4 words: flavored 16.8, cheddar 12.1, calories 11.5, includes, filling, fun 9.9, creamy, serving, strawberry, grams, cheesy, school, caramel, artificial, gum, irresistible 7.9, individually, satisfy, adults, packet, dinner, quick, favorite, minutes, colors
  -> PLEASURE (fun, irresistible, satisfy, favorite, creamy, cheesy) + CONVENIENCE / PORTIONS (individually, packet, quick, minutes, school) + nutrition-label talk (calories, grams, serving).
 Caveat: some words are still food sub-type within a category (cheddar within cheese, olives within oils); 'artificial' can be negated ('no artificial colors').
- 15 Nov: STORY PAGE 'Sold on Pleasure' (draft, data-journalism style; no third-party branding): upf/site/sold-on-pleasure.html, published privately at https://claude.ai/artifact/RM7ax3VptsSo9ZDJrDneXC
  Sections: aisle facts (nutrition-label style), category-balanced word plot (interactive, searchable), valence comparison, the 'treat' trap, shopper-network picture (2-core of the largest component: 1,328 products,
  9,908 links; 72% NOVA 4; 69% of links join same kind vs ~60% expected) with a shuffle button, corrected assortativity nulls, 'what did not hold up', credits (Open Food Facts ODbL attribution, Amazon Reviews 2023, NRC lexicons).
  The page embeds only our own log-odds scores and network coordinates, no lexicon entries.

## CROSS-CATEGORY REVIEWERS (15 Nov; user: test whether we can see what the same reviewers review elsewhere)
FEASIBILITY (checked before any hypothesis): Amazon Reviews 2023 uses the SAME hashed user_id across category files. Health_and_Personal_Care (69.5 MB; 494,121 reviews, 461,656 reviewers):
 4.6% of the 1,643,635 grocery reviewers of matched products and 9.2% of the 336,899 shopper-network reviewers also review there. No profile data, no re-identification: aggregate patterns of pseudonymous reviewers only.
 Reviews are not purchases (92% of grocery reviews are verified purchases, but most purchases are never reviewed).
PRE-DECLARED (before downloading the other categories): who are the ultra-processed shoppers?
 Reviewers: >= 3 reviews of matched grocery products. UPF share = share of those reviews on NOVA-4 products. Groups: ALL-UPF (share = 1.0) vs MOSTLY-NOT (share <= 0.5).
 Outcome per category: the reviewer has >= 1 review in that category file. Statistic: difference in presence rate (ALL-UPF minus MOSTLY-NOT), weighted over activity strata of matched grocery reviews (3, 4, 5-9, 10+),
 p from 2,000 shuffles of group labels WITHIN strata (heavier reviewers appear in more categories). Categories: Video_Games, Toys_and_Games, Sports_and_Outdoors, Health_and_Household, Baby_Products, Pet_Supplies, Health_and_Personal_Care.
 H5a ALL-UPF reviewers are MORE likely to review Video Games and Toys & Games (one-sided each).
 H5b ALL-UPF reviewers are LESS likely to review Sports & Outdoors and Health & Household (one-sided each).
 H5c Baby Products: difference in either direction (two-sided). Holm over the 5 tests in H5a-c. Pet Supplies and Health & Personal Care: descriptive only.
 Robustness: UPF share as a continuous score (Spearman with number of categories reviewed); reviewers in the shopper-network backbone only.
 Caveat: reviewing a video game is not the same as being a gamer household; the claims are about review behaviour.
H5 RESULTS (15 Nov; upf/notebooks/cross_category.py; data/processed/cross_category_results.txt; six more category files downloaded, all gzip OK: Video_Games 0.81 GB, Baby_Products 0.84, Toys_and_Games 1.95, Pet_Supplies 2.33, Sports_and_Outdoors 2.63, Health_and_Household 3.20; gitignored)
 141,977 reviewers with >= 3 matched grocery reviews: ALL-UPF 37,287; MOSTLY-NOT 40,577; between 64,113. Share also reviewing: Video Games 19%, Toys 51%, Sports 62%, Health & Household 89%, Baby 29%, Pet 57%, Health & Personal Care 13%.
 Difference ALL-UPF minus MOSTLY-NOT (percentage points, weighted over activity strata; 2,000 shuffles within strata; Holm over 5):
  H5a Video Games +4.3 (19.7% vs 16.3%), Holm p=.0025: SUPPORTED; Toys & Games +4.7 (51.4% vs 47.9%), Holm .0025: SUPPORTED.
  H5b Sports & Outdoors -4.5 (58.1% vs 63.8%), Holm .0025: SUPPORTED; Health & Household -4.2 (85.7% vs 91.0%), Holm .0025: SUPPORTED.
  H5c Baby Products -0.4, p=.20: no difference. Descriptive: Pet Supplies +0.2 (none); Health & Personal Care -2.7 (9.9% vs 13.5%).
 Robustness: same differences among network-filter reviewers (3-50 matched reviews, 77,833). UPF share is NOT related to how many of the 7 categories a reviewer uses (Spearman -0.003), so it is not an activity artefact;
  continuous UPF share vs each category: Video Games +.044, Toys +.038, Sports -.037, Health & Household -.051, Health & Personal Care -.033 (small).
 READING: the ultra-processed side of the shopper network is also the games-and-toys side; the less processed side reviews more sports, household-health and personal-care products. Effects are modest (4-5 points).
 NOT CONTROLLED: what kind of groceries they buy (a candy-heavy basket may signal children in the household; Baby shows no difference though); demographics are unobservable (and not to be inferred).
- 15 Nov: story page v2 adds 'Beyond the grocery aisle' (H5 cross-department results, dot chart) and a footer line on pseudonymous cross-category linking.

## MIXED PRODUCT NETWORK across departments (16 Nov; user: 'an interesting network of purchases from what we already have, scale to all categories later'). Design fixed BEFORE building.
Nodes = products from groceries (matched to Open Food Facts) and the 7 downloaded departments; link = shared reviewers. Reviews, not purchases; pseudonymous IDs; aggregate only.
 Reviewers: the shopper-network reviewers (2-50 reviews of matched groceries); drop accounts with > 200 reviews across the 7 departments (power reviewers would link everything).
 Products: >= 10 distinct such reviewers. Projection = shared-reviewer counts; backbone = disparity filter (alpha .01); largest connected component.
 Describe: Louvain communities (department mix, NOVA-4 share among their groceries), labelled by c-TF-IDF words from a sample of each community's review text (course method, no word lists);
 bridges (betweenness); non-food products whose grocery neighbours lean most ultra-processed vs least.
 Product names need the department METADATA files (not downloaded); labels come from review text for now.
PRE-DECLARED H6 (product-level version of H5): for each non-food product in the backbone, 'UPF lean' = share of its grocery neighbours that are NOVA 4.
 Mean UPF lean is HIGHER for Video Games + Toys products than for Sports + Health & Household products (one-sided).
 Null: NOVA labels of grocery nodes shuffled within Open Food Facts category (correct within-group shuffle), 2,000 times. Exploratory otherwise.
MIXED NETWORK RESULTS (16 Nov; upf/notebooks/mixed_network.py; data/processed/mixed_network_results.txt, mixed_communities.csv; caches gitignored)
 Collected 6,544,641 reviewer-product pairs (336,899 reviewers; 1.14M products; 8 departments). After filters (1,188 power reviewers dropped; products with >= 10 reviewers): 104,809 products; 47.5M co-review pairs;
 disparity backbone 129,973 edges; largest component 16,729 products / 128,582 links (H&H 6,508, Pet 4,634, Grocery 3,020, Sports 862, Toys 713, Baby 542, Video Games 410). 67% of links stay within a department.
 Louvain 104 communities, modularity .46. Labelled by c-TF-IDF of sampled reviews (no product names: department metadata not downloaded). Largest: household-health + groceries (714 groceries, NOVA-4 share .50; words taste, oil, pain, scent);
  cleaning/batteries household (groceries .62); dogs; cats; SNACKS/SWEETS groceries (1,155 groceries, NOVA-4 .77: chocolate, snack, protein, cookies); PANTRY groceries (613, .79: pantry, sauce, soup); baby + toys (diapers, toys);
  video games; aquarium; emergency/camping food (sports + grocery, .71); GUMMY VITAMINS + GAMES (H&H + toys + grocery, .80); birds; small pets; VEGAN meat/cheese substitutes (76 groceries, .93).
 Reading: the network is organised mainly by department and by pet; the grocery side splits into a household-health cluster where only half the groceries are ultra-processed vs snack and pantry clusters at ~.77-.79.
 H6 (pre-declared): mean UPF lean of non-food neighbours, games/toys .756 vs sports/household .569, difference +0.187 vs null mean +0.142, one-sided p=.028 -> nominally SUPPORTED but WEAK: only 18 games/toys products have >= 3 grocery neighbours (828 sports/household).

## THE COMPLETE JOURNEY (16 Nov; 84.51 deg / dunnhumby via the completejourney R package, CC0; downloaded to upf/data/raw/completejourney/, gitignored; read with pyreadr 0.5.9, newly installed in .venv-nlp)
Files: transactions.rds 12,775,661 B; products.rda 869,019; demographics.rda 4,237; coupons.rda 324,969; coupon_redemptions.rda 8,370; campaigns.rda 8,264; campaign_descriptions.rda 496 (promotions.rds 25 MB skipped).
Profile: 1,469,307 transaction lines, 2,469 households, 155,848 baskets, 68,509 distinct products bought, 2017-01-01 to 2018-01-01. Demographics for 801 households (age, income, home ownership, marital status, size, composition, kids).
 Products (92,331): department (32), brand (National / Private), product_category (303), product_type (2,378, e.g. 'KIDS CEREAL', 'WAFFLES/PANCAKES/FRENCH TOAST'), package size. NO product barcode.
 coupons.coupon_upc is the COUPON's code (one coupon covers many product_ids), not a product barcode.
LINKING CONSTRAINT: no product-level link to Amazon or Open Food Facts is possible. Only a TYPE-level bridge: map each product type to Open Food Facts categories (embedding cosine between type names and
 category names, hand-checked) -> typical NOVA-4 share per type -> estimated ultra-processed share of each household's basket; optionally attach the Amazon pleasure/purity vocabulary per category.
 Within-type variation is lost (an organic and a sugary kids cereal get the same type). Not decided yet whether to link or to analyse Complete Journey on its own.
TYPE-LEVEL BRIDGE + HOUSEHOLD TESTS -- PRE-DECLARED 16 Nov before any match or household estimate was computed (user chose 'link by product type').
 Food departments: GROCERY, PRODUCE, MEAT, MEAT-PCKGD, DELI, PASTRY, NUTRITION, SEAFOOD, SEAFOOD-PCKGD, SALAD BAR, FROZEN GROCERY, CHEF SHOPPE (drug/GM, fuel, cosmetics, floral, spirits, misc excluded).
 Reference: Open Food Facts main categories with >= 30 NOVA-labelled products sold in the United States; for each, NOVA-4 share.
 Match: embed 'product category: product type' (lowercased) and the readable Open Food Facts category name with all-MiniLM-L6-v2; each product type takes its TOP-1 category by cosine.
  Types with best cosine < 0.50 are UNMATCHED (left out). Hand-check 40 random matched types (read by me) and report the share judged a sensible match.
 Household estimate: estimated UPF share = mean of the matched types' NOVA-4 shares over the household's food purchase LINES (one line = one product bought); report the share of food lines matched.
 H7a households with children (kids_count > 0) have a HIGHER estimated UPF share than households without (one-sided; permutation of the label, 5,000).
 H7b estimated UPF share DECREASES with income (Spearman across the ordered income bands, one-sided; permutation 5,000). Holm over 2. Sample: the 801 households with demographics.
 Exploratory: private-label vs national-brand share; household similarity network (cosine of type profiles) and its communities vs income/kids/UPF share.
 Caveats to state: within-type variation lost; one retailer's frequent shoppers; reference shares come from what Open Food Facts volunteers scanned.
BRIDGE + H7 RESULTS (16 Nov; upf/notebooks/cj_bridge.py; data/processed/cj/ gitignored; pyreadr used to read the R files)
 2,012 food product types; 499 Open Food Facts reference categories (>= 30 US NOVA products); 1,756 types matched (cosine >= .50; quartiles .57/.64/.71).
 HAND-CHECK of 40 matched types: 27 sensible (68%). Misses: non-food types filed under GROCERY (bird seed, cleaners, 'kites', supplements), wrong food class (baby food -> crackers,
  fresh papaya -> dried mangoes, fresh cranberries -> dried cranberries, creamer -> dairy drinks, fruit tray -> sandwiches, vegetarian meats -> frozen meats, honey -> condiments), a nonsense type ('condiments: covergirl').
 Household estimates: 1,280,373 food purchase lines, 91% matched; 2,463 households; estimated UPF share mean .632 (quartiles .589/.631/.673).
 H7a kids (288 households) vs none (513): .633 vs .619, +0.0145, one-sided p=.0002, Holm .0004: SUPPORTED (small).
 H7b income: Spearman -0.190 (n=801), one-sided p=.0002, Holm .0004: SUPPORTED. Band means fall from about .64 (15-34K) to about .58-.60 (150K+); 'Under 15K' .625.
 EXPLORATORY robustness (not pre-declared): only types with cosine >= .65 (954 types, 54% of lines): kids +0.014, income Spearman -0.173; cosine >= .75 (321 types, 21% of lines): kids +0.024, income -0.208. Holds.
 Exploratory: private-label share vs estimated UPF share Spearman +0.085.
 READING: households with children and lower-income households buy baskets whose product TYPES are more often ultra-processed; small effects; type-level estimate (within-type variation lost); one retailer's frequent shoppers.
DECISION (16 Nov, user): DROP the Complete Journey type-level link and the household income/children analysis from the story -- the type link loses too much nuance (68% sensible matches,
 within-type variation lost) and income/households do not add to the story. Results above stay on record, not to be cited. Focus instead: WHAT ELSE PEOPLE BUY (review) WHEN THEY BUY FOOD,
 with marketing VALENCE of those other products and the SENTIMENT of reviews across departments.

## WHAT ELSE DO FOOD SHOPPERS BUY, HOW IS IT SOLD, HOW DO THEY FEEL? -- PRE-DECLARED 16 Nov, before the metadata files were downloaded
Groups as in H5: reviewers with >= 3 reviews of matched groceries; ALL-UPF (share 1.0) vs MOSTLY-NOT (<= 0.5). Their reviews in the 7 departments (Video Games, Toys & Games, Sports & Outdoors, Health & Household,
 Baby, Pet Supplies, Health & Personal Care). Marketing copy = product features + description from the department metadata (>= 10 words). Valence = NRC VAD v2.1 mean over lexicon words (scale -1..1),
 ingredient-name words excluded as before. Comparisons are WITHIN department: per reviewer and department, the mean over their reviews; group difference per department weighted by number of reviewers;
 p from 2,000 shuffles of group labels within activity strata (3, 4, 5-9, 10+ matched grocery reviews).
 H8 PLEASURE EVERYWHERE: non-food products reviewed by ALL-UPF reviewers have HIGHER marketing valence than those reviewed by MOSTLY-NOT reviewers in the same department (one-sided).
 H9 HOW THEY WRITE: the valence of the reviews ALL-UPF reviewers write in other departments DIFFERS from MOSTLY-NOT reviewers' (two-sided). Star ratings reported alongside (descriptive).
 Holm over H8, H9. Descriptive: per-department breakdown; EmoLex emotions of these reviews (with the 'treat'-type artefact reading); a category-balanced log-odds word plot of the marketing copy of
 products that lean ALL-UPF vs lean MOSTLY-NOT (lean = share of a product's group reviewers who are ALL-UPF), and product names for the mixed-network communities.
H8/H9 RESULTS (16 Nov; upf/notebooks/elsewhere.py; data/processed/elsewhere_results.txt, elsewhere_wordplot.csv; caches gitignored; metadata files downloaded, all gzip OK: 3.03 GB total)
 1,593,627 reviews by the two groups in the 7 departments; marketing valence for 95%. (A first run crashed after H8/H9 on a column named 'copy'; fixed, rerun identical for H8/H9.)
 H8 PLEASURE EVERYWHERE: NOT SUPPORTED. Marketing valence of the non-food products ALL-UPF reviewers review vs MOSTLY-NOT: -0.0008 (null -0.0002), p=.997, Holm 1.0; every department within +-0.006.
 H9 HOW THEY WRITE: SUPPORTED. ALL-UPF reviewers write warmer reviews in other departments: +0.011 valence (null 0.000), p=.0005, Holm .001; positive in 6/7 departments (Video Games +.018, Toys +.013, Sports +.013, Baby +.013, Pet +.009, H&H +.008; H&PC +.001).
  Stars a little higher too (e.g. Toys 4.46 vs 4.42, Baby 4.40 vs 4.34; descriptive).
 Emotion words (descriptive): ALL-UPF reviewers say love (51.9 vs 39.1 per 10k), perfect, gift, fun, daughter, birthday, money; also disappointed, bad, smell, broke(n). MOSTLY-NOT reviewers say health words:
  weight, stomach, gut, disease, cancer, toxic, effective, formula, daily, result. 'treat' again inflates fear/sadness/disgust (artefact).
 WORD PLOT of non-food marketing copy (products leaning ALL-UPF vs MOSTLY-NOT reviewers, top vs bottom quartile, balanced in 7 departments, 15,552 per side):
  ALL-UPF side: durable, lasting, material, fabric, comfortable, adjustable, portable, convenient, lightweight, disposable, reusable, stains, odors, messes, birthday, holiday -> PRACTICAL / HOUSEHOLD / OCCASIONS.
  MOSTLY-NOT side: non-GMO, soy, dairy, supports, potency, preservatives, fillers, artificial, absorption, antioxidant, USDA, kosher, vegetarian, capsules, tested, verified -> SUPPLEMENTS / PURITY / CERTIFICATION.
  Top-leaning products: ALL-UPF baby wash, kids' paint books, Skylanders, doll food, batteries, potty; MOSTLY-NOT fermented chlorella, organic cinnamon supplement, vitamins, magnesium lotion.
 READING: the purity-and-certification vocabulary follows the less processed shoppers into supplements and wellness products; the ultra-processed shoppers' other products are family, kids and household
  goods sold on practicality, and they write warmer, gift-and-family reviews. Marketing pleasantness itself does not differ (H8 null).
 Mixed-network communities now have product names (e.g. 0 supplements + health foods; 6 Pampers, Play-Doh, Melissa & Doug; 7 video games; 9 camping/emergency; 10 board games + gummy vitamins; 13 Beyond Meat, Gardein, Oatly).

## THREE MORE (16 Nov, user picks from the course list) -- PRE-DECLARED before running
H10 RICH GET RICHER (week 2: preferential attachment). Grocery products (all Amazon grocery items). k0 = reviews a product had before 2018-01-01 (k0 >= 1); dk = new reviews during 2018.
 Measured attachment Pi(k) = mean dk among products with k0 = k (log bins); fit log(mean dk) = a + alpha*log(k). PREDICTION: alpha > 0 (popular products attract more new reviews); report whether
 alpha is near 1 (linear, as in the Barabasi-Albert model) or below 1 (sublinear). 95% CI by bootstrap over products (1,000). Null: the same number of 2018 reviews spread uniformly over products -> alpha 0.
 Also: the review-count distribution (CCDF, log-log). Exploratory: alpha for NOVA-4 vs NOVA 1-3 matched products.
HUBS (week 3: eigenvector centrality, PageRank; exploratory). On the mixed product network backbone (16,729 products): PageRank (weighted, alpha .85) and eigenvector centrality; top hubs by name;
 'compared to what': Spearman with degree, and the products with the highest PageRank relative to their degree (residual of log PageRank on log degree).
H11 VALIDATING THE SENTIMENT INSTRUMENT (week 7: validate a sentiment measure; stars as labels). Random 200,000 grocery reviews of matched products with text and a star rating.
 Our measure = NRC VAD valence of the review (food words excluded, as used in the story). PREDICTION / BAR: AUC for telling 1-2 star from 4-5 star reviews >= 0.70, and Spearman(valence, stars) > 0.
 Benchmarks: shuffled stars (null, AUC ~ .5); EmoLex positive-minus-negative share; a TF-IDF + logistic regression classifier trained on 80% and tested on 20% (upper benchmark, week 7).
RESULTS OF THE THREE (16 Nov; upf/notebooks/habits.py; data/processed/h11_validation.txt, h10_rich.txt, hubs.txt; upf/figures/rich_get_richer.png)
 H11 SENTIMENT VALIDATION: PASSES. 200,000 random grocery reviews of matched products (5-star 67%). VAD valence vs stars Spearman +0.547; AUC 1-2 vs 4-5 stars 0.886 (bar 0.70); EmoLex pos-neg 0.801;
  shuffled stars 0.500; TF-IDF + logistic regression (held-out) 0.988 = upper benchmark. Mean valence by stars 1..5: .058/.125/.168/.258/.337.
  Failure modes read: negation ('Not happy', 'Not tasty' score high), non-English reviews. Our valence measure is a valid but blunt instrument; the classifier catches negation ('not good', 'not worth').
 H10 RICH GET RICHER: SUPPORTED. 253,995 grocery products with reviews before 2018; 1,002,240 new reviews in 2018 (61% of products got none). Attachment exponent alpha 0.925 (95% CI 0.910-0.936), uniform null 0.000:
  near-linear (slightly sublinear) preferential attachment. Review counts heavy-tailed: 28% of products >= 10 reviews, 4% >= 100, 0.23% >= 1,000, max 36,707.
  Exploratory: alpha NOVA 4 .898 vs NOVA 1-3 .845. Caveat: 'fit get richer' (better products both had and get more reviews) is not separated from pure popularity; discontinued products also stop gaining.
 HUBS (exploratory): PageRank vs degree Spearman +0.84 (eigenvector +0.75): hubs are mostly the high-degree products. Top hubs are everyday staples, not food: Amazon Basics AA/AAA batteries,
  essential oils (cassia, cedarwood, rosemary), Kleenex, Glad trash bags, Penetrex pain cream, Dr. Elsey's cat litter, Greenies dog treats, Fancy Feast, a bathroom scale. Top-100 PageRank: Health & Household 48, Pet 30, Grocery 21, Baby 1.
  Groceries among the top-100 grocery hubs are NOVA 4 at .72 vs .70 for all network groceries: hubs are not especially ultra-processed. Beyond-degree hubs include a bird food (degree 74) and a calorie-free peanut spread (degree 12).
- 16 Nov: story page v3 adds 'Purity travels, pleasure stays home' (H8 null, H9, non-food word contrast), a validation callout (stars, AUC .89), 'The rich get richer' (log-log chart, alpha .93), 'The hubs are not food' (PageRank), and H8 under 'What did not hold up'.
- 16 Nov: story page v4 adds the NOVA breakdown of the 75,933 matched listings (1: 7,337 10% / 2: 1,537 2% / 3: 14,923 20% / 4: 52,136 69%) and the volunteer-scanning disclaimer under the Story Facts label.
- 16 Nov: LISTING VAD (descriptive; upf/notebooks/listing_vad.py; data/processed/listing_vad.txt; upf/figures/listing_vad.png): 61,341 matched listings with copy >= 10 words (median 42 lexicon words), food words excluded.
  Means NOVA 1/2/3/4: valence .267/.252/.263/.280; arousal -.137/-.135/-.124/-.116; dominance .062/.070/.048/.031. Spearman: V-A .14, V-D .34, A-D .42.
  Within category (25 categories, 29,822 listings, 2,000 shuffles): valence +0.0135 (p=.0005), arousal +0.0099 (p=.0005), DOMINANCE -0.0180 (p=.0005; descriptive, not pre-declared):
  ultra-processed copy is slightly more pleasant and more exciting but LESS 'in control' (dominance = powerful/in-control vs weak/no control). All shifts small; the distributions overlap almost completely.
- 16 Nov: DRIVERS of arousal and dominance (upf/notebooks/vad_drivers.py; category-balanced, 10,255 listings per side, 25 categories; descriptive):
  DOMINANCE (balanced difference -0.014): less processed copy is pulled UP by authority/control words: certified (+.61; 5.8 vs 3.1 per 1k), healthy, Non-GMO 'project', best, most, pure, verified, world, all,
   and the brand voice 'we' (9.6 vs 6.7 per 1k: smaller makers speaking as 'we'). Ultra-processed copy is pulled DOWN by sensory/portion/convenience words with low dominance: flavor, snack, box, cup, gram, easy, creamy.
   Partly offset: ultra-processed copy uses more perfect, great, real, your, enjoy, favorite, ready (positive-dominance pleasure words) and fewer low-dominance purity words (kosher, vegan, simple).
  AROUSAL (balanced difference +0.011): about half because PURITY words are CALM (organic -.31 is the largest single contributor; also non[-GMO], vegan, simple, ingredient, healthy, pure),
   half because PLEASURE words are EXCITING (delicious, bite, enjoy, tasty, fun, up); calm convenience words (easy, box, pack, baked, minute, classic) pull the other way.
  READING: confirms the pleasure-vs-purity reading for all three dimensions; 'dominance' here = authority/certification vs portions/sensations, not hard-selling.

## YELP LEXICON PILOT (16 Nov; user: 'test a small portion with Yelp') -- written BEFORE download and scoring
Resource: NRC Yelp Restaurant Sentiment Lexicon (Kiritchenko et al., SemEval-2014; automatic from Yelp restaurant reviews; affirmative and negated-context entries; unigrams + bigrams; free for research, cite).
Sample: 20,000 random reviews from the H11 validation draw (grocery reviews of matched products; seed fixed). Compare against stars: AUC 1-2 vs 4-5 stars and Spearman; and COVERAGE (share of tokens scored).
Yelp score = mean of unigram scores, with tokens inside a negated context (from a negator such as not/no/never/n't to the next punctuation) looked up as their negated entry; bigram variant reported too.
Reference on the SAME 20,000: our NRC VAD valence (AUC .886 on the full 200k). Decision rule: prefer Yelp only if AUC is >= 0.02 higher; note that Yelp scores were learned from review stars (partly circular).
Also: what Yelp gives 'treat', 'hot', 'sweet', 'not happy' (the known failures).
YELP PILOT RESULT (16 Nov; upf/notebooks/yelp_pilot.py; data/processed/yelp_pilot.txt; lexicon 2,191,177 B in upf/data/raw/nrc/yelp/, gitignored):
 Same 20,000 reviews (18,770 with 1-2 or 4-5 stars): NRC VAD valence AUC .889, Spearman +.550; Yelp unigrams AUC .950, +.658; Yelp unigrams+bigrams AUC .964, +.683. Coverage: Yelp scores 94% of tokens.
 Decision rule (>= .02 better) MET: Yelp (unigrams+bigrams) is the better review-sentiment instrument. Caveat: learned from Yelp review stars (partly circular), restaurant domain; scores are PMI differences (unbounded), not -1..1.
 Fixes the known failures: 'Not happy' Yelp -1.47 (VAD +0.98), 'Not tasty' -2.31 (VAD +0.92), 'treat' +0.92 (positive, unlike EmoLex), 'stale' -2.57, 'arrived broken' -0.90.
 Remaining errors are mostly label noise: 1-star reviews that read positive ('Great. Can't miss with skippy').
 Implication: review-side results (H9 review valence elsewhere, A1-H3 promise-experience gap, review emotion comparisons) were measured with the weaker instrument; marketing copy stays on VAD (Yelp is review language).

## EMOTION CLASSIFIER PILOT (16 Nov; user: emotion over positive/negative; 'classifiers handle negation better than a lexicon'; picked 'Cardiff large only') -- written BEFORE download and scoring
Why: EmoLex counts words, so 'not happy' scores as joy and 'treat' as anger/disgust/fear. A contextual classifier reads the whole sentence.
Model: cardiffnlp/twitter-roberta-large-emotion-latest (RoBERTa-large fine-tuned on SemEval-2018 Task 1 tweets via SuperTweetEval; MIT; safetensors).
 11 emotions, multi-label (a sigmoid per emotion): anger, anticipation, disgust, fear, joy, love, optimism, pessimism, sadness, surprise, trust.
 The 8 Plutchik emotions overlap EmoLex exactly, so results line up with the EmoLex numbers. Not trained on product reviews: must be validated here.
Sample: the SAME 20,000 reviews as the Yelp pilot (H11 draw, same seeds); text = review title + '. ' + body, truncated to 512 tokens. No food-word exclusion (the model needs whole sentences).
Scores: per-emotion probability; an emotion is 'present' if probability >= 0.5 (the model's own rule). EmoLex on the same reviews = share of words tagged with each emotion (food words excluded, as before).
PRE-DECLARED CHECKS
 C1 STARS: 4-5 star reviews should have higher joy, love, optimism, trust and lower anger, disgust, sadness, pessimism than 1-2 star reviews.
  Bar: correct direction for at least 7 of these 8 emotions; AND the composite (mean of joy, love, optimism, trust minus mean of anger, disgust, sadness, pessimism) separates 1-2 from 4-5 stars with AUC >= the VAD valence AUC on the same reviews (.889).
  Same check reported for EmoLex as the comparison.
 C2 NEGATION (the course's argument): split reviews by whether they contain a negator (not, no, never, cannot, none, nothing, nobody, nowhere, neither, nor, or any word ending in n't).
  Prediction: the classifier's composite AUC beats EmoLex's on both subsets, and its advantage is LARGER on reviews with a negator. Also report 'joy' among 1-2 star reviews with a negator (EmoLex should be fooled, the classifier less so).
 C3 'TREAT' ARTEFACT: reviews containing 'treat': mean anger/disgust/fear from the classifier vs EmoLex, against matched reviews without it. Prediction: the classifier does not show EmoLex's excess.
 C4 HAND LABELS (after the user labels ~100 reviews, stratified by stars, blind to model output): for each emotion present >= 10 times in the labels, F1 of the classifier vs EmoLex.
  Bar: classifier macro-F1 >= 0.5 and higher than EmoLex's.
DECISION RULE: the classifier replaces EmoLex as the review-emotion measure if C1 and C4 pass. Then the review-emotion comparisons (UPF vs less processed, ALL-UPF vs MOSTLY-NOT reviewers elsewhere) are rerun with it on samples sized by the measured speed.
 If C1 or C4 fails, EmoLex stays and the classifier is reported as a robustness check. Marketing copy is NOT scored (the model was trained on personal expression, not ad copy).
EMOTION PILOT RESULT (16 Nov; upf/notebooks/emotion_pilot.py; data/processed/emotion_pilot.txt; soj/emotion_pilot.csv.gz; model 1.42 GB in ~/.cache/huggingface, user-approved download)
 Sample verified identical to the Yelp pilot. Speed 91 reviews/s on the Mac GPU (MPS): 20,000 in 220 s; 1M reviews ~3 h.
 C1 PASSES: 8/8 directions right (joy .09 -> .93, love .02 -> .54, optimism .04 -> .70, trust .01 -> .14; anger .73 -> .05, disgust .80 -> .04, sadness .54 -> .04, pessimism .14 -> .01).
  Composite AUC 1-2 vs 4-5 stars: classifier .983 | VAD valence .889 | EmoLex .785 (TF-IDF+LR benchmark on the 200k was .988).
 C2 SUPPORTED: advantage over EmoLex +.251 on reviews with a negator (AUC .972 vs .721) vs +.144 without (.984 vs .840). 1-2 star reviews with a negator: joy present 4.6% (classifier) vs 47.8% with a joy word (EmoLex).
  'Not happy with the product.' -> anger .99, sadness .96 (EmoLex: joy, trust, anticipation). "Not bad at all, I'd buy again." -> optimism .95, joy .70 (EmoLex: anger, disgust, fear, sadness).
 C3 SUPPORTED: reviews with 'treat' (n=280) have LESS anger/disgust/fear from the classifier (.057/.065/.009 vs .194/.213/.015) where EmoLex had 5-6x MORE.
 C4 PENDING (user's ~100 hand labels).
 CAVEATS: (1) anticipation, fear, surprise, trust, pessimism are present (p >= .5) in under 2% of reviews: in practice the instrument has ~6 working emotions (joy, optimism, love | disgust, anger, sadness).
  (2) The emotions are strongly correlated (Spearman joy-disgust -.82, anger-disgust +.89, sadness-pessimism +.86): much of the signal is one positive-negative axis.
  Within 5-star reviews the positive emotions still separate (love present in 58%, joy 96%; joy-love Spearman .32, joy-optimism .23), so 'love' vs plain 'joy' is the usable nuance.
  (3) Remaining errors are mostly star-label noise (1-star reviews whose text is glowing).
 C4 SET-UP (16 Nov): upf/label_emotions.html (built by upf/notebooks/make_emotion_label_tool.py; gitignored, holds review text). 100 reviews = 20 per star level from the pilot 20,000,
  random order, stars and all scores hidden; 11 emotions + None, multi-label. Key (id -> stars) in soj/emotion_label_ids.csv. Scoring: upf/notebooks/emotion_c4.py (dry-run on fake labels only).
 C4 RESULT (16 Nov; user labelled all 100; data/processed/emotion_c4.txt): FAILS the pre-declared bar.
  User ticked: joy 33, sadness 20, disgust 18, pessimism 15, trust 12, love 9, anger 7, anticipation/surprise/fear 5 each, optimism 2, None 12. Notes: 'disappointment' (x2).
  Emotions ticked >= 10 times: joy, trust, disgust, sadness, pessimism. Classifier macro-F1 .396 (bar .50). On the shared emotions (joy, trust, disgust, sadness) classifier .470 vs EmoLex .409.
  Per emotion F1 classifier | EmoLex: joy .82 | .58; sadness .60 | .43; disgust .46 | .36; trust .00 | .27; pessimism .10 | n/a.
  Why: (1) the classifier OVER-labels: optimism 37 reviews vs user 2, anger 33 vs 7, disgust 43 vs 18, love 23 vs 9: complaints get anger + disgust + sadness together (a negativity detector).
   (2) it almost never fires trust (0) or pessimism (5) where the user saw 12 and 15. (3) the user's notes ask for 'disappointment', which neither instrument has as a category.
  DECISION (pre-declared rule): EmoLex stays the review-emotion measure; the classifier is reported as a robustness check. Both beat chance mainly on POLARITY;
   neither reproduces a human's distinction between specific negative emotions. Only joy (F1 .82) and sadness (.60) reach usable agreement. Caveat: one labeller, 100 reviews.

## GOEMOTIONS PILOT (16 Nov; user: 'Try GoEmotions model') -- written BEFORE download, scoring and labelling
Why: C4 failed; the user's notes asked for 'disappointment', which GoEmotions has (also approval, annoyance, gratitude, admiration: closer to review language).
Model: SamLowe/roberta-base-go_emotions (RoBERTa-base on GoEmotions, 58k Reddit comments, 28 labels incl. neutral; multi-label sigmoid; MIT; safetensors 0.5 GB).
Same 20,000 pilot reviews, same text and truncation. Present = probability >= 0.5 (fixed now; NO per-label threshold tuning on our labels).
LABEL SET for the new hand labels (12 + None; chosen now for review relevance, before seeing any GoEmotions output):
 positive: admiration, approval, gratitude, joy, love, excitement | negative: disappointment, annoyance, anger, disgust, sadness | other: surprise.
 The other 16 GoEmotions labels are scored but not hand-labelled and not used in G4.
FRESH LABELS: 100 NEW reviews (20 per star level) from the 20,000, excluding the 100 used for C4 (re-using those would bias the test). Blind: stars and all scores hidden.
PRE-DECLARED CHECKS
 G1 STARS: admiration, approval, gratitude, joy, love, excitement higher in 4-5 than 1-2 star reviews; disappointment, annoyance, anger, disgust, sadness lower.
  Bar: >= 10 of these 11 directions right AND composite (mean positive six minus mean negative five) AUC 1-2 vs 4-5 >= .889 (VAD on the same reviews).
 G2 NEGATION: as C2: composite AUC beats EmoLex on reviews with and without a negator; report the advantage on each.
 G4 HAND LABELS: per emotion the user ticks >= 10 times, F1 of GoEmotions (p >= .5).
  Bar: macro-F1 >= 0.5; AND on the emotions that Cardiff also has (joy, love, anger, disgust, sadness, surprise) GoEmotions macro-F1 > Cardiff's; AND > EmoLex on the ones EmoLex has (joy, anger, disgust, sadness, surprise).
  Disappointment F1 reported on its own (the user's own category).
 DESCRIPTIVE ONLY (not a test): GoEmotions vs the OLD 100 C4 labels on the shared emotions (joy, love, anger, disgust, sadness, surprise, fear).
DECISION RULE: if G1 and G4 pass, GoEmotions becomes the review-emotion measure; else 'joy and sadness only' (from C4) with EmoLex + both classifiers as robustness.
GOEMOTIONS RESULT G1-G2 (16 Nov; upf/notebooks/goemotions_pilot.py; data/processed/goemotions_pilot.txt; soj/goemotions_pilot.csv.gz; model 0.5 GB in ~/.cache/huggingface)
 300 reviews/s on MPS (3x Cardiff). G1 PASSES: 11/11 directions; composite AUC .959 (VAD .889, Cardiff .983). G2: advantage over EmoLex +.219 with a negator vs +.121 without.
 RISK SEEN BEFORE LABELLING: at p >= .5 it is SPARSE. Present in: admiration 46%, love 18%, neutral 12%, disappointment 3.4%, approval 3.0%, joy 2.9%, disgust 1.6%, sadness .5%, anger 0%.
  Only 24% of 1-2 star reviews get any of the five negative labels (13% disappointment). Happy reviews come out as 'admiration' rather than 'joy'.
 DESCRIPTIVE vs the OLD C4 labels: joy F1 .00 (it says admiration), love .57 (Cardiff .44), disgust .29, sadness .00; its 'disappointment' vs the user's sadness-or-disappointment-note: F1 .58.
 G4 SET-UP: upf/label_emotions_set2.html (gitignored), 100 NEW reviews (0 overlap with set 1; 20 per star level; seeds 21/22), 12 labels + None; key soj/go_label_ids.csv; scoring upf/notebooks/go_g4.py (dry-run on fake labels only).
 G4 RESULT (16 Nov; user labelled all 100; data/processed/go_g4.txt): FAILS. Emotions ticked >= 10 times: approval 29, disappointment 29, admiration 18, annoyance 10.
  GoEmotions F1: admiration .49, approval .13, disappointment .23, annoyance .00 -> macro-F1 .212 (bar .50). No shared emotion reached 10 ticks, so the Cardiff/EmoLex comparisons are empty.
  Cause = UNDER-labelling at p >= .5 (the risk logged before labelling): approval 2 vs user 29, disappointment 6 vs 29, annoyance 0 vs 10.
  EXPLORATORY (threshold-free, not a test): GoEmotions RANKS the reviews sensibly: ranking AUC admiration .82, approval .77, disappointment .77, annoyance .79, disgust .96.
   So the information is there but the fixed cut-off is too high; choosing a lower cut-off on these labels would be tuning on the test set and is NOT done.
  FINDING ABOUT THE LABELS THEMSELVES: with set-2's label list the user ticked joy 4 and sadness 1 (set 1: joy 33, sadness 20); approval and disappointment took their place.
   Human emotion labels depend on the label list offered: the same kind of review is 'joy' or 'approval', 'sadness' or 'disappointment' depending on the menu.
  DECISION (pre-declared): fallback = emotion claims restricted to the polarity-level signal (joy-like vs sadness/disappointment-like), EmoLex + both classifiers as robustness;
   no classifier is adopted as a fine-grained emotion measure.
 DISTRIBUTIONS (20,000 reviews, p >= .5): Cardiff 2.4 emotions per review, 3.5% with none; 4-5 stars joy 95% / optimism 85% / love 54%, 1-2 stars disgust 85% / anger 76% / sadness 52%.
  GoEmotions 0.9 labels per review, 24% with none (excluding neutral); 4-5 stars admiration 59% / love 23% / joy 4%; 1-2 stars neutral 26% / disappointment 13% / disapproval 13%.
 DOMAIN SHIFT (user, 16 Nov): both models were trained on social media (Cardiff: tweets; GoEmotions: Reddit comments), not product reviews; each carries its platform's idea of an emotion
  (Cardiff 'optimism' on 85% of good reviews; GoEmotions calls praise 'admiration' and a quarter of complaints 'neutral'). For the limitations section.

## EXTRA OPEN FOOD FACTS FIELDS (16 Nov; descriptive; soj/off_fields_matched.csv.gz, gitignored)
The 75,933 matched listings are 58,051 distinct barcodes (several listings share one). Coverage among them:
 countries 99.9% but 81.5% list ONLY the United States (scan location, not market: useless for cross-country comparison); origins 2.3%, manufacturing places 0.8%, stores 1.7%.
 Nutrition per 100 g: energy 96.5%, salt 95.0%, sugars 92.4%, saturated fat 86.3%, fibre 79.2%. Nutri-Score grade 100% (unknown ~10-20%). Additives count 100% (mean NOVA 1/2/3/4: .08/.04/.32/3.24).
 Labels 32% (organic 9.6%, kosher 4.3%, vegan 4.0%). Brand owner 80% (Whole Foods 1,420 products, NOVA-4 share .46; General Mills .90, Kellogg .96, Mondelez .93, Nestle .92).
 Environmental score 72.5% unknown. Palm oil tag 13%; vegan 18% / non-vegan 42%.
 Nutri-Score by NOVA: NOVA 1 is 42% grade A; NOVA 4 is 34% grade E (processing and nutrition overlap but are not the same).

## PROCESSING OR NUTRITION? (16 Nov; user: 'try comparing with Nutri-Score on language sentiment') -- written BEFORE computing
Question: is the warmer, livelier marketing copy of NOVA 4 (A1: valence +0.0135, arousal +0.0099 within category) about PROCESSING, or just about worse NUTRITION (sweet treats)?
Data: soj/listing_vad.csv.gz (61,341 listings with copy >= 10 words; NRC VAD, food words excluded) joined to Open Food Facts Nutri-Score grade A-E by barcode; listings with grade unknown / not-applicable dropped.
 N1 (primary) PROCESSING BEYOND NUTRITION: within strata of category x Nutri-Score grade, NOVA 4 copy has HIGHER valence than NOVA 1-3 copy (one-sided).
  Strata need >= 20 listings per side. Baseline on the SAME listings and the same >= 20 rule, strata = category only. Report the share of the baseline effect that remains.
  Reading fixed now: >= 50% retained and p < .05 -> 'about processing, not only nutrition'; < 50% or p >= .05 -> 'nutrition explains much of it'.
 N2 NUTRITION BEYOND PROCESSING: within strata of category x NOVA group (4 vs 1-3), does valence change with Nutri-Score grade (A=1 ... E=5)?
  Statistic: listing-weighted mean of within-stratum Spearman(grade, valence), strata with >= 30 listings and >= 3 grades; two-sided.
 Arousal is reported the same way (N1b, N2b). Nulls: labels (N1) or grades (N2) shuffled within strata, 5,000 times. Holm over the four p-values.
 Descriptive: mean valence by NOVA group x grade.
RESULT (16 Nov; upf/notebooks/nutri_vs_nova.py; data/processed/nutri_vs_nova.txt). 50,004 of 61,341 listings have a Nutri-Score A-E (82%).
 N1 SUPPORTED, 'ABOUT PROCESSING, NOT ONLY NUTRITION': within category x grade NOVA 4 copy valence +0.0117 (p=.0002, Holm .0008; 100 strata, 30,556 listings);
  on exactly those listings the category-only effect is +0.0108 -> 108% retained (holding nutrition fixed does not shrink it). Baseline on all graded listings +0.0127.
 N1b arousal: +0.0116 within category x grade vs +0.0118 category-only on the same listings -> 98% retained (p=.0002, Holm .0008).
 N2 valence vs grade within category x NOVA: Spearman +0.009, p=.067 (Holm .067): NOT significant -> worse nutrition alone does not make copy warmer.
 N2b arousal vs grade: +0.023, p=.0002 (Holm .0008): worse nutrition goes with slightly livelier copy (tiny).
 Descriptive: NOVA 1-3 copy valence is flat across grades (.258-.272); NOVA 4 copy is warmer at EVERY grade, including grade A (.273 vs .265) and E (.284 vs .258).
 READING: the pleasure-vs-purity wording follows PROCESSING, not nutrition. A grade-A ultra-processed product is still sold more warmly than a grade-A less processed one.
Status: the pre-declared fallback above stands until the TAs advise: no classifier is adopted for specific emotions.
Questions to ask:
 1. Which emotion classifier (if any) should we use for review text: Cardiff (11 emotions, over-labels), GoEmotions (28, under-labels), or stay with EmoLex? Is a transformer classifier acceptable as the course's 'classifier' technique?
 2. Both failed our hand-label bar (macro-F1 .40 and .21 vs .50) but beat EmoLex and track stars well (AUC .98 / .96). Is that enough to use one at the polarity level, or for a few emotions (joy, sadness, disgust)?
 3. Is lowering GoEmotions' 0.5 cut-off acceptable if chosen on a SEPARATE labelled set (its ranking AUC is .77-.96), or is that out of scope?
 4. Domain shift (tweets / Reddit vs product reviews): is a short limitations note enough, or should we fine-tune / use a review-trained model?
 5. One labeller, 2 x 100 reviews, and labels that shift with the label list: should the partner label the same reviews for inter-annotator agreement (Cohen's kappa)?
Bring: C1-C4 and G1-G4 numbers above, the distribution chart, the two label sets.
- 16 Nov: COMMUNITY MAP (descriptive figure; upf/notebooks/community_map.py -> upf/figures/community_map.png). The 14 largest Louvain communities of the mixed network (16,132 of 16,729 products)
  as bubbles (area = products, colour = main department), links = backbone links between communities (>= 30), layout by link strength relative to size (Kamada-Kawai + overlap removal).
  Strongest between-community links: household health -- household essentials 9,700; household essentials -- snacks & sweets 6,105; -- dogs 4,815; household health -- dogs 3,986; household essentials -- pantry 3,685.
  Reading: the two grocery communities (snacks 77% UPF, pantry 79%) sit beside household essentials, while the healthier grocery mix (50% UPF) sits inside the household-health community;
  video games, aquarium and camping are on the edge; birds, small pets and vegan substitutes are islands (< 30 links to any other community). UPF shares shown only where a community holds >= 50 groceries.
- 16 Nov: HOUSEHOLD 'CHECKOUT AISLE' IDEA (user hypothesis: buying household products on Amazon makes it easy to sneak in UPF). EXPLORATORY count, not pre-declared.
  Health & Household split by Amazon sub-category (soj/hh_subcategories.csv.gz; 172,058 reviewed products, 100% have one): Household Supplies 39k, Health Care 39k, Vitamins/Supplements 39k, ...
  Share of reviewers who reviewed >= 1 product (activity-adjusted, ALL-UPF vs MOSTLY-NOT): household supplies 63.0% vs 66.1%; vitamins/diet 46.3% vs 59.5%; health care 60.2% vs 66.1%.
  ALL-UPF reviewers with both UPF and household supplies: 23,094 vs 24,163 expected if UPF made no difference (ratio 0.96). Mean household-supplies reviews 2.37 vs 2.98.
  READING: NOT supported at the population level: ultra-processed reviewers are slightly LESS likely to review household supplies. The big gap is supplements (the less processed group).
  The strong snacks <-> household-essentials link on the community map is a BASE-RATE / HUB effect: about two-thirds of everyone reviews household supplies, so those products link to everything.
  Not tested: same-day co-occurrence within reviewer (needs timestamps).

## SHOPPER TYPES (16 Nov; user: 'shopper profiles') -- written BEFORE building. EXPLORATORY (one pre-declared test, T1).
Question: what kinds of shoppers are there among grocery reviewers, judged only by what they review OUTSIDE groceries, and how ultra-processed is each type's grocery reviewing?
Reviewers: the two groups with cached reviews in other departments (soj/elsewhere_reviews.csv.gz): ALL-UPF (UPF share 1.0) and MOSTLY-NOT (<= 0.5); the 'between' group is not cached (limit).
 Keep reviewers with >= 5 non-food reviews. Groceries are NOT in the profile, so the types are not built from the thing we compare (no circularity).
Profile: counts over Amazon sub-categories (second level of each product's category path, all 7 departments), weighted TF-IDF style so that categories nearly everyone reviews
 (e.g. Household Supplies) count less (the base-rate trap found on 16 Nov). Similarity: cosine. Network: each reviewer linked to their 10 most similar reviewers (kNN, symmetrised).
Types: Louvain communities (seed fixed); described by over-represented sub-categories (lift vs all kept reviewers) and size. Names are our reading.
T1 (pre-declared): ALL-UPF share differs across types more than chance. Statistic: chi-square of type x group; null: group labels shuffled across reviewers within activity strata, 2,000 times.
 Per type, report the ALL-UPF share against its EXPECTED share given its members' activity strata (so busy-reviewer types are not mistaken for UPF types).
SHOPPER TYPES RESULT (16 Nov; upf/notebooks/shopper_types.py, shopper_types_plot.py; data/processed/shopper_types.txt; soj/shopper_types*.csv*; upf/figures/shopper_types.png)
 58,391 reviewers (ALL-UPF 26,812) with >= 5 non-food reviews; 634 sub-categories; 1.52M reviews. kNN (k=10) cosine network 464,468 links; Louvain 45 types, modularity .704.
 T1 SUPPORTED: chi-square type x group 836 vs null mean 46 (95th pct 64), p = .0005: shopper types differ strongly in how ultra-processed their grocery reviewing is.
 ALL-UPF share minus expected-from-activity (overall ~46%): collectors (action figures, fan shop; 1,092) +11.4 pts; gamers (consoles; 4,555) +9.7; party & novelty gifts +7.1;
  little kids' toys +6.0; toy builders & crafters (6,451) +5.8; sports fans with dogs +4.6; small-pet keepers +4.1 ... baby gear +0.8; mobility/medical +0.6;
  outdoors (hunting, fishing; 4,721) -5.5; grooming/oral/vision -5.8; fitness & oral care -5.9; wellness & supplements -7.7; heart health & Whole Foods -10.2;
  sports nutrition (1,918) -11.9; natural & organic women's health (305) -19.7.
 READING: play and fandom go with ultra-processed groceries; health maintenance, fitness and natural products go with less processed groceries. Baby gear and medical supplies are neutral.
 CAVEATS: exploratory beyond T1; names are our reading; some Amazon sub-category labels are promotions (e.g. 'MasterCard Subscribe & Save'), left in as data;
  only the two extreme groups (the 'between' group is not cached); reviews not purchases; Louvain types depend on k and resolution (not yet checked).
SHOPPER TYPES STABILITY CHECK (16 Nov; user: 'why >= 5 non-food reviews? seems trivial'; 'try different cut-offs') -- written BEFORE running
 The settings were judgement calls: minimum non-food reviews 5, neighbours k = 10, Louvain resolution 1.0. Re-run with: minimum 3, 10, 20 (k 10, res 1); k 5 and 20 (min 5); resolution 0.5 and 2 (min 5, k 10).
 Per setting: T1 chi-square vs 500 within-strata shuffles; for the baseline types collectors, gamers, toy builders (+) and sports nutrition, wellness, outdoors (-), the type in the new run
  that holds most of their members and its ALL-UPF share minus expected; Spearman (over reviewers in both runs) of 'my type's share minus expected' between baseline and new run.
 Pattern HOLDS if, in every setting: T1 p < .01; all six anchor types keep their sign; Spearman >= .5.
STABILITY RESULT (16 Nov; upf/notebooks/shopper_stability.py; data/processed/shopper_stability.txt; soj/shopper_stability.csv): PATTERN HOLDS IN ALL 8 SETTINGS.
 Every run: T1 p = .002 (smallest possible with 500 shuffles); Spearman vs baseline .66-.81; all six anchors keep their sign.
 Collectors +8.5 to +13.6 pts; gamers +5.9 to +13.1; toy builders +2.8 to +7.0 (weakest); sports nutrition -7.1 to -14.3; wellness -5.3 to -12.4; outdoors -0.8 to -7.1 (near zero at minimum 20 reviews).
 Types found: 21 (resolution .5) to 85 (resolution 2); at resolution .5 the three minus-anchors merge into one type (-7.1).
 DISCLAIMER for paper/figure: 'We tried minimum 3, 5, 10 and 20 non-food reviews, 5, 10 and 20 neighbours and Louvain resolution 0.5, 1 and 2; the same types lean the same way in all eight runs.'
 Figure upf/figures/shopper_types.png footnote updated with this.
- 16 Nov: SHOPPER MIX, GROCERIES INCLUDED (descriptive; upf/notebooks/shopper_mix_full.py -> upf/figures/shopper_mix_full.png, soj/shopper_mix_full.csv). User: types looked 'strictly categorised'.
  Each type's reviews split into UPF groceries, less processed groceries, household supplies, health/vitamins/care, pets, toys & games, video games, sports & outdoors, baby, other.
  Types are NOT exclusive: the defining category is 18-32% of a type's reviews (collectors' toys 27%, gamers' video games 18%, outdoors' sports 32%); every type spends 9-17% on
  household supplies and 20%+ on health/vitamins/care. The health share is what grows down the ranking (collectors 20% -> sports nutrition 48%, heart health 50%).
  UPF share of the type's groceries: collectors 69%, gamers 68%, party 68%, toy builders 65% ... wellness 54%, sports nutrition 51%, heart health 50%, natural & organic 45%.
  Also kNN link mix (shopper_network_view.py first run): 64-81% of each type's similarity links stay inside the type. Network drawing of reviewers set aside by the user (unclear value).
- 16 Nov: WHICH UPF DO THE TYPES REVIEW? (descriptive; reviewer_pairs x products). Average UPF share of grocery reviews over all 58,391 typed reviewers: 60.5%.
  Fitness & oral care 57% (near average, not high): ordinary staples plus diet items (instant oatmeal, stevia drops, Cheerios, Crystal Light; over-represented NOVA-4 categories multigrain bread 1.9x, peanut butter 1.7x, ice cream 1.5x).
  Sports nutrition 51%: its UPF is 'health-coded': protein bars 3.7x over-represented, sweeteners 2.1x, plant-based milks 1.8x, meat analogues 1.8x (RXBAR, KIND, Lakanto, SweetLeaf, Nutpods).
  Collectors 69%: crisps 1.8x, beef jerky 1.8x, stews 1.6x, ready meals 1.6x, sweetened drinks 1.5x.
  Protein powder and creatine are sold under Health & Household (Sports Nutrition), not Grocery, so they are NOT in the grocery match or NOVA at all.
- 16 Nov: WHO ARE OUR REVIEWERS? (selection caveat for the paper). All Amazon grocery reviews: 7,034,393 reviewers, 14,318,520 reviews; mean 2.04, median 1; 65.6% wrote exactly one.
  >= 3 reviews: 17.2% of reviewers but 50.9% of reviews; >= 10: 2.0% of reviewers, 18.6% of reviews. Our 141,977 (>= 3 MATCHED grocery reviews) are 2.0% of grocery reviewers;
  their total grocery reviews: median 11, mean 15.8. Shopper types add >= 5 non-food reviews (collectors: median 16). All shopper results describe heavy reviewers, not typical shoppers.
- 16 Nov: SHOPPER TYPE MAP (descriptive; upf/notebooks/shopper_type_map.py -> upf/figures/shopper_type_map.png; kNN edges saved soj/shopper_knn_edges.csv.gz, 583,910 links).
  38 types with >= 300 members as bubbles, colour = lean (diverging, -20..+20 pts), lines = >= 300 between-type links, layout by link strength relative to size.
  76% of similarity links stay inside a type. Strongest between-type links: toy builders - baby gear 5,973; toy builders - gamers 2,379; toy builders - outdoors 2,309; outdoors - gamers 2,041;
  outdoors - fitness & oral care 1,773; fitness & oral care - sports nutrition 1,538. Reading: play/family types (orange) on one side, body-care types (blue) on the other,
  outdoors and pets+supplements in the middle as bridges; natural & organic and heart health are small and peripheral.
- 16 Nov: COMMUNITY PROFILES, UNNAMED (user: pool the communities and show what members have in common without labels). upf/notebooks/community_profiles.py -> upf/figures/community_profiles.png, soj/community_profiles.csv.
  15 largest communities C1-C15 (by size) x sub-categories; cell = share of members who reviewed >= 1 product there.
  Common base in every community: Household Supplies 68-84%, Health Care 59-80%, Vitamins 49-80%, Dogs 36-67%.
  Most communities are ONE shared interest on top of that base: C5 cats 99%, C12 stationery 99%, C13 birds 98%, C14 puzzles 100%, C10 vision 96%, C11 wellness 96%, C15 fan shop 94%,
  C9 diet & sports nutrition 88%, C8 fish 86%, C3 hunting & fishing 81%. Broader ones: C1 (toys across building, dolls, preschool 75%, games 45%), C2 (baby feeding 65%, preschool 67%, diapering 48%),
  C4 (video games 55% / 48%), C6 (diffuse: oral care 44%, exercise 33%).
  METHOD NOTE: TF-IDF down-weights common categories, so a shared less-common category dominates cosine similarity; communities therefore crystallise around one distinctive interest.
- 16 Nov: CONSISTENCY CHECK (descriptive). Share of people who are all-UPF, games & figures types (gamers + collectors) vs health & fitness types (sports nutrition, wellness, heart health, natural & organic) vs everyone else:
  by quartile of grocery share of a person's reviews (edges .12/.20/.30): games & figures 53.3/56.5/61.0/54.3% vs everyone else 46.4/45.9/46.8/43.6% vs health & fitness 32.0/34.0/40.0/31.9%.
  by grocery-review count (3 / 4 / 5-9 / 10+): games & figures 63.3/50.6/51.5/31.8 vs everyone else 54.7/40.1/39.1/15.9 vs health & fitness 45.7/31.4/24.3/6.9.
  Reading: the gap holds in every band of grocery share and every activity level (games & figures +7 to +16 pts above everyone else; health & fitness 6 to 15 pts below).
- 16 Nov: PRODUCT LEAN, PRE-DECLARED (written before computing anything; user asked for the 'one row per food category' strip chart).
  Question: which grocery products are reviewed mostly by hobby-minded vs health-minded shoppers, and do ultra-processed products sit on the hobby side WITHIN the same food category?
  Reviewers: the 58,391 shopper-type reviewers (>= 3 matched grocery reviews, >= 5 non-food reviews). Groceries NOT used for the lean (it is the outcome side).
  HEALTH-CODED set (narrow core): H&H > Vitamins, Minerals & Supplements; H&H > Diet & Sports Nutrition; H&H > Wellness & Relaxation; Sports & Outdoors > Exercise & Fitness.
  HOBBY set (narrow core): Toys & Games > Toy Figures & Playsets, Collectible Toys, Games & Accessories, Puzzles, Building Toys, Novelty & Gag Toys; all Video Games; Sports & Outdoors > Fan Shop, Memorabilia Display & Storage.
   (Kids' toys - preschool, dolls, plush, pretend play, outdoor play, learning - are left out: those mark parents, not hobbies.)
  Reviewer lean = (health-coded reviews - hobby reviews) / all non-food reviews; -1 = all hobby, +1 = all health-coded. 'Health-coded' = sold as healthy, NOT shown to be healthy.
  Product lean = mean lean of its reviewers; products with >= 20 of our reviewers. Rows = Amazon grocery category (level 2 > level 3) with >= 15 such products.
  Null: shuffle reviewer leans within activity strata (3 / 4 / 5-9 / 10+ matched grocery reviews), 1,000 shuffles; per-product two-sided p; products flagged at Benjamini-Hochberg FDR 5%.
  L1 (pre-declared test): within each Amazon category, mean lean of NOVA 4 products minus NOVA 1-3 products, averaged over categories weighted by the smaller side; same shuffle null.
   Prediction: negative (UPF products lean hobby). Categories need >= 3 products on each side.
  Robustness: WIDE sets (health adds Oral Care and Vision; hobby adds all Toys & Games). Result holds if L1 keeps its sign with p < .05 in both.
PRODUCT LEAN RESULT (16 Nov; upf/notebooks/product_lean.py; data/processed/product_lean.txt; soj/product_lean.csv.gz): L1 SUPPORTED, holds in both sets.
 2,373 products with >= 20 of our reviewers (1,347 UPF). L1 narrow -0.071 (null -0.005, sd .002), p = .001 (smallest possible); wide -0.095, p = .001.
 588 products lean beyond chance at FDR 5% (256 hobby side, 332 health side). Reviewers: 19% have lean exactly 0 (no hobby or health-coded reviews); 5.5% >= +.5, 1.6% <= -.5.
 Within category, UPF products sit on the hobby side of less processed ones in nearly every Amazon category (drink mixes, cookies, cereals, canned foods, sauces, soups, snack foods, spices);
 exceptions: plant-based milk and milk & cream, where the UPF products lean health (health-coded UPF again).
- 16 Nov: PRODUCT BINS (descriptive companion to PRODUCT LEAN; user found the lean axis too abstract). upf/notebooks/product_bins_plot.py -> upf/figures/product_bins.png, soj/product_bins.csv.
  Reviewers in 5 groups by rank of lean (narrow sets): hobby side and health side each split at their median, 'neither' = lean exactly 0. Sizes 13 / 13 / 19 / 26 / 29%.
  Per food category x processing: share of its reviewers (unique people, all matched products) in each group; rows ranked by mean group.
  Within every category except milk & plant milk, the UPF bar has more strong-hobby and fewer strong-health reviewers than the less processed bar
  (strong health: candy 23 vs 42%, cookies 23 vs 40%, jerky 24 vs 40%, crackers 23 vs 39%, nut butters 32 vs 45%; milk & plant milk 36 vs 33%, the health-coded exception).
  CAVEAT: category bars count people who reviewed that category, so heavy reviewers (in many categories) weigh more than in the 'all reviewers' bar; compare UPF vs less processed WITHIN a row.
  The activity-adjusted test is L1 (PRODUCT LEAN), not this chart.
  DIVERGING VERSION (16 Nov, user: hard to see at a glance): upf/figures/product_bins_diverging.png (same script). Centre = middle of 'neither'; hobby groups left, health right.
  Reference bar = 'average food bar' (all category bars pooled: 12 / 13 / 18 / 27 / 30%), so it has the same weighting as the rows.
  Why the bars lean blue: (1) groups are unequal by construction (hobby side 26% of reviewers, health side 55%: health-coded products are common, vitamins reviewed by 58%);
  (2) heavier grocery reviewers lean health (strong health 28% at 3 grocery reviews vs 37% at 10+) and appear in more category bars.
  So the absolute amount of blue says nothing about grocery reviewers being healthy; only the shift between the two bars of a row is the finding.
- 16 Nov: ONE CURVE, PRE-DECLARED (written before computing; user asked for the health-share curve proposed earlier).
  Question: if health-coded products make up a bigger part of someone's non-food reviews, are they less likely to have only ultra-processed grocery reviews?
  Reviewers: the 58,391 shopper-type reviewers (ALL-UPF 26,812 vs MOSTLY-NOT 31,579; 'between' reviewers are not in this set). Groceries not used on the x-axis.
  x = health-coded share of non-food reviews (narrow set as PRODUCT LEAN). Bins: 'none' (share 0) + deciles of the positive shares. Second panel: hobby share, same binning.
  y = % ALL-UPF in the bin, with 95% binomial interval; expected = mean of the activity-stratum rate (3 / 4 / 5-9 / 10+), as in SHOPPER TYPES.
  C1 (test): reviewer-level slope of (ALL-UPF - expected) on health share; null = health shares shuffled within activity strata, 2,000 shuffles. Prediction: negative.
  C2 (test): same for hobby share. Prediction: positive. Holm over C1, C2.
  Robustness: WIDE sets; and C1 among reviewers with no hobby reviews only (the two shares compete for the same reviews, so each curve partly mirrors the other).
ONE CURVE RESULT (16 Nov; upf/notebooks/one_curve.py; data/processed/one_curve.txt; soj/one_curve.csv; upf/figures/one_curve.png): C1 AND C2 SUPPORTED.
 C1 health share: -5.0 pts ALL-UPF per 10 pts of share, p = .0005 (Holm .001); wide -4.8; among reviewers with no hobby reviews -4.2 (all p = .0005).
 C2 hobby share: +4.5 pts per 10 pts, p = .0005 (Holm .0005); wide +3.6.
 Curve (observed vs expected ~45%): health none 57% -> top tenth (44-100% health-coded) 26%; hobby none 42%, lowest tenth 36%, top tenth (33-100% hobby) 63%.
 Expected barely moves (45-47%), so activity does not explain the curves. Dip at the lowest hobby tenth (0.1-3.3% hobby: 1 hobby review among many) is unexplained; probably very heavy reviewers.
- 16 Nov: story page v7. Removed 'Purity travels, pleasure stays home' (user: the purity words just mirror vitamins vs toys, the shopper-type split again; pleasantness elsewhere confusing).
  H8 null kept as one line and H9 (+0.011 warmer reviews) added as one line under 'What did not hold up' (gift/toy reviews are warm anyway). Pleasantness validation callout moved up to 'Two vocabularies'.
  New section 'Hobbies and health': ONE CURVE chart (log x, both panels), then 'Who reviews the candy?' (diverging bars) as a subsection. one_curve.png now also on a log x-axis.
- 16 Nov: OPEN, HAND-LABELLING ACCURACY CHECK (planned by the user for Wed 18 Nov, after checking with the TA; nothing built yet).
  Trigger: concordance snippets for the dial words showed lexicon words used across both sides (e.g. a NOVA-4 listing 'certified organic, non GMO, vegan';
  'pure butter' on the NOVA-4 side), raising (a) whether words are used in the sense the lexicon scores and (b) whether OFF NOVA labels are right.
  Candidate checks (pre-declare the pass rule here BEFORE labelling; blind to side/label; offline labelling page like the emotion ones, gitignored):
   (1) WORD-IN-CONTEXT: ~25 dial words x ~10 random snippets per side (~500), label 'used in the sense the lexicon scores' yes/no; compare error rates by side.
   (2) NOVA LABEL: 50-100 random matched products, hand-classify NOVA from the OFF ingredient list, report agreement with the OFF label.
  Concordance tooltips for the dials are ON HOLD until then: snippets drafted (1 random per word and side, brand-named ones filtered out, one dropped by hand;
  scratchpad kwic.json, not saved in the project). If shown later, draw them from the labelled sample and say they are random.
- 16 Nov: story page v23 (after review comments, v8-v22): facts-card hand-check note removed; 'Two vocabularies' intro paragraph removed; VAD paragraph covers all three
  dimensions + interactive 'three dials' (Valence / Arousal / Dominance tabs, words at rounded lexicon scores, side averages; zoom toggle removed); box 'Why a fixed word list?'
  (static lexicon chosen on purpose; only valence validated by stars); dumbbell chart and the whole 'Do shoppers feel it?' section removed (user: thin value);
  its results kept as two lines under 'What did not hold up' (equal review pleasantness 0.207 vs 0.207; 'treat' artefact). Hover tooltips moved to the page's own tooltip.
- 18 Nov: NETWORK STRUCTURES, EXPLORATORY + CORRECTED H4 (user: most reviewers review few products, so check how connected the co-review network really is; try other structures).
  Reason for the correction: Week 4 says the backbone is for drawing, not data; H4 assortativity and the product-community Louvain ran on the disparity backbone (alpha = .01).
  CORRECTED H4 (pre-declared now, before computing): NOVA assortativity (NOVA 4 vs 1-3) on the FULL weighted grocery co-review projection (reviewers with 2-50 matched reviews,
   weight = shared reviewers), null = NOVA labels shuffled within Open Food Facts category (as the original H4), 1,000 shuffles, one-sided. This replaces the backbone number in the paper;
   the backbone stays only for the drawing.
  EXPLORATORY comparison (descriptive, no new claims): S1 full projection; S2 links with >= 2 shared reviewers; S3 kNN product graph (cosine on reviewer sets, k = 10, products with >= 5 reviewers);
   S4 the old disparity backbone; S5 category network (Amazon grocery sub-category x processing level, links = shared reviewers relative to expectation).
   For each: nodes, links, share of products connected, giant component, clustering, Louvain modularity, NOVA assortativity vs within-category null.
NETWORK STRUCTURES RESULT (18 Nov; upf/notebooks/network_structures.py; data/processed/network_structures.txt; soj/network_structures.csv, category_network.csv; figure upf/figures/network_structures.png):
 CONNECTIVITY: 79.5% of grocery reviewers wrote exactly 1 matched review (52.7% of reviews) and create no links. Projection (2-50 reviewers): 63,841 products, 2.85M links, giant component ~100%,
  but 92.5% of links rest on ONE shared reviewer; requiring >= 2 shared reviewers keeps 212,774 links and only 21,019 products (33%), giant 19,859.
 CORRECTED H4 (full weighted projection): NOVA assortativity +0.105 vs within-category null +0.028 (sd .001), p = .001 (1,000 shuffles) -> SUPPORTED, but about a third of the
  backbone value (+0.28 vs +0.09) that the page and earlier notes report. Unweighted +0.093 vs +0.024.
 Structures (weighted assortativity, observed vs null; modularity of Louvain):
  S2 >= 2 shared reviewers +0.176 vs +0.055; modularity .43, 13 communities >= 20 products, clustering .25.
  S3 kNN cosine k=10 (products >= 5 reviewers, 32,016 = 50%) +0.158 vs +0.039; modularity .41, 34 communities >= 20.
  S4 disparity backbone +0.281 vs +0.090; modularity .53; only 6% of products. The stricter the link rule, the higher the assortativity: strong ties are more same-kind.
 S5 CATEGORY NETWORK (123 nodes = Amazon grocery sub-category x UPF/less, link = reviewers of both relative to chance, 'lift'): UPF-UPF lift 2.71, less-less 2.82, UPF-less 2.34
  (different sub-categories); same sub-category UPF-less 6.12. Louvain (lift > 1) finds 2 weak communities (modularity .09) that split FRESH / CHILLED / FROZEN (deli, cheese,
  meat, bread, yogurt, ice cream, fresh produce, pizza) from SHELF-STABLE PANTRY (candy, cereal, cookies, canned, snacks, spices, pasta, tea, nut butters), each holding both
  the UPF and less-processed versions. READING: at category level shoppers sort by how food is stored and delivered, not by processing level.
 TO DO (not yet run): the category / brand shuffle bars on the story page are backbone-based; rerun them on the full projection before the paper uses them.
- 18 Nov: IS THERE A REAL PRODUCT COMMUNITY? (exploratory; user: '2 shared reviewers sounds like coincidence; interesting would be most repeat reviewers reviewing the same few foods').
  OVERLAP: product pairs where >= 50% of the smaller product's repeat reviewers (2-50 matched reviews) also reviewed the other: 246 pairs / 460 products with >= 3 shared;
   62 pairs / 113 products with >= 5 shared; 5 pairs with >= 10. Same processing level 90%+, and they are PRODUCT LINES: same brand 52-60% by name, and the 'different brand' ones
   checked by hand are the same brand spelled differently (Cypress Grove goat cheeses, Erin Baker's breakfast cookies, Mrs. Wages salsa mixes, Jolly Rancher gelatin).
  CONCENTRATION (50,938 reviewers with 5-50 matched reviews, median 7; null = products shuffled across all reviews, 5 shuffles): top brand 24.9% of a reviewer's reviews vs 20.4%;
   top Amazon sub-category 33.3% vs 25.6%; distinct brands per review 86.8% vs 93.4%; ALL reviews ultra-processed 14.0% vs 7.9%; NO ultra-processed 1.0% vs 0.1%.
   (brand strings normalised to 8 letters; missing brands pooled, which inflates both sides a little.)
  READING: no 'overwhelming majority reviews the same few foods'. Repeat reviewers spread their reviews; the only tight product clusters are flavours of one product line.
   What sorts people beyond chance is processing level (all-UPF 1.8x chance) more than brand (1.2x) or sub-category (1.3x). So the network is better used as a TEST of sorting
   (corrected H4, person-level all-UPF vs mostly-not) than as a source of product communities; drop product-community detection as a headline.
- 18 Nov: CATEGORY CO-REVIEW NETWORK (exploratory; user: 'of those who reviewed food category X, what other clusters of Amazon categories do they also review?').
  upf/notebooks/category_network.py -> data/processed/category_network.txt, soj/category_nodes.csv, category_links.csv, category_food_nonfood_rel.csv; figure category_network_plot.py -> upf/figures/category_clusters.png.
  141,977 reviewers (>= 3 matched grocery reviews); nodes = Amazon grocery sub-categories (81) and non-food sub-categories (68), each >= 500 reviewers; promo pseudo-categories removed.
  A (all links, lift): trivial split food vs non-food (everyone here reviews food). B (food x non-food only): cell = reviewers of both / expected from reviewers with the same number of
   non-food categories (strata 0/1-2/3-5/6-10/11-20/21-40/41+). (A first null that shuffled non-food categories across reviewers was biased: duplicates collapsed, inflating popular
   categories like Household Supplies; replaced.) 141 pairs > 1.25x, 106 < 0.8x. Bipartite Louvain (links > 1.15x, >= 50 shared): 6 clusters, modularity .49, adjusted Rand over seeds .69.
  Clusters (our names): YOUNG FAMILIES (chilled & frozen: ice cream, yogurt, milk, cheese, meats, ready meals, pizza; food 71% UPF) with baby feeding/care/nursery, toddler toys, party,
   Switch (up to 1.6x); PANTRY & HOME CARE (cooking & baking, canned, sauces, soups, spices, tea; 64% UPF) with mobility aids, bathroom safety, cold & flu, hunting & fishing, birds (weak, ~1.1-1.3x);
   HEALTH & FITNESS (nut butters, plant milk, oats, dried fruit, eggs, beans, granola, organic; 51% UPF) with diet & sports nutrition (1.3-1.5x), vitamins, exercise, wellness;
   TREATS & GAMING (candy, cereal bars, chocolate, toaster pastries, cold cereal, syrups; 95% UPF) with video games, collectibles, fan shop, novelty toys (up to 1.5x).
  READING: at category level the network IS informative: four lifestyle clusters spanning food and non-food, and their food's UPF share ranges 51% (health & fitness) to 95% (treats & gaming).
   Effects are modest (1.2-1.6x), clusters only moderately stable; describe as exploratory. Fits the shopper-type and hobbies/health results from the other direction (food first).
- 18 Nov: 2018 CO-PURCHASE NETWORK (user OK to download; upf/data/raw/amazon/2018/meta_Grocery_and_Gourmet_Food.json.gz, 110 MB, gzip OK, Amazon Review Data 2018,
  Ni, Li & McAuley EMNLP 2019, research use). 283,354 grocery products; also_buy for 29%, also_view for 42%.
  Linking: 2018 ASINs mapped to 2023 parent_asin via the 2023 reviews' (asin, parent_asin) pairs (soj/asin_to_parent_2023.csv.gz, 240,059 variants). Coverage of our 75,933 matched products:
  37% present in 2018; also_buy links between matched products 78,781 (undirected) on 18,415 products (24%), 17% listed in both directions; also_view 55,278 links, 22,703 products.
  PRE-DECLARED (before building): H4-CP NOVA assortativity on the undirected also_buy network among matched products (weight 2 if listed both ways, else 1) is above a null that shuffles
   NOVA labels within Open Food Facts category (1,000 shuffles), one-sided. Robustness (pre-set): (a) drop same-brand links; (b) null shuffled within brand; (c) also_view network.
  EXPLORATORY: Louvain communities on the also_buy network (no backbone: it is already sparse); describe each by Amazon sub-categories, brands and UPF share; compare with the review network.
CO-PURCHASE RESULT (18 Nov; upf/notebooks/copurchase_network.py, copurchase_describe.py; data/processed/copurchase_network.txt; soj/copurchase_*.csv*):
 30,842 matched products found in 2018; also_buy network 18,415 products, 78,781 links (same brand 17%, same OFF category 20%, same processing level 76%; products 71% UPF).
 H4-CP SUPPORTED: NOVA assortativity +0.425 vs within-category null +0.118 (sd .009), p = .001.
 Robustness all hold (p = .001): without same-brand links +0.350 vs +0.103; null shuffled within brand +0.425 vs +0.314 (brand explains part, not all); also_view +0.567 vs +0.163.
 Compare: review network (full) +0.105 vs +0.028. Co-purchase links are far more processing-sorted than review overlaps.
 Communities (exploratory): giant component 17,464 products (95%); Louvain 60 communities, modularity .698; stability adjusted Rand .56 over 5 seeds (moderate).
 Read by TF-IDF of titles (brand words removed) and UPF vs expected from the community's OFF category mix: they look like SHOPPING MISSIONS, e.g.
  C2 whole-food baking & health (ghee, hulled, bran, crispbread, carob; Bob's Red Mill) UPF 38% vs 57% expected (-19 pts); C5 organic/natural (muesli, Edensoy, Amy's) 55% vs 66% (-11);
  C18 fish & Latin pantry (herring, mole, achiote; Goya) 30% vs 44% (-13); C7 Asian/global cooking (Patak's, mirin, tempura) 49% vs 56% (-8);
  C1 chilled & frozen convenience (refrigerated, battered, Steamfresh) 79% vs 71% (+7); C3 boxed sides & convenience (Suddenly Salad, Fluff, chowder) 77% vs 65% (+12);
  C16 barbecue (Kansas City, Stubb's, breading) 83% vs 67% (+17); C4 seasonal candy (Valentine, Easter, Halloween) 98% vs 90%; C19 drink mixes (Crystal Light) 95% vs 87%;
  C6 gluten-free & allergy (Glutino, Passover) 76% vs 71%; C13 desserts (Jell-O pudding) 83% vs 80%; C14 coffee & cocktails at home 87% vs 83%.
 READING: co-purchase gives a sensible community structure: missions (scratch baking, organic, world cooking, BBQ, convenience, holiday candy), and the mission shifts processing
  level beyond the food types it contains (-19 to +17 pts). 'UPF vs expected' is descriptive (no test yet). Caveats: 2018 snapshot; 24% of matched products have a link;
  'also bought' is Amazon's own aggregate (recommendation lists), not raw baskets.
 FIGURE: upf/notebooks/copurchase_plot.py -> upf/figures/copurchase_missions.png (community map of the 20 largest communities + observed vs expected UPF per community).
 CIRCULARITY CHECK (18 Nov, exploratory; user: 'isn't also-bought circular?'). NOVA is not used to build links or communities (Amazon computes also-bought from purchases; Louvain
  uses links only), so not circular by construction. The real risk is SIMILARITY: also-bought includes substitutes (same kind of product), and similar products share processing level.
  Of the links: same OFF category 20%, same Amazon sub-category 40%, same sub-sub-category 25%, same brand 17%.
  Finer null (shuffle within Amazon sub-sub-category): +0.425 vs +0.134, p = .002 (500 shuffles).
  CROSS links only (different OFF category AND different Amazon sub-category AND different brand: complements, not substitutes; 37,833 links): +0.252 vs +0.058 (within OFF category)
   and vs +0.052 (within sub-sub-category), p = .002. Sorting by processing level survives among products that are NOT alike: baskets, not just look-alikes.
  Remaining caveat: also-bought is shaped partly by Amazon's own recommendations (feedback loop); cannot be separated with this data.
- 18 Nov: MARKETING WORD NETWORK (user: do the words form an interesting network?). Pre-declared before computing:
  Listings: the category-balanced sample of the word plot (marketing_wordplot.py: 25 OFF categories, equal NOVA 4 / NOVA 1-3 per category). Words: the word-plot vocabulary
  (>= 30 listings) minus Open Food Facts ingredient words (as for the VAD scores), so communities are about how food is sold, not what it is.
  SPLIT-HALF: listings split at random into halves A and B. Word lean = log-odds z (NOVA 4 vs 1-3, Dirichlet prior) from half A; network from half B:
   link = two words used in the same listing; weight = positive PMI; kept if >= 15 co-occurring listings and PMI > 0.
  W1 (test): word-lean assortativity (Pearson correlation of A-half z across B-half links, weighted) > null from shuffling z across words (1,000), one-sided.
  Exploratory: Louvain communities on the B-half network (stability over seeds); described by top words, mean lean, share of UPF- / less-processed-leaning words.
WORD NETWORK RESULT (18 Nov; upf/notebooks/word_network.py; data/processed/word_network.txt; soj/word_nodes.csv, word_edges.csv.gz):
 20,698 balanced listings; 1,976 words (218 ingredient words removed). Half-B network: 16,265 PPMI links among 1,131 words.
 W1 SUPPORTED: word-lean assortativity +0.293 vs null -0.003 (sd .010), p = .001 (split-half, so not circular): words that lean the same way are used together.
 Louvain: 18 communities, modularity .53; stability adjusted Rand .53 (min .40) over 5 seeds (moderate). Our reading of the larger ones (mean lean, + = ultra-processed):
  W1 432 cooking & use (favorite, make, creamy, quick, minutes, versatile) +0.36;  W2 220 nutrition panel + pleasure & convenience (serving, calories, grams, convenient, fun,
  irresistible, school, satisfying) +1.23;  W3 137 certification & sourcing (non-GMO, certified, sourced, facility, organically, practices) -0.95;  W4 53 brand values (believe, proud,
  customers, BPA, recyclable, additives, allergens) -1.09;  W7 41 heritage & freshness (generations, picked, freshly, peak, preservatives) -1.07;  W9 34 free-from claims (USDA, hormones,
  antibiotics, nitrates, bleached, bromated, pesticides, rBST) -2.57;  W12 22 anti-GMO / no chemicals -2.03;  W8 40 company history (founded, decades) ~0.
  Boilerplate communities: W5 package specs/dimensions/Spanish, W10 Amazon/seller disclaimer text ('actual', 'consult', 'professional'), W6 retailer pitch (pantries, freezers, standards).
 READING: the purity side is several distinct vocabularies (certification, free-from, heritage/freshness, brand values), the ultra-processed side mostly one (pleasure + convenience
  + nutrition-panel numbers) plus generic cooking language. Caveat: some communities are seller templates, not language choices.
 FIGURE: upf/notebooks/word_network_plot.py -> upf/figures/word_network.png (7 main vocabularies, top 13 words each, groups ordered by mean lean; boilerplate groups left out).
 NOVA 1-3 CHECK (18 Nov, exploratory; user hypothesis: less-processed side splits into several vocabularies because it pools NOVA 1, 2 and 3). NOT SUPPORTED.
  Balanced sample: NOVA 1 13%, NOVA 2 0.5%, NOVA 3 36%, NOVA 4 50% (the 'less processed' side is mostly NOVA 3: cheese, cured meat, bread, canned).
  Listings using >= 2 words of a purity vocabulary draw NOVA 1 / 2 / 3 in about their base proportions (NOVA 1 at 0.83-1.16x, NOVA 3 at 0.94-1.06x of the less-processed mix);
  no vocabulary belongs to one NOVA group. And NOVA 4 listings use every purity vocabulary too (34-43% of users vs 50% base).
  READING: the several clusters are distinct claim systems (free-from lists, Non-GMO/organic certification, heritage storytelling, brand values) that sellers adopt as packages,
  across NOVA groups; the pleasure register is one generic style. Purity talk is a strategy, also used by ultra-processed products (health halo).
- 18 Nov: NEGATION CHECK on marketing valence (exploratory; user: 'no pesticides'). Balanced word-plot sample; VADER negator list (Hutto & Gilbert 2014; no, not, never, without ...),
  scope = next 3 words or punctuation. Negated share of scored words: 1.85% (UPF) vs 1.88% (less processed); 37% vs 39% of listings have one.
  Most negated words on BOTH sides are positive ones in 'no artificial flavors or colors' (flavor +0.77, colors +0.75, ingredient +0.58), then cholesterol, antibiotics, nitrate.
  Within-category valence gap (sample): +0.0110 as published; +0.0087 with negated words dropped; +0.0070 with their valence flipped. Gap shrinks 20-35%, stays positive (not yet
  permutation-tested). Flipping is semantically wrong for 'no artificial flavors' (flavor is not bad), so DROPPING is the fairer correction. Not handled: '-free' compounds
  (gluten-free, preservative-free; 'free' scores positive). TO DO before the paper: rerun A1-H1 within-category test with negated words dropped and '-free' compounds handled.
- 18 Nov: CLAIM SYSTEMS (exploratory; upf/notebooks/claim_systems.py -> upf/figures/claim_systems.png, soj/claim_systems.csv, data/processed/claim_systems.txt).
  Balanced sample (20,698). Free-from claims detected by NEGATION (VADER negators, 3-word scope; 'X-free'; 'free of/from X'), other systems = word-network communities (>= 2 words, not negated).
  Share of NOVA 1 / NOVA 3 / NOVA 4 listings: free-from 54 / 54 / 47%; certification & sourcing 41 / 33 / 22%; heritage & freshness 6 / 7 / 4%; brand values 10 / 9 / 7%;
   pleasure, convenience & nutrition panel 58 / 47 / 54% (this community mixes panel numbers and pleasure words, so it is not a clean UPF marker).
  Free-from targets: gluten 3,093 listings, preservatives 1,581, flavors 1,429, MSG 942, sugar 903, colors 724, high(-fructose) 665, GMO 523, cholesterol, trans, hydrogenated, dairy, guilt(-free).
  Combinations: free-from alone 12% (48% UPF); free-from + certification (+ pleasure) 16% (35-40% UPF); pleasure alone 14% (63% UPF); none 26% (53% UPF).
  READING: free-from is a general register used by ultra-processed products almost as much (gluten-free, no preservatives, no artificial flavors, sugar-free, guilt-free);
   CERTIFICATION is the claim system that marks less processed food. Revises the word-network reading ('several purity dialects'): only some are purity-specific.
- 18 Nov: MATCHED-PRODUCT INGREDIENT NETWORK (exploratory; user: 'pick the ingredients out of the lists of the NOVA-matched foods, build a network, run community detection').
  Differs from the 15 Nov ingredient network: only the 58,051 Amazon-matched barcodes, and ingredients PARSED FROM THE LIST TEXT (not Open Food Facts tags, so no parent-tag inflation).
  upf/notebooks/matched_ingredients_extract.py -> soj/matched_ingredients_raw.csv.gz; matched_ingredient_parse.py -> soj/matched_ingredients_long.csv.gz;
  matched_ingredient_network.py -> data/processed/matched_ingredient_network.txt, soj/matched_ingredient_{nodes,communities}.csv, _edges.csv.gz; figure matched_ingredient_network_plot.py -> upf/figures/matched_ingredient_network.png.
  PARSE: brackets = sub-ingredients; compound 'X (a, b, c)' replaced by its leaves; single-item brackets kept as X unless X is a function word ('preservative (sodium benzoate)');
   stops at allergen/facility statements ('contains: milk'); strips %, footnote marks, organic/non-GMO/pure, purpose phrases; dye and vitamin numbers kept (red 40, vitamin b12); small synonym map; plural merge.
   57,870 products parsed, median 11 ingredients; 34,902 distinct strings, 1,174 in >= 50 products (87% of mentions). Known slips: bare 'corn' from 'sunflower, corn and/or canola oil'; 'durum (wheat) semolina' -> 'durum';
   sea salt vs salt and cane sugar vs sugar kept apart on purpose (label choices). Not hand-validated yet.
  NETWORK: 1,174 nodes, 250,438 co-occurrence links (density .36) -> disparity backbone (alpha .01) 19,931 links, giant component 1,166.
  Louvain (weighted, 20 seeds): modularity .194 (range .188-.194), stability adjusted Rand .71 (min .52); unweighted .253 vs degree-preserving rewired null .105 (sd .008): structure is real but modest.
  Communities (our names; members' median NOVA-4 share; products assigned to their majority community, NOVA-4 share):
   C0 479 savoury (salt, water, spices, garlic, onion, dairy, meat) .85 / 64%;  C1 259 'clean label' (natural flavors, sea salt, cane sugar, honey, seeds, nuts, whole grains) .82 / 62%;
   C2 190 confectionery & sweet drinks (sugar, corn syrup, cocoa butter, dyes, gum base, sweeteners) 1.00 / 94%;  C3 173 bakery (enriched wheat flour, leavening, dough conditioners) .95 / 81%;
   C4 62 fortification (vitamins, calcium carbonate, BHT: cereals) .94 / 63%;  C5 3 French-language lists (sucre, sel, eau) -- artefact.
  Second level (Louvain inside each community >= 100): the low-UPF pockets are fresh-veg cooking C0.1 (garlic, onion, tomatoes, olive oil, herbs) .58, nuts/honey/baking C1.3 .62, cane sugar & sea salt C1.1 .68,
   whole grains C1.4 .76; at ~1.00: candy & dyes, dye lakes, sweeteners/gum/energy drinks; ~.95: savoury snack seasoning (MSG, yeast extract, disodium inosinate), processed meat (nitrite, erythorbate), dairy & cheese, cakes & mixes.
  READING: ingredients sort into product families (savoury, sweet/confectionery, bakery, fortified cereal, 'clean label'), and processing level differs more WITHIN the savoury and clean-label families than between families.
  CAVEATS: NOVA-4 share of marker ingredients (dyes, sweeteners, modified starch) is ~1 BY DEFINITION (OFF assigns NOVA from them), so their communities restate the rule; informative part = the non-marker families.
   Centrality still tracks frequency. One product per barcode (not per listing). Louvain resolution limit: C0 lumps five families; the second level is descriptive.
  HAND-CHECK OF THE PARSER (18 Nov; user asked). 50 random matched products (seed 2026), raw list read against parsed output by me (Claude), not by the user.
   Before fixes: 625 items, 45 wrong (not an ingredient / two fused / fragment), 6 ingredients missed. Fixed: seed-name -> 'X oil' only inside 'and/or ... oil' or an oil bracket
   ('organic coconut' had become coconut oil); inline 'contains 2% or less of' headers split instead of swallowing the item; text after a bracket kept ('ascorbic acid (vitamin c) and malic acid');
   fragments dropped ('preserved with', 'includes', trailing 'added'); 'x and y' split when both are common ingredients, sharing a word across the 'and'
   ('disodium inosinate and guanylate', 'palm and coconut oil'), with a keep-list of real compounds (natural and artificial flavors, mono and diglycerides, fruit and vegetable juice).
   After: 630 items, 27 wrong (precision 96%), 0 missed found. 18 of the 27 come from broken source text: one OCR-garbled multi-flavour list gives 14, plus typos/missing commas;
   multi-flavour lists also leave variant names as items ('strawberry :', 'cherry -'). Of the 630, 545 are in the network (>= 50 products); network-level errors are rare
   (e.g. 'hydrolyzed corn' from 'hydrolyzed corn, soy and wheat protein'). Bare seed names remain at ~100 products each vs 5,000+ for the oil names.
  REVISED RESULT after the fixes (supersedes the community list above): 57,901 products parsed; 1,153 nodes; backbone 19,965 links; Louvain modularity .194, stability ARI .75 (min .50);
   unweighted .254 vs rewired null .108 (sd .009). Top level: C0 412 savoury (sauces, seasoning, meat, Asian cooking) products 63% NOVA 4; C1 269 'clean label' (cane sugar, sea salt,
   starches, nuts, honey, whole grains, fruit, stevia drinks) 64%; C2 211 grain (enriched flour, bakery, fortified cereal: vitamins joined here) 76%; C3 186 confectionery 94%;
   C4 65 dairy & cheese (now its own community) 67%; C5 3 French-language lists. Second-level lows unchanged: fresh-veg cooking .57, nuts/honey/baking .68, whole grains .75,
   cane sugar & sea salt .77; highs ~1.00 candy, dyes, sweeteners, chocolate & sweet bakery, cakes & mixes. Reading unchanged.
- 18 Nov: CENTRALITY CONTRAST (exploratory, ad hoc script; user: can centrality highlight the certification finding?). Two word co-occurrence networks from the balanced sample,
  one from less processed listings, one from NOVA 4 listings (same vocabulary; links = >= 10 co-occurring listings with PMI > 0; weight = co-occurring listings); PageRank in each; ratio.
  Certification words gain centrality only modestly on the less processed side (mean x1.4); 'certified' etc. are hubs on BOTH sides (kosher / gluten-free certifications are common in UPF copy too).
  Biggest gains on the less processed side: PROCESS words (slowly x9.5, harvested x8.1, ripened x4.3, batches x3.3, soil x5.8), chemicals x6.4, additives x5.0, nutrients x3.7, USDA x3.2.
  Biggest gains on the UPF side: OCCASION / ON-THE-GO words (lunchboxes x9.1, backpacks x7.9, stow x8.1, travel x6.1, office x5.0, night x5.4, adults x5.4, moments x5.3), cheesy x9.3, spoonful x7.0.
  By claim system (mean log2 ratio less/UPF): no-GMO/chemicals +0.97, brand values +0.65, free-from +0.47, certification +0.46, heritage +0.43, cooking +0.09, pleasure/panel -0.85.
  READING: centrality frames it as 'how it was made' (less processed) vs 'when and where you eat it' (ultra-processed); certification is better shown by prevalence than by centrality.
