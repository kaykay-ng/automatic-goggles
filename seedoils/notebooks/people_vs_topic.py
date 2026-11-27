"""Did hostility and downvotes rise in r/StopEatingSeedOils because of WHO is commenting (newcomers), because OLD commenters changed, or because the TOPICS changed?
Population: the 2,618 commenters of the ~130-topic network (>= 10 topic-model comments), their topic-model comments (>= 15 words). Cohort: long-time = first comment before 2024-01-01; newcomer = first comment from then on.
Outcomes per comment: hostile (GoEmotions anger/annoyance/disapproval/disgust max >= 0.5) and downvoted (score <= 0), as on the page. Topic = the model's ~130 topics (rare ones, < 200 comments in all, pooled as 'other').
(1) How much of the variation sits in the topic, the person, the period (R^2 of linear models with topic dummies, person dummies, both).
(2) Decomposition of the change pre-2024 -> from-2024 (percentage points):  total = old guard's own change + newcomers' contribution, each split into topic mix and within-topic parts
    (standardising on the other group's topic mix).
(3) Same people over time: long-time commenters with >= 5 comments in both periods, paired change in their own share.
Intervals: bootstrap over people (300 resamples). Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python seedoils/notebooks/people_vs_topic.py   (aggregates only)"""
from seedoil_common import is_bot, not_bot, SPLIT_TS# shared bot rule: AutoModerator + names ending in 'bot'
import glob
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.sparse.linalg import lsqr

P = Path("seedoils/data/processed"); CUT = SPLIT_TS; rng = np.random.default_rng(0)
raw = {}
with gzip.open(glob.glob("seedoils/data/raw/*StopEatingSeedOils_comments.jsonl.gz")[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); raw[x["id"]] = (x["author"], int(x["created_utc"]), x.get("score"))
first = pd.DataFrame([(a, t) for a, t, _ in raw.values()], columns=["a", "t"]).groupby("a").t.min()
D = pd.read_csv(P / "seso_doc_topics.csv.gz"); D = D[D.kind == "comment"].copy(); D["a"] = D.id.map(lambda i: raw.get(i, (None,))[0])
D = D[D.a.notna() & (~D.a.isin(["[deleted]", "AutoModerator"]) & not_bot(D.a))]; nd = D.groupby("a").size(); U = set(nd[nd >= 10].index); D = D[D.a.isin(U)].copy()
LABS = list(pd.read_csv(P / "goemo_monthly.csv", nrows=1).columns[1:29]); HOST = ["anger", "annoyance", "disapproval", "disgust"]
docs = pd.read_csv(P / "seso_docs.csv.gz", usecols=["id"], keep_default_na=False); z = np.load(P / "goemo_seso.npz", allow_pickle=True); assert (z["id"].astype(str) == docs.id.astype(str).values).all()
hostile = pd.Series((pd.DataFrame(z["p"].astype(np.float32), columns=LABS)[HOST].max(axis=1) >= .5).values, index=docs.id.astype(str).values)
D["host"] = D.id.map(hostile).astype(float); D["down"] = (D.id.map(lambda i: raw[i][2]).astype(float) <= 0).astype(float); D = D.dropna(subset=["host"])
D["post"] = (D.created_utc >= CUT).astype(int); D["new"] = (D.a.map(first) >= CUT).astype(int)
tc = D.topic.value_counts(); D["tp"] = np.where(D.topic.map(tc) >= 200, D.topic, -1)
print(f"comments {len(D):,}; people {D.a.nunique():,}; topics kept {D.tp.nunique() - 1} + other; pre {int((D.post == 0).sum()):,}, from 2024 {int((D.post == 1).sum()):,} (newcomers {int(((D.post == 1) & (D.new == 1)).sum()):,}); newcomers' share of 2024+ comments {D[D.post == 1].new.mean():.0%}")

def r2(y, cols):
    X = sp.hstack([sp.csr_matrix(c) for c in cols]).tocsr(); X = sp.hstack([sp.csr_matrix(np.ones((len(y), 1))), X]).tocsr()
    b = lsqr(X, y, atol=1e-8, btol=1e-8, iter_lim=2000)[0]; res = y - X @ b; k = X.shape[1]; n = len(y)
    r = 1 - res.var() / y.var(); return r, 1 - (1 - r) * (n - 1) / (n - k)
dum = lambda s: sp.csr_matrix((np.ones(len(s)), (np.arange(len(s)), pd.factorize(s)[0])))
print("\n(1) share of variation explained (R^2 / adjusted R^2), linear models")
for k, nm in (("host", "hostile"), ("down", "downvoted")):
    y = D[k].values; T, A, Pd = dum(D.tp), dum(D.a), dum(D.post)
    print(f"  {nm}: period only {r2(y, [Pd])[0]:.4f} | topic {r2(y, [T])[0]:.4f} / {r2(y, [T])[1]:.4f} | person {r2(y, [A])[0]:.4f} / {r2(y, [A])[1]:.4f} | topic + person {r2(y, [T, A])[0]:.4f} / {r2(y, [T, A])[1]:.4f} | topic + person + period {r2(y, [T, A, Pd])[0]:.4f} / {r2(y, [T, A, Pd])[1]:.4f}")

def decomp(d, k):
    pre, post = d[d.post == 0], d[d.post == 1]; L, N = post[post.new == 0], post[post.new == 1]
    w = lambda x: x.groupby("tp").size() / len(x); rate = lambda x: x.groupby("tp")[k].mean()
    wpre, wL, wN = w(pre), w(L), w(N); rpre, rL, rN = rate(pre), rate(L), rate(N)
    std = lambda wt, r: float((wt.reindex(r.index).fillna(0) * r).sum() / wt.reindex(r.index).fillna(0).sum())
    r_pre = pre[k].mean() * 100; r_L = L[k].mean() * 100; r_N = N[k].mean() * 100; s = len(N) / len(post)
    L_std = std(wpre, rL) * 100; N_onL = std(wL, rN) * 100
    return {"pre": r_pre, "post_all": post[k].mean() * 100, "old_guard_post": r_L, "newcomers_post": r_N, "newcomer_share": s,
            "total_change": post[k].mean() * 100 - r_pre, "old_within": L_std - r_pre, "old_mix": r_L - L_std, "newcomer_contrib": s * (r_N - r_L),
            "new_within": s * (N_onL - r_L) * -1 + s * 0, "new_mix": s * (r_N - N_onL)}

def show(d, k, nm):
    c = decomp(d, k)
    print(f"  {nm}: before {c['pre']:.2f}% -> from 2024 {c['post_all']:.2f}% (change {c['total_change']:+.2f} pts); old guard {c['old_guard_post']:.2f}%, newcomers {c['newcomers_post']:.2f}% ({c['newcomer_share']:.0%} of comments)")
    return c
print("\n(2) decomposition of the change (percentage points)")
res = {}
for k, nm in (("host", "hostile"), ("down", "downvoted")):
    c = show(D, k, nm); res[k] = c
    boots = {key: [] for key in ("old_within", "old_mix", "newcomer_contrib", "total_change", "new_mix")}
    people = D.a.unique(); grp = {a: g for a, g in D.groupby("a")}
    for _ in range(300):
        s_ = rng.choice(people, len(people)); d = pd.concat([grp[a] for a in s_]); b = decomp(d, k)
        for key in boots: boots[key].append(b[key])
    ci = lambda key: f"[{np.percentile(boots[key], 2.5):+.2f}, {np.percentile(boots[key], 97.5):+.2f}]"
    print(f"     total change {c['total_change']:+.2f} {ci('total_change')}")
    print(f"       old guard, same topics (rate change within topic): {c['old_within']:+.2f} {ci('old_within')}")
    print(f"       old guard, topic mix shift:                        {c['old_mix']:+.2f} {ci('old_mix')}")
    print(f"       newcomers' contribution (share x gap to old guard): {c['newcomer_contrib']:+.2f} {ci('newcomer_contrib')}")
    print(f"          of which: they talk about different topics:       {c['new_mix']:+.2f} {ci('new_mix')}")

print("\n(3) the same people over time: long-time commenters with >= 5 comments before and >= 5 from 2024")
g = D[D.new == 0].groupby(["a", "post"])[["host", "down"]].agg(["mean", "size"]).unstack("post")
for k, nm in (("host", "hostile"), ("down", "downvoted")):
    ok = (g[(k, "size", 0)] >= 5) & (g[(k, "size", 1)] >= 5); pre = g[(k, "mean", 0)][ok]; post = g[(k, "mean", 1)][ok]; dd = (post - pre) * 100
    bs = [rng.choice(dd.values, len(dd)).mean() for _ in range(1000)]
    print(f"  {nm}: {int(ok.sum())} people; their own share {pre.mean() * 100:.2f}% -> {post.mean() * 100:.2f}% (mean paired change {dd.mean():+.2f} pts, 95% interval [{np.percentile(bs, 2.5):+.2f}, {np.percentile(bs, 97.5):+.2f}])")
