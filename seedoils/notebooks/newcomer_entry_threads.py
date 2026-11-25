"""How did the 2024 newcomers enter r/StopEatingSeedOils? Looks at the thread of each person's FIRST comment (newcomer = first comment in the subreddit in 2024).
 (1) concentration: share of 2024 newcomers whose first comment was in the 10 / 50 / 200 biggest entry threads;
 (2) popularity: share of newcomers' first comments vs established commenters' comments (first comment before 2024) by decile of the post's score (2024 posts);
 (3) a ROUGH category of the 200 biggest entry threads from keyword rules on the post TITLE (politics/RFK; health news; food products and restaurants; questions; other).
Limits: the first comment is not the reason for joining; no referral or feed data; keyword rules are crude; the raw posts file has no link-domain or crosspost field.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python seedoils/notebooks/newcomer_entry_threads.py   (aggregates and public post titles only)"""
import glob
import gzip
import json

import numpy as np
import pandas as pd


def load(pat, keys):
    rows = []
    with gzip.open(glob.glob("seedoils/data/raw/" + pat)[0], "rt", encoding="utf-8") as f:
        for l in f:
            x = json.loads(l); rows.append([x.get(k) for k in keys])
    return pd.DataFrame(rows, columns=keys)


C = load("*StopEatingSeedOils_comments.jsonl.gz", ["id", "link_id", "author", "created_utc"]); C = C[~C.author.isin(["[deleted]", "AutoModerator"])].copy()
P = load("*StopEatingSeedOils_posts.jsonl.gz", ["id", "title", "score", "num_comments", "created_utc"]); P["link_id"] = "t3_" + P.id.astype(str); P["score"] = P.score.fillna(0)
C["d"] = pd.to_datetime(C.created_utc, unit="s"); first = C.sort_values("d").drop_duplicates("author")[["author", "link_id", "d"]]
n24 = first[(first.d >= "2024-01-01") & (first.d < "2025-01-01")]; oldset = set(first[first.d < "2024-01-01"].author)
reg = C[(C.d >= "2024-01-01") & (C.d < "2025-01-01") & C.author.isin(oldset)]
T = n24.groupby("link_id").size().rename("firsts").reset_index().merge(P[["link_id", "title", "score"]], on="link_id", how="left").sort_values("firsts", ascending=False)
print(f"first-time commenters in 2024: {len(n24):,}; share whose first comment was in the top 10 / 50 / 200 threads: {[round(T.firsts.head(k).sum() / len(n24) * 100, 1) for k in (10, 50, 200)]}")
P24 = P[pd.to_datetime(P.created_utc, unit="s").dt.year == 2024].copy(); P24["dec"] = pd.qcut(P24.score.rank(method="first"), 10, labels=False); mp = dict(zip(P24.link_id, P24.dec))
sa = n24.link_id.map(mp).dropna().value_counts(normalize=True).sort_index() * 100; sb = reg.link_id.map(mp).dropna().value_counts(normalize=True).sort_index() * 100
print("post-score decile (0 least upvoted .. 9 most): newcomers' first comments %", sa.round(1).tolist(), "| regulars' comments %", sb.round(1).tolist())
top = T.head(200).copy(); tl = top.title.astype(str).str.lower()
top["cat"] = np.select([tl.str.contains(r"rfk|trump|maha|kennedy|biden|harris|vote|elect|politic|republican|democrat|fda|government|big pharma"), tl.str.contains(r"cancer|doctor|study|studies|research|science|heart|health"),
                        tl.str.contains(r"butter|margarine|ice cream|restaurant|sauce|chips|popcorn|label|ingredient|fries|fry|bread|protein shake|menu|store|grocery|costco|mayo|dressing|cereal|snack|everything|food|eat"), tl.str.contains(r"\?|what |why |how |anyone|should|help|advice")],
                       ["politics, government, RFK Jr.", "health news, doctors, studies", "food products, restaurants, labels", "question or advice"], "other")
print((top.groupby("cat").firsts.sum() / len(n24) * 100).round(1).sort_values(ascending=False).to_string())
