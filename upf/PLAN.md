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
