"""Figure for the matched-product ingredient network (matched_ingredient_network.py).
Run from final_project/:  ./.venv-nlp/bin/python upf/notebooks/matched_ingredient_network_plot.py  -> upf/figures/matched_ingredient_network.png
Left: the 220 most common ingredients and the backbone links among them, coloured by top-level Louvain community; spring layout on the full backbone.
Right: second-level communities, members' median NOVA-4 share (share of an ingredient's products that are NOVA 4), coloured by parent community. Names are our reading.
"""
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

SOJ = Path("upf/data/processed/soj")
N = pd.read_csv(SOJ / "matched_ingredient_nodes.csv", dtype={"sub": str}); E = pd.read_csv(SOJ / "matched_ingredient_edges.csv.gz")
COL = {0: "#2a78d6", 1: "#eb6834", 2: "#1baf7a", 3: "#eda100", 4: "#e87ba4"}; GREY = "#b4b2a9"; INK = "#2c2c2a"; MUTED = "#5f5e5a"
TOP = {0: "Savoury: sauces, seasoning, meat, world cooking", 1: "'Clean label': cane sugar, sea salt, nuts, grains, fruit", 2: "Grain: enriched flour, bakery, fortified cereal",
       3: "Confectionery: chocolate, candy, dyes, sweeteners", 4: "Dairy & cheese", 5: "French-language lists"}
SUB = {"0.0": "condiments & dressings", "0.1": "fresh-veg cooking", "0.2": "savoury snack seasoning", "0.3": "processed meat", "0.4": "Asian cooking (soy, sesame)",
       "1.0": "fruit, gums, stevia drinks", "1.1": "cane sugar, sea salt, starches", "1.2": "nuts, honey, baking", "1.3": "whole grains",
       "2.0": "enriched flour", "2.1": "fortification (cereals)", "2.2": "cakes, mixes, HFCS", "2.3": "bread dough conditioners",
       "3.0": "chocolate & sweet bakery", "3.1": "candy & dyes", "3.2": "sweeteners & gum", "3.3": "dye lakes & coatings", "4": "dairy & cheese", "5": "French-language lists"}

G = nx.Graph(); G.add_weighted_edges_from(E.itertuples(index=False))
Gl = nx.Graph(); Gl.add_edges_from((a, b, {"w": np.log1p(w)}) for a, b, w in E.itertuples(index=False))
pos = nx.spring_layout(Gl, weight="w", seed=4, iterations=200, k=0.09)
show = N.sort_values("n_products", ascending=False).head(220).set_index("ingredient")
S = G.subgraph(show.index)

fig = plt.figure(figsize=(15, 8.2), facecolor="white")
ax = fig.add_axes([0.01, 0.06, 0.55, 0.84]); bx = fig.add_axes([0.66, 0.08, 0.32, 0.80])
ws = np.array([d["weight"] for *_, d in S.edges(data=True)]); cut = np.quantile(ws, 0.5)
for a, b, d in S.edges(data=True):
    if d["weight"] < cut: continue
    (x1, y1), (x2, y2) = pos[a], pos[b]; same = show.community[a] == show.community[b]
    ax.plot([x1, x2], [y1, y2], color=COL.get(show.community[a], GREY) if same else "#d3d1c7", lw=0.4, alpha=0.35 if same else 0.25, zorder=1)
for ing, r in show.iterrows():
    ax.scatter(*pos[ing], s=8 + 400 * r.n_products / show.n_products.max(), color=COL.get(r.community, GREY), edgecolor="white", linewidth=0.8, zorder=2)
placed = []; span = np.ptp(np.array(list(pos.values())), axis=0)
for ing in show.groupby("community").head(12).index:                      # most common first; skip a label that would collide with one already placed
    x, y = pos[ing]
    if any(abs(x - px) < 0.07 * span[0] and abs(y - py) < 0.011 * span[1] for px, py in placed): continue
    placed.append((x, y)); ax.text(x, y, " " + ing, fontsize=6.8, color=INK, va="center", zorder=3)
ax.axis("off")
handles = [plt.Line2D([], [], marker="o", ls="", color=COL.get(c, GREY), markersize=7, label=f"C{c} {TOP[c]} ({(N.community == c).sum()})") for c in sorted(N.community.unique())]
ax.legend(handles=handles, loc="lower left", fontsize=7.4, frameon=False, labelcolor=INK)
fig.text(0.015, 0.955, "Ingredient network of 56,277 Open Food Facts products matched to Amazon grocery listings", fontsize=12.5, color=INK, weight="bold")
fig.text(0.015, 0.925, "Dot = ingredient (220 most common of 1,146 shown; area = products). Lines = backbone links (disparity filter), stronger half. "
         "Colour = Louvain community (modularity .19; unweighted .25 vs rewired null .11)", fontsize=8, color=MUTED)

# right: sub-communities
R = (N.assign(sub=N["sub"].astype(str)).groupby("sub").agg(n=("ingredient", "size"), nova4=("nova4_share", "median"), community=("community", "first"))
     .reset_index().query("n >= 5").sort_values(["nova4"]))
for yi, r in enumerate(R.itertuples()):
    bx.plot([0, r.nova4 * 100], [yi, yi], color="#e6e8e1", lw=1, zorder=1)
    bx.scatter(r.nova4 * 100, yi, s=20 + r.n * 0.9, color=COL.get(r.community, GREY), edgecolor="white", linewidth=1, zorder=2)
bx.set_yticks(range(len(R))); bx.set_yticklabels([f"{SUB.get(s, s)}  (C{s}, {n})" for s, n in zip(R["sub"], R.n)], fontsize=7.6, color=INK)
bx.set_xlim(40, 102); bx.set_xlabel("members' median NOVA-4 share (%)", fontsize=8, color=MUTED)
bx.axvline(71, color=GREY, lw=0.8, ls="--"); bx.text(71.5, len(R) - 0.4, "all products 71%", fontsize=7, color=MUTED)
for sp in ["top", "right", "left"]: bx.spines[sp].set_visible(False)
bx.tick_params(axis="y", length=0); bx.tick_params(axis="x", colors=MUTED, labelsize=7.5); bx.grid(axis="x", color="#eeeeea", lw=0.6); bx.set_axisbelow(True)
bx.set_title("Second-level communities: how ultra-processed are their ingredients?", fontsize=9.5, color=INK, loc="left")
fig.text(0.66, 0.02, "NOVA-4 share of an ingredient = share of the listings using it that are NOVA 4; dot area = ingredients. Exploratory.", fontsize=7, color=MUTED)
fig.savefig("upf/figures/matched_ingredient_network.png", dpi=170)
print("saved upf/figures/matched_ingredient_network.png")
