"""Re-fetch a subreddit's posts with the crosspost fields the first download left out (num_crossposts, crosspost_parent).
num_crossposts = how many times THIS post was crossposted elsewhere (outbound); crosspost_parent = the original post, when THIS post is itself a crosspost (inbound).
Output (separate from the rerun data): seedoils/data/raw_crosspost/<sub>_posts_crosspost.jsonl.gz (not resumable; ~120 requests for r/StopEatingSeedOils).
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/fetch_crosspost_fields.py StopEatingSeedOils"""
import gzip
import json
import sys
import time
import urllib.parse
from pathlib import Path

from fetch_arctic_shift import API, PAGE, PAUSE, START, get

sub = sys.argv[1]
out = Path("seedoils/data/raw_crosspost"); out.mkdir(parents=True, exist_ok=True)
KEEP = ("id", "created_utc", "subreddit", "num_crossposts", "crosspost_parent", "score", "num_comments", "url", "subreddit_subscribers")  # the API rejects num_crossposts in `fields`, so full records are requested and trimmed here
after, seen, n = START, set(), 0
with gzip.open(out / f"{sub}_posts_crosspost.jsonl.gz", "wt", encoding="utf-8") as f:
    while True:
        page = get(API.format(kind="posts") + "?" + urllib.parse.urlencode({"subreddit": sub, "limit": PAGE, "sort": "asc", "after": after - 1}))
        fresh = [x for x in page if x["id"] not in seen]
        for x in fresh: f.write(json.dumps({k: x.get(k) for k in KEEP}) + "\n"); seen.add(x["id"])
        n += len(fresh)
        if len(page) < PAGE or not fresh: break
        after = int(fresh[-1]["created_utc"]); time.sleep(PAUSE)
        if n % 2000 < PAGE: print(f"  {n:,} posts, up to {time.strftime('%Y-%m-%d', time.gmtime(after))}", flush=True)
print(f"{sub}: {n:,} posts saved")
