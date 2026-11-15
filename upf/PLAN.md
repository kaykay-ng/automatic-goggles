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
