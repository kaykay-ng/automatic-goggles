"""Extract the products that have both a NOVA group and an ingredient list from the Open Food Facts export, in compact form.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/off_extract.py
Keeps only ingredient tags in the shared English taxonomy ('en:...'); products whose tags are less than 80% English-taxonomy are dropped (untranslated lists).
Writes upf/data/processed/off_products.csv.gz (code, nova, countries, main_category, tags) -- gitignored (large).
"""
import csv
from pathlib import Path
import pandas as pd

SRC = Path("upf/data/raw/off/en.openfoodfacts.org.products.csv.gz"); OUT = Path("upf/data/processed/off_products.csv.gz")
cols = ["code", "countries_tags", "main_category", "ingredients_tags", "nova_group"]
parts, n_in, n_drop_lang = [], 0, 0
for ch in pd.read_csv(SRC, sep="\t", usecols=cols, dtype=str, chunksize=300_000, quoting=csv.QUOTE_NONE, on_bad_lines="skip", encoding_errors="replace"):
    ch = ch[ch.nova_group.isin(["1", "2", "3", "4"]) & ch.ingredients_tags.notna()]
    n_in += len(ch)
    tags = ch.ingredients_tags.str.split(",")
    en = tags.map(lambda t: [x for x in t if x.startswith("en:")])
    share = en.str.len() / tags.str.len()
    keep = (share >= 0.8) & (en.str.len() >= 1)
    n_drop_lang += int((~keep).sum())
    parts.append(pd.DataFrame({"code": ch.code[keep], "nova": ch.nova_group[keep].astype(int), "countries": ch.countries_tags[keep].fillna(""),
                               "main_category": ch.main_category[keep].fillna(""), "tags": en[keep].map(lambda t: ",".join(dict.fromkeys(t)))}))
D = pd.concat(parts, ignore_index=True)
dup = D.code.duplicated().sum(); D = D.drop_duplicates("code")
D.to_csv(OUT, index=False)
print(f"products with NOVA + ingredients: {n_in:,}; dropped (mostly untranslated tags): {n_drop_lang:,}; duplicate codes removed: {dup:,}; kept {len(D):,}")
print("NOVA among kept:", D.nova.value_counts().sort_index().to_dict(), "| median tags per product:", int(D.tags.str.count(",").median() + 1))
