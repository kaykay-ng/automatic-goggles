"""EXPLORATORY: monthly share of themed documents for all 14 themes (v3, outlier rule 0.05), one small panel per theme, 3-month mean, 2022 on. Each panel has its own y axis (shown) and the growth ratio (from 2024 / before). Not a paper figure.
Output: seedoils/figures/themes_small_multiples.png. Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/themes_small_multiples.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

P, R = "seedoils/data/processed/", "seedoils/data/processed_rebuild_prob/"
S = pd.read_csv(P + "themes_final_summary_v3.csv").sort_values("ratio", ascending=False)
A = pd.read_csv(R + "seso_doc_topics_prob005_v3.csv.gz"); A["t"] = pd.to_datetime(A.created_utc, unit="s"); K = A[A.theme.notna()].copy(); K["m"] = K.t.dt.to_period("M").dt.to_timestamp()
tot = K.groupby("m").size(); keep = tot[(tot >= 300) & (tot.index >= "2022-01-01")].index
short = lambda s: s.split(" (")[0].replace("Distrust of industry, medicine and media", "Distrust of industry & media").replace("Ingredient labels and processed food", "Ingredient labels").replace("Omega-6 / PUFA biochemistry", "Omega-6 / PUFA").replace("Other diets", "Other diets").replace("General talk and meta", "General talk, meta").replace("Cooking and cooking fats", "Cooking, cooking fats").replace("Distrust of industry & media", "Distrust of industry")
plt.rcParams.update({"font.size": 6.5, "axes.spines.top": False, "axes.spines.right": False})
fig, axs = plt.subplots(3, 5, figsize=(9.5, 5.2), sharex=True, constrained_layout=True)
for ax, r in zip(axs.ravel(), S.itertuples()):
    sh = (K[K.theme == r.theme].groupby("m").size().reindex(tot.index, fill_value=0) / tot * 100)[keep].rolling(3, min_periods=1).mean()
    col = "#b5482a" if r.ratio > 1.25 else "#2a6f97" if r.ratio < 0.8 else "0.45"
    ax.plot(sh.index, sh.values, color=col, lw=1.3); ax.set_ylim(0, max(sh.max() * 1.15, 1)); ax.set_title(f"{short(r.theme)}  ×{r.ratio:.2f}", fontsize=6.0, loc="left", color=col, fontweight="bold")
    for d in ("2024-01-01", "2024-08-01"): ax.axvline(pd.Timestamp(d), color="0.7", ls=":", lw=0.7)
    ax.xaxis.set_major_locator(mdates.YearLocator(1)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%y"))
for ax in axs.ravel()[len(S):]: ax.axis("off")
fig.supylabel("Share of themed documents (%), own scale per panel", fontsize=7); fig.suptitle("All 14 themes: monthly share, 3-month mean (title: growth ratio from 2024 / before; dotted lines: Jan and Aug 2024)", fontsize=7.5)
fig.savefig("seedoils/figures/themes_small_multiples.png", dpi=190)
