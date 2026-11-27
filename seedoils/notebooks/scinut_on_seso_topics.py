"""Figure 1b's topics in r/ScientificNutrition. The two subreddits were fitted separately, so topic ids differ; to compare the SAME topics, each r/ScientificNutrition comment is given
the r/StopEatingSeedOils topic whose centroid (mean MiniLM embedding of that topic's comments) is nearest by cosine, but only if the similarity is at least the 10th percentile of how
similar r/StopEatingSeedOils comments are to their own topic's centroid; otherwise it is 'no match'. The same rule is applied to r/StopEatingSeedOils so the two columns are comparable.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python seedoils/notebooks/scinut_on_seso_topics.py  -> printed table + data/processed/scinut_on_seso_topics.csv (aggregates only)."""
from seedoil_common import SPLIT_TS  # analysis split: 1 Jan 2024 (decision 26 Nov)
import json
from pathlib import Path

import numpy as np
import pandas as pd

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
SPLIT = SPLIT_TS
G = pd.DataFrame(json.load(open(PROC / "artifact" / "topic_growth.json"))["rows"])
G = G[G.subreddit == "r/StopEatingSeedOils"].dropna(subset=["ratio"]).sort_values("ratio", ascending=False).head(15)
top = G.topic.tolist()
def load(p):
    V = np.load(PROC / f"{p}_vectors.npy").astype(np.float32); V /= np.linalg.norm(V, axis=1, keepdims=True)
    T = pd.read_csv(PROC / f"{p}_doc_topics.csv.gz", usecols=["id", "created_utc", "topic"]); assert len(T) == len(V)
    return V, T
Vs, Ts = load("seso"); Vn, Tn = load("scinut")
ids = sorted(set(Ts.topic)); C = np.stack([Vs[(Ts.topic == t).values].mean(0) for t in ids]); C /= np.linalg.norm(C, axis=1, keepdims=True)
pos = {t: i for i, t in enumerate(ids)}
own = np.einsum("ij,ij->i", Vs, C[Ts.topic.map(pos).values]); thr = np.percentile(own, 10)
print(f"threshold (10th pct of own-centroid similarity in r/StopEatingSeedOils): {thr:.3f}")
def assign(V):
    S = V @ C.T; j = S.argmax(1); ok = S.max(1) >= thr
    return np.where(ok, np.array(ids)[j], -1)
As, An = assign(Vs), assign(Vn)
print(f"r/StopEatingSeedOils: matched {np.mean(As >= 0):.0%}; same topic as the model's own label {np.mean(As == Ts.topic.values):.0%}")
print(f"r/ScientificNutrition: matched {np.mean(An >= 0):.0%}")
def stats(A, T, t):
    post = (T.created_utc >= SPLIT).values; a, b = int(((A == t) & ~post).sum()), int(((A == t) & post).sum())
    sa, sb = 100 * a / (~post).sum(), 100 * b / post.sum()
    return a, b, sa, sb, (sb / sa if a else np.nan)
rows = []
for r in G.itertuples():
    o = (r.n_pre2024, r.n_from2024, r.ratio)
    a1, b1, sa1, sb1, k1 = stats(As, Ts, r.topic); a2, b2, sa2, sb2, k2 = stats(An, Tn, r.topic)
    rows.append({"topic": r.topic, "label": r.label, "seso_ratio_own_labels": o[2], "seso_ratio_centroid": round(k1, 2), "scinut_n_pre": a2, "scinut_n_from": b2,
                 "scinut_share_pre": round(sa2, 3), "scinut_share_from": round(sb2, 3), "scinut_ratio": round(k2, 2) if k2 == k2 else None})
R = pd.DataFrame(rows); R.to_csv(PROC / "scinut_on_seso_topics.csv", index=False)
pd.set_option("display.width", 250); print(R.to_string(index=False))
print("totals r/ScientificNutrition: pre", int((Tn.created_utc < SPLIT).sum()), "from", int((Tn.created_utc >= SPLIT).sum()))
