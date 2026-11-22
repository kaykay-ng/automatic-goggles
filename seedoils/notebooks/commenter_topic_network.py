"""Commenter network from shared sub-topics in r/StopEatingSeedOils, with a statistical backbone (disparity filter) and communities (Louvain).
Nodes: commenters with >= MIN_DOCS topic-model documents (comments of >= 15 words; [deleted] and AutoModerator removed). Profile: counts over the 50 data-driven topics (seso_k50_doc_topics), IDF-weighted, L2-normalised.
Similarity: cosine of profiles -> a dense weighted network (every pair has a weight). Backbone: disparity filter (Serrano, Boguna, Vespignani 2009): per node, p_ij = w_ij / s_i and an edge is kept when (1 - p_ij)^(k_i - 1) < ALPHA for at least one end.
Why this filter: the network is complete (a plain threshold would keep mostly the heavy commenters' edges), the disparity filter judges each edge against the node's own strengths, so light commenters keep their strongest ties and no global cut-off is needed.
Checks: topic-label permutation null (modularity of the backbone communities against chance), stability of communities across Louvain seeds and ALPHA values. Aggregates only; no text.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/commenter_topic_network.py
"""
import gzip, glob, json, sys
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
from networkx.algorithms.community import louvain_communities, modularity
from sklearn.metrics import adjusted_mutual_info_score as ami
EXPORT = "--export" in sys.argv
P = Path("seedoils/data/processed"); CUT = pd.Timestamp("2024-01-01").timestamp(); MIN_DOCS = 10; ALPHA = 0.05; rng = np.random.default_rng(0)
raw = {}
with gzip.open(glob.glob("seedoils/data/raw/*StopEatingSeedOils_comments.jsonl.gz")[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); raw[x["id"]] = (x["author"], int(x["created_utc"]))
first = pd.Series({}, dtype=float); allc = pd.DataFrame([(a, t) for a, t in raw.values()], columns=["a", "t"]); first = allc.groupby("a").t.min()
D = pd.read_csv(P / "seso_k50_doc_topics.csv.gz"); D = D[D.kind == "comment"]; D["a"] = D.id.map(lambda i: raw.get(i, (None,))[0]); D = D[D.a.notna() & ~D.a.isin(["[deleted]", "AutoModerator"])]
n_docs = D.groupby("a").size()
for m in (5, 10, 20, 50): print(f"users with >= {m} topic docs: {(n_docs >= m).sum():,}")
U = n_docs[n_docs >= MIN_DOCS].index; D = D[D.a.isin(U)]; users = np.array(sorted(U)); ui = {u: i for i, u in enumerate(users)}; K = 50
print(f"nodes (MIN_DOCS={MIN_DOCS}): {len(users):,}; documents {len(D):,} = {len(D)/ (n_docs.sum())*100:.0f}% of all topic documents")
def profile(a_idx, t_idx):
    X = np.zeros((len(users), K)); np.add.at(X, (a_idx, t_idx), 1); df = (X > 0).sum(0); idf = np.log(len(users) / (1 + df)) + 1; Xw = X * idf; Xw /= np.linalg.norm(Xw, axis=1, keepdims=True); return X, Xw
a_idx = D.a.map(ui).values; t_idx = D.topic.values; X, Xw = profile(a_idx, t_idx)
def backbone(Xw, alpha):
    S = Xw @ Xw.T; np.fill_diagonal(S, 0); S[S < 1e-9] = 0; n = len(S); s = S.sum(1, keepdims=True); k = (S > 0).sum(1, keepdims=True)
    p = np.divide(S, s, out=np.zeros_like(S), where=s > 0); a = (1 - p) ** np.maximum(k - 1, 1); keep = (a < alpha); keep = keep | keep.T
    return S, np.triu(keep, 1)
S, K_ = backbone(Xw, ALPHA); n = len(S); full_edges = int((np.triu(S > 0, 1)).sum()); kept = int(K_.sum())
G = nx.Graph(); G.add_nodes_from(range(n)); ii, jj = np.where(K_); G.add_weighted_edges_from(zip(ii.tolist(), jj.tolist(), S[ii, jj].tolist()))
iso = [v for v in G if G.degree(v) == 0]; print(f"\nBACKBONE (disparity filter, alpha={ALPHA}): links {full_edges:,} -> {kept:,} ({kept/full_edges*100:.2f}% kept, {100-kept/full_edges*100:.2f}% removed); nodes with no remaining link: {len(iso)} of {n} ({len(iso)/n*100:.1f}%)")
cc = sorted(nx.connected_components(G), key=len, reverse=True); print(f"components: {len(cc)}; largest {len(cc[0])} nodes ({len(cc[0])/n*100:.0f}%); mean degree {2*kept/n:.1f}; median degree {np.median([d for _, d in G.degree()]):.0f}")
H = G.subgraph(cc[0]).copy()
def louv(H, seed): return louvain_communities(H, weight="weight", seed=seed, resolution=1.0)
runs = [louv(H, s) for s in range(20)]; nodes_H = sorted(H.nodes); lab = lambda c: np.array([next(i for i, s in enumerate(c) if v in s) for v in nodes_H])
labs = [lab(c) for c in runs]; mods = [modularity(H, c, weight="weight") for c in runs]; ref = int(np.argmax(mods))
amis = [ami(labs[ref], l) for i, l in enumerate(labs) if i != ref]; print(f"Louvain, 20 seeds on the largest component: modularity {np.mean(mods):.3f} (range {min(mods):.3f}-{max(mods):.3f}); communities {sorted(set(len(c) for c in runs))}; AMI vs reference mean {np.mean(amis):.2f} (min {np.min(amis):.2f})")
comm = runs[ref]; comm = sorted(comm, key=len, reverse=True); print("community sizes:", [len(c) for c in comm][:12]); base = {v: i for i, c in enumerate(comm) for v in c}
if not EXPORT:
    # null: permute topic labels among documents (keeps each user's number of documents and the topic frequencies)
    nm = []
    for r in range(5):
        t_perm = rng.permutation(t_idx); _, Xp = profile(a_idx, t_perm); Sp, Kp = backbone(Xp, ALPHA); Gp = nx.Graph(); Gp.add_nodes_from(range(n)); a, b = np.where(Kp); Gp.add_weighted_edges_from(zip(a.tolist(), b.tolist(), Sp[a, b].tolist()))
        c0 = max(nx.connected_components(Gp), key=len); Hp = Gp.subgraph(c0).copy(); cp = louvain_communities(Hp, weight="weight", seed=1); nm.append((Gp.number_of_edges(), len(c0), modularity(Hp, cp, weight="weight")))
    print("NULL (topic labels permuted among documents, 5 reps): backbone edges %s, largest component %s, modularity %.3f +/- %.3f  vs observed %.3f" % ([e for e, _, _ in nm], [c for _, c, _ in nm], np.mean([m for *_, m in nm]), np.std([m for *_, m in nm]), np.mean(mods)))
    # robustness to alpha
    base = {v: i for i, c in enumerate(comm) for v in c}
    for al in (0.01, 0.02, 0.1):
        S2, K2 = backbone(Xw, al); G2 = nx.Graph(); G2.add_nodes_from(range(n)); a, b = np.where(K2); G2.add_weighted_edges_from(zip(a.tolist(), b.tolist(), S2[a, b].tolist())); c0 = max(nx.connected_components(G2), key=len); H2 = G2.subgraph(c0).copy()
        c2 = louvain_communities(H2, weight="weight", seed=1); common = [v for v in H2 if v in base]; l2 = {v: i for i, c in enumerate(c2) for v in c}
        print(f"alpha={al}: links kept {int(K2.sum()):,} ({K2.sum()/full_edges*100:.2f}%), isolated {sum(1 for v in G2 if G2.degree(v)==0)}, largest component {len(c0)}, communities {len(c2)}, modularity {modularity(H2, c2, weight='weight'):.3f}, AMI vs alpha={ALPHA} on shared nodes {ami([base[v] for v in common],[l2[v] for v in common]):.2f}")
# describe communities
tinfo = pd.read_csv(P / "seso_k50_topics_info.csv").set_index("topic"); fa = first.reindex(users).values; old = fa < CUT
overall = X.sum(0) / X.sum()
print("\nCOMMUNITIES (reference run): size | share of long-time (first comment before 2024) | mean docs per user | top over-represented topics (share in community vs overall)")
res = []
for ci, c in enumerate(comm[:16] if EXPORT else comm[:8]):
    idx = np.array(sorted(c)); idx_users = idx  # nodes_H indices equal node ids
    share = X[idx].sum(0) / X[idx].sum(); lift = share / overall; top = np.argsort(-(share - overall))[:4]
    print(f"  C{ci}: {len(c):>4} | long-time {old[idx].mean()*100:3.0f}% | docs/user {X[idx].sum()/len(c):5.0f} | " + "; ".join(f"[{t}] {tinfo.loc[t,'top_words'].split(',')[0]}, {tinfo.loc[t,'top_words'].split(',')[1].strip()} ({share[t]*100:.0f}% vs {overall[t]*100:.0f}%)" for t in top))
    res.append({"community": ci, "size": len(c), "long_time_pct": round(old[idx].mean() * 100, 1), "docs_per_user": round(X[idx].sum() / len(c), 1), "top_topics": [int(t) for t in top]})
pd.DataFrame({"user_index": range(n), "author": users, "community": [base.get(i, -1) for i in range(n)], "old": old, "docs": X.sum(1)}).drop(columns="author").to_csv(P / "commenter_topic_network_nodes.csv", index=False)
json.dump(res, open(P / "commenter_topic_network_communities.json", "w"), indent=1)

if EXPORT:
    pos = nx.spring_layout(H, weight="weight", k=0.12, iterations=400, seed=2); order = sorted(H.nodes); ix = {v: i for i, v in enumerate(order)}
    xy = np.array([pos[v] for v in order]); lo, hi = xy.min(0), xy.max(0); xy = (xy - lo) / (hi - lo)
    cid = {v: i for i, c in enumerate(comm) for v in c}
    nodes = [{"c": cid[v], "o": int(old[v]), "d": int(X[v].sum()), "x": round(float(xy[ix[v], 0]), 4), "y": round(float(xy[ix[v], 1]), 4)} for v in order]
    edges = [[ix[a], ix[b]] for a, b in H.edges]
    comms = []
    for ci, c in enumerate(comm):
        idx = np.array(sorted(c)); share = X[idx].sum(0) / X[idx].sum(); top = np.argsort(-(share - overall))[:3]
        comms.append({"id": ci, "size": len(c), "long": round(float(old[idx].mean() * 100)), "dpu": round(float(X[idx].sum() / len(c))), "topics": [{"w": ", ".join(w.strip() for w in tinfo.loc[int(t_), "top_words"].split(",")[:3]), "s": round(float(share[t_] * 100), 1), "o": round(float(overall[t_] * 100), 1)} for t_ in top]})
    isolated = [v for v in range(n) if v not in H]
    out = {"nodes": nodes, "edges": edges, "comms": comms, "n_users": int(n), "links_full": full_edges, "links_kept": kept, "alpha": ALPHA, "min_docs": MIN_DOCS,
           "iso": {"n": len(isolated), "docs": round(float(X[isolated].sum(1).mean())), "long": round(float(old[isolated].mean() * 100)), "gen_share": round(float((X[isolated, int(np.argmax(overall))] / X[isolated].sum(1)).mean() * 100)),
                "gen_share_linked": round(float((X[sorted(H.nodes), int(np.argmax(overall))] / X[sorted(H.nodes)].sum(1)).mean() * 100)), "gen_words": ", ".join(w.strip() for w in tinfo.loc[int(np.argmax(overall)), "top_words"].split(",")[:3]), "gen_all": round(float(overall.max() * 100))}, "long_all": round(float(old.mean() * 100)),
           "meta": [{"label": "commenter_topic_network.py", "value": Path(__file__).read_text()}]}
    (P / "artifact" / "commenter_network.json").write_text(json.dumps(out)); print("exported", len(nodes), "nodes", len(edges), "edges", len(comms), "communities")
