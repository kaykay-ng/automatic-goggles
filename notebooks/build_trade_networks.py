"""Build commodity-group food-trade networks among the 26 ParlaMint countries (FAOSTAT detailed trade matrix).

Run from final_project/:  ../.venv/bin/python notebooks/build_trade_networks.py
Reads data/processed/trade_parlamint_pairs.csv (made by profile_faostat.py). Writes data/processed/networks/*.graphml
and figures/trade_*.png. Edge i->j means "i exports to j" (tonnes per year, mean over 2015-2022).

Choices to defend in the paper:
- Weight = importer-reported import quantity; if the importer reports nothing for a pair-year, use the exporter's
  export quantity (mirror data). Only items measured in tonnes ('t'); live animals (head counts) are excluded.
- Commodity group from the CPC prefix of each FAO item (map below). Fish is absent from this FAO trade matrix.
- Backbone: disparity filter (Serrano et al. 2009), alpha=0.05, applied to out- and in-strength; edge kept if significant
  on either side.
"""
import numpy as np, pandas as pd, networkx as nx
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("data/processed/networks"); OUT.mkdir(parents=True, exist_ok=True)
FIG = Path("figures"); FIG.mkdir(exist_ok=True)
YEARS = [f"Y{y}" for y in range(2015, 2023)]

GROUPS = {  # CPC prefix -> group
    "cereals": ["011", "231"],
    "fruit_veg": ["012", "013", "015", "213", "214", "F02", "F04"],
    "pulses_spices": ["016", "017"],
    "oilseeds_oils": ["014", "215", "216", "217", "219"],
    "sugar_sweets": ["018", "232", "235", "236", "F06"],
    "meat": ["211", "F08", "F10", "F11"],
    "dairy_eggs": ["022", "023", "221", "222"],
    "beverages": ["241", "242", "243", "244"],
    "feed_byproducts": ["233", "391"],
}
PREFIX2GROUP = {p: g for g, ps in GROUPS.items() for p in ps}


def load():
    ic = pd.read_csv("data/raw/Trade_DetailedTradeMatrix_E_All_Data/Trade_DetailedTradeMatrix_E_ItemCodes.csv",
                     encoding="latin-1")
    ic["cpc"] = ic["CPC Code"].astype(str).str.lstrip("'")
    ic["group"] = ic["cpc"].str[:3].map(PREFIX2GROUP)
    t = pd.read_csv("data/processed/trade_parlamint_pairs.csv")
    t = t.merge(ic[["Item Code", "group"]], on="Item Code", how="left")
    t = t[t["group"].notna() & (t["Unit"] == "t")]
    t["Element"] = t["Element"].str.strip()
    return t


def edge_table(t, group=None):
    """Return DataFrame exporter, importer, weight (mean tonnes/yr)."""
    if group:
        t = t[t["group"] == group]
    imp = t[t["Element"] == "Import quantity"].copy()
    exp = t[t["Element"] == "Export quantity"].copy()
    imp = imp.rename(columns={"reporter": "importer", "partner": "exporter"})
    exp = exp.rename(columns={"reporter": "exporter", "partner": "importer"})
    key = ["exporter", "importer", "Item Code"]
    a = imp.groupby(key)[YEARS].sum(min_count=1)
    b = exp.groupby(key)[YEARS].sum(min_count=1)
    both = a.combine_first(b)              # importer-reported first, exporter mirror fills gaps
    both = both.reset_index()
    both["w"] = both[YEARS].fillna(0).mean(axis=1)   # mean over the 8 years (missing years count as 0)
    e = both.groupby(["exporter", "importer"], as_index=False)["w"].sum()
    return e[e["w"] > 0]


def disparity_backbone(G, alpha=0.05):
    keep = set()
    for mode in ("out", "in"):
        for n in G:
            edges = list(G.out_edges(n, data="weight")) if mode == "out" else list(G.in_edges(n, data="weight"))
            k = len(edges)
            if k < 2:
                keep |= {(u, v) for u, v, _ in edges}
                continue
            s = sum(w for _, _, w in edges)
            for u, v, w in edges:
                if (1 - w / s) ** (k - 1) < alpha:
                    keep.add((u, v))
    B = nx.DiGraph()
    B.add_nodes_from(G.nodes)
    for u, v in keep:
        B.add_edge(u, v, weight=G[u][v]["weight"])
    return B


def analyse(name, e):
    G = nx.DiGraph()
    G.add_weighted_edges_from(e[["exporter", "importer", "w"]].itertuples(index=False))
    B = disparity_backbone(G)
    U = nx.Graph()
    U.add_nodes_from(B.nodes)
    for u, v, w in B.edges(data="weight"):
        U.add_edge(u, v, weight=U[u][v]["weight"] + w if U.has_edge(u, v) else w)
    comms = nx.community.louvain_communities(U, weight="weight", seed=42)
    mod = nx.community.modularity(U, comms, weight="weight")
    comm_of = {n: i for i, c in enumerate(sorted(comms, key=len, reverse=True)) for n in c}
    nx.set_node_attributes(B, comm_of, "community")
    nx.write_graphml(B, OUT / f"trade_{name}.graphml")
    sin = dict(G.in_degree(weight="weight")); sout = dict(G.out_degree(weight="weight"))
    top_exp = sorted(sout, key=sout.get, reverse=True)[:3]
    top_imp = sorted(sin, key=sin.get, reverse=True)[:3]
    print(f"{name:16s} full: {G.number_of_edges():4d} edges, {G.number_of_edges()/(26*25):.0%} density | "
          f"backbone: {B.number_of_edges():3d} edges | Louvain: {len(comms)} comms, Q={mod:.2f} | "
          f"top exporters {top_exp} importers {top_imp} | total {sum(sout.values())/1e6:.1f} Mt/yr")
    return G, B, comm_of


def plot(name, B, comm_of):
    pos = nx.spring_layout(B.to_undirected(), weight="weight", seed=1, k=0.9)
    fig, ax = plt.subplots(figsize=(7, 6))
    cmap = plt.get_cmap("tab10")
    w = np.array([d["weight"] for _, _, d in B.edges(data=True)]) if B.number_of_edges() else np.array([1])
    nx.draw_networkx_edges(B, pos, ax=ax, width=0.3 + 3 * w / w.max() if B.number_of_edges() else 0.3,
                           edge_color="#999", alpha=0.5, arrows=True, arrowsize=6, connectionstyle="arc3,rad=0.1")
    nx.draw_networkx_nodes(B, pos, ax=ax, node_color=[cmap(comm_of[n] % 10) for n in B],
                           node_size=[60 + 25 * B.degree(n) for n in B], edgecolors="white")
    nx.draw_networkx_labels(B, pos, ax=ax, font_size=7)
    ax.set_title(f"{name}: trade backbone (disparity filter 0.05)\ncolour = Louvain community", fontsize=10)
    ax.axis("off")
    fig.tight_layout(); fig.savefig(FIG / f"trade_{name}.png", dpi=150); plt.close(fig)


if __name__ == "__main__":
    t = load()
    print("items grouped:", t.groupby("group")["Item Code"].nunique().to_dict())
    results = {}
    for g in [None] + list(GROUPS):
        name = g or "all_food"
        e = edge_table(t, g)
        results[name] = analyse(name, e)
        plot(name, results[name][1], results[name][2])
    # how similar are communities across commodity layers? (adjusted Rand index)
    def adjusted_rand_score(x, y):  # no sklearn dependency
        ct = pd.crosstab(pd.Series(x), pd.Series(y)).values
        c2 = lambda a: a * (a - 1) / 2
        sij, sa, sb = c2(ct).sum(), c2(ct.sum(1)).sum(), c2(ct.sum(0)).sum()
        exp = sa * sb / c2(ct.sum())
        return (sij - exp) / ((sa + sb) / 2 - exp)
    names = list(results); nodes = sorted(results["all_food"][1].nodes)
    M = pd.DataFrame(index=names, columns=names, dtype=float)
    for a in names:
        for b in names:
            M.loc[a, b] = adjusted_rand_score([results[a][2].get(n, -1) for n in nodes],
                                              [results[b][2].get(n, -1) for n in nodes])
    print("\nAdjusted Rand index between layers' communities:\n", M.round(2).to_string())
    M.to_csv("data/processed/networks/layer_community_ari.csv")
