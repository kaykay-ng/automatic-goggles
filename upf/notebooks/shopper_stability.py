"""Stability of SHOPPER TYPES (upf/PLAN.md 'SHOPPER TYPES STABILITY CHECK'): re-run with other minimum-review cut-offs, k and Louvain resolution.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/shopper_stability.py
"""
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
from scipy import sparse, stats
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.preprocessing import normalize

C = Path("upf/data/processed/soj"); RNG = np.random.default_rng(1811)
E0 = pd.read_csv(C / "elsewhere_reviews.csv.gz", usecols=["user_id", "parent_asin"])
S = pd.read_csv(C / "all_subcategories.csv.gz", index_col=0)
E0["cat"] = (S.dept + " > " + S["sub"]).reindex(E0.parent_asin).values
E0 = E0.dropna(subset=["cat"]); E0 = E0[~E0.cat.str.endswith("unknown")]
R = pd.read_csv(C / "reviewer_categories.csv.gz", usecols=["user_id", "stratum", "group"]).set_index("user_id"); R = R[R.group != "between"]
n_all = E0.groupby("user_id").size()


def run(minrev, k, res):
    keep = n_all[n_all >= minrev].index.intersection(R.index); E = E0[E0.user_id.isin(keep)]
    users = pd.Index(sorted(keep)); cats = pd.Index(sorted(E.cat.unique()))
    X = sparse.csr_matrix((np.ones(len(E)), (users.get_indexer(E.user_id), cats.get_indexer(E.cat))), shape=(len(users), len(cats)))
    W = normalize(TfidfTransformer(sublinear_tf=True).fit_transform(X)); rows, cols, vals = [], [], []
    for s in range(0, W.shape[0], 4000):
        sim = (W[s:s + 4000] @ W.T).toarray(); np.fill_diagonal(sim[:, s:s + 4000], -1); idx = np.argpartition(-sim, k, axis=1)[:, :k]
        r_ = np.repeat(np.arange(idx.shape[0]), k); c_ = idx.ravel(); v_ = sim[r_, c_]; ok = v_ > 0
        rows += list(s + r_[ok]); cols += list(c_[ok]); vals += list(v_[ok])
    G = nx.Graph(); G.add_weighted_edges_from(zip(rows, cols, vals))
    comm = sorted(nx.community.louvain_communities(G, weight="weight", seed=7, resolution=res), key=len, reverse=True)
    lab = np.full(len(users), -1)
    for i, c in enumerate(comm): lab[list(c)] = i
    T = pd.DataFrame({"type": lab, "upf": (R.group[users] == "ALL-UPF").values.astype(int), "stratum": R.stratum[users].values}, index=users)
    big = T.type.value_counts(); T["t"] = np.where(T.type.isin(big[big >= 300].index), T.type, -1)
    T["exp"] = T.stratum.map(T.groupby("stratum").upf.mean())
    g = T.groupby("t").agg(obs=("upf", "mean"), exp=("exp", "mean")); T["diff"] = T.t.map(100 * (g.obs - g.exp))
    def chi(y):
        ct = pd.crosstab(T.t.values, y).values.astype(float); ex = ct.sum(1, keepdims=True) * ct.sum(0, keepdims=True) / ct.sum(); return ((ct - ex) ** 2 / ex).sum()
    y = T.upf.values; st = pd.factorize(T.stratum)[0]; grp = [np.where(st == v)[0] for v in np.unique(st)]; obs = chi(y); null = []
    for _ in range(500):
        yy = y.copy()
        for m in grp: yy[m] = y[m][RNG.permutation(len(m))]
        null.append(chi(yy))
    return T, len(users), len(comm), nx.community.modularity(G, comm, weight="weight"), obs, np.mean(null), (1 + np.sum(np.array(null) >= obs)) / 501


base = pd.read_csv(C / "shopper_types.csv.gz").set_index("user_id")
ANCHOR = {17: "collectors (+)", 3: "gamers (+)", 0: "toy builders (+)", 8: "sports nutrition (-)", 10: "wellness (-)", 2: "outdoors (-)"}
SIGN = {17: 1, 3: 1, 0: 1, 8: -1, 10: -1, 2: -1}
SETTINGS = [(5, 10, 1.0), (3, 10, 1.0), (10, 10, 1.0), (20, 10, 1.0), (5, 5, 1.0), (5, 20, 1.0), (5, 10, 0.5), (5, 10, 2.0)]
rows = []; Tb = None
for mr, k, res in SETTINGS:
    T, n, nt, mod, obs, nm, p = run(mr, k, res)
    if (mr, k, res) == (5, 10, 1.0): Tb = T
    common = T.index.intersection(Tb.index); rho = stats.spearmanr(Tb.loc[common, "diff"], T.loc[common, "diff"])[0]
    an = {}
    for b, nmn in ANCHOR.items():
        mem = base.index[base.type == b].intersection(T.index)
        if len(mem) == 0: an[nmn] = np.nan; continue
        tt = T.loc[mem, "t"].value_counts().index[0]; an[nmn] = T.loc[T.t == tt, "diff"].iloc[0]
    ok = (p < .01) and all(np.sign(an[ANCHOR[b]]) == SIGN[b] for b in ANCHOR if not np.isnan(an[ANCHOR[b]])) and rho >= .5
    rows.append(dict(min_reviews=mr, k=k, resolution=res, reviewers=n, types=nt, modularity=round(mod, 3), chi2=round(obs), null_chi2=round(nm), p=round(p, 4),
                     spearman_vs_base=round(rho, 2), **{a: round(v, 1) for a, v in an.items()}, holds=ok))
    print(rows[-1], flush=True)
O = pd.DataFrame(rows); O.to_csv(C / "shopper_stability.csv", index=False)
pd.set_option("display.width", 250); print("\n" + O.to_string(index=False)); print(f"\nPATTERN HOLDS IN ALL SETTINGS: {bool(O.holds.all())}")
