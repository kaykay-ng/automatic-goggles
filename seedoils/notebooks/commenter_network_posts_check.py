"""Does leaving self-posts out of the commenter topic network matter? (user question 27 Nov). commenter_topic_network_130.py builds each person's
profile from their COMMENTS only (topic-model documents of 15+ words). This check rebuilds the network with the same rules (IDF-weighted topic
counts, L2-normalised, cosine, disparity filter alpha 0.05, Louvain best of 20 seeds) in three versions:
  A  comments only, same as the main script (reproduction check: should match the saved communities);
  B  the same 2,621 people, profiles from comments AND their self-posts;
  C  the node rule also counts self-posts (>= 10 comments + self-posts), profiles from both (may add people).
Reported: people, self-posts added, backbone links, modularity, communities, and agreement (AMI, and the share of people whose community maps to
the same main community) with the saved communities (commenter_topic_network_130_nodes.csv), plus the long-time share of the Politics and
Omega-6 communities in each version. Output: data/processed/commenter_network_posts_check.json (aggregates only).
Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/commenter_network_posts_check.py"""
import glob
import gzip
import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from networkx.algorithms.community import louvain_communities, modularity
from sklearn.metrics import adjusted_mutual_info_score as ami

sys.path.insert(0, str(Path(__file__).parent))
from seedoil_common import not_bot, SPLIT_TS  # noqa: E402

P, RAW = Path("seedoils/data/processed"), Path("seedoils/data/raw"); MIN_DOCS = 10; ALPHA = 0.05
cauth, first = {}, {}
with gzip.open(glob.glob(str(RAW / "*StopEatingSeedOils_comments.jsonl.gz"))[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); cauth[x["id"]] = x["author"]; t = int(x["created_utc"]); first[x["author"]] = min(first.get(x["author"], t), t)
pauth = {}
with gzip.open(glob.glob(str(RAW / "*StopEatingSeedOils_posts.jsonl.gz"))[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); pauth[x["id"]] = x.get("author") or ""
D = pd.read_csv(P / "seso_doc_topics.csv.gz", usecols=["id", "kind", "topic"]); D["id"] = D.id.astype(str)
D["a"] = np.where(D.kind == "comment", D.id.map(cauth), D.id.map(pauth))
D = D[D.a.notna() & (D.a != "") & ~D.a.isin(["[deleted]", "AutoModerator"]) & not_bot(D.a.fillna(""))]
K = int(D.topic.max()) + 1
saved = pd.read_csv(P / "commenter_topic_network_130_nodes.csv")
nc = D[D.kind == "comment"].groupby("a").size(); base_users = np.array(sorted(nc[nc >= MIN_DOCS].index))
assert len(base_users) == len(saved), (len(base_users), len(saved))
base_comm = dict(zip(base_users, saved.community.values))


def build(users, docs):
    ui = {u: i for i, u in enumerate(users)}; d = docs[docs.a.isin(ui)]
    X = np.zeros((len(users), K)); np.add.at(X, (d.a.map(ui).values, d.topic.values), 1)
    idf = np.log(len(users) / (1 + (X > 0).sum(0))) + 1; Xw = X * idf; Xw /= np.linalg.norm(Xw, axis=1, keepdims=True)
    S = Xw @ Xw.T; np.fill_diagonal(S, 0); S[S < 1e-9] = 0; s = S.sum(1, keepdims=True); k = (S > 0).sum(1, keepdims=True)
    p = np.divide(S, s, out=np.zeros_like(S), where=s > 0); keep = (1 - p) ** np.maximum(k - 1, 1) < ALPHA; keep = np.triu(keep | keep.T, 1)
    G = nx.Graph(); G.add_nodes_from(range(len(users))); ii, jj = np.where(keep); G.add_weighted_edges_from(zip(ii.tolist(), jj.tolist(), S[ii, jj].tolist()))
    H = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    runs = [louvain_communities(H, weight="weight", seed=sd, resolution=1.0) for sd in range(20)]; mods = [modularity(H, c, weight="weight") for c in runs]
    best = sorted(runs[int(np.argmax(mods))], key=len, reverse=True); lab = {v: i for i, c in enumerate(best) for v in c}
    return {users[v]: lab[v] for v in H}, int(keep.sum()), round(float(np.mean(mods)), 3), len(best), int(len(d))


def compare(name, users, docs):
    lab, links, mod, nco, ndocs = build(users, docs)
    common = [u for u in lab if u in base_comm]; a, b = [base_comm[u] for u in common], [lab[u] for u in common]
    ct = pd.crosstab(pd.Series(a, name="saved"), pd.Series(b, name="new")); match = ct.max(1).sum() / ct.values.sum()  # each saved community -> its main new community
    res = {"people": int(len(users)), "documents": ndocs, "self_posts_used": int(docs[docs.a.isin(set(users)) & (docs.kind == "post")].shape[0]),
           "backbone_links": links, "modularity_mean": mod, "communities": nco, "people_in_both": len(common),
           "ami_vs_saved_communities": round(float(ami(a, b)), 3), "share_kept_with_main_group_pct": round(float(match * 100), 1)}
    for cname, cid in (("Politics", 1), ("Omega-6", 3)):
        members = [u for u in common if base_comm[u] == cid]; tgt = pd.Series([lab[u] for u in members]).mode()[0]
        grp = [u for u, c in lab.items() if c == tgt]
        res[f"{cname}_group"] = {"size": len(grp), "long_time_pct": round(100 * float(np.mean([first[u] < SPLIT_TS for u in grp])), 1),
                                 "share_of_saved_members_in_it_pct": round(100 * float(np.mean([lab[u] == tgt for u in members])), 1)}
    print(name, json.dumps(res), flush=True); return res


out = {"A_comments_only_reproduction": compare("A", base_users, D[D.kind == "comment"]),
       "B_same_people_plus_self_posts": compare("B", base_users, D)}
na = D.groupby("a").size(); out["C_node_rule_counts_self_posts"] = compare("C", np.array(sorted(na[na >= MIN_DOCS].index)), D)
out["self_posts_in_topic_model"] = int((D.kind == "post").sum()); out["documents_in_topic_model"] = int(len(D))
(P / "commenter_network_posts_check.json").write_text(json.dumps(out, indent=1))
