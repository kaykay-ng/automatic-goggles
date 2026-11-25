"""Where were the newcomers active before they joined r/StopEatingSeedOils? Uses the whole-history subreddit counts fetched for the 1,500 most active r/StopEatingSeedOils commenters (seed_authors.csv, author_subreddit_counts*.jsonl.gz).
Newcomer = first comment in r/StopEatingSeedOils from 2024-01-01; old guard = before. 'Active' = 3+ posts or comments in a subreddit BEFORE 2024. Share of newcomers (with any prior history) vs the old guard's share who were active in each subreddit before 2024.
Limits: heavy commenters only (not the typical newcomer, who writes 1-2 comments); the counts are per period, not a sequence, so this shows where they were active, not a path; 32% of these newcomers have no history of 3+ interactions before 2024.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python seedoils/notebooks/newcomer_origins.py   (aggregates only)"""
import collections
import csv
import glob
import gzip
import json

CUT = 1704067200; S = "StopEatingSeedOils"
sel = {r["author"] for r in csv.DictReader(open("seedoils/data/processed/seed_authors.csv")) if r["seed_subreddit"] == S}
first = {}
with gzip.open(glob.glob("seedoils/data/raw/*StopEatingSeedOils_comments.jsonl.gz")[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); a = x.get("author") or ""; t = int(x["created_utc"])
        if a not in first or t < first[a]: first[a] = t
recs = {}
for p in sorted(glob.glob("seedoils/data/raw/author_subreddit_counts*.jsonl.gz")):
    try:
        with gzip.open(p, "rt") as fh:
            for l in fh:
                try: r = json.loads(l)
                except Exception: continue
                if r["author"] in sel: recs[r["author"]] = r
    except Exception: pass
new = [a for a in recs if first.get(a, 0) >= CUT]; old = [a for a in recs if first.get(a, CUT) < CUT]
pre = lambda a: {s for s, n in recs[a]["counts"].get("pre2024", {}).items() if n >= 3 and s != S}
tot = {a: sum(recs[a]["counts"].get("pre2024", {}).values()) for a in recs}
an = [a for a in new if tot[a] >= 3]; ao = [a for a in old if tot[a] >= 3]
print(f"heavy commenters {len(recs)}; newcomers {len(new)} ({len(an)} with prior history), old guard {len(old)} ({len(ao)} with prior history)")
cn = collections.Counter(s for a in an for s in pre(a)); co = collections.Counter(s for a in ao for s in pre(a))
rows = sorted(((s, cn[s] / len(an) * 100, co[s] / len(ao) * 100, cn[s]) for s in cn if cn[s] >= 40), key=lambda r: -r[1])
for s, a, b, n in rows[:20]: print(f"  r/{s:<24} newcomers {a:5.1f}%  old guard {b:5.1f}%  (n={n})")
