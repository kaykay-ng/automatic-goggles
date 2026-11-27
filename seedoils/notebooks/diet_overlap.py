"""Did the seed-oil crowd come from (or move away from) diet communities? Overlap with a SET of diet subreddits, not one (replaces the
r/carnivore-only measure, which mixed 'left diet communities' with 'moved between diet subreddits').

Lists: seedoil_common.DIET_CORE (main result) and DIET_BORDERLINE (sensitivity), both fixed on 22 Nov before these numbers existed.
People: the heaviest commenters with fetched author histories (seed_authors.csv + author_subreddit_counts*.jsonl.gz):
  r/StopEatingSeedOils, split into OLD (first comment there before 2024-01-01) and NEW (from 2024), and r/ScientificNutrition for comparison.
  Heavy commenters only (>= 5 comments, top 1,500 per subreddit): the result describes the core regulars, not one-off visitors.
Measure: of the people in a group who were active anywhere on Reddit in a period (>= 1 interaction), the share with >= MIN interactions
  (posts + comments) in AT LEAST ONE subreddit of the list in that period. Interval: 95% bootstrap over people (1,000 resamples).
Variants: core | core + each borderline group | core + all borderline groups. Also the share per core subreddit (which communities move).
Run from final_project/ (repo root):  ./.venv-nlp/bin/python seedoils/notebooks/diet_overlap.py
 -> seedoils/data/processed/diet_overlap.csv, diet_overlap_by_subreddit.csv; facts seso_diet_* in data/processed/artifact/facts.json
   (if facts.json exists; run after artifact_data.py). Aggregates only: no usernames."""
import glob
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

from seedoil_common import DIET_BORDERLINE, DIET_CORE, SPLIT_TS, HISTORY_GLOB

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
SPLIT, MIN, REPS = SPLIT_TS, 3, 1000
rng = np.random.default_rng(0)

flat = lambda groups: {s.lower() for subs in groups.values() for s in subs}
CORE = flat(DIET_CORE)
VARIANTS = {"core": CORE}
for g, subs in DIET_BORDERLINE.items():
    VARIANTS[f"core + {g}"] = CORE | {s.lower() for s in subs}
VARIANTS["core + all borderline"] = CORE | flat(DIET_BORDERLINE)

A = pd.read_csv(PROC / "seed_authors.csv")
groups = {}
for r in A.itertuples():
    if r.seed_subreddit == "StopEatingSeedOils":
        groups.setdefault(r.author, set()).add("SESO old" if r.first_utc < SPLIT else "SESO new")
    elif r.seed_subreddit == "ScientificNutrition":
        groups.setdefault(r.author, set()).add("SciNut")
counts = {}
for f in sorted(glob.glob(str(RAW / HISTORY_GLOB))):
    for line in gzip.open(f, "rt"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d["author"] in groups:
            counts[d["author"]] = {per: {s.lower(): n for s, n in c.items()} for per, c in d["counts"].items()}
print(f"authors with fetched histories: {len(counts):,} of {len(groups):,} selected")


def share(active_sets, subs):
    hit = np.array([bool(s & subs) for s in active_sets], dtype=float)
    boots = [hit[rng.integers(0, len(hit), len(hit))].mean() for _ in range(REPS)] if len(hit) else [np.nan]
    return 100 * hit.mean(), 100 * np.percentile(boots, 2.5), 100 * np.percentile(boots, 97.5)


rows, per_sub = [], []
for grp in ("SESO old", "SESO new", "SESO all", "SciNut"):
    members = [a for a, g in groups.items() if a in counts and (grp in g or (grp == "SESO all" and g & {"SESO old", "SESO new"}))]
    for per in ("pre2024", "from2024"):
        act = [counts[a].get(per, {}) for a in members]
        act = [c for c in act if sum(c.values()) > 0]  # active anywhere on Reddit in this period
        sets = [{s for s, n in c.items() if n >= MIN} for c in act]
        for v, subs in VARIANTS.items():
            m, lo, hi = share(sets, subs)
            rows.append({"group": grp, "period": per, "variant": v, "n_people": len(sets), "share_pct": round(m, 1), "ci_lo": round(lo, 1), "ci_hi": round(hi, 1)})
        for cat, subs in DIET_CORE.items():
            for s in subs:
                per_sub.append({"group": grp, "period": per, "category": cat, "subreddit": s, "n_people": len(sets),
                                "share_pct": round(100 * np.mean([s.lower() in x for x in sets]), 1) if sets else None})
R = pd.DataFrame(rows); S = pd.DataFrame(per_sub)
R.to_csv(PROC / "diet_overlap.csv", index=False); S.to_csv(PROC / "diet_overlap_by_subreddit.csv", index=False)
pd.set_option("display.width", 200)
print(f"\nShare of each group active (>= {MIN} interactions) in at least one diet subreddit, before vs from 2024 (95% bootstrap interval):")
W = R.assign(v=R.share_pct.astype(str) + " [" + R.ci_lo.astype(str) + "-" + R.ci_hi.astype(str) + "]").pivot_table(index=["variant", "group"], columns="period", values="v", aggfunc="first")
print(W[["pre2024", "from2024"]].to_string())
print(f"\nCore subreddits, SESO all, share active before -> from 2024:")
T = S[S.group == "SESO all"].pivot_table(index=["category", "subreddit"], columns="period", values="share_pct")
print(T[["pre2024", "from2024"]].assign(change=lambda x: x.from2024 - x.pre2024).sort_values("change").to_string())

F = PROC / "artifact" / "facts.json"
if F.exists():
    d = json.loads(F.read_text()); facts = {r["key"]: r for r in d["rows"]}
    get = lambda g, p, v="core": R[(R.group == g) & (R.period == p) & (R.variant == v)].share_pct.iloc[0]
    for k, g, p, lab in (("seso_diet_pre", "SESO all", "pre2024", "Heavy r/StopEatingSeedOils commenters active in a diet subreddit before 2024"),
                         ("seso_diet_from", "SESO all", "from2024", "Heavy r/StopEatingSeedOils commenters active in a diet subreddit from 2024"),
                         ("seso_new_diet_pre", "SESO new", "pre2024", "Heavy newcomers (first comment 2024+) active in a diet subreddit BEFORE 2024")):
        facts[k] = {"key": k, "value": float(get(g, p)), "label": lab + f" (core list of {len(CORE)} diet subreddits, >= {MIN} interactions)", "unit": "%"}
    d["rows"] = list(facts.values()); F.write_text(json.dumps(d)); print("\nfacts.json updated: seso_diet_pre, seso_diet_from, seso_new_diet_pre")
