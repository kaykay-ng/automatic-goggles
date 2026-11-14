"""H9: do NDCs become more alike across rounds? Pre-declared in ndc/PLAN.md 'ROUND 3'.
Re-embeds each round using only the text fields present in all four rounds (indc, first_ndc, revised_first_ndc, third_ndc), so changes in
Climate Watch's coding template cannot create convergence. Run from final_project/:  ./.venv-nlp/bin/python ndc/notebooks/ndc_convergence.py
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from ndc_embed import clean, passages

PROC = Path("ndc/data/processed"); RNG = np.random.default_rng(909)
ROUNDS = ["indc", "first_ndc", "revised_first_ndc", "third_ndc"]
T = pd.read_csv(PROC / "ndc_text_long.csv"); T = T[T.document.isin(ROUNDS)]
common = set.intersection(*[set(T[T.document == r].indicator) for r in ROUNDS])
T = T[T.indicator.isin(common)]
print(f"fields present in all four rounds: {len(common)}")

from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2", device="mps")
C = pd.read_csv(PROC / "controls.csv").set_index("iso")
vec, words = {}, {}
for rd in ROUNDS:
    docs = {}
    for iso, g in T[T.document == rd].groupby("iso"):
        seen, parts = set(), []
        for v in g.value:
            c = clean(str(v))
            if len(c) >= 40 and c not in seen: seen.add(c); parts.append(c)
        if parts: docs[iso] = " ".join(parts)
    isos = sorted(docs); chunks, owner = [], []
    for k, iso in enumerate(isos):
        for p in passages(docs[iso]): chunks.append(p); owner.append(k)
    E = model.encode(chunks, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
    V = np.zeros((len(isos), E.shape[1])); np.add.at(V, np.array(owner), E); V /= np.linalg.norm(V, axis=1, keepdims=True)
    # collapse near-identical joint texts (EU): keep one representative per group of cosine > 0.98
    S = V @ V.T; keep, drop = [], set()
    for i in range(len(isos)):
        if i in drop: continue
        keep.append(i); drop |= {j for j in range(i + 1, len(isos)) if S[i, j] > 0.98}
    vec[rd] = {isos[i]: V[i] for i in keep}; words[rd] = {isos[i]: len(docs[isos[i]].split()) for i in keep}
    print(f"   {rd:18s}: {len(isos)} countries with text, {len(keep)} after collapsing joint texts, median words {np.median(list(words[rd].values())):.0f}")

both = sorted(set.intersection(*[set(vec[r]) for r in ROUNDS]))
both = [i for i in both if i in C.index]
reg = np.asarray(C.loc[both, "region"].astype(str).tolist(), dtype=object); n = len(both); iu = np.triu_indices(n, 1)
same = (reg[:, None] == reg[None, :])[iu]
print(f"\ncountries present in all four rounds (after collapse): {n}")


def stats_for(rd, idx):
    V = np.array([vec[rd][both[i]] for i in idx]); S = V @ V.T; m = np.triu_indices(len(idx), 1)
    sr = (reg[idx][:, None] == reg[idx][None, :])[m]
    return S[m].mean(), S[m][sr].mean() - S[m][~sr].mean()


obs = {rd: stats_for(rd, np.arange(n)) for rd in ROUNDS}
for rd in ROUNDS:
    print(f"   {rd:18s} mean pairwise cosine {obs[rd][0]:.3f}   regional clustering (within - between region) {obs[rd][1]:+.3f}   median words {np.median([words[rd][i] for i in both]):.0f}")
bs = []
for _ in range(2000):
    idx = RNG.choice(n, n, replace=True)
    a, b = stats_for("first_ndc", idx), stats_for("third_ndc", idx); bs.append((b[0] - a[0], b[1] - a[1]))
bs = np.array(bs)
d0 = obs["third_ndc"][0] - obs["first_ndc"][0]; d1 = obs["third_ndc"][1] - obs["first_ndc"][1]
print(f"\nPRIMARY third minus first, mean similarity: {d0:+.3f}  95% CI [{np.percentile(bs[:, 0], 2.5):+.3f}, {np.percentile(bs[:, 0], 97.5):+.3f}]  one-sided p(<=0) = {(1 + (bs[:, 0] <= 0).sum()) / 2001:.4f}")
print(f"secondary third minus first, regional clustering: {d1:+.3f}  95% CI [{np.percentile(bs[:, 1], 2.5):+.3f}, {np.percentile(bs[:, 1], 97.5):+.3f}]")
# length check: does similarity rise simply because texts got longer (longer averages are smoother)?
wl = {rd: np.log([words[rd][i] for i in both]) for rd in ROUNDS}
print(f"length check: median words first {np.exp(np.median(wl['first_ndc'])):.0f} vs third {np.exp(np.median(wl['third_ndc'])):.0f}")
mid = [i for i in range(n) if abs(wl["third_ndc"][i] - wl["first_ndc"][i]) < np.log(1.5)]
if len(mid) > 20:
    a, b = stats_for("first_ndc", np.array(mid)), stats_for("third_ndc", np.array(mid))
    print(f"   countries whose length changed by < 1.5x (n={len(mid)}): mean similarity first {a[0]:.3f} -> third {b[0]:.3f}")
