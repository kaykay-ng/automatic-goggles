"""EXPLORATORY: monthly share of ALL documents (r/StopEatingSeedOils, 149,815 documents of 15+ words) scoring >= 0.5 for each of the 28 GoEmotions labels, Jan 2022 - Oct 2026, 3-month mean; panels sorted by overall prevalence, coloured by GoEmotions group; dotted lines mark Jan and Aug 2024; each panel has its own y axis.
Output: seedoils/figures/emotions28_over_time.png. Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/emotions28_over_time.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

R, Rp, P = "seedoils/data/processed_rebuild/", "seedoils/data/processed_rebuild_prob/", "seedoils/data/processed/"
labs = list(pd.read_csv(P + "goemo_monthly.csv", nrows=1).columns[1:29]); g = np.load(R + "goemo_seso.npz", allow_pickle=True); pr = g["p"].astype(np.float32); ids = g["id"]
A = pd.read_csv(Rp + "seso_doc_topics_prob005_v3.csv.gz", usecols=["id", "created_utc"]).set_index("id").loc[ids].reset_index(); A["m"] = pd.to_datetime(A.created_utc, unit="s").dt.to_period("M").dt.to_timestamp()
GR = {"positive": "admiration amusement approval caring desire excitement gratitude joy love optimism pride relief".split(), "negative": "anger annoyance disappointment disapproval disgust embarrassment fear grief nervousness remorse sadness".split(), "ambiguous": "confusion curiosity realization surprise".split(), "neutral": ["neutral"]}
COL = {"positive": "#2a7f62", "negative": "#b5482a", "ambiguous": "#d19a2a", "neutral": "#7a8794"}; grp = {l: k for k, v in GR.items() for l in v}
F = pd.DataFrame((pr >= 0.5).astype(np.float32), columns=labs); F["m"] = A.m.values; mo = F.groupby("m").mean() * 100; n = F.groupby("m").size(); mo = mo[(n >= 200) & (mo.index >= "2022-01-01")]
order = list(F[labs].mean().sort_values(ascending=False).index)
plt.rcParams.update({"font.size": 6, "axes.spines.top": False, "axes.spines.right": False})
fig, axs = plt.subplots(7, 4, figsize=(8.6, 10.2), sharex=True, constrained_layout=True)
for ax, l in zip(axs.ravel(), order):
    s = mo[l].rolling(3, min_periods=1).mean(); ax.plot(s.index, s.values, color=COL[grp[l]], lw=1.2); ax.set_ylim(0, max(s.max() * 1.2, 0.05))
    ax.set_title(f"{l}  ({100 * F[l].mean():.2f}% of all docs)", fontsize=6.4, loc="left", color=COL[grp[l]], fontweight="bold")
    for d in ("2024-01-01", "2024-08-01"): ax.axvline(pd.Timestamp(d), color="0.7", ls=":", lw=0.7)
    ax.xaxis.set_major_locator(mdates.YearLocator(1)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%y"))
fig.supylabel("Share of all documents (%), own scale per panel", fontsize=7)
fig.suptitle("All 28 GoEmotions labels over time (>= 0.5; 3-month mean; green positive, red negative, amber ambiguous, grey neutral; dotted: Jan and Aug 2024)", fontsize=7.5)
fig.savefig("seedoils/figures/emotions28_over_time.png", dpi=170)
