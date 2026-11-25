"""Questions on the r/StopEatingSeedOils reply network (user request 25 Nov), replies from 2024 unless stated (both cohorts present).
Reply = a comment by A whose parent is B's post or comment (same rules as reply_network.py: no bots, no [deleted], no self-replies).
Tone = GoEmotions 'disapproving tone' (max of anger, annoyance, disapproval, disgust >= 0.5; hand-checked: mostly criticism, about 1 in 5 hostile
toward people), scored on every comment (goemo_seso.npz + goemo_seso_short.npz).
Q1 Do the old guard and newcomers talk to each other? (a) who replies to whom vs activity alone; (b) tone of replies by pair type, raw and within
   replier (each replier compared with themselves: linear probability, replier means removed, 95% CI from resampling repliers); (c) do newcomers'
   first contributions get a reply, and from whom (vs the old guard's share of all replies that month)?
Q2 Do people reply to those who share their interests? For the 2,621 commenters with >= 10 topic-model documents: topic profile = share of their
   documents in each of the ~123 topics, LEAVING OUT the thread in question. For each reply A -> B in thread T: cosine(A, B) vs the mean cosine of A
   with every other of these commenters active in T (the people A could have answered there).
Q3 Is the tone harsher toward people with different interests? Disapproving share by similarity quintile, and within replier (and within thread).
Output: data/processed/reply_findings.json (aggregates only). Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/reply_findings.py"""
import glob
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from seedoil_common import is_bot  # noqa: E402

P, RAW = Path("seedoils/data/processed"), Path("seedoils/data/raw")
SPLIT = int(pd.Timestamp("2024-01-01", tz="UTC").timestamp())
H4 = ["anger", "annoyance", "disapproval", "disgust"]
bad = lambda a: (not isinstance(a, str)) or (not a) or a == "[deleted]" or is_bot(a)  # noqa: E731
out = {}

# ---------------------------------------------------------------- data
posts = {}
with gzip.open(glob.glob(str(RAW / "*StopEatingSeedOils_posts.jsonl.gz"))[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); posts[x["id"]] = (x.get("author") or "", int(x["created_utc"]))
rows = []
with gzip.open(glob.glob(str(RAW / "*StopEatingSeedOils_comments.jsonl.gz"))[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); rows.append((x["id"], x.get("author") or "", x["parent_id"], x["link_id"][3:], int(x["created_utc"]), x.get("score")))
C = pd.DataFrame(rows, columns=["id", "a", "parent", "thread", "t", "score"])
cauth = dict(zip(C.id, C.a))
C["to_post"] = C.parent.str.startswith("t3_")
C["b"] = [posts.get(p[3:], ("", 0))[0] if tp else cauth.get(p[3:], "") for p, tp in zip(C.parent, C.to_post)]
LAB = list(pd.read_csv(P / "goemo_monthly.csv", nrows=1).columns[1:29]); dis = {}
for fn in ("goemo_seso.npz", "goemo_seso_short.npz"):
    z = np.load(P / fn, allow_pickle=True); pr = z["p"].astype(np.float32); m = pr[:, [LAB.index(h) for h in H4]].max(1) >= .5
    dis.update(zip(z["id"].astype(str), m))
C["dis"] = C.id.map(dis)
act = pd.concat([pd.DataFrame({"a": [v[0] for v in posts.values()], "t": [v[1] for v in posts.values()]}), C[["a", "t"]]])
act = act[~act.a.map(bad)]; first = act.groupby("a").t.min(); newc = first >= SPLIT
R = C[~C.a.map(bad) & ~C.b.map(bad) & (C.a != C.b)].copy()
R["a_new"], R["b_new"] = R.a.map(newc), R.b.map(newc)
R24 = R[R.t >= SPLIT].copy()
print(f"replies {len(R):,}; from 2024 {len(R24):,}; with a tone score {R24.dis.notna().mean():.1%}")
rng = np.random.default_rng(0)


def boot_by(df, key, stat, reps=500):
    g = df.groupby(key).indices; ks = list(g); vals = []
    for _ in range(reps):
        pick = rng.choice(len(ks), len(ks)); idx = np.concatenate([g[ks[i]] for i in pick]); vals.append(stat(df.iloc[idx]))
    return [round(float(np.percentile(vals, 2.5)), 4), round(float(np.percentile(vals, 97.5)), 4)]


def within(df, y, x, group):
    """slope of y on x after removing group means (fixed effects), as a difference for binary x"""
    d = df[[y, x, group]].dropna().astype({y: float, x: float})
    yd = d[y] - d.groupby(group)[y].transform("mean"); xd = d[x] - d.groupby(group)[x].transform("mean")
    return float((xd * yd).sum() / (xd * xd).sum()) if (xd * xd).sum() else float("nan")


# ---------------------------------------------------------------- Q1
lab = {False: "old guard", True: "newcomer"}
tot = len(R24); send = R24.groupby("a_new").size() / tot; recv = R24.groupby("b_new").size() / tot
q1a = []
for s_ in (False, True):
    for t_ in (False, True):
        sub = R24[(R24.a_new == s_) & (R24.b_new == t_)]; e = send[s_] * recv[t_]
        q1a.append({"from": lab[s_], "to": lab[t_], "replies": int(len(sub)), "observed_share": round(len(sub) / tot, 3), "expected_share": round(float(e), 3),
                    "lift": round(len(sub) / tot / e, 2), "disapproving_pct": round(float(sub.dis.mean() * 100), 2)})
out["q1_mixing_and_tone"] = q1a
T = R24.dropna(subset=["dis"]).copy(); T["to_new"] = T.b_new.astype(float); T["d"] = T.dis.astype(float)
q1b = {}
for s_ in (False, True):
    sub = T[T.a_new == s_].reset_index(drop=True)
    est = within(sub, "d", "to_new", "a")
    ci = boot_by(sub, "a", lambda d: within(d, "d", "to_new", "a"), reps=300)
    q1b[lab[s_] + " repliers"] = {"replies": int(len(sub)), "repliers": int(sub.a.nunique()),
                                  "within_replier_diff_pts_to_newcomer_vs_old": round(est * 100, 2), "ci95_pts": [round(v * 100, 2) for v in ci]}
out["q1_tone_within_replier"] = q1b
# (c) first contributions of newcomers (from 2024): does the first post or comment get a reply, and who replies first?
contrib = pd.concat([pd.DataFrame({"id": list(posts), "a": [v[0] for v in posts.values()], "t": [v[1] for v in posts.values()], "kind": "post"}),
                     C[["id", "a", "t"]].assign(kind="comment")])
contrib = contrib[~contrib.a.map(bad)].sort_values("t"); fc = contrib.groupby("a").head(1)
fc = fc[fc.a.map(newc)]
rep = R.assign(pid=R.parent.str[3:]).sort_values("t").groupby("pid").head(1)[["pid", "a_new", "t"]]
fc = fc.merge(rep, left_on="id", right_on="pid", how="left", suffixes=("", "_r"))
fc["replied"] = fc.pid.notna(); fc["month"] = pd.to_datetime(fc.t, unit="s").dt.to_period("M")
R24["month"] = pd.to_datetime(R24.t, unit="s").dt.to_period("M"); old_share_month = 1 - R24.groupby("month").a_new.mean()
fr = fc[fc.replied]; exp_old = fr.month.map(old_share_month).mean()
allc = contrib[contrib.t >= SPLIT].merge(rep, left_on="id", right_on="pid", how="left")
out["q1_first_contribution"] = {"newcomers": int(len(fc)), "first_is_post_pct": round(float((fc.kind == "post").mean() * 100), 1),
                                "first_gets_reply_pct": round(float(fc.replied.mean() * 100), 1),
                                "first_post_gets_reply_pct": round(float(fc[fc.kind == "post"].replied.mean() * 100), 1),
                                "first_comment_gets_reply_pct": round(float(fc[fc.kind == "comment"].replied.mean() * 100), 1),
                                "any_contribution_from_2024_gets_reply_pct": round(float(allc.pid.notna().mean() * 100), 1),
                                "first_reply_by_old_guard_pct": round(float((~fr.a_new.astype(bool)).mean() * 100), 1),
                                "expected_old_guard_pct_from_reply_share_that_month": round(float(exp_old * 100), 1),
                                "hours_to_first_reply_median": round(float(((fr.t_r - fr.t) / 3600).median()), 2)}
print(json.dumps(out, indent=1))

# ---------------------------------------------------------------- Q2: topic profiles of the 2,621 commenters, leave-thread-out
D = pd.read_csv(P / "seso_doc_topics.csv.gz", usecols=["id", "kind", "topic"])
thread_of = dict(zip(C.id, C.thread)); thread_of.update({k: k for k in posts})
auth = dict(cauth); auth.update({k: v[0] for k, v in posts.items()})
D["a"], D["thread"] = D.id.map(auth), D.id.map(thread_of); D = D[D.a.notna() & ~D.a.map(bad)]
nd = D.groupby("a").size(); heavy = set(nd[nd >= 10].index); D = D[D.a.isin(heavy)]
K = int(D.topic.max()) + 1; people = sorted(heavy); pix = {a: i for i, a in enumerate(people)}
Prof = np.zeros((len(people), K)); np.add.at(Prof, (D.a.map(pix).values, D.topic.values), 1)
TC = D.groupby(["thread", "a", "topic"]).size()
print(f"heavy commenters {len(people):,}, topics {K}")
HR = R24[R24.a.isin(heavy) & R24.b.isin(heavy)].copy()
active = pd.concat([C[["a", "thread"]], pd.DataFrame({"a": [v[0] for v in posts.values()], "thread": list(posts)})])
active = active[active.a.isin(heavy)].drop_duplicates()
act_by_t = active.groupby("thread").a.apply(list).to_dict()
obs, expv, rows_sim = [], [], []
for th, grp in HR.groupby("thread"):
    cand = act_by_t.get(th, [])
    if len(cand) < 3:
        continue
    M = Prof[[pix[a] for a in cand]].copy()
    if th in TC.index.get_level_values(0):
        sub = TC.loc[th]
        for (a, tp), n in sub.items():
            if a in cand:
                M[cand.index(a), tp] -= n
    nrm = np.linalg.norm(M, axis=1); nrm[nrm == 0] = np.nan; M = M / nrm[:, None]
    S = M @ M.T; ci = {a: i for i, a in enumerate(cand)}
    for r in grp.itertuples():
        if r.a not in ci or r.b not in ci:
            continue
        i, j = ci[r.a], ci[r.b]; others = [k for k in range(len(cand)) if k != i]
        s_obs = S[i, j]; s_exp = np.nanmean(S[i, others])
        if np.isnan(s_obs) or np.isnan(s_exp):
            continue
        rows_sim.append((r.a, r.b, th, r.id, s_obs, s_exp, r.dis, r.a_new, r.b_new))
SIM = pd.DataFrame(rows_sim, columns=["a", "b", "thread", "id", "sim", "sim_exp", "dis", "a_new", "b_new"])
SIM["gap"] = SIM.sim - SIM.sim_exp
out["q2_interest_similarity"] = {"replies": int(len(SIM)), "repliers": int(SIM.a.nunique()), "threads": int(SIM.thread.nunique()),
                                 "mean_similarity_to_replied": round(float(SIM.sim.mean()), 4), "mean_similarity_to_others_in_thread": round(float(SIM.sim_exp.mean()), 4),
                                 "mean_gap": round(float(SIM.gap.mean()), 4), "gap_ci95": boot_by(SIM.reset_index(drop=True), "a", lambda d: d.gap.mean(), reps=300),
                                 "share_replies_above_thread_mean_pct": round(float((SIM.gap > 0).mean() * 100), 1)}
print(out["q2_interest_similarity"])

# ---------------------------------------------------------------- Q3: tone by interest similarity
S3 = SIM.dropna(subset=["dis"]).reset_index(drop=True); S3["d"] = S3.dis.astype(float)
S3["q"] = pd.qcut(S3.sim, 5, labels=False)
S3["z"] = (S3.sim - S3.sim.mean()) / S3.sim.std()
out["q3_tone_by_similarity"] = {
    "quintiles": [{"quintile": int(k) + 1, "similarity_range": [round(float(g.sim.min()), 3), round(float(g.sim.max()), 3)], "replies": int(len(g)),
                   "disapproving_pct": round(float(g.d.mean() * 100), 2)} for k, g in S3.groupby("q")],
    "within_replier_pts_per_sd_similarity": round(within(S3, "d", "z", "a") * 100, 2),
    "within_replier_ci95": [round(v * 100, 2) for v in boot_by(S3, "a", lambda d: within(d, "d", "z", "a"), reps=300)],
    "within_thread_pts_per_sd_similarity": round(within(S3, "d", "z", "thread") * 100, 2),
    "within_thread_ci95": [round(v * 100, 2) for v in boot_by(S3, "thread", lambda d: within(d, "d", "z", "thread"), reps=300)]}
print(json.dumps(out["q3_tone_by_similarity"], indent=1))
(P / "reply_findings.json").write_text(json.dumps(out, indent=1))
print("wrote reply_findings.json")
