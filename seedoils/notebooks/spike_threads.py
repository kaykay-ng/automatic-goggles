"""Which threads drove the activity spikes and where did 2024 newcomers enter? (rerun data seedoils/data/raw_haoyu; bots and [deleted] removed.)
(1) the 8 busiest weeks of r/StopEatingSeedOils (distinct active commenters, 2022 on) and, for each, the 3 threads that received most comments that week (post title, post age in days, share of the week's comments);
(2) newcomer entry (newcomer = first comment in the subreddit from 2024-01-01): share of newcomers whose first comment is in the 10 / 50 / 200 biggest entry threads; age of the post at the first comment (share on posts older than 30 / 365 days); the 10 biggest entry threads (title, month of post, newcomers).
(3) threads whose title mentions cancer and young/early: comments per month.
Prints post TITLES (public text) and aggregates, no usernames. Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/spike_threads.py"""
import gzip, json
import pandas as pd
from seedoil_common import is_bot

S = "StopEatingSeedOils"; CUT = pd.Timestamp("2024-01-01")
P = pd.DataFrame([(x["id"], x.get("title") or "", pd.to_datetime(int(x["created_utc"]), unit="s")) for x in map(json.loads, gzip.open(f"seedoils/data/raw_haoyu/{S}_posts.jsonl.gz", "rt"))], columns=["post", "title", "pt"])
C = pd.DataFrame([(x["author"] or "", x["link_id"][3:], pd.to_datetime(int(x["created_utc"]), unit="s")) for x in map(json.loads, gzip.open(f"seedoils/data/raw_haoyu/{S}_comments.jsonl.gz", "rt"))], columns=["a", "post", "t"])
C = C[(C.a != "[deleted]") & (C.a != "") & ~C.a.map(is_bot)].merge(P, on="post", how="left")
C["age"] = (C.t - C.pt).dt.days
short = lambda s: (s[:80] + "...") if len(s) > 80 else s
C["wk"] = C.t.dt.to_period("W").dt.start_time
wk = C.groupby("wk").a.nunique(); top = wk[wk.index >= "2022-01-01"].sort_values(ascending=False).head(8)
print("== busiest weeks (distinct commenters) and their top threads")
for w, n in top.sort_index().items():
    g = C[C.wk == w]; vc = g.post.value_counts(); print(f"{w.date()}  {n} commenters, {len(g)} comments; top-3 threads take {vc.head(3).sum() / len(g):.0%}")
    for p, k in vc.head(3).items():
        r = P[P.post == p]; t = r.title.iloc[0] if len(r) else "(post not in file)"; ag = g[g.post == p].age.median()
        print(f"    {k:>4} comments, post age {ag:.0f} d: {short(t)}")
print("\n== 2024 newcomers' first comments")
first = C.sort_values("t").groupby("a").head(1); N = first[first.t >= CUT]
print(f"newcomers {len(N):,}; first comment on a post older than 30 d: {(N.age > 30).mean():.0%}, older than 365 d: {(N.age > 365).mean():.0%} (median age {N.age.median():.0f} d)")
vc = N.post.value_counts()
for k in (10, 50, 200): print(f"  first comment in the {k} biggest entry threads: {vc.head(k).sum() / len(N):.1%}")
for p, k in vc.head(10).items():
    r = P[P.post == p]; print(f"    {k:>4} newcomers, post {r.pt.iloc[0].strftime('%Y-%m') if len(r) else '?'}: {short(r.title.iloc[0]) if len(r) else '(not in file)'}")
print("\n== threads with 'cancer' and 'young' / 'early' / 'millennial' in the title")
m = C[C.title.str.lower().str.contains(r"cancer") & C.title.str.lower().str.contains(r"young|early|gen z|millennial|under 50|younger")]
print(f"{m.post.nunique()} threads, {len(m):,} comments; biggest:")
for p, k in m.post.value_counts().head(5).items():
    r = P[P.post == p]; print(f"    {k:>4} comments, post {r.pt.iloc[0].strftime('%Y-%m')}: {short(r.title.iloc[0])}; newcomers' first comments there: {(N.post == p).sum()}")
