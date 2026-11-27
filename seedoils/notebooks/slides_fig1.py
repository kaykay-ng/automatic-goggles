"""Slide version of Figure 1 (larger type, fewer labels), drawn at its final size (3.9 x 3.2 in) from the saved aggregates fig1_quarterly_topic_shares.csv and fig1_quarterly_documents.csv (first 10 rows = ten largest topics, last 6 = fastest-growing other topics). Output: paper/slides/slides_fig1.pdf. Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/slides_fig1.py"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as md, pandas as pd
P = "seedoils/data/processed/"
S = pd.read_csv(P + "fig1_quarterly_topic_shares.csv", index_col=0); S.columns = pd.to_datetime(S.columns); d = pd.read_csv(P + "fig1_quarterly_documents.csv", index_col=0, parse_dates=True).documents
top, mov = list(S.index[:10]), list(S.index[10:16]); x = S.columns + pd.Timedelta(days=45)
names = {1: "omega-6 / PUFA", 0: "generic seed-oil talk", 47: "RFK Jr., Trump", 98: "Trump, voting", 26: "vaccines, covid", 97: "left, right, party", 89: "political left/right", 73: "food industry"}
plt.rcParams.update({"font.size": 7, "axes.spines.top": False, "font.family": "sans-serif"})
fig, ax = plt.subplots(2, 1, figsize=(3.9, 3.3), sharex=True, gridspec_kw={"height_ratios": [1.15, 1], "hspace": 0.28})
for a, ts, title in ((ax[0], top, "Ten largest topics (% of all documents)"), (ax[1], mov, "Fastest-growing other topics")):
    b = a.twinx(); b.bar(d.index + pd.Timedelta(days=45), d.values, width=70, color="#d0d0d0", alpha=.6, zorder=0); b.set_ylim(0, d.max() * 3.3); b.set_yticks([]); b.spines[:].set_visible(False)
    a.set_zorder(b.get_zorder() + 1); a.patch.set_visible(False); a.spines["right"].set_visible(False); a.set_title(title, loc="left", fontsize=7.5, fontweight="bold")
    for t in ts:
        hi = t in (0, 1); a.plot(x, S.loc[t].values, lw=1.8 if (hi or a is ax[1]) else 0.8, color={1: "#e8742c", 0: "#2a6fdb"}.get(t) if hi else (None if a is ax[1] else "#9aa5b1"), marker="o" if a is ax[1] else None, ms=2, label=names.get(t))
ax[0].set_ylim(0, 17); ax[1].set_ylim(0, 2.7); ax[0].legend(frameon=False, loc="upper right", fontsize=6.5, handlelength=1.2); ax[1].legend(frameon=False, loc="upper left", fontsize=6, ncol=2, handlelength=1.0, columnspacing=0.8)
ax[1].xaxis.set_major_locator(md.YearLocator()); ax[1].xaxis.set_major_formatter(md.DateFormatter("%Y")); ax[0].text(0.01, 0.92, "grey bars: documents per quarter", transform=ax[0].transAxes, ha="left", fontsize=5.8, color="0.45")
fig.savefig("paper/slides/slides_fig1.pdf", bbox_inches="tight", pad_inches=0.02); fig.savefig("seedoils/figures/slides_fig1.png", dpi=200, bbox_inches="tight", pad_inches=0.02); print("ok")
