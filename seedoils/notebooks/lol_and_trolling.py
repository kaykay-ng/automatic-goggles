"""Why is 'lol' the top newcomer term, and are there signs of trolling? Descriptive checks on the same documents as newcomer_terms.py (comments of >= 15 words from 2024, quotes/links removed).
For comments containing 'lol' (a): how many people, how concentrated in a few authors, hostile and downvoted shares vs comments without it, by cohort. (b) other casual or trolling-style words (lmao, shill, bot, sheep, idiot, stupid, ...):
their rate in each cohort. (c) copy-pasted text: share of comments whose exact text appears 3+ times. Aggregates only.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python seedoils/notebooks/lol_and_trolling.py"""
from seedoil_common import is_bot, not_bot, SPLIT_TS# shared bot rule: AutoModerator + names ending in 'bot'
import glob
import gzip
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

P = Path("seedoils/data/processed"); CUT = SPLIT_TS
first = {}; score = {}
with gzip.open(glob.glob("seedoils/data/raw/*StopEatingSeedOils_comments.jsonl.gz")[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); a = x["author"]; t = int(x["created_utc"]); score[x["id"]] = x.get("score")
        if a not in first or t < first[a]: first[a] = t
D = pd.read_csv(P / "seso_docs.csv.gz", keep_default_na=False); D = D[(D.kind == "comment") & (D.created_utc >= CUT) & (~D.author.isin(["[deleted]", "AutoModerator"]) & not_bot(D.author))].copy()
D["new"] = (D.author.map(first) >= CUT).astype(int); D["down"] = (D.id.map(score).astype(float) <= 0).astype(float)
LABS = list(pd.read_csv(P / "goemo_monthly.csv", nrows=1).columns[1:29]); HI = [LABS.index(k) for k in ("anger", "annoyance", "disapproval", "disgust")]
z = np.load(P / "goemo_seso.npz", allow_pickle=True); h = pd.Series(z["p"][:, HI].max(1) >= .5, index=z["id"].astype(str)); D["host"] = D.id.map(h).astype(float)
low = D.text.str.lower(); words = lambda w: low.str.contains(r"\b" + w + r"\b", regex=True)
D["lol"] = words("lol")
print("(a) 'lol'")
for c, nm in ((0, "old guard"), (1, "newcomers")):
    s = D[D.new == c]; l = s[s.lol]; n = s[~s.lol]; top = l.author.value_counts()
    print(f"  {nm}: {len(l):,} of {len(s):,} comments ({len(l) / len(s):.1%}); {l.author.nunique():,} people ({l.author.nunique() / s.author.nunique():.1%} of the group); top 10 people write {top.head(10).sum() / len(l):.1%} of them; max by one person {top.iloc[0]}")
    print(f"     with lol: hostile {l.host.mean() * 100:.1f}%, downvoted {l.down.mean() * 100:.1f}%, median words {l.text.str.split().str.len().median():.0f} | without lol: hostile {n.host.mean() * 100:.1f}%, downvoted {n.down.mean() * 100:.1f}%, median words {n.text.str.split().str.len().median():.0f}")
nm_ = D[D.new == 1]; per = nm_.groupby("author").size(); one = per[per <= 2].index
print(f"  newcomers who wrote at most 2 comments: {len(one):,} people ({len(one) / len(per):.0%}); 'lol' rate in their comments {nm_[nm_.author.isin(one)].lol.mean():.1%} vs {nm_[~nm_.author.isin(one)].lol.mean():.1%} for the rest")
print("(b) casual and trolling-style words, share of comments containing the word (old guard -> newcomers, ratio)")
for w in ("lol", "lmao", "lmfao", "haha", "shill", "shills", "bot", "bots", "sheep", "idiot", "idiots", "stupid", "dumb", "moron", "clown", "cope", "troll", "trolls", "triggered", "snowflake", "libtard", "bullshit"):
    a = words(w)[D.new == 0].mean() * 100; b = words(w)[D.new == 1].mean() * 100
    if a + b > 0.02: print(f"  {w:<10} {a:5.2f}% -> {b:5.2f}%  x{(b / a if a else float('nan')):.2f}")
t = D.text.str.strip().str.lower(); dup = t.map(t.value_counts()); print("(c) copy-paste: comments whose exact text appears 3+ times:", f"old guard {(dup[D.new == 0] >= 3).mean():.2%}, newcomers {(dup[D.new == 1] >= 3).mean():.2%}; most repeated text appears {int(dup.max())} times")
print("    hostile / downvoted share of comments by newcomers whose text is repeated 3+ times:", f"{D[(D.new == 1) & (dup >= 3)].host.mean() * 100:.1f}% / {D[(D.new == 1) & (dup >= 3)].down.mean() * 100:.1f}%")
