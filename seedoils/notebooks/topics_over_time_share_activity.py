"""Top-10 topics per quarter as a SHARE of all documents that quarter, with total activity (documents per quarter) as grey bars on the right axis.
Reads seedoils/data/processed/topics_over_time_quarterly_all_topics.csv (from topics_over_time_top10_quarterly.py) and seso_docs.csv.gz (counts only, no text kept).
Output: seedoils/figures/topics_over_time_top10_share_activity.html. Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/topics_over_time_share_activity.py"""
import pandas as pd, plotly.graph_objects as go
from plotly.subplots import make_subplots
M, P = "seedoils/data/processed_rebuild_model/", "seedoils/data/processed/"
D = pd.read_csv(M + "seso_docs.csv.gz", usecols=["id", "created_utc"]).merge(pd.read_csv(M + "seso_doc_topics.csv.gz", usecols=["id", "topic"]), on="id")
D["q"] = pd.to_datetime(D.created_utc, unit="s").dt.to_period("Q").dt.to_timestamp(); D = D[D.q >= "2022-01-01"]
tot = D.groupby("q").size(); T = pd.read_csv(P + "topics_over_time_quarterly_all_topics.csv", parse_dates=["Timestamp"])
info = pd.read_csv(M + "seso_topics_info.csv").set_index("topic"); TOP = list(pd.read_csv(M + "seso_doc_topics.csv.gz", usecols=["topic"]).topic.value_counts().head(10).index)
print("outlier docs (-1) after 2022:", int((D.topic == -1).sum()), "of", len(D))
f = make_subplots(specs=[[{"secondary_y": True}]])
f.add_bar(x=tot.index, y=tot.values, name="all documents (right axis)", marker_color="rgba(160,160,160,0.35)", secondary_y=True, hovertemplate="%{x|%Y Q%q}: %{y:,} documents<extra></extra>")
for t in TOP:
    a = T[T.Topic == t].set_index("Timestamp"); share = (a.Frequency / tot.reindex(a.index) * 100)
    f.add_scatter(x=share.index, y=share.values, mode="lines+markers", name=f"{t}: " + ", ".join(info.top_words[t].split(", ")[:3]), customdata=a.Words.str.split(", ").str[:5].str.join(", "), hovertemplate="%{x|%Y Q%q}<br>%{y:.1f}% of documents<br>%{customdata}<extra>topic " + str(t) + "</extra>", secondary_y=False)
f.update_xaxes(tickformat="%Y", dtick="M12", ticklabelmode="period"); f.update_yaxes(title_text="share of the quarter's documents (%)", secondary_y=False); f.update_yaxes(title_text="documents per quarter", secondary_y=True, showgrid=False)
f.update_layout(width=1100, height=600, template="plotly_white", title="Ten largest topics: share of each quarter's documents, with total activity", legend=dict(orientation="h", y=-0.15))
f.write_html("seedoils/figures/topics_over_time_top10_share_activity.html", include_plotlyjs="cdn")
s = pd.DataFrame({t: (T[T.Topic == t].set_index("Timestamp").Frequency / tot).round(3) * 100 for t in TOP}); s["docs"] = tot; print(s.round(1).to_string())
