"""Does the change in emotion follow the change in topics? Midpoint decomposition (as emotion_by_theme_decomposition.py, but over the 123 BERTopic topics from BERTopic's own reduce_outliers at 0.05, plus 'no topic' as a group) of the change in the share of ALL documents with a negative / positive / ambiguous GoEmotions group, before 2024 -> from August 2024.
change = within (the rate of the emotion changed inside the same topics) + mix (the topics' sizes changed: more documents in topics with a higher or lower emotion rate). Thread-resampled 95% intervals (1,000 draws) for the totals. Also: the correlation over the 19 quarters between the negative share and the combined share of the five political topics (47, 89, 93, 97, 98).
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/emotion_by_topic_decomposition.py"""
import gzip, json
import numpy as np, pandas as pd
R, Rp, P = "seedoils/data/processed_rebuild/", "seedoils/data/processed_rebuild_prob/", "seedoils/data/processed/"
labs = list(pd.read_csv(P + "goemo_monthly.csv", nrows=1).columns[1:29]); g = np.load(R + "goemo_seso.npz", allow_pickle=True); pr = g["p"].astype(np.float32); ids = g["id"]
G = {"negative": "anger annoyance disappointment disapproval disgust embarrassment fear grief nervousness remorse sadness".split(), "positive": "admiration amusement approval caring desire excitement gratitude joy love optimism pride relief".split(), "ambiguous": "confusion curiosity realization surprise".split()}
A = pd.read_csv(Rp + "seso_doc_topics_official005.csv.gz").set_index("id").loc[ids].reset_index(); A["t"] = pd.to_datetime(A.created_utc, unit="s")
L = {}
for x in map(json.loads, gzip.open("seedoils/data/raw_haoyu/StopEatingSeedOils_comments.jsonl.gz", "rt")): L[x["id"]] = x["link_id"][3:]
A["thread"] = A.id.map(lambda i: L.get(i, i)); A["grp"] = A.topic.where(A.topic >= 0, -1)
keep = ((A.t < "2024-01-01") | (A.t >= "2024-08-01")).values; A2 = A[keep].reset_index(drop=True); pre = (A2.t < "2024-01-01").values; pr2 = pr[keep]
names = sorted(A2.grp.unique()); K = len(names); th = A2.grp.map({n: i for i, n in enumerate(names)}).values; tix = A2.thread.astype("category").cat.codes.values; nT = tix.max() + 1
def agg(flag, sel): n = np.zeros((K, nT)); f = np.zeros((K, nT)); np.add.at(n, (th[sel], tix[sel]), 1); np.add.at(f, (th[sel], tix[sel]), flag[sel]); return n, f
def decomp(npre, fpre, npost, fpost):
    Npre, Npost = npre.sum(), npost.sum(); wpre, wpost = npre.sum(1) / Npre, npost.sum(1) / Npost; rpre = fpre.sum(1) / np.maximum(npre.sum(1), 1); rpost = fpost.sum(1) / np.maximum(npost.sum(1), 1)
    Rbar = 0.5 * (fpre.sum() / Npre + fpost.sum() / Npost); return 100 * 0.5 * (wpre + wpost) * (rpost - rpre), 100 * (wpost - wpre) * (0.5 * (rpre + rpost) - Rbar)
rng = np.random.default_rng(0); info = pd.read_csv(Rp + "seso_topics_info.csv").set_index("topic")
for grp, ls in G.items():
    flag = (pr2[:, [labs.index(l) for l in ls]] >= 0.5).any(1).astype(float); (npre, fpre), (npost, fpost) = agg(flag, pre), agg(flag, ~pre); w, m = decomp(npre, fpre, npost, fpost)
    bs = np.array([[x.sum() for x in decomp(npre[:, p], fpre[:, p], npost[:, p], fpost[:, p])] for p in (rng.integers(0, nT, nT) for _ in range(1000))])
    ci = lambda v: f"[{np.percentile(v, 2.5):+.2f}, {np.percentile(v, 97.5):+.2f}]"
    print(f"{grp:<9} change {w.sum() + m.sum():+.2f} = within {w.sum():+.2f} {ci(bs[:, 0])} + mix {m.sum():+.2f} {ci(bs[:, 1])}   (total {ci(bs.sum(1))})")
    if grp == "negative":
        D = pd.DataFrame({"topic": names, "within": w, "mix": m}); D["total"] = D.within + D.mix; D["words"] = D.topic.map(lambda t: "no confident topic" if t == -1 else ", ".join(info.top_words[t].split(", ")[:3]))
        print(D.reindex(D.total.abs().sort_values(ascending=False).index).head(8).round(2).to_string(index=False))
# correlation over quarters
A["q"] = A.t.dt.to_period("Q").dt.to_timestamp(); qs = A.groupby("q").size(); qk = qs[(qs.index >= "2022-01-01") & (qs.index < "2026-10-01")].index
neg = pd.Series((pr[:, [labs.index(l) for l in G["negative"]]] >= 0.5).any(1)).groupby(A.q.values).mean().reindex(qk) * 100
pol = pd.Series(A.topic.isin([47, 89, 93, 97, 98]).values).groupby(A.q.values).mean().reindex(qk) * 100
from scipy import stats
r, p = stats.pearsonr(neg, pol); rs, ps = stats.spearmanr(neg, pol); print(f"\nquarterly negative share vs political-topic share (19 quarters): Pearson r {r:+.2f} (p {p:.2f}), Spearman {rs:+.2f} (p {ps:.2f})")
print("political share by quarter:", pol.round(2).tolist()); print("negative share by quarter:", neg.round(1).tolist())
