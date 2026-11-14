"""Fetch Climate Watch historical emissions (source Climate Watch, All GHG, MtCO2e) for all countries.
Run from final_project/:  ../.venv/bin/python ndc/notebooks/fetch_emissions.py
Sector ids from the API meta: 3208 total excl LULUCF, 3209 total incl LULUCF, 3210 energy, 3211 industrial processes, 3212 agriculture,
3213 waste, 3214 LULUCF, 3216-3221 energy sub-sectors. Writes ndc/data/raw/climatewatch_emissions_all_ghg.json and
ndc/data/processed/emissions_cw_long.csv (iso, country, sector, year, MtCO2e).
"""
import json, time, urllib.request, urllib.parse
from pathlib import Path
import pandas as pd

RAW, PROC = Path("ndc/data/raw"), Path("ndc/data/processed")
SECTORS = [3208, 3209, 3210, 3211, 3212, 3213, 3214, 3216, 3217, 3218, 3219, 3220, 3221]
base = "https://www.climatewatchdata.org/api/v1/data/historical_emissions"
rows, page = [], 1
while True:
    q = "&".join(["source_ids[]=274", "gas_ids[]=553"] + [f"sector_ids[]={s}" for s in SECTORS] + [f"page={page}", "per_page=500"])
    with urllib.request.urlopen(f"{base}?{q}", timeout=120) as r:
        d = json.load(r)
    rows += d["data"]
    print(f"page {page}: {len(d['data'])} series", flush=True)
    if len(d["data"]) < 500:
        break
    page += 1; time.sleep(0.5)
(RAW / "climatewatch_emissions_all_ghg.json").write_text(json.dumps(rows))
long = [dict(iso=s["iso_code3"], country=s["country"], sector=s["sector"], year=e["year"], mtco2e=e["value"])
        for s in rows for e in s["emissions"]]
df = pd.DataFrame(long)
df.to_csv(PROC / "emissions_cw_long.csv", index=False)
print("series:", len(rows), "| countries:", df.iso.nunique(), "| years", df.year.min(), "-", df.year.max(), "| rows", len(df))
print(df.groupby("sector").iso.nunique().to_string())
last = df.groupby("iso").year.max().value_counts().sort_index()
print("last year available per country:", last.to_dict())
