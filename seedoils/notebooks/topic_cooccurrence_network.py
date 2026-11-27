"""Topic network of r/StopEatingSeedOils (user request 27 Nov): which BERTopic topics are written about by the SAME people more often than chance?
Nodes: the 123 BERTopic topics (seso_doc_topics; every topic-model document, comments and self-posts of 15+ words), coloured by the 14 hand-made
themes (seedoil_common.THEMES_FILE). Data: a binary person x topic matrix (1 = the person wrote at least one document in the topic); people with
documents in 2+ topics (others cannot co-occur); bots, AutoModerator and [deleted] removed.
Observed weight of a topic pair = number of people who wrote in both.
Null (degree preserving): the curveball algorithm (Strona et al. 2014, Nat. Commun.) randomises the bipartite person-topic matrix while keeping
EXACTLY every person's number of topics and every topic's number of people. One chain: burn-in 10 x people trades, then a sample every 2 x people
trades, N_SAMPLES samples. Expected weight E = null mean; z = (O - E) / null sd.
Edge: O above every null sample AND z significant after Benjamini-Hochberg (q = 0.01, normal tail); weight = lift O / E.
Reported: edges, density, Louvain communities (best modularity of 20 seeds, stability across seeds) and their agreement with the 14 themes (AMI,
NMI, against shuffled theme labels), share of edges inside a theme; per period (before / from seedoil_common.SPLIT_TS) the same network with its
own null on EQUAL numbers of people (the larger period subsampled, seed 0): edge overlap (Jaccard), theme-to-theme edge density before -> from,
and the topics that gained or lost the most links.
Output: data/processed/topic_cooccurrence_network.json (topic ids, words and aggregates only).
Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/topic_cooccurrence_network.py [n_samples]"""
import glob
import gzip
import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from networkx.algorithms.community import louvain_communities, modularity
from scipy.sparse import csr_matrix
from scipy.stats import norm
from sklearn.metrics import adjusted_mutual_info_score as ami, normalized_mutual_info_score as nmi

sys.path.insert(0, str(Path(__file__).parent))
from seedoil_common import not_bot, SPLIT_TS, THEMES_FILE  # noqa: E402

P, RAW = Path("seedoils/data/processed"), Path("seedoils/data/raw_haoyu")  # 27 Nov: reference raw data (the rerun); outliers.py table below
REB = Path("seedoils/data/processed_rebuild_prob")
N_SAMPLES = int(sys.argv[1]) if len(sys.argv) > 1 else 300
Q = 0.01
cauth, pauth = {}, {}
with gzip.open(glob.glob(str(RAW / "*StopEatingSeedOils_comments.jsonl.gz"))[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); cauth[x["id"]] = x["author"]
with gzip.open(glob.glob(str(RAW / "*StopEatingSeedOils_posts.jsonl.gz"))[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); pauth[x["id"]] = x.get("author") or ""
D = pd.read_csv(REB / "seso_doc_topics_official005.csv.gz", usecols=["id", "created_utc", "topic"]); D["id"] = D.id.astype(str)
# 27 Nov: ONLY documents with a confident topic = BERTopic's reduce_outliers (probabilities strategy, threshold 0.05; outliers_official.py); outliers below it (topic -1, 28.8% of documents) are not used
D = D[D.topic >= 0].copy(); _k = pd.read_csv(REB / "seso_doc_topics.csv.gz", usecols=["id", "kind"]); D["kind"] = D.id.map(dict(zip(_k.id.astype(str), _k.kind)))
D["a"] = np.where(D.kind == "comment", D.id.map(cauth), D.id.map(pauth))
D = D[D.a.notna() & (D.a != "") & ~D.a.isin(["[deleted]", "AutoModerator"]) & not_bot(D.a.fillna(""))]
K = int(D.topic.max()) + 1
TH = json.loads((P / THEMES_FILE).read_text()); theme_of = {int(t): name for name, ids in TH.items() for t in ids}
short = {name: name.split(" (")[0] for name in TH}
info = pd.read_csv(REB / "seso_topics_info.csv").set_index("topic")
words = {int(t): ", ".join(w.strip() for w in str(info.loc[t, "top_words"]).split(",")[:4]) for t in range(K)}
IU = np.triu_indices(K, 1)


def rows_of(docs, people=None):
    s = docs.groupby("a").topic.apply(lambda x: frozenset(int(t) for t in x))
    s = s[s.map(len) >= 2]
    if people is not None:
        s = s.loc[people]
    return [set(r) for r in s.values]


def cooc(rows):
    ri = np.repeat(np.arange(len(rows)), [len(r) for r in rows]); ci = np.fromiter((t for r in rows for t in r), dtype=np.int64)
    B = csr_matrix((np.ones(len(ci), dtype=np.float32), (ri, ci)), shape=(len(rows), K))
    return np.asarray((B.T @ B).todense())[IU]


def curveball(rows, n_samples, seed):
    rng = np.random.default_rng(seed); rows = [set(r) for r in rows]; n = len(rows); out = np.empty((n_samples, len(IU[0])), dtype=np.float32)

    def trades(m):
        pairs = rng.integers(0, n, size=(m, 2))
        for a, b in pairs:
            if a == b:
                continue
            A, Bs = rows[a], rows[b]; ao, bo = A - Bs, Bs - A
            if not ao or not bo:
                continue
            pool = list(ao | bo); rng.shuffle(pool); k = len(ao)
            rows[a] = (A & Bs) | set(pool[:k]); rows[b] = (A & Bs) | set(pool[k:])
    trades(10 * n)
    for s in range(n_samples):
        trades(2 * n); out[s] = cooc(rows)
    return out


def network(rows, n_samples, seed, label):
    O = cooc(rows); Nl = curveball(rows, n_samples, seed); E = Nl.mean(0); sd = Nl.std(0); mx = Nl.max(0)
    z = np.divide(O - E, sd, out=np.zeros_like(E), where=sd > 0); p = norm.sf(z)
    order = np.argsort(p); m = len(p); passed = np.zeros(m, bool)
    ok = p[order] <= Q * np.arange(1, m + 1) / m
    if ok.any():
        passed[order[: np.max(np.where(ok)[0]) + 1]] = True
    keep = passed & (O > mx) & (E > 0)
    print(f"{label}: people {len(rows):,}; pairs {m:,}; edges {int(keep.sum()):,} ({keep.mean()*100:.1f}% of pairs)", flush=True)
    ed = [(int(IU[0][k]), int(IU[1][k]), float(O[k] / E[k]), float(z[k]), int(O[k])) for k in np.where(keep)[0]]
    return ed, O, E


def communities(ed):
    G = nx.Graph(); G.add_nodes_from(range(K)); G.add_weighted_edges_from((i, j, w) for i, j, w, _, _ in ed)
    runs = [louvain_communities(G, weight="weight", seed=s) for s in range(20)]; mods = [modularity(G, c, weight="weight") for c in runs]
    lab = lambda c: np.array([next(k for k, s_ in enumerate(sorted(c, key=len, reverse=True)) if v in s_) for v in range(K)])  # noqa: E731
    L = [lab(c) for c in runs]; ref = int(np.argmax(mods)); comm = L[ref]
    th = np.array([theme_of.get(t, "none") for t in range(K)])
    rng = np.random.default_rng(1)
    res = {"edges": len(ed), "density": round(2 * len(ed) / (K * (K - 1)), 3), "isolated_topics": int(sum(1 for v in G if G.degree(v) == 0)),
           "modularity_best": round(float(max(mods)), 3), "modularity_mean": round(float(np.mean(mods)), 3), "communities": int(len(set(comm))),
           "community_sizes": [int(x) for x in np.bincount(comm)],
           "stability_ami_across_seeds": round(float(np.mean([ami(comm, l_) for i, l_ in enumerate(L) if i != ref])), 3),
           "ami_vs_14_themes": round(float(ami(th, comm)), 3), "nmi_vs_14_themes": round(float(nmi(th, comm)), 3),
           "ami_vs_shuffled_themes": round(float(np.mean([ami(rng.permutation(th), comm) for _ in range(200)])), 3),
           "edges_inside_a_theme_pct": round(100 * float(np.mean([th[i] == th[j] for i, j, *_ in ed])), 1) if ed else None,
           "pairs_inside_a_theme_pct": round(100 * float(np.mean(th[IU[0]] == th[IU[1]])), 1)}
    res["community_contents"] = [{"community": int(c), "topics": int((comm == c).sum()),
                                  "themes": pd.Series(th[comm == c]).map(short).value_counts().head(4).to_dict(),
                                  "example_topics": [words[t] for t in sorted(np.where(comm == c)[0], key=lambda t: -info.loc[t, "n_docs"])[:4]]}
                                 for c in range(len(set(comm)))]
    return res, comm


def theme_density(ed):
    names = list(TH); ix = {n: i for i, n in enumerate(names)}; cnt = np.zeros((len(names),) * 2); pos = np.zeros_like(cnt)
    for a, b in zip(*IU):
        ta, tb = theme_of.get(int(a)), theme_of.get(int(b))
        if ta and tb:
            i, j = sorted((ix[ta], ix[tb])); pos[i, j] += 1
    for a, b, *_ in ed:
        ta, tb = theme_of.get(a), theme_of.get(b)
        if ta and tb:
            i, j = sorted((ix[ta], ix[tb])); cnt[i, j] += 1
    return {(short[names[i]], short[names[j]]): (cnt[i, j], pos[i, j]) for i in range(len(names)) for j in range(i, len(names)) if pos[i, j]}


out = {"n_samples": N_SAMPLES, "q": Q, "topics": K, "themes_file": THEMES_FILE}
rows_all = rows_of(D); ed_all, O_all, E_all = network(rows_all, N_SAMPLES, 0, "all years")
res_all, comm_all = communities(ed_all); out["all_years"] = {"people": len(rows_all), **res_all}
print(json.dumps({k: v for k, v in res_all.items() if k != "community_contents"}), flush=True)
for c in res_all["community_contents"]:
    print(" ", c, flush=True)
# periods with equal numbers of people
pre, post = D[D.created_utc < SPLIT_TS], D[D.created_utc >= SPLIT_TS]
spre = pre.groupby("a").topic.nunique(); spost = post.groupby("a").topic.nunique()
ppl_pre, ppl_post = np.array(sorted(spre[spre >= 2].index)), np.array(sorted(spost[spost >= 2].index))
n_eq = min(len(ppl_pre), len(ppl_post)); rs = np.random.default_rng(0)
ppl_pre_s = ppl_pre if len(ppl_pre) == n_eq else np.sort(rs.choice(ppl_pre, n_eq, replace=False))
ppl_post_s = ppl_post if len(ppl_post) == n_eq else np.sort(rs.choice(ppl_post, n_eq, replace=False))
ed_pre, O_pre, E_pre = network(rows_of(pre, ppl_pre_s), N_SAMPLES, 1, "before")
ed_post, O_post, E_post = network(rows_of(post, ppl_post_s), N_SAMPLES, 2, "from")
r_pre, c_pre = communities(ed_pre); r_post, c_post = communities(ed_post)
S1, S2 = {(i, j) for i, j, *_ in ed_pre}, {(i, j) for i, j, *_ in ed_post}
deg = lambda ed: np.bincount([x for i, j, *_ in ed for x in (i, j)], minlength=K)  # noqa: E731
dpre, dpost = deg(ed_pre), deg(ed_post); dd = dpost - dpre
tdp, tdq = theme_density(ed_pre), theme_density(ed_post)
td = sorted(({"themes": f"{a} - {b}", "edges_before": int(tdp[(a, b)][0]), "edges_from": int(tdq[(a, b)][0]), "possible": int(tdp[(a, b)][1]),
              "density_before": round(tdp[(a, b)][0] / tdp[(a, b)][1], 3), "density_from": round(tdq[(a, b)][0] / tdq[(a, b)][1], 3)} for (a, b) in tdp),
            key=lambda r: -(r["density_from"] - r["density_before"]))
out["periods"] = {"people_each": int(n_eq), "people_available": {"before": int(len(ppl_pre)), "from": int(len(ppl_post))},
                  "before": r_pre, "from": r_post, "edges_in_both": len(S1 & S2), "jaccard_edges": round(len(S1 & S2) / len(S1 | S2), 3),
                  "ami_communities_before_vs_from": round(float(ami(c_pre, c_post)), 3),
                  "topics_gaining_links": [{"topic": int(t), "words": words[int(t)], "theme": short.get(theme_of.get(int(t)), "none"), "before": int(dpre[t]), "from": int(dpost[t])} for t in np.argsort(-dd)[:12]],
                  "topics_losing_links": [{"topic": int(t), "words": words[int(t)], "theme": short.get(theme_of.get(int(t)), "none"), "before": int(dpre[t]), "from": int(dpost[t])} for t in np.argsort(dd)[:12]],
                  "theme_pairs_density_change": td[:15] + td[-10:]}
for k in ("before", "from"):
    print(k, json.dumps({kk: vv for kk, vv in out["periods"][k].items() if kk != "community_contents"}), flush=True)
print("jaccard", out["periods"]["jaccard_edges"], "ami before vs from", out["periods"]["ami_communities_before_vs_from"])
for r in out["periods"]["topics_gaining_links"][:8]:
    print("GAIN", r)
for r in td[:10]:
    print("THEME PAIR UP", r)
for r in td[-6:]:
    print("THEME PAIR DOWN", r)
# robustness of the period comparison: 10 different random samples of the larger period (the smaller period is used whole)
KEY = [("Politics", "Politics"), ("Politics", "Vaccines and COVID"), ("Distrust of industry", "Politics"), ("Omega-6 / PUFA biochemistry", "Keto"),
       ("Omega-6 / PUFA biochemistry", "Omega-6 / PUFA biochemistry"), ("Omega-6 / PUFA biochemistry", "Studies and evidence")]
def pick(td_, a, b):  # noqa: E302
    for (x, y), (c, n) in td_.items():
        if {x.split(",")[0], y.split(",")[0]} == {a.split(",")[0], b.split(",")[0]}:
            return int(c), int(n)
    return None
big_is_post = len(ppl_post) > len(ppl_pre); reps = []  # noqa: E305
for sd in range(10):
    rr = np.random.default_rng(100 + sd); samp = np.sort(rr.choice(ppl_post if big_is_post else ppl_pre, n_eq, replace=False))
    e_, *_ = network(rows_of(post if big_is_post else pre, samp), N_SAMPLES, 10 + sd, f"rep {sd}")
    t_ = theme_density(e_); th_ = {int(t): theme_of.get(int(t)) for t in range(K)}
    reps.append({"edges": len(e_), "inside_theme_pct": round(100 * float(np.mean([th_[i] == th_[j] for i, j, *_ in e_])), 1) if e_ else None,
                 "isolated": int(K - len({x for i, j, *_ in e_ for x in (i, j)})), **{f"{a} - {b}": pick(t_, a, b)[0] for a, b in KEY}})
R = pd.DataFrame(reps); base_t = theme_density(ed_pre if big_is_post else ed_post)
out["periods"]["resampled_" + ("from" if big_is_post else "before")] = {
    "reps": len(R), "edges_range": [int(R.edges.min()), int(R.edges.max())],
    "inside_theme_pct_range": [float(R.inside_theme_pct.min()), float(R.inside_theme_pct.max())], "isolated_range": [int(R.isolated.min()), int(R.isolated.max())],
    "key_theme_pairs": {f"{a} - {b}": {"possible": pick(base_t, a, b)[1], ("before" if big_is_post else "from"): pick(base_t, a, b)[0],
                                       ("from_range" if big_is_post else "before_range"): [int(R[f'{a} - {b}'].min()), int(R[f'{a} - {b}'].max())]} for a, b in KEY}}
print("RESAMPLED", json.dumps(out["periods"]["resampled_" + ("from" if big_is_post else "before")]), flush=True)
# drawing data (all years): nodes with theme, community, size; edges with lift
out["nodes"] = [{"topic": t, "words": words[t], "theme": short.get(theme_of.get(t), "none"), "community": int(comm_all[t]), "docs": int(info.loc[t, "n_docs"]),
                 "degree_all": int(deg(ed_all)[t]), "degree_before": int(dpre[t]), "degree_from": int(dpost[t])} for t in range(K)]
out["edges_all"] = [{"a": i, "b": j, "lift": round(w, 3), "z": round(z_, 1), "people": o} for i, j, w, z_, o in ed_all]
out["edges_before"] = [{"a": i, "b": j, "lift": round(w, 3)} for i, j, w, *_ in ed_pre]
out["edges_from"] = [{"a": i, "b": j, "lift": round(w, 3)} for i, j, w, *_ in ed_post]
(P / "topic_cooccurrence_network.json").write_text(json.dumps(out, indent=1))
print("wrote topic_cooccurrence_network.json")
