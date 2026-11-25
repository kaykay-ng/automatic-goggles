"""Compare Google search interest in 'seed oils' with Reddit activity (r/StopEatingSeedOils comments, people and first-time commenters per month).
Input: a CSV exported from Google Trends (explore page, download button; monthly values for 2022 onwards), saved as seedoils/data/processed/trends_seed_oils.csv; Reddit monthly counts from reddit_monthly_activity.csv (aggregates).
Google Trends gives RELATIVE interest (100 = the peak of the chosen window), not counts, and is a sample; say which region and window were used.
Prints: the series side by side (2023-01 to 2025-06); correlation of levels and of month-to-month changes; correlation at lags (Google leading or lagging Reddit by up to 6 months); the first month each series is more than 2x its 2022 average.
Run from final_project/:  python3 seedoils/notebooks/google_trends_compare.py [--demo]   (--demo: synthetic trends data, to test the script only)"""
import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd

P = Path("seedoils/data/processed")
R = pd.read_csv(P / "reddit_monthly_activity.csv"); R = R[R["sub"] == "StopEatingSeedOils"].set_index("month")
if "--demo" in sys.argv:
    idx = pd.period_range("2022-01", "2026-10", freq="M").astype(str); rng = np.random.default_rng(0)
    G = pd.Series(10 + 5 * rng.random(len(idx)), index=idx, name="interest"); G.loc["2023-08":"2024-09"] += np.linspace(5, 60, 14)
else:
    rows = list(csv.reader(open(P / "trends_seed_oils.csv", encoding="utf-8-sig")))
    start = next(i for i, r in enumerate(rows) if r and r[0].strip().lower() in ("month", "week", "day", "time"))
    d = pd.DataFrame(rows[start + 1:], columns=["date", "interest"]).dropna(); d = d[d.date.str.match(r"\d{4}-\d{2}")]
    d["interest"] = pd.to_numeric(d.interest.astype(str).str.replace("<1", "0.5"), errors="coerce"); d["month"] = d.date.str[:7]
    G = d.groupby("month").interest.mean()  # weekly values are averaged to months
J = pd.concat([G.rename("google"), R.comments.rename("reddit_comments"), R.people.rename("reddit_people"), R.first_time.rename("reddit_first_time")], axis=1).dropna().loc["2022-01":]
print(J.round(0).astype(int).loc["2023-01":"2025-06"].to_string())
for c in ("reddit_comments", "reddit_people", "reddit_first_time"):
    lv = J.google.corr(J[c]); df = J.google.diff().corr(J[c].diff()); print(f"\n{c}: correlation of levels {lv:.2f}; of month-to-month changes {df:.2f}")
    print("  lag (months, Google leads Reddit when positive): " + "  ".join(f"{k:+d}: {J.google.shift(k).corr(J[c]):.2f}" for k in range(-12, 13, 2)))
    L = np.log(J[[c, "google"]].clip(lower=1)).diff().dropna()  # month-to-month log changes: removes the shared trend
    print("  same on log changes (trend removed): " + "  ".join(f"{k:+d}: {L.google.shift(k).corr(L[c]):.2f}" for k in range(-6, 7)))
base = J.loc["2022-01":"2022-12"].mean()
for c in J.columns:
    over = J[c][J[c] > 2 * base[c]]; print(f"first month above 2x its 2022 average, {c}: {over.index[0] if len(over) else 'never'}")
