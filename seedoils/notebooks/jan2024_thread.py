"""How much of the January 2024 jump in r/StopEatingSeedOils came from one thread, and where did newcomers' first comments land? Counts only; thread titles are public post titles.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/jan2024_thread.py"""
import gzip, glob, json
import pandas as pd
def load(pat, keys):
    rows = []
    with gzip.open(glob.glob("seedoils/data/raw/" + pat)[0], "rt", encoding="utf-8") as f:
        for l in f:
            x = json.loads(l); rows.append([x.get(k) for k in keys])
    return pd.DataFrame(rows, columns=keys)
C = load("*StopEatingSeedOils_comments.jsonl.gz", ["id", "link_id", "author", "created_utc"]); P = load("*StopEatingSeedOils_posts.jsonl.gz", ["id", "created_utc", "title", "num_comments"])
C["d"] = pd.to_datetime(C.created_utc, unit="s"); P["d"] = pd.to_datetime(P.created_utc, unit="s"); P["link_id"] = "t3_" + P.id.astype(str)
cancer = P[P.title.astype(str).str.contains("Cancer Is Striking More Young People")].sort_values("num_comments", ascending=False).iloc[0]; print("thread:", cancer.d.date(), cancer.num_comments, cancer.link_id)
T = C[C.link_id == cancer.link_id]; print("its comments by week start:"); print(T.set_index("d").resample("W").size().loc[lambda s: s > 0].head(8).to_string())
for lab, a, b in (("Dec 2023 (4 weeks to 7 Jan)", "2023-12-11", "2024-01-08"), ("weeks of 8 Jan to 4 Feb 2024", "2024-01-08", "2024-02-05")):
    X = C[(C.d >= a) & (C.d < b)]; print(f"{lab}: {len(X)} comments, of which in the cancer thread {int((X.link_id == cancer.link_id).sum())}, in the top 5 threads {int(X.link_id.value_counts().head(5).sum())}")
base = C[(C.d >= "2023-12-11") & (C.d < "2024-01-08")]; jump = C[(C.d >= "2024-01-08") & (C.d < "2024-02-05")]
excl = jump[jump.link_id != cancer.link_id]; print(f"comments per 4 weeks: before {len(base)}, after {len(jump)}, after without the cancer thread {len(excl)}  -> excluding that thread the rise is x{len(excl)/len(base):.2f} instead of x{len(jump)/len(base):.2f}")
print("threads with 100+ comments per 4-week block: before", int((base.link_id.value_counts() >= 100).sum()), " after", int((jump.link_id.value_counts() >= 100).sum()))
first = C[~C.author.isin(["[deleted]", "AutoModerator"])].groupby("author").agg(t=("created_utc", "min")); fc = C.sort_values("created_utc").drop_duplicates("author")[["author", "link_id", "d"]]
nf = fc[(fc.d >= "2024-01-08") & (fc.d < "2024-02-05")]; print(f"authors whose first comment is in 8 Jan to 4 Feb 2024: {len(nf)}; of them in the cancer thread: {int((nf.link_id == cancer.link_id).sum())} ({(nf.link_id == cancer.link_id).mean()*100:.0f}%)")
na = fc[(fc.d >= "2023-12-11") & (fc.d < "2024-01-08")]; print(f"first-time commenters in the 4 weeks before: {len(na)}")
nl = fc[(fc.d >= "2024-01-08") & (fc.d < "2024-12-31")]; print("share of 2024 newcomers whose first comment was in that thread:", round((nl.link_id == cancer.link_id).mean() * 100, 1), "%")
