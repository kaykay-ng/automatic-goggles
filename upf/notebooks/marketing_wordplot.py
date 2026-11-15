"""Word plot: which words sell ultra-processed (NOVA 4) vs less processed (NOVA 1-3) food on Amazon? Descriptive (illustrates A1), not a test.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/marketing_wordplot.py
Text = Amazon marketing copy (features + description). Score = log-odds ratio with an informative Dirichlet prior (Monroe, Colaresi & Quinn 2008), z-scored (same method as ndc/notebooks/ndc_wordplot.py).
To keep 'what the food is' out of it, products are CATEGORY-BALANCED: in each Open Food Facts category with >= 100 products on both sides, the larger side is randomly
downsampled to the size of the smaller one. Counts are document counts (a word counts once per product), so long boilerplate descriptions do not dominate.
Brand and store words are removed, as are pack-size/unit words.
"""
import re
from collections import Counter
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

PROC = Path("upf/data/processed"); CACHE = PROC / "soj"; FIG = Path("upf/figures"); FIG.mkdir(exist_ok=True)
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"; BLUE, ORANGE = "#2a78d6", "#eb6834"
P = pd.read_csv(CACHE / "products.csv.gz", usecols=["parent_asin", "nova", "category", "brand", "store"])
M = pd.read_csv(PROC / "amazon_meta_compact.csv.gz", usecols=["parent_asin", "features", "description"]).drop_duplicates("parent_asin")
D = P.merge(M, on="parent_asin"); D["text"] = (D.features.fillna("") + " " + D.description.fillna("")).str.strip()
D = D[D.text.str.split().str.len() >= 10]; D["u"] = D.nova == 4
c = D.groupby("category").u.agg(["sum", "size"]); cats = c[(c["sum"] >= 100) & (c["size"] - c["sum"] >= 100)].index
rng = np.random.default_rng(31); parts = []
for k in cats:
    s = D[D.category == k]; n = min(int(s.u.sum()), int((~s.u).sum()))
    parts += [s[s.u].sample(n, random_state=int(rng.integers(1e9))), s[~s.u].sample(n, random_state=int(rng.integers(1e9)))]
B = pd.concat(parts)
brandw = set()
for x in pd.concat([B.brand.dropna().astype(str), B.store.dropna().astype(str)]): brandw |= set(re.findall(r"[a-z]{3,}", x.lower()))
STOP = set(ENGLISH_STOP_WORDS) | brandw | {"oz", "ounce", "ounces", "pack", "packs", "count", "lb", "lbs", "pound", "pounds", "fl", "size", "bag", "bags", "box", "boxes", "case",
                                           "bottle", "bottles", "can", "cans", "jar", "jars", "per", "product", "products", "item", "items", "amazon", "br"}
docs = {g: [set(w for w in re.findall(r"[a-z]{3,}", t.lower()) if w not in STOP) for t in B.text[B.u == g]] for g in (True, False)}
ca = Counter(w for d in docs[True] for w in d); cb = Counter(w for d in docs[False] for w in d)
na, nb = len(docs[True]), len(docs[False])
vocab = [w for w in set(ca) | set(cb) if ca[w] + cb[w] >= 30]
ya = np.array([ca[w] for w in vocab], float); yb = np.array([cb[w] for w in vocab], float)
bg = ya + yb; alpha = 500 * bg / bg.sum(); a0 = alpha.sum(); Na, Nb = ya.sum(), yb.sum()
delta = np.log((ya + alpha) / (Na + a0 - ya - alpha)) - np.log((yb + alpha) / (Nb + a0 - yb - alpha))
z = delta / np.sqrt(1 / (ya + alpha) + 1 / (yb + alpha))
fa, fb = 100 * ya / na, 100 * yb / nb                        # % of products whose copy uses the word
W = pd.DataFrame({"word": vocab, "pct_nova4": fa, "pct_nova123": fb, "z": z}).sort_values("z")
W.to_csv(PROC / "marketing_wordplot.csv", index=False)
print(f"categories {len(cats)}; balanced products {na:,} per side; vocabulary {len(vocab):,} words (>= 30 products)")
print("MOST 'NOVA 1-3' words: " + ", ".join(f"{r.word} ({r.z:.1f})" for r in W.head(30).itertuples()))
print("MOST 'NOVA 4' words: " + ", ".join(f"{r.word} ({r.z:.1f})" for r in W.tail(30).iloc[::-1].itertuples()))

fig, ax = plt.subplots(figsize=(10, 8.4))
floor = 0.05; x = np.maximum(W.pct_nova123, floor); y = np.maximum(W.pct_nova4, floor)
col = np.where(W.z >= 3, ORANGE, np.where(W.z <= -3, BLUE, "#cfcdc6"))
size = np.where(np.abs(W.z) >= 3, 16, 6)
ax.scatter(x, y, c=col, s=size, linewidths=0, alpha=0.85, zorder=2)
lim = [floor, max(x.max(), y.max()) * 1.4]; ax.plot(lim, lim, color=AXIS, lw=0.9, ls="--", zorder=1)
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(lim); ax.set_ylim(lim)
placed = []                                                     # greedy label placement in log space: skip a label if it would sit on top of one already drawn
cand = pd.concat([W.head(26), W.tail(26)]).assign(a=lambda d: d.z.abs()).sort_values("a", ascending=False)
for r in cand.itertuples():
    lx, ly = np.log10(max(r.pct_nova123, floor)), np.log10(max(r.pct_nova4, floor)); up = r.z > 0
    tx, ty = (lx - 0.03, ly + 0.035) if up else (lx + 0.03, ly - 0.045)
    if any(abs(tx - px) < 0.022 * max(len(r.word), 4) / 4 + 0.05 and abs(ty - py) < 0.05 for px, py in placed): continue
    placed.append((tx, ty))
    ax.annotate(r.word, (10 ** lx, 10 ** ly), xytext=(10 ** tx, 10 ** ty), textcoords="data", fontsize=8.5, color=INK, ha="right" if up else "left",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.4, shrinkA=0, shrinkB=2))
ax.grid(color=GRID, lw=0.5); ax.set_axisbelow(True)
for s in ("top", "right"): ax.spines[s].set_visible(False)
ax.set_xlabel("% of LESS processed products (NOVA 1-3) whose marketing copy uses the word", color=INK2)
ax.set_ylabel("% of ULTRA-processed products (NOVA 4) whose marketing copy uses the word", color=INK2)
ax.set_title(f"Pleasure vs purity: words that sell ultra-processed vs less processed food on Amazon\n"
             f"{na:,} products per side, balanced within {len(cats)} food categories; log-odds z-score (|z| >= 3 coloured)", loc="left", fontsize=11, color=INK)
ax.legend(handles=[plt.Line2D([], [], marker="o", ls="", color=ORANGE, label="used more for ultra-processed (z >= 3)"),
                   plt.Line2D([], [], marker="o", ls="", color=BLUE, label="used more for less processed (z <= -3)"),
                   plt.Line2D([], [], marker="o", ls="", color="#cfcdc6", label="no clear difference")], loc="upper left", frameon=False, fontsize=8.5)
fig.text(0.01, 0.005, "Data: Amazon Reviews 2023 (Hou et al. 2024) matched by barcode to Open Food Facts (ODbL). Brand, store and pack-size words removed.", fontsize=7.5, color=MUTED)
fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(FIG / "marketing_wordplot.png", dpi=170); print("saved upf/figures/marketing_wordplot.png")
