"""Datasets for the artifact's introduction ('Where the comments come from'): subreddits, activity (items per month), events.
Run from final_project/:  ../.venv/bin/python seedoils/notebooks/intro_data.py  -> seedoils/data/processed/artifact/{subreddits,activity,events}.json
Reads seedoils/data/raw/<sub>_{posts,comments}.jsonl.gz (Arctic Shift). Aggregates only: no usernames, no text.
Events are public news dates added by hand (NOT from our data); the Reddit counts are ours."""
import collections
import datetime as dt
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed" / "artifact"
SUBS = [("StopEatingSeedOils", "Seed-oil critics", "Active from 2018. Argues that seed oils are harmful; grew most from 2024."),
        ("ScientificNutrition", "Research discussion", "Active from 2018. Posts and debates about nutrition studies; the comparison community.")]
EVENTS = [("2024-08-23", "RFK Jr. ends his campaign and endorses Trump"), ("2024-11-05", "US presidential election"), ("2024-11-14", "RFK Jr. named as nominee for health secretary")]
rows_s, rows_a = [], []
for s, role, about in SUBS:
    cnt, auth, n = collections.Counter(), set(), {"posts": 0, "comments": 0}
    lo, hi = 10 ** 11, 0
    for k in ("posts", "comments"):
        for line in gzip.open(RAW / f"{s}_{k}.jsonl.gz", "rt"):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            t = int(d["created_utc"]); lo, hi = min(lo, t), max(hi, t); n[k] += 1
            if d.get("author") not in (None, "[deleted]", "AutoModerator"):
                auth.add(d["author"])
            m = dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m")
            if m >= "2018-10":
                cnt[m] += 1
    f = lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m")
    rows_s.append({"subreddit": "r/" + s, "role": role, "about": about, "posts": n["posts"], "comments": n["comments"], "people": len(auth), "first": f(lo), "last": f(hi)})
    last = f(hi)
    for m in sorted(cnt):
        if m < last:  # drop the unfinished final month
            rows_a.append({"month": m, "subreddit": "r/" + s, "items": cnt[m]})
script = Path(__file__).read_text()
meta = [{"label": "intro_data.py", "value": script}]
(OUT / "subreddits.json").write_text(json.dumps({"rows": rows_s, "meta": meta}))
(OUT / "activity.json").write_text(json.dumps({"rows": rows_a, "meta": meta}))
(OUT / "events.json").write_text(json.dumps({"rows": [{"date": d, "label": l} for d, l in EVENTS], "meta": [{"label": "source", "value": "Public news dates, added by hand; not derived from the Reddit data."}]}))
print(rows_s)
