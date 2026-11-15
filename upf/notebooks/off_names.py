"""Extract product names of NOVA-labelled products sold in English-speaking markets (for the emotion analysis).
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/off_names.py
Markets: United States, United Kingdom, Canada, Australia, Ireland, New Zealand. A name is kept if it has >= 2 letters and >= 95% ASCII characters
(drops French-Canadian and other non-English names only roughly; reported). Writes upf/data/processed/off_names_en.csv.gz (gitignored).
"""
import csv, re
from pathlib import Path
import pandas as pd

SRC = Path("upf/data/raw/off/en.openfoodfacts.org.products.csv.gz"); OUT = Path("upf/data/processed/off_names_en.csv.gz")
EN = {"en:united-states", "en:united-kingdom", "en:canada", "en:australia", "en:ireland", "en:new-zealand"}
parts = []
for ch in pd.read_csv(SRC, sep="\t", usecols=["code", "countries_tags", "main_category", "product_name", "generic_name", "brands", "nova_group"], dtype=str,
                      chunksize=300_000, quoting=csv.QUOTE_NONE, on_bad_lines="skip", encoding_errors="replace"):
    ch = ch[ch.nova_group.isin(["1", "2", "3", "4"]) & ch.product_name.notna()]
    ch = ch[ch.countries_tags.fillna("").map(lambda s: bool(EN & set(s.split(","))))]
    nm = ch.product_name.str.strip()
    ascii_share = nm.map(lambda s: sum(c.isascii() for c in s) / max(len(s), 1))
    ok = (ascii_share >= 0.95) & nm.str.contains(r"[A-Za-z]{2}", regex=True)
    parts.append(ch[ok].assign(product_name=nm[ok]))
D = pd.concat(parts, ignore_index=True).drop_duplicates("code")
D["nova"] = D.nova_group.astype(int); D["n_words"] = D.product_name.str.findall(r"[A-Za-z']+").str.len()
D.drop(columns="nova_group").to_csv(OUT, index=False)
print(f"products kept: {len(D):,}; NOVA: {D.nova.value_counts().sort_index().to_dict()}; words per name: median {int(D.n_words.median())}, mean {D.n_words.mean():.1f}")
print(f"with a generic name too: {D.generic_name.notna().sum():,}; with a brand: {D.brands.notna().sum():,}")
print("random examples:", D.sample(12, random_state=3)[["product_name", "nova"]].values.tolist())
