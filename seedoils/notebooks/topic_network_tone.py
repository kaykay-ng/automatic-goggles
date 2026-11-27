"""Tone and downvotes on the topic co-writing network (user question 27 Nov). For every topic-model document of r/StopEatingSeedOils
(comments and self-posts of 15+ words): disapproving tone = GoEmotions max(anger, annoyance, disapproval, disgust) >= 0.5 (goemo_seso.npz,
the hand-checked flag); downvoted = Reddit score <= 0 (seso_docs.csv.gz). Grouped by the Louvain communities of the topic network
(topic_cooccurrence_network.json), the five politics topics, the saturated-fat hub (topic 4), and all documents; before vs from
seedoil_common.SPLIT_TS. 95% intervals: 1,000 bootstrap resamples of THREADS (documents in a thread are not independent).
Also: across topics, Spearman correlation of the change in tone / downvotes with the topic's network position (degree, participation).
Output: data/processed/topic_network_tone.json (aggregates only). Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/topic_network_tone.py"""
import glob
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).parent))
from seedoil_common import SPLIT_TS  # noqa: E402

P = Path("seedoils/data/processed"); RAW = Path("seedoils/data/raw")
LAB = list(pd.read_csv(P / "goemo_monthly.csv", nrows=1).columns[1:29])
g = np.load(P / "goemo_seso.npz", allow_pickle=True)
G = pd.DataFrame({"id": g["id"].astype(str), "dis": g["p"][:, [LAB.index(x) for x in ("anger", "annoyance", "disapproval", "disgust")]].astype(np.float32).max(1) >= 0.5})
D = pd.read_csv(P / "seso_doc_topics.csv.gz", usecols=["id", "created_utc", "topic"]); D["id"] = D.id.astype(str)
S = pd.read_csv(P / "seso_docs.csv.gz", usecols=["id", "score"]); S["id"] = S.id.astype(str)
link, rows = {}, []
with gzip.open(glob.glob(str(RAW / "*StopEatingSeedOils_comments.jsonl.gz"))[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); link[x["id"]] = x.get("link_id", "")[3:]; rows.append((x["id"], x.get("link_id", "")[3:], x.get("score", 0), int(x["created_utc"])))
# reception (27 Nov, user: normalise the score): a comment's score as a percentile among ALL comments of its own thread (ties share the mean
# rank; threads with >= 5 comments), so thread popularity, size and age cancel out. 50 = typical for its thread.
A = pd.DataFrame(rows, columns=["id", "thread", "score", "t"]); A = A[A.groupby("thread").id.transform("size") >= 5]
A["reception"] = (A.groupby("thread").score.rank(method="average") - 0.5) / A.groupby("thread").score.transform("size") * 100
RECEP = dict(zip(A.id, A.reception)); T_END = int(A.t.max())
D = D.merge(G, on="id").merge(S, on="id"); D["down"] = D.score <= 0; D["post"] = D.created_utc >= SPLIT_TS
D["recep"] = D.id.map(RECEP); D["old30"] = D.created_utc <= T_END - 30 * 86400  # at least 30 days old when the data were collected
D["down30"] = np.where(D.old30, D.down, np.nan)
D["thread"] = D.id.map(link).fillna(D.id)  # self-posts are their own thread
NET = json.loads((P / "topic_cooccurrence_network.json").read_text()); C = json.loads((P / "topic_network_centrality.json").read_text())
nodes = {n["topic"]: n for n in NET["nodes"]}; names = {int(k): v for k, v in C["community_names"].items()}
D["comm"] = D.topic.map(lambda t: nodes[int(t)]["community"]); D["theme"] = D.topic.map(lambda t: nodes[int(t)]["theme"])
SETS = {"all documents": D.index == D.index, "five politics topics": D.theme == "Politics", "saturated-fat hub (topic 4)": D.topic == 4}
for c, nm in names.items():
    SETS[f"community: {nm}"] = D.comm == c
SETS["topics without a link or in small groups"] = ~D.topic.isin([int(k) for k in C["layout"]])
rng = np.random.default_rng(0)


def stats(df):
    th = df.thread.values; ut, inv = np.unique(th, return_inverse=True)
    r_ok = df.recep.notna(); d_ok = df.down30.notna()
    sums = pd.DataFrame({"inv": inv, "dis": df.dis.values, "down": df.down.values, "n": 1, "recep": df.recep.fillna(0).values, "n_recep": r_ok.values.astype(int),
                         "down30": df.down30.fillna(0).values, "n_down30": d_ok.values.astype(int)}).groupby("inv").sum()
    out = {"documents": int(len(df)), "disapproving_pct": round(100 * float(df.dis.mean()), 2), "downvoted_pct": round(100 * float(df.down.mean()), 2),
           "reception_pct": round(float(df.recep.mean()), 2), "downvoted30_pct": round(100 * float(df.down30.mean()), 2)}
    B = rng.integers(0, len(sums), size=(1000, len(sums)))
    for k, num, den, mult in (("disapproving", "dis", "n", 100), ("downvoted", "down", "n", 100), ("reception", "recep", "n_recep", 1), ("downvoted30", "down30", "n_down30", 100)):
        bs = sums[num].values[B].sum(1) / sums[den].values[B].sum(1) * mult; out[f"{k}_ci95"] = [round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)]
    return out, sums


res = {}
for name, m in SETS.items():
    a, sa = stats(D[m & ~D.post]); b, sb = stats(D[m & D.post])
    # interval of the change: bootstrap threads within each period independently
    Ba = rng.integers(0, len(sa), size=(1000, len(sa))); Bb = rng.integers(0, len(sb), size=(1000, len(sb)))
    ch = {}
    for k, col, den, mult in (("disapproving", "dis", "n", 100), ("downvoted", "down", "n", 100), ("reception", "recep", "n_recep", 1), ("downvoted30", "down30", "n_down30", 100)):
        da = sa[col].values[Ba].sum(1) / sa[den].values[Ba].sum(1); db = sb[col].values[Bb].sum(1) / sb[den].values[Bb].sum(1)
        d = (db - da) * mult; ch[k] = {"change_pts": round(float(b[f"{k}_pct"] - a[f"{k}_pct"]), 2), "ci95": [round(float(np.percentile(d, 2.5)), 2), round(float(np.percentile(d, 97.5)), 2)]}
    res[name] = {"before 2024": a, "from 2024": b, "change": ch}
# across topics: change vs network position (topics with >= 100 documents in each period)
T = D.groupby(["topic", "post"]).agg(dis=("dis", "mean"), down=("down", "mean"), n=("dis", "size")).unstack()
T = T[(T[("n", False)] >= 100) & (T[("n", True)] >= 100)]
T["d_dis"] = (T[("dis", True)] - T[("dis", False)]) * 100; T["d_down"] = (T[("down", True)] - T[("down", False)]) * 100
cent = json.loads((P / "topic_network_centrality.json").read_text())
deg = {n["topic"]: n["degree_all"] for n in NET["nodes"]}
part = {}
import networkx as nx  # noqa: E402
Gx = nx.Graph(); Gx.add_nodes_from(nodes); Gx.add_edges_from((e["a"], e["b"]) for e in NET["edges_all"])
for v in Gx:
    k = Gx.degree(v); part[v] = 0.0 if k == 0 else 1 - sum((sum(1 for u in Gx[v] if nodes[u]["community"] == c) / k) ** 2 for c in {nodes[u]["community"] for u in Gx[v]})
T["degree"] = [deg[int(t)] for t in T.index]; T["participation"] = [part[int(t)] for t in T.index]
res["across_topics"] = {"topics": int(len(T)), **{f"spearman_{a}_vs_{b}": round(float(spearmanr(T[a], T[b]).statistic), 2) for a in ("d_dis", "d_down") for b in ("degree", "participation")},
                        "spearman_d_dis_vs_d_down": round(float(spearmanr(T.d_dis, T.d_down).statistic), 2)}
(P / "topic_network_tone.json").write_text(json.dumps(res, indent=1))
print("\nRECEPTION (within-thread score percentile, 50 = typical) and DOWNVOTED among comments >= 30 days old")
for name in SETS:
    r = res[name]; a, b, c = r["before 2024"], r["from 2024"], r["change"]
    print(f"{name[:52]:52s} reception {a['reception_pct']:5.1f} -> {b['reception_pct']:5.1f} ({c['reception']['change_pts']:+.1f} [{c['reception']['ci95'][0]:+.1f}, {c['reception']['ci95'][1]:+.1f}])   "
          f"down30 {a['downvoted30_pct']:5.1f} -> {b['downvoted30_pct']:5.1f} ({c['downvoted30']['change_pts']:+.1f} [{c['downvoted30']['ci95'][0]:+.1f}, {c['downvoted30']['ci95'][1]:+.1f}])")
print(f"\n{'group':52s} {'disapproving % before -> from (change [95%])':48s} {'downvoted % before -> from (change [95%])'}")
for name in SETS:
    r = res[name]; a, b, c = r["before 2024"], r["from 2024"], r["change"]
    print(f"{name[:52]:52s} {a['disapproving_pct']:5.1f} -> {b['disapproving_pct']:5.1f} ({c['disapproving']['change_pts']:+.1f} [{c['disapproving']['ci95'][0]:+.1f}, {c['disapproving']['ci95'][1]:+.1f}])     "
          f"{a['downvoted_pct']:5.1f} -> {b['downvoted_pct']:5.1f} ({c['downvoted']['change_pts']:+.1f} [{c['downvoted']['ci95'][0]:+.1f}, {c['downvoted']['ci95'][1]:+.1f}])")
print("across topics:", res["across_topics"])
