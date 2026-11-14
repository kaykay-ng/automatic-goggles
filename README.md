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
