"""NETWORK STRUCTURES (upf/PLAN.md, 18 Nov): how connected is the grocery co-review network, and which structure is insightful?
Corrected H4 (pre-declared): NOVA assortativity on the FULL weighted projection, null = labels shuffled within OFF category, 1,000 shuffles.
Exploratory: S1 full projection, S2 links with >= 2 shared reviewers, S3 kNN cosine product graph (k = 10, >= 5 reviewers), S4 disparity backbone (alpha .01),
S5 category network (Amazon grocery sub-category x processing level; link = shared reviewers relative to chance).
Writes data/processed/network_structures.txt and soj/network_structures.csv, soj/category_network.csv.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/network_structures.py
"""
from pathlib import Path
import time
import numpy as np, pandas as pd, networkx as nx
from scipy import sparse
from scipy.sparse.csgraph import connected_components

C = Path("upf/data/processed/soj"); OUT = Path("upf/data/processed/network_structures.txt"); RNG = np.random.default_rng(1811); NPERM = 1000
log = []
def say(s=""): print(s, flush=True); log.append(s)

pr = pd.read_csv(C / "reviewer_pairs.csv.gz").drop_duplicates()
k = pr.groupby("user_id").size(); pr = pr[pr.user_id.map(k).between(2, 50)]
P = pd.read_csv(C / "products.csv.gz", usecols=["parent_asin", "nova", "category"]).drop_duplicates("parent_asin").set_index("parent_asin")
ui, users = pd.factorize(pr.user_id); pi, items = pd.factorize(pr.parent_asin)
B = sparse.csr_matrix((np.ones(len(pr), np.float32), (ui, pi)), shape=(len(users), len(items)))
nrev = np.asarray(B.sum(0)).ravel()
W = sparse.triu(B.T @ B, k=1).tocoo(); I, J, Wt = W.row, W.col, W.data.astype(float)
upf = (P.nova.reindex(items).values == 4).astype(int); cat = P.category.reindex(items).fillna("none").values
say(f"projection: {len(items):,} products, {len(I):,} links (reviewers with 2-50 matched grocery reviews: {len(users):,})")


def shuffle_within(lab, groups):
    pos = np.argsort(groups, kind="stable"); src = np.lexsort((RNG.random(len(lab)), groups)); out = np.empty_like(lab); out[pos] = lab[src]; return out


def assort(i, j, w, lab):
    """Newman's assortativity for a two-class label on an undirected weighted edge list"""
    a, b = lab[i], lab[j]; tot = w.sum()
    e11 = w[(a == 1) & (b == 1)].sum() / tot; e00 = w[(a == 0) & (b == 0)].sum() / tot
    p1 = (np.bincount(a, w, 2) + np.bincount(b, w, 2)) / (2 * tot); sq = (p1 ** 2).sum()
    return (e11 + e00 - sq) / (1 - sq)


def test(name, i, j, w, nperm=NPERM):
    obs = assort(i, j, w, upf); null = np.array([assort(i, j, w, shuffle_within(upf, cat)) for _ in range(nperm)])
    p = (1 + (null >= obs).sum()) / (nperm + 1); return obs, null.mean(), null.std(), p


def describe(name, i, j, w, louvain=True):
    n = len(items); A = sparse.coo_matrix((np.ones(len(i)), (i, j)), shape=(n, n)).tocsr(); A = A + A.T
    deg = np.diff(A.indptr); has = deg > 0; nc, lab = connected_components(A, directed=False); giant = np.bincount(lab[has]).max() if has.any() else 0
    G = nx.Graph(); G.add_weighted_edges_from(zip(i.tolist(), j.tolist(), w.tolist()))
    sample = RNG.choice(list(G.nodes()), size=min(3000, G.number_of_nodes()), replace=False)
    clus = nx.average_clustering(G, nodes=sample.tolist()); mod = np.nan; ncom = np.nan
    if louvain:
        t = time.time(); com = nx.community.louvain_communities(G, weight="weight", seed=7); mod = nx.community.modularity(G, com, weight="weight"); ncom = sum(len(c) >= 20 for c in com)
        say(f"  [{name}] Louvain {time.time() - t:.0f}s")
    a, nm, ns, p = test(name, i, j, w)
    a_u, nm_u, _, p_u = test(name, i, j, np.ones_like(w), nperm=200)
    r = dict(structure=name, products=int(has.sum()), share_connected=has.mean(), links=len(i), mean_degree=deg[has].mean(), giant=int(giant), giant_share=giant / max(1, has.sum()),
             clustering=clus, modularity=mod, communities_20plus=ncom, assort_weighted=a, null_weighted=nm, null_sd=ns, p_weighted=p, assort_unweighted=a_u, null_unweighted=nm_u, p_unweighted=p_u)
    say(f"  [{name}] products {r['products']:,} ({r['share_connected']:.0%}), links {r['links']:,}, mean degree {r['mean_degree']:.1f}, giant {r['giant']:,} ({r['giant_share']:.0%}), "
        f"clustering {clus:.3f}, modularity {mod:.3f}, communities >= 20 products {ncom}; NOVA assortativity weighted {a:+.3f} (null {nm:+.3f} sd {ns:.3f}, p {p:.4f}), unweighted {a_u:+.3f} (null {nm_u:+.3f}, p {p_u:.4f})")
    return r


rows = []
say("\n== CORRECTED H4 + S1: full weighted projection ==")
rows.append(describe("S1 full projection", I, J, Wt, louvain=False))
say("\n== S2: only links with >= 2 shared reviewers ==")
m = Wt >= 2; rows.append(describe("S2 >= 2 shared reviewers", I[m], J[m], Wt[m]))
say("\n== S3: kNN product graph (cosine on reviewer sets, k = 10, products with >= 5 reviewers) ==")
cos = Wt / np.sqrt(nrev[I] * nrev[J]); ok = (nrev[I] >= 5) & (nrev[J] >= 5)
E = pd.DataFrame({"a": np.r_[I[ok], J[ok]], "b": np.r_[J[ok], I[ok]], "c": np.r_[cos[ok], cos[ok]]})
E = E.sort_values(["a", "c"], ascending=[True, False]).groupby("a").head(10)
E["p"], E["q"] = E[["a", "b"]].min(1), E[["a", "b"]].max(1); E = E.groupby(["p", "q"]).c.max().reset_index()
rows.append(describe("S3 kNN cosine k=10", E.p.values, E.q.values, E.c.values))
say("\n== S4: disparity backbone alpha = .01 (the old one; for drawing only) ==")
s = np.bincount(I, Wt, len(items)) + np.bincount(J, Wt, len(items)); dg = np.bincount(I, minlength=len(items)) + np.bincount(J, minlength=len(items))
keep = ((1 - Wt / s[I]) ** (dg[I] - 1) < 0.01) | ((1 - Wt / s[J]) ** (dg[J] - 1) < 0.01)
rows.append(describe("S4 disparity backbone a=.01", I[keep], J[keep], Wt[keep]))
pd.DataFrame(rows).to_csv(C / "network_structures.csv", index=False)

say("\n== S5: category network (Amazon grocery sub-category x processing level) ==")
M = pd.read_csv("upf/data/processed/amazon_meta_compact.csv.gz", usecols=["parent_asin", "categories"]).drop_duplicates("parent_asin").set_index("parent_asin").categories
lv = M.reindex(items).fillna("").str.split("|")
sub = np.array([x[2] if len(x) > 2 else "" for x in lv], dtype=object)
node = np.array([f"{c} | {'UPF' if u else 'less'}" if c else "" for c, u in zip(sub, upf)], dtype=object)
cnt = pd.Series(node[node != ""]).value_counts(); good = set(cnt[cnt >= 30].index)
ok = np.array([x in good for x in node]); nodes = sorted(good); nid = {x: t for t, x in enumerate(nodes)}
col = np.array([nid[x] for x in node[ok]]); Bc = B[:, np.where(ok)[0]] @ sparse.csr_matrix((np.ones(ok.sum()), (np.arange(ok.sum()), col)), shape=(ok.sum(), len(nodes)))
Bc.data = np.ones_like(Bc.data)                                                               # reviewer reviewed >= 1 product in that node
R = (Bc.T @ Bc).toarray(); nn = np.diag(R).copy(); N = Bc.shape[0]; lift = R * N / np.outer(nn, nn); np.fill_diagonal(lift, np.nan)
iu = np.triu_indices(len(nodes), 1); L = pd.DataFrame({"a": np.array(nodes)[iu[0]], "b": np.array(nodes)[iu[1]], "shared": R[iu], "lift": lift[iu]})
L.to_csv(C / "category_network.csv", index=False)
isu = np.array([x.endswith("UPF") for x in nodes]); base = np.array([x.split(" | ")[0] for x in nodes])
pair_u = isu[iu[0]] & isu[iu[1]]; pair_l = ~isu[iu[0]] & ~isu[iu[1]]; mix = isu[iu[0]] != isu[iu[1]]; diffcat = base[iu[0]] != base[iu[1]]
say(f"  {len(nodes)} nodes (sub-category x UPF/less with >= 30 products), {N:,} reviewers")
for nm_, m_ in (("UPF - UPF", pair_u & diffcat), ("less - less", pair_l & diffcat), ("UPF - less", mix & diffcat), ("same sub-category, UPF - less", mix & ~diffcat)):
    say(f"  mean lift {nm_:32s} {np.nanmean(lift[iu][m_]):.2f}  (pairs {m_.sum()})")
G5 = nx.Graph()
for a_, b_, l_ in zip(L.a, L.b, L.lift):
    if l_ > 1: G5.add_edge(a_, b_, weight=float(np.log(l_)))
com5 = nx.community.louvain_communities(G5, weight="weight", seed=7); say(f"  Louvain on links with lift > 1 (weight log lift): {len(com5)} communities, modularity {nx.community.modularity(G5, com5, weight='weight'):.3f}")
for c in sorted(com5, key=len, reverse=True):
    say(f"   [{sum(x.endswith('UPF') for x in c)}/{len(c)} UPF] " + "; ".join(sorted(c)))
OUT.write_text("\n".join(log) + "\n"); print("saved", OUT)
