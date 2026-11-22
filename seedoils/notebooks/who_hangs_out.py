"""Where do seed-oil commenters hang out? Two cohorts of the 1,500 heaviest r/StopEatingSeedOils commenters (author_subreddit_counts*.jsonl.gz, seed_authors.csv):
  OLD = first comment in the subreddit before 2024-01-01, NEW = first comment from 2024.
For each cohort and period (before / from 2024) the share of the cohort with >= MIN interactions (posts + comments) in each subreddit. Aggregates only: no usernames.
Run from final_project/:  ../.venv/bin/python seedoils/notebooks/who_hangs_out.py  -> seedoils/data/processed/who_hangs_out.csv + summary printed."""
import glob
import gzip
import json
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
SPLIT, MIN = 1704067200, 3
A = pd.read_csv(PROC / "seed_authors.csv")
A = A[A.seed_subreddit == "StopEatingSeedOils"]
cohort = {r.author: ("new" if r.first_utc >= SPLIT else "old") for r in A.itertuples()}
counts = {}
for f in sorted(glob.glob(str(RAW / "author_subreddit_counts*.jsonl.gz"))):
    for line in gzip.open(f, "rt"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d["author"] in cohort:
            counts[d["author"]] = d["counts"]
N = Counter(cohort[a] for a in counts)
rows = []
for per in ("pre2024", "from2024"):
    share = {c: Counter() for c in ("old", "new")}
    for a, ct in counts.items():
        for sub, n in ct.get(per, {}).items():
            if n >= MIN and not sub.startswith("u_"):
                share[cohort[a]][sub] += 1
    for c in ("old", "new"):
        for sub, k in share[c].items():
            rows.append({"cohort": c, "period": per, "subreddit": sub, "authors": k, "n_cohort": N[c], "share_pct": round(100 * k / N[c], 1)})
R = pd.DataFrame(rows)
R.to_csv(PROC / "who_hangs_out.csv", index=False)
print("cohort sizes (fetched):", dict(N))
for per in ("pre2024", "from2024"):
    P = R[R.period == per].pivot_table(index="subreddit", columns="cohort", values="share_pct", fill_value=0)
    P["top"] = P.max(axis=1)
    print(f"\n== {per}: share of cohort with >= {MIN} interactions"); print(P.sort_values("top", ascending=False).head(22).round(1).to_string())
