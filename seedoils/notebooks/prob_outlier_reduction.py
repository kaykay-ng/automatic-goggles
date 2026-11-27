"""Outlier reduction as BERTopic's documentation describes it: an outlier (topic -1 from HDBSCAN) is moved to its highest-probability topic only if that probability reaches a THRESHOLD ('probabilities' strategy of reduce_outliers); outliers below the threshold stay UNASSIGNED and are left out of the themes.
Documents HDBSCAN placed in a cluster keep their topic. The docs' own example threshold is 0.05; 0.02 and 0.10 are shown as sensitivity. Probabilities: seso_probs.npz (refit with calculate_probabilities=True; topics identical to the earlier fit).
Per threshold: share of documents assigned, per theme (themes_full.json) the number of documents, growth ratio (share of assigned documents from 2024 vs before) and negative-group share (GoEmotions, any negative emotion >= 0.5). Output seedoils/data/processed/prob_outlier_reduction.csv.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/prob_outlier_reduction.py"""
import json
import numpy as np
import pandas as pd

R, P, Q = "seedoils/data/processed_rebuild_prob/", "seedoils/data/processed/", "seedoils/data/processed_rebuild/"
z = np.load(R + "seso_probs.npz", allow_pickle=True); pr = z["p"].astype(np.float32); ids = z["id"]
T = pd.read_csv(R + "seso_doc_topics.csv.gz"); assert (T.id.values == ids).all()
T["maxp"] = pr.max(1); T["arg"] = pr.argmax(1); T["pre"] = pd.to_datetime(T.created_utc, unit="s") < "2024-01-01"
g = np.load(Q + "goemo_seso.npz", allow_pickle=True); labs = list(pd.read_csv(P + "goemo_monthly.csv", nrows=1).columns[1:29]); Pm = g["p"].astype(float)
neg = "anger annoyance disappointment disapproval disgust embarrassment fear grief nervousness remorse sadness".split()
E = pd.DataFrame({"id": g["id"], "neg": (Pm[:, [labs.index(l) for l in neg]] >= 0.5).any(1)}); T = T.merge(E, on="id")
th = json.load(open(P + "themes_full.json")); m = {int(i): k for k, v in th.items() for i in v}; names = list(th)
rows = []
for t in (0.02, 0.05, 0.10):
    topic = np.where(T.topic_before_outlier_fix != -1, T.topic_before_outlier_fix, np.where(T.maxp >= t, T.arg, -1)); A = T.assign(tp=topic); A["theme"] = A.tp.map(m); K = A[A.tp != -1]
    out = T.topic_before_outlier_fix == -1
    print(f"\n=== threshold {t}: outliers {out.sum():,}; reassigned {int((out & (T.maxp >= t)).sum()):,}; left unassigned {int((A.tp == -1).sum()):,} ({(A.tp == -1).mean():.1%}); assigned {len(K):,} ({len(K) / len(A):.1%}); assigned before 2024 {K.pre.mean() * 0 + len(K[K.pre]) / A.pre.sum():.1%} / from 2024 {len(K[~K.pre]) / (~A.pre).sum():.1%}")
    for k in names:
        a, b = K[(K.theme == k) & K.pre], K[(K.theme == k) & ~K.pre]; allk = A_all = None
        rows.append({"threshold": t, "theme": k, "docs": len(a) + len(b), "share_before": 100 * len(a) / K.pre.sum(), "share_from24": 100 * len(b) / (~K.pre).sum(), "ratio": (len(b) / (~K.pre).sum()) / (len(a) / K.pre.sum()), "negative_%": 100 * K[K.theme == k].neg.mean()})
D = pd.DataFrame(rows).round(2); D.to_csv(P + "prob_outlier_reduction.csv", index=False)
base = {k: (len(T[(T.topic.map(m) == k) & ~T.pre]) / (~T.pre).sum()) / (len(T[(T.topic.map(m) == k) & T.pre]) / T.pre.sum()) for k in names}
pv = D.pivot(index="theme", columns="threshold", values="ratio").reindex(names); pv.insert(0, "all docs (nearest-topic)", [round(base[k], 2) for k in names]); pd.set_option("display.width", 250)
print("\ngrowth ratio (from 2024 vs before) by theme:"); print(pv.rename(index=lambda s: s[:44]).to_string())
dv = D.pivot(index="theme", columns="threshold", values="docs").reindex(names); print("\ndocuments kept per theme:"); print(dv.rename(index=lambda s: s[:44]).to_string())
