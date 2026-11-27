"""Figure 3 candidate: six GoEmotions emotions over time, share of ALL documents (r/StopEatingSeedOils, 149,815 documents of 15+ words; label counted at score >= 0.5), monthly with a 3-month mean, Jan 2022 - Oct 2026.
Grey band = 5th-95th percentile of the monthly shares in 2022-2023 (ordinary variation before the surge); dashed line = mean of 2022-2023; dotted lines = Jan and Aug 2024. Panel titles give the change before 2024 -> from Aug 2024 (percentage points) with the 95% interval from resampling threads (emotions_change_thread_intervals.csv).
Output: paper/figures/fig3_emotions.pdf, seedoils/figures/fig3_emotions.png. Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/figure3_emotions.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

R, Rp, P = "seedoils/data/processed_rebuild/", "seedoils/data/processed_rebuild_prob/", "seedoils/data/processed/"
labs = list(pd.read_csv(P + "goemo_monthly.csv", nrows=1).columns[1:29]); g = np.load(R + "goemo_seso.npz", allow_pickle=True); pr = g["p"].astype(np.float32); ids = g["id"]
A = pd.read_csv(Rp + "seso_doc_topics_prob005_v3.csv.gz", usecols=["id", "created_utc"]).set_index("id").loc[ids].reset_index(); A["m"] = pd.to_datetime(A.created_utc, unit="s").dt.to_period("M").dt.to_timestamp()
CH = pd.read_csv(P + "emotions_change_thread_intervals.csv").set_index("measure")
EM = [("annoyance", "#b5482a"), ("anger", "#b5482a"), ("disapproval", "#b5482a"), ("amusement", "#2a7f62"), ("curiosity", "#d19a2a"), ("gratitude", "#2a7f62")]
n = A.groupby("m").size(); keep = n[(n >= 200) & (n.index >= "2022-01-01")].index
plt.rcParams.update({"font.size": 7, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})
fig, axs = plt.subplots(2, 3, figsize=(7.2, 3.9), sharex=True, constrained_layout=True)
for ax, (e, c) in zip(axs.ravel(), EM):
    m = pd.Series((pr[:, labs.index(e)] >= 0.5).astype(float)).groupby(A.m.values).mean().reindex(keep) * 100
    base = m[(m.index >= "2022-01-01") & (m.index < "2024-01-01")]; lo, hi = np.percentile(base, [5, 95])
    ax.axhspan(lo, hi, color="0.88", zorder=0); ax.axhline(base.mean(), color="0.55", ls="--", lw=0.7, zorder=1)
    ax.plot(m.index, m.rolling(3, min_periods=1).mean(), color=c, lw=1.5, zorder=3)
    for d in ("2024-01-01", "2024-08-01"): ax.axvline(pd.Timestamp(d), color="0.5", ls=":", lw=0.8)
    r = CH.loc[e]; ax.set_title(f"{e[0].upper() + e[1:]}   {r.change:+.2f} [{r.lo95:+.2f}, {r.hi95:+.2f}]", fontsize=7.2, loc="left", color=c, fontweight="bold")
    ax.set_ylim(0, max(m.rolling(3, min_periods=1).mean().max(), hi) * 1.18); ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.supylabel("Share of all documents (%)", fontsize=7.5)
fig.savefig("paper/figures/fig3_emotions.pdf"); fig.savefig("seedoils/figures/fig3_emotions.png", dpi=200)
