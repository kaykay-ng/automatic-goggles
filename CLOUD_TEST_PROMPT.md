Test whether this cloud environment can host our pipeline. Read `README.md` and `PLAN.md` in the repo root first; they describe the rebuild order and the numbers we already got locally.

Do these steps in order and report findings; do NOT push, commit, or change any tracked file.

1. Environment: report Python version, CPU count, RAM, and free disk space (`df -h`). `pip install -r requirements.txt` (use a venv).
2. Network: with `curl -sI`, check that these are reachable and give HTTP status and content-length:
   `https://bulks-faostat.fao.org/production/Emissions_Totals_E_All_Data.zip`, `.../FoodBalanceSheets_E_All_Data.zip`,
   `.../Trade_DetailedTradeMatrix_E_All_Data.zip`, `.../Environment_Emissions_intensities_E_All_Data.zip`, and
   `https://www.clarin.si/repository/xmlui/bitstream/handle/11356/2006/ParlaMint-LV-en.ana.tgz`. Note any that are blocked.
3. Rebuild FAOSTAT: download the four FAOSTAT zips into `data/raw/` (unzip each into `data/raw/<zipname without .zip>/`), then run
   `python notebooks/profile_faostat.py` and `python notebooks/build_trade_networks.py` from the repo root. Time each step.
   Compare with `PLAN.md`: profile should find all 26 countries in each table and keep ~656k trade rows; the all_food network
   should have Louvain Q about 0.32 with 4 communities, backbone ~93 edges.
4. ParlaMint streaming test on ONE small country only: run the equivalent of the loop body of `notebooks/fetch_parlamint_en_txt.sh`
   for LV (stream the 566 MB tgz through `tar -xzf - -C data/raw/parlamint_en_txt --include '*-en.txt*'`), measure download speed
   in MB/s and the resulting folder size (expected ~269 MB), then run `process_country('LV')` from `notebooks/parse_parlamint.py`
   and report speeches/flagged counts (local result: 159,711 speeches, 5,357 flagged). Do NOT download any other country.
5. Extrapolate: given measured speed and free disk, estimate whether the full ParlaMint set (56 GB transfer, ~19 GB stored) and the
   parse (6M speeches; locally ~10 min on 8 cores) fit, and say what limit (disk, time, network, memory, session length) would bite first.

Done looks like: one clear final message with a short table of the checks above (pass/fail with numbers), any blocked URLs, whether
FAOSTAT outputs matched PLAN.md, measured speed and disk, and a recommendation: run everything in the cloud / run only part / do not
use the cloud. Report problems faithfully; do not work around a blocked network by other means.
