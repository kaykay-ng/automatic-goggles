"""Where else do seed-oil commenters post? Build the author x subreddit table for the co-commenter network.

Step 1 (select): pick seed authors from the downloaded comments of the core subreddits
    python seedoils/notebooks/fetch_author_histories.py select --min-comments 5 --top 1500
  -> seedoils/data/processed/seed_authors.csv  (author, seed_subreddit, n_comments_in_seed, first_utc, last_utc)
  An author active in several seed subreddits gets one row per seed subreddit.
  Excluded: [deleted], AutoModerator and accounts whose name ends in 'bot'.

Step 2 (fetch): for each seed author, count their posts + comments per subreddit over their WHOLE history,
split at PERIOD_SPLIT, using Arctic Shift's /api/users/interactions/subreddits (one request per author per period,
so 2 per author, and no recency cap).
    python seedoils/notebooks/fetch_author_histories.py fetch [--authors FILE]
  -> seedoils/data/raw/author_subreddit_counts.jsonl.gz  (one line per author:
     {"author", "n", "counts": {"pre2024": {"<subreddit>": n}, "from2024": {...}}})
  Counts are interactions (posts + comments, weight 1 each). Resumable: authors already in the output are skipped.

Speed (19 Nov): this endpoint answers slowly (~12 s per author for the 2 requests), so 4,292 authors take ~14 h in one process.
Run shards in parallel, e.g. 4 processes with --shard 0/4 ... 3/4 (together < 1 request per second).

Rate limits (API docs, read 18 Nov 2026): "a couple requests per second" is fine; limits are dynamic, based on server
load and query cost. A 429 response carries X-RateLimit-Reset (seconds); get() waits that long and retries.
The docs ask heavy users to prefer the monthly dumps.

Network construction from this table lives in build_cocommenter_network.py.
"""

import argparse
import csv
import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
SEEDS = ["StopEatingSeedOils", "ScientificNutrition", "carnivore"]
API = "https://arctic-shift.photon-reddit.com/api/users/interactions/subreddits"
PERIOD_SPLIT = "2024-01-01"  # before vs during the RFK Jr./MAHA surge
PAUSE = 0.8
SKIP = {"[deleted]", "AutoModerator"}


def get(url, tries=6):
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
            if e.code == 429:  # rate limited: wait until the window resets
                wait = max(wait, int(e.headers.get("X-RateLimit-Reset") or 60) + 2)
                print(f"  rate limited, waiting {wait}s", flush=True)
        except (urllib.error.URLError, RuntimeError, TimeoutError, json.JSONDecodeError) as e:
            last = e
        time.sleep(wait)
    raise RuntimeError(f"giving up after {tries} tries: {last}")


def select(min_comments, top, subreddits):
    PROC.mkdir(parents=True, exist_ok=True)
    rows = []
    for sub in subreddits:
        path = RAW / f"{sub}_comments.jsonl.gz"
        if not path.exists():
            print(f"missing {path.name}; download it first with fetch_arctic_shift.py")
            continue
        n, first, last = Counter(), {}, {}
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                c = json.loads(line)
                a, t = c.get("author"), int(c["created_utc"])
                if not a or a in SKIP or a.lower().endswith("bot"):
                    continue
                n[a] += 1
                first[a] = min(first.get(a, t), t)
                last[a] = max(last.get(a, t), t)
        keep = [(a, k) for a, k in n.most_common() if k >= min_comments][:top]
        print(f"{sub}: {len(n):,} commenters, {sum(k >= min_comments for k in n.values()):,} with >= {min_comments}, keeping {len(keep):,}")
        rows += [(a, sub, k, first[a], last[a]) for a, k in keep]
    out = PROC / "seed_authors.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["author", "seed_subreddit", "n_comments_in_seed", "first_utc", "last_utc"])
        w.writerows(rows)
    print(f"{len(rows):,} rows, {len({r[0] for r in rows}):,} distinct authors -> {out}")


def fetch(authors_file, out, shard=None):
    authors = []
    with open(authors_file) as f:
        for r in csv.DictReader(f):
            if r["author"] not in authors:
                authors.append(r["author"])
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()  # authors already fetched in ANY output file (main file or shard files), so shards never repeat work
    for p in out.parent.glob("author_subreddit_counts*.jsonl.gz"):
        try:
            with gzip.open(p, "rt", encoding="utf-8") as f:
                for line in f:
                    try:
                        done.add(json.loads(line)["author"])
                    except json.JSONDecodeError:
                        pass
        except (EOFError, OSError):
            pass  # a file cut off mid-write: the complete lines before the cut were read
    todo = [a for a in authors if a not in done]
    if shard:
        k, n_shards = (int(x) for x in shard.split("/"))
        todo = [a for j, a in enumerate(todo) if j % n_shards == k]
    print(f"{len(authors):,} authors, {len(done):,} done, {len(todo):,} to fetch" + (f" (shard {shard})" if shard else ""), flush=True)
    windows = {"pre2024": {"before": PERIOD_SPLIT}, "from2024": {"after": PERIOD_SPLIT}}
    for i, a in enumerate(todo, 1):
        counts = {}
        try:
            for name, bound in windows.items():
                params = {"author": a, "limit": "", **bound}  # limit= (empty) means no limit
                counts[name] = {r["subreddit"]: r["count"] for r in get(API + "?" + urllib.parse.urlencode(params))}
                time.sleep(PAUSE)
        except RuntimeError as e:
            print(f"  skip {a}: {e}", flush=True)
            continue
        n = sum(sum(c.values()) for c in counts.values())
        with gzip.open(out, "at", encoding="utf-8") as f:
            f.write(json.dumps({"author": a, "n": n, "counts": counts}) + "\n")
        if i % 50 == 0:
            print(f"  {i:,}/{len(todo):,}", flush=True)
        time.sleep(PAUSE)
    print(f"done -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("select")
    s.add_argument("--min-comments", type=int, default=5)
    s.add_argument("--top", type=int, default=1500, help="max authors per seed subreddit, most active first")
    s.add_argument("--subreddits", nargs="+", default=SEEDS,
                   help="seed subreddits to read (default: all three); use while other downloads are still writing")
    f = sp.add_parser("fetch")
    f.add_argument("--authors", default=str(PROC / "seed_authors.csv"))
    f.add_argument("--out", default=None, help="default: author_subreddit_counts.jsonl.gz, or ..._shard<k>.jsonl.gz with --shard")
    f.add_argument("--shard", default=None, help="k/n: fetch only every n-th remaining author starting at k (run n processes in parallel; "
                                                 "each writes its own file; all files are read when skipping done authors and when building)")
    args = ap.parse_args()
    if args.cmd == "select":
        select(args.min_comments, args.top, args.subreddits)
    else:
        k = args.shard.split("/")[0] if args.shard else None
        out = args.out or str(RAW / (f"author_subreddit_counts_shard{k}.jsonl.gz" if k is not None else "author_subreddit_counts.jsonl.gz"))
        fetch(args.authors, out, args.shard)
