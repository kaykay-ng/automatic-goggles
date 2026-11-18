"""Binned view of PRODUCT LEAN (upf/PLAN.md): who reviews each food category, by reviewer group from hobby to health.
Reviewer lean (as product_lean.py, narrow sets) -> 5 groups by rank: hobby side split in two halves, 'neither' (lean exactly 0), health side split in two halves.
Per food category and processing level: share of its reviewers (unique people, all matched products) in each group. Rows ranked by mean group.
Writes upf/figures/product_bins.png and soj/product_bins.csv.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/product_bins_plot.py
"""
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Patch

C = Path("upf/data/processed/soj")
T = pd.read_csv(C / "shopper_types.csv.gz").set_index("user_id")
E = pd.read_csv(C / "elsewhere_reviews.csv.gz", usecols=["user_id", "parent_asin"]); E = E[E.user_id.isin(T.index)]
S = pd.read_csv(C / "all_subcategories.csv.gz", index_col=0); E["d"] = S.dept.reindex(E.parent_asin).values; E["s"] = S["sub"].reindex(E.parent_asin).values
HEALTH = {("Health_and_Household", "Vitamins, Minerals & Supplements"), ("Health_and_Household", "Diet & Sports Nutrition"),
          ("Health_and_Household", "Wellness & Relaxation"), ("Sports_and_Outdoors", "Exercise & Fitness")}
HOBBY = {("Toys_and_Games", s) for s in ("Toy Figures & Playsets", "Collectible Toys", "Games & Accessories", "Puzzles", "Building Toys", "Novelty & Gag Toys")} \
        | {("Sports_and_Outdoors", "Fan Shop"), ("Sports_and_Outdoors", "Memorabilia Display & Storage")}
tot = E.groupby("user_id").size().reindex(T.index)
h = E[[x in HEALTH for x in zip(E.d, E.s)]].groupby("user_id").size().reindex(T.index, fill_value=0)
b = E[[x in HOBBY or x[0] == "Video_Games" for x in zip(E.d, E.s)]].groupby("user_id").size().reindex(T.index, fill_value=0)
lean = (h - b) / tot
grp = pd.Series(3, index=T.index)
neg, pos = lean[lean < 0], lean[lean > 0]
grp[neg.index] = np.where(neg <= neg.median(), 1, 2); grp[pos.index] = np.where(pos >= pos.median(), 5, 4)
base = grp.value_counts(normalize=True).sort_index()
print("groups (share of reviewers):", base.round(3).to_dict(), "| hobby median", round(neg.median(), 3), "health median", round(pos.median(), 3))

P = pd.read_csv(C / "products.csv.gz", usecols=["parent_asin", "nova"]).drop_duplicates("parent_asin").set_index("parent_asin").nova
M = pd.read_csv("upf/data/processed/amazon_meta_compact.csv.gz", usecols=["parent_asin", "categories"]).drop_duplicates("parent_asin").set_index("parent_asin").categories
ROW = {"Snacks & Sweets > Candy & Chocolate": "Candy & chocolate", "Snacks & Sweets > Chocolate": "Candy & chocolate", "Snacks & Sweets > Chocolate Candy": "Candy & chocolate",
       "Breads & Bakery > Cookies": "Cookies", "Breakfast Foods > Toaster Pastries": "Toaster pastries", "Breakfast Foods > Cereals": "Breakfast cereals",
       "Beverages > Bottled Beverages, Water & Drink Mixes": "Bottled drinks & drink mixes", "Beverages > Tea": "Tea", "Beverages > Coffee": "Coffee",
       "Dairy, Eggs & Plant-Based Alternatives > Plant-Based Milk": "Milk & plant milk", "Dairy, Eggs & Plant-Based Alternatives > Milk & Cream": "Milk & plant milk",
       "Pantry Staples > Canned, Jarred & Packaged Foods": "Canned & packaged foods", "Pantry Staples > Soups, Stocks & Broths": "Soups & broths",
       "Pantry Staples > Sauces, Gravies & Marinades": "Sauces & condiments", "Pantry Staples > Condiments & Salad Dressings": "Sauces & condiments",
       "Pantry Staples > Cooking & Baking": "Cooking & baking", "Pantry Staples > Nut & Seed Butters": "Nut butters", "Pantry Staples > Herbs, Spices & Seasonings": "Herbs & spices"}
SNACK = {"Bars": "Snack & protein bars", "Chips & Crisps": "Chips & crisps", "Crackers": "Crackers", "Meat Snacks": "Jerky & meat snacks",
         "Popcorn": "Popcorn & pretzels", "Pretzels": "Popcorn & pretzels"}
pr = pd.read_csv(C / "reviewer_pairs.csv.gz").drop_duplicates(); pr = pr[pr.user_id.isin(T.index)]
lv = M.reindex(pr.parent_asin).fillna("").str.split("|").values
pr["row"] = [(SNACK.get(x[3]) if len(x) > 3 else None) if len(x) > 2 and x[2] == "Snack Foods" else (ROW.get(f"{x[1]} > {x[2]}") if len(x) > 2 else None) for x in lv]
pr["nova"] = P.reindex(pr.parent_asin).values; pr = pr.dropna(subset=["row", "nova"]); pr["upf"] = pr.nova.eq(4)
u = pr.drop_duplicates(["user_id", "row", "upf"]).assign(g=lambda d: d.user_id.map(grp))
tab = u.groupby(["row", "upf", "g"]).size().unstack(fill_value=0); n = tab.sum(1); share = tab.div(n, axis=0)
score = u.groupby("row").g.mean().sort_values()                                                     # low = hobby
order = list(score.index)
share.assign(reviewers=n).round(4).to_csv(C / "product_bins.csv")

COL = {1: "#eb6834", 2: "#f5b496", 3: "#d3d1c7", 4: "#98bdec", 5: "#2a78d6"}
LAB = {1: "strong hobby", 2: "some hobby", 3: "neither", 4: "some health-coded", 5: "strong health-coded"}
MINN = 200
pooled = u.g.value_counts(normalize=True).reindex(range(1, 6)).values          # same weighting as the category bars: a person counts once per bar they appear in
rows = [("Average food bar", None, pooled, len(u))]
for r in order:
    for up in (True, False):
        if (r, up) in share.index and n[(r, up)] >= MINN: rows.append((r, up, share.loc[(r, up)].reindex(range(1, 6), fill_value=0).values, n[(r, up)]))
fig, ax = plt.subplots(figsize=(10.5, 10)); y = 0; yt, yl = [], []; prev = None
for r, up, v, nn in rows:                                                       # diverging: centre = middle of 'neither'; hobby left, health right
    if r != prev and prev is not None: y += 0.45
    left = -(v[0] + v[1] + v[2] / 2)
    for k, w in enumerate(v, start=1):
        ax.barh(y, w, left=left, color=COL[k], edgecolor="white", linewidth=1.2, height=0.78 if up is None else 0.72)
        if w >= 0.08: ax.text(left + w / 2, y, f"{w:.0%}", ha="center", va="center", fontsize=6.8, color="white" if k in (1, 5) else "#2c2c2a")
        left += w
    yt.append(y); yl.append(("Average food bar" if up is None else (f"{r}   " if r != prev else "") + ("ultra-processed" if up else "less processed")) + ("" if up is None else f"  ({nn:,})"))
    prev = r; y += 1
for x in (-(pooled[0] + pooled[1] + pooled[2] / 2), pooled[2] / 2 + pooled[3] + pooled[4]): ax.axvline(x, color="#2c2c2a", lw=0.8, ls=(0, (3, 3)), zorder=3)
ax.axvline(0, color="#888780", lw=0.8, zorder=0)
ax.set_yticks(yt, yl, fontsize=7.8); ax.set_ylim(y - 0.4, -0.7); ax.tick_params(axis="y", length=0)
ax.set_xlim(-0.55, 0.85); tk = [-0.5, -0.25, 0, 0.25, 0.5, 0.75]; ax.set_xticks(tk, [f"{abs(t):.0%}" for t in tk], fontsize=8)
for s_ in ("top", "right", "left"): ax.spines[s_].set_visible(False)
ax.text(-0.02, -0.045, "← hobby-focused reviewers", transform=ax.get_xaxis_transform(), ha="right", va="top", fontsize=8.5, color="#c4501f")
ax.text(0.02, -0.045, "health-focused reviewers →", transform=ax.get_xaxis_transform(), ha="left", va="top", fontsize=8.5, color="#1f5fae")
ax.legend(handles=[Patch(color=COL[k], label=LAB[k]) for k in range(1, 6)], ncol=5, frameon=False, fontsize=8, loc="lower left", bbox_to_anchor=(0, 1.0), handlelength=1)
ax.set_title("Who reviews each kind of food: hobby-focused to the left, health-focused to the right", loc="left", fontsize=11, pad=24)
fig.text(0.01, 0.01, "Reviewer groups from the share of non-food reviews that are health-coded (vitamins, sports nutrition, wellness, exercise) minus hobby (figures, collectibles, games,\n"
         "puzzles, building toys, video games, fan shop). Hobby side and health side each split at their median; 'neither' (grey) = no hobby or health-coded reviews, centred on 0.\n"
         "Bar = that category's reviewers (people, in brackets) by group. Average food bar = all category bars pooled. Dashed lines = its edges: a bar reaching further left than the left line\n"
         f"has more hobby reviewers than usual. Compare the two bars in a row. Rows ranked from hobby (top) to health (bottom); bars with < {MINN} reviewers left out.",
         fontsize=7.2, color="#5f5e5a")
fig.tight_layout(rect=(0, 0.085, 1, 1)); fig.savefig("upf/figures/product_bins_diverging.png", dpi=170); print("saved upf/figures/product_bins_diverging.png")
print("pooled", pooled.round(3))
