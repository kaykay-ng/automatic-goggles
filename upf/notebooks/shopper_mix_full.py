"""Descriptive figure for SHOPPER TYPES (upf/PLAN.md): each type's full review mix, groceries included.
Groceries = members' reviews of matched grocery products (soj/reviewer_categories.csv.gz: n reviews, UPF share), split into ultra-processed (NOVA 4) and less processed.
Non-food = members' reviews in the 7 other departments (soj/elsewhere_reviews.csv.gz), grouped by Amazon sub-category into 7 groups + other.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/shopper_mix_full.py
"""
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

C = Path("upf/data/processed/soj")
T = pd.read_csv(C / "shopper_types.csv.gz").set_index("user_id")
R = pd.read_csv(C / "reviewer_categories.csv.gz", usecols=["user_id", "n", "upf"]).set_index("user_id").reindex(T.index)
E = pd.read_csv(C / "elsewhere_reviews.csv.gz", usecols=["user_id", "parent_asin"]); E = E[E.user_id.isin(T.index)]
S = pd.read_csv(C / "all_subcategories.csv.gz", index_col=0); E["dept"] = S.dept.reindex(E.parent_asin).values; E["sub"] = S["sub"].reindex(E.parent_asin).values
DIFF = pd.read_csv(C / "shopper_types_summary.csv").set_index("type").diff_pts
NAME = {17: "Collectors (figures, fan shop)", 3: "Gamers (consoles, PC games)", 30: "Party & novelty gifts", 20: "Little kids' toys",
        0: "Toy builders & crafters", 14: "Sports fans with dogs", 18: "Small-pet & reptile keepers", 13: "Puzzles & mobility aids",
        7: "Aquarium keepers", 1: "Baby gear", 6: "Mobility & medical supplies", 4: "Pet owners who take supplements",
        2: "Outdoors (hunting, fishing)", 9: "Grooming, oral & vision care", 5: "Fitness & oral care", 10: "Wellness & supplements",
        28: "Heart health & Whole Foods", 8: "Sports nutrition", 37: "Natural & organic women's health"}


def group(d, s):
    if d == "Health_and_Household":
        if s == "Household Supplies": return "Household supplies"
        if s in ("Baby & Child Care",): return "Baby"
        if s in ("Stationery & Gift Wrapping Supplies",) or "Coupon" in str(s) or "Save" in str(s) or s == "unknown": return "Other"
        return "Health, vitamins & care"
    return {"Health_and_Personal_Care": "Health, vitamins & care", "Pet_Supplies": "Pets", "Toys_and_Games": "Toys & games", "Video_Games": "Video games",
            "Sports_and_Outdoors": "Sports & outdoors", "Baby_Products": "Baby"}.get(d, "Other")


E["g"] = [group(d, s) for d, s in zip(E.dept, E["sub"])]; E["type"] = E.user_id.map(T.type)
SEG = [("Ultra-processed groceries", "#444441"), ("Less processed groceries", "#b4b2a9"), ("Household supplies", "#2a78d6"), ("Health, vitamins & care", "#6250d6"),
       ("Pets", "#1baf7a"), ("Toys & games", "#eb6834"), ("Video games", "#eda100"), ("Sports & outdoors", "#008300"), ("Baby", "#e87ba4"), ("Other", "#e1e0d9")]
rows = {}
for t in NAME:
    m = T.index[T.type == t]; g = E[E.type == t].g.value_counts()
    g["Ultra-processed groceries"] = (R.n[m] * R.upf[m]).sum(); g["Less processed groceries"] = (R.n[m] * (1 - R.upf[m])).sum()
    rows[t] = g / g.sum()
M = pd.DataFrame(rows).T.reindex(columns=[s for s, _ in SEG]).fillna(0)
order = sorted(NAME, key=lambda t: -DIFF[t]); M = M.loc[order]
M.round(4).assign(name=[NAME[t] for t in order]).to_csv(C / "shopper_mix_full.csv")

fig, ax = plt.subplots(figsize=(11, 8)); y = np.arange(len(order))[::-1]; left = np.zeros(len(order))
for s, col in SEG:
    v = M[s].values; ax.barh(y, v, left=left, color=col, edgecolor="white", linewidth=1.2, height=0.7, label=s)
    for yi, l, w in zip(y, left, v):
        if w >= 0.06: ax.text(l + w / 2, yi, f"{w:.0%}", ha="center", va="center", fontsize=7.3, color="#2c2c2a" if col in ("#b4b2a9", "#e1e0d9", "#eda100") else "white")
    left += v
ax.set_yticks(y, [f"{NAME[t]}  {DIFF[t]:+.1f}" for t in order], fontsize=8.6); ax.set_xlim(0, 1)
ax.set_xticks([0, .25, .5, .75, 1], ["0", "25%", "50%", "75%", "100%"], fontsize=8)
for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.legend(ncol=5, frameon=False, fontsize=8, loc="lower left", bbox_to_anchor=(0, 1.0), handlelength=1, columnspacing=1.2)
ax.set_title("What each shopper type reviews, groceries included", loc="left", fontsize=11.5, pad=40)
fig.text(0.01, 0.01, "Each bar: all reviews by the type's members (matched groceries + 7 other departments), by group of Amazon sub-categories. Number after the name: points by which the type\n"
         "has more (+) or fewer (-) members whose grocery reviews are all ultra-processed than expected. Types are ordered by that number. 'Other' = stationery, promotions, unknown.\n"
         "Types were found from non-food reviews only. Groceries here count only products matched to Open Food Facts.", fontsize=7.3, color="#5f5e5a")
fig.tight_layout(rect=(0, 0.06, 1, 1)); fig.savefig("upf/figures/shopper_mix_full.png", dpi=170); print("saved upf/figures/shopper_mix_full.png")
print((100 * M[["Ultra-processed groceries", "Less processed groceries", "Household supplies", "Health, vitamins & care"]]).round(1).assign(name=[NAME[t] for t in order]).to_string())
