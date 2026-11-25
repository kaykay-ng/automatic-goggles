"""Did newcomers change the old guard's behaviour? A reply-network test with the GoEmotions labels.
Reply edge: a comment whose parent_id points to another person's comment (both authors real, different). Hostility = GoEmotions anger/annoyance/disapproval/disgust >= 0.5 for EVERY comment (the long and the short scoring files);
downvoted = score <= 0. Cohort: long-time = the author's first comment in the subreddit is before 2024-01-01 (old guard), newcomer = from then on. All replies from 2024-01-01 on.
Linear probability models with two-way fixed effects (replier and thread, by alternating demeaning), standard errors clustered by replier. Coefficients in percentage points.
 A. Old guard's replies: hostile ~ parent is a newcomer + parent is hostile | replier, thread  (same person, same thread: do they answer a newcomer more harshly than an old-guard commenter, and does a hostile parent invite a hostile reply?)
 B. The same for newcomers' replies.
 C. Old guard's hostile share ~ newcomers' share of the thread's commenters | replier, month  (do old-guard people get harsher in threads with more newcomers?)
 D. Downvoted ~ replier is a newcomer + reply is hostile + parent is hostile | thread  (is the newcomer gap in downvotes about content or reception?)
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python seedoils/notebooks/reply_exposure.py   (aggregates only)"""
from seedoil_common import is_bot, not_bot  # shared bot rule: AutoModerator + names ending in 'bot'
import glob
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

P = Path("seedoils/data/processed"); CUT = 1704067200
rows = []
with gzip.open(glob.glob("seedoils/data/raw/*StopEatingSeedOils_comments.jsonl.gz")[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); rows.append((x["id"], x["author"], x["link_id"], x["parent_id"], int(x["created_utc"]), x.get("score")))
R = pd.DataFrame(rows, columns=["id", "a", "thread", "parent", "t", "score"]).set_index("id")
LABS = list(pd.read_csv(P / "goemo_monthly.csv", nrows=1).columns[1:29]); HI = [LABS.index(k) for k in ("anger", "annoyance", "disapproval", "disgust")]
host = {}
for fn in ("goemo_seso.npz",):  # 15+ words only (decision 22 Nov): replies shorter than 15 words have no hostility label and drop out
    z = np.load(P / fn, allow_pickle=True); h = z["p"][:, HI].max(1) >= .5; host.update(zip(z["id"].astype(str), h.astype(float)))
R["host"] = R.index.map(host); print(f"comments {len(R):,}; with a hostility label {R.host.notna().mean():.0%}")
first = R.groupby("a").t.min(); R["new"] = (R.a.map(first) >= CUT).astype(int)
ok = (~R.a.isin(["[deleted]", "AutoModerator"]) & not_bot(R.a))
rep = R[ok & R.parent.str.startswith("t1_") & (R.t >= CUT)].copy(); rep["pid"] = rep.parent.str[3:]
for c in ("a", "host", "new", "score"): rep["p_" + c] = rep.pid.map(R[c])
rep = rep[rep.p_a.notna() & (~rep.p_a.isin(["[deleted]", "AutoModerator"]) & not_bot(rep.p_a)) & (rep.p_a != rep.a) & rep.host.notna() & rep.p_host.notna()].copy()
rep["down"] = (rep.score.astype(float) <= 0).astype(float); rep["month"] = pd.to_datetime(rep.t, unit="s").dt.to_period("M").astype(str)
print(f"replies from 2024 between two real people: {len(rep):,}; by old guard {int((rep.new == 0).sum()):,}, by newcomers {int((rep.new == 1).sum()):,}")
print("raw hostile share of replies by (replier cohort -> parent cohort):")
for rc in (0, 1):
    for pc in (0, 1):
        s = rep[(rep.new == rc) & (rep.p_new == pc)]; print(f"  {'newcomer' if rc else 'old guard'} -> {'newcomer' if pc else 'old guard'}: {s.host.mean() * 100:.2f}% hostile, {s.down.mean() * 100:.1f}% downvoted ({len(s):,})")
print("raw: hostile share of replies to a hostile parent %.2f%% vs a non-hostile parent %.2f%%" % (rep[rep.p_host == 1].host.mean() * 100, rep[rep.p_host == 0].host.mean() * 100))

def demean(d, cols, fes, it=30):
    d = d.copy()
    for _ in range(it):
        for fe in fes:
            d[cols] = d[cols] - d.groupby(fe)[cols].transform("mean")
    return d

def fe_ols(d, y, xs, fes, cluster="a"):
    d = d[list(dict.fromkeys([y] + xs + list(fes) + [cluster]))].dropna().copy(); d = d.rename(columns={y: "_y"}); dm = demean(d, ["_y"] + xs, list(fes))
    X = dm[xs].values; Y = dm["_y"].values; XtX = X.T @ X; b = np.linalg.solve(XtX, X.T @ Y); e = Y - X @ b
    g = pd.DataFrame(X * e[:, None]).groupby(d[cluster].values).sum().values; V = np.linalg.inv(XtX) @ (g.T @ g) @ np.linalg.inv(XtX); se = np.sqrt(np.diag(V))
    return {x: (b[i] * 100, 1.96 * se[i] * 100) for i, x in enumerate(xs)}, len(d)

def show(title, res, n):
    print(f"  {title} (n={n:,})"); [print(f"     {k:<26}{v[0]:+.2f} pts  [{v[0] - v[1]:+.2f}, {v[0] + v[1]:+.2f}]") for k, v in res.items()]
print("\nA. old guard's replies: hostile ~ parent newcomer + parent hostile | replier, thread")
O = rep[rep.new == 0]; show("old guard", *fe_ols(O.assign(p_new=O.p_new.astype(float)), "host", ["p_new", "p_host"], ["a", "thread"]))
print("B. newcomers' replies: same model")
N = rep[rep.new == 1]; show("newcomers", *fe_ols(N.assign(p_new=N.p_new.astype(float)), "host", ["p_new", "p_host"], ["a", "thread"]))
print("C. old guard's hostile share ~ newcomers' share of the thread's commenters | replier, month")
tn = R[ok].groupby("thread").apply(lambda g: g.drop_duplicates("a").new.mean()); ts = R[ok].groupby("thread").a.nunique()
O = O.assign(thread_new=O.thread.map(tn), thread_people=O.thread.map(ts)); O = O[O.thread_people >= 5].copy(); O["thread_new"] = O.thread_new * 100 / 10  # per +10 points of newcomer share
show("old guard, threads of >= 5 people; coefficient per +10 points of newcomer share", *fe_ols(O, "host", ["thread_new"], ["a", "month"]))
print("D. downvoted ~ replier newcomer + reply hostile + parent hostile | thread")
A_ = rep.assign(new=rep.new.astype(float)); show("all replies", *fe_ols(A_, "down", ["new", "host", "p_host"], ["thread"]))
