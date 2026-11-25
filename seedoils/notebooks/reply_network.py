"""Reply network of r/StopEatingSeedOils (user request 25 Nov). Nodes: every account that wrote a post or comment (bots, AutoModerator and
[deleted] left out). Directed edge A -> B: A wrote a comment that replies to B's post (parent t3_, top-level comment) or to B's comment (parent t1_);
weight = number of such replies; self-replies dropped. All comments of any length, whole history (no date cap).
Reported (aggregates only, usernames never written: nodes are numbered by sorted name):
  size, density, replies to posts vs to comments; weakly / strongly connected components; reciprocity (share of linked pairs that reply both ways)
  against a degree-preserving directed null; in- and out-degree distributions (CCDF; power law vs lognormal, powerlaw package); clustering of the
  undirected simple graph against degree-preserving rewiring; degree assortativity; Louvain communities on the undirected weighted graph
  (modularity, sizes, agreement with the co-commenting topic communities for the 2,618 people in both, AMI); newcomers (first post or comment
  from 2024) vs the old guard: who replies to whom, against the expectation from activity alone; the same measures before 2024 and from 2024.
Outputs: data/processed/reply_network_nodes.csv, reply_network_edges.csv, reply_network_stats.json.
Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/reply_network.py"""
import glob
import gzip
import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_mutual_info_score

sys.path.insert(0, str(Path(__file__).parent))
from seedoil_common import is_bot  # noqa: E402

P, RAW = Path("seedoils/data/processed"), Path("seedoils/data/raw")
SPLIT = int(pd.Timestamp("2024-01-01", tz="UTC").timestamp())
rng = np.random.default_rng(0)


def load():
    posts = {}
    with gzip.open(glob.glob(str(RAW / "*StopEatingSeedOils_posts.jsonl.gz"))[0], "rt", encoding="utf-8") as f:
        for l in f:
            x = json.loads(l); posts[x["id"]] = (x.get("author") or "", int(x["created_utc"]))
    rows = []
    with gzip.open(glob.glob(str(RAW / "*StopEatingSeedOils_comments.jsonl.gz"))[0], "rt", encoding="utf-8") as f:
        for l in f:
            x = json.loads(l); rows.append((x["id"], x.get("author") or "", x["parent_id"], int(x["created_utc"])))
    C = pd.DataFrame(rows, columns=["id", "a", "parent", "t"])
    return posts, C


def bad(a):
    return (not a) or a == "[deleted]" or is_bot(a)


posts, C = load()
cauth = dict(zip(C.id, C.a))
C["kind"] = np.where(C.parent.str.startswith("t3_"), "post", "comment")
C["pid"] = C.parent.str[3:]
C["b"] = [posts.get(p, ("", 0))[0] if k == "post" else cauth.get(p, "") for p, k in zip(C.pid, C.kind)]
# activity per account (posts + comments), first appearance
act = pd.concat([pd.DataFrame({"a": [v[0] for v in posts.values()], "t": [v[1] for v in posts.values()], "post": 1}),
                 pd.DataFrame({"a": C.a, "t": C.t, "post": 0})])
act = act[~act.a.map(bad)]
users = act.groupby("a").agg(first=("t", "min"), n_posts=("post", "sum"), n=("t", "size"))
users["n_comments"] = users.n - users.n_posts; users = users.sort_index(); users["idx"] = np.arange(len(users))
users["newcomer"] = users["first"] >= SPLIT
idx = users.idx.to_dict()
E = C[~C.a.map(bad) & ~C.b.map(bad) & (C.a != C.b)].copy()
ok_a, ok_b = ~C.a.map(bad), ~C.b.map(bad)
lost = {"replies_total": int(len(C)), "by_deleted_or_bot_account": int((~ok_a).sum()), "parent_missing_deleted_or_bot": int((ok_a & ~ok_b).sum()),
        "self_replies": int((ok_a & ok_b & (C.a == C.b)).sum()), "self_replies_to_own_post": int((ok_a & ok_b & (C.a == C.b) & (C.kind == "post")).sum())}
E["u"], E["v"] = E.a.map(idx), E.b.map(idx)
print(f"accounts {len(users):,}; reply links (comment -> its parent's author) {len(E):,} of {len(C):,} comments")


def edges_of(df):
    g = df.groupby(["u", "v"]).agg(w=("id", "size"), to_post=("kind", lambda s: int((s == "post").sum())), first_t=("t", "min")).reset_index()
    g["to_comment"] = g.w - g.to_post
    return g


def digraph(g):
    G = nx.DiGraph(); G.add_weighted_edges_from(g[["u", "v", "w"]].itertuples(index=False, name=None)); return G


def reciprocity_null(G, reps=5):
    """Degree-preserving directed rewiring (directed edge swaps); returns reciprocity per run."""
    out = []
    for r in range(reps):
        H = nx.DiGraph(G); H.remove_edges_from(nx.selfloop_edges(H))
        e = list(H.edges()); m = len(e); s = np.random.default_rng(r)
        E2 = np.array(e); src, dst = E2[:, 0].copy(), E2[:, 1].copy()
        # shuffle targets among edges keeps in- and out-degrees exactly (a configuration-model style null); drop self-loops / multi-edges
        dst = dst[s.permutation(m)]
        H2 = nx.DiGraph(); H2.add_edges_from((a, b) for a, b in zip(src, dst) if a != b)
        out.append(nx.reciprocity(H2))
    return out


def clustering_null(U, reps=3):
    out = []
    for r in range(reps):
        H = U.copy(); nx.double_edge_swap(H, nswap=H.number_of_edges(), max_tries=H.number_of_edges() * 20, seed=r)
        out.append(nx.transitivity(H))
    return out


def fit_tail(x):
    import powerlaw
    x = np.asarray([v for v in x if v > 0])
    f = powerlaw.Fit(x, discrete=True, verbose=False); R, p = f.distribution_compare("power_law", "lognormal", normalized_ratio=True)
    return {"alpha": round(float(f.power_law.alpha), 2), "xmin": int(f.power_law.xmin), "loglik_ratio_pl_vs_lognormal": round(float(R), 2), "p": round(float(p), 3),
            "better": "power law" if R > 0 and p < .1 else ("lognormal" if R < 0 and p < .1 else "cannot tell")}


def ccdf(x):
    x = np.sort(np.asarray([v for v in x if v > 0])); u, c = np.unique(x, return_counts=True); s = 1 - (np.cumsum(c) - c) / len(x)
    keep = np.unique(np.round(np.geomspace(1, len(u), 60)).astype(int) - 1)
    return [[int(u[i]), round(float(s[i]), 6)] for i in keep]


def describe(g, label, full=True):
    G = digraph(g); U = nx.Graph(G.to_undirected())
    n, m = G.number_of_nodes(), G.number_of_edges()
    wcc = max(nx.weakly_connected_components(G), key=len); scc = max(nx.strongly_connected_components(G), key=len)
    indeg, outdeg = dict(G.in_degree()), dict(G.out_degree())
    d = {"period": label, "nodes": n, "edges": m, "replies": int(g.w.sum()), "share_replies_to_posts": round(float(g.to_post.sum() / g.w.sum()), 3),
         "density": float(f"{nx.density(G):.2e}"), "largest_weak_component_share": round(len(wcc) / n, 3), "largest_strong_component_share": round(len(scc) / n, 3),
         "reciprocity": round(nx.reciprocity(G), 4), "mean_out_degree": round(m / n, 2),
         "share_nodes_never_replied_to": round(float(np.mean([indeg[k] == 0 for k in G])), 3), "share_nodes_never_replying": round(float(np.mean([outdeg[k] == 0 for k in G])), 3),
         "transitivity_undirected": round(nx.transitivity(U), 4), "degree_assortativity_undirected": round(nx.degree_assortativity_coefficient(U), 3)}
    if full:
        rn = reciprocity_null(G); cn = clustering_null(U)
        d |= {"reciprocity_null_mean": round(float(np.mean(rn)), 4), "reciprocity_null_range": [round(min(rn), 4), round(max(rn), 4)],
              "transitivity_null_mean": round(float(np.mean(cn)), 4), "transitivity_null_range": [round(min(cn), 4), round(max(cn), 4)],
              "in_degree_fit": fit_tail(indeg.values()), "out_degree_fit": fit_tail(outdeg.values()),
              "in_degree_ccdf": ccdf(indeg.values()), "out_degree_ccdf": ccdf(outdeg.values()),
              "top1pct_share_of_replies_received": round(float(np.sort(g.groupby("v").w.sum().values)[::-1][:max(1, n // 100)].sum() / g.w.sum()), 3)}
    return d, G, U


def cohort_mixing(g):
    """Replies old->old, old->new, new->old, new->new: observed share vs expected if repliers picked targets in proportion to replies received."""
    nw = users.set_index("idx").newcomer
    g = g.assign(sn=g.u.map(nw), tn=g.v.map(nw)); obs = g.groupby(["sn", "tn"]).w.sum(); obs = obs / obs.sum()
    recv = g.groupby("tn").w.sum() / g.w.sum(); send = g.groupby("sn").w.sum() / g.w.sum()
    out = []
    for s_ in (False, True):
        for t_ in (False, True):
            e = send.get(s_, 0) * recv.get(t_, 0); o = obs.get((s_, t_), 0)
            out.append({"from": "newcomer" if s_ else "old guard", "to": "newcomer" if t_ else "old guard", "observed": round(float(o), 3), "expected": round(float(e), 3), "lift": round(float(o / e), 2) if e else None})
    return out


g_all = edges_of(E)
stats, G, U = describe(g_all, "all")
print(json.dumps({k: v for k, v in stats.items() if "ccdf" not in k}, indent=1))
stats["dropped"] = lost
# Louvain on the undirected weighted graph (weights summed both ways), largest weak component
Uw = nx.Graph()
for a, b, w in g_all[["u", "v", "w"]].itertuples(index=False, name=None):
    Uw.add_edge(a, b, weight=Uw[a][b]["weight"] + w if Uw.has_edge(a, b) else w)
core = Uw.subgraph(max(nx.connected_components(Uw), key=len)).copy()
parts = [nx.community.louvain_communities(core, weight="weight", seed=s, resolution=1.0) for s in range(5)]
lab = [dict((n, k) for k, c in enumerate(sorted(p, key=len, reverse=True)) for n in c) for p in parts]
nodes = sorted(core); amis = [adjusted_mutual_info_score([lab[0][n] for n in nodes], [l[n] for n in nodes]) for l in lab[1:]]
best = parts[0]; sizes = sorted((len(c) for c in best), reverse=True)
stats["louvain"] = {"nodes_in_largest_component": core.number_of_nodes(), "communities": len(best), "modularity": round(nx.community.modularity(core, best, weight="weight"), 3),
                    "largest_sizes": sizes[:12], "communities_with_100plus": int(sum(s >= 100 for s in sizes)), "ami_across_5_seeds_mean": round(float(np.mean(amis)), 3)}
# agreement with the co-commenting topic communities (commenter_topic_network_130), for the people in both
heavy = pd.read_csv(P / "commenter_topic_network_130_nodes.csv")
cand = C[~C.a.map(bad)].a.value_counts()
try:
    D = pd.read_csv(P / "seso_doc_topics.csv.gz", usecols=["id", "kind"]); D = D[D.kind == "comment"]; D["a"] = D.id.map(cauth)
    D = D[D.a.notna() & ~D.a.map(lambda a: bad(a) if isinstance(a, str) else True)]
    nd = D.groupby("a").size(); H = np.array(sorted(nd[nd >= 10].index))
    if len(H) == len(heavy):
        tc = dict(zip(H, heavy.community)); both = [a for a in H if idx.get(a) in lab[0]]
        stats["louvain"]["vs_topic_communities"] = {"people_in_both": len(both), "ami": round(adjusted_mutual_info_score([tc[a] for a in both], [lab[0][idx[a]] for a in both]), 3)}
except FileNotFoundError:
    pass
stats["cohort_mixing"] = cohort_mixing(g_all)  # confounded by time: before 2024 everyone is old guard
stats["cohort_mixing_from2024"] = cohort_mixing(edges_of(E[E.t >= SPLIT]))  # both cohorts present: the fair comparison
stats["periods"] = [describe(edges_of(E[E.t < SPLIT]), "before 2024", full=False)[0], describe(edges_of(E[E.t >= SPLIT]), "from 2024", full=False)[0]]
for d in stats["periods"]:
    print(d)
print("louvain:", stats["louvain"]); print("cohort mixing:", stats["cohort_mixing"]); print("cohort mixing from 2024:", stats["cohort_mixing_from2024"])
# outputs (no usernames)
users["louvain"] = users.idx.map(lab[0]).astype("Int64")
users["in_replies"] = users.idx.map(g_all.groupby("v").w.sum()).fillna(0).astype(int); users["out_replies"] = users.idx.map(g_all.groupby("u").w.sum()).fillna(0).astype(int)
users["first_month"] = pd.to_datetime(users["first"], unit="s").dt.strftime("%Y-%m")
users[["idx", "n_posts", "n_comments", "first_month", "newcomer", "in_replies", "out_replies", "louvain"]].to_csv(P / "reply_network_nodes.csv", index=False)
g_all.rename(columns={"u": "source", "v": "target", "w": "replies"}).to_csv(P / "reply_network_edges.csv", index=False)
(P / "reply_network_stats.json").write_text(json.dumps(stats, indent=1))
print("wrote reply_network_nodes.csv, reply_network_edges.csv, reply_network_stats.json")
