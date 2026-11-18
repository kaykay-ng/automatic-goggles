"""Pull the raw ingredient list text for the Open Food Facts products matched to Amazon listings (the 58,051 barcodes with NOVA).
Run from final_project/:  ./.venv-nlp/bin/python upf/notebooks/matched_ingredients_extract.py
Writes upf/data/processed/soj/matched_ingredients_raw.csv.gz (code13, nova, ingredients_text, ingredients_tags) -- gitignored.
"""
import csv
from pathlib import Path
import pandas as pd

SRC = Path("upf/data/raw/off/en.openfoodfacts.org.products.csv.gz"); SOJ = Path("upf/data/processed/soj")
pad = lambda s: s.lstrip("0").zfill(13) if isinstance(s, str) and s.isdigit() else None
F = pd.read_csv(SOJ / "off_fields_matched.csv.gz", usecols=["code13", "nova"], dtype=str)
F["code13"] = F.code13.str.zfill(13); want = set(F.code13)
print(f"matched barcodes: {len(want):,}", flush=True)
parts = []
for ch in pd.read_csv(SRC, sep="\t", usecols=["code", "ingredients_text", "ingredients_tags"], dtype=str, chunksize=300_000,
                      quoting=csv.QUOTE_NONE, on_bad_lines="skip", encoding_errors="replace"):
    ch["code13"] = ch.code.map(pad); ch = ch[ch.code13.isin(want)]
    if len(ch): parts.append(ch[["code13", "ingredients_text", "ingredients_tags"]])
D = pd.concat(parts).drop_duplicates("code13").merge(F.drop_duplicates("code13"), on="code13")
D.to_csv(SOJ / "matched_ingredients_raw.csv.gz", index=False)
print(f"found {len(D):,}; with ingredients_text {D.ingredients_text.notna().sum():,}; with tags {D.ingredients_tags.notna().sum():,}")
