"""MOCKUPS (27 Nov 2026) for the emotion figure, not paper figures yet.
Option 4: (A) dumbbell, share of all documents before 2024 (open) -> from August 2024 (filled), log axis, for the three GoEmotions groups and the emotions whose 95% thread-resampled interval excludes 0; change and interval printed at the right; (B) quarterly share of documents with a negative emotion, grey bars = documents per quarter (as in Figure 1).
Option 2: quarterly share of documents with a negative / positive / ambiguous emotion (any member of the group at score >= 0.5), same quarters and grey bars as Figure 1.
Shares are shares of ALL documents (149,815 documents of 15+ words). Quarters 2022 Q1 - 2026 Q3. Outputs: seedoils/figures/emotion_option4.png, emotion_option2.png. Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/emotion_mockups.py"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as md, numpy as np, pandas as pd
R, Rp, P = "seedoils/data/processed_rebuild/", "seedoils/data/processed_rebuild_prob/", "seedoils/data/processed/"
labs = list(pd.read_csv(P + "goemo_monthly.csv", nrows=1).columns[1:29]); g = np.load(R + "goemo_seso.npz", allow_pickle=True); pr = g["p"].astype(np.float32); ids = g["id"]
A = pd.read_csv(Rp + "seso_doc_topics_official005.csv.gz", usecols=["id", "created_utc"]).set_index("id").loc[ids].reset_index(); A["t"] = pd.to_datetime(A.created_utc, unit="s"); A["q"] = A.t.dt.to_period("Q").dt.to_timestamp()
G = {"positive": "admiration amusement approval caring desire excitement gratitude joy love optimism pride relief".split(), "negative": "anger annoyance disappointment disapproval disgust embarrassment fear grief nervousness remorse sadness".split(), "ambiguous": "confusion curiosity realization surprise".split()}
COL = {"negative": "#b5482a", "positive": "#2a7f62", "ambiguous": "#d19a2a"}; flag = (pr >= 0.5)
grp = {k: flag[:, [labs.index(e) for e in v]].any(axis=1) for k, v in G.items()}
before = (A.t < "2024-01-01").values; after = (A.t >= "2024-08-01").values
CH = pd.read_csv(P + "emotions_change_thread_intervals.csv").set_index("measure")
def share(mask, sel): return float(mask[sel].mean() * 100)
print("before docs", before.sum(), "after docs", after.sum()); [print(k, round(share(v, before), 2), "->", round(share(v, after), 2)) for k, v in grp.items()]
# ---- quarterly series
tot = A.groupby("q").size(); keep = tot[(tot.index >= "2022-01-01") & (tot.index < "2026-10-01")].index; tot = tot.loc[keep]
Q = {k: pd.Series(v).groupby(A.q.values).mean().reindex(keep) * 100 for k, v in grp.items()}
plt.rcParams.update({"font.size": 7.5, "axes.spines.top": False, "axes.spines.right": False, "font.family": "sans-serif"})
def bars_old(ax):
    b = ax.twinx(); b.bar(tot.index + pd.Timedelta(days=45), tot.values, width=70, color="#d0d0d0", alpha=.65, zorder=0); b.set_ylim(0, tot.max() * 3.2); b.set_ylabel("documents per quarter (bars)", color="0.45"); b.tick_params(colors="0.45"); b.spines["top"].set_visible(False); b.spines["right"].set_color("0.7")
    ax.set_zorder(b.get_zorder() + 1); ax.patch.set_visible(False); return b
def bars(ax): return None
def wilson_band(ax, k, c):
    n = tot.values.astype(float); p = Q[k].values / 100; z = 1.96; d = 1 + z * z / n; ctr = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    ax.fill_between(Q[k].index + pd.Timedelta(days=45), (ctr - h) * 100, (ctr + h) * 100, color=c, alpha=0.18, lw=0, zorder=1)
def marks(ax):
    for d in ("2024-01-01", "2024-08-01"): ax.axvline(pd.Timestamp(d), color="0.5", ls=":", lw=0.8)
    ax.xaxis.set_major_locator(md.YearLocator()); ax.xaxis.set_major_formatter(md.DateFormatter("%Y"))
# ---- option 2
fig, ax = plt.subplots(figsize=(7.2, 3.0)); bars(ax)
for k in ("positive", "ambiguous", "negative"): wilson_band(ax, k, COL[k]); ax.plot(Q[k].index + pd.Timedelta(days=45), Q[k].values, marker="o", ms=2.5, lw=1.4, color=COL[k], label=f"{k} emotion")
marks(ax); ax.set_ylim(0, 28); ax.set_ylabel("share of all documents (%)"); ax.legend(frameon=False, loc="upper left", ncol=3, fontsize=7); ax.set_title("Option 2: GoEmotions groups per quarter (bands: 95% intervals; dotted lines: Jan and Aug 2024)", loc="left", fontsize=8)
fig.savefig("seedoils/figures/emotion_option2.png", dpi=200, bbox_inches="tight")
# ---- option 4
rows = [(k + " (group)", share(grp[k], before), share(grp[k], after), CH.loc["GROUP " + k], COL[k]) for k in ("negative", "ambiguous", "positive")]
for e in labs:
    r = CH.loc[e]
    if bool(r.excl0_95): rows.append((e, share(flag[:, labs.index(e)], before), share(flag[:, labs.index(e)], after), r, next(c for k, c in COL.items() if e in G[k])))
grows, erows = rows[:3], sorted(rows[3:], key=lambda r: -(r[2] - r[1])); rows = grows + erows
fig = plt.figure(figsize=(7.2, 6.2)); gs = fig.add_gridspec(2, 1, height_ratios=[2.1, 1], hspace=0.28); a = fig.add_subplot(gs[0]); b = fig.add_subplot(gs[1])
for i, (name, x0, x1, r, c) in enumerate(rows):
    y = len(rows) - i - (0 if i < 3 else 0.6); a.plot([x0, x1], [y, y], color=c, lw=1.6, zorder=2); a.scatter([x0], [y], s=22, facecolor="white", edgecolor=c, zorder=3); a.scatter([x1], [y], s=22, color=c, zorder=3)
    d = x1 - x0; txt = f"{d:+.2f}" + (f" [{r.lo95:+.2f}, {r.hi95:+.2f}]" if r is not None else ""); a.text(1.02, y, txt, transform=a.get_yaxis_transform(), va="center", fontsize=6.8)
    a.text(-0.01, y, name, transform=a.get_yaxis_transform(), ha="right", va="center", fontsize=7.2, fontweight="bold" if i < 3 else "normal", color=c)
a.set_xscale("log"); a.set_yticks([]); a.spines["left"].set_visible(False); a.set_xlabel("share of all documents (%, log scale): before 2024 (open) to from Aug 2024 (filled)"); a.set_title("A  Change in expressed emotion (points, 95% interval)", loc="left", fontsize=8); a.set_ylim(0.2, len(rows) + 0.8)
b.set_title("B  Documents with a negative emotion, per quarter (band: 95% interval)", loc="left", fontsize=8)
bb = None; ax2 = b; wilson_band(ax2, "negative", COL["negative"]); ax2.plot(Q["negative"].index + pd.Timedelta(days=45), Q["negative"].values, marker="o", ms=2.5, lw=1.5, color=COL["negative"]); marks(ax2); ax2.set_ylim(0, 14); ax2.set_ylabel("share of all documents (%)")
fig.savefig("seedoils/figures/emotion_option4.png", dpi=200, bbox_inches="tight"); print("ok")


# ---- option 5: option 2 on top, the three negative emotions that moved most below (own y axes, 95% bands)
def band_for(series, ax, c):
    p = series.values / 100; n = tot.values.astype(float); z = 1.96; d = 1 + z * z / n; ctr = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    ax.fill_between(series.index + pd.Timedelta(days=45), (ctr - h) * 100, (ctr + h) * 100, color=c, alpha=0.18, lw=0, zorder=1)
fig = plt.figure(figsize=(7.2, 6.0)); gs = fig.add_gridspec(2, 3, height_ratios=[1.5, 1], hspace=0.85, wspace=0.38); top = fig.add_subplot(gs[0, :])
for k in ("positive", "ambiguous", "negative"): wilson_band(top, k, COL[k]); top.plot(Q[k].index + pd.Timedelta(days=45), Q[k].values, marker="o", ms=2.5, lw=1.4, color=COL[k], label=f"{k} emotion")
marks(top); top.set_ylim(0, 28); top.set_ylabel("share of all documents (%)"); top.legend(frameon=False, loc="upper left", ncol=3, fontsize=7); top.set_title("A  Documents with a positive, ambiguous or negative emotion, per quarter", loc="left", fontsize=8)
for j, e in enumerate(("annoyance", "disapproval", "anger")):
    a = fig.add_subplot(gs[1, j]); s_ = pd.Series(flag[:, labs.index(e)]).groupby(A.q.values).mean().reindex(keep) * 100; band_for(s_, a, COL["negative"]); a.plot(s_.index + pd.Timedelta(days=45), s_.values, marker="o", ms=2, lw=1.3, color=COL["negative"]); marks(a)
    a.xaxis.set_major_locator(md.YearLocator(2)); r = CH.loc[e]; a.set_title(f"{e}  {r.change:+.2f} [{r.lo95:+.2f}, {r.hi95:+.2f}]", loc="left", fontsize=7.2, color=COL["negative"], fontweight="bold"); a.set_ylim(0, s_.max() * 1.35)
    if j == 0: a.set_ylabel("share of all documents (%)")
fig.text(0.01, 0.405, "B  The negative emotions that moved most (change in points before 2024 to from Aug 2024, 95% interval)", fontsize=8)
fig.savefig("seedoils/figures/emotion_option5.png", dpi=200, bbox_inches="tight"); print("option 5 ok")
