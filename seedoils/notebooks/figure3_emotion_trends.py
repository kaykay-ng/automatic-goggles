"""Figure 3 of the paper (27 Nov 2026): expressed emotion per quarter, share of ALL documents (149,815 documents of 15+ words; a document has an emotion if its GoEmotions score is >= 0.5; a group if any of its members is).
(A) positive / ambiguous / negative group per quarter, 2022 Q1 - 2026 Q3, with Wilson 95% bands per quarter and weighted least-squares trend lines (dashed; weights = documents per quarter). (B) the three negative emotions that moved most (annoyance, disapproval, anger), own y axes, same bands; panel titles give the change before 1 Jan 2024 -> from 1 Jan 2024 (percentage points) with the 95% interval from resampling threads (emotions_change_thread_intervals_jan.csv, from emotion_jan_rerun.py). Dotted line: 1 January 2024.
Output: paper/figures/fig3_emotion_trends.pdf, seedoils/figures/fig3_emotion_trends.png. Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/figure3_emotion_trends.py  (LaTeX text if a latex binary is on PATH, else Computer Modern from matplotlib)"""
import shutil
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as md, numpy as np, pandas as pd
import os
R, Rp, P = "seedoils/data/processed_rebuild/", "seedoils/data/processed_rebuild_prob/", "seedoils/data/processed/"
if not os.path.exists(R + "goemo_seso.npz"): R = P  # same scores, other machine (27 Nov, Jan split rerun)
DOCS = Rp + "seso_doc_topics_official005.csv.gz" if os.path.exists(Rp + "seso_doc_topics_official005.csv.gz") else P + "seso_doc_topics.csv.gz"  # only id and date are read
labs = list(pd.read_csv(P + "goemo_monthly.csv", nrows=1).columns[1:29]); g = np.load(R + "goemo_seso.npz", allow_pickle=True); pr = g["p"].astype(np.float32); ids = g["id"]
A = pd.read_csv(DOCS, usecols=["id", "created_utc"]).set_index("id").loc[ids].reset_index(); A["q"] = pd.to_datetime(A.created_utc, unit="s").dt.to_period("Q").dt.to_timestamp()
G = {"positive": "admiration amusement approval caring desire excitement gratitude joy love optimism pride relief".split(), "negative": "anger annoyance disappointment disapproval disgust embarrassment fear grief nervousness remorse sadness".split(), "ambiguous": "confusion curiosity realization surprise".split()}
COL = {"negative": "#b5482a", "positive": "#2a7f62", "ambiguous": "#d19a2a"}; flag = pr >= 0.5; CH = pd.read_csv(P + "emotions_change_thread_intervals_jan.csv").set_index("measure")
tot = A.groupby("q").size(); keep = tot[(tot.index >= "2022-01-01") & (tot.index < "2026-10-01")].index; tot = tot.loc[keep]; t = (keep - keep[0]).days.values / 365.25; x = keep + pd.Timedelta(days=45); n = tot.values.astype(float)
share = lambda mask: pd.Series(mask).groupby(A.q.values).mean().reindex(keep) * 100
def band(ax, s, c):
    p = s.values / 100; z = 1.96; d = 1 + z * z / n; ctr = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d; ax.fill_between(x, (ctr - h) * 100, (ctr + h) * 100, color=c, alpha=0.18, lw=0, zorder=1)
def trend(s):
    X = np.c_[np.ones_like(t), t]; W = np.diag(n / n.mean()); b = np.linalg.solve(X.T @ W @ X, X.T @ W @ s.values); return X @ b, b[1]
TEX = shutil.which("latex") is not None
plt.rcParams.update({"font.size": 7, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42, "text.usetex": TEX, "font.family": "serif", "font.serif": ["cmr10", "DejaVu Serif"], "axes.formatter.use_mathtext": True, "text.latex.preamble": r"\usepackage[T1]{fontenc}\usepackage{lmodern}", "axes.unicode_minus": False})
bold = (lambda s: r"\textbf{" + s + "}") if TEX else (lambda s: s)
PCT = r"\%" if TEX else "%"  # a bare % starts a LaTeX comment
fig = plt.figure(figsize=(7.2, 3.9)); gs = fig.add_gridspec(2, 3, height_ratios=[1.35, 1], hspace=0.7, wspace=0.34); top = fig.add_subplot(gs[0, :])
for k in ("positive", "ambiguous", "negative"):
    s = share(flag[:, [labs.index(e) for e in G[k]]].any(axis=1)); band(top, s, COL[k]); fit, slope = trend(s)
    top.plot(x, s.values, marker="o", ms=2.3, lw=1.2, color=COL[k], label=f"{k} emotion"); top.plot(x, fit, ls="--", lw=1.2, color=COL[k], label=f"trend {slope:+.2f} points a year")
for d in ("2024-01-01",): top.axvline(pd.Timestamp(d), color="0.5", ls=":", lw=0.8)
top.xaxis.set_major_locator(md.YearLocator()); top.xaxis.set_major_formatter(md.DateFormatter("%Y")); top.set_ylim(0, 36); top.set_yticks(range(0, 31, 10)); top.set_ylabel(f"share of all documents ({PCT})")
h, l = top.get_legend_handles_labels(); order = [0, 1, 2, 3, 4, 5]; top.legend([h[i] for i in order], [l[i] for i in order], frameon=False, loc="upper left", ncol=3, fontsize=6.3, handlelength=2.2, columnspacing=1.2)
top.set_title(bold("A") + "  Documents with a positive, ambiguous or negative emotion, per quarter", loc="left", fontsize=7.8)
for j, e in enumerate(("annoyance", "disapproval", "anger")):
    a = fig.add_subplot(gs[1, j]); s = share(flag[:, labs.index(e)]); band(a, s, COL["negative"]); a.plot(x, s.values, marker="o", ms=1.8, lw=1.2, color=COL["negative"])
    for d in ("2024-01-01",): a.axvline(pd.Timestamp(d), color="0.5", ls=":", lw=0.8)
    a.xaxis.set_major_locator(md.YearLocator(2)); a.xaxis.set_major_formatter(md.DateFormatter("%Y")); r = CH.loc[e]; a.set_title(f"{e}  {r.change:+.2f} [{r.lo95:+.2f}, {r.hi95:+.2f}]", loc="left", fontsize=6.6, color=COL["negative"]); a.set_ylim(0, s.max() * 1.35)
    if j == 0: a.set_ylabel(f"share of all documents ({PCT})")
fig.text(0.0, 0.415, bold("B") + f"  The negative emotions that moved most (change in points, before 2024 to from 2024, 95{PCT} interval)", fontsize=7.8)
fig.savefig("paper/figures/fig3_emotion_trends.pdf", bbox_inches="tight", pad_inches=0.02); fig.savefig("seedoils/figures/fig3_emotion_trends.png", dpi=200, bbox_inches="tight", pad_inches=0.02); print("ok")
