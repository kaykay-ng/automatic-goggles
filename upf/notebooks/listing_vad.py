"""DESCRIPTIVE: valence, arousal and dominance (NRC VAD v2.1, -1..1) of Amazon marketing copy for the 75,933 matched food listings, by NOVA group.
Valence and arousal were pre-declared (amendment A1); DOMINANCE is added here on request and is descriptive only (not pre-declared).
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/listing_vad.py
"""
import re, sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).parent))
import sold_on_joy as S

PROC = Path("upf/data/processed"); CACHE = PROC / "soj"; FIG = Path("upf/figures")
V = pd.read_csv("upf/data/raw/nrc/NRC-VAD-Lexicon-v2.1/Unigrams/unigrams-NRC-VAD-Lexicon-v2.1.txt", sep="\t", keep_default_na=False).set_index("term")
_, FOOD = S.lexicon(); TOK = re.compile(r"[a-z']+")
P = pd.read_csv(CACHE / "products.csv.gz", usecols=["parent_asin", "nova", "category", "title", "m_tokens"])
M = pd.read_csv(PROC / "amazon_meta_compact.csv.gz", usecols=["parent_asin", "features", "description"]).drop_duplicates("parent_asin")
D = P.merge(M, on="parent_asin"); D = D[D.m_tokens >= 10].copy()
lex = {t: (v, a, d) for t, v, a, d in zip(V.index, V.valence, V.arousal, V.dominance)}


def score(text):
    s = np.zeros(3); n = 0
    for w in TOK.findall(text.lower()):
        w = w.strip("'"); w = w[:-1] if (w not in lex and w.endswith("s") and w[:-1] in lex) else w
        if w in lex and w not in FOOD: s += lex[w]; n += 1
    return (s / n if n else np.full(3, np.nan)), n


sc = [score(f"{f if isinstance(f, str) else ''} {d if isinstance(d, str) else ''}") for f, d in zip(D.features, D.description)]
D["valence"], D["arousal"], D["dominance"] = zip(*[tuple(s[0]) for s in sc]); D["n_lex"] = [s[1] for s in sc]
D = D.dropna(subset=["valence"]); D["u"] = D.nova == 4; D["group"] = np.where(D.u, "NOVA 4", "NOVA 1-3")
print(f"listings with marketing copy >= 10 words and lexicon words: {len(D):,}; median lexicon words per listing {int(D.n_lex.median())}")
print("\nMEAN (median) by NOVA group, scale -1..1, food words excluded:")
print(D.groupby("nova")[["valence", "arousal", "dominance"]].agg(["mean", "median"]).round(3).to_string())
print("\ncorrelations between the three scores (Spearman):"); print(D[["valence", "arousal", "dominance"]].corr("spearman").round(2).to_string())
print("\nWITHIN-CATEGORY difference NOVA 4 minus NOVA 1-3 (25 categories with >= 100 each side; 2,000 shuffles within category):")
for c in ("valence", "arousal", "dominance"):
    est, p, k, n = S.within(D, c, nperm=2000, two_sided=True); print(f"  {c:10s} {est:+.4f}  two-sided p = {p:.4f}  ({k} categories, {n:,} listings){'   <- descriptive, not pre-declared' if c == 'dominance' else ''}")
print("\nexample listings (titles only) at the extremes of each score:")
for c in ("valence", "arousal", "dominance"):
    lo, hi = D.nsmallest(3, c), D.nlargest(3, c)
    print(f"  {c} LOW: " + " | ".join(f"{t[:40]} ({v:+.2f})" for t, v in zip(lo.title.astype(str), lo[c])))
    print(f"  {c} HIGH: " + " | ".join(f"{t[:40]} ({v:+.2f})" for t, v in zip(hi.title.astype(str), hi[c])))
D[["parent_asin", "nova", "category", "valence", "arousal", "dominance", "n_lex"]].to_csv(CACHE / "listing_vad.csv.gz", index=False)

fig, axs = plt.subplots(1, 3, figsize=(12, 3.6), sharey=False)
for ax, c in zip(axs, ("valence", "arousal", "dominance")):
    bins = np.linspace(-0.6, 0.8, 57)
    for g, col in (("NOVA 1-3", "#23756f"), ("NOVA 4", "#d9531e")):
        x = D.loc[D.group == g, c]; h, e = np.histogram(x, bins=bins, density=True)
        ax.plot((e[:-1] + e[1:]) / 2, h, color=col, lw=2, label=f"{g} (mean {x.mean():+.3f})")
    ax.axvline(0, color="#c3c2b7", lw=0.8); ax.set_title(c.capitalize(), loc="left", fontsize=11); ax.set_xlabel("listing score (-1 to +1)")
    ax.spines[["top", "right"]].set_visible(False); ax.legend(frameon=False, fontsize=8)
axs[0].set_ylabel("density of listings")
fig.suptitle(f"Amazon marketing copy of {len(D):,} matched food listings (copy >= 10 words): valence, arousal, dominance (NRC VAD v2.1, food words excluded)", fontsize=10, x=0.01, ha="left")
fig.tight_layout(); fig.savefig(FIG / "listing_vad.png", dpi=160); print("saved upf/figures/listing_vad.png")
