"""Why did the relative comment score (within-thread percentile) dip after 2024, in both subreddits? Tests: (1) mechanical effect of bigger threads, (2) length premium, (3) top-level vs reply, (4) stratified by thread size, (5) old vs new commenters.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/reception_why.py"""
from seedoil_common import is_bot, not_bot, SPLIT_TS# shared bot rule: AutoModerator + names ending in 'bot'
import gzip, json
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[2]; RAWD = ROOT / "seedoils" / "data" / "raw"; CUT = SPLIT_TS
def load(pat):
    f = next(RAWD.glob(pat)); rows = []
    with gzip.open(f, "rt", encoding="utf-8") as fh:
        for line in fh:
            x = json.loads(line); rows.append((x["id"], x["link_id"], str(x.get("parent_id", "")).startswith("t3_"), int(x["created_utc"]), x.get("score"), len((x.get("body") or "").split()), x.get("author")))
    C = pd.DataFrame(rows, columns=["id", "link_id", "top", "t", "score", "words", "author"]).dropna(subset=["score"])
    C = C[not_bot(C.author)]; first = C.groupby("author").t.min()
    g = C.groupby(["link_id", "top"]).score; C["n"] = g.transform("size"); C = C[C.n >= 5].copy(); C["pct"] = g.rank(method="average", pct=True).loc[C.index]
    C["post"] = C.t >= CUT; C["expected"] = (C.n + 1) / (2 * C.n); C["long"] = C.words >= 15; C["new"] = C.author.map(first) >= CUT
    return C
def d(X, col="pct"): return X[X.post][col].mean() - X[~X.post][col].mean()
for sub, pat in (("r/StopEatingSeedOils", "*StopEatingSeedOils_comments.jsonl.gz"), ("r/ScientificNutrition", "*ScientificNutrition_comments.jsonl.gz")):
    C = load(pat); print("\n=====", sub, "n", len(C))
    print(f"all comments: pct pre {C[~C.post].pct.mean():.3f} post {C[C.post].pct.mean():.3f} change {d(C):+.3f} | mechanical expectation (n+1)/2n pre {C[~C.post].expected.mean():.3f} post {C[C.post].expected.mean():.3f} change {d(C,'expected'):+.3f} | median group size {C[~C.post].n.median():.0f} -> {C[C.post].n.median():.0f}")
    L = C[C.long]; S = C[~C.long]
    print(f">=15 words: {L[~L.post].pct.mean():.3f} -> {L[L.post].pct.mean():.3f} ({d(L):+.3f}; mechanical {d(L,'expected'):+.3f}) | <15 words: {S[~S.post].pct.mean():.3f} -> {S[S.post].pct.mean():.3f} ({d(S):+.3f}; mechanical {d(S,'expected'):+.3f})")
    print(f"length premium (long minus short pct): pre {L[~L.post].pct.mean()-S[~S.post].pct.mean():.3f} post {L[L.post].pct.mean()-S[S.post].pct.mean():.3f}")
    L = L.assign(resid=L.pct - L.expected); print(f">=15 words after removing the mechanical part (pct - expected): pre {L[~L.post].resid.mean():+.3f} post {L[L.post].resid.mean():+.3f} change {d(L,'resid'):+.3f}")
    for k, lab in ((True, "top-level"), (False, "replies")):
        X = L[L.top == k]; print(f"  {lab:<9} >=15 words: {X[~X.post].pct.mean():.3f} -> {X[X.post].pct.mean():.3f} ({d(X):+.3f})")
    for lo, hi in ((5, 9), (10, 19), (20, 49), (50, 10**6)):
        X = L[(L.n >= lo) & (L.n <= hi)]
        if X.post.any() and (~X.post).any(): print(f"  thread-group size {lo}-{hi if hi<10**6 else '+'}: {X[~X.post].pct.mean():.3f} -> {X[X.post].pct.mean():.3f} ({d(X):+.3f}) n={len(X)}")
    A = L[(~L.author.isin(["[deleted]", "AutoModerator"]) & not_bot(L.author))]; o, nw = A[~A.new], A[A.new]
    print(f"  old commenters >=15 words: pre {o[~o.post].pct.mean():.3f} post {o[o.post].pct.mean():.3f} | new commenters from 2024: {nw[nw.post].pct.mean():.3f}")
