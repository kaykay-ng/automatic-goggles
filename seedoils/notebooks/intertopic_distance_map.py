"""EXPLORATORY: intertopic distance map (like BERTopic's visualize_topics / LDAvis). The fitted BERTopic object was not saved, so the map is rebuilt from the same ingredients: each of the 123 topics is represented by the mean sentence embedding of its documents (all-MiniLM-L6-v2), reduced to 2 dimensions with UMAP (cosine, n_neighbors 8, seed 42). Bubble area = number of documents in the topic (assigned topic, all 149,815 documents); colour = hand-made theme (themes_full_v3.json). Distances are only approximate and the axes have no meaning.
Outputs: seedoils/figures/intertopic_distance_map.png (static, largest topics labelled) and seedoils/figures/intertopic_distance_map.html (interactive, hover shows topic id, top words, size, theme; topic words only, no Reddit text).
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/intertopic_distance_map.py"""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import umap
R, P = "seedoils/data/processed_rebuild/", "seedoils/data/processed/"
V = np.load(R + "seso_vectors.npy").astype(np.float32); D = pd.read_csv(R + "seso_docs.csv.gz", usecols=["id"]).merge(pd.read_csv(R + "seso_doc_topics.csv.gz", usecols=["id", "topic"]), on="id")
info = pd.read_csv(R + "seso_topics_info.csv").set_index("topic"); topics = sorted(info.index)
C = np.stack([V[(D.topic == t).values].mean(0) for t in topics]); C /= np.linalg.norm(C, axis=1, keepdims=True)
X = umap.UMAP(n_neighbors=8, n_components=2, min_dist=0.6, metric="cosine", random_state=42).fit_transform(C)
th = json.load(open(P + "themes_full_v3.json")); of = {t: k for k, v in th.items() for t in v}; names = list(th)
short = lambda s: s.split(" (")[0].replace("Distrust of industry, medicine and media", "Distrust of industry & media").replace("Ingredient labels and processed food", "Ingredient labels").replace("Omega-6 / PUFA biochemistry", "Omega-6 / PUFA").replace("General talk and meta", "General talk, meta")
cm = plt.get_cmap("tab20"); col = {k: cm(i % 20) for i, k in enumerate(names)}; hexc = {k: matplotlib.colors.to_hex(col[k]) for k in names}
n = np.array([info.n_docs[t] for t in topics], float); size = 40 + 2400 * n / n.max()
fig, ax = plt.subplots(figsize=(10.5, 8.2), constrained_layout=True)
for k in names:
    sel = [i for i, t in enumerate(topics) if of[t] == k]; ax.scatter(X[sel, 0], X[sel, 1], s=size[sel], color=col[k], alpha=0.75, edgecolor="white", linewidth=0.6, label=short(k))
for i in np.argsort(-n)[:26]: ax.annotate(f"{topics[i]}  {info.top_words[topics[i]].split(', ')[0]}", (X[i, 0], X[i, 1]), fontsize=6.6, ha="center", va="center")
ax.set_xticks([]); ax.set_yticks([]); ax.set_title("Intertopic distance map: 123 topics (bubble area = documents; colour = theme)", fontsize=10); ax.legend(frameon=False, fontsize=7, loc="center left", bbox_to_anchor=(1.0, 0.5), markerscale=0.35)
fig.savefig("seedoils/figures/intertopic_distance_map.png", dpi=170)
fg = go.Figure()
for k in names:
    sel = [i for i, t in enumerate(topics) if of[t] == k]
    fg.add_trace(go.Scatter(x=X[sel, 0], y=X[sel, 1], mode="markers+text", name=short(k), text=[str(topics[i]) for i in sel], textfont=dict(size=8), marker=dict(size=[8 + 52 * (n[i] / n.max()) ** 0.5 for i in sel], color=hexc[k], opacity=0.75, line=dict(width=0.6, color="white")),
        customdata=[[topics[i], info.top_words[topics[i]][:90], int(n[i])] for i in sel], hovertemplate="Topic %{customdata[0]}<br>%{customdata[1]}<br>%{customdata[2]:,} documents<extra>" + short(k) + "</extra>"))
fg.update_layout(title="Intertopic distance map (bubble size = documents; colour = theme; hover for topic words)", xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x"), template="simple_white", width=1050, height=780)
fg.write_html("seedoils/figures/intertopic_distance_map.html", include_plotlyjs="cdn"); print("done")
