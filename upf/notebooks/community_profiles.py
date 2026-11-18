"""What the reviewer communities (Louvain on the cosine kNN network, shopper_types.py) have in common, WITHOUT naming them.
For the 15 largest communities: share of members who reviewed >= 1 product in each Amazon sub-category (columns = each community's 3 most distinctive
sub-categories reviewed by >= 25% of its members, plus the 4 reviewed most often overall). Communities are numbered by size.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/community_profiles.py
"""
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

C = Path("upf/data/processed/soj")
T = pd.read_csv(C / "shopper_types.csv.gz").set_index("user_id"); O = pd.read_csv(C / "shopper_types_summary.csv").set_index("type")
E = pd.read_csv(C / "elsewhere_reviews.csv.gz", usecols=["user_id", "parent_asin"]); E = E[E.user_id.isin(T.index)]
S = pd.read_csv(C / "all_subcategories.csv.gz", index_col=0)
short = {"Health_and_Household": "H&H", "Pet_Supplies": "Pets", "Toys_and_Games": "Toys", "Video_Games": "Video Games", "Sports_and_Outdoors": "Sports",
         "Baby_Products": "Baby", "Health_and_Personal_Care": "Personal Care"}
E["cat"] = (S.dept.map(short) + " > " + S["sub"]).reindex(E.parent_asin).values; E = E.dropna(subset=["cat"]); E = E[~E.cat.str.endswith("unknown")]
E["type"] = E.user_id.map(T.type)
have = E.drop_duplicates(["user_id", "cat"]); size = T.type.value_counts()
tops = size.index[:15]
prev = have[have.type.isin(tops)].groupby(["type", "cat"]).size().unstack(fill_value=0).div(size[tops], axis=0)
overall = have.groupby("cat").size() / len(T)
cols = list(overall.sort_values(ascending=False).index[:4])
for t in tops:
    p = prev.loc[t]; lift = (p / overall.reindex(p.index)).where(p >= 0.25).dropna().sort_values(ascending=False)
    cols += [c for c in lift.index[:3] if c not in cols]
H = prev.reindex(columns=cols).fillna(0); H.index = [f"C{i + 1}" for i in range(len(tops))]
print("members per community:", dict(zip(H.index, size[tops].values)))
lean = O.diff_pts.reindex(tops).values

fig, (ax, ax2) = plt.subplots(1, 2, figsize=(14, 8.4), gridspec_kw=dict(width_ratios=[len(cols), 2.2], wspace=0.04))
im = ax.imshow(H.values, cmap="Blues", vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(len(cols)), [c.replace(" > ", ": ") for c in cols], rotation=55, ha="right", rotation_mode="anchor", fontsize=7.5)
ax.set_yticks(range(len(H)), [f"{r}  ({n:,})" for r, n in zip(H.index, size[tops].values)], fontsize=8.5)
for i in range(H.shape[0]):
    for j in range(H.shape[1]):
        v = H.values[i, j]
        if v >= 0.15: ax.text(j, i, f"{v:.0%}", ha="center", va="center", fontsize=6.4, color="white" if v > 0.55 else "#0c447c")
ax.axvline(3.5, color="#2c2c2a", lw=1); ax.text(1.5, -0.9, "reviewed by most people", ha="center", fontsize=8, color="#444441")
ax.text(3.5 + (len(cols) - 3.5) / 2, -0.9, "each community's most distinctive sub-categories", ha="center", fontsize=8, color="#444441")
for s in ax.spines.values(): s.set_visible(False)
ax2.barh(range(len(H)), lean, color=["#eb6834" if v > 0 else "#2a78d6" for v in lean], height=0.6); ax2.invert_yaxis(); ax2.set_ylim(len(H) - 0.5, -0.5)
ax2.axvline(0, color="#888780", lw=0.8); ax2.set_yticks([]); ax2.set_xlim(-14, 14); ax2.tick_params(labelsize=7)
for i, v in enumerate(lean): ax2.text(v + (0.6 if v > 0 else -0.6), i, f"{v:+.1f}", va="center", ha="left" if v > 0 else "right", fontsize=7)
ax2.set_title("groceries: points vs\nexpected all-UPF", fontsize=8); [ax2.spines[s].set_visible(False) for s in ("top", "right", "left")]
fig.suptitle("What the 15 largest reviewer communities have in common (share of members who reviewed at least one product in each sub-category)", x=0.01, ha="left", fontsize=11)
fig.text(0.01, 0.01, "Communities: Louvain on the network linking each of 58,391 reviewers to the 10 with the most similar non-food reviewing (cosine). Numbered by size; members in brackets.\n"
         "Cell = share of the community's members who reviewed at least one product there (H&H = Health & Household).\n"
         "Columns: the 4 sub-categories most people review, then each community's 3 most over-represented ones that at least 25% of its members reviewed. Groceries not used to form communities.",
         fontsize=7.3, color="#5f5e5a")
fig.subplots_adjust(left=0.08, right=0.98, bottom=0.31, top=0.89); fig.savefig("upf/figures/community_profiles.png", dpi=170); print("saved upf/figures/community_profiles.png")
H.round(3).assign(members=size[tops].values, lean=lean).to_csv(C / "community_profiles.csv")
