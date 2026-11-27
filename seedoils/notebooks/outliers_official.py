"""Outlier reduction with BERTopic's OWN function (27 Nov 2026), so that every analysis uses one rule: topic_model.reduce_outliers(docs, topics, strategy="probabilities", probabilities=probs, threshold=0.05).
Inputs: the fitted model (processed_rebuild_model/seso_bertopic_model), HDBSCAN's topics before any reassignment (topic_before_outlier_fix) and the soft-clustering probabilities (processed_rebuild_prob/seso_probs.npz, saved before outliers were touched).
Checks that the result equals the earlier hand-written implementation (seso_doc_topics_prob005_v3.csv.gz, column topic_final). Writes seedoils/data/processed_rebuild_prob/seso_doc_topics_official005.csv.gz (id, created_utc, topic, -1 = left without a topic) for all later analyses, including the networks.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/outliers_official.py [threshold]"""
import sys, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from bertopic import BERTopic
R, M = "seedoils/data/processed_rebuild_prob/", "seedoils/data/processed_rebuild_model/"; thr = float(sys.argv[1]) if len(sys.argv) > 1 else 0.05
T = pd.read_csv(R + "seso_doc_topics.csv.gz"); z = np.load(R + "seso_probs.npz", allow_pickle=True); assert (z["id"].astype(str) == T.id.astype(str).values).all(); probs = z["p"].astype(np.float32)
D = pd.read_csv(R + "seso_docs.csv.gz", usecols=["id", "text"], keep_default_na=False); assert (D.id.astype(str).values == T.id.astype(str).values).all()
m = BERTopic.load(M + "seso_bertopic_model", embedding_model=None)
m.topic_sizes_[-1] = int((T.topic_before_outlier_fix == -1).sum())  # the saved model was updated AFTER the old reassignment, so it has no -1 topic and reduce_outliers refuses ('No outliers to reduce'); we restore HDBSCAN's outlier count, as before the reassignment; the probabilities strategy itself does not use any other model state
new = np.array(m.reduce_outliers(D.text.tolist(), T.topic_before_outlier_fix.tolist(), strategy="probabilities", probabilities=probs, threshold=thr))
out = T.topic_before_outlier_fix.values == -1
print(f"threshold {thr}: outliers {out.sum():,}; moved by BERTopic's reduce_outliers {int((out & (new != -1)).sum()):,}; still without a topic {int((new == -1).sum()):,} ({(new == -1).mean():.1%}); with a topic {int((new != -1).sum()):,} ({(new != -1).mean():.1%})")
if thr == 0.05:
    old = pd.read_csv(R + "seso_doc_topics_prob005_v3.csv.gz"); o = old.topic_final.fillna(-1).astype(int).values
    print("identical to the hand-written 0.05 implementation:", bool((o == new).all()), "| differing documents:", int((o != new).sum()))
pd.DataFrame({"id": T.id, "created_utc": T.created_utc, "topic": new}).to_csv(R + f"seso_doc_topics_official{int(round(thr * 100)):03d}.csv.gz", index=False)
