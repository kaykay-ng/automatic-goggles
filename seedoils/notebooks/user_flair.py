"""User flair (self-declared identity) in r/StopEatingSeedOils, before / from 2024. Aggregates only; no usernames.
CAUTION: flair options were added over time (e.g. 'Skeptical of SESO', 'Low Fat', 'Keto' first appear in Oct 2023, 'Vegan' in Jul 2023), so shares across 1 Jan 2024 are partly mechanical.
Fair comparisons: (a) within the period when the options exist (Q4 2023 on), by quarter, among flaired comments; (b) OLD vs NEW authors (first comment before / from 2024, all authors) among flaired authors, by their commonest flair from 2024.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/user_flair.py -> seedoils/data/processed/user_flair_by_quarter.csv, user_flair_by_cohort.csv"""
from seedoil_common import is_bot, not_bot  # shared bot rule: AutoModerator + names ending in 'bot'
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
SPLIT = 1704067200
MAIN = ["🍤Seed Oil Avoider", "🌾 🥓 Omnivore", "🥩 Carnivore", "🥩 Carnivore - Moderator", "🤿Ray Peat", "Skeptical of SESO", "🥬Low Fat", "🧀 Keto", "🌱 Vegan", "🍓Low Carb"]
rows, first = [], {}
for line in gzip.open(RAW / "StopEatingSeedOils_comments.jsonl.gz", "rt"):
    try:
        d = json.loads(line)
    except ValueError:
        continue
    a, t = d.get("author"), int(d["created_utc"])
    if a in (None, "[deleted]") or is_bot(a):
        continue
    first[a] = min(first.get(a, t), t)
    f = d.get("author_flair_text")
    rows.append((a, t, None if f in (None, "None", "") else f))
C = pd.DataFrame(rows, columns=["a", "t", "f"])
C["q"] = pd.to_datetime(C.t, unit="s").dt.to_period("Q").astype(str)
C["f2"] = C.f.where(C.f.isin(MAIN), "other")
Q = C[(C.t >= 1696118400) & C.f.notna()]  # from 2023-10-01
qt = Q.groupby(["q", "f2"]).size().unstack(fill_value=0)
share = (qt.div(qt.sum(axis=1), axis=0) * 100).round(1)
share["n_flaired"] = qt.sum(axis=1); share["share_of_all_comments_pct"] = (qt.sum(axis=1) / C.groupby("q").size() * 100).round(1)
share.to_csv(PROC / "user_flair_by_quarter.csv")
pd.set_option("display.width", 250)
print("share of flaired comments by quarter, % (flair options all available from 2023-10):"); print(share.round(1).to_string())
F = C[(C.t >= SPLIT) & C.f.notna()]
mode = F.groupby("a").f2.agg(lambda s: Counter(s).most_common(1)[0][0])
coh = pd.Series({a: ("new" if first[a] >= SPLIT else "old") for a in mode.index})
ct = pd.crosstab(mode, coh); tot = ct.sum()
out = pd.DataFrame({"old_pct": (ct.old / tot.old * 100).round(1), "new_pct": (ct.new / tot.new * 100).round(1), "old_n": ct.old, "new_n": ct.new})
out.to_csv(PROC / "user_flair_by_cohort.csv")
print(f"\nflaired authors from 2024 by commonest flair: old n={tot.old}, new n={tot.new}"); print(out.sort_values("new_pct", ascending=False).to_string())
allf = C[C.t >= SPLIT]; allc = pd.Series({a: ("new" if first[a] >= SPLIT else "old") for a in allf.a.unique()})
print("\nshare of authors from 2024 who ever display a flair: old", round(100 * allf[allf.f.notna()].a.nunique() and (allc[allf[allf.f.notna()].a.unique()] == "old").sum() / (allc == "old").sum(), 1),
      "% new", round(100 * (allc[allf[allf.f.notna()].a.unique()] == "new").sum() / (allc == "new").sum(), 1), "%")
