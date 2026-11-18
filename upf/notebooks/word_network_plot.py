"""Figure for the MARKETING WORD NETWORK (word_network.py): the main vocabularies (seller boilerplate communities left out), top words each, links = strongest PMI ties
among the shown words (top 4 per word; for drawing only). Text colour = lean (half-A log-odds z; blue = less processed, orange = ultra-processed); size = listings using the word.
Writes upf/figures/word_network.png.  Run from final_project/:  ./.venv-nlp/bin/python upf/notebooks/word_network_plot.py
"""
import numpy as np, pandas as pd, networkx as nx
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
C = "upf/data/processed/soj/"
N = pd.read_csv(C + "word_nodes.csv"); E = pd.read_csv(C + "word_edges.csv.gz")
SHOW = {1: "Pleasure, convenience\n& nutrition panel", 0: "Cooking & use", 2: "Certification\n& sourcing", 3: "Brand values", 6: "Heritage & freshness", 8: "Free-from claims", 11: "No GMOs, no chemicals"}
GENERIC = {"use", "make", "makes", "used", "using", "comes", "come", "includes", "include", "thing", "possible", "provide", "provides", "contain", "help", "need", "expect", "fact",
           "making", "available", "order", "choose", "going", "nearly", "doing", "shown", "fully", "set", "offer", "brought", "keeps", "away", "typically", "higher", "working", "bring", "years"}
K = 13; sel = []
for c in SHOW:
    m = N[(N.community == c) & ~N.word.isin(GENERIC)].sort_values("listings", ascending=False).head(K); sel.append(m)
S = pd.concat(sel).set_index("word"); words = set(S.index)
F = E[E.a.isin(words) & E.b.isin(words)]
keep = set()
for w in words:
    t = F[(F.a == w) | (F.b == w)].nlargest(4, "pmi"); keep |= set(t.index)
F = F.loc[sorted(keep)]
G = nx.Graph(); G.add_nodes_from(words); G.add_weighted_edges_from(zip(F.a, F.b, F.pmi))
lean = {c: N[N.community == c].z_halfA.mean() for c in SHOW}; order = sorted(SHOW, key=lambda c: lean[c])     # left = purity, right = pleasure
centers = {}
for k, c in enumerate(order):
    row = k % 2; centers[c] = np.array([1.6 + k * 1.75, 5.2 if row == 0 else 1.9])
cmap = LinearSegmentedColormap.from_list("d", ["#2a78d6", "#a9a79e", "#eb6834"]); norm = TwoSlopeNorm(0, -6, 6)
fig, ax = plt.subplots(figsize=(14, 9.2)); ax.set_axis_off(); ax.set_xlim(0, 13.6); ax.set_ylim(0, 7.4)
mx = S.listings.max(); fs = {w: 7.5 + 7 * np.sqrt(S.listings[w] / mx) for w in words}
upi = 13.6 / (14 * 0.98)                                                       # data units per inch (x)
pos = {}
for c in order:
    ws = list(S.index[S.community == c]); H = G.subgraph(ws)
    pp = nx.spring_layout(H, weight="weight", k=0.9, iterations=200, seed=3, center=(0, 0))
    P_ = np.array([pp[w] for w in ws]); P_ = P_ / (np.abs(P_).max(0) + 1e-9) * [0.75, 1.05]
    wd = np.array([len(w) * fs[w] * 0.62 / 72 * upi for w in ws]); ht = np.array([fs[w] * 1.5 / 72 * upi for w in ws])
    for _ in range(600):                                                          # push overlapping labels apart
        mv = False
        for i_ in range(len(ws)):
            for j_ in range(i_ + 1, len(ws)):
                dx, dy = P_[j_] - P_[i_]; ox = (wd[i_] + wd[j_]) / 2 - abs(dx); oy = (ht[i_] + ht[j_]) / 2 - abs(dy)
                if ox > 0 and oy > 0:
                    mv = True
                    if oy < ox: s_ = np.sign(dy) or 1; P_[i_, 1] -= s_ * oy / 2; P_[j_, 1] += s_ * oy / 2
                    else: s_ = np.sign(dx) or 1; P_[i_, 0] -= s_ * ox / 2; P_[j_, 0] += s_ * ox / 2
        if not mv: break
    for w, q in zip(ws, P_): pos[w] = centers[c] + q
for a_, b_, d in G.edges(data=True):
    (x1, y1), (x2, y2) = pos[a_], pos[b_]; same = S.community[a_] == S.community[b_]
    if same: ax.plot([x1, x2], [y1, y2], color="#c9c7bd", lw=0.3 + 0.35 * d["weight"], alpha=0.55, zorder=1)
    else: ax.plot([x1, x2], [y1, y2], color="#e1e0d9", lw=0.4, alpha=0.35, zorder=0)
for w in words:
    x, y = pos[w]; ax.text(x, y, w, ha="center", va="center", fontsize=fs[w], color=cmap(norm(S.z_halfA[w])), fontweight="bold", zorder=3)
for c in order:
    P_ = np.array([pos[w] for w in S.index[S.community == c]]); top = P_[:, 1].max()
    ax.text(centers[c][0], top + 0.32, f"{SHOW[c]}\nmean lean {lean[c]:+.1f}", ha="center", va="bottom", fontsize=9.3, color="#2c2c2a", style="italic", zorder=4,
            bbox=dict(boxstyle="round,pad=0.3", fc="#f5f6f2", ec="#d3d1c7"))
ax.annotate("", xy=(13.3, 0.25), xytext=(0.3, 0.25), arrowprops=dict(arrowstyle="->", color="#888780"))
ax.text(0.3, 0.38, "groups ordered from less processed (left) to ultra-processed (right) by mean lean", fontsize=8, color="#5f5e5a")
ax.set_title("Marketing words used together: one pleasure-and-convenience pitch, several kinds of purity talk", loc="left", fontsize=12.5)
fig.text(0.01, 0.01, "20,698 Amazon grocery listings, equal numbers of ultra-processed and less processed products in each of 25 food categories; ingredient words removed. Words are linked when they appear\n"
         "in the same listing more often than chance (PMI). Groups: Louvain on the full word network (16,265 links, modularity 0.53); 7 main groups shown, top 13 words each; seller boilerplate groups\n"
         "(package specs, disclaimers, retailer pitch) left out. Colour: which side uses the word more (measured on the other half of the listings): orange = ultra-processed, blue = less processed.\n"
         "Lines: each shown word's 4 strongest ties (for drawing only). Group names are our reading.", fontsize=7.4, color="#5f5e5a")
fig.subplots_adjust(left=0.01, right=0.99, top=0.94, bottom=0.08); fig.savefig("upf/figures/word_network.png", dpi=170); print("saved")
