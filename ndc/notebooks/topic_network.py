"""Network of the 122 BERTopic topics of the climate passages. Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python ndc/notebooks/topic_network.py
A: semantic network. Node = topic, size = number of passages; each topic linked to its 3 most similar topics (centred cosine of topic centroids, same recipe as the language network); Louvain communities.
B: co-occurrence network. Same nodes; edge = topics whose passages appear in the same speeches (cosine of speech-by-topic incidence), each topic linked to its 3 strongest partners.
Thick dark outline = topic on the KEEP list (ndc/PLAN.md 'CLIMATE TOPICS: KEEP LIST'); thin = dropped. Descriptive figure, no test.
"""
import re
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROC = Path("ndc/data/processed"); FIG = Path("ndc/figures"); FIG.mkdir(exist_ok=True)
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]; GREY = "#898781"
P = pd.read_csv(PROC / "climate_passages.csv.gz", usecols=["pid", "speech_id"]); S = pd.read_csv(PROC / "climate_passage_topics.csv.gz")
V = np.load(PROC / "climate_passages_vectors.npy").astype(np.float32); T = pd.read_csv(PROC / "climate_topics_info.csv").set_index("topic")
KEEP = {int(x) for x in (PROC / "climate_topics_keep.txt").read_text().split()}
D = P.merge(S, on="pid"); topics = sorted(T.index); idx = {t: i for i, t in enumerate(topics)}
assert (D.pid.values == np.arange(len(D))).all()
mu = V.mean(0); C = np.vstack([V[D.topic.values == t].mean(0) - mu for t in topics]); C /= np.linalg.norm(C, axis=1, keepdims=True); SIM = C @ C.T
# co-occurrence: speech x topic incidence
sp = D.groupby("speech_id").ngroup().values; M = np.zeros((sp.max() + 1, len(topics)), np.float32)
M[sp, [idx[t] for t in D.topic.values]] = 1
CO = (M.T @ M); nn = np.sqrt(np.diag(CO)); COS = CO / np.outer(nn, nn); np.fill_diagonal(COS, 0)


def knn(S, k=3):
    G = nx.Graph(); G.add_nodes_from(range(len(S)))
    for i in range(len(S)):
        for j in [j for j in np.argsort(-S[i]) if j != i][:k]: G.add_edge(i, j, weight=float(max(S[i, j], 0.01)))
    return G


def short(t):
    w = [x for x in T.loc[t, "top_words"].split(", ") if " " not in x][:2]; return f"{t}: " + "/".join(w)


GA, GB = knn(SIM), knn(COS)
comm = nx.community.louvain_communities(GA, weight="weight", seed=42); comm = sorted(comm, key=len, reverse=True)
lab = np.zeros(len(topics), int)
for c, m in enumerate(comm):
    for i in m: lab[i] = c
print(f"semantic network: {GA.number_of_nodes()} nodes, {GA.number_of_edges()} edges, {len(comm)} communities, sizes {[len(c) for c in comm]}")
for c, m in enumerate(comm):
    ts = sorted(m, key=lambda i: -T.loc[topics[i], "n_passages"])[:7]
    print(f"  community {c} ({len(m)} topics, {sum(topics[i] in KEEP for i in m)} on KEEP): " + "; ".join(short(topics[i]) for i in ts))
# how well do the two views agree, and where does the KEEP list sit?
mod = nx.community.modularity(GB, [set(m) for m in comm], weight="weight")
print(f"modularity of the SEMANTIC communities on the CO-OCCURRENCE network: Q = {mod:.3f}")
kept_idx = [idx[t] for t in KEEP]; e = [(i, j) for i, j in GA.edges() if (i in kept_idx) == (j in kept_idx)]
print(f"semantic edges inside the same KEEP/DROP side: {len(e)} of {GA.number_of_edges()} ({len(e) / GA.number_of_edges():.0%})")

fig, axs = plt.subplots(1, 2, figsize=(17, 8.6))
for ax, G, title in [(axs[0], GA, "A  Semantic network (similar meaning)"), (axs[1], GB, "B  Co-occurrence network (same speeches)")]:
    pos = nx.spring_layout(G, weight="weight", seed=7, k=0.55, iterations=400)
    size = [20 + 0.07 * T.loc[t, "n_passages"] ** 1.0 for t in topics]
    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.25, width=0.7, edge_color=GREY)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=[CAT[lab[i]] if lab[i] < 8 else GREY for i in range(len(topics))], node_size=size,
                           edgecolors=["#0b0b0b" if topics[i] in KEEP else "white" for i in range(len(topics))], linewidths=[1.8 if topics[i] in KEEP else 0.5 for i in range(len(topics))])
    show = [i for i in range(len(topics)) if (topics[i] in KEEP and T.loc[topics[i], "n_passages"] >= 1000) or T.loc[topics[i], "n_passages"] >= 2500]
    nx.draw_networkx_labels(G, pos, labels={i: short(topics[i]) for i in show}, ax=ax, font_size=5.5)
    ax.set_title(title, loc="left", fontweight="bold"); ax.axis("off")
NAMES = ["domestic politics: economy, housing, schools, air", "climate politics and agreements", "energy transition and net zero", "Nordic climate policy, oil and gas, air and sea transport",
         "coal, strategy and climate protection laws", "money: budgets, taxes, carbon price", "land, food and nature", "legislative procedure and amendments", "road and rail transport"]
fig.legend(handles=[plt.Line2D([], [], marker="o", ls="", color=CAT[c] if c < 8 else GREY, label=f"{NAMES[c] if c < len(NAMES) else 'other'} ({len(m)})") for c, m in enumerate(comm)] +
           [plt.Line2D([], [], marker="o", ls="", markerfacecolor="white", markeredgecolor="#0b0b0b", markeredgewidth=1.8, label="on KEEP list (thick outline)")],
           loc="lower center", ncol=3, fontsize=8, frameon=False)
fig.suptitle("Topics of 158,233 parliamentary climate passages (BERTopic, 122 topics). Node size = passages. Colours = Louvain communities of panel A (names written by hand from the topics inside).", fontsize=10)
fig.tight_layout(rect=(0, 0.07, 1, 0.97)); fig.savefig(FIG / "climate_topic_network.png", dpi=150); print("saved ndc/figures/climate_topic_network.png")
