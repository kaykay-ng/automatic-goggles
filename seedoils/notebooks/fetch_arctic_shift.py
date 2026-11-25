"""Download a subreddit's full post or comment history from the Arctic Shift API.

Arctic Shift (https://arctic-shift.photon-reddit.com, run by u/RaiderBDev) serves the
Pushshift-style Reddit archive per subreddit, up to the present day. The Academic Torrents
dumps only come as whole-of-Reddit monthly files (~30 GB each), so this is the practical route.

Output: seedoils/data/raw/<subreddit>_<kind>.jsonl.gz (one JSON object per line, gzip members
appended per page). Resumable: re-running continues after the newest saved item, and items that
share the boundary timestamp are de-duplicated by id.

Usage (from the repo root):
    python seedoils/notebooks/fetch_arctic_shift.py StopEatingSeedOils posts
    python seedoils/notebooks/fetch_arctic_shift.py StopEatingSeedOils comments
"""

import gzip
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

API = "https://arctic-shift.photon-reddit.com/api/{kind}/search"
FIELDS = {
    "posts": "id,author,title,selftext,created_utc,num_comments,score,url,subreddit,link_flair_text",
    "comments": "id,author,body,created_utc,link_id,parent_id,score,subreddit,author_flair_text",
}
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
PAGE = 100
PAUSE = 0.7  # seconds between requests; the API asks clients to slow down when busy
START = 1104537600  # 2005-01-01, before Reddit existed


def get(url, tries=6):
    """Rate limits (API docs, read 18 Nov 2026): a couple of requests per second is fine; limits are dynamic.
    A 429 carries X-RateLimit-Reset (seconds until reset): wait that long, then retry."""
    last = None
    for i in range(tries):
        wait = 5 * (i + 1)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "research-script (course project)"})
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
            if body[:2] == b"\x1f\x8b":
                body = gzip.decompress(body)
            data = json.loads(body)
            if data.get("error"):
                raise RuntimeError(data["error"])
            return data.get("data") or []
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code == 429:
                wait = max(wait, int(e.headers.get("X-RateLimit-Reset") or 60) + 2)
                print(f"  rate limited, waiting {wait}s", flush=True)
        except (urllib.error.URLError, RuntimeError, TimeoutError, json.JSONDecodeError) as e:
            last = e
        time.sleep(wait)
    raise SystemExit(f"giving up after {tries} tries: {last} (rerun to resume)")


def resume_point(path):
    """Newest created_utc already saved, plus the ids saved at exactly that second.

    If the previous run was killed mid-write, the last gzip member is truncated. Reading stops there
    (EOFError / zlib error); the file is then rewritten with only the complete lines, so later appends
    and the analysis scripts see one clean stream. The lost tail is re-fetched by the resume itself."""
    if not path.exists():
        return START, set()
    newest, ids, good, broken = START, set(), [], False
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    broken = True  # a line cut off mid-write
                    break
                good.append(line if line.endswith("\n") else line + "\n")
                t = int(item["created_utc"])
                if t > newest:
                    newest, ids = t, {item["id"]}
                elif t == newest:
                    ids.add(item["id"])
    except (EOFError, OSError, zlib.error):
        broken = True
    if broken:
        tmp = path.with_suffix(".repair.gz")
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            f.writelines(good)
        tmp.replace(path)
        print(f"  repaired {path.name}: kept {len(good):,} complete items", flush=True)
    return newest, ids


def main(subreddit, kind):
    if kind not in FIELDS:
        raise SystemExit("kind must be 'posts' or 'comments'")
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / f"{subreddit}_{kind}.jsonl.gz"
    after, boundary_ids = resume_point(path)
    total = 0
    print(f"{subreddit} {kind}: starting after {time.strftime('%Y-%m-%d', time.gmtime(after))}", flush=True)
    while True:
        # after is exclusive, so step back one second and drop the ids already saved at the boundary
        params = {"subreddit": subreddit, "limit": PAGE, "sort": "asc",
                  "after": after - 1, "fields": FIELDS[kind]}
        page = get(API.format(kind=kind) + "?" + urllib.parse.urlencode(params))
        fresh = [x for x in page if not (int(x["created_utc"]) == after and x["id"] in boundary_ids)]
        if fresh:
            with gzip.open(path, "at", encoding="utf-8") as f:
                for x in fresh:
                    f.write(json.dumps(x, ensure_ascii=False) + "\n")
            total += len(fresh)
            newest = int(fresh[-1]["created_utc"])
            if newest != after:
                after, boundary_ids = newest, set()
            boundary_ids.update(x["id"] for x in fresh if int(x["created_utc"]) == after)
            if total % 5000 < len(fresh):
                print(f"  {total:,} new, up to {time.strftime('%Y-%m-%d', time.gmtime(after))}", flush=True)
        if len(page) < PAGE or not fresh:
            break
        time.sleep(PAUSE)
    print(f"{subreddit} {kind}: done, {total:,} new items -> {path}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
