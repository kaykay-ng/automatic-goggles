"""Topic REPLY network of r/StopEatingSeedOils (user request 27 Nov): the reply network mapped onto the 123 BERTopic topics. For every reply whose
own text and whose parent (comment or self-post) both have a topic (documents of 15+ words), count topic of the reply -> topic of the parent.
Same reply rules as reply_network.py: bots, AutoModerator and deleted accounts removed on both ends, self-replies dropped.
Null: expected count = (replies sent from topic A) x (replies received by topic B) / all replies (fixed in- and out-degrees, directed);
lift = observed / expected. Theme-pair lift = sum of observed / sum of expected over the topic pairs of the two themes.
95% intervals: 400 bootstrap resamples of THREADS (replies in one thread are not independent). Periods: by the reply's time, before / from
seedoil_common.SPLIT_TS. Also: (i) topic pairs significant against the null (Poisson upper tail, Benjamini-Hochberg q 0.01, off-diagonal,
both directions summed) -> undirected reply-topic network, Louvain (best of 20 seeds) and its agreement with the co-writing communities and
the 14 themes (AMI); (ii) reply lift on the 299 co-writing links of topic_cooccurrence_network.py against all other pairs.
Output: data/processed/topic_reply_network.json (aggregates only). Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/topic_reply_network.py"""
import glob
import gzip
import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from networkx.algorithms.community import louvain_communities, modularity
from scipy.stats import poisson
from sklearn.metrics import adjusted_mutual_info_score as ami

sys.path.insert(0, str(Path(__file__).parent))
from seedoil_common import is_bot, SPLIT_TS, THEMES_FILE  # noqa: E402

P, RAW = Path("seedoils/data/processed"), Path("seedoils/data/raw")
N_BOOT = 400; Q = 0.01
bad = lambda a: (not a) or a == "[deleted]" or is_bot(a)  # noqa: E731
posts = {}
with gzip.open(glob.glob(str(RAW / "*StopEatingSeedOils_posts.jsonl.gz"))[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); posts[x["id"]] = x.get("author") or ""
rows = []
with gzip.open(glob.glob(str(RAW / "*StopEatingSeedOils_comments.jsonl.gz"))[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); rows.append((x["id"], x.get("author") or "", x["parent_id"], x.get("link_id", ""), int(x["created_utc"])))
C = pd.DataFrame(rows, columns=["id", "a", "parent", "link", "t"]); cauth = dict(zip(C.id, C.a))
C["pid"] = C.parent.str[3:]; C["to_post"] = C.parent.str.startswith("t3_")
C["b"] = [posts.get(p, "") if tp else cauth.get(p, "") for p, tp in zip(C.pid, C.to_post)]
n_all = len(C); C = C[~C.a.map(bad) & ~C.b.map(bad) & (C.a != C.b)]; n_valid = len(C)
T = pd.read_csv(P / "seso_doc_topics.csv.gz", usecols=["id", "topic"]); T["id"] = T.id.astype(str); top = dict(zip(T.id, T.topic.astype(int)))
C["ta"] = C.id.map(top); C["tb"] = C.pid.map(top)
R = C.dropna(subset=["ta", "tb"]).copy(); R["ta"] = R.ta.astype(int); R["tb"] = R.tb.astype(int)
K = int(T.topic.max()) + 1
TH = json.loads((P / THEMES_FILE).read_text()); theme_of = {int(t): n.split(" (")[0] for n, ids in TH.items() for t in ids}
themes = sorted(set(theme_of.values())); tix = {t: i for i, t in enumerate(themes)}; thv = np.array([tix[theme_of[t]] for t in range(K)])
NET = json.loads((P / "topic_cooccurrence_network.json").read_text()); words = {n["topic"]: n["words"] for n in NET["nodes"]}
cow_comm = np.array([next(n["community"] for n in NET["nodes"] if n["topic"] == t) for t in range(K)])
COW_LINKS = {(min(e["a"], e["b"]), max(e["a"], e["b"])) for e in NET["edges_all"]}
print(f"replies: {n_all:,} comments; {n_valid:,} valid replies; {len(R):,} with a topic on both ends ({100 * len(R) / n_valid:.1f}%); "
      f"to posts {100 * R.to_post.mean():.1f}%", flush=True)


def counts(df):
    M = np.zeros((K, K)); np.add.at(M, (df.ta.values, df.tb.values), 1); return M


def expected(M):
    return np.outer(M.sum(1), M.sum(0)) / M.sum()


def theme_lift(M, E):
    tm = np.zeros((len(themes),) * 2); te = np.zeros_like(tm)
    np.add.at(tm, (thv[:, None].repeat(K, 1), thv[None, :].repeat(K, 0)), M); np.add.at(te, (thv[:, None].repeat(K, 1), thv[None, :].repeat(K, 0)), E)
    return tm, te


FOOD = [t for t in themes if t in {"Keto, carbs, fasting", "Other diets", "Specific oils", "Cooking and cooking fats", "Staple foods", "Shopping", "Ingredient labels and processed food"}]
KEY = [("Politics", ["Politics"]), ("Politics", FOOD), (FOOD, ["Politics"]), ("Politics", ["Omega-6 / PUFA biochemistry"]), (["Omega-6 / PUFA biochemistry"], ["Politics"]),
       ("Politics", ["Distrust of industry, medicine and media"]), (["Distrust of industry, medicine and media"], ["Politics"]),
       ("Politics", ["Studies and evidence"]), (["Studies and evidence"], ["Politics"]), ("Politics", ["Vaccines and COVID"]),
       (["Omega-6 / PUFA biochemistry"], ["Omega-6 / PUFA biochemistry"]), (["Omega-6 / PUFA biochemistry"], FOOD), (FOOD, ["Omega-6 / PUFA biochemistry"])]
KEY = [([a] if isinstance(a, str) else a, b) for a, b in KEY]
lab = lambda xs: "food, diet and shopping themes" if xs == FOOD else " + ".join(xs)  # noqa: E731


def summarise(df, seed):
    M = counts(df); E = expected(M); tm, te = theme_lift(M, E)
    links = df.link.values; ul, inv = np.unique(links, return_inverse=True); rng = np.random.default_rng(seed)
    by_thread = pd.Series(np.arange(len(df))).groupby(inv).apply(np.array).values
    boots = []
    for _ in range(N_BOOT):
        pick = np.concatenate([by_thread[i] for i in rng.integers(0, len(by_thread), len(by_thread))]); Mb = counts(df.iloc[pick]); Eb = expected(Mb)
        boots.append(theme_lift(Mb, Eb))
    out = {"replies": int(len(df)), "threads": int(len(ul)), "same_topic_share_pct": round(100 * float(np.trace(M) / M.sum()), 1),
           "same_topic_lift": round(float(np.trace(M) / np.trace(E)), 2),
           "same_theme_lift": round(float(np.trace(tm) / np.trace(te)), 2), "pairs": {}}
    for a, b in KEY:
        ia, ib = [tix[x] for x in a], [tix[x] for x in b]
        v = tm[np.ix_(ia, ib)].sum() / te[np.ix_(ia, ib)].sum(); bs = [bm[np.ix_(ia, ib)].sum() / be[np.ix_(ia, ib)].sum() for bm, be in boots]
        out["pairs"][f"{lab(a)} -> {lab(b)}"] = {"observed": int(tm[np.ix_(ia, ib)].sum()), "lift": round(float(v), 2),
                                                 "ci95": [round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)]}
    pol = tix["Politics"]; row = tm[pol]
    out["where_politics_replies_go_pct"] = {themes[j]: round(100 * float(row[j] / row.sum()), 1) for j in np.argsort(-row)[:6]}
    col = tm[:, pol]; out["who_replies_to_politics_pct"] = {themes[j]: round(100 * float(col[j] / col.sum()), 1) for j in np.argsort(-col)[:6]}
    return out, M, E


res = {"replies_all": n_all, "valid_replies": n_valid, "with_topics_both_ends": int(len(R)), "with_topics_pct": round(100 * len(R) / n_valid, 1)}
res["all_years"], M, E = summarise(R, 0)
res["before_2024"], _, _ = summarise(R[R.t < SPLIT_TS], 1)
res["from_2024"], _, _ = summarise(R[R.t >= SPLIT_TS], 2)
# (i) significant reply links between DIFFERENT topics (both directions summed) -> undirected network -> Louvain
S = M + M.T; ES = E + E.T; iu = np.triu_indices(K, 1); o, e = S[iu], ES[iu]
p = poisson.sf(o - 1, e); order = np.argsort(p); m = len(p); passed = np.zeros(m, bool); ok = p[order] <= Q * np.arange(1, m + 1) / m
if ok.any():
    passed[order[: np.max(np.where(ok)[0]) + 1]] = True
keep = passed & (o > e)
G = nx.Graph(); G.add_nodes_from(range(K)); G.add_weighted_edges_from((int(iu[0][k]), int(iu[1][k]), float(o[k] / e[k])) for k in np.where(keep)[0])
runs = [louvain_communities(G, weight="weight", seed=s) for s in range(20)]; mods = [modularity(G, c, weight="weight") for c in runs]; best = runs[int(np.argmax(mods))]
rc = np.array([next(i for i, c in enumerate(sorted(best, key=len, reverse=True)) if v in c) for v in range(K)])
res["reply_topic_network"] = {"links": int(keep.sum()), "density": round(float(keep.mean()), 3), "isolated_topics": int(sum(1 for v in G if G.degree(v) == 0)),
                              "modularity": round(float(max(mods)), 3), "communities_2plus": int(sum(1 for c in best if len(c) >= 2)),
                              "ami_vs_cowriting_communities": round(float(ami(cow_comm, rc)), 3), "ami_vs_14_themes": round(float(ami(thv, rc)), 3),
                              "links_also_cowriting_links": int(sum(1 for k in np.where(keep)[0] if (int(iu[0][k]), int(iu[1][k])) in COW_LINKS)),
                              "cowriting_links": len(COW_LINKS)}
res["reply_topic_network"]["edges"] = [{"a": int(iu[0][k]), "b": int(iu[1][k]), "replies": int(o[k]), "expected": round(float(e[k]), 1), "lift": round(float(o[k] / e[k]), 3),
                                         "a_to_b": int(M[iu[0][k], iu[1][k]]), "b_to_a": int(M[iu[1][k], iu[0][k]])} for k in np.where(keep)[0]]
res["reply_topic_network"]["community_of_topic"] = {int(t): int(rc[t]) for t in range(K)}
res["reply_topic_network"]["same_topic_replies"] = {int(t): int(M[t, t]) for t in range(K)}
pol_t = [t for t in range(K) if theme_of[t] == "Politics"]
res["reply_topic_network"]["politics_topic_neighbours"] = {int(t): sorted([(theme_of[u], words[u][:30]) for u in G[t]]) for t in pol_t}
# (ii) reply lift on co-writing links vs other pairs (between different topics)
lift_pairs = np.divide(o, e, out=np.zeros_like(o), where=e > 0); is_cow = np.array([(int(a), int(b)) in COW_LINKS for a, b in zip(*iu)])
res["reply_lift_on_cowriting_links"] = {"cowriting_links_sum_lift": round(float(o[is_cow].sum() / e[is_cow].sum()), 2),
                                        "other_pairs_sum_lift": round(float(o[~is_cow].sum() / e[~is_cow].sum()), 2)}
(P / "topic_reply_network.json").write_text(json.dumps(res, indent=1, default=float))
for per in ("all_years", "before_2024", "from_2024"):
    r = res[per]; print(f"\n== {per}: {r['replies']:,} replies, {r['threads']:,} threads; same topic {r['same_topic_share_pct']}% (lift {r['same_topic_lift']}), same theme lift {r['same_theme_lift']}")
    for k, v in r["pairs"].items():
        print(f"   {k:70s} {v['lift']:5.2f} [{v['ci95'][0]:.2f}, {v['ci95'][1]:.2f}]  (n {v['observed']:,})")
    print("   politics replies go to:", r["where_politics_replies_go_pct"]); print("   replies to politics come from:", r["who_replies_to_politics_pct"])
print("\nreply topic network:", {k: v for k, v in res["reply_topic_network"].items() if k not in ("politics_topic_neighbours", "edges", "community_of_topic", "same_topic_replies")})
print("politics topic neighbours:", res["reply_topic_network"]["politics_topic_neighbours"])
print("reply lift on co-writing links vs others:", res["reply_lift_on_cowriting_links"])
