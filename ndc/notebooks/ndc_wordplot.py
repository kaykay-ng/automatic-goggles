"""Scattertext-style word plot: which NDC words separate agriculture-heavy from energy-heavy emitters? (illustrates H1; descriptive, not a test)
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python ndc/notebooks/ndc_wordplot.py
Groups: top tercile of agriculture share of 2015 emissions (excl. LULUCF) vs top tercile of energy share; overlap removed.
Score: log-odds ratio with an informative Dirichlet prior (Monroe, Colaresi & Quinn 2008), z-scored. x/y = frequency per 10,000 words in each group.
"""
import re, sys
from collections import Counter
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
sys.path.insert(0, str(Path(__file__).parent))
import ndc_common as D
from ndc_embed import clean

nodes, PROC = D.nodes, D.PROC
em = D.E15.loc[nodes]; TOT = D.TOT
agri = (em["Agriculture"] / em[TOT]).values; ener = (em["Energy"] / em[TOT]).values
ta, te = np.quantile(agri, 2 / 3), np.quantile(ener, 2 / 3)
A = [i for i, a, e in zip(nodes, agri, ener) if a >= ta and e < te]; B = [i for i, a, e in zip(nodes, agri, ener) if e >= te and a < ta]
print(f"agriculture-heavy (agri share >= {ta:.2f}): {len(A)} countries, e.g. {' '.join(A[:12])}")
print(f"energy-heavy (energy share >= {te:.2f}): {len(B)} countries, e.g. {' '.join(B[:12])}")

T = pd.read_csv(PROC / "ndc_text_long.csv"); T = T[T.document == "first_ndc"]
docs = {}
for iso, g in T.groupby("iso"):
    seen, parts = set(), []
    for v in g.value:
        c = clean(v)
        if c and c not in seen: seen.add(c); parts.append(c)
    docs[iso] = " ".join(parts)
STOP = set(ENGLISH_STOP_WORDS) | {"ndc", "ndcs", "indc", "per", "cent", "also", "will", "shall", "may", "would", "could", "within", "including", "well", "one", "two"}


def terms(text):
    toks = [t for t in re.findall(r"[a-z]+", text.lower()) if len(t) >= 3]
    uni = [t for t in toks if t not in STOP]
    big = [f"{a} {b}" for a, b in zip(toks, toks[1:]) if a not in STOP and b not in STOP]
    return uni + big


cnt = {i: Counter(terms(docs[i])) for i in set(A) | set(B) if i in docs}
ca = sum((cnt[i] for i in A if i in cnt), Counter()); cb = sum((cnt[i] for i in B if i in cnt), Counter())
support = Counter(t for i in cnt for t in cnt[i])
vocab = [t for t in set(ca) | set(cb) if support[t] >= 5 and ca[t] + cb[t] >= 8]
ya = np.array([ca[t] for t in vocab], float); yb = np.array([cb[t] for t in vocab], float)
na, nb = ya.sum(), yb.sum(); bg = ya + yb; alpha = 500 * bg / bg.sum(); a0 = alpha.sum()
delta = np.log((ya + alpha) / (na + a0 - ya - alpha)) - np.log((yb + alpha) / (nb + a0 - yb - alpha))
z = delta / np.sqrt(1 / (ya + alpha) + 1 / (yb + alpha))
fa, fb = 1e4 * ya / na, 1e4 * yb / nb
df = pd.DataFrame({"term": vocab, "agri_per10k": fa, "energy_per10k": fb, "z": z, "countries": [support[t] for t in vocab]}).sort_values("z")
df.to_csv(PROC / "ndc_wordplot_agri_vs_energy.csv", index=False)
print(f"\nvocabulary: {len(vocab)} terms (in >=5 countries, >=8 uses); words in groups: agri {int(na)}, energy {int(nb)}")
print("\nMOST ENERGY-HEAVY terms (z strongly negative):\n  " + "; ".join(f"{r.term} ({r.z:.1f})" for r in df.head(25).itertuples()))
print("\nMOST AGRICULTURE-HEAVY terms (z strongly positive):\n  " + "; ".join(f"{r.term} ({r.z:.1f})" for r in df.tail(25).iloc[::-1].itertuples()))

fig, ax = plt.subplots(figsize=(11.5, 9.5))
floor = 0.5
sc = ax.scatter(np.maximum(fb, floor), np.maximum(fa, floor), c=z, cmap="coolwarm", s=14 + 2 * np.sqrt(ya + yb), alpha=0.75, vmin=-6, vmax=6, linewidths=0)
ax.set_xscale("log"); ax.set_yscale("log")
ax.plot([floor, max(fa.max(), fb.max()) * 1.3], [floor, max(fa.max(), fb.max()) * 1.3], color="#999", lw=0.8, ls="--")
lab = list(df.head(18).itertuples()) + list(df.tail(18).itertuples()) + [r for r in df.assign(f=fa + fb).nlargest(8, "f").itertuples()]
done = set()
for k, r in enumerate(lab):
    if r.term in done: continue
    done.add(r.term)
    ax.annotate(r.term, (max(r.energy_per10k, floor), max(r.agri_per10k, floor)), fontsize=8, xytext=(4, 3 + (k % 3) * 3), textcoords="offset points")
ax.set_xlabel(f"frequency in ENERGY-heavy NDCs (per 10,000 words; {len(B)} countries)  →  words used more by energy emitters lie below the diagonal")
ax.set_ylabel(f"frequency in AGRICULTURE-heavy NDCs (per 10,000 words; {len(A)} countries)  →  agriculture words lie above")
ax.set_title("NDC words: agriculture-heavy vs energy-heavy emitters (first NDC; colour = log-odds z, red = agriculture-heavy)")
fig.colorbar(sc, ax=ax, label="log-odds z (red: agriculture-heavy, blue: energy-heavy)", shrink=0.7)
fig.tight_layout(); fig.savefig(Path("ndc/figures") / "wordplot_agri_vs_energy.png", dpi=140)
print("\nsaved ndc/figures/wordplot_agri_vs_energy.png")
