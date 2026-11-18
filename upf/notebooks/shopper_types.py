"""Shopper types (upf/PLAN.md 'SHOPPER TYPES'): reviewer profiles over non-food sub-categories -> TF-IDF -> cosine kNN network -> Louvain types;
T1 = ALL-UPF share differs across types (chi-square, labels shuffled within activity strata).
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/shopper_types.py
"""
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
from scipy import sparse
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.preprocessing import normalize

C = Path("upf/data/processed/soj"); RNG = np.random.default_rng(1711); K = 10; MINREV = 5
E = pd.read_csv(C / "elsewhere_reviews.csv.gz", usecols=["user_id", "parent_asin"])
S = pd.read_csv(C / "all_subcategories.csv.gz", index_col=0)
E["cat"] = (S.dept.str.replace("_", " ").str.replace(" and ", " & ") + " > " + S["sub"]).reindex(E.parent_asin).values
E = E.dropna(subset=["cat"]); E = E[~E.cat.str.endswith("unknown")]
R = pd.read_csv(C / "reviewer_categories.csv.gz", usecols=["user_id", "upf", "stratum", "group"]).set_index("user_id")
n = E.groupby("user_id").size(); keep = n[n >= MINREV].index.intersection(R.index[R.group != "between"]); E = E[E.user_id.isin(keep)]
users = pd.Index(sorted(keep)); cats = pd.Index(sorted(E.cat.unique()))
X = sparse.csr_matrix((np.ones(len(E)), (users.get_indexer(E.user_id), cats.get_indexer(E.cat))), shape=(len(users), len(cats)))
print(f"reviewers kept (>= {MINREV} non-food reviews): {len(users):,} (ALL-UPF {(R.group[users] == 'ALL-UPF').sum():,}); sub-categories {len(cats)}; reviews {len(E):,}")
W = normalize(TfidfTransformer(sublinear_tf=True).fit_transform(X))           # down-weights categories nearly everyone reviews

rows, cols, vals = [], [], []                                                 # exact top-K cosine neighbours, in chunks
for s in range(0, W.shape[0], 4000):
    sim = (W[s:s + 4000] @ W.T).toarray(); np.fill_diagonal(sim[:, s:s + 4000], -1)
    idx = np.argpartition(-sim, K, axis=1)[:, :K]
    for i in range(idx.shape[0]):
        for j in idx[i]:
            if sim[i, j] > 0: rows.append(s + i); cols.append(j); vals.append(sim[i, j])
G = nx.Graph(); G.add_weighted_edges_from(zip(rows, cols, vals))
comm = sorted(nx.community.louvain_communities(G, weight="weight", seed=7, resolution=1.0), key=len, reverse=True)
print(f"kNN network: {G.number_of_nodes():,} reviewers, {G.number_of_edges():,} links; Louvain {len(comm)} types, modularity {nx.community.modularity(G, comm, weight='weight'):.3f}; sizes {[len(c) for c in comm[:15]]}")
lab = np.full(len(users), -1)
for k, c in enumerate(comm): lab[list(c)] = k
T = pd.DataFrame({"user_id": users, "type": lab, "upf": (R.group[users] == "ALL-UPF").values.astype(int), "stratum": R.stratum[users].values})
big = T.type.value_counts(); big = big[big >= 300].index; T["t"] = np.where(T.type.isin(big), T.type, -1)

# expected ALL-UPF share given activity strata
p_st = T.groupby("stratum").upf.mean(); T["exp"] = T.stratum.map(p_st)
def chi(lbl):
    ct = pd.crosstab(T.t, lbl).values.astype(float); ex = ct.sum(1, keepdims=True) * ct.sum(0, keepdims=True) / ct.sum(); return ((ct - ex) ** 2 / ex).sum()
obs = chi(T.upf); st = pd.factorize(T.stratum)[0]; null = np.empty(2000); y = T.upf.values
for b in range(2000):
    o = np.lexsort((RNG.random(len(y)), st)); yy = np.empty_like(y); yy[o] = y[o][np.argsort(RNG.random(len(o)))] if False else y[o]
    # shuffle within strata: permute y among positions sharing a stratum
    yy = y.copy()
    for g in np.unique(st): m = np.where(st == g)[0]; yy[m] = y[m][RNG.permutation(len(m))]
    null[b] = chi(yy)
print(f"\nT1: chi-square type x group {obs:.0f} vs null mean {null.mean():.0f} (95th pct {np.percentile(null, 95):.0f}); p = {(1 + (null >= obs).sum()) / 2001:.4f}")

base = W.mean(0).A1; out = []
for t in sorted(T.t.unique()):
    m = (T.t == t).values; prof = np.asarray(X[m].sum(0)).ravel(); share = prof / prof.sum(); allshare = np.asarray(X.sum(0)).ravel() / X.sum()
    lift = (share + 1e-4) / (allshare + 1e-4); top = [cats[i] for i in np.argsort(-lift) if prof[i] >= 0.02 * m.sum()][:6]
    common = [cats[i] for i in np.argsort(-share)[:4]]
    out.append(dict(type=t, reviewers=int(m.sum()), upf_share=T.upf[m].mean(), expected=T.exp[m].mean(), over=" | ".join(top), most_reviewed=" | ".join(common)))
O = pd.DataFrame(out); O["diff_pts"] = 100 * (O.upf_share - O.expected)
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 140)
print("\nTYPES (type -1 = all types under 300 reviewers), sorted by ALL-UPF share minus expected:")
for r in O.sort_values("diff_pts", ascending=False).itertuples():
    print(f"\n type {r.type:3d}  {r.reviewers:6,} reviewers  ALL-UPF {r.upf_share:.1%} (expected {r.expected:.1%}, {r.diff_pts:+.1f} pts)\n   over-represented: {r.over}\n   most reviewed:    {r.most_reviewed}")
T.to_csv(C / "shopper_types.csv.gz", index=False); O.to_csv(C / "shopper_types_summary.csv", index=False)
