"""Hubs of the topic co-occurrence network (user question 27 Nov). Reads data/processed/topic_cooccurrence_network.json (topic_cooccurrence_network.py)
and computes, on the all-years network: degree (number of significant partner topics), strength (sum of lifts), betweenness (shortest paths with
distance = 1 / lift), eigenvector centrality and PageRank (weight = lift), and the participation coefficient (Guimera and Amaral 2005: 1 - sum over
communities of (links into that community / degree)^2; 0 = all links inside its own community, high = a bridge between communities).
Also: Spearman correlation of each centrality with topic size (number of documents), because bigger topics have more power to pass the test even
though the null keeps topic popularity; and the top topics by degree in the before / from 2024 networks.
Output: data/processed/topic_network_centrality.json. Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/topic_network_centrality.py"""
import json
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

P = Path("seedoils/data/processed")
d = json.loads((P / "topic_cooccurrence_network.json").read_text())
N = pd.DataFrame(d["nodes"]).set_index("topic")
G = nx.Graph(); G.add_nodes_from(N.index)
G.add_edges_from((e["a"], e["b"], {"weight": e["lift"], "dist": 1 / e["lift"]}) for e in d["edges_all"])
N["degree"] = pd.Series(dict(G.degree()))
N["strength"] = pd.Series(dict(G.degree(weight="weight")))
N["betweenness"] = pd.Series(nx.betweenness_centrality(G, weight="dist", normalized=True))
core = G.subgraph(max(nx.connected_components(G), key=len))
N["eigenvector"] = pd.Series(nx.eigenvector_centrality_numpy(core, weight="weight")).reindex(N.index).fillna(0)
N["pagerank"] = pd.Series(nx.pagerank(G, weight="weight"))
comm = N.community.to_dict()
N["participation"] = pd.Series({v: (1 - sum((np.array([sum(1 for u in G[v] if comm[u] == c) for c in set(comm[u] for u in G[v])]) / G.degree(v)) ** 2)) if G.degree(v) else 0.0 for v in G})
N["communities_reached"] = pd.Series({v: len(set(comm[u] for u in G[v])) for v in G})
M = ["degree", "strength", "betweenness", "eigenvector", "pagerank", "participation"]
out = {"largest_component": core.number_of_nodes(), "spearman_with_topic_size": {m: round(float(spearmanr(N[m], N.docs).statistic), 2) for m in M},
       "spearman_between": {f"{a}-{b}": round(float(spearmanr(N[a], N[b]).statistic), 2) for i, a in enumerate(M) for b in M[i + 1:]}}
cols = ["words", "theme", "community", "docs"] + M + ["communities_reached"]
for m in ("degree", "betweenness", "eigenvector", "participation"):
    top = N[N.degree >= 3].sort_values(m, ascending=False).head(10) if m == "participation" else N.sort_values(m, ascending=False).head(10)
    out[f"top_by_{m}"] = [{"topic": int(t), **{k: (round(float(v), 3) if isinstance(v, (float, np.floating)) else (int(v) if isinstance(v, (np.integer,)) else v)) for k, v in r[cols].items()}} for t, r in top.iterrows()]
# theme-level: mean degree and betweenness per theme
out["by_theme"] = N.groupby("theme").agg(topics=("docs", "size"), mean_degree=("degree", "mean"), mean_betweenness=("betweenness", "mean"),
                                          mean_participation=("participation", "mean")).round(3).sort_values("mean_degree", ascending=False).reset_index().to_dict("records")
for per in ("before", "from"):
    out[f"top_degree_{per}"] = N.sort_values(f"degree_{per}", ascending=False).head(8)[["words", "theme", f"degree_{per}"]].reset_index().to_dict("records")
(P / "topic_network_centrality.json").write_text(json.dumps(out, indent=1, default=float))
print(json.dumps({k: out[k] for k in ("largest_component", "spearman_with_topic_size")}))
for m in ("degree", "betweenness", "eigenvector", "participation"):
    print(f"\nTOP {m}")
    for r in out[f"top_by_{m}"][:8]:
        print(f"  [{r['topic']}] {r['words'][:40]:40s} {r['theme'][:22]:22s} c{r['community']} docs {r['docs']:>6} deg {r['degree']:>3} btw {r['betweenness']:.3f} eig {r['eigenvector']:.3f} part {r['participation']:.2f} reach {r['communities_reached']}")
print("\nBY THEME"); [print(" ", r) for r in out["by_theme"]]
for per in ("before", "from"):
    print(per, [(r["words"][:25], r[f"degree_{per}"]) for r in out[f"top_degree_{per}"][:6]])

# ---- layout and names for drawing (27 Nov): one layout for the all-years network, reused for the period panels and the paper figure
KEY_TOPICS = [(17, "Politics, distrust and evidence"), (4, "Diet, weight and saturated fat"), (1, "Omega-6 and animal foods"),
              (24, "Oils and cooking fats"), (23, "Home cooking and sugar"), (19, "Shopping")]  # named by a defining topic; the first three are coloured in the figures
cname = {}
for t, nm in KEY_TOPICS:
    cname.setdefault(int(N.loc[t, "community"]), nm)
linked = sorted(core.nodes)  # the largest connected component; the few small separate groups are listed in the caption, not drawn
Gl = G.subgraph(linked)
pos = nx.kamada_kawai_layout(Gl, weight="dist")
xy = np.array([pos[v] for v in linked]); lo, hi = xy.min(0), xy.max(0)
out["layout"] = {int(v): [round(float((pos[v][0] - lo[0]) / (hi[0] - lo[0])), 4), round(float((pos[v][1] - lo[1]) / (hi[1] - lo[1])), 4)] for v in linked}
out["community_names"] = {int(c): nm for c, nm in cname.items()}; out["coloured_communities"] = [int(N.loc[t, "community"]) for t, _ in KEY_TOPICS[:3]]
out["unlinked_topics"] = int((N.degree == 0).sum()); out["small_components"] = [sorted(int(x) for x in c) for c in nx.connected_components(G) if len(c) > 1 and len(c) < len(linked)]
K = len(N) - len(linked)
(P / "topic_network_centrality.json").write_text(json.dumps(out, indent=1, default=float))

# paper figure (PDF + PNG): A all years, B before 2024, C from 2024 (one of the equal-size samples), same positions
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
COL = {out["coloured_communities"][0]: "#2a78d6", out["coloured_communities"][1]: "#eb6834", out["coloured_communities"][2]: "#1baf7a"}
GREY, EDGE = "#b9b8b0", "#c3c2b7"
OFF = {4: (-70, 16), 1: (-62, -22), 14: (-78, 12), 0: (16, 10), 24: (8, 6), 9: (8, 6), 47: (-20, -16), 17: (12, -4)}  # label offsets (points)
def panel(ax, edges, title, labels=False, scale=1.0):  # noqa: E302
    for e_ in edges:
        if e_["a"] in pos and e_["b"] in pos:
            (x1, y1), (x2, y2) = out["layout"][e_["a"]], out["layout"][e_["b"]]
            pol = N.loc[e_["a"], "theme"] == "Politics" and N.loc[e_["b"], "theme"] == "Politics"
            ax.plot([x1, x2], [y1, y2], color="#2a78d6" if pol and not labels else EDGE, lw=1.6 if pol and not labels else 0.5, alpha=0.9 if pol and not labels else 0.55, zorder=1)
    for v in linked:
        x, y = out["layout"][v]; c = COL.get(int(N.loc[v, "community"]), GREY)
        ax.scatter(x, y, s=(8 + 0.035 * N.loc[v, "docs"]) * scale, color=c, edgecolors="white", linewidths=0.8, zorder=2)
    if labels:
        for v in [4, 1, 14, 0, 24, 9, 47, 17]:
            if v in pos:
                x, y = out["layout"][v]; ax.annotate(", ".join(N.loc[v, "words"].split(", ")[:2]), (x, y), xytext=OFF.get(v, (4, 4)), textcoords="offset points", fontsize=7, color="#0b0b0b", zorder=3, arrowprops=dict(arrowstyle="-", color="#898781", lw=0.5), bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
    ax.set_title(title, fontsize=9, loc="left"); ax.set_xticks([]); ax.set_yticks([]); [s.set_visible(False) for s in ax.spines.values()]
fig = plt.figure(figsize=(7.2, 4.4))
axA = fig.add_axes([0.0, 0.0, 0.62, 0.95]); axB = fig.add_axes([0.64, 0.5, 0.36, 0.45]); axC = fig.add_axes([0.64, 0.0, 0.36, 0.45])
panel(axA, d["edges_all"], "A  All years: 299 links between topics", labels=True)
panel(axB, d["edges_before"], f"B  Before 2024 ({len(d['edges_before'])} links)", scale=0.35); panel(axC, d["edges_from"], f"C  From 2024 ({len(d['edges_from'])} links)", scale=0.35)
from matplotlib.lines import Line2D  # noqa: E402
hand = [Line2D([], [], marker="o", ls="", color=COL[c], label=cname[c]) for c in out["coloured_communities"]] + [Line2D([], [], marker="o", ls="", color=GREY, label="other topic communities"),
        Line2D([], [], color="#2a78d6", lw=1.6, label="politics-politics link (B, C)")]
fig.legend(handles=hand, loc="lower center", ncol=3, fontsize=7, frameon=False, bbox_to_anchor=(0.5, -0.09))
Path("seedoils/figures").mkdir(exist_ok=True)
for ext in ("pdf", "png"):
    fig.savefig(f"seedoils/figures/topic_network.{ext}", dpi=200, bbox_inches="tight")
print("figure: seedoils/figures/topic_network.pdf/.png;", len(linked), "topics drawn (largest component);", out["unlinked_topics"], "without a link; small groups", out["small_components"])
