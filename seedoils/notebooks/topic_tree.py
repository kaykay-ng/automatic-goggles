"""Topic tree for the rebuilt r/StopEatingSeedOils BERTopic (processed_rebuild; same 123 topics as the teammate's model): broader groups that cover ALL 123 topics.
Method: each topic is represented by the mean of its documents' sentence embeddings (all-MiniLM-L6-v2, unit length); Ward hierarchical clustering of the 123 topic centroids (scipy), which is the same idea as BERTopic's hierarchical_topics (that uses c-TF-IDF; centroids used here because the fitted model object was not saved). The tree is cut into K groups.
Each group is described by its three largest topics and their first words; shares of all documents before 2024 and from 2024 are per group. Output: seedoils/data/processed/topic_tree_groups_K<K>.csv and topic_tree_topic_to_group_K<K>.csv.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/topic_tree.py [K]"""
import json
import sys

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage

K = int(sys.argv[1]) if len(sys.argv) > 1 else 14
R, P = "seedoils/data/processed_rebuild/", "seedoils/data/processed/"
V = np.load(R + "seso_vectors.npy").astype(np.float32)
D = pd.read_csv(R + "seso_docs.csv.gz", usecols=["id", "created_utc"]); T = pd.read_csv(R + "seso_doc_topics.csv.gz", usecols=["id", "topic"]); D = D.merge(T, on="id")
assert len(D) == len(V)
info = pd.read_csv(R + "seso_topics_info.csv").set_index("topic")
topics = sorted(info.index); C = np.stack([V[(D.topic == t).values].mean(0) for t in topics]); C /= np.linalg.norm(C, axis=1, keepdims=True)
Z = linkage(C, method="ward"); g = fcluster(Z, K, criterion="maxclust"); grp = dict(zip(topics, g))
th = json.load(open(P + "themes_confirmed.json")); theme_of = {int(i): k.split(" (")[0].split(",")[0] for k, v in th.items() for i in v}
D["group"] = D.topic.map(grp); D["pre"] = pd.to_datetime(D.created_utc, unit="s") < "2024-01-01"
rows = []
for gid, s in D.groupby("group"):
    ts = sorted({int(t) for t in s.topic}, key=lambda t: -info.n_docs[t])
    desc = " | ".join(f"{t}: " + ", ".join(info.top_words[t].split(", ")[:3]) for t in ts[:3])
    mix = pd.Series([theme_of.get(t, "(no theme)") for t in ts]).value_counts().to_dict()
    pre, post = s[s.pre], s[~s.pre]
    rows.append({"group": gid, "topics": len(ts), "docs": len(s), "share_pre2024": round(100 * len(pre) / D.pre.sum(), 2), "share_from2024": round(100 * len(post) / (~D.pre).sum(), 2),
                 "ratio": round((len(post) / (~D.pre).sum()) / max(len(pre) / D.pre.sum(), 1e-9), 2), "largest_topics": desc, "theme_topics_inside": mix})
G = pd.DataFrame(rows).sort_values("docs", ascending=False); G.to_csv(P + f"topic_tree_groups_K{K}.csv", index=False)
pd.DataFrame({"topic": topics, "group": [grp[t] for t in topics]}).to_csv(P + f"topic_tree_topic_to_group_K{K}.csv", index=False)
pd.set_option("display.width", 300, "display.max_colwidth", 130)
print(G[["group", "topics", "docs", "share_pre2024", "share_from2024", "ratio", "largest_topics"]].to_string(index=False))
print("\nwhere the nine themes sit (theme topics inside each group):")
for _, r in G.iterrows(): print(f"  group {r.group}: {r.theme_topics_inside}")
