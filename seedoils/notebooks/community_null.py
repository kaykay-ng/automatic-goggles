"""Null model for Figure 2 (the 12 Louvain communities of the ~130-topic commenter network): do the communities exist beyond what a random network of the same size and density would show?
The earlier null (shuffle topic labels, keep the disparity filter) is not usable at ~130 topics: it leaves ~1,500 links against 55,748 so modularity cannot be compared. Here density is fixed:
 (1) SAME-DENSITY NULL. Real: cosine similarity of the IDF-weighted topic profiles, each person keeps their strongest links until the network has the same number of links as the page's backbone (union of top-m per person).
     Null: shuffle which comment has which topic among all comments (keeps each person's number of comments and each topic's total), recompute profiles, similarity and the same top-m network. 20 shuffles. Compare Louvain modularity, community count, and the share of links inside communities.
 (2) PER-COMMUNITY TEST on the page's own backbone: for each community, the number of links inside it against what random community labels of the same sizes would give (2,000 shuffles of the labels over people): z-score and empirical p.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python seedoils/notebooks/community_null.py   (aggregates only)"""
import glob
import gzip
import json
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from networkx.algorithms.community import louvain_communities, modularity

P = Path("seedoils/data/processed"); A = P / "artifact"; rng = np.random.default_rng(3)
raw = {}
with gzip.open(glob.glob("seedoils/data/raw/*StopEatingSeedOils_comments.jsonl.gz")[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); raw[x["id"]] = x["author"]
D = pd.read_csv(P / "seso_doc_topics.csv.gz"); D = D[D.kind == "comment"].copy(); D["a"] = D.id.map(raw)
D = D[D.a.notna() & ~D.a.isin(["[deleted]", "AutoModerator"])]; nd = D.groupby("a").size(); U = np.array(sorted(nd[nd >= 10].index)); ui = {u: i for i, u in enumerate(U)}
D = D[D.a.isin(set(U))]; a_idx = D.a.map(ui).values; t_idx = D.topic.values; K = int(t_idx.max()) + 1; n = len(U)
nodes = pd.read_csv(P / "commenter_topic_network_130_nodes.csv"); comm = nodes.community.values; E = json.load(open(A / "cn_edges.json"))["rows"]; target = len(E)
def profile(ti):
    X = np.zeros((n, K)); np.add.at(X, (a_idx, ti), 1); df = (X > 0).sum(0); Xw = X * (np.log(n / (1 + df)) + 1); return Xw / np.linalg.norm(Xw, axis=1, keepdims=True)
def topm_graph(Xw, m):
    S = Xw @ Xw.T; np.fill_diagonal(S, -1); nb = np.argpartition(-S, m, axis=1)[:, :m]; G = nx.Graph(); G.add_nodes_from(range(n))
    for i in range(n):
        for j in nb[i]: G.add_edge(i, int(j), weight=float(S[i, j]))
    return G
def find_m(Xw):
    lo, hi = 5, 60
    while lo < hi:
        mid = (lo + hi) // 2; e = topm_graph(Xw, mid).number_of_edges()
        if e < target: lo = mid + 1
        else: hi = mid
    return lo
def summarise(G):
    best = None
    for s in range(5):
        c = louvain_communities(G, weight="weight", seed=s); q = modularity(G, c, weight="weight")
        if best is None or q > best[0]: best = (q, c)
    q, c = best; lab = np.zeros(n, int)
    for k, s in enumerate(c): lab[list(s)] = k
    inside = np.mean([lab[a] == lab[b] for a, b in G.edges]); return q, len(c), inside
Xr = profile(t_idx); m = find_m(Xr); Gr = topm_graph(Xr, m); print(f"top-m per person: m={m}, links {Gr.number_of_edges():,} (page backbone {target:,})")
qr, kr, ir = summarise(Gr); print(f"REAL      : modularity {qr:.3f}, communities {kr}, links inside communities {ir:.1%}")
Q, KK, II = [], [], []
for r in range(20):
    Xp = profile(rng.permutation(t_idx)); Gp = topm_graph(Xp, m); q, k, i_ = summarise(Gp); Q.append(q); KK.append(k); II.append(i_)
print(f"SHUFFLED  : modularity {np.mean(Q):.3f} (range {min(Q):.3f}-{max(Q):.3f}), communities {np.mean(KK):.1f} (range {min(KK)}-{max(KK)}), links inside {np.mean(II):.1%}  [20 shuffles; edge count at m={m}: {Gp.number_of_edges():,}]")
# (2) per-community test on the page backbone
names = ['Shopping, food', 'Politics, vaccines', 'Omega-6 science', 'Evidence, the sub', 'Keto, LDL', 'Olive oil', 'Vegan, soy', 'Weight, fasting', 'Mayo, sugar', 'Pork, canola', 'Sun, skin', 'Formula, kids']
cn = json.load(open(A / "cn_nodes.json"))["rows"]; c = np.array([r["c"] for r in cn]); es = np.array([[e["s"], e["t"]] for e in E]); assert len(c) == n
obs = np.array([np.sum((c[es[:, 0]] == k) & (c[es[:, 1]] == k)) for k in range(12)]); null = np.zeros((2000, 12))
for r in range(2000):
    cp = rng.permutation(c); same = cp[es[:, 0]] == cp[es[:, 1]]; null[r] = [np.sum(same & (cp[es[:, 0]] == k)) for k in range(12)]
print("\n(2) links inside each community vs random labels of the same sizes (2,000 shuffles)")
for k in range(12):
    mu, sd = null[:, k].mean(), null[:, k].std(); p_ = (1 + np.sum(null[:, k] >= obs[k])) / 2001
    print(f"  {names[k]:<20} people {int(np.sum(c == k)):>4} | inside links {int(obs[k]):>6} vs expected {mu:>8.0f} (x{obs[k] / mu:.1f}) | z {(obs[k] - mu) / sd:7.1f} | p {p_:.4f}")
