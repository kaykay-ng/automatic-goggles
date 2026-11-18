"""Processing or nutrition? (upf/PLAN.md 'PROCESSING OR NUTRITION?'): N1/N1b marketing valence/arousal NOVA 4 vs 1-3 within category x Nutri-Score grade;
N2/N2b valence/arousal vs Nutri-Score grade within category x NOVA group.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/nutri_vs_nova.py
"""
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

C = Path("upf/data/processed/soj"); RNG = np.random.default_rng(1611); NPERM = 5000
L = pd.read_csv(C / "listing_vad.csv.gz")
P = pd.read_csv(C / "products.csv.gz", usecols=["parent_asin", "code13"]); P["code13"] = P.code13.astype(str).str.zfill(13)
F = pd.read_csv(C / "off_fields_matched.csv.gz", usecols=["code13", "nutriscore_grade"], dtype=str)
D = L.merge(P, on="parent_asin").merge(F, on="code13", how="left")
GR = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}; D["grade"] = D.nutriscore_grade.map(GR); n0 = len(D); D = D.dropna(subset=["grade"]).reset_index(drop=True)
D["u"] = D.nova == 4
print(f"listings with copy scores {n0:,}; with Nutri-Score A-E {len(D):,} ({len(D) / n0:.0%})")
print("\nmean valence by NOVA group x grade (n):")
t = D.assign(g=np.where(D.u, "NOVA 4", "NOVA 1-3")).groupby(["g", "nutriscore_grade"]).valence.agg(["mean", "size"])
print(t.unstack(0).round(3).to_string())


def diff_test(df, val, strata, minside=20):
    s = df[strata].astype(str).agg("|".join, axis=1)
    ok = df.groupby(s).u.agg(["sum", "size"]); ok = ok[(ok["sum"] >= minside) & (ok["size"] - ok["sum"] >= minside)].index
    d = df[s.isin(ok)].copy(); d["s"] = s[s.isin(ok)]; d = d.sort_values("s", kind="stable").reset_index(drop=True)
    cat = pd.factorize(d.s)[0]; y = d[val].values.astype(float); lab = d.u.values.astype(bool); k = cat.max() + 1; w = np.bincount(cat).astype(float)
    def stat(lb):
        s4 = np.bincount(cat, y * lb, k); n4 = np.bincount(cat, lb.astype(float), k); s1 = np.bincount(cat, y * ~lb, k); n1 = np.bincount(cat, (~lb).astype(float), k)
        return float(np.sum(w * (s4 / n4 - s1 / n1)) / w.sum())
    obs = stat(lab); null = np.empty(NPERM)
    for i in range(NPERM): null[i] = stat(lab[np.lexsort((RNG.random(len(lab)), cat))])   # d is sorted by stratum, so this shuffles within strata
    return obs, (1 + np.sum(null >= obs)) / (NPERM + 1), len(ok), len(d), set(d.parent_asin)


def grade_test(df, val):
    s = df.category.astype(str) + "|" + df.u.astype(str); d = df.assign(s=s)
    ok = [g for g, x in d.groupby("s") if len(x) >= 30 and x.grade.nunique() >= 3]; d = d[d.s.isin(ok)].sort_values("s", kind="stable").reset_index(drop=True)
    cat = pd.factorize(d.s)[0]; y = d[val].values; g = d.grade.values; idx = [np.where(cat == c)[0] for c in range(cat.max() + 1)]; w = np.array([len(i) for i in idx], float)
    yr = [stats.rankdata(y[i]) for i in idx]
    def stat(gg): return float(np.sum(w * np.array([np.corrcoef(stats.rankdata(gg[i]), r)[0, 1] for i, r in zip(idx, yr)])) / w.sum())
    obs = stat(g); null = np.empty(NPERM)
    for k in range(NPERM): null[k] = stat(g[np.lexsort((RNG.random(len(g)), cat))])
    return obs, (1 + np.sum(np.abs(null) >= abs(obs))) / (NPERM + 1), len(ok), len(d)


res = {}
for val, tag in (("valence", "N1"), ("arousal", "N1b")):
    b, pb, kb, nb, _ = diff_test(D, val, ["category"])
    e, p, k, n, keep = diff_test(D, val, ["category", "nutriscore_grade"])
    b2, pb2, _, _, _ = diff_test(D[D.parent_asin.isin(keep)], val, ["category"])
    res[tag] = p
    print(f"\n== {tag} {val} == baseline within category (same listings, >= 20 per side): {b:+.4f} p={pb:.4f} ({kb} strata, {nb:,} listings)")
    print(f"  within category x Nutri-Score grade: {e:+.4f} p={p:.4f} ({k} strata, {n:,} listings)")
    print(f"  baseline restricted to exactly those {n:,} listings: {b2:+.4f} -> share retained after holding grade fixed {e / b2:.0%}")
for val, tag in (("valence", "N2"), ("arousal", "N2b")):
    r, p, k, n = grade_test(D, val); res[tag] = p
    print(f"\n== {tag} {val} vs Nutri-Score grade (A=1..E=5) within category x NOVA group: mean Spearman {r:+.3f}, two-sided p={p:.4f} ({k} strata, {n:,} listings)")
import sys; sys.path.insert(0, str(Path(__file__).parent)); from sold_on_joy import holm
print("\nHolm-adjusted:", dict(zip(res, np.round(holm(list(res.values())), 4))))
