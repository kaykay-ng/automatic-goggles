"""ONE CURVE (pre-declared in upf/PLAN.md, 16 Nov): health-coded (and hobby) share of non-food reviews vs share of reviewers whose grocery reviews are all ultra-processed.
Reviewers: soj/shopper_types.csv.gz (58,391; upf = ALL-UPF 1 / MOSTLY-NOT 0; exp = activity-stratum rate). Non-food: soj/elsewhere_reviews.csv.gz.
Tests C1 (health, predicted negative) and C2 (hobby, predicted positive): slope of (upf - exp) on the share; null = share shuffled within strata.
Writes upf/figures/one_curve.png, soj/one_curve.csv, data/processed/one_curve.txt.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/one_curve.py
"""
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

C = Path("upf/data/processed/soj"); OUT = Path("upf/data/processed/one_curve.txt"); RNG = np.random.default_rng(1611); NPERM = 2000
T = pd.read_csv(C / "shopper_types.csv.gz").set_index("user_id")
E = pd.read_csv(C / "elsewhere_reviews.csv.gz", usecols=["user_id", "parent_asin"]); E = E[E.user_id.isin(T.index)]
S = pd.read_csv(C / "all_subcategories.csv.gz", index_col=0); E["d"] = S.dept.reindex(E.parent_asin).values; E["s"] = S["sub"].reindex(E.parent_asin).values
HN = {("Health_and_Household", "Vitamins, Minerals & Supplements"), ("Health_and_Household", "Diet & Sports Nutrition"),
      ("Health_and_Household", "Wellness & Relaxation"), ("Sports_and_Outdoors", "Exercise & Fitness")}
BN = {("Toys_and_Games", s) for s in ("Toy Figures & Playsets", "Collectible Toys", "Games & Accessories", "Puzzles", "Building Toys", "Novelty & Gag Toys")} \
     | {("Sports_and_Outdoors", "Fan Shop"), ("Sports_and_Outdoors", "Memorabilia Display & Storage")}
HW = HN | {("Health_and_Household", "Oral Care"), ("Health_and_Household", "Vision")}
tot = E.groupby("user_id").size().reindex(T.index)
pairs = list(zip(E.d, E.s))
def share(mask): return E[mask].groupby("user_id").size().reindex(T.index, fill_value=0) / tot
health = share([x in HN for x in pairs]); hobby = share([x in BN or x[0] == "Video_Games" for x in pairs])
health_w = share([x in HW for x in pairs]); hobby_w = share([x in BN or x[0] in ("Video_Games", "Toys_and_Games") for x in pairs])
y = T.upf.values.astype(float); ex = T.exp.values; resid = y - ex
strata = T.stratum.astype(str).values; groups = [np.where(strata == s)[0] for s in np.unique(strata)]
log = []
def say(s=""): print(s); log.append(s)


def slope(x, r): xc = x - x.mean(); return (xc * r).sum() / (xc * xc).sum()


def test(x, r=resid, idx=None, name=""):
    x = np.asarray(x, float); r = np.asarray(r, float); g = groups if idx is None else [np.intersect1d(gg, idx) for gg in groups]
    if idx is not None: keep = np.concatenate(g); x, r = x[keep], r[keep]; pos = {v: i for i, v in enumerate(keep)}; g = [np.array([pos[v] for v in gg]) for gg in g]
    obs = slope(x, r); null = np.empty(NPERM)
    for k in range(NPERM):
        xs = x.copy()
        for gg in g: xs[gg] = x[RNG.permutation(gg)]
        null[k] = slope(xs, r)
    p = (1 + (np.abs(null) >= abs(obs)).sum()) / (NPERM + 1)
    say(f"{name}: slope {obs:+.4f} per unit share (= {obs * 10:+.2f} pts per 10 pts of share); null sd {null.std():.4f}; p = {p:.4f}"); return obs, p


def bins(x):
    x = pd.Series(np.asarray(x), index=T.index); b = pd.Series("none", index=T.index, dtype=object)
    pos = x[x > 0]; q = pd.qcut(pos.rank(method="first"), 10, labels=False); b[pos.index] = q.astype(int).astype(str)
    D = pd.DataFrame({"b": b, "x": x, "y": y, "e": ex}).groupby("b").agg(n=("y", "size"), x=("x", "mean"), xmin=("x", "min"), xmax=("x", "max"), y=("y", "mean"), e=("e", "mean"))
    D["ci"] = 1.96 * np.sqrt(D.y * (1 - D.y) / D.n); return D.reindex(["none"] + [str(i) for i in range(10)])


say(f"reviewers {len(T):,}; ALL-UPF {y.mean():.1%}; no health-coded reviews {np.mean(health == 0):.1%}; no hobby reviews {np.mean(hobby == 0):.1%}; corr(health, hobby) {np.corrcoef(health, hobby)[0, 1]:+.3f}")
c1 = test(health, name="C1 health share (narrow)"); c2 = test(hobby, name="C2 hobby share (narrow)")
ps = sorted([(c1[1], "C1"), (c2[1], "C2")]); say("Holm: " + ", ".join(f"{n} p_adj = {min(1, p * (2 - i)):.4f}" for i, (p, n) in enumerate(ps)))
test(health_w, name="C1 wide"); test(hobby_w, name="C2 wide")
test(health, idx=np.where(hobby.values == 0)[0], name="C1 among reviewers with no hobby reviews")
Hb, Bb = bins(health), bins(hobby)
say("\nHealth-coded share bins:\n" + (Hb.assign(x=Hb.x * 100, xmin=Hb.xmin * 100, xmax=Hb.xmax * 100, y=Hb.y * 100, e=Hb.e * 100, ci=Hb.ci * 100)).round(1).to_string())
say("\nHobby share bins:\n" + (Bb.assign(x=Bb.x * 100, xmin=Bb.xmin * 100, xmax=Bb.xmax * 100, y=Bb.y * 100, e=Bb.e * 100, ci=Bb.ci * 100)).round(1).to_string())
pd.concat({"health": Hb, "hobby": Bb}).to_csv(C / "one_curve.csv"); OUT.write_text("\n".join(log) + "\n")

BLUE, ORANGE, GREY = "#2a78d6", "#eb6834", "#888780"
fig, axs = plt.subplots(1, 2, figsize=(11, 4.9), sharey=True)
for ax, D, col, nm, (sl, p) in ((axs[0], Hb, BLUE, "health-coded", c1), (axs[1], Bb, ORANGE, "hobby", c2)):
    xs = np.r_[-0.35, np.log10(D.x.values[1:] * 100)]                      # 'none' left of a break; the rest at log10(mean share %)
    ax.plot(xs[1:], D.e[1:] * 100, color=GREY, lw=1.6, ls=(0, (4, 3)), marker="o", ms=3.5, label="expected from activity", zorder=2)
    ax.plot(xs[0], D.e.iloc[0] * 100, "o", color=GREY, ms=3.5, zorder=2)
    ax.errorbar(xs[1:], D.y[1:] * 100, yerr=D.ci[1:] * 100, color=col, lw=2, marker="o", ms=6, mec="white", mew=1, capsize=0, elinewidth=1, label="observed", zorder=3)
    ax.errorbar(xs[0], D.y.iloc[0] * 100, yerr=D.ci.iloc[0] * 100, color=col, marker="o", ms=6, mec="white", mew=1, elinewidth=1, ls="none", zorder=3)
    ax.axvline(-0.12, color="#b4b2a9", lw=0.8, ls=(0, (2, 3)))
    ax.set_xticks([-0.35] + list(np.log10([1, 2, 5, 10, 20, 50, 100])), ["none", "1%", "2%", "5%", "10%", "20%", "50%", "100%"], fontsize=8); ax.set_xlim(-0.55, 2.05)
    ax.set_xlabel(f"{nm} share of non-food reviews (log scale)", fontsize=8.5, color="#444441")
    ax.set_title(f"{nm.capitalize()} share  (slope {sl * 10:+.1f} pts per 10 pts of share, p = {max(p, 1 / (NPERM + 1)):.4f})", loc="left", fontsize=9.5)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", labelsize=8); ax.grid(axis="y", color="#e6e8e1", lw=0.6); ax.set_axisbelow(True)
axs[0].set_ylabel("% of reviewers whose grocery reviews\nare all ultra-processed", fontsize=8.5); axs[0].legend(frameon=False, fontsize=8, loc="lower left")
fig.suptitle("The bigger the share of health-coded reviews, the fewer all-ultra-processed grocery reviewers; hobby goes the other way", x=0.01, ha="left", fontsize=11)
fig.text(0.01, 0.01, "58,391 reviewers with >= 3 matched grocery reviews (all ultra-processed vs at most half) and >= 5 non-food reviews. 'None' = no reviews of that kind; other points = tenths of the rest, placed at their average share.\n"
         "Expected = rate for people with the same number of grocery reviews. Lines = 95% intervals. Health-coded: vitamins, sports nutrition, wellness, exercise. Hobby: figures, collectibles,\n"
         "games, puzzles, building toys, video games, fan shop. p from 2,000 shuffles of the share among reviewers with similar activity. 'Health-coded' = sold as healthy.", fontsize=7.2, color="#5f5e5a")
fig.tight_layout(rect=(0, 0.1, 1, 0.95)); fig.savefig("upf/figures/one_curve.png", dpi=170); print("saved upf/figures/one_curve.png")
