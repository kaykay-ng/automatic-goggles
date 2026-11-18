"""Figure for SHOPPER TYPES (upf/PLAN.md): ALL-UPF share of each shopper type minus its expected share (given activity), with 95% intervals.
Type names are our reading of each type's over-represented sub-categories (data/processed/shopper_types.txt).
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/shopper_types_plot.py
"""
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

O = pd.read_csv("upf/data/processed/soj/shopper_types_summary.csv").set_index("type")
NAME = {17: "Collectors (action figures, fan shop)", 3: "Gamers (consoles, PC games)", 30: "Party & novelty gifts", 20: "Little kids' toys (plush, preschool)",
        0: "Toy builders & crafters (building sets, dolls, STEM)", 14: "Sports fans with dogs", 18: "Small-pet & reptile keepers", 13: "Puzzles & mobility aids",
        7: "Aquarium keepers", 1: "Baby gear (feeding, strollers)", 6: "Mobility & medical supplies", 4: "Cat & dog owners who take supplements",
        2: "Outdoors (hunting, fishing, sport)", 9: "Grooming, oral & vision care", 5: "Fitness & oral care", 10: "Wellness & supplements",
        28: "Heart health & Whole Foods", 8: "Sports nutrition", 37: "Natural & organic women's health"}
D = O.loc[list(NAME)].copy(); D["name"] = [NAME[t] for t in D.index]
D["se"] = np.sqrt(D.upf_share * (1 - D.upf_share) / D.reviewers) * 100; D = D.sort_values("diff_pts")
fig, ax = plt.subplots(figsize=(9, 7.2)); y = np.arange(len(D))
col = np.where(D.diff_pts > 0, "#eb6834", "#2a78d6")
ax.barh(y, D.diff_pts, color=col, height=0.62, zorder=2)
ax.errorbar(D.diff_pts, y, xerr=1.96 * D.se, fmt="none", ecolor="#5f5e5a", elinewidth=0.9, capsize=2, zorder=3)
ax.axvline(0, color="#888780", lw=0.8, zorder=1)
ax.set_yticks(y, [f"{n}  ({r:,})" for n, r in zip(D.name, D.reviewers)], fontsize=8.5)
ax.set_xlabel("share of all-ultra-processed grocery reviewers, minus expected (percentage points)", fontsize=9)
for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0); ax.grid(axis="x", color="#e1e0d9", lw=0.6, zorder=0)
ax.text(0.99, 0.02, "more ultra-processed →", transform=ax.transAxes, ha="right", fontsize=8.5, color="#993c1d")
ax.text(0.01, 0.98, "← less processed", transform=ax.transAxes, ha="left", va="top", fontsize=8.5, color="#185fa5")
ax.set_title("Shopper types found from what people review outside groceries", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "58,391 grocery reviewers with >= 5 non-food reviews, grouped by cosine similarity of their sub-category profiles (kNN network, Louvain; 19 of 45 types shown, n in brackets).\n"
         "Bar: share whose grocery reviews are all ultra-processed (NOVA 4), minus the share expected from how active its members are (overall ~46%). Whiskers: 95% intervals.\n"
         "Type names are our reading of each type's most over-represented sub-categories. Groceries are not used to form the types.\n"
         "Settings tried (8 runs): minimum 3, 5, 10 or 20 non-food reviews; 5, 10 or 20 neighbours; Louvain resolution 0.5, 1 or 2.\n"
         "The leaning types keep their direction in every run (p <= .002).", fontsize=7, color="#5f5e5a")
fig.tight_layout(rect=(0, 0.1, 1, 1)); fig.savefig("upf/figures/shopper_types.png", dpi=170); print("saved upf/figures/shopper_types.png")
