"""EXPLORATORY: ingredient co-occurrence network of the Amazon-matched Open Food Facts products (58,051 barcodes with NOVA), from the PARSED ingredient text, + communities.
Run from final_project/:  ./.venv-nlp/bin/python upf/notebooks/matched_ingredient_network.py
Input: soj/matched_ingredients_long.csv.gz (matched_ingredient_parse.py).
 1. nodes = ingredients in >= 50 products; edge weight = number of products listing both;
 2. backbone = disparity filter (Serrano et al. 2009; alpha = 0.01, kept if significant for either end) -- same rule as ingredient_network.py;
 3. Louvain (weighted) over 20 seeds: best-modularity partition kept; stability = mean adjusted Rand between seeds;
 4. null: modularity of Louvain on 20 degree-preserving rewirings of the (unweighted) backbone vs the observed unweighted modularity;
 5. communities described by most common ingredients, most 'own' ingredients (share of strength inside), and NOVA: (a) median NOVA-4 share of members' products,
    (b) products assigned to the community holding most of their ingredients -> NOVA mix.
Writes data/processed/matched_ingredient_network.txt, soj/matched_ingredient_nodes.csv, soj/matched_ingredient_edges.csv.gz, soj/matched_ingredient_communities.csv.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
from scipy import sparse
from sklearn.metrics import adjusted_rand_score

PROC = Path("upf/data/processed"); SOJ = PROC / "soj"; MIN_PRODUCTS = 50; ALPHA = 0.01
out = open(PROC / "matched_ingredient_network.txt", "w")
def say(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); out.write(s + "\n")

L = pd.read_csv(SOJ / "matched_ingredients_long.csv.gz", dtype={"code13": str})
L["nova"] = L.nova.astype(float).astype(int)
vc = L.ingredient.value_counts(); nodes = vc[vc >= MIN_PRODUCTS].index.tolist(); ix = {t: i for i, t in enumerate(nodes)}
K = L[L.ingredient.isin(ix)].copy(); prods = K.code13.unique(); pix = {c: i for i, c in enumerate(prods)}
Y = sparse.csr_matrix((np.ones(len(K), np.float32), (K.code13.map(pix), K.ingredient.map(ix))), shape=(len(prods), len(nodes)))
pnova = K.drop_duplicates("code13").set_index("code13").nova.reindex(prods).values
n_i = np.asarray(Y.sum(0)).ravel(); nova4 = np.asarray(Y[pnova == 4].sum(0)).ravel() / n_i
say(f"products with NOVA and a parsed list: {L.code13.nunique():,} (NOVA 4 share {(L.drop_duplicates('code13').nova == 4).mean():.2f}); distinct ingredients {len(vc):,}")
say(f"nodes: {len(nodes):,} ingredients in >= {MIN_PRODUCTS} products; they cover {len(prods):,} products, "
    f"{len(K) / len(L):.0%} of all product-ingredient mentions")

# ---- 1-2. co-occurrence + disparity backbone ----
W = (Y.T @ Y).toarray(); np.fill_diagonal(W, 0)
s = W.sum(1); k = (W > 0).sum(1); keep = np.zeros_like(W, bool)
for i in range(len(nodes)):
    p = W[i] / s[i]; keep[i] = ((1 - p) ** (k[i] - 1) < ALPHA) & (W[i] > 0)
keep = keep | keep.T
G = nx.Graph(); G.add_nodes_from(range(len(nodes)))
for i, j in zip(*np.where(np.triu(keep, 1))): G.add_edge(int(i), int(j), weight=float(W[i, j]))
iso = [n for n in G if G.degree(n) == 0]
say(f"co-occurrence links {int((W > 0).sum() / 2):,} (density {(W > 0).sum() / (len(nodes) * (len(nodes) - 1)):.2f}); "
    f"backbone {G.number_of_edges():,} links, {len(iso)} isolated ingredients; giant component {len(max(nx.connected_components(G), key=len)):,}")
G.remove_nodes_from(iso)

# ---- 3. Louvain over seeds ----
parts = []
for seed in range(20):
    c = nx.community.louvain_communities(G, weight="weight", seed=seed); parts.append((nx.community.modularity(G, c, weight="weight"), seed, c))
order = list(G.nodes())
labs = [{n: ci for ci, m in enumerate(c) for n in m} for _, _, c in parts]
ari = [adjusted_rand_score([a[n] for n in order], [b[n] for n in order]) for x, a in enumerate(labs) for b in labs[x + 1:]]
Q, seed, comm = max(parts, key=lambda x: x[0]); comm = sorted(comm, key=len, reverse=True)
say(f"Louvain (weighted): best of 20 seeds modularity {Q:.3f} (range {min(p[0] for p in parts):.3f}-{max(p[0] for p in parts):.3f}); "
    f"{len(comm)} communities, sizes {[len(c) for c in comm]}; stability adjusted Rand mean {np.mean(ari):.2f} (min {np.min(ari):.2f})")

# ---- 4. null: degree-preserving rewiring ----
Gu = nx.Graph(G.edges()); Qu = nx.community.modularity(Gu, nx.community.louvain_communities(Gu, seed=0))
null = []
for r in range(20):
    R = Gu.copy(); nx.double_edge_swap(R, nswap=4 * R.number_of_edges(), max_tries=40 * R.number_of_edges(), seed=r)
    null.append(nx.community.modularity(R, nx.community.louvain_communities(R, seed=0)))
say(f"null (unweighted backbone, 20 degree-preserving rewirings): observed modularity {Qu:.3f} vs null {np.mean(null):.3f} (sd {np.std(null):.3f}, max {np.max(null):.3f})")

# ---- 5. describe ----
lab = {n: ci for ci, m in enumerate(comm) for n in m}
strength = dict(G.degree(weight="weight"))
inside = {n: sum(d["weight"] for _, m, d in G.edges(n, data=True) if lab[m] == lab[n]) / strength[n] for n in G}
N = pd.DataFrame({"ingredient": [nodes[n] for n in G], "n_products": [int(n_i[n]) for n in G], "nova4_share": [round(nova4[n], 3) for n in G],
                  "community": [lab[n] for n in G], "degree": [G.degree(n) for n in G], "strength": [strength[n] for n in G],
                  "share_inside": [round(inside[n], 3) for n in G]})
N.to_csv(SOJ / "matched_ingredient_nodes.csv", index=False)
pd.DataFrame([(nodes[a], nodes[b], d["weight"]) for a, b, d in G.edges(data=True)], columns=["a", "b", "products"]).to_csv(SOJ / "matched_ingredient_edges.csv.gz", index=False)

# product -> community holding most of its (node) ingredients
nidx = np.array([lab.get(i, -1) for i in range(len(nodes))])
M = np.zeros((len(prods), len(comm)), np.float32); Yc = Y.tocoo()
np.add.at(M, (Yc.row[nidx[Yc.col] >= 0], nidx[Yc.col][nidx[Yc.col] >= 0]), 1)
has = M.sum(1) > 0; pc = np.where(has, M.argmax(1), -1); purity = np.where(has, M.max(1) / np.maximum(M.sum(1), 1), np.nan)
say(f"products assigned to the community holding most of their ingredients: {has.sum():,}; median share of a product's ingredients in its community {np.nanmedian(purity):.2f}")

rows = []
say("\nCOMMUNITIES (most common members | most 'own' members = share of link weight inside the community, among >= 200 products):")
for ci, m in enumerate(comm):
    g = N[N.community == ci]; pm = pc == ci; nv = pnova[pm]
    common = ", ".join(g.sort_values("n_products", ascending=False).ingredient.head(14))
    own = ", ".join(g[g.n_products >= 200].sort_values("share_inside", ascending=False).ingredient.head(10))
    mix = {v: round(float((nv == v).mean()), 2) for v in (1, 2, 3, 4)} if pm.sum() else {}
    rows.append({"community": ci, "n_ingredients": len(g), "n_products_assigned": int(pm.sum()), "median_nova4_share_of_members": round(g.nova4_share.median(), 2),
                 "products_nova4_share": mix.get(4), "products_nova1_share": mix.get(1), "most_common": common, "most_own": own})
    say(f"\n C{ci}: {len(g)} ingredients; members' median NOVA-4 share {g.nova4_share.median():.2f}; products assigned {pm.sum():,} (NOVA mix {mix})")
    say(f"   common: {common}"); say(f"   own:    {own}")
pd.DataFrame(rows).to_csv(SOJ / "matched_ingredient_communities.csv", index=False)

# ---- 6. second level: Louvain inside each community with >= 100 ingredients (the top level lumps a lot together) ----
say("\nSECOND LEVEL (Louvain inside each community of >= 100 ingredients, seed 0):")
N["sub"] = N.community.astype(str); name2n = {nodes[n]: n for n in G}
for ci, m in enumerate(comm):
    if len(m) < 100: continue
    S = G.subgraph(m); sub = sorted(nx.community.louvain_communities(S, weight="weight", seed=0), key=len, reverse=True)
    say(f" C{ci}: {len(sub)} sub-communities, modularity within {nx.community.modularity(S, sub, weight='weight'):.3f}")
    for si, sm in enumerate(sub):
        g = N[N.ingredient.isin([nodes[n] for n in sm])].sort_values("n_products", ascending=False); N.loc[g.index, "sub"] = f"{ci}.{si}"
        say(f"   C{ci}.{si} ({len(sm)}; members' median NOVA-4 share {g.nova4_share.median():.2f}): " + ", ".join(g.ingredient.head(14)))
N.to_csv(SOJ / "matched_ingredient_nodes.csv", index=False)
say(f"\nall products NOVA mix: { {v: round(float((pnova == v).mean()), 2) for v in (1, 2, 3, 4)} }")
out.close()
