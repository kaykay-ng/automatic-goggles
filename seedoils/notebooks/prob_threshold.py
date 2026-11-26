"""Confidence thresholds from HDBSCAN soft memberships (seso_probs.npz, refit with calculate_probabilities=True; topics identical to the earlier fit).
Confidence of a document = its highest membership over the 123 topics. For each threshold: share of documents kept (overall, before / from 2024), share kept per theme, and each theme's growth ratio (share of kept documents from 2024 vs before) next to the all-documents ratio.
Themes = themes_full.json. Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/prob_threshold.py"""
import json
import numpy as np
import pandas as pd

R, P = "seedoils/data/processed_rebuild_prob/", "seedoils/data/processed/"
z = np.load(R + "seso_probs.npz", allow_pickle=True); pr = z["p"].astype(np.float32); ids = z["id"]
T = pd.read_csv(R + "seso_doc_topics.csv.gz"); assert (T.id.values == ids).all()
T["maxp"] = pr.max(1); T["arg"] = pr.argmax(1); T["pre"] = pd.to_datetime(T.created_utc, unit="s") < "2024-01-01"; T["outlier"] = T.topic_before_outlier_fix == -1
th = json.load(open(P + "themes_full.json")); m = {int(i): k for k, v in th.items() for i in v}; T["theme"] = T.topic.map(m)
print("row sums of the probability matrix: median", round(float(np.median(pr.sum(1))), 2), "| share of rows summing to ~0:", round(float((pr.sum(1) < 1e-6).mean()), 3))
print("max-probability quantiles (10/25/50/75/90%):", np.round(np.quantile(T.maxp, [.1, .25, .5, .75, .9]), 2).tolist())
print("  documents HDBSCAN put in a cluster: median maxp", round(float(T[~T.outlier].maxp.median()), 2), "| reassigned outliers: median maxp", round(float(T[T.outlier].maxp.median()), 2))
print("  argmax of the probabilities equals the cluster topic for", round(float((T[~T.outlier].arg == T[~T.outlier].topic).mean()), 3), "of clustered documents")
names = list(th); base = {k: (len(T[(T.theme == k) & ~T.pre]) / (~T.pre).sum()) / (len(T[(T.theme == k) & T.pre]) / T.pre.sum()) for k in names}
rows = []
for t in (0.0, 0.1, 0.25, 0.5, 0.75):
    K = T[T.maxp > t] if t > 0 else T; r = {"threshold": t, "kept_%": round(100 * len(K) / len(T), 1), "kept_before_%": round(100 * K.pre.sum() / T.pre.sum(), 1), "kept_from24_%": round(100 * (~K.pre).sum() / (~T.pre).sum(), 1)}
    for k in names:
        a, b = K[(K.theme == k) & K.pre], K[(K.theme == k) & ~K.pre]; r[k.split(" (")[0].split(",")[0][:14] + " ratio"] = round((len(b) / max((~K.pre).sum(), 1)) / max(len(a) / max(K.pre.sum(), 1), 1e-9), 2) if len(a) > 20 else np.nan
    rows.append(r)
D = pd.DataFrame(rows); pd.set_option("display.width", 300); print("\n" + D.to_string(index=False)); print("\nall-documents ratios:", {k.split(' (')[0].split(',')[0][:14]: round(v, 2) for k, v in base.items()})
print("\nshare of each theme's documents kept (maxp > threshold):")
print(pd.DataFrame({f"> {t}": (T[T.maxp > t].theme.value_counts() / T.theme.value_counts() * 100).round(0) for t in (0.1, 0.25, 0.5, 0.75)}).to_string())
D.to_csv(P + "prob_threshold_summary.csv", index=False)
