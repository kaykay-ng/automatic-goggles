"""Parse the Climate Watch /ndcs JSON into tidy tables. Run from final_project/:  ../.venv/bin/python ndc/notebooks/parse_ndc.py
Writes ndc/data/processed/ndc_indicators_long.csv (iso, indicator, source, category, document, value) and ndc_text_long.csv
(text indicators only, with document round)."""
import json
from pathlib import Path
import pandas as pd

RAW, PROC = Path("ndc/data/raw"), Path("ndc/data/processed")
d = json.load(open(RAW / "climatewatch_ndcs.json"))
cats = {int(k): v["name"] for k, v in d["categories"].items()}
rows = []
for i in d["indicators"]:
    cat = next((cats[c] for c in i["category_ids"] if c in cats), "")
    for iso, vals in i.get("locations", {}).items():
        for v in vals:
            if isinstance(v, dict):
                rows.append((iso, i["name"], i["source"], cat, v.get("document_slug"), v.get("value")))
L = pd.DataFrame(rows, columns=["iso", "indicator", "source", "category", "document", "value"])
L.to_csv(PROC / "ndc_indicators_long.csv", index=False)
txt = L[L.value.map(lambda x: isinstance(x, str) and len(x) >= 150)]
txt.to_csv(PROC / "ndc_text_long.csv", index=False)
print("rows:", len(L), "| countries:", L.iso.nunique(), "| indicators:", L.indicator.nunique())
print("document rounds (all indicators):", L.document.value_counts(dropna=False).to_dict())
print("text rows (>=150 chars):", len(txt), "| countries with any text:", txt.iso.nunique())
t = txt.groupby("iso").value.apply(lambda s: s.str.len().sum())
print("total characters of text per country: median", int(t.median()), "min", int(t.min()), "max", int(t.max()))
print("text by document round:", txt.document.value_counts(dropna=False).to_dict())
em = pd.read_csv(PROC / "emissions_cw_long.csv")
a, b = set(L.iso), set(em.iso)
print(f"overlap NDC countries and emissions countries: {len(a & b)} | only NDC: {sorted(a - b)[:15]} | only emissions: {sorted(b - a)[:15]}")
sub = L[(L.indicator == "2025 NDC Submission")]
print("2025 submitters:", sub.iso.nunique())
