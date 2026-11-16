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
