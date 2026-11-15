"""EXPLORATORY: ingredient co-occurrence network of Open Food Facts products, with centrality and communities.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/ingredient_network.py
Steps:
 1. product x tag incidence (tags seen in >= 200 products);
 2. PARENT TAGS inferred from the data: P is treated as a parent of T if P appears in >= 99.5% of products containing T and P is at least 1.2x as common as T
    (e.g. sugar -> added-sugar, hazelnut -> tree-nut -> nut); a product's parent tags are dropped when a child is present, so each product keeps its most specific ingredients;
 3. nodes = ingredients in >= 1,000 products (after step 2); edge weight = number of products containing both;
 4. backbone = disparity filter (Serrano et al. 2009; alpha = 0.01, kept if significant for either end);
 5. centrality on the backbone (degree, weighted degree, eigenvector, betweenness) and Louvain communities; NOVA-4 share of each ingredient's products.
Also builds the same network separately for NOVA 4 products and NOVA 1-3 products to compare who is central.
"""
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
from scipy import sparse

PROC = Path("upf/data/processed")
D = pd.read_csv(PROC / "off_products.csv.gz", usecols=["code", "nova", "tags"])
T = D.tags.str.split(",")
vc = pd.Series([t for ts in T for t in ts]).value_counts(); vocab = vc[vc >= 200].index.tolist(); vid = {t: i for i, t in enumerate(vocab)}
rows, cols = [], []
for r, ts in enumerate(T):
    for t in ts:
        j = vid.get(t)
        if j is not None: rows.append(r); cols.append(j)
X = sparse.csr_matrix((np.ones(len(rows), np.float32), (rows, cols)), shape=(len(D), len(vocab)))
cnt = np.asarray(X.sum(0)).ravel()
print(f"products {len(D):,}; tags in >= 200 products: {len(vocab):,}", flush=True)

# ---- 2. parents from data ----
C = (X.T @ X).toarray()
cond = C / cnt[:, None]                             # cond[t, p] = share of t's products that also contain p
par = (cond >= 0.995) & (cnt[None, :] >= 1.2 * cnt[:, None]); np.fill_diagonal(par, False)
is_parent_of = {vocab[p]: set() for p in range(len(vocab))}
for t, p in zip(*np.where(par)): is_parent_of[vocab[p]].add(vocab[t])
n_par = sum(1 for v in is_parent_of.values() if v)
print(f"tags acting as a parent of at least one other tag: {n_par}")
ex = sorted([(p, len(c)) for p, c in is_parent_of.items() if c], key=lambda x: -x[1])[:15]
print("  biggest parents (number of children):", ex)
for t in ["en:hazelnut", "en:sugar", "en:sunflower-oil", "en:e322", "en:whole-milk-powder", "en:carbonated-water"]:
    if t in vid: print(f"  parents of {t}: {[vocab[p] for p in np.where(par[vid[t]])[0]]}")
parents_by_child = {vocab[t]: {vocab[p] for p in np.where(par[t])[0]} for t in range(len(vocab))}
leaf = [[t for t in ts if t in vid and not any(t in parents_by_child.get(o, ()) for o in ts if o != t)] for ts in T]
D["leaf"] = [",".join(l) for l in leaf]
print(f"median tags per product: before {int(T.str.len().median())}, after dropping parents {int(np.median([len(l) for l in leaf]))}")

# ---- 3-5. networks ----
def build(mask, label, min_products=1000):
    L = [l for l, m in zip(leaf, mask) if m]
    v2 = pd.Series([t for l in L for t in l]).value_counts(); nodes = v2[v2 >= min_products].index.tolist(); ix = {t: i for i, t in enumerate(nodes)}
    r, c = [], []
    for k, l in enumerate(L):
        for t in l:
            if t in ix: r.append(k); c.append(ix[t])
    Y = sparse.csr_matrix((np.ones(len(r), np.float32), (r, c)), shape=(len(L), len(nodes)))
    W = (Y.T @ Y).toarray(); np.fill_diagonal(W, 0); n_i = v2[nodes].values
    s = W.sum(1); k = (W > 0).sum(1); keep = np.zeros_like(W, bool)
    for i in range(len(nodes)):
        p = W[i] / s[i]; a = (1 - p) ** (k[i] - 1); keep[i] = (a < 0.01) & (W[i] > 0)
    keep = keep | keep.T
    G = nx.Graph(); G.add_nodes_from(range(len(nodes)))
    for i, j in zip(*np.where(np.triu(keep, 1))): G.add_edge(i, j, weight=float(W[i, j]), dist=1.0 / W[i, j])
    nova4 = None
    if label == "all":
        nv = np.array([n for n, m in zip(D.nova.values, mask) if m]); nova4 = np.asarray((Y.T @ sparse.csr_matrix((nv == 4).astype(np.float32)).T).todense()).ravel() / n_i
    eig = nx.eigenvector_centrality_numpy(G, weight="weight"); btw = nx.betweenness_centrality(G, weight="dist", k=min(400, len(nodes)), seed=1)
    comm = sorted(nx.community.louvain_communities(G, weight="weight", seed=42), key=len, reverse=True); lab = {}
    for ci, m in enumerate(comm):
        for i in m: lab[i] = ci
    N = pd.DataFrame({"ingredient": [t.replace("en:", "") for t in nodes], "n_products": n_i, "degree": [G.degree(i) for i in range(len(nodes))],
                      "strength": [G.degree(i, weight="weight") for i in range(len(nodes))], "eigenvector": [eig[i] for i in range(len(nodes))],
                      "betweenness": [btw[i] for i in range(len(nodes))], "community": [lab[i] for i in range(len(nodes))]})
    if nova4 is not None: N["nova4_share"] = nova4.round(3)
    print(f"\n== {label}: {len(L):,} products, {len(nodes)} ingredients (>= {min_products} products), backbone {G.number_of_edges()} edges of {int((W > 0).sum() / 2)}; "
          f"{len(comm)} communities, modularity {nx.community.modularity(G, comm, weight='weight'):.3f}")
    return N, G, nodes


N, G, nodes = build(np.ones(len(D), bool), "all")
N.to_csv(PROC / "ingredient_nodes.csv", index=False)
nx.write_weighted_edgelist(nx.relabel_nodes(G, {i: t.replace("en:", "") for i, t in enumerate(nodes)}), PROC / "ingredient_backbone_edges.txt")
pd.set_option("display.width", 220)
print("\nTOP 25 by eigenvector centrality (all products):"); print(N.sort_values("eigenvector", ascending=False).head(25).round(3).to_string(index=False))
print("\nTOP 15 by betweenness (bridges):"); print(N.sort_values("betweenness", ascending=False).head(15)[["ingredient", "n_products", "degree", "betweenness", "nova4_share"]].round(3).to_string(index=False))
print("\nCOMMUNITIES (largest members by products):")
for c, g in N.groupby("community"):
    print(f"  {c} ({len(g)}; median NOVA-4 share {g.nova4_share.median():.2f}): " + ", ".join(g.sort_values("n_products", ascending=False).ingredient.head(12)))
N4, _, _ = build(D.nova.values == 4, "NOVA 4 (ultra-processed)")
N13, _, _ = build(D.nova.values < 4, "NOVA 1-3")
for nm, M in [("NOVA 4", N4), ("NOVA 1-3", N13)]:
    print(f"\nTOP 20 by eigenvector centrality, {nm}: " + ", ".join(M.sort_values("eigenvector", ascending=False).ingredient.head(20)))
only4 = set(N4.sort_values("eigenvector", ascending=False).ingredient.head(50)) - set(N13.sort_values("eigenvector", ascending=False).ingredient.head(50))
print(f"\nin the top-50 central of NOVA 4 but not of NOVA 1-3: {sorted(only4)}")
N4.to_csv(PROC / "ingredient_nodes_nova4.csv", index=False); N13.to_csv(PROC / "ingredient_nodes_nova123.csv", index=False)
