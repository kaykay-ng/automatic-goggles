"""Trend lines for the three GoEmotions groups per quarter (2022 Q1 - 2026 Q3; share of all documents; group = any member at score >= 0.5). Weighted least squares of the quarterly share on time (weights = documents per quarter), slope in percentage points per YEAR with a t-based 95% interval (17 degrees of freedom); also the slope from 2024 Q1 on and 2022-2023 only, and the change fitted at the ends of the line. Caveats: 19 points, neighbouring quarters are not independent, so the intervals are too narrow; the line is descriptive.
Output: seedoils/figures/emotion_option6.png (panel A of option 5 with the fitted lines) and printed table. Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/emotion_trends.py"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as md, numpy as np, pandas as pd
from scipy import stats
R, Rp, P = "seedoils/data/processed_rebuild/", "seedoils/data/processed_rebuild_prob/", "seedoils/data/processed/"
labs = list(pd.read_csv(P + "goemo_monthly.csv", nrows=1).columns[1:29]); g = np.load(R + "goemo_seso.npz", allow_pickle=True); pr = g["p"].astype(np.float32); ids = g["id"]
A = pd.read_csv(Rp + "seso_doc_topics_official005.csv.gz", usecols=["id", "created_utc"]).set_index("id").loc[ids].reset_index(); A["q"] = pd.to_datetime(A.created_utc, unit="s").dt.to_period("Q").dt.to_timestamp()
G = {"positive": "admiration amusement approval caring desire excitement gratitude joy love optimism pride relief".split(), "negative": "anger annoyance disappointment disapproval disgust embarrassment fear grief nervousness remorse sadness".split(), "ambiguous": "confusion curiosity realization surprise".split()}
COL = {"negative": "#b5482a", "positive": "#2a7f62", "ambiguous": "#d19a2a"}; flag = pr >= 0.5
tot = A.groupby("q").size(); keep = tot[(tot.index >= "2022-01-01") & (tot.index < "2026-10-01")].index; tot = tot.loc[keep]; t = (keep - keep[0]).days.values / 365.25
Q = {k: pd.Series(flag[:, [labs.index(e) for e in v]].any(axis=1)).groupby(A.q.values).mean().reindex(keep) * 100 for k, v in G.items()}
def wls(x, y, w):
    X = np.c_[np.ones_like(x), x]; W = np.diag(w / w.mean()); b = np.linalg.solve(X.T @ W @ X, X.T @ W @ y); res = y - X @ b; df = len(x) - 2; s2 = (w / w.mean() * res ** 2).sum() / df; cov = s2 * np.linalg.inv(X.T @ W @ X); se = np.sqrt(np.diag(cov))[1]; tq = stats.t.ppf(0.975, df); r2 = 1 - (w / w.mean() * res ** 2).sum() / (w / w.mean() * (y - np.average(y, weights=w)) ** 2).sum(); return b, se, tq, r2
print(f"{'group':<10}{'slope/yr':>9}{'95% interval':>18}{'R2':>6}   {'2024Q1+ slope':>14}  {'2022-23 slope':>14}")
fits = {}
for k in ("negative", "ambiguous", "positive"):
    y = Q[k].values; b, se, tq, r2 = wls(t, y, tot.values.astype(float)); fits[k] = b
    m2 = keep >= "2024-01-01"; b2, se2, tq2, _ = wls(t[m2], y[m2], tot.values[m2].astype(float)); m1 = keep < "2024-01-01"; b1, se1, tq1, _ = wls(t[m1], y[m1], tot.values[m1].astype(float))
    print(f"{k:<10}{b[1]:>+9.2f}  [{b[1] - tq * se:+.2f}, {b[1] + tq * se:+.2f}]{r2:>6.2f}   {b2[1]:>+8.2f} ±{tq2 * se2:.2f}   {b1[1]:>+8.2f} ±{tq1 * se1:.2f}")
plt.rcParams.update({"font.size": 7.5, "axes.spines.top": False, "axes.spines.right": False, "font.family": "sans-serif"})
fig, ax = plt.subplots(figsize=(7.2, 3.3))
for k in ("positive", "ambiguous", "negative"):
    x = keep + pd.Timedelta(days=45); ax.plot(x, Q[k].values, marker="o", ms=2.5, lw=1.2, color=COL[k], label=f"{k} emotion"); ax.plot(x, fits[k][0] + fits[k][1] * t, ls="--", lw=1.3, color=COL[k])
for d in ("2024-01-01", "2024-08-01"): ax.axvline(pd.Timestamp(d), color="0.5", ls=":", lw=0.8)
ax.xaxis.set_major_locator(md.YearLocator()); ax.xaxis.set_major_formatter(md.DateFormatter("%Y")); ax.set_ylim(0, 28); ax.set_ylabel("share of all documents (%)"); ax.legend(frameon=False, loc="upper left", ncol=3, fontsize=7)
ax.set_title("Documents with a positive, ambiguous or negative emotion per quarter, with fitted trend lines (dashed)", loc="left", fontsize=8)
fig.savefig("seedoils/figures/emotion_option6.png", dpi=200, bbox_inches="tight")
