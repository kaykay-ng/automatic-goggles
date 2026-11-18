# 02805 final project: food trade, emissions and parliamentary language

Working notes, decisions and results live in `PLAN.md`. This repo holds code and small outputs only; raw data is rebuilt.

## Rebuild order (run from the repo root, Python 3.12+, `pip install -r requirements.txt`)
1. FAOSTAT bulk files into `data/raw/` (public, no key). Each is `https://bulks-faostat.fao.org/production/<name>.zip`;
   unzip each into `data/raw/<name>/`:
   `Emissions_Totals_E_All_Data` (14 MB), `FoodBalanceSheets_E_All_Data` (22 MB),
   `Trade_DetailedTradeMatrix_E_All_Data` (428 MB zip, 2.1 GB csv), `Environment_Emissions_intensities_E_All_Data` (3 MB).
2. `python notebooks/profile_faostat.py`   -> data/processed/{emissions,fbs,trade}_parlamint*.csv
3. `python notebooks/build_trade_networks.py`, `null_and_attributes.py`, `gravity_null.py`, `exporters_vs_emitters.py`,
   `meat_dairy_deep_dive.py`, `food_use_profile.py`
4. ParlaMint-en text (CC BY 4.0, CLARIN.SI hdl 11356/2006): `bash notebooks/fetch_parlamint_en_txt.sh`
   streams ~56 GB of transfer, keeps only the plain-text part (~19 GB on disk; resumable, has stall timeout).
5. `python notebooks/parse_parlamint.py` (6M speeches, ~10 min on 8 cores), then `skim_parlamint.py`.

## UPF project: "Sold on Pleasure" (ultra-processed food on Amazon), in `upf/`
Amazon grocery listings and reviews (Amazon Reviews 2023, McAuley Lab) matched by barcode to Open Food Facts NOVA groups; the 2018 Amazon metadata adds
"also bought" links. Everything is logged, pre-declared tests first, in `upf/PLAN.md`; the paper outline is `upf/PAPER_PLAN.md`.
Raw data, caches (`upf/data/processed/soj/`), the NRC lexicons (non-redistributable) and anything holding review text stay local (see `.gitignore`).
Small result summaries are in `upf/data/processed/*.txt`, with review text replaced by "[review text omitted]".

| Strand | Scripts (`upf/notebooks/`) | Figure (`upf/figures/`) |
|---|---|---|
| How food is sold: marketing words, valence/arousal/dominance | `marketing_wordplot.py` (`--neg` for the negation-aware version), `listing_vad.py`, `vad_drivers.py`, `negation.py` | `marketing_wordplot(_neg).png`, `listing_vad.png` |
| Word network and claim systems (certification vs free-from) | `word_network.py`, `word_network_plot.py`, `claim_systems.py` | `word_network.png`, `claim_systems.png` |
| Processing vs nutrition (Nutri-Score) | `nutri_vs_nova.py` | |
| Who reviews what: review co-review network, corrected H4 | `sold_on_joy.py`, `network_structures.py`, `network_structures_plot.py` | `network_structures.png` |
| Co-purchase network ("also bought", 2018) and shopping missions | `copurchase_network.py`, `copurchase_describe.py`, `copurchase_plot.py` | `copurchase_missions.png` |
| Food x non-food category clusters | `category_network.py`, `category_network_plot.py` | `category_clusters.png` |
| Shopper types (reviewer similarity network + Louvain) | `shopper_types.py`, `shopper_stability.py`, `shopper_types_plot.py`, `shopper_mix_full.py`, `community_profiles.py` | `shopper_types.png`, `shopper_mix_full.png`, `community_profiles.png` |
| Hobbies vs health | `one_curve.py`, `product_lean.py`, `product_bins_plot.py` | `one_curve.png`, `product_bins_diverging.png` |
| Ingredient network of matched products | `matched_ingredients_extract.py`, `matched_ingredient_parse.py`, `matched_ingredient_network.py`, `matched_ingredient_network_plot.py` | `matched_ingredient_network.png` |
| Emotion classifier pilots (choice still open, see PLAN) | `emotion_pilot.py`, `goemotions_pilot.py`, `emotion_c4.py`, `go_g4.py`, `make_emotion_label_tool.py` | |

The interactive story page is `upf/site/sold-on-pleasure.html` (open in a browser). Run scripts from the repo root with the NLP environment
(`./.venv-nlp/bin/python upf/notebooks/<script>.py`). Note: `emotion_pilot.py` and `emotion_c4.py` print review snippets; redact before committing their output.
