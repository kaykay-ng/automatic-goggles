"""Fastest-changing topics: share of each quarter's documents, for the 8 topics whose share rose most and the 8 whose share fell most between 2022-2023 (pooled) and 2025-2026 (pooled; Q4 2026 left out, quarter not finished).
Change = percentage points of all documents; only topics with >= 300 documents after 2022 are ranked, so tiny topics cannot win on noise. Top words per quarter come from topics_over_time_quarterly_all_topics.csv.
Output: seedoils/figures/topics_over_time_movers.html. Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/topics_over_time_movers.py"""
import pandas as pd, plotly.graph_objects as go
from plotly.subplots import make_subplots
M, P = "seedoils/data/processed_rebuild_model/", "seedoils/data/processed/"
D = pd.read_csv(M + "seso_docs.csv.gz", usecols=["id", "created_utc"]).merge(pd.read_csv(M + "seso_doc_topics.csv.gz", usecols=["id", "topic"]), on="id")
D["q"] = pd.to_datetime(D.created_utc, unit="s").dt.to_period("Q").dt.to_timestamp(); D = D[(D.q >= "2022-01-01") & (D.q < "2026-10-01")]
tot = D.groupby("q").size(); C = D.groupby(["topic", "q"]).size().unstack(fill_value=0).reindex(columns=tot.index, fill_value=0); S = C / tot * 100
info = pd.read_csv(M + "seso_topics_info.csv").set_index("topic"); T = pd.read_csv(P + "topics_over_time_quarterly_all_topics.csv", parse_dates=["Timestamp"])
early = (C.loc[:, "2022-01-01":"2023-10-01"].sum(1) / tot["2022-01-01":"2023-10-01"].sum() * 100); late = (C.loc[:, "2025-01-01":"2026-07-01"].sum(1) / tot["2025-01-01":"2026-07-01"].sum() * 100)
ch = (late - early)[C.sum(1) >= 300]; ch = ch[ch.index >= 0]
up, down = ch.nlargest(8), ch.nsmallest(8)
for name, s in (("RISERS", up), ("FALLERS", down)):
    print(name, "(pp change, 2022-23 share -> 2025-26 share, docs, topic words)")
    for t, v in s.items(): print(f"  {t:>3} {v:+5.2f}  {early[t]:.2f}% -> {late[t]:.2f}%  n={int(C.loc[t].sum()):,}  {', '.join(info.top_words[t].split(', ')[:4])}")
f = make_subplots(rows=1, cols=2, subplot_titles=("Share rose most", "Share fell most"), shared_yaxes=False)
for col, s in ((1, up), (2, down)):
    for t in s.index:
        a = T[T.Topic == t].set_index("Timestamp").reindex(S.columns); words = a.Words.fillna("").str.split(", ").str[:5].str.join(", ")
        f.add_scatter(x=S.columns, y=S.loc[t].values, mode="lines+markers", name=f"{t}: " + ", ".join(info.top_words[t].split(", ")[:3]), customdata=words, hovertemplate="%{x|%Y Q%q}<br>%{y:.1f}% of documents<br>%{customdata}<extra>topic " + str(t) + "</extra>", row=1, col=col)
f.update_xaxes(tickformat="%Y", dtick="M12", ticklabelmode="period"); f.update_yaxes(title_text="share of the quarter's documents (%)", col=1)
f.update_layout(width=1300, height=620, template="plotly_white", legend=dict(orientation="h", y=-0.2), title="Fastest-changing topics, share of each quarter's documents (hover for that quarter's top words)")
f.write_html("seedoils/figures/topics_over_time_movers.html", include_plotlyjs="cdn")
