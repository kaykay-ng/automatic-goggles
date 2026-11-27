"""Kaykay's emotion comparison rerun at the paper's 1 January 2024 split (27 Nov; her scripts compare before 2024 with from August 2024 and read
files that are only on her machine). Same definitions: a document has an emotion if its GoEmotions score >= 0.5, a group if any member does;
shares are of ALL 149,815 documents; 95% intervals from resampling threads (2,000 draws for the changes, 1,000 for the decomposition).
1) change per group and per emotion, before vs from 1 Jan 2024 -> data/processed/emotions_change_thread_intervals_jan.csv (read by Figure 3).
2) within/mix midpoint decomposition over topics (as emotion_by_topic_decomposition.py). Her topics use the 0.05 reduce_outliers rule, whose
   per-document file (when present, 'official005') was first not here, so it is also run with two versions that bracket it: 'hdbscan' (topic_before_outlier_fix; unplaced = one 'no topic' group) and
   'all' (every outlier assigned). 3) angry documents from 2024 in the five political topics.
Output: data/processed/emotion_jan_rerun.json. Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/emotion_jan_rerun.py"""
import glob, gzip, json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from seedoil_common import SPLIT_TS  # noqa: E402

P = Path("seedoils/data/processed"); RAW = Path("seedoils/data/raw")
LAB = list(pd.read_csv(P / "goemo_monthly.csv", nrows=1).columns[1:29])
G = {"negative": "anger annoyance disappointment disapproval disgust embarrassment fear grief nervousness remorse sadness".split(),
     "positive": "admiration amusement approval caring desire excitement gratitude joy love optimism pride relief".split(),
     "ambiguous": "confusion curiosity realization surprise".split(), "neutral": ["neutral"]}
POL = [47, 89, 93, 97, 98]
g = np.load(P / "goemo_seso.npz", allow_pickle=True); F = pd.DataFrame(g["p"].astype(np.float32) >= 0.5, columns=LAB); F["id"] = g["id"].astype(str)
for k, ls in G.items(): F[k] = F[ls].any(axis=1)
D = pd.read_csv(P / "seso_doc_topics.csv.gz"); D["id"] = D.id.astype(str); D = D.merge(F, on="id"); assert len(D) == len(F)
OFF = P / "seso_doc_topics_official005.csv.gz"  # Kaykay's 0.05 rule (the paper's topics); copied in 27 Nov
if OFF.exists():
    O = pd.read_csv(OFF, usecols=["id", "topic"]).rename(columns={"topic": "topic_005"}); O["id"] = O.id.astype(str); D = D.merge(O, on="id", how="left"); assert D.topic_005.notna().all()
link = {}
with gzip.open(glob.glob(str(RAW / "*StopEatingSeedOils_comments.jsonl.gz"))[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); link[x["id"]] = x.get("link_id", "")[3:]
D["thread"] = D.id.map(link).fillna(D.id); post = (D.created_utc >= SPLIT_TS).values
tix = pd.factorize(D.thread)[0]; nT = tix.max() + 1; rng = np.random.default_rng(0)

# 1) changes, thread bootstrap (threads resampled within each period, as in emotion_groups_jan_network.py)
cols = list(G) + [l for l in LAB if l != "neutral"]; rows = []
S = {}
for per in (False, True):
    m = post == per; t = pd.factorize(D.thread[m])[0]; X = D.loc[m, cols].astype(int).values
    s = np.zeros((t.max() + 1, len(cols))); np.add.at(s, t, X); nn = np.bincount(t).astype(float); S[per] = (s, nn, X.mean(0) * 100)
I = {per: rng.integers(0, len(S[per][1]), size=(2000, len(S[per][1]))) for per in S}
for j, c in enumerate(cols):
    a = S[False][0][:, j][I[False]].sum(1) / S[False][1][I[False]].sum(1); b = S[True][0][:, j][I[True]].sum(1) / S[True][1][I[True]].sum(1); d = (b - a) * 100
    rows.append({"measure": c, "before": round(S[False][2][j], 2), "from": round(S[True][2][j], 2), "change": round(S[True][2][j] - S[False][2][j], 2),
                 "lo95": round(np.percentile(d, 2.5), 2), "hi95": round(np.percentile(d, 97.5), 2)})
CH = pd.DataFrame(rows); CH.to_csv(P / "emotions_change_thread_intervals_jan.csv", index=False)
out = {"documents": {"before": int((~post).sum()), "from": int(post.sum())}, "no_emotion_pct": round(100 * float((~D[[l for l in LAB if l != "neutral"]].any(axis=1)).mean()), 1),
       "changes": CH.set_index("measure").to_dict("index")}

# 2) decomposition
def decomp(npre, fpre, npost, fpost):
    Npre, Npost = npre.sum(), npost.sum(); wpre, wpost = npre.sum(1) / Npre, npost.sum(1) / Npost
    rpre = fpre.sum(1) / np.maximum(npre.sum(1), 1); rpost = fpost.sum(1) / np.maximum(npost.sum(1), 1); Rbar = 0.5 * (fpre.sum() / Npre + fpost.sum() / Npost)
    return 100 * 0.5 * (wpre + wpost) * (rpost - rpre), 100 * (wpost - wpre) * (0.5 * (rpre + rpost) - Rbar)
out["decomposition"] = {}
for ver, col in ((("official005", "topic_005"),) if "topic_005" in D else ()) + (("hdbscan", "topic_before_outlier_fix"), ("all", "topic")):
    grp = D[col].where(D[col] >= 0, -1); names = sorted(grp.unique()); th = grp.map({n: i for i, n in enumerate(names)}).values; K = len(names)
    res = {}
    for gname in ("negative", "positive", "ambiguous"):
        fl = D[gname].values.astype(float); M = {}
        for per in (False, True):
            sel = post == per; n = np.zeros((K, nT)); f = np.zeros((K, nT)); np.add.at(n, (th[sel], tix[sel]), 1); np.add.at(f, (th[sel], tix[sel]), fl[sel]); M[per] = (n, f)
        w, m = decomp(*M[False], *M[True])
        bs = np.array([[x.sum() for x in decomp(M[False][0][:, p], M[False][1][:, p], M[True][0][:, p], M[True][1][:, p])] for p in (rng.integers(0, nT, nT) for _ in range(1000))])
        ci = lambda v: [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)]
        res[gname] = {"change": round(float(w.sum() + m.sum()), 2), "within": round(float(w.sum()), 2), "within_ci": ci(bs[:, 0]), "mix": round(float(m.sum()), 2), "mix_ci": ci(bs[:, 1])}
    ang = post & D.anger.values
    res["angry_from2024"] = int(ang.sum()); res["angry_from2024_in_politics"] = int((ang & D[col].isin(POL).values).sum())
    neg = post & D.negative.values; res["negative_from2024_in_politics_pct"] = round(100 * float((neg & D[col].isin(POL).values).sum() / neg.sum()), 1)
    out["decomposition"][ver] = res
(P / "emotion_jan_rerun.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k != "changes"}, indent=1))
print(CH.reindex(CH.change.abs().sort_values(ascending=False).index).head(14).to_string(index=False))
