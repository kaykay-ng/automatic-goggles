"""Figures 1 and 2 for the paper (BERTopic part only; themes_full_v3.json, 14 themes; outlier rule: move an HDBSCAN outlier to its most probable topic only if that probability >= 0.05).
Fig 1: (A) monthly share of themed documents for five themes (3-month mean; months with >= 300 themed documents); (B) share of themed documents before 2024 -> from 2024 for all 14 themes (log axis), ratio printed.
Fig 2: (A) growth ratio (from 2024 / before) under four outlier handlings (all outliers to nearest topic; probability >= 0.02, 0.05, 0.10); (B) hand check: share of 15 comments per theme and side judged to fit the theme, just above vs just below the 0.05 threshold (Wilson 95% intervals).
Outputs: paper/figures/fig1_themes.pdf, fig2_checks.pdf (+ PNG previews in seedoils/figures). 27 Nov: text rendered by LaTeX in Latin Modern (lmodern, T1),
the font of paper/preview.tex (needs a LaTeX install on PATH); the plotted numbers are also saved as aggregates (data/processed/fig1_monthly_theme_shares.csv,
fig2_outlier_ratios.csv; no text, no ids), and when the per-document files of processed_rebuild_prob/ are missing the figures are redrawn from them. Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/figures_bertopic.py"""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

R, P = os.environ.get("FIG_REBUILD_DIR", "seedoils/data/processed_rebuild_prob/"), os.environ.get("FIG_PROCESSED_DIR", "seedoils/data/processed/")
HAVE_DOCS = os.path.exists(R + "seso_doc_topics_prob005_v3.csv.gz")
tex = lambda x: str(x).replace("&", r"\&").replace("%", r"\%")  # noqa: E731  (LaTeX special characters in labels)
S = pd.read_csv(P + "themes_final_summary_v3.csv"); short = lambda s: s.split(" (")[0].split(",")[0].replace("Keto", "Keto, carbs, fasting").replace("Distrust of industry", "Distrust of industry & media").replace("Ingredient labels and processed food", "Ingredient labels").replace("Omega-6 / PUFA biochemistry", "Omega-6 / PUFA")
S["name"] = S.theme.map(short)
if HAVE_DOCS:
    A = pd.read_csv(R + "seso_doc_topics_prob005_v3.csv.gz"); A["t"] = pd.to_datetime(A.created_utc, unit="s"); K = A[A.theme.notna()].copy(); K["month"] = K.t.dt.to_period("M").dt.to_timestamp()
C = {"Politics": "#b5482a", "Vaccines and COVID": "#6a4c93", "Distrust of industry & media": "#d19a2a", "Omega-6 / PUFA": "#2a6f97", "Keto, carbs, fasting": "#2a7f62"}
plt.rcParams.update({"font.size": 7, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
                     "text.usetex": True, "font.family": "serif", "text.latex.preamble": r"\usepackage[T1]{fontenc}\usepackage{lmodern}"})
# ---- Figure 1
fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.1), gridspec_kw={"width_ratios": [1.05, 1]}, constrained_layout=True)
if HAVE_DOCS:  # monthly shares from the documents, saved as an aggregate so the figure can be redrawn without them
    tot = K.groupby("month").size(); keepm = tot[tot >= 300].index; MS = {}
    for k in C:
        th = [t for t in K.theme.unique() if short(t) == k][0]; sh = (K[K.theme == th].groupby("month").size().reindex(tot.index, fill_value=0) / tot * 100)[keepm]; MS[k] = sh[sh.index >= "2022-01-01"]
    pd.DataFrame(MS).rename_axis("month").round(4).to_csv(P + "fig1_monthly_theme_shares.csv")
MS = pd.read_csv(P + "fig1_monthly_theme_shares.csv", parse_dates=["month"]).set_index("month")
for k, c in C.items():
    sh = MS[k].dropna(); ax[0].plot(sh.index, sh.rolling(3, min_periods=1).mean(), color=c, lw=1.4, label=tex(k))
for d in ("2024-01-01", "2024-08-01"): ax[0].axvline(pd.Timestamp(d), color="0.5", ls=":", lw=0.8)
ax[0].set_ylabel(r"Share of themed documents (\%)"); ax[0].xaxis.set_major_locator(mdates.YearLocator()); ax[0].xaxis.set_major_formatter(mdates.DateFormatter("%Y")); ax[0].legend(frameon=False, fontsize=5.8, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
ax[0].text(-0.02, 1.04, r"\textbf{A}", transform=ax[0].transAxes, fontsize=9)
D = S.sort_values("ratio"); y = np.arange(len(D))
for i, r in enumerate(D.itertuples()):
    c = "#b5482a" if r.ratio > 1.25 else "#2a6f97" if r.ratio < 0.8 else "0.5"; ax[1].plot([r.share_before, r.share_from24], [i, i], color=c, lw=1.5, zorder=1)
    ax[1].scatter([r.share_before], [i], s=16, facecolor="white", edgecolor="0.25", zorder=2); ax[1].scatter([r.share_from24], [i], s=16, color=c, zorder=3); ax[1].text(max(r.share_before, r.share_from24) * 1.18, i, f"$\\times${r.ratio:.2f}", va="center", fontsize=6, color=c)
ax[1].set_yticks(y); ax[1].set_yticklabels([tex(n) for n in D.name]); ax[1].set_xscale("log"); ax[1].set_xlim(0.2, 40); ax[1].set_xlabel(r"Share of themed documents (\%, log scale)")
ax[1].text(0.5, -0.2, "open: before 2024; filled: from 2024", transform=ax[1].transAxes, ha="center", va="top", fontsize=5.8, color="0.35")  # below the axis label (it used to overlap the bottom row)
ax[1].text(-0.02, 1.04, r"\textbf{B}", transform=ax[1].transAxes, fontsize=9)
fig.savefig("paper/figures/fig1_themes.pdf", bbox_inches="tight", pad_inches=0.02); fig.savefig("seedoils/figures/fig1_themes.png", dpi=200, bbox_inches="tight", pad_inches=0.02)
# ---- Figure 2
if HAVE_DOCS:
    z = np.load(R + "seso_probs.npz", allow_pickle=True); pr = z["p"].astype(np.float32); T = pd.read_csv(R + "seso_doc_topics.csv.gz"); T["maxp"] = pr.max(1); T["arg"] = pr.argmax(1); T["pre"] = pd.to_datetime(T.created_utc, unit="s") < "2024-01-01"
    th = json.load(open(P + "themes_full_v3.json")); m = {int(i): k for k, v in th.items() for i in v}; names = list(th); rat = {}
    for lab, thr in (("all", None), ("0.02", 0.02), ("0.05", 0.05), ("0.10", 0.10)):
        tp = T.topic if thr is None else np.where(T.topic_before_outlier_fix != -1, T.topic_before_outlier_fix, np.where(T.maxp >= thr, T.arg, -1)); s = pd.Series(tp).map(m); asg = (pd.Series(tp) != -1).values
        for k in names: a = ((s == k) & T.pre).sum(); b = ((s == k) & ~T.pre).sum(); rat[(k, lab)] = (b / (~T.pre)[asg].sum()) / (a / T.pre[asg].sum())
    R2 = pd.Series(rat).unstack(); R2["name"] = [short(k) for k in R2.index]; R2.set_index("name").round(4).to_csv(P + "fig2_outlier_ratios.csv")
R2 = pd.read_csv(P + "fig2_outlier_ratios.csv").set_index("name").loc[D.name]
fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.1), gridspec_kw={"width_ratios": [1.15, 1]}, constrained_layout=True)
mk = {"all": ("x", "0.35", "all outliers to nearest topic"), "0.02": ("o", "#9ecae1", r"probability $\geq$ 0.02"), "0.05": ("o", "#2a6f97", r"probability $\geq$ 0.05 (main)"), "0.10": ("o", "#08306b", r"probability $\geq$ 0.10")}
for i, (nm, r) in enumerate(R2.iterrows()):
    ax[0].plot([r[["all", "0.02", "0.05", "0.10"]].min(), r[["all", "0.02", "0.05", "0.10"]].max()], [i, i], color="0.8", lw=2, zorder=1)
    for lab, (mkr, c, _) in mk.items(): ax[0].scatter([r[lab]], [i], marker=mkr, s=14 if mkr == "o" else 18, color=c, zorder=3, linewidths=0.9)
ax[0].axvline(1, color="0.5", ls=":", lw=0.8); ax[0].set_xscale("log"); ax[0].set_xlim(0.55, 6.5); ax[0].set_xticks([0.6, 1, 2, 4]); ax[0].set_xticklabels(["0.6", "1", "2", "4"]); ax[0].xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter()); ax[0].set_yticks(range(len(R2))); ax[0].set_yticklabels([tex(n) for n in R2.index])
ax[0].set_xlabel("Growth ratio, from 2024 / before (log scale)")
for lab, (mkr, c, t) in mk.items(): ax[0].scatter([], [], marker=mkr, color=c, s=14, label=t)
ax[0].legend(frameon=False, fontsize=5.6, loc="lower right"); ax[0].text(-0.02, 1.04, r"\textbf{A}", transform=ax[0].transAxes, fontsize=9)
Kd = pd.read_csv(P + "threshold_reading_key.csv").merge(pd.read_csv(P + "threshold_reading_answers.csv"), on="id"); Kd["fit"] = Kd.answer == "fits"
def wil(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d; return c - h, c + h
lab = {"Politics": "Politics", "Politics (RFK, Trump, left/right)": "Politics", "Distrust of industry, medicine and media": "Distrust", "Omega-6 / PUFA biochemistry": "Omega-6 / PUFA"}
rows = [(lab[t], g) for t, g in Kd.groupby("theme")] + [("All three", Kd)]
for i, (nm, g) in enumerate(rows):
    for side, off, c in (("above", 0.14, "#2a6f97"), ("below", -0.14, "#b5482a")):
        s = g[g.side == side]; p = s.fit.mean() * 100; lo, hi = wil(int(s.fit.sum()), len(s)); ax[1].plot([lo * 100, hi * 100], [i + off] * 2, color=c, lw=1.2); ax[1].scatter([p], [i + off], color=c, s=16, zorder=3)
ax[1].set_yticks(range(len(rows))); ax[1].set_yticklabels([tex(r[0]) for r in rows]); ax[1].set_xlim(0, 100); ax[1].set_xlabel(r"Comments judged to fit the theme (\%)")
ax[1].scatter([], [], color="#2a6f97", s=14, label="just above threshold (moved to topic)"); ax[1].scatter([], [], color="#b5482a", s=14, label="just below (left unassigned)"); ax[1].legend(frameon=False, fontsize=5.6, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=1); ax[1].text(-0.02, 1.04, r"\textbf{B}", transform=ax[1].transAxes, fontsize=9)
fig.savefig("paper/figures/fig2_checks.pdf", bbox_inches="tight", pad_inches=0.02); fig.savefig("seedoils/figures/fig2_checks.png", dpi=200, bbox_inches="tight", pad_inches=0.02)
print(R2.round(2).to_string())
