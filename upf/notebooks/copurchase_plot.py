"""Figure for the 2018 CO-PURCHASE NETWORK (upf/PLAN.md, 18 Nov): (left) the 20 largest Louvain communities as a community-level map;
(right) each community's ultra-processed share vs what its mix of food categories predicts. Names are our reading of each community's distinctive title words.
Reads soj/copurchase_edges.csv.gz, copurchase_membership.csv.gz, copurchase_communities_described.csv. Writes upf/figures/copurchase_missions.png.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/copurchase_plot.py
"""
import numpy as np, pandas as pd, networkx as nx
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

C = "upf/data/processed/soj/"
E = pd.read_csv(C + "copurchase_edges.csv.gz"); mem = pd.read_csv(C + "copurchase_membership.csv.gz").set_index("node").community
D = pd.read_csv(C + "copurchase_communities_described.csv")
size = mem.value_counts(); top = list(size.index[:20])
NAME = ["Chilled & frozen\nconvenience", "Whole-food baking\n& health", "Boxed sides\n& convenience", "Holiday candy", "Organic & natural", "Gluten-free\n& allergy",
        "World cooking", "Ready-to-drink\ncoffee & drinks", "Southern spices\n& seasonings", "Tea time", "Vegan & specialty\nbaking", "Nuts, olives\n& deli snacks",
        "Desserts &\nbaking mixes", "Coffee & cocktails\nat home", "Hot sauces", "Barbecue", "Regional sauces\n& relishes", "Fish & Latin\npantry", "Drink mixes", "Classic cereals"]
D["name"] = NAME; D["comm"] = top; D = D.set_index("comm")
cmap = LinearSegmentedColormap.from_list("d", ["#2a78d6", "#d3d1c7", "#eb6834"]); norm = TwoSlopeNorm(0, -20, 20)

# community-level graph
E["ca"], E["cb"] = E.p.map(mem), E.q.map(mem); X = E[(E.ca != E.cb) & E.ca.isin(top) & E.cb.isin(top)]
L = X.assign(u=X[["ca", "cb"]].min(axis=1), v=X[["ca", "cb"]].max(axis=1)).groupby(["u", "v"]).w.sum()
G = nx.Graph(); G.add_nodes_from(top)
for (u, v), n in L.items(): G.add_edge(u, v, s=n / np.sqrt(size[u] * size[v]))
smax = max(d["s"] for *_, d in G.edges(data=True))
for *_, d in G.edges(data=True): d["d"] = 1.0 + 3.0 * (1 - np.log1p(9 * d["s"] / smax) / np.log(10))
pos = nx.kamada_kawai_layout(G, dist=dict(nx.shortest_path_length(G, weight="d")))
P = np.array([pos[c] for c in top]); u_ = np.ptp(P[:, 0]) / 600; R = np.sqrt(60 + 0.9 * size[top].values) / 2 * u_
for _ in range(400):
    mv = False
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            dv = P[j] - P[i]; dist = np.hypot(*dv); need = R[i] + R[j] + 26 * u_
            if dist < need: st = (need - dist) / 2 * dv / (dist + 1e-9); P[i] -= st; P[j] += st; mv = True
    if not mv: break
pos = {c: P[k] for k, c in enumerate(top)}

fig = plt.figure(figsize=(15, 8.6)); ax = fig.add_axes([0.01, 0.1, 0.52, 0.78]); ax.set_axis_off(); bx = fig.add_axes([0.68, 0.12, 0.3, 0.78])
sv = sorted((d["s"] for *_, d in G.edges(data=True)), reverse=True); thr = sv[min(45, len(sv) - 1)]
for a, b, d in G.edges(data=True):
    if d["s"] < thr: continue
    (x1, y1), (x2, y2) = pos[a], pos[b]; ax.plot([x1, x2], [y1, y2], color="#888780", lw=0.5 + 5 * d["s"] / smax, alpha=0.35, zorder=1)
for k, c in enumerate(top):
    x, y = pos[c]; s = 60 + 0.9 * size[c]
    ax.scatter(x, y, s=s, color=cmap(norm(100 * D.loc[c, "diff"])), edgecolor="white", linewidth=1.5, zorder=2)
    ax.text(x, y - (np.sqrt(s) / 2 + 4) * u_ * 1.0, f"{D.loc[c, 'name']}\n{D.loc[c, 'upf']:.0%} UPF", ha="center", va="top", fontsize=7.6, color="#2c2c2a", linespacing=1.05, zorder=3)
fig.text(0.015, 0.965, "Products bought together form shopping missions", fontsize=12.5)
fig.text(0.015, 0.94, "Bubble = a community of products (area = products); lines = strongest also-bought ties between communities", fontsize=8, color="#5f5e5a", va="top")

S = D.sort_values("diff"); y = np.arange(len(S))[::-1]
for yi, (_, r) in zip(y, S.iterrows()):
    col = cmap(norm(100 * r["diff"]))
    bx.plot([100 * r.expected, 100 * r.upf], [yi, yi], color="#b4b2a9", lw=2, zorder=1)
    bx.scatter(100 * r.expected, yi, s=36, color="#888780", zorder=2); bx.scatter(100 * r.upf, yi, s=60, color=col, edgecolor="white", zorder=3)
bx.set_yticks(y, [f"{n.replace(chr(10), ' ')}  {100 * d:+.0f}" for n, d in zip(S.name, S["diff"])], fontsize=8)
bx.set_xlim(20, 102); bx.set_xticks([25, 50, 75, 100], ["25%", "50%", "75%", "100%"], fontsize=8)
for s_ in ("top", "right", "left"): bx.spines[s_].set_visible(False)
bx.tick_params(axis="y", length=0); bx.grid(axis="x", color="#e6e8e1", lw=0.6); bx.set_axisbelow(True)
bx.set_title("Ultra-processed share: observed (colour) vs\nexpected from the community's food categories (grey)", loc="left", fontsize=9.5)
fig.text(0.01, 0.015, "Amazon 'also bought' lists (2018 metadata, Ni, Li & McAuley 2019) between 18,415 grocery products matched to Open Food Facts; 78,781 links. Louvain on the giant component (17,464 products):\n"
         "60 communities, modularity 0.70 (20 largest shown; membership moderately stable across runs, adjusted Rand 0.56). Names are our reading of each community's most distinctive title words (TF-IDF).\n"
         "Colour = observed minus expected UPF share in points (blue = less processed than its food mix predicts, orange = more). Descriptive; not yet tested against a shuffle.", fontsize=7.3, color="#5f5e5a")
fig.savefig("upf/figures/copurchase_missions.png", dpi=170); print("saved upf/figures/copurchase_missions.png")
