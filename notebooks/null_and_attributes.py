"""(1) Null model for trade-network community structure; (2) emissions / food-supply node attributes and a test of
whether trade communities differ in them.

Run from final_project/:  ../.venv/bin/python notebooks/null_and_attributes.py

Null model (strength-preserving, geography-blind): keep each country's total exports and imports in the layer, but place
tonnage on country pairs with probability proportional to out-strength(i) * in-strength(j) (i != j). Same number of units
for every draw, then the SAME disparity backbone + Louvain as the observed network. If observed modularity Q is well above
the null, community structure is NOT explained by how big each country's trade is; what is left over includes geography,
trade agreements, specialisation.
Attribute test: eta^2 (between-community share of variance) with a label-permutation p-value (n = 26 nodes, so small!).
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
sys.path.insert(0, str(Path(__file__).parent))
from build_trade_networks import load, edge_table, disparity_backbone, GROUPS

RNG = np.random.default_rng(42)
N_NULL, UNITS = 200, 100_000
PROC = Path("data/processed")
YEARS = [f"Y{y}" for y in range(2015, 2023)]


def graph_from(e):
    G = nx.DiGraph()
    G.add_weighted_edges_from(e[["exporter", "importer", "w"]].itertuples(index=False))
    return G


def louvain_Q(G, seed):
    B = disparity_backbone(G)
    U = nx.Graph(); U.add_nodes_from(B.nodes)
    for u, v, w in B.edges(data="weight"):
        U.add_edge(u, v, weight=U[u][v]["weight"] + w if U.has_edge(u, v) else w)
    comms = nx.community.louvain_communities(U, weight="weight", seed=seed)
    return nx.community.modularity(U, comms, weight="weight"), comms, B


def null_graph(G):
    nodes = sorted(G.nodes)
    so = np.array([G.out_degree(n, weight="weight") for n in nodes])
    si = np.array([G.in_degree(n, weight="weight") for n in nodes])
    P = np.outer(so, si); np.fill_diagonal(P, 0); P = P / P.sum()
    counts = RNG.multinomial(UNITS, P.ravel()).reshape(P.shape)
    H = nx.DiGraph(); H.add_nodes_from(nodes)
    for i, j in zip(*np.nonzero(counts)):
        H.add_edge(nodes[i], nodes[j], weight=float(counts[i, j]))
    return H


def attributes():
    em = pd.read_csv(PROC / "emissions_co2eq_parlamint.csv").set_index(["iso", "Item"])
    f = pd.read_csv(PROC / "fbs_parlamint.csv")
    m = lambda df: df[YEARS].mean(axis=1)
    pop = f[(f.Item == "Population")].set_index("iso"); pop = m(pop) * 1000       # persons
    kc = lambda item: m(f[(f.Item == item) & (f.Element == "Food supply (kcal/capita/day)")].set_index("iso"))
    agri = m(em.xs("Agrifood systems", level="Item")) * 1000                       # kt -> t CO2eq
    A = pd.DataFrame({
        "agrifood_tCO2eq_pc": agri / pop,
        "livestock_share": m(em.xs("Emissions from livestock", level="Item")) * 1000 / agri,
        "farmgate_share": m(em.xs("Farm gate", level="Item")) * 1000 / agri,
        "landusechange_share": m(em.xs("Land-use change", level="Item")) * 1000 / agri,
        "kcal_pc_day": kc("Grand Total"),
        "animal_kcal_share": kc("Animal Products") / kc("Grand Total"),
        "log_population": np.log10(pop),
    })
    A.to_csv(PROC / "country_attributes.csv")
    return A


def eta2(x, labels):
    x = np.asarray(x, float); labels = np.asarray(labels)
    ss_tot = ((x - x.mean()) ** 2).sum()
    ss_b = sum(((x[labels == c].mean() - x.mean()) ** 2) * (labels == c).sum() for c in np.unique(labels))
    return ss_b / ss_tot


if __name__ == "__main__":
    t = load()
    rows, comm_labels = [], {}
    print(f"== NULL MODEL ({N_NULL} strength-preserving draws per layer)")
    for g in [None] + list(GROUPS):
        name = g or "all_food"
        G = graph_from(edge_table(t, g))
        q_obs, comms, _ = louvain_Q(G, 42)
        nulls = np.array([louvain_Q(null_graph(G), s)[0] for s in range(N_NULL)])
        z = (q_obs - nulls.mean()) / nulls.std()
        p = (1 + (nulls >= q_obs).sum()) / (1 + N_NULL)
        rows.append(dict(layer=name, Q_obs=q_obs, Q_null_mean=nulls.mean(), Q_null_sd=nulls.std(), z=z, p=p))
        comm_labels[name] = {n: i for i, c in enumerate(comms) for n in c}
        print(f"{name:16s} Q_obs={q_obs:.2f}  null={nulls.mean():.2f}±{nulls.std():.2f}  z={z:5.1f}  p={p:.3f}")
    pd.DataFrame(rows).to_csv(PROC / "networks/null_modularity.csv", index=False)

    A = attributes()
    print("\n== ATTRIBUTES (country means 2015-22)\n", A.describe().loc[["mean", "std", "min", "max"]].round(2).to_string())
    print("\n== eta^2 of attribute by trade community (permutation p, 5000 shuffles)")
    out = []
    for name, lab in comm_labels.items():
        L = np.array([lab[n] for n in A.index])
        for col in A.columns:
            x = A[col].values
            obs = eta2(x, L)
            perm = np.array([eta2(x, RNG.permutation(L)) for _ in range(5000)])
            out.append(dict(layer=name, attribute=col, eta2=obs, p=(1 + (perm >= obs).sum()) / 5001))
    R = pd.DataFrame(out); R.to_csv(PROC / "networks/community_attribute_tests.csv", index=False)
    print(R.pivot(index="layer", columns="attribute", values="eta2").round(2).to_string())
    print("\nsignificant at p<0.05 (uncorrected; 10 layers x 7 attributes = 70 tests!):")
    print(R[R.p < 0.05].round(3).to_string(index=False))
