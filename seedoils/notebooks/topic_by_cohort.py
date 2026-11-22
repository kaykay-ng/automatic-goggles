"""Are the 2024 shifts in r/StopEatingSeedOils topic shares driven by new people, by long-time commenters, or both?
Cohorts: OLD = commenter's first post/comment in the subreddit before 2024-01-01; NEW = first from 2024. Themes = SESO_THEMES in artifact_data.py (hand grouping of BERTopic topics; topic model covers documents of >= 15 words).
Decomposition of the change in theme share (all documents from 2024 minus all before 2024; documents before 2024 are all OLD by construction):
  change = (OLD from 2024 - OLD before)  [what long-time commenters changed]  +  w_new * (NEW from 2024 - OLD from 2024)  [what newcomers add, w_new = newcomers' share of documents from 2024].
Also 'returners': the same people before and after (OLD authors with a topic-model document in both periods). Cluster bootstrap over commenters (300) for the intervals. Output: data/processed/topic_by_cohort.csv.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/topic_by_cohort.py"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
CUT = pd.Timestamp("2024-01-01").timestamp(); rng = np.random.default_rng(0)
TH = {"Politics": [46, 117, 43, 68, 107], "Vaccines and COVID": [20], "Pharma, FDA, corporations": [10, 50, 80, 116], "Ingredient labels and processed food": [61, 92, 60],
      "Shopping": [17, 11, 9], "Studies and evidence": [23, 52, 53], "Keto, carbs, fasting": [1, 66], "Omega-6 / PUFA biochemistry": [0, 79, 96]}
cols = ["id", "author", "created_utc"]
first = pd.concat([pd.read_csv(PROC / f, usecols=cols, keep_default_na=False) for f in ("seso_docs.csv.gz", "seso_short_docs.csv.gz")]).groupby("author").created_utc.min()
D = pd.read_csv(PROC / "seso_docs.csv.gz", usecols=cols, keep_default_na=False).merge(pd.read_csv(PROC / "seso_doc_topics.csv.gz", usecols=["id", "topic"]), on="id")
D = D[~D.author.isin(["[deleted]", "AutoModerator"])].copy(); D["post"] = D.created_utc >= CUT; D["new"] = D.author.map(first) >= CUT
print("docs", len(D), "pre", (~D.post).sum(), "post", D.post.sum(), "share of post docs by NEW", round(D[D.post].new.mean(), 3), "| authors", D.author.nunique())
for th, ts in TH.items(): D[th] = D.topic.isin(ts)
ret = set(D[(~D.new) & D.post].author) & set(D[~D.post].author)
D["ret"] = D.author.isin(ret)
rows = []
def stats(X):
    pre, old_post, new_post, allpost = X[~X.post], X[X.post & ~X.new], X[X.post & X.new], X[X.post]; w = len(new_post) / len(allpost)
    r = {}
    for th in TH:
        a, b, c, d = pre[th].mean(), old_post[th].mean(), new_post[th].mean(), allpost[th].mean()
        rp, rq = X[(~X.post) & X.ret][th].mean(), X[X.post & X.ret][th].mean()
        r[th] = dict(pre=a, old_post=b, new_post=c, total_change=d - a, long_time_changed=b - a, newcomers_add=w * (c - b), returners_pre=rp, returners_post=rq)
    return r
base = stats(D); idx = D.groupby("author").indices; keys = list(idx); boots = {th: {k: [] for k in base[th]} for th in TH}
for _ in range(300):
    pick = rng.integers(0, len(keys), len(keys)); ii = np.concatenate([idx[keys[j]] for j in pick]); s = stats(D.iloc[ii])
    for th in TH:
        for k in boots[th]: boots[th][k].append(s[th][k])
for th in TH:
    row = {"theme": th}
    for k, v in base[th].items():
        lo, hi = np.nanpercentile(boots[th][k], [2.5, 97.5]); row[k] = round(v * 100, 2); row[k + "_lo"] = round(lo * 100, 2); row[k + "_hi"] = round(hi * 100, 2)
    rows.append(row)
R = pd.DataFrame(rows); R.to_csv(PROC / "topic_by_cohort.csv", index=False)
pd.set_option("display.width", 250)
print(R[["theme", "pre", "old_post", "new_post", "total_change", "long_time_changed", "newcomers_add", "returners_pre", "returners_post"]].to_string(index=False))
print(R[["theme", "long_time_changed_lo", "long_time_changed_hi", "newcomers_add_lo", "newcomers_add_hi"]].to_string(index=False))
