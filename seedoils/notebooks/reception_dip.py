"""Is the small fall in 'reception' (mean within-thread percentile of a comment's score) after 2024 specific to some themes, or general? Same percentile as seso_topics.votes(); thread-cluster bootstrap (300) for intervals.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/reception_dip.py"""
from seedoil_common import is_bot, not_bot, SPLIT_TS# shared bot rule: AutoModerator + names ending in 'bot'
import gzip, json
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[2]; PROC = ROOT / "seedoils" / "data" / "processed"; RAW = next((ROOT / "seedoils" / "data" / "raw").glob("*StopEatingSeedOils_comments.jsonl.gz"))
CUT = SPLIT_TS; rng = np.random.default_rng(0)
rows = []
with gzip.open(RAW, "rt", encoding="utf-8") as f:
    for line in f:
        x = json.loads(line)
        if is_bot(x.get("author")): continue
        rows.append((x["id"], x["link_id"], str(x.get("parent_id", "")).startswith("t3_"), int(x["created_utc"]), x.get("score"), len((x.get("body") or "").split())))
C = pd.DataFrame(rows, columns=["id", "link_id", "top_level", "created_utc", "score", "words"]).dropna(subset=["score"])
g = C.groupby(["link_id", "top_level"]).score; C["n_in_group"] = g.transform("size"); C = C[C.n_in_group >= 5].copy(); C["vote_pct"] = g.rank(method="average", pct=True).loc[C.index]
C["post"] = C.created_utc >= CUT
T = pd.read_csv(PROC / "seso_doc_topics.csv.gz", usecols=["id", "kind", "topic"]); T = T[T.kind == "comment"]
TH = {"Politics": [46, 117, 43, 68, 107], "Pharma, FDA, corporations": [10, 50, 80, 116], "Omega-6 / PUFA": [0, 79, 96], "Studies and evidence": [23, 52, 53], "Ingredient labels": [61, 92, 60], "Shopping": [17, 11, 9], "Vaccines": [20], "Keto": [1, 66]}
M = C.merge(T[["id", "topic"]], on="id", how="left"); M["in_topic"] = M.topic.notna()
def diff(X): return X[X.post].vote_pct.mean() - X[~X.post].vote_pct.mean()
def boot(X, n=300):
    thr = X.groupby("link_id").indices; keys = list(thr); out = []
    for _ in range(n):
        ii = np.concatenate([thr[keys[j]] for j in rng.integers(0, len(keys), len(keys))]); out.append(diff(X.iloc[ii]))
    return np.percentile(out, [2.5, 97.5])
def show(name, X):
    lo, hi = boot(X); print(f"{name:<34} n pre {int((~X.post).sum()):>6} post {int(X.post.sum()):>6}  mean pct pre {X[~X.post].vote_pct.mean():.3f} post {X[X.post].vote_pct.mean():.3f}  change {diff(X):+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]")
show("ALL scored comments (any length)", M)
show("  of which >= 15 words (topic corpus)", M[M.in_topic]); show("  of which < 15 words", M[~M.in_topic])
for n, ts in TH.items(): show("theme: " + n, M[M.topic.isin(ts)])
print("comments per thread-level group, median pre/post:", C[~C.post].n_in_group.median(), C[C.post].n_in_group.median())
print("share of scores equal to 1 (ties) pre/post:", round((C[~C.post].score == 1).mean(), 3), round((C[C.post].score == 1).mean(), 3))
