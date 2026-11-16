"""Which words drive the arousal and dominance differences between NOVA-4 and NOVA 1-3 marketing copy? (descriptive; same food-word exclusion as listing_vad.py)
Category-balanced: within each of the 25 categories with >= 100 listings on both sides, equal numbers of each group (random downsampling), as in marketing_wordplot.py.
Contribution of word w to the mean difference: c_w = score_w x (share of the group's lexicon tokens that are w, NOVA 4 minus NOVA 1-3).
Run: ./.venv-nlp/bin/python upf/notebooks/vad_drivers.py
"""
import re, sys
from collections import Counter
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import sold_on_joy as S
V = pd.read_csv("upf/data/raw/nrc/NRC-VAD-Lexicon-v2.1/Unigrams/unigrams-NRC-VAD-Lexicon-v2.1.txt", sep="\t", keep_default_na=False).set_index("term")
_, FOOD = S.lexicon(); TOK = re.compile(r"[a-z']+")
L = pd.read_csv("upf/data/processed/soj/listing_vad.csv.gz"); M = pd.read_csv("upf/data/processed/amazon_meta_compact.csv.gz", usecols=["parent_asin", "features", "description"]).drop_duplicates("parent_asin")
D = L.merge(M, on="parent_asin"); D["u"] = D.nova == 4; D["text"] = D.features.fillna("") + " " + D.description.fillna("")
c = D.groupby("category").u.agg(["sum", "size"]); cats = c[(c["sum"] >= 100) & (c["size"] - c["sum"] >= 100)].index
rng = np.random.default_rng(31); parts = []
for k in cats:
    s = D[D.category == k]; n = min(int(s.u.sum()), int((~s.u).sum())); parts += [s[s.u].sample(n, random_state=int(rng.integers(1e9))), s[~s.u].sample(n, random_state=int(rng.integers(1e9)))]
B = pd.concat(parts); print(f"balanced sample: {len(B) // 2:,} listings per side in {len(cats)} categories")
cnt = {g: Counter() for g in (True, False)}
for t, g in zip(B.text, B.u):
    for w in TOK.findall(t.lower()):
        w = w.strip("'"); w = w[:-1] if (w not in V.index and w.endswith("s") and w[:-1] in V.index) else w
        if w in V.index and w not in FOOD: cnt[g][w] += 1
n4, n1 = sum(cnt[True].values()), sum(cnt[False].values())
for dim in ("dominance", "arousal"):
    sc = V[dim]; words = set(cnt[True]) | set(cnt[False])
    m4 = sum(sc[w] * c_ for w, c_ in cnt[True].items()) / n4; m1 = sum(sc[w] * c_ for w, c_ in cnt[False].items()) / n1
    con = sorted(((sc[w] * (cnt[True][w] / n4 - cnt[False][w] / n1), w) for w in words))
    print(f"\n{dim.upper()}: balanced mean NOVA 4 {m4:+.4f} vs NOVA 1-3 {m1:+.4f}, difference {m4 - m1:+.4f}")
    fmt = lambda x, w: f"{w} ({sc[w]:+.2f}; {1e3 * cnt[True][w] / n4:.1f}/{1e3 * cnt[False][w] / n1:.1f} per 1k; {x:+.4f})"
    print("  pulling NOVA 4 DOWN: " + ", ".join(fmt(x, w) for x, w in con[:18]))
    print("  pulling NOVA 4 UP:   " + ", ".join(fmt(x, w) for x, w in con[::-1][:14]))
