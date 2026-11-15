"""First look at the Open Food Facts export: which columns exist, and how much usable data each country has.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/off_profile.py
Streams upf/data/raw/off/en.openfoodfacts.org.products.csv.gz (tab-separated, ~1.5 GB compressed) in chunks; nothing is unpacked to disk.
Writes upf/data/processed/off_columns.txt and off_country_coverage.csv. Data: Open Food Facts, ODbL (attribution + share-alike).
"""
import csv, gzip, sys
from collections import Counter, defaultdict
from pathlib import Path
import pandas as pd

csv.field_size_limit(sys.maxsize)
SRC = Path("upf/data/raw/off/en.openfoodfacts.org.products.csv.gz"); OUT = Path("upf/data/processed"); OUT.mkdir(parents=True, exist_ok=True)
with gzip.open(SRC, "rt", encoding="utf-8", errors="replace") as f:
    header = f.readline().rstrip("\n").split("\t")
(OUT / "off_columns.txt").write_text("\n".join(header))
want = ["code", "product_name", "countries_tags", "categories_tags", "main_category", "ingredients_text", "ingredients_tags", "ingredients_analysis_tags",
        "additives_tags", "labels_tags", "nova_group", "nutriscore_grade", "brands", "origins_tags", "manufacturing_places_tags"]
have = [c for c in want if c in header]
print(f"{len(header)} columns. Wanted columns present: {have}\nmissing: {[c for c in want if c not in header]}")
print("other columns mentioning ingredient/nova/ultra:", [c for c in header if any(k in c for k in ("ingredient", "nova", "ultra")) and c not in have])

n = 0; per = defaultdict(Counter); nova_all = Counter()
reader = pd.read_csv(SRC, sep="\t", usecols=have, dtype=str, chunksize=200_000, quoting=csv.QUOTE_NONE, on_bad_lines="skip", encoding="utf-8", encoding_errors="replace")
for ch in reader:
    n += len(ch)
    ok_ing = ch.get("ingredients_tags", ch.get("ingredients_text")).notna()
    nova = ch["nova_group"] if "nova_group" in ch else pd.Series([None] * len(ch), index=ch.index)
    nova_all.update(nova.fillna("missing"))
    for ctags, ing, nv in zip(ch["countries_tags"].fillna(""), ok_ing, nova.fillna("")):
        for c in ctags.split(","):
            if not c: continue
            p = per[c]; p["products"] += 1
            if ing: p["with_ingredients"] += 1
            if nv: p["with_nova"] += 1; p[f"nova{nv[:1]}"] += 1
    print(f"  read {n:,} rows", flush=True)
print(f"\nrows: {n:,}; NOVA overall: {dict(nova_all.most_common())}")
T = pd.DataFrame(per).T.fillna(0).astype(int).sort_values("products", ascending=False)
for k in ("nova1", "nova2", "nova3", "nova4"):
    if k not in T: T[k] = 0
T["nova4_share"] = (T.nova4 / T.with_nova.where(T.with_nova > 0)).round(3)
T.to_csv(OUT / "off_country_coverage.csv")
pd.set_option("display.width", 200)
print(f"\ncountries (tags) with >= 1,000 products having a NOVA group: {(T.with_nova >= 1000).sum()}; >= 5,000: {(T.with_nova >= 5000).sum()}")
print(T.head(40).to_string())
