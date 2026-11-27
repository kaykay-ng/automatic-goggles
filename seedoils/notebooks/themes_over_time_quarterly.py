"""The 14 themes (themes_full_v3, outlier rule 0.05) as quarterly share of ALL documents (themed or not; the rest is the 'no theme' share), 2022 on, Q4 2026 left out (quarter not finished).
Outputs: seedoils/figures/themes_quarterly_lines.html (one chart, 14 lines + 'no theme' dashed; click legend to hide) and seedoils/figures/themes_quarterly_panels.html (one panel per theme, own y axis, grey bars = documents per quarter). Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/themes_over_time_quarterly.py"""
import pandas as pd, plotly.graph_objects as go
from plotly.subplots import make_subplots
A = pd.read_csv("seedoils/data/processed_rebuild_prob/seso_doc_topics_prob005_v3.csv.gz"); A["q"] = pd.to_datetime(A.created_utc, unit="s").dt.to_period("Q").dt.to_timestamp()
A = A[(A.q >= "2022-01-01") & (A.q < "2026-10-01")]; A["theme"] = A.theme.fillna("No theme (outliers after threshold 0.05)")
tot = A.groupby("q").size(); S = A.groupby(["theme", "q"]).size().unstack(fill_value=0).reindex(columns=tot.index, fill_value=0) / tot * 100
order = S.drop(index=[i for i in S.index if i.startswith("No theme")]).loc[:, "2025-01-01":].mean(axis=1).sub(S.loc[:, :"2023-10-01"].mean(axis=1)).dropna().sort_values(ascending=False).index.tolist() + [i for i in S.index if i.startswith("No theme")]
f = go.Figure()
for t in order: f.add_scatter(x=S.columns, y=S.loc[t].values, mode="lines+markers", name=t.split(" (")[0], line=dict(dash="dash", color="grey") if t.startswith("No theme") else None, hovertemplate="%{x|%Y Q%q}: %{y:.1f}%<extra>" + t[:40] + "</extra>")
f.update_xaxes(tickformat="%Y", dtick="M12", ticklabelmode="period"); f.update_yaxes(title_text="share of the quarter's documents (%)")
f.update_layout(width=1200, height=650, template="plotly_white", title="14 themes: share of all documents per quarter", legend=dict(font=dict(size=10))); f.write_html("seedoils/figures/themes_quarterly_lines.html", include_plotlyjs="cdn")
th = [t for t in order if not t.startswith("No theme")]; g = make_subplots(rows=5, cols=3, subplot_titles=[t.split(" (")[0] for t in th], vertical_spacing=0.07, specs=[[{"secondary_y": True}] * 3] * 5)
for i, t in enumerate(th):
    r, c = i // 3 + 1, i % 3 + 1
    g.add_bar(x=tot.index, y=tot.values, marker_color="rgba(160,160,160,0.3)", showlegend=False, hoverinfo="skip", row=r, col=c, secondary_y=True)
    g.add_scatter(x=S.columns, y=S.loc[t].values, mode="lines+markers", showlegend=False, line=dict(color="#1f77b4"), hovertemplate="%{x|%Y Q%q}: %{y:.1f}%<extra></extra>", row=r, col=c, secondary_y=False)
    g.update_yaxes(showgrid=False, showticklabels=False, secondary_y=True, row=r, col=c)
g.update_xaxes(tickformat="%Y", dtick="M12"); g.update_layout(width=1300, height=1300, template="plotly_white", title="14 themes: share of all documents per quarter (grey bars: documents per quarter)"); g.write_html("seedoils/figures/themes_quarterly_panels.html", include_plotlyjs="cdn")
pd.set_option("display.width", 250); print(S.round(1).loc[order].assign(**{"2022-23": S.loc[:, :"2023-10-01"].mean(axis=1).round(1), "2025-26": S.loc[:, "2025-01-01":].mean(axis=1).round(1)})[["2022-23", "2025-26"]].to_string())
