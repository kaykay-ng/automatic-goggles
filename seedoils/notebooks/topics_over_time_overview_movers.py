"""EXPLORATORY two-panel figure, topics only (no hand-grouped themes). A: the 10 largest topics as quarterly share of all documents, grey bars = documents per quarter (right axis). B: the 6 fastest-growing other topics (ratio of mean share 2024 Q1-2026 Q3 to mean share 2022-2023, denominator floored at 0.1 pp, >= 300 documents, not in the top 10), same y logic, to show spikes.
Quarters 2022 Q1 - 2026 Q3 (Q4 2026 unfinished). Output: seedoils/figures/topics_overview_and_movers.png. Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/topics_over_time_overview_movers.py"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as md, pandas as pd
M = "seedoils/data/processed_rebuild_model/"
D = pd.read_csv(M + "seso_docs.csv.gz", usecols=["id", "created_utc"]).merge(pd.read_csv(M + "seso_doc_topics.csv.gz", usecols=["id", "topic"]), on="id")
D["q"] = pd.to_datetime(D.created_utc, unit="s").dt.to_period("Q").dt.to_timestamp(); N = D.topic.value_counts(); D = D[(D.q >= "2022-01-01") & (D.q < "2026-10-01")]
tot = D.groupby("q").size(); C = D.groupby(["topic", "q"]).size().unstack(fill_value=0).reindex(columns=tot.index, fill_value=0); S = C / tot * 100
info = pd.read_csv(M + "seso_topics_info.csv").set_index("topic"); lab = lambda t: f"{t}: " + ", ".join(info.top_words[t].split(", ")[:3])
TOP = list(N.head(10).index); early = C.loc[:, :"2023-10-01"].sum(axis=1) / tot[:"2023-10-01"].sum() * 100; late = C.loc[:, "2024-01-01":].sum(axis=1) / tot["2024-01-01":].sum() * 100
g = (late / early.clip(lower=0.1)); g = g[(C.sum(axis=1) >= 300) & ~g.index.isin(TOP) & (g.index >= 0)].nlargest(6)
print("fastest-growing:"); [print(f"  {t:>3} x{v:.1f}  {early[t]:.2f}% -> {late[t]:.2f}%  peak {S.loc[t].max():.1f}% in {S.loc[t].idxmax():%Y Q%q}  {lab(t)}") for t, v in g.items()]
fig, ax = plt.subplots(2, 1, figsize=(11, 9), sharex=True, gridspec_kw={"height_ratios": [2, 1], "hspace": 0.12})
for a, ts, title in ((ax[0], TOP, "A  The ten largest topics: share of each quarter's documents"), (ax[1], list(g.index), "B  Fastest-growing other topics (ratio of 2024+ share to 2022-23 share)")):
    b = a.twinx(); b.bar(tot.index, tot.values, width=70, color="#cfcfcf", alpha=.6, zorder=0); b.set_ylim(0, tot.max() * 3); b.set_ylabel("documents per quarter (bars)", color="grey"); b.tick_params(colors="grey")
    a.set_zorder(b.get_zorder() + 1); a.patch.set_visible(False)
    for t in ts: a.plot(S.columns, S.loc[t].values, marker="o", ms=3, lw=1.5, label=lab(t))
    a.set_title(title, loc="left", fontsize=11); a.set_ylabel("share of documents (%)"); a.legend(fontsize=7, ncol=2 if a is ax[0] else 1, loc="upper left", frameon=False); a.spines[["top"]].set_visible(False)
ax[1].xaxis.set_major_locator(md.YearLocator()); ax[1].xaxis.set_major_formatter(md.DateFormatter("%Y"))
fig.savefig("seedoils/figures/topics_overview_and_movers.png", dpi=170, bbox_inches="tight")
