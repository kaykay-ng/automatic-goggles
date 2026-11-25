"""INDEPENDENCE CHECK for the commenter niches (Figure 2). The niche network links commenters by the similarity of their TOPIC mixes, so it cannot confirm BERTopic's topics: it is built from them.
Here the same commenters are linked by something that never uses a topic label: WHICH THREADS they comment in. Profile = counts per thread (all their comments, link_id), IDF-weighted, L2-normalised;
cosine; the same disparity filter (alpha 0.05) and Louvain (20 seeds) as the topic network. Then:
  (1) AMI between the thread-based communities and the topic-based niches (same people), next to the AMI of the thread communities with arrival year (time confound) and of two Louvain runs of the topic network;
  (2) for each thread-based community, which of the 50 topics its members' comments over-represent (topics are used ONLY here, to describe), and whether the politics and vaccine topics are among them;
  (3) the share of each topic-based niche that lands in each thread community.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python seedoils/notebooks/commenter_thread_network.py   (needs commenter_topic_network_130.py run first for commenter_topic_network_130_nodes.csv)
Aggregates only; no usernames or text are written."""
from seedoil_common import community_labels  # hand-written community names
from seedoil_common import is_bot, not_bot  # shared bot rule: AutoModerator + names ending in 'bot'
import glob
import gzip
import json
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from networkx.algorithms.community import louvain_communities, modularity
from sklearn.metrics import adjusted_mutual_info_score as ami

P = Path("seedoils/data/processed"); ALPHA = 0.05; MIN_DOCS = 10; MIN_THREAD_USERS = 5
raw = {}
rows = []
with gzip.open(glob.glob("seedoils/data/raw/*StopEatingSeedOils_comments.jsonl.gz")[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); raw[x["id"]] = (x["author"], int(x["created_utc"]))
        rows.append((x["author"], x["link_id"], int(x["created_utc"])))
R = pd.DataFrame(rows, columns=["a", "thread", "t"])
first = R.groupby("a").t.min()
# the ~130 topics (refit 22 Nov; the k=50 merge is not rebuilt)
D = pd.read_csv(P / "seso_doc_topics.csv.gz"); D = D[D.kind == "comment"]; D["a"] = D.id.map(lambda i: raw.get(i, (None,))[0]); D = D[D.a.notna() & (~D.a.isin(["[deleted]", "AutoModerator"]) & not_bot(D.a))]
n_docs = D.groupby("a").size(); U = n_docs[n_docs >= MIN_DOCS].index; D = D[D.a.isin(U)]; users = np.array(sorted(U)); ui = {u: i for i, u in enumerate(users)}; n = len(users)
N0 = pd.read_csv(P / "commenter_topic_network_130_nodes.csv"); assert len(N0) == n, (len(N0), n)
topic_comm = N0.community.values  # -1 = not in the largest component
print(f"commenters {n:,}; in topic-network niches (largest component) {np.sum(topic_comm >= 0):,}; niche sizes {np.bincount(topic_comm[topic_comm >= 0])[:10].tolist()}")
# thread profiles
T = R[R.a.isin(set(users))]
tc = T.groupby(["a", "thread"]).size().reset_index(name="c")
users_per_thread = tc.groupby("thread").a.nunique(); keep = users_per_thread[users_per_thread >= MIN_THREAD_USERS].index
tc = tc[tc.thread.isin(keep)]; threads = {t: i for i, t in enumerate(sorted(keep))}
X = np.zeros((n, len(threads))); X[tc.a.map(ui).values, tc.thread.map(threads).values] = tc.c.values
has = X.sum(1) > 0
print(f"threads kept (>= {MIN_THREAD_USERS} of these commenters): {len(threads):,}; commenters with at least one: {has.sum():,}")
df = (X > 0).sum(0); idf = np.log(n / (1 + df)) + 1; Xw = X * idf; nr = np.linalg.norm(Xw, axis=1, keepdims=True); Xw = np.divide(Xw, nr, out=np.zeros_like(Xw), where=nr > 0)
S = Xw @ Xw.T; np.fill_diagonal(S, 0); S[S < 1e-9] = 0; s = S.sum(1, keepdims=True); k = (S > 0).sum(1, keepdims=True)
p = np.divide(S, s, out=np.zeros_like(S), where=s > 0); a = (1 - p) ** np.maximum(k - 1, 1); keepm = a < ALPHA; keepm = keepm | keepm.T; Kt = np.triu(keepm, 1)
G = nx.Graph(); G.add_nodes_from(range(n)); ii, jj = np.where(Kt); G.add_weighted_edges_from(zip(ii.tolist(), jj.tolist(), S[ii, jj].tolist()))
full = int(np.triu(S > 0, 1).sum()); print(f"thread backbone: links {full:,} -> {int(Kt.sum()):,} ({Kt.sum() / full * 100:.2f}% kept); isolated {sum(1 for v in G if G.degree(v) == 0)}")
cc = sorted(nx.connected_components(G), key=len, reverse=True); H = G.subgraph(cc[0]).copy(); print(f"largest component {len(cc[0])} ({len(cc[0]) / n * 100:.0f}%)")
runs = [louvain_communities(H, weight="weight", seed=sd) for sd in range(20)]; mods = [modularity(H, c, weight="weight") for c in runs]; ref = int(np.argmax(mods))
nodes_H = sorted(H.nodes); labf = lambda c: np.array([next(i for i, s_ in enumerate(c) if v in s_) for v in nodes_H]); labs = [labf(c) for c in runs]
print(f"Louvain (20 seeds): modularity {np.mean(mods):.3f}; communities {sorted(set(len(c) for c in runs))}; AMI vs reference mean {np.mean([ami(labs[ref], l) for i, l in enumerate(labs) if i != ref]):.2f}")
comm = sorted(runs[ref], key=len, reverse=True); thread_comm = np.full(n, -1)
for ci, c in enumerate(comm):
    for v in c: thread_comm[v] = ci
print("thread-community sizes:", [len(c) for c in comm][:14])
both = (thread_comm >= 0) & (topic_comm >= 0)
yr = pd.to_datetime(first.reindex(users).values, unit="s").year.values
print(f"\n(1) AGREEMENT on {both.sum():,} commenters in both networks")
print(f"  AMI thread communities vs topic niches: {ami(thread_comm[both], topic_comm[both]):.3f}")
print(f"  AMI thread communities vs year of first comment: {ami(thread_comm[both], yr[both]):.3f}   (topic niches vs year: {ami(topic_comm[both], yr[both]):.3f})")
# baseline: shuffled niche labels
rng = np.random.default_rng(0); print(f"  shuffled niche labels (10 reps): AMI mean {np.mean([ami(thread_comm[both], rng.permutation(topic_comm[both])) for _ in range(10)]):.3f}")
# topic description of thread communities
tinfo = pd.read_csv(P / "seso_topics_info.csv").set_index("topic"); Xt = np.zeros((n, int(D.topic.max()) + 1)); np.add.at(Xt, (D.a.map(ui).values, D.topic.values), 1); overall = Xt.sum(0) / Xt.sum()
word = lambda t: ", ".join(w.strip() for w in tinfo.loc[t, "top_words"].split(",")[:3])
pol = [t for t in tinfo.index if any(("rfk" in w or "trump" in w) for w in tinfo.loc[t, "top_words"].split(",")[:4])]; vac = [t for t in tinfo.index if any(w.strip() in ("vaccines", "vaccine") for w in tinfo.loc[t, "top_words"].split(",")[:3])]
print(f"\n(2) topics over-represented in each thread-based community (politics topic ids {pol}, vaccine topic ids {vac}); topics used only to describe")
for ci, c in enumerate(comm[:12]):
    idx = np.array(sorted(c)); sh = Xt[idx].sum(0) / Xt[idx].sum(); top = np.argsort(-(sh - overall))[:3]
    print(f"  T{ci}: {len(c):>4} people | " + "; ".join(f"[{t}] {word(t)} ({sh[t] * 100:.0f}% vs {overall[t] * 100:.0f}%)" for t in top) + f" | politics share {sh[pol].sum() * 100:.0f}% (all {overall[pol].sum() * 100:.0f}%), vaccines {sh[vac].sum() * 100:.1f}% (all {overall[vac].sum() * 100:.1f}%)")
print("\n(3) where each topic-based niche's people land (% of the niche in thread community T0..T7; other = T8+ or none)")
LAB = community_labels(int(topic_comm.max()) + 1)[1]
print(f"  {'niche':<20}{'n':>5} " + "".join(f"{'T' + str(j):>5}" for j in range(8)) + "  other")
for ci in range(len(LAB)):
    m = topic_comm == ci; row = [np.sum(m & (thread_comm == j)) / m.sum() * 100 for j in range(8)]
    print(f"  {LAB[ci]:<20}{m.sum():>5} " + "".join(f"{v:>5.0f}" for v in row) + f"  {100 - sum(row):>4.0f}")
