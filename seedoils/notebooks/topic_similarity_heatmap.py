"""EXPLORATORY: heatmap of topic similarity. Each of the 123 BERTopic topics is represented by the mean sentence embedding of its documents (all-MiniLM-L6-v2, unit length); the cell is the cosine similarity between two topics (diagonal left blank).
Left: topics grouped by the 14 hand-made themes (themes_full_v3.json), largest topic first within a theme, so the blocks along the diagonal show how tightly each theme holds together. Right: the same topics ordered by Ward hierarchical clustering of the centroids (the data-driven order), with the theme as a colour strip, to see whether themes follow the data.
Output seedoils/figures/topic_similarity_heatmap.png. Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/topic_similarity_heatmap.py"""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import leaves_list, linkage
R, P = "seedoils/data/processed_rebuild/", "seedoils/data/processed/"
V = np.load(R + "seso_vectors.npy").astype(np.float32); D = pd.read_csv(R + "seso_docs.csv.gz", usecols=["id"]).merge(pd.read_csv(R + "seso_doc_topics.csv.gz", usecols=["id", "topic"]), on="id")
info = pd.read_csv(R + "seso_topics_info.csv").set_index("topic"); topics = sorted(info.index)
C = np.stack([V[(D.topic == t).values].mean(0) for t in topics]); C /= np.linalg.norm(C, axis=1, keepdims=True); S = C @ C.T; ix = {t: i for i, t in enumerate(topics)}
th = json.load(open(P + "themes_full_v3.json")); names = list(th); of = {t: k for k, v in th.items() for t in v}
cols = plt.get_cmap("tab20")(np.linspace(0, 1, 20)); col = {k: cols[i % 20] for i, k in enumerate(names)}
short = lambda s: s.split(" (")[0].replace("Distrust of industry, medicine and media", "Distrust of industry & media").replace("Ingredient labels and processed food", "Ingredient labels").replace("Omega-6 / PUFA biochemistry", "Omega-6 / PUFA").replace("General talk and meta", "General talk, meta")
order1 = [t for k in names for t in sorted(th[k], key=lambda t: -info.n_docs[t])]; order2 = [topics[i] for i in leaves_list(linkage(C, "ward"))]
M = S.copy(); np.fill_diagonal(M, np.nan); within = [S[ix[a], ix[b]] for k in names for a in th[k] for b in th[k] if a < b]; between = [S[ix[a], ix[b]] for a in topics for b in topics if a < b and of[a] != of[b]]
print(f"mean cosine similarity: within the same theme {np.mean(within):.3f} (pairs {len(within):,}), between themes {np.mean(between):.3f} (pairs {len(between):,}); median over all pairs {np.median([S[i, j] for i in range(123) for j in range(i + 1, 123)]):.3f}")
fig, axs = plt.subplots(1, 2, figsize=(13, 6.6), constrained_layout=True)
for ax, order, title in ((axs[0], order1, "Ordered by theme"), (axs[1], order2, "Ordered by hierarchical clustering of the topics")):
    idx = [ix[t] for t in order]; im = ax.imshow(M[np.ix_(idx, idx)], cmap="viridis", vmin=0.15, vmax=0.8, interpolation="nearest"); ax.set_xticks([]); ax.set_yticks([]); ax.set_title(title, fontsize=9, pad=22)
    for i, t in enumerate(order):  # theme colour strips on the left and top
        ax.add_patch(plt.Rectangle((-4.2, i - 0.5), 3, 1, color=col[of[t]], clip_on=False)); ax.add_patch(plt.Rectangle((i - 0.5, -4.2), 1, 3, color=col[of[t]], clip_on=False))
    if order is order1:
        pos = 0
        for k in names:
            n = len(th[k]); ax.axhline(pos - 0.5, color="w", lw=0.4); ax.axvline(pos - 0.5, color="w", lw=0.4); ax.text(-6, pos + n / 2 - 0.5, short(k), ha="right", va="center", fontsize=6.3, color="k"); pos += n
cb = fig.colorbar(im, ax=axs, shrink=0.6, pad=0.01); cb.set_label("cosine similarity between topic centroids", fontsize=8)
fig.savefig("seedoils/figures/topic_similarity_heatmap.png", dpi=170)
