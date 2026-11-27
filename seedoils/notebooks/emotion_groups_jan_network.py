"""GoEmotions groups before vs from 2024 (1 January split, as in the rest of the paper), overall, per emotion, and on the topic network
(27 Nov; replaces the before-2024 vs from-Aug-2024 comparison, which left out January-July 2024). Definitions follow Kaykay's emotion work:
a document carries a group when any of its emotions scores >= 0.5 (negative = anger, annoyance, disappointment, disapproval, disgust,
embarrassment, fear, grief, nervousness, remorse, sadness; positive = admiration, amusement, approval, caring, desire, excitement, gratitude,
joy, love, optimism, pride, relief; ambiguous = confusion, curiosity, realization, surprise; neutral = the neutral label >= 0.5); every share
is a share of ALL documents in the group of documents described. Documents: all 149,815 topic-model documents (comments and self-posts of
15+ words). Network: topic -> Louvain community from data/processed/topic_cooccurrence_network.json (the paper's network); the five politics
topics; the topic of a document = its topic in seso_doc_topics.csv.gz (every outlier assigned; NOTE: the paper's network uses the 0.05 rule,
whose per-document file is not in the repository, so the community rows here are provisional). 95% intervals: 1,000 bootstrap resamples of
threads. Output: data/processed/emotion_groups_jan_network.json. Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/emotion_groups_jan_network.py"""
import glob
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from seedoil_common import SPLIT_TS  # noqa: E402

P, RAW = Path("seedoils/data/processed"), Path("seedoils/data/raw")
LAB = list(pd.read_csv(P / "goemo_monthly.csv", nrows=1).columns[1:29])
GR = {"negative": "anger annoyance disappointment disapproval disgust embarrassment fear grief nervousness remorse sadness".split(),
      "positive": "admiration amusement approval caring desire excitement gratitude joy love optimism pride relief".split(),
      "ambiguous": "confusion curiosity realization surprise".split(), "neutral": ["neutral"]}
g = np.load(P / "goemo_seso.npz", allow_pickle=True); pr = g["p"].astype(np.float32) >= 0.5
E = pd.DataFrame(pr, columns=LAB); E["id"] = g["id"].astype(str)
for k, ls in GR.items():
    E[k] = E[ls].any(axis=1)
D = pd.read_csv(P / "seso_doc_topics.csv.gz", usecols=["id", "created_utc", "topic"]); D["id"] = D.id.astype(str); D = D.merge(E, on="id")
link = {}
with gzip.open(glob.glob(str(RAW / "*StopEatingSeedOils_comments.jsonl.gz"))[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); link[x["id"]] = x.get("link_id", "")[3:]
D["thread"] = D.id.map(link).fillna(D.id); D["post"] = D.created_utc >= SPLIT_TS
NET = json.loads((P / "topic_cooccurrence_network.json").read_text()); nodes = {n["topic"]: n for n in NET["nodes"]}
D["comm"] = D.topic.map(lambda t: nodes[int(t)]["community"]); D["pol"] = D.topic.map(lambda t: nodes[int(t)]["theme"] == "Politics")
deg = {n["topic"]: n["degree_all"] for n in NET["nodes"]}; D["linked"] = D.topic.map(lambda t: deg[int(t)] > 0)
rng = np.random.default_rng(0)


def change(df, cols, B=1000):
    out = {}
    for per in (False, True):
        d = df[df.post == per]; th = pd.factorize(d.thread)[0]; S = pd.DataFrame(d[cols].astype(int).values, columns=cols); S["n"] = 1; S["th"] = th; S = S.groupby("th").sum()
        out[per] = (S, d[cols].mean() * 100)
    res = {}
    Ia = rng.integers(0, len(out[False][0]), size=(B, len(out[False][0]))); Ib = rng.integers(0, len(out[True][0]), size=(B, len(out[True][0])))
    for c in cols:
        a, b = out[False][0], out[True][0]
        da = a[c].values[Ia].sum(1) / a["n"].values[Ia].sum(1); db = b[c].values[Ib].sum(1) / b["n"].values[Ib].sum(1); d = (db - da) * 100
        res[c] = {"before_pct": round(float(out[False][1][c]), 2), "from_pct": round(float(out[True][1][c]), 2), "change_pts": round(float(out[True][1][c] - out[False][1][c]), 2),
                  "ci95": [round(float(np.percentile(d, 2.5)), 2), round(float(np.percentile(d, 97.5)), 2)]}
    return res


G4 = list(GR)
res = {"documents": {"before": int((~D.post).sum()), "from": int(D.post.sum())}, "overall_groups": change(D, G4), "overall_emotions": change(D, LAB)}
names = {}
try:
    C = json.loads((P / "topic_network_centrality.json").read_text()); names = {int(k): v for k, v in C["community_names"].items()}
except Exception:
    pass
SETS = {"five politics topics": D.pol, "topics without a network link": ~D.linked}
for c in sorted(D.comm.unique()):
    m = D.comm == c
    if m.sum() > 3000:
        tops = [nodes[t]["words"].split(", ")[0] for t in D[m].topic.value_counts().index[:3]]
        SETS[f"community {c} ({', '.join(tops)})"] = m
res["by_network_part"] = {k: change(D[m], ["negative", "positive", "ambiguous"]) for k, m in SETS.items()}
(P / "emotion_groups_jan_network.json").write_text(json.dumps(res, indent=1))
print(f"documents before 2024 {res['documents']['before']:,}, from 2024 {res['documents']['from']:,}\nGROUPS (share of all documents):")
for k, v in res["overall_groups"].items():
    print(f"  {k:10s} {v['before_pct']:5.2f} -> {v['from_pct']:5.2f}  ({v['change_pts']:+.2f} [{v['ci95'][0]:+.2f}, {v['ci95'][1]:+.2f}])")
em = sorted(res["overall_emotions"].items(), key=lambda kv: -abs(kv[1]["change_pts"]))[:10]
print("LARGEST EMOTION CHANGES:"); [print(f"  {k:14s} {v['before_pct']:5.2f} -> {v['from_pct']:5.2f}  ({v['change_pts']:+.2f} [{v['ci95'][0]:+.2f}, {v['ci95'][1]:+.2f}])") for k, v in em]
print("BY NETWORK PART (negative / positive / ambiguous, share of that part's documents):")
for k, r in res["by_network_part"].items():
    print(f"  {k[:60]:60s} " + "  ".join(f"{g_[:3]} {r[g_]['before_pct']:4.1f}->{r[g_]['from_pct']:4.1f} ({r[g_]['change_pts']:+.1f} [{r[g_]['ci95'][0]:+.1f},{r[g_]['ci95'][1]:+.1f}])" for g_ in ("negative", "positive", "ambiguous")))
