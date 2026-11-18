"""Figure for NETWORK STRUCTURES (upf/PLAN.md, 18 Nov): NOVA assortativity, observed vs within-category null, for four product-network structures.
Reads soj/network_structures.csv (network_structures.py). Writes upf/figures/network_structures.png.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/network_structures_plot.py
"""
import pandas as pd, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
D = pd.read_csv("upf/data/processed/soj/network_structures.csv")
lab = {"S1 full projection": "All links (any shared reviewer)", "S2 >= 2 shared reviewers": "Links with >= 2 shared reviewers", "S3 kNN cosine k=10": "Each product's 10 most similar",
       "S4 disparity backbone a=.01": "Disparity backbone (alpha .01)"}
fig, ax = plt.subplots(figsize=(9.5, 3.9)); y = np.arange(len(D))[::-1]
for yi, (_, r) in zip(y, D.iterrows()):
    ax.plot([r.null_weighted, r.assort_weighted], [yi, yi], color="#b4b2a9", lw=2, zorder=1)
    ax.scatter(r.null_weighted, yi, s=70, color="#888780", zorder=2); ax.scatter(r.assort_weighted, yi, s=90, color="#eb6834", zorder=3, edgecolor="white")
    ax.text(r.assort_weighted + 0.008, yi, f"{r.assort_weighted:+.2f}  (chance {r.null_weighted:+.2f})", va="center", fontsize=8.5)
ax.set_yticks(y, [f"{lab[s]}\n{p:,} products ({c:.0%}), {l:,} links" for s, p, c, l in zip(D.structure, D.products, D.share_connected, D.links)], fontsize=8.5)
ax.axvline(0, color="#d3d1c7", lw=0.8); ax.set_xlim(-0.02, 0.38); ax.tick_params(axis="x", labelsize=8)
for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0); ax.set_xlabel("NOVA assortativity (weighted): do links join products of the same processing level?", fontsize=8.5, color="#444441")
ax.set_title("Stricter link rules, more same-kind links; every version beats chance (p = .001)", loc="left", fontsize=10.5)
fig.text(0.01, 0.01, "Grocery products linked by reviewers with 2-50 matched grocery reviews. Orange = observed; grey = average of 1,000 shuffles of the NOVA labels within the same food category.\n"
         "92.5% of all links rest on a single shared reviewer. The backbone keeps only 6% of products and is for drawing, not for measuring (Week 4).", fontsize=7.3, color="#5f5e5a")
fig.tight_layout(rect=(0, 0.09, 1, 1)); fig.savefig("upf/figures/network_structures.png", dpi=170); print("saved")
