"""Figure 1 of the paper (replaces the theme figure fig1_themes.pdf; 27 Nov 2026). Topics only, no hand-grouped themes. Topic of a document = topic_final under the 0.05 outlier rule (processed_rebuild_prob/seso_doc_topics_prob005_v3.csv.gz); share = documents of the topic / ALL documents of the quarter (documents left without a topic stay in the denominator).
(A) the 10 largest topics; (B) the 6 fastest-growing other topics (mean share 2024 Q1-2026 Q3 divided by mean share 2022-2023, denominator floored at 0.1 pp, >= 300 documents). Grey bars: documents per quarter. Quarters 2022 Q1 - 2026 Q3 (Q4 2026 unfinished).
Labels: the top three c-TF-IDF words, except words that come from one repeated document (topic_word_concentration.py: 'rape' in topic 47, 'et al' in 103, 'capita' in 108) are skipped.
Outputs: paper/figures/fig1_topics.pdf, seedoils/figures/fig1_topics.png, seedoils/data/processed/fig1_quarterly_topic_shares.csv (aggregates only). Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/figure1_topics_overview.py"""
import os, matplotlib; matplotlib.use("Agg")
TEX = shutil_which = __import__("shutil").which("latex") is not None  # LaTeX text if a latex binary is on PATH, else matplotlib's Computer Modern (cmr10)
import matplotlib.pyplot as plt, matplotlib.dates as md, pandas as pd
R, M, P = "seedoils/data/processed_rebuild_prob/", "seedoils/data/processed_rebuild_model/", "seedoils/data/processed/"
A = pd.read_csv(R + "seso_doc_topics_prob005_v3.csv.gz"); A["q"] = pd.to_datetime(A.created_utc, unit="s").dt.to_period("Q").dt.to_timestamp()
A = A[(A.q >= "2022-01-01") & (A.q < "2026-10-01")]; tot = A.groupby("q").size(); K = A[A.topic_final.notna() & (A.topic_final >= 0)]
C = K.groupby(["topic_final", "q"]).size().unstack(fill_value=0).reindex(columns=tot.index, fill_value=0); C.index = C.index.astype(int); S = C / tot * 100
info = pd.read_csv(M + "seso_topics_info.csv").set_index("topic"); SKIP = {47: {"rape"}, 103: {"et al", "et", "al"}, 108: {"capita"}}
def lab(t):
    w = [x for x in info.top_words[t].split(", ") if x not in SKIP.get(t, ())][:3]; return f"{t}: " + ", ".join(w)
TOP = list(C.sum(axis=1).nlargest(10).index); early = C.loc[:, :"2023-10-01"].sum(axis=1) / tot[:"2023-10-01"].sum() * 100; late = C.loc[:, "2024-01-01":].sum(axis=1) / tot["2024-01-01":].sum() * 100
g = late / early.clip(lower=0.1); g = g[(C.sum(axis=1) >= 300) & ~g.index.isin(TOP)].nlargest(6)
S.loc[TOP + list(g.index)].round(3).to_csv(P + "fig1_quarterly_topic_shares.csv"); tot.rename("documents").to_csv(P + "fig1_quarterly_documents.csv")
print("share of documents with a topic:", round(len(K) / len(A), 3)); print("TOP10:", [lab(t) for t in TOP]); print("movers:", [(lab(t), round(v, 1), round(S.loc[t].max(), 2), f"{S.loc[t].idxmax():%Y-%m}") for t, v in g.items()])
plt.rcParams.update({"font.size": 7, "axes.spines.top": False, "pdf.fonttype": 42, "text.usetex": TEX, "font.family": "serif", "font.serif": ["cmr10", "DejaVu Serif"], "axes.formatter.use_mathtext": True, "text.latex.preamble": r"\usepackage[T1]{fontenc}\usepackage{lmodern}"})
PC = r"\%" if TEX else "%"; bold = lambda x: (r"\textbf{" + x + "}") if TEX else x
fig, ax = plt.subplots(2, 1, figsize=(7.2, 5.6), sharex=True, gridspec_kw={"height_ratios": [2, 1.15], "hspace": 0.1}, constrained_layout=False)
for a, ts, title, nc in ((ax[0], TOP, bold("A") + "  The ten largest topics", 3), (ax[1], list(g.index), bold("B") + "  Fastest-growing other topics", 2)):
    b = a.twinx(); b.bar(tot.index + pd.Timedelta(days=45), tot.values, width=70, color="#d0d0d0", alpha=.65, zorder=0); b.set_ylim(0, tot.max() * (2.6 if a is ax[0] else 3.2)); b.set_ylabel("documents per quarter (bars)", color="0.45"); b.tick_params(colors="0.45"); b.spines["top"].set_visible(False); b.spines["right"].set_color("0.7")
    a.set_zorder(b.get_zorder() + 1); a.patch.set_visible(False); a.spines["right"].set_visible(False)
    for t in ts: a.plot(S.columns + pd.Timedelta(days=45), S.loc[t].values, marker="o", ms=2.5, lw=1.1, label=lab(t))
    a.set_ylabel("share of all documents (" + PC + ")"); a.set_title(title, loc="left", fontsize=8, fontweight="bold" if not TEX else "normal"); a.legend(fontsize=6, ncol=nc, loc="upper left", frameon=False, handlelength=1.4, columnspacing=1.2, borderaxespad=0.1)
ax[0].set_ylim(0, 21); ax[1].set_ylim(0, 3.4)
ax[1].xaxis.set_major_locator(md.YearLocator()); ax[1].xaxis.set_major_formatter(md.DateFormatter("%Y"))
fig.savefig("paper/figures/fig1_topics.pdf", bbox_inches="tight", pad_inches=0.02); fig.savefig("seedoils/figures/fig1_topics.png", dpi=200, bbox_inches="tight", pad_inches=0.02)
