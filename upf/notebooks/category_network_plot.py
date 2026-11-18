"""Block heatmap for the CATEGORY CO-REVIEW NETWORK (exploratory; category_network.py): food x non-food sub-categories, grouped by bipartite Louvain cluster.
Cell = shared reviewers relative to reviewers with the same number of non-food categories (1 = as expected). Writes upf/figures/category_clusters.png.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/category_network_plot.py
"""
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
C = "upf/data/processed/soj/"
ND = pd.read_csv(C + "category_nodes.csv").set_index("node"); R = pd.read_csv(C + "category_food_nonfood_rel.csv", index_col=0)
NAME = {0: "Young families", 1: "Pantry & home care", 2: "Health & fitness", 3: "Treats & gaming"}
NF_PER, F_PER = 6, 7
rows, cols, rb, cb = [], [], [], []
for c in NAME:
    m = ND[ND.bicluster == c]; f = m[m.food].sort_values("reviewers", ascending=False).index[:F_PER]; n = m[~m.food].sort_values("reviewers", ascending=False).index[:NF_PER]
    rows += list(f); cols += list(n); rb.append(len(rows)); cb.append(len(cols))
M = R.loc[rows, cols].values
cmap = LinearSegmentedColormap.from_list("d", ["#2a78d6", "#f1f0ea", "#eb6834"])
fig, ax = plt.subplots(figsize=(12, 9.6)); im = ax.imshow(M, cmap=cmap, norm=TwoSlopeNorm(1, 0.6, 1.6), aspect="auto")
ax.set_yticks(range(len(rows)), [f"{r[7:]}  ({ND.upf_share[r]:.0%} UPF)" for r in rows], fontsize=8)
ax.set_xticks(range(len(cols)), [c.replace(" > ", ": ").replace("Sports & Outdoor Recreation Accessories", "Outdoor Rec. Accessories").replace("Bathroom Safety, Aids & Accessories", "Bathroom Safety Aids").replace("Vitamins, Minerals & Supplements", "Vitamins & Supplements") for c in cols], rotation=55, ha="right", rotation_mode="anchor", fontsize=7.8)
for b in rb[:-1]: ax.axhline(b - 0.5, color="#2c2c2a", lw=1.2)
for b in cb[:-1]: ax.axvline(b - 0.5, color="#2c2c2a", lw=1.2)
starts = [0] + rb[:-1]
for (c, nm), s, e in zip(NAME.items(), starts, rb):
    m = ND[(ND.bicluster == c) & ND.food]; u = (m.upf_share * m.reviewers).sum() / m.reviewers.sum()
    ax.text(len(cols) - 0.3, (s + e - 1) / 2, f"  {nm}\n  food {u:.0%} UPF", va="center", ha="left", fontsize=9, fontweight="bold", color="#2c2c2a")
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        if M[i, j] >= 1.25 or M[i, j] <= 0.8: ax.text(j, i, f"{M[i, j]:.1f}", ha="center", va="center", fontsize=6.3, color="#2c2c2a")
cax = fig.add_axes([0.62, 0.115, 0.2, 0.012]); cb_ = fig.colorbar(im, cax=cax, orientation="horizontal"); cb_.set_label("reviewers of both, relative to expected", fontsize=7.5); cb_.ax.tick_params(labelsize=7)
ax.set_title("Of those who reviewed a kind of food, which non-food categories did they also review?", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "141,977 reviewers with >= 3 matched grocery reviews. Cell: reviewers of both, divided by what reviewers with the same number of non-food categories would give (1 = as expected;\n"
         "H&H = Health & Household; orange = more, blue = fewer; numbers shown from 1.25 up or 0.8 down). Groups: Louvain on the food x non-food network (links > 1.15x, >= 50 shared reviewers); 4 largest of 6 shown,\n"
         "top 7 foods and 6 non-food categories by size. Group names are our reading. Exploratory; group membership changes somewhat between runs (adjusted Rand 0.69 over 10 seeds).", fontsize=7.2, color="#5f5e5a")
fig.subplots_adjust(left=0.27, right=0.84, top=0.95, bottom=0.3); fig.savefig("upf/figures/category_clusters.png", dpi=170); print("saved")
