"""Dataset 'topic_growth' for Figure 1b: every BERTopic topic (the ~130 the model found by itself, outliers reassigned), no hand-made groups, share of comments before / from 2024.
The page ranks them by growth; topics need at least MIN_N comments over both periods to be listed. Label = first words of the topic with repeats removed (mechanical, not hand-written).
Run from final_project/:  python3 seedoils/notebooks/topic_growth_data.py  (needs pandas) -> seedoils/data/processed/artifact/topic_growth.json ({rows, meta}). Aggregates only."""
import json
from pathlib import Path

import pandas as pd

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
OUT = PROC / "artifact" / "topic_growth.json"
SPLIT = 1704067200  # 2024-01-01 UTC
MIN_N = 300


def label(words, n=4):
    keep = []
    for w in (x.strip() for x in words.split(",")):
        if any(w in k or k in w for k in keep):
            continue
        keep.append(w)
        if len(keep) == n:
            break
    return ", ".join(keep)


rows = []
for sub, pfx in (("r/StopEatingSeedOils", "seso"), ("r/ScientificNutrition", "scinut")):
    T = pd.read_csv(PROC / f"{pfx}_doc_topics.csv.gz", usecols=["id", "created_utc", "topic"])
    I = pd.read_csv(PROC / f"{pfx}_topics_info.csv").set_index("topic")
    post = T.created_utc >= SPLIT
    n_pre, n_post = int((~post).sum()), int(post.sum())
    cp, cq = T[~post].topic.value_counts(), T[post].topic.value_counts()
    for t in I.index:
        a, b = int(cp.get(t, 0)), int(cq.get(t, 0))
        if a + b < MIN_N:
            continue
        sa, sb = 100 * a / n_pre, 100 * b / n_post
        rows.append({"subreddit": sub, "topic": int(t), "label": label(I.loc[t, "top_words"]), "words": I.loc[t, "top_words"],
                     "n_pre2024": a, "n_from2024": b, "share_pre2024_pct": round(sa, 3), "share_from2024_pct": round(sb, 3),
                     "ratio": round(sb / sa, 2) if a else None})
meta = [{"label": "Topics", "value": "BERTopic (all-MiniLM-L6-v2, UMAP 5 dims, HDBSCAN min cluster 150, c-TF-IDF, outliers reassigned) on comments and self-posts of at least 15 words; "
                                    f"every topic with at least {MIN_N} comments over both periods; no grouping. Share = comments in the topic / all comments of that period. Labels are the first words of the topic."}]
OUT.write_text(json.dumps({"rows": rows, "meta": meta}, ensure_ascii=False))
print(len(rows), "rows")
