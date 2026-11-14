"""Cross-layer modularity: how well do the communities found on layer A explain the trade network of layer B?

Run from final_project/:  ../.venv/bin/python notebooks/cross_layer_modularity.py
Entry [A, B] = modularity Q of layer-A's Louvain partition evaluated on layer-B's backbone (undirected, weighted).
Diagonal = each layer's own Q. Significance: permute A's labels over the 26 countries (same community sizes) 2000 times
and evaluate on B's backbone -> z-score and one-sided p. Writes data/processed/networks/cross_layer_*.csv + figure.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).parent))
from build_trade_networks import load, edge_table, GROUPS
from null_and_attributes import graph_from, louvain_Q

RNG = np.random.default_rng(42)
N_PERM = 2000
OUT = Path("data/processed/networks")


def undirected_backbone(G):
    _, comms, B = louvain_Q(G, 42)
    U = nx.Graph(); U.add_nodes_from(B.nodes)
    for u, v, w in B.edges(data="weight"):
        U.add_edge(u, v, weight=U[u][v]["weight"] + w if U.has_edge(u, v) else w)
    return U, comms


def Q(U, labels):
    groups = {}
    for n, l in labels.items():
        groups.setdefault(l, set()).add(n)
    return nx.community.modularity(U, list(groups.values()), weight="weight")


if __name__ == "__main__":
    t = load()
    names = ["all_food"] + list(GROUPS)
    U, P = {}, {}
    for name in names:
        U[name], comms = undirected_backbone(graph_from(edge_table(t, None if name == "all_food" else name)))
        P[name] = {n: i for i, c in enumerate(comms) for n in c}
    nodes = sorted(U["all_food"].nodes)
    M = pd.DataFrame(index=names, columns=names, dtype=float)
    Z, PV = M.copy(), M.copy()
    for a in names:
        lab = np.array([P[a][n] for n in nodes])
        for b in names:
            M.loc[a, b] = Q(U[b], P[a])
            perm = np.array([Q(U[b], dict(zip(nodes, RNG.permutation(lab)))) for _ in range(N_PERM)])
            Z.loc[a, b] = (M.loc[a, b] - perm.mean()) / perm.std()
            PV.loc[a, b] = (1 + (perm >= M.loc[a, b]).sum()) / (1 + N_PERM)
    M.to_csv(OUT / "cross_layer_modularity.csv"); Z.to_csv(OUT / "cross_layer_z.csv"); PV.to_csv(OUT / "cross_layer_p.csv")
    print("Rows = partition from layer A, columns = network of layer B. Entry = modularity Q.\n", M.round(2).to_string())
    print("\nz-score vs permuted labels:\n", Z.round(1).to_string())
    print("\nOff-diagonal cells with p>=0.05 (partition A does NOT explain network B):")
    for a in names:
        for b in names:
            if a != b and PV.loc[a, b] >= 0.05:
                print(f"  {a} -> {b}: Q={M.loc[a,b]:.2f} p={PV.loc[a,b]:.3f}")
    off = M.values[~np.eye(len(names), dtype=bool)]
    print(f"\nmean off-diagonal Q = {off.mean():.2f}; mean diagonal Q = {np.diag(M.values).mean():.2f}")

    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(M.values, cmap="viridis", vmin=0)
    ax.set_xticks(range(len(names)), names, rotation=60, ha="right", fontsize=8)
    ax.set_yticks(range(len(names)), names, fontsize=8)
    for i in range(len(names)):
        for j in range(len(names)):
            ax.text(j, i, f"{M.values[i, j]:.2f}", ha="center", va="center", fontsize=6,
                    color="white" if M.values[i, j] < M.values.max() * 0.6 else "black")
    ax.set_xlabel("network evaluated on (layer B)"); ax.set_ylabel("communities taken from (layer A)")
    ax.set_title("Cross-layer modularity Q", fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.046); fig.tight_layout()
    fig.savefig("figures/cross_layer_modularity.png", dpi=150)
