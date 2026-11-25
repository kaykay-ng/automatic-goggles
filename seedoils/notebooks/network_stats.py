"""Network measures of the commenter backbone (course weeks 1-4) and a comparison of community methods.
Network: the r/StopEatingSeedOils commenter backbone (commenter_topic_network_130.py --export): 2,621 commenters, links = disparity-filtered cosine
similarity of topic mixes (weight = similarity). Louvain communities = cn_nodes.json 'c' (reference run of 20 seeds).
Measures:
  size, density, components; degree and strength distributions (log-binned histogram, CCDF), power-law fit with the powerlaw package
  (alpha, x_min, likelihood-ratio tests against lognormal and exponential); clustering (average local, transitivity, weighted) against an
  Erdos-Renyi graph of the same density (expected C = p) and a degree-preserving null (double edge swaps, NULL_REPS); shortest paths from
  PATH_SOURCES random sources (average, longest seen) against ln n / ln <k>; degree assortativity (and its degree-preserving null), cohort
  and community assortativity with label shuffles; centralities (degree, betweenness on PATH_SOURCES samples, eigenvector, PageRank),
  their Spearman correlations and who the top 30 are (cohort, community; no usernames).
Community methods compared with Louvain:
  k-clique percolation (Palla et al. 2005; networkx k_clique_communities) for k in K_VALUES: overlapping, people outside every k-clique stay out;
  link communities (Ahn, Bagrow & Lehmann 2010): similarity of two links sharing a node = Jaccard of the inclusive neighbourhoods of their other
  ends; single-linkage clustering of links cut at the maximum partition density D (thresholds scanned on a grid). People belong to every link
  community their links fall in; their main one = the one holding most of their links.
  Agreement with Louvain: AMI / NMI on people with exactly one community (k-clique) or on the main community (link communities); coverage and
  memberships per person.
Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/network_stats.py  -> data/processed/network_stats.json (aggregates only)"""
import json
import time
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.sparse.csgraph import connected_components
from scipy.stats import spearmanr
from sklearn.metrics import adjusted_mutual_info_score as ami, normalized_mutual_info_score as nmi

P = Path("seedoils/data/processed"); A = P / "artifact"
NULL_REPS, LABEL_REPS, PATH_SOURCES, K_VALUES = 10, 200, 500, [4, 6, 8, 10, 12]
rng = np.random.default_rng(0); out = {}
t_all = time.time()
nodes = json.load(open(A / "cn_nodes.json"))["rows"]; E = pd.read_csv(P / "commenter_backbone_edges.csv")
n = len(nodes); G = nx.Graph(); G.add_nodes_from(range(n)); G.add_weighted_edges_from(E[["s", "t", "w"]].itertuples(index=False))
comm = np.array([r["c"] for r in nodes]); old = np.array([r["o"] for r in nodes])
nx.set_node_attributes(G, dict(enumerate(comm.tolist())), "comm"); nx.set_node_attributes(G, dict(enumerate(old.tolist())), "old")
deg = np.array([d for _, d in G.degree()]); strength = np.array([d for _, d in G.degree(weight="weight")]); m = G.number_of_edges(); dens = nx.density(G)
out["basic"] = {"nodes": n, "edges": m, "density": round(dens, 5), "components": nx.number_connected_components(G), "mean_degree": round(float(deg.mean()), 1),
                "median_degree": int(np.median(deg)), "max_degree": int(deg.max()), "min_degree": int(deg.min()), "mean_strength": round(float(strength.mean()), 2)}
print("basic", out["basic"], flush=True)

# ---- degree distribution, CCDF, power-law fit
def logbins(x):
    b = np.unique(np.round(np.logspace(0, np.log10(x.max() + 1), 25)).astype(int)); h, e = np.histogram(x, bins=b)
    w = np.diff(e); mid = np.sqrt(e[:-1] * e[1:]); keep = h > 0
    return [[round(float(a), 2), float(c)] for a, c in zip(mid[keep], (h / w / len(x))[keep])]
ccdf = lambda x: [[int(v), round(float((x >= v).mean()), 6)] for v in np.unique(x)]
import powerlaw
fit = powerlaw.Fit(deg, discrete=True, verbose=False)
R_ln, p_ln = fit.distribution_compare("power_law", "lognormal", normalized_ratio=True)
R_ex, p_ex = fit.distribution_compare("power_law", "exponential", normalized_ratio=True)
from scipy.stats import poisson
pois = [[int(v), round(float(poisson.sf(v - 1, deg.mean())), 8)] for v in np.unique(deg)]
out["degree"] = {"hist_logbinned": logbins(deg), "ccdf": ccdf(deg), "ccdf_poisson_same_mean": pois, "strength_ccdf": [[round(float(v), 2), round(float((strength >= v).mean()), 6)] for v in np.quantile(strength, np.linspace(0, 1, 60))],
                 "powerlaw": {"alpha": round(float(fit.power_law.alpha), 2), "xmin": int(fit.power_law.xmin), "n_tail": int((deg >= fit.power_law.xmin).sum()),
                              "vs_lognormal_R": round(float(R_ln), 2), "vs_lognormal_p": round(float(p_ln), 4), "vs_exponential_R": round(float(R_ex), 2), "vs_exponential_p": round(float(p_ex), 4)},
                 "std": round(float(deg.std()), 1), "friendship_paradox_mean_neighbour_degree": round(float(np.mean([deg[list(G[v])].mean() for v in G])), 1)}
print("degree", out["degree"]["powerlaw"], flush=True)

# ---- clustering vs nulls
C_avg, C_tr, C_w = nx.average_clustering(G), nx.transitivity(G), nx.average_clustering(G, weight="weight")
null_c, null_t, null_r = [], [], []
for i in range(NULL_REPS):
    H = G.copy(); nx.double_edge_swap(H, nswap=2 * m, max_tries=40 * m, seed=int(rng.integers(1e9)))
    null_c.append(nx.average_clustering(H)); null_t.append(nx.transitivity(H)); null_r.append(nx.degree_assortativity_coefficient(H))
out["clustering"] = {"average_local": round(C_avg, 3), "transitivity": round(C_tr, 3), "average_weighted": round(C_w, 4), "er_expected": round(dens, 4),
                     "config_null_average": [round(float(np.mean(null_c)), 3), round(float(np.std(null_c)), 3)], "config_null_transitivity": [round(float(np.mean(null_t)), 3), round(float(np.std(null_t)), 3)],
                     "by_degree": [[int(k), round(float(np.mean([c for v, c in nx.clustering(G).items() if deg[v] == k])), 3)] for k in np.unique(deg) if (deg == k).sum() >= 5][::3]}
print("clustering", {k: v for k, v in out["clustering"].items() if k != "by_degree"}, flush=True)

# ---- paths (sampled sources)
src = rng.choice(n, min(PATH_SOURCES, n), replace=False); dist_sum, dist_n, ecc, hist = 0, 0, 0, np.zeros(20)
for s in src:
    L = np.array(list(nx.single_source_shortest_path_length(G, int(s)).values())); L = L[L > 0]
    dist_sum += L.sum(); dist_n += len(L); ecc = max(ecc, L.max()); hist[:L.max() + 1] += np.bincount(L, minlength=L.max() + 1)[:20]
out["paths"] = {"sources": len(src), "average": round(dist_sum / dist_n, 2), "longest_seen": int(ecc), "er_expected": round(float(np.log(n) / np.log(deg.mean())), 2),
                "distribution": [[int(k), round(float(h / hist.sum()), 4)] for k, h in enumerate(hist) if h > 0]}
print("paths", {k: v for k, v in out["paths"].items() if k != "distribution"}, flush=True)

# ---- assortativity
def shuffle(attr):
    """Label-permutation null: the same network, the attribute values shuffled over people (LABEL_REPS times)."""
    H = G.copy(); vals = [G.nodes[v][attr] for v in G.nodes]; res = []
    for _ in range(LABEL_REPS):
        nx.set_node_attributes(H, dict(zip(G.nodes, rng.permutation(vals).tolist())), attr); res.append(nx.attribute_assortativity_coefficient(H, attr))
    return res
r_deg = nx.degree_assortativity_coefficient(G); r_old = nx.attribute_assortativity_coefficient(G, "old"); r_com = nx.attribute_assortativity_coefficient(G, "comm")
sh_old = shuffle("old"); sh_com = shuffle("comm")
out["assortativity"] = {"degree": round(r_deg, 3), "degree_config_null": [round(float(np.mean(null_r)), 3), round(float(np.std(null_r)), 3)],
                        "cohort_old_new": round(r_old, 3), "cohort_shuffle": [round(float(np.mean(sh_old)), 3), round(float(np.std(sh_old)), 3)],
                        "community": round(r_com, 3), "community_shuffle": [round(float(np.mean(sh_com)), 3), round(float(np.std(sh_com)), 3)],
                        "knn_by_degree": [[int(k), round(float(v), 1)] for k, v in sorted(nx.average_degree_connectivity(G).items()) if (deg == k).sum() >= 5][::3]}
print("assortativity", {k: v for k, v in out["assortativity"].items() if k != "knn_by_degree"}, flush=True)

# ---- centralities
bt = nx.betweenness_centrality(G, k=PATH_SOURCES, seed=1); ev = nx.eigenvector_centrality_numpy(G); pr = nx.pagerank(G, weight="weight")
Cn = pd.DataFrame({"degree": deg, "strength": strength, "betweenness": [bt[v] for v in range(n)], "eigenvector": [ev[v] for v in range(n)], "pagerank": [pr[v] for v in range(n)]})
rho = Cn.corr(method="spearman").round(2)
top = {c: {"newcomer_share": round(float(1 - old[Cn[c].nlargest(30).index].mean()), 2), "communities": pd.Series(comm[Cn[c].nlargest(30).index]).value_counts().head(4).to_dict()} for c in Cn}
out["centrality"] = {"spearman": rho.to_dict(), "top30": {k: {"newcomer_share": v["newcomer_share"], "communities": {str(a + 1): int(b) for a, b in v["communities"].items()}} for k, v in top.items()},
                     "newcomer_share_all": round(float(1 - old.mean()), 2)}
print("centrality top30 newcomer share", {k: v["newcomer_share"] for k, v in top.items()}, flush=True)

# ---- community methods
def cover_stats(cover, name, **extra):
    memb = np.zeros(n, int); main = np.full(n, -1)
    for i, c in enumerate(cover):
        for v in c: memb[v] += 1
    one = memb == 1
    for i, c in enumerate(cover):
        for v in c:
            if one[v]: main[v] = i
    sizes = sorted((len(c) for c in cover), reverse=True)
    res = {"method": name, "communities": len(cover), "largest": sizes[0] if sizes else 0, "sizes_top": sizes[:8], "coverage": round(float((memb > 0).mean()), 3),
           "mean_memberships_covered": round(float(memb[memb > 0].mean()), 2) if (memb > 0).any() else None, "share_in_exactly_one": round(float(one.mean()), 3),
           "ami_vs_louvain_single": round(float(ami(comm[one], main[one])), 3) if one.sum() > 10 else None,
           "nmi_vs_louvain_single": round(float(nmi(comm[one], main[one])), 3) if one.sum() > 10 else None, **extra}
    print(" ", res, flush=True); return res
methods = [{"method": "Louvain (reference of 20 seeds)", "communities": int(comm.max()) + 1, "largest": int(np.bincount(comm).max()), "sizes_top": sorted(np.bincount(comm).tolist(), reverse=True)[:8],
            "coverage": 1.0, "mean_memberships_covered": 1.0, "share_in_exactly_one": 1.0, "ami_vs_louvain_single": 1.0, "nmi_vs_louvain_single": 1.0}]
cliques = list(nx.find_cliques(G)); print(f"maximal cliques {len(cliques):,}", flush=True)
for k in K_VALUES:
    t0 = time.time(); cover = [set(c) for c in nx.community.k_clique_communities(G, k, cliques=[c for c in cliques if len(c) >= k])]
    methods.append(cover_stats(cover, f"k-clique percolation, k={k}", seconds=round(time.time() - t0)))

# link communities (Ahn, Bagrow & Lehmann 2010)
t0 = time.time(); Ad = nx.to_scipy_sparse_array(G, nodelist=range(n), format="csr", weight=None).astype(np.float32); Ai = (Ad + sp.eye(n, dtype=np.float32)).tocsr()
inter = (Ai @ Ai).toarray(); kk = np.asarray(Ai.sum(1)).ravel(); jac = inter / (kk[:, None] + kk[None, :] - inter)
eid = {}; EL = np.array([(a, b) if a < b else (b, a) for a, b in G.edges()]); [eid.__setitem__((int(a), int(b)), i) for i, (a, b) in enumerate(EL)]
key = lambda a, b: eid[(a, b) if a < b else (b, a)]
e1, e2, sim = [], [], []
for k_ in range(n):
    nb = np.array(list(G[k_]));
    if len(nb) < 2: continue
    iu, ju = np.triu_indices(len(nb), 1); a, b = nb[iu], nb[ju]
    e1.append([key(k_, int(x)) for x in a]); e2.append([key(k_, int(x)) for x in b]); sim.append(jac[a, b])
e1, e2, sim = np.concatenate(e1), np.concatenate(e2), np.concatenate(sim).astype(np.float32); M = len(EL)
print(f"link pairs {len(sim):,} in {time.time() - t0:.0f}s", flush=True)
def partition(th):
    keep = sim >= th; g = sp.coo_matrix((np.ones(keep.sum()), (e1[keep], e2[keep])), shape=(M, M)); _, lab = connected_components(g, directed=False)
    return lab
def density(lab):
    D = 0.0
    for c in np.unique(lab):
        ed = EL[lab == c]; mc = len(ed); nc = len(np.unique(ed))
        if nc > 2: D += mc * (mc - (nc - 1)) / ((nc - 2) * (nc - 1))
    return 2 * D / M
grid = np.quantile(sim, np.linspace(0.5, 0.999, 40)); scan = [(float(th), density(partition(th))) for th in grid]
th_best, D_best = max(scan, key=lambda x: x[1]); lab = partition(th_best)
cover = []
for c in np.unique(lab):
    ed = EL[lab == c]
    if len(ed) >= 3: cover.append(set(np.unique(ed).tolist()))
link_counts = {}
for c in np.unique(lab):
    for a, b in EL[lab == c]:
        link_counts.setdefault(int(a), {}).setdefault(int(c), 0); link_counts[int(a)][int(c)] += 1
        link_counts.setdefault(int(b), {}).setdefault(int(c), 0); link_counts[int(b)][int(c)] += 1
main_lc = np.array([max(link_counts[v], key=link_counts[v].get) if v in link_counts else -1 for v in range(n)])
lc = cover_stats(cover, "Link communities (max partition density)", threshold=round(th_best, 3), partition_density=round(D_best, 4),
                 ami_vs_louvain_main=round(float(ami(comm, main_lc)), 3), nmi_vs_louvain_main=round(float(nmi(comm, main_lc)), 3),
                 link_communities_all=int(len(np.unique(lab))), density_scan=[[round(a, 3), round(b, 4)] for a, b in scan], seconds=round(time.time() - t0))
methods.append(lc)
out["communities"] = methods
(P / "network_stats.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
print(f"wrote network_stats.json in {time.time() - t_all:.0f}s")
