"""Visiting crowd or lasting change? Cohorts of commenters by the month of their FIRST comment in the subreddit (rerun data seedoils/data/raw_haoyu; bots and [deleted] removed; comments only).
Cohorts: before 2022 | 2022-23 | 2024 Jan-Jul | 2024 Aug-Dec (the political wave) | 2025-26. The data starts Oct 2018, so 'first comment' means first within the data; people who commented before 2018 cannot be told apart from new ones (the sub started in 2018).
Outputs: (A) monthly active commenters by cohort (stacked), (B) retention: share of each cohort that comments again k months after its first month (k = 0..24, only people whose month k lies inside complete data, i.e. up to Oct 2026), (C) composition of each quarter's active commenters by cohort.
Also prints one-and-done shares, repeat commenters and the old guard's activity before and after the surge. Last complete month = 2026-10.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/cohort_retention.py   (aggregates only)"""
import gzip, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from seedoil_common import is_bot

LAST = pd.Period("2026-10", "M")
COH = ["before 2022", "2022-23", "2024 Jan-Jul", "2024 Aug-Dec", "2025-26"]
COL = {"before 2022": "#9aa5b1", "2022-23": "#2a6f97", "2024 Jan-Jul": "#e0a030", "2024 Aug-Dec": "#b5482a", "2025-26": "#6a4c93"}
lines = []; res = {}


def cohort(p):
    return "before 2022" if p < pd.Period("2022-01", "M") else "2022-23" if p < pd.Period("2024-01", "M") else "2024 Jan-Jul" if p < pd.Period("2024-08", "M") else "2024 Aug-Dec" if p < pd.Period("2025-01", "M") else "2025-26"


for sub in ("StopEatingSeedOils", "ScientificNutrition"):
    rows = [(x["author"] or "", int(x["created_utc"])) for x in map(json.loads, gzip.open(f"seedoils/data/raw_haoyu/{sub}_comments.jsonl.gz", "rt"))]
    C = pd.DataFrame(rows, columns=["a", "t"]); C = C[(C.a != "[deleted]") & (C.a != "") & ~C.a.map(is_bot)]
    C["m"] = pd.to_datetime(C.t, unit="s").dt.to_period("M"); C = C[C.m <= LAST]
    first = C.groupby("a").m.min(); coh = first.map(cohort)
    M = C.drop_duplicates(["a", "m"]).copy(); M["coh"] = M.a.map(coh); M["k"] = (M.m - M.a.map(first)).map(lambda d: d.n)
    n_months = M.groupby("a").size(); n_comments = C.groupby("a").size()
    lines.append(f"\n===== r/{sub}: {len(coh):,} commenters, comments to {LAST}")
    lines.append(f"{'cohort':<14}{'people':>8}{'1 comment only':>16}{'active 1 month only':>20}{'>= 3 months':>13}{'median months active':>22}{'active Aug-Oct 2026':>20}")
    for c in COH:
        who = coh[coh == c].index; l = M[M.a.isin(who)]
        late = l[(l.m >= pd.Period("2026-08", "M"))].a.nunique() / len(who)
        lines.append(f"{c:<14}{len(who):>8,}{(n_comments[who] == 1).mean():>16.0%}{(n_months[who] == 1).mean():>20.0%}{(n_months[who] >= 3).mean():>13.0%}{n_months[who].median():>22.0f}{late:>20.1%}")
    # retention curves
    ret = {}
    for c in COH:
        who = coh[coh == c].index; fm = first[who]; l = M[M.a.isin(who)]
        curve = []
        for k in range(0, 25):
            ok = who[(fm + k) <= LAST]
            if len(ok) < 50: curve.append(np.nan); continue
            act = set(l[l.k == k].a); curve.append(np.mean([a in act for a in ok]))
        ret[c] = curve
    lines.append("retention (share of the cohort commenting again k months after their first month):")
    for c in COH: lines.append(f"  {c:<14}" + "  ".join(f"k={k}: {ret[c][k]:.1%}" if not np.isnan(ret[c][k]) else f"k={k}: n/a" for k in (1, 3, 6, 12, 24)))
    # composition of active commenters by quarter
    M["q"] = M.m.dt.asfreq("Q") if hasattr(M.m, "dt") else M.m.map(lambda p: p.asfreq("Q"))
    comp = M.groupby(["q", "coh"]).a.nunique().unstack().reindex(columns=COH).fillna(0)
    comp = comp[comp.index >= pd.Period("2022Q1")]
    sh = comp.div(comp.sum(1), axis=0)
    lines.append("share of active commenters by cohort, selected quarters:")
    for q in ("2023Q4", "2024Q2", "2024Q4", "2025Q2", "2025Q4", "2026Q3"):
        lines.append(f"  {q}: " + ", ".join(f"{c} {sh.loc[pd.Period(q), c]:.0%}" for c in COH) + f"  (total {int(comp.loc[pd.Period(q)].sum()):,})")
    # old guard (first comment before 2024) activity: median monthly active, before vs after
    og = M[M.coh.isin(["before 2022", "2022-23"])].groupby("m").a.nunique()
    for lab, a, b in (("2023", "2023-01", "2023-12"), ("2024 Jan-Jul", "2024-01", "2024-07"), ("2024 Aug-Dec", "2024-08", "2024-12"), ("2025", "2025-01", "2025-12"), ("2026 Jan-Oct", "2026-01", "2026-10")):
        s = og[(og.index >= pd.Period(a, "M")) & (og.index <= pd.Period(b, "M"))]
        lines.append(f"  old guard (first comment before 2024), median monthly active, {lab}: {s.median():.0f}")
    res[sub] = (M, ret, comp)

plt.rcParams.update({"font.size": 7, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})
M, ret, comp = res["StopEatingSeedOils"]
fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.5), constrained_layout=True)
mm = M.groupby(["m", "coh"]).a.nunique().unstack().reindex(columns=COH).fillna(0); mm = mm[mm.index >= pd.Period("2021-01", "M")]
ax[0].stackplot(mm.index.to_timestamp(), [mm[c] for c in COH], colors=[COL[c] for c in COH], labels=COH, lw=0)
ax[0].set_ylabel("Active commenters per month"); ax[0].legend(frameon=False, fontsize=5.5, loc="upper left")
for c in COH[1:]:
    ax[1].plot(range(25), ret[c], color=COL[c], lw=1.3, label=c)
ax[1].set_xlabel("Months since first comment"); ax[1].set_ylabel("Share still commenting that month"); ax[1].yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0)); ax[1].set_xlim(1, 24); ax[1].set_ylim(0, None)
sh = comp.div(comp.sum(1), axis=0); ax[2].stackplot(sh.index.to_timestamp(), [sh[c] for c in COH], colors=[COL[c] for c in COH], lw=0)
ax[2].set_ylabel("Share of the quarter's active commenters"); ax[2].yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0)); ax[2].set_ylim(0, 1)
for a, lab in zip(ax, "ABC"): a.text(-0.02, 1.06, lab, transform=a.transAxes, fontweight="bold", fontsize=8)
fig.savefig("paper/figures/cohort_retention.pdf"); fig.savefig("seedoils/figures/cohort_retention.png", dpi=200)
open("seedoils/data/processed/cohort_retention_summary.txt", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))
