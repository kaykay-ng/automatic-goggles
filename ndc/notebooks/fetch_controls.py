"""World Bank controls + World Happiness Report 2026 (Figure 2.1 data) keyed by ISO3.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python ndc/notebooks/fetch_controls.py
Writes ndc/data/processed/controls.csv (iso, name, region, income, lat, lon, pop, gdppc_ppp) and happiness.csv (iso + WHR 2023-2025 average
of life evaluation and the six 'explained by' factors)."""
import json, re, unicodedata, urllib.request
from pathlib import Path
import pandas as pd, numpy as np, openpyxl

RAW, PROC = Path("ndc/data/raw"), Path("ndc/data/processed")
def get(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)

meta = get("https://api.worldbank.org/v2/country?format=json&per_page=400")[1]
C = pd.DataFrame([dict(iso=e["id"], name=e["name"], region=e["region"]["value"], income=e["incomeLevel"]["value"],
                       lat=float(e["latitude"]) if e["latitude"] else np.nan, lon=float(e["longitude"]) if e["longitude"] else np.nan)
                  for e in meta if e["region"]["value"] != "Aggregates"])
def latest(ind):
    js = get(f"https://api.worldbank.org/v2/country/all/indicator/{ind}?format=json&per_page=20000&date=2018:2023")[1]
    (RAW / f"wb_{ind}.json").write_text(json.dumps(js))
    d = pd.DataFrame([(e["countryiso3code"], int(e["date"]), e["value"]) for e in js if e["value"] is not None], columns=["iso", "year", "v"])
    return d.sort_values("year").groupby("iso").v.last()
C["pop"] = C.iso.map(latest("SP.POP.TOTL")); C["gdppc_ppp"] = C.iso.map(latest("NY.GDP.PCAP.PP.CD"))
C.to_csv(PROC / "controls.csv", index=False)
print("World Bank countries:", len(C), "| with population:", C["pop"].notna().sum(), "| with GDP pc:", C.gdppc_ppp.notna().sum())

wb = openpyxl.load_workbook(RAW / "WHR26_Data_Figure_2.1.xlsx", read_only=True)
rows = [r[:13] for r in wb.worksheets[0].iter_rows(values_only=True)]; hdr = rows[0]
H = pd.DataFrame(rows[1:], columns=[h if h else f"x{i}" for i, h in enumerate(hdr)]).dropna(subset=["Country name"])
H = H[H.Year.notna()]; H["Year"] = H.Year.astype(int)
cols = {"Life evaluation (3-year average)": "ladder", "Explained by: Log GDP per capita": "f_gdp", "Explained by: Social support": "f_social",
        "Explained by: Healthy life expectancy": "f_health", "Explained by: Freedom to make life choices": "f_freedom",
        "Explained by: Generosity": "f_generosity", "Explained by: Perceptions of corruption": "f_corruption"}
H = H.rename(columns=cols)
def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]+", " ", s).strip()
alias = {"turkiye": "turkey", "czechia": "czech republic", "russian federation": "russia", "slovak republic": "slovakia", "korea rep": "south korea",
         "egypt arab rep": "egypt", "iran islamic rep": "iran", "viet nam": "vietnam", "lao pdr": "laos", "kyrgyz republic": "kyrgyzstan",
         "gambia the": "gambia", "congo dem rep": "congo kinshasa", "congo rep": "congo brazzaville", "yemen rep": "yemen",
         "venezuela rb": "venezuela", "hong kong sar china": "hong kong s a r of china", "syrian arab republic": "syria",
         "cote d ivoire": "ivory coast", "brunei darussalam": "brunei", "bahamas the": "bahamas", "micronesia fed sts": "micronesia"}
wbn = {}
for r in C.itertuples():
    n = norm(r.name); wbn[alias.get(n, n)] = r.iso
MANUAL = {"Congo": "COG", "DR Congo": "COD", "Czechia": "CZE", "Côte d’Ivoire": "CIV", "Hong Kong SAR of China": "HKG", "Lao PDR": "LAO",
          "Republic of Korea": "KOR", "Republic of Moldova": "MDA", "Russian Federation": "RUS", "Somalia": "SOM", "State of Palestine": "PSE",
          "Swaziland": "SWZ", "Türkiye": "TUR", "Viet Nam": "VNM", "Puerto Rico": "PRI"}          # North Cyprus, Somaliland, Taiwan: no World Bank entry
H["iso"] = H["Country name"].map(lambda s: MANUAL.get(s) or wbn.get(norm(s)))
miss = sorted(H[H.iso.isna()]["Country name"].unique())
print("WHR names not matched to a World Bank country:", miss)
recent = H[H.Year >= 2023].groupby("iso")[list(cols.values())].mean().reset_index()
recent.to_csv(PROC / "happiness.csv", index=False)
print("happiness rows (2023-25 average):", len(recent), "| years in file:", H.Year.min(), "-", H.Year.max(), "| countries ever:", H["Country name"].nunique())
