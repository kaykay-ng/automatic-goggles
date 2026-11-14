"""Validate the NDC language measure BEFORE any test. Run from final_project/ with the NLP env: ./.venv-nlp/bin/python ndc/notebooks/ndc_validate.py"""
from pathlib import Path
import numpy as np, pandas as pd
PROC = Path("ndc/data/processed"); rng = np.random.default_rng(5)
rd = "first_ndc"
V = np.load(PROC / f"ndc_vectors_{rd}.npy"); idx = pd.read_csv(PROC / f"ndc_index_{rd}.csv"); isos = list(idx.iso)
E = np.load(PROC / f"ndc_passvec_{rd}.npy"); own = np.load(PROC / f"ndc_passowner_{rd}.npy")
raw_sim = V @ V.T; n = len(isos); iu = np.triu_indices(n, 1)
print("== (1) near-duplicate texts (raw cosine > 0.98):")
dup = [(isos[i], isos[j], raw_sim[i, j]) for i, j in zip(*iu) if raw_sim[i, j] > 0.98]
print("   pairs:", len(dup), "| countries involved:", len({a for a, b, c in dup} | {b for a, b, c in dup}))
from collections import defaultdict
g = defaultdict(set)
for a, b, c in dup:
    g[a].add(b); g[b].add(a)
seen, groups = set(), []
for k in g:
    if k in seen: continue
    comp, stack = set(), [k]
    while stack:
        x = stack.pop()
        if x in comp: continue
        comp.add(x); stack += list(g[x] - comp)
    seen |= comp; groups.append(sorted(comp))
for c in groups:
    print(f"   group of {len(c)}: {' '.join(c)}")
Vc = V - V.mean(axis=0); Vc /= np.linalg.norm(Vc, axis=1, keepdims=True); S = Vc @ Vc.T
print("\n== (2) nearest neighbours (centred cosine), pre-chosen BRA, IND, NGA, FJI, USA, CHN:")
for c in ["BRA", "IND", "NGA", "FJI", "USA", "CHN"]:
    if c in isos:
        i = isos.index(c); o = [j for j in np.argsort(-S[i]) if j != i][:6]
        print(f"   {c}: " + ", ".join(f"{isos[j]} {S[i, j]:.2f}" for j in o))
print("\n== (3) split-half reliability (random halves of each country's passages; countries with >=6 passages)")
keep = [k for k in range(n) if (own == k).sum() >= 6]
rs = []
for _ in range(100):
    A = np.zeros((len(keep), E.shape[1])); B = A.copy()
    for r, k in enumerate(keep):
        ps = np.where(own == k)[0]; rng.shuffle(ps); h = len(ps) // 2
        A[r] = E[ps[:h]].mean(0); B[r] = E[ps[h:]].mean(0)
    A -= A.mean(0); B -= B.mean(0)
    A /= np.linalg.norm(A, axis=1, keepdims=True); B /= np.linalg.norm(B, axis=1, keepdims=True)
    SA, SB = A @ A.T, B @ B.T; u = np.triu_indices(len(keep), 1)
    rs.append(np.corrcoef(SA[u], SB[u])[0, 1])
print(f"   countries {len(keep)} | r between halves: mean {np.mean(rs):.2f}, range {min(rs):.2f}-{max(rs):.2f}")
print("\n== (4) text length vs mean similarity to others (length artefact?)")
ms = (S.sum(1) - 1) / (n - 1)
print("   Spearman(n_words, mean similarity to others) =", round(float(pd.Series(idx.n_words).corr(pd.Series(ms), method='spearman')), 2))
