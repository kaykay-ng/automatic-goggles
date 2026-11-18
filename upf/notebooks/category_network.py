"""CATEGORY CO-REVIEW NETWORK (exploratory, upf/PLAN.md 18 Nov): of those who reviewed food category X, which other Amazon categories (food and non-food) do they also review?
Reviewers: the 141,977 with >= 3 matched grocery reviews (soj/reviewer_categories.csv.gz). Nodes: Amazon grocery sub-categories (level 3) and non-food sub-categories
(soj/all_subcategories.csv.gz), each reviewed by >= 500 of these reviewers. Link weight: lift = P(reviewed both) / (P(a) P(b)); kept if lift > 1.2 and >= 50 shared reviewers.
Louvain (weight = log lift, seed 7) for clusters. Food nodes carry the UPF share of their matched reviews.
Writes soj/category_nodes.csv, soj/category_links.csv, data/processed/category_network.txt.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/category_network.py
"""
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
from scipy import sparse
from sklearn.metrics import adjusted_rand_score

C = Path("upf/data/processed/soj"); OUT = Path("upf/data/processed/category_network.txt"); MINREV, MINSHARED, MINLIFT = 500, 50, 1.2
log = []
def say(s=""): print(s, flush=True); log.append(s)

R = pd.read_csv(C / "reviewer_categories.csv.gz", usecols=["user_id"]); users = pd.Index(R.user_id.unique())
G = pd.read_csv(C / "reviewer_pairs.csv.gz").drop_duplicates(); G = G[G.user_id.isin(users)]
P = pd.read_csv(C / "products.csv.gz", usecols=["parent_asin", "nova"]).drop_duplicates("parent_asin").set_index("parent_asin").nova
M = pd.read_csv("upf/data/processed/amazon_meta_compact.csv.gz", usecols=["parent_asin", "categories"]).drop_duplicates("parent_asin").set_index("parent_asin").categories
lv = M.reindex(G.parent_asin).fillna("").str.split("|").values
G["node"] = ["Food > " + x[2] if len(x) > 2 and x[2] else None for x in lv]; G["upf"] = P.reindex(G.parent_asin).values == 4
E = pd.read_csv(C / "elsewhere_reviews.csv.gz", usecols=["user_id", "parent_asin"]); E = E[E.user_id.isin(users)]
S = pd.read_csv(C / "all_subcategories.csv.gz", index_col=0)
short = {"Health_and_Household": "H&H", "Pet_Supplies": "Pets", "Toys_and_Games": "Toys", "Video_Games": "Video Games", "Sports_and_Outdoors": "Sports",
         "Baby_Products": "Baby", "Health_and_Personal_Care": "Personal Care"}
E["node"] = (S.dept.map(short) + " > " + S["sub"]).reindex(E.parent_asin).values; E = E.dropna(subset=["node"]); E = E[~E.node.str.endswith("unknown")]
A = pd.concat([G[["user_id", "node"]].dropna(), E[["user_id", "node"]]]).drop_duplicates()
PROMO = ("Subscribe", "Event", "Top ", "Prime Day", "Featured", "SNAP", "Low Return", "Stocking", "Buy $", "Redeem", "Genre of the Month")
A = A[~A.node.str.contains("|".join(map(__import__("re").escape, PROMO)))]
size = A.node.value_counts(); keep = size[size >= MINREV].index; A = A[A.node.isin(keep)]
nodes = pd.Index(sorted(keep)); ui = users.get_indexer(A.user_id)
X = sparse.csr_matrix((np.ones(len(A), np.float32), (ui, nodes.get_indexer(A.node))), shape=(len(users), len(nodes)))
N = len(users); co = (X.T @ X).toarray(); n = np.diag(co).copy(); lift = co * N / np.outer(n, n)
say(f"reviewers {N:,}; nodes {len(nodes)} ({sum(x.startswith('Food') for x in nodes)} food, {sum(not x.startswith('Food') for x in nodes)} non-food), each reviewed by >= {MINREV}")
ups = G.dropna(subset=["node"]).groupby("node").upf.mean()
ND = pd.DataFrame({"node": nodes, "reviewers": n.astype(int), "food": [x.startswith("Food") for x in nodes], "upf_share": ups.reindex(nodes).values})
iu = np.triu_indices(len(nodes), 1)
L = pd.DataFrame({"a": nodes[iu[0]], "b": nodes[iu[1]], "shared": co[iu].astype(int), "lift": lift[iu]})
Lk = L[(L.lift > MINLIFT) & (L.shared >= MINSHARED)]
say(f"links with lift > {MINLIFT} and >= {MINSHARED} shared reviewers: {len(Lk):,} of {len(L):,} pairs")
H = nx.Graph(); H.add_nodes_from(nodes)
H.add_weighted_edges_from(zip(Lk.a, Lk.b, np.log(Lk.lift)))
com = sorted(nx.community.louvain_communities(H, weight="weight", seed=7), key=len, reverse=True)
mod = nx.community.modularity(H, com, weight="weight"); say(f"Louvain: {len(com)} clusters, modularity {mod:.3f}")
cid = {x: c for c, m in enumerate(com) for x in m}; ND["cluster"] = ND.node.map(cid)
# stability: 10 seeds, share of node pairs that stay together
same = []
base = ND.cluster.values
for sd in range(10):
    cm = nx.community.louvain_communities(H, weight="weight", seed=100 + sd); cc = {x: c for c, m in enumerate(cm) for x in m}; lab = ND.node.map(cc).values
    from sklearn.metrics import adjusted_rand_score; same.append(adjusted_rand_score(base, lab))
say(f"stability over 10 other seeds: adjusted Rand {np.mean(same):.2f} (min {np.min(same):.2f})")
for c, m in enumerate(com):
    d = ND[ND.node.isin(m)]; f = d[d.food]; nf = d[~d.food]
    wup = (f.upf_share * f.reviewers).sum() / f.reviewers.sum() if len(f) else np.nan
    say(f"\n[cluster {c}] {len(d)} nodes: {len(f)} food (UPF share of their reviews {wup:.0%}), {len(nf)} non-food")
    say("  food: " + "; ".join(f"{x[7:]} ({u:.0%})" for x, u in zip(f.sort_values('reviewers', ascending=False).node, f.sort_values('reviewers', ascending=False).upf_share)))
    say("  non-food: " + "; ".join(nf.sort_values("reviewers", ascending=False).node.head(25)))
say("\nEach food category's 5 most over-represented NON-FOOD categories (lift, shared reviewers >= 50):")
nf_nodes = ND[~ND.food].node.values
for fnode in ND[ND.food].sort_values("reviewers", ascending=False).node.head(30):
    s = L[((L.a == fnode) & L.b.isin(nf_nodes)) | ((L.b == fnode) & L.a.isin(nf_nodes))].copy(); s["other"] = np.where(s.a == fnode, s.b, s.a)
    s = s[s.shared >= MINSHARED].sort_values("lift", ascending=False).head(5)
    u = ND.set_index("node").upf_share[fnode]
    say(f"  {fnode[7:]:40s} (UPF {u:.0%}): " + ", ".join(f"{o} {l:.1f}x" for o, l in zip(s.other, s.lift)))

# ---- B. bipartite: food x non-food, against people with the same number of non-food categories (activity strata 0 / 1-2 / 3-5 / 6-10 / 11-20 / 21-40 / 41+)
RNG = np.random.default_rng(18); fd = ND.food.values; F, NF = np.where(fd)[0], np.where(~fd)[0]
Xf, Xn = X[:, F].tocsc(), X[:, NF].tocoo(); obs = (Xf.T @ X[:, NF]).toarray()
kn = np.asarray(X[:, NF].sum(1)).ravel()                                  # number of non-food categories each reviewer reviewed
st = np.digitize(kn, [1, 3, 6, 11, 21, 41]); Sm = sparse.csr_matrix((np.ones(len(st)), (np.arange(len(st)), st)), shape=(len(st), st.max() + 1))
pnf = (Sm.T @ X[:, NF]).toarray() / np.maximum(np.asarray(Sm.sum(0)).ravel()[:, None], 1)   # P(non-food category | activity stratum)
null = (Xf.T @ Sm).toarray() @ pnf                                         # expected shared reviewers if food reviewers behaved like others of the same activity
rel = obs / np.maximum(null, 1e-9)
say(f"\n== B. food x non-food: observed shared reviewers relative to reviewers with the same number of non-food categories ==")
say(f"  {len(F)} food x {len(NF)} non-food = {obs.size:,} pairs; relative > 1.25 with >= {MINSHARED} shared: {((rel > 1.25) & (obs >= MINSHARED)).sum():,}; < 0.8: {((rel < 0.8) & (obs >= MINSHARED)).sum():,}")
BG = nx.Graph()
for a_, b_ in zip(*np.where((rel > 1.15) & (obs >= MINSHARED))): BG.add_edge(nodes[F[a_]], nodes[NF[b_]], weight=float(np.log(rel[a_, b_])))
bcom = sorted(nx.community.louvain_communities(BG, weight="weight", seed=7), key=len, reverse=True)
say(f"  bipartite Louvain (links relative > 1.15): {len(bcom)} clusters, modularity {nx.community.modularity(BG, bcom, weight='weight'):.3f}")
aris = []
for sd in range(10):
    cm = nx.community.louvain_communities(BG, weight="weight", seed=200 + sd); cc = {x: c for c, m in enumerate(cm) for x in m}; c0 = {x: c for c, m in enumerate(bcom) for x in m}
    ks = list(c0); aris.append(adjusted_rand_score([c0[x] for x in ks], [cc[x] for x in ks]))
say(f"  stability over 10 seeds: adjusted Rand {np.mean(aris):.2f} (min {np.min(aris):.2f})")
ups_ = ND.set_index("node").upf_share; rv = ND.set_index("node").reviewers; bc = {}
for c, m in enumerate(bcom):
    f = sorted([x for x in m if x.startswith("Food")], key=lambda x: -rv[x]); nf = sorted([x for x in m if not x.startswith("Food")], key=lambda x: -rv[x])
    wup = sum(ups_[x] * rv[x] for x in f) / max(1, sum(rv[x] for x in f))
    for x in m: bc[x] = c
    say(f"\n  [B{c}] {len(f)} food (UPF share {wup:.0%}) + {len(nf)} non-food")
    say("    food: " + "; ".join(f"{x[7:]} ({ups_[x]:.0%})" for x in f[:18]))
    say("    non-food: " + "; ".join(nf[:18]))
ND["bicluster"] = ND.node.map(bc)
say("\nEach food category's 5 most over-represented non-food categories vs reviewers of the same activity (>= 50 shared):")
for fi in np.argsort(-n[F])[:30]:
    r = rel[fi].copy(); r[obs[fi] < MINSHARED] = 0; top = np.argsort(-r)[:5]
    say(f"  {nodes[F[fi]][7:]:38s} (UPF {ups_[nodes[F[fi]]]:.0%}): " + ", ".join(f"{nodes[NF[t]]} {r[t]:.2f}x" for t in top))
pd.DataFrame(rel, index=nodes[F], columns=nodes[NF]).round(3).to_csv(C / "category_food_nonfood_rel.csv")
ND.to_csv(C / "category_nodes.csv", index=False); L.to_csv(C / "category_links.csv", index=False); OUT.write_text("\n".join(log) + "\n"); print("saved", OUT)
