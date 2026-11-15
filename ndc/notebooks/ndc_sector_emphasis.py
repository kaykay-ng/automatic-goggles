"""Recompute ndc/data/processed/ndc_sector_emphasis.csv with the current SECTORS lists in ndc_embed.py, WITHOUT re-embedding (vectors stay as they are).
Same document construction as ndc_embed.py. Run from final_project/:  ./.venv-nlp/bin/python ndc/notebooks/ndc_sector_emphasis.py
"""
import re, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from ndc_embed import SECTORS, clean, ROUNDS, PROC

T = pd.read_csv(PROC / "ndc_text_long.csv"); rows = []
for rd in ROUNDS:
    for iso, g in T[T.document == rd].groupby("iso"):
        seen, parts = set(), []
        for v in g.value:
            c = clean(v)
            if c and c not in seen: seen.add(c); parts.append(c)
        low = " ".join(parts).lower(); nw = max(len(low.split()), 1)
        r = {"round": rd, "iso": iso, "n_words": nw}; r.update({s: 1e4 * len(re.findall(rx, low)) / nw for s, rx in SECTORS.items()}); rows.append(r)
pd.DataFrame(rows).to_csv(PROC / "ndc_sector_emphasis.csv", index=False); print("rows", len(rows))
