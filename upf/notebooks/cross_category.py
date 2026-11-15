"""H5 'Who are the ultra-processed shoppers?' -- pre-declared in upf/PLAN.md 'CROSS-CATEGORY REVIEWERS'. Pseudonymous reviewer IDs only; aggregate results; no profile data.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/cross_category.py
"""
import gzip, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

PROC = Path("upf/data/processed"); CACHE = PROC / "soj"; OTHER = Path("upf/data/raw/amazon/other"); RNG = np.random.default_rng(55)
CATS = ["Video_Games", "Toys_and_Games", "Sports_and_Outdoors", "Health_and_Household", "Baby_Products", "Pet_Supplies", "Health_and_Personal_Care"]
TESTS = [("Video_Games", "greater"), ("Toys_and_Games", "greater"), ("Sports_and_Outdoors", "less"), ("Health_and_Household", "less"), ("Baby_Products", "two")]

P = pd.read_csv(CACHE / "products.csv.gz", usecols=["parent_asin", "nova"]); nova = dict(zip(P.parent_asin, P.nova))
pr = pd.read_csv(CACHE / "reviewer_pairs.csv.gz").drop_duplicates(); pr["u4"] = pr.parent_asin.map(nova).eq(4)
R = pr.groupby("user_id").agg(n=("u4", "size"), upf=("u4", "mean")); R = R[R.n >= 3].copy()
R["stratum"] = pd.cut(R.n, [2, 3, 4, 9, 10 ** 6], labels=["3", "4", "5-9", "10+"])
R["group"] = np.where(R.upf == 1.0, "ALL-UPF", np.where(R.upf <= 0.5, "MOSTLY-NOT", "between"))
print(f"reviewers with >= 3 matched grocery reviews: {len(R):,}; ALL-UPF {(R.group == 'ALL-UPF').sum():,}, MOSTLY-NOT {(R.group == 'MOSTLY-NOT').sum():,}, between {(R.group == 'between').sum():,}")
print("strata sizes:", R.stratum.value_counts().sort_index().to_dict())
users = set(R.index)
for c in CATS:
    seen = set()
    with gzip.open(OTHER / f"{c}.jsonl.gz", "rt") as f:
        for line in f:
            i = line.find('"user_id": "')
            uid = line[i + 12: line.find('"', i + 12)] if i >= 0 else json.loads(line).get("user_id")
            if uid in users: seen.add(uid)
    R[c] = R.index.isin(seen); print(f"  {c:26s}: {len(seen):,} of our reviewers ({len(seen) / len(R):.1%})", flush=True)
R.drop(columns=[]).to_csv(CACHE / "reviewer_categories.csv.gz")

G = R[R.group != "between"].copy(); G["is_upf"] = G.group == "ALL-UPF"; st = pd.factorize(G.stratum)[0]


def stat(lab, y):
    d, wsum = 0.0, 0.0
    for s in np.unique(st):
        m = st == s; a, b = lab[m], y[m]
        if a.sum() == 0 or (~a).sum() == 0: continue
        w = m.sum(); d += w * (b[a].mean() - b[~a].mean()); wsum += w
    return d / wsum


def shuffle_within(lab):
    out = lab.copy()
    for s in np.unique(st):
        m = np.where(st == s)[0]; out[m] = RNG.permutation(lab[m])
    return out


print("\n== H5 (ALL-UPF minus MOSTLY-NOT, difference in % reviewing in the category, weighted over activity strata; 2,000 shuffles within strata) ==")
lab = G.is_upf.values; res = []
for c, side in TESTS + [("Pet_Supplies", "two"), ("Health_and_Personal_Care", "two")]:
    y = G[c].values.astype(float); obs = stat(lab, y); null = np.array([stat(shuffle_within(lab), y) for _ in range(2000)])
    p = {"greater": (1 + (null >= obs).sum()) / 2001, "less": (1 + (null <= obs).sum()) / 2001, "two": (1 + (np.abs(null) >= abs(obs)).sum()) / 2001}[side]
    res.append((c, side, obs, p, 100 * G[G.is_upf][c].mean(), 100 * G[~G.is_upf][c].mean()))
ps = np.array([r[3] for r in res[:5]]); o = np.argsort(ps); adj = np.empty(5); run = 0
for r_, i in enumerate(o): run = max(run, (5 - r_) * ps[i]); adj[i] = min(run, 1)
for k, (c, side, obs, p, a, b) in enumerate(res):
    tag = f"Holm p = {adj[k]:.4f}" if k < 5 else "descriptive"
    print(f"  {c:26s} ({side:7s}) difference {100 * obs:+.2f} points; raw rates ALL-UPF {a:.1f}% vs MOSTLY-NOT {b:.1f}%; p = {p:.4f}; {tag}")
print("\n== ROBUSTNESS ==")
R["n_cats"] = R[CATS].sum(1)
rho = stats.spearmanr(R.upf, R.n_cats)[0]; print(f"  continuous UPF share vs number of the 7 categories reviewed (all {len(R):,} reviewers): Spearman {rho:+.3f}")
for c in CATS: print(f"    UPF share vs reviewing {c:26s}: Spearman {stats.spearmanr(R.upf, R[c])[0]:+.3f}")
Gs = G[G.n <= 50]; lab2 = Gs.is_upf.values; st_backup = st; st = pd.factorize(Gs.stratum)[0]
print(f"  network-filter reviewers only (3-50 matched reviews, n={len(Gs):,}):")
for c, side in TESTS:
    y = Gs[c].values.astype(float); print(f"    {c:26s}: {100 * stat(lab2, y):+.2f} points")
