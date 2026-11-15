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
