"""Cumulative posts over time, r/StopEatingSeedOils vs r/ScientificNutrition (rerun data, seedoils/data/raw_haoyu).
Posts only (bots removed with seedoil_common.is_bot; deleted authors kept: the post still exists). Panel A: cumulative number of posts; panel B: cumulative share of each subreddit's own total (shows WHEN each community's history happened).
Marks 1 January 2024 and August 2024 (political topics take off). Writes paper/figures/cumulative_posts.pdf and seedoils/data/processed/cumulative_posts_summary.txt.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/cumulative_posts.py"""
import gzip
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from seedoil_common import is_bot

SUBS = {"StopEatingSeedOils": "#b5482a", "ScientificNutrition": "#2a6f97"}
EVENTS = [("2024-01-01", "Jan 2024"), ("2024-08-01", "Aug 2024")]
data, lines = {}, []
for sub in SUBS:
    t = []
    with gzip.open(f"seedoils/data/raw_haoyu/{sub}_posts.jsonl.gz", "rt", encoding="utf-8") as f:
        for l in f:
            x = json.loads(l)
            if not is_bot(x.get("author") or ""): t.append(int(x["created_utc"]))
    s = pd.to_datetime(pd.Series(sorted(t)), unit="s")
    data[sub] = s
    n = len(s); lines.append(f"r/{sub}: {n:,} posts, {s.iloc[0].date()} to {s.iloc[-1].date()}")
    for y in (2022, 2023, 2024):
        lines.append(f"  share of all posts made by end of {y}: {(s < f'{y + 1}-01-01').mean():.1%}; posts in {y}: {((s >= f'{y}-01-01') & (s < f'{y + 1}-01-01')).sum():,}")
    lines.append(f"  share of all posts made from 1 Jan 2024: {(s >= '2024-01-01').mean():.1%}; median post date: {s.iloc[n // 2].date()}")

plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})
fig, ax = plt.subplots(1, 2, figsize=(7.0, 2.6), constrained_layout=True)
for sub, c in SUBS.items():
    s = data[sub]; y = np.arange(1, len(s) + 1)
    ax[0].step(s, y, where="post", color=c, lw=1.6, label=f"r/{sub}")
    ax[1].step(s, y / len(s), where="post", color=c, lw=1.6)
ax[0].set_ylabel("Cumulative posts"); ax[1].set_ylabel("Share of the subreddit's own total")
ax[0].yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v / 1000:.0f}k" if v else "0"))
ax[1].yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
for a, lab in zip(ax, "AB"):
    a.set_xlim(pd.Timestamp("2018-06-01"), pd.Timestamp("2026-12-01"))
    a.xaxis.set_major_locator(mdates.YearLocator(2)); a.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    for d, name in EVENTS: a.axvline(pd.Timestamp(d), color="0.45", ls=":", lw=0.9)
    a.text(0, 1.04, lab, transform=a.transAxes, fontweight="bold", fontsize=9)
ax[0].text(pd.Timestamp("2023-10-01"), ax[0].get_ylim()[1] * 0.03, "Jan 2024", ha="right", va="bottom", color="0.35", fontsize=7)
ax[0].text(pd.Timestamp("2024-10-01"), ax[0].get_ylim()[1] * 0.03, "Aug 2024", ha="left", va="bottom", color="0.35", fontsize=7)
ax[0].legend(frameon=False, loc="upper left", fontsize=7)
fig.savefig("paper/figures/cumulative_posts.pdf"); fig.savefig("seedoils/figures/cumulative_posts.png", dpi=200)
open("seedoils/data/processed/cumulative_posts_summary.txt", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
