"""Language network of NDCs, communities, null models, stability, and edge-layer comparison (design in ndc/PLAN.md 'LANGUAGE NETWORK').
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python ndc/notebooks/ndc_network.py
"""
import sys
from collections import Counter
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).parent))
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist, squareform
import ndc_common as D

RNG = np.random.default_rng(77); nodes, n = D.nodes, D.n; PROC = D.PROC
FIG = Path("ndc/figures"); FIG.mkdir(exist_ok=True)


def knn_graph(S, k=5, names=None):
    names = names if names is not None else list(range(S.shape[0]))
    G = nx.Graph(); G.add_nodes_from(range(S.shape[0]))
    for i in range(S.shape[0]):
        o = [j for j in np.argsort(-S[i]) if j != i][:k]
        for j in o:
            w = max(float(S[i, j]), 0.01) if np.isfinite(S[i, j]) else 0.01
            G.add_edge(i, j, weight=w)
    return G


def louvain(G, seed=42, weight="weight"):
    comms = nx.community.louvain_communities(G, weight=weight, seed=seed)
    lab = np.zeros(G.number_of_nodes(), int)
    for c, members in enumerate(sorted(comms, key=len, reverse=True)):
        for m in members:
            lab[m] = c
    return lab, comms


def mod(G, lab, weight="weight"):
    groups = {}
    for i, l in enumerate(lab):
        groups.setdefault(l, set()).add(i)
    return nx.community.modularity(G, list(groups.values()), weight=weight)


def ari(x, y):
    ct = pd.crosstab(pd.Series(x), pd.Series(y)).values
    c2 = lambda a: a * (a - 1) / 2
    sij, sa, sb = c2(ct).sum(), c2(ct.sum(1)).sum(), c2(ct.sum(0)).sum()
    exp = sa * sb / c2(ct.sum()); den = (sa + sb) / 2 - exp
    return (sij - exp) / den if den else 0.0


def ari_p(x, y, nperm=5000):
    a = ari(x, y); x = np.asarray(x); y = np.asarray(y)
    return a, (1 + sum(ari(x, RNG.permutation(y)) >= a for _ in range(nperm))) / (nperm + 1)


def silhouette(Z, lab):
    Dm = squareform(pdist(Z)); s = []
    for i in range(len(lab)):
        same = (lab == lab[i]) & (np.arange(len(lab)) != i)
        if same.sum() == 0: s.append(0); continue
        a = Dm[i, same].mean(); b = min(Dm[i, lab == c].mean() for c in np.unique(lab) if c != lab[i]); s.append((b - a) / max(a, b))
    return float(np.mean(s))


# ---------------- 1. language network ----------------
G = knn_graph(D.L, 5)
lab, comms = louvain(G)
print(f"== LANGUAGE NETWORK (k=5): {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, mean degree {2*G.number_of_edges()/n:.1f}, components {nx.number_connected_components(G)}")
print(f"   Louvain: {len(comms)} communities, sizes {sorted([len(c) for c in comms], reverse=True)}, weighted modularity Q={mod(G, lab):.3f}")
regs = np.asarray(D.reg, dtype=object); incs = np.asarray(D.inc, dtype=object)
for c in range(len(comms)):
    m = np.where(lab == c)[0]
    if len(m) < 4: continue
    rc = Counter(regs[m]).most_common(2); ic = Counter(incs[m]).most_common(2)
    print(f"   community {c} (n={len(m)}): {' '.join(nodes[i] for i in m[:14])}{' ...' if len(m) > 14 else ''}")
    print(f"      top regions {[(a, b) for a, b in rc]} | income {[(a, b) for a, b in ic]}")

# ---------------- 2. null model ----------------
Gu = nx.Graph(G.edges()); Gu.add_nodes_from(range(n))
labu, _ = louvain(Gu, weight=None); Qobs = mod(Gu, labu, weight=None)
Qn = []
for s in range(200):
    H = Gu.copy(); nx.double_edge_swap(H, nswap=5 * H.number_of_edges(), max_tries=200 * H.number_of_edges(), seed=int(RNG.integers(1e9)))
    Qn.append(mod(H, louvain(H, seed=s, weight=None)[0], weight=None))
Qn = np.array(Qn)
print(f"\n== NULL: unweighted Louvain Q observed {Qobs:.3f} vs {Qn.mean():.3f} +- {Qn.std():.3f} in 200 degree-preserving rewired graphs; empirical p={(1+(Qn>=Qobs).sum())/201:.4f}")

# ---------------- 3. agreement with region / income / emission clusters ----------------
Z = D.z(D.prof); Lk = linkage(Z, "ward"); best = None
for k in range(3, 7):
    l = fcluster(Lk, k, "maxclust"); sc = silhouette(Z, l)
    if best is None or sc > best[0]: best = (sc, k, l)
emc = best[2]
print(f"\n== PRIMARY: agreement of language communities with other partitions (ARI, 5,000 permutations; emission clusters: Ward k={best[1]}, silhouette {best[0]:.2f})")
for nm, p in [("World Bank region", regs), ("income group", incs), ("emission-profile clusters", emc)]:
    a, pv = ari_p(lab, p); labp = pd.factorize(p)[0]
    print(f"   language communities vs {nm:26s} ARI={a:+.3f} p={pv:.4f} | modularity of THAT partition on the language network Q={mod(G, labp):.3f} (Louvain Q={mod(G, lab):.3f})")

# ---------------- 4. stability ----------------
print("\n== STABILITY")
for k in (3, 8, 10, 15):
    lk, _ = louvain(knn_graph(D.L, k)); print(f"   k={k:2d}: {len(set(lk))} communities, ARI vs k=5 partition {ari(lk, lab):+.2f}")
seeds = [louvain(G, seed=s)[0] for s in range(20)]
print(f"   20 Louvain seeds: communities {sorted(set(len(set(s)) for s in seeds))}, mean pairwise ARI {np.mean([ari(seeds[i], seeds[j]) for i in range(20) for j in range(i+1, 20)]):.2f}")
iso_idx = {i: k for k, i in enumerate(nodes)}
for rd in ("revised_first_ndc", "third_ndc", "indc"):
    Vr = np.load(PROC / f"ndc_vectors_{rd}.npy"); ir = list(pd.read_csv(PROC / f"ndc_index_{rd}.csv").iso)
    common = [i for i in ir if i in iso_idx]
    Vs = Vr[[ir.index(i) for i in common]]; Vs = Vs - Vs.mean(0); Vs /= np.linalg.norm(Vs, axis=1, keepdims=True)
    lr, _ = louvain(knn_graph(Vs @ Vs.T, 5)); base = [lab[iso_idx[i]] for i in common]
    print(f"   round {rd:18s}: {len(common)} countries, {len(set(lr))} communities, ARI vs first_ndc partition {ari(lr, base):+.2f}, vs region {ari(lr, [regs[iso_idx[i]] for i in common]):+.2f}")

# ---------------- 5. alternate the edges ----------------
layers = {"language": D.L, "emissions": D.M, "income": -np.abs(D.lg[:, None] - D.lg[None, :]), "geography": -D.dist}
parts, edges = {}, {}
for nm, S in layers.items():
    g = knn_graph(S, 5); parts[nm], _ = louvain(g); edges[nm] = {frozenset(e) for e in g.edges()}
print("\n== ALTERNATING THE EDGES: k=5 nearest-neighbour graphs on the same 154 nodes")
names = list(layers)
A = pd.DataFrame([[ari(parts[a], parts[b]) for b in names] for a in names], index=names, columns=names)
J = pd.DataFrame([[len(edges[a] & edges[b]) / len(edges[a] | edges[b]) for b in names] for a in names], index=names, columns=names)
print("   communities per layer:", {k: len(set(v)) for k, v in parts.items()})
print("   ARI between layer partitions:\n", A.round(2).to_string())
print("   edge-set overlap (Jaccard):\n", J.round(2).to_string())
hv = ["ladder", "f_gdp", "f_social", "f_health", "f_freedom", "f_generosity", "f_corruption"]
has = [k for k, i in enumerate(nodes) if i in D.H.index and D.H.loc[i, hv].notna().all()]; sub = np.array(has)
Hs = D.eucl_sim(D.z(D.H.loc[[nodes[k] for k in has], hv].values))
sp = {"happiness": louvain(knn_graph(Hs, 5))[0], "language": louvain(knn_graph(D.L[np.ix_(sub, sub)], 5))[0],
      "income": louvain(knn_graph(layers["income"][np.ix_(sub, sub)], 5))[0], "geography": louvain(knn_graph(layers["geography"][np.ix_(sub, sub)], 5))[0]}
print(f"   happiness layer on {len(has)} nodes, ARI with: " + ", ".join(f"{k} {ari(sp['happiness'], v):+.2f}" for k, v in sp.items() if k != "happiness"))

# ---------------- 6. figure ----------------
pos = nx.spring_layout(G, weight="weight", seed=4, k=0.5, iterations=300)
fig, axs = plt.subplots(1, 2, figsize=(17, 8))
cmap = plt.get_cmap("tab10"); rl = sorted(set(regs)); rcol = {r: plt.get_cmap("Set2")(i) for i, r in enumerate(rl)}
deg = dict(G.degree())
for ax, colors, title in [(axs[0], [cmap(lab[i] % 10) for i in range(n)], "language communities (Louvain)"),
                          (axs[1], [rcol[regs[i]] for i in range(n)], "World Bank region")]:
    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.12, width=0.5)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=colors, node_size=[30 + 6 * deg[i] for i in range(n)], edgecolors="white", linewidths=0.4)
    big = sorted(range(n), key=lambda i: -deg[i])[:35]
    nx.draw_networkx_labels(G, pos, labels={i: nodes[i] for i in big}, ax=ax, font_size=7)
    ax.set_title(title); ax.axis("off")
axs[1].legend(handles=[plt.Line2D([], [], marker="o", ls="", color=rcol[r], label=r) for r in rl], fontsize=7, loc="lower left")
fig.suptitle("NDC language network: each country linked to its 5 most similar NDCs (first NDC, 154 countries)")
fig.tight_layout(); fig.savefig(FIG / "language_network.png", dpi=140)
pd.DataFrame({"iso": nodes, "language_community": lab, "region": regs, "income": incs, "emission_cluster": emc}).to_csv(PROC / "ndc_language_communities.csv", index=False)
print("\nsaved ndc/figures/language_network.png and data/processed/ndc_language_communities.csv")
