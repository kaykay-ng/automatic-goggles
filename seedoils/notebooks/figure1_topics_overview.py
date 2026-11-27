"""Figure 1 of the paper (replaces the theme figure fig1_themes.pdf; 27 Nov 2026). Topics only, no hand-grouped themes. Topic of a document = the result of BERTopic's own reduce_outliers (strategy "probabilities", threshold 0.05; outliers_official.py writes processed_rebuild_prob/seso_doc_topics_official005.csv.gz, topic -1 = no topic); share = documents of the topic / ALL documents of the quarter (documents left without a topic stay in the denominator).
(A) the 10 largest topics; (B) the 6 fastest-growing other topics (mean share 2024 Q1-2026 Q3 divided by mean share 2022-2023, denominator floored at 0.1 pp, >= 300 documents). Grey bars: documents per quarter. Quarters 2018 Q4 (the first with documents) - 2026 Q3 (Q4 2026 unfinished); the topics shown are still chosen on 2022 Q1 - 2026 Q3, as before, and quarters with fewer than 100 documents (all before 2021) are drawn with open markers because one document there can be several percent of the quarter.
If the 0.05 file is not on this machine, a PREVIEW is drawn from the local HDBSCAN-only topics (seso_doc_topics.csv.gz, topic_before_outlier_fix) to seedoils/figures/fig1_topics_preview_hdbscan.png; the paper figure and the aggregates are not touched.
Labels: the top three c-TF-IDF words, except words that come from one repeated document (topic_word_concentration.py: 'rape' in topic 47, 'et al' in 103, 'capita' in 108) are skipped.
Outputs: paper/figures/fig1_topics.pdf, seedoils/figures/fig1_topics.png, seedoils/data/processed/fig1_quarterly_topic_shares.csv (aggregates only). Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/figure1_topics_overview.py"""
import os, matplotlib; matplotlib.use("Agg")
if os.path.isdir("/Library/TeX/texbin"): os.environ["PATH"] = "/Library/TeX/texbin:" + os.environ["PATH"]  # MacTeX is often not on a script's PATH; the paper figures use LaTeX text
TEX = shutil_which = __import__("shutil").which("latex") is not None  # LaTeX text if a latex binary is on PATH, else matplotlib's Computer Modern (cmr10)
import matplotlib.pyplot as plt, matplotlib.dates as md, pandas as pd
R, M, P = "seedoils/data/processed_rebuild_prob/", "seedoils/data/processed_rebuild_model/", "seedoils/data/processed/"
if not os.path.exists(R + "seso_doc_topics_official005.csv.gz") and os.path.exists(P + "seso_doc_topics_official005.csv.gz"): R = P  # same file, copied into data/processed
if not os.path.exists(M + "seso_topics_info.csv"): M = P  # identical topic words
PREVIEW = not os.path.exists(R + "seso_doc_topics_official005.csv.gz")
if PREVIEW: M = P; A = pd.read_csv(P + "seso_doc_topics.csv.gz", usecols=["id", "created_utc", "topic_before_outlier_fix"]).rename(columns={"topic_before_outlier_fix": "topic_final"}); print("PREVIEW: 0.05 file missing, using HDBSCAN-only topics")
else: A = pd.read_csv(R + "seso_doc_topics_official005.csv.gz").rename(columns={"topic": "topic_final"})
A["q"] = pd.to_datetime(A.created_utc, unit="s").dt.to_period("Q").dt.to_timestamp()
A = A[(A.q >= "2018-01-01") & (A.q < "2026-10-01")]; tot = A.groupby("q").size(); K = A[A.topic_final.notna() & (A.topic_final >= 0)]; SMALL = 100  # quarters below this many documents: open markers
C = K.groupby(["topic_final", "q"]).size().unstack(fill_value=0).reindex(columns=tot.index, fill_value=0); C.index = C.index.astype(int); S = C / tot * 100
info = pd.read_csv(M + "seso_topics_info.csv").set_index("topic"); SKIP = {47: {"rape"}, 103: {"et al", "et", "al"}, 108: {"capita"}}
def lab(t):
    w = [x for x in info.top_words[t].split(", ") if x not in SKIP.get(t, ())][:3]; return f"{t}: " + ", ".join(w)
C22, tot22 = C.loc[:, "2022-01-01":], tot["2022-01-01":]  # topics chosen on 2022 Q1 - 2026 Q3, as in the published figure
TOP = list(C22.sum(axis=1).nlargest(10).index); early = C22.loc[:, :"2023-10-01"].sum(axis=1) / tot22[:"2023-10-01"].sum() * 100; late = C22.loc[:, "2024-01-01":].sum(axis=1) / tot22["2024-01-01":].sum() * 100
g = late / early.clip(lower=0.1); g = g[(C22.sum(axis=1) >= 300) & ~g.index.isin(TOP)].nlargest(6)
if not PREVIEW: S.loc[TOP + list(g.index)].round(3).to_csv(P + "fig1_quarterly_topic_shares.csv"); tot.rename("documents").to_csv(P + "fig1_quarterly_documents.csv")
print("share of documents with a topic:", round(len(K) / len(A), 3)); print("TOP10:", [lab(t) for t in TOP]); print("movers:", [(lab(t), round(v, 1), round(S.loc[t].max(), 2), f"{S.loc[t].idxmax():%Y-%m}") for t, v in g.items()])
plt.rcParams.update({"font.size": 7, "axes.spines.top": False, "pdf.fonttype": 42, "text.usetex": TEX, "font.family": "serif", "font.serif": ["cmr10", "DejaVu Serif"], "axes.formatter.use_mathtext": True, "text.latex.preamble": r"\usepackage[T1]{fontenc}\usepackage{lmodern}"})
PC = r"\%" if TEX else "%"; bold = lambda x: (r"\textbf{" + x + "}") if TEX else x
fig, ax = plt.subplots(2, 1, figsize=(7.2, 4.0), sharex=True, gridspec_kw={"height_ratios": [1.7, 1], "hspace": 0.16}, constrained_layout=False)
for a, ts, title, nc in ((ax[0], TOP, bold("A") + "  The ten largest topics", 4), (ax[1], list(g.index), bold("B") + "  Fastest-growing other topics", 3)):
    b = a.twinx(); b.bar(tot.index + pd.Timedelta(days=45), tot.values, width=70, color="#d0d0d0", alpha=.65, zorder=0); b.set_ylim(0, tot.max() * (2.6 if a is ax[0] else 3.2)); b.set_ylabel("documents per quarter (bars)", color="0.45"); b.tick_params(colors="0.45"); b.spines["top"].set_visible(False); b.spines["right"].set_color("0.7")
    a.set_zorder(b.get_zorder() + 1); a.patch.set_visible(False); a.spines["right"].set_visible(False)
    big = (tot >= SMALL).values; xq = S.columns + pd.Timedelta(days=45)
    COLS = plt.get_cmap("tab10").colors  # ten distinct colours per panel (the legend sits outside, so colours must not repeat)
    for ci, t in enumerate(ts):
        ln, = a.plot(xq, S.loc[t].where(big).values, marker="o", ms=2.5, lw=1.1, label=lab(t), color=COLS[ci])  # line only through quarters with 100+ documents
        cap = 21 if a is ax[0] else 2.6; v = S.loc[t].values; low = ~big & (v <= cap)  # open markers above the legend band are left out (listed when the script runs; stated in the caption)
        a.plot(xq[low], v[low], ls="none", marker="o", ms=2.5, color=ln.get_color())  # filled like the rest; not joined by lines
    lastsmall = tot.index[~big].max() if (~big).any() else None
    if lastsmall is not None: a.axvspan(tot.index.min(), lastsmall + pd.Timedelta(days=91), color="0.93", lw=0, zorder=-1)
    a.set_ylabel("share of all documents (" + PC + ")"); a.set_title(title, loc="left", fontsize=8, fontweight="bold" if not TEX else "normal", pad=3)
    hl, ll = a.get_legend_handles_labels(); order = sorted(range(len(hl)), key=lambda i: (i % nc, i // nc))  # matplotlib fills columns first: reorder so rows read left to right in rank order
    a.legend([hl[i] for i in order], [ll[i] for i in order], fontsize=6, ncol=nc, loc="upper center", bbox_to_anchor=(0.5, 1.0), frameon=False, handlelength=1.2, handletextpad=0.4, borderaxespad=0.2, labelspacing=0.25, columnspacing=0.9)  # centred inside the top of the plot; the y limits below leave that band empty
ax[0].set_ylim(0, 26); ax[1].set_ylim(0, 3.4); ax[0].set_yticks(range(0, 21, 5)); ax[1].set_yticks(range(0, 3))  # headroom for the legend; ticks only under it  # a few open-marker quarters before 2021 can lie above these limits and are cut off
ax[0].text(pd.Timestamp("2019-12-15"), 15.5, "fewer than 100\ndocuments per quarter", ha="center", va="top", fontsize=6, color="0.4", zorder=5)
ax[1].xaxis.set_major_locator(md.YearLocator()); ax[1].xaxis.set_major_formatter(md.DateFormatter("%Y"))
if PREVIEW: fig.savefig("seedoils/figures/fig1_topics_preview_hdbscan.png", dpi=200, bbox_inches="tight", pad_inches=0.02)
else: fig.savefig("paper/figures/fig1_topics.pdf", bbox_inches="tight", pad_inches=0.02); fig.savefig("seedoils/figures/fig1_topics.png", dpi=200, bbox_inches="tight", pad_inches=0.02)
print("quarters above the y limits (open markers):", {lab(t): [f"{q:%Y-%m} {v:.1f}" for q, v in S.loc[t].items() if v > (21 if t in TOP else 2.6)] for t in TOP + list(g.index) if (S.loc[t] > (21 if t in TOP else 2.6)).any()})
