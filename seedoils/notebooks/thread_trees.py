"""The shape of each post's reply tree, before and from 2024. Each post is a tree: the post is the root, a comment hangs under its parent (a comment or the post). Counts and shapes only; no text or names.
Data: seedoils/data/raw_haoyu (the 22 Nov rerun, the reference for every number). Cleaning, as in the rerun: a comment is dropped when it is a bot (seedoil_common.is_bot) or was deleted/removed (body '[deleted]'/'[removed]' or author '[deleted]') AND nobody replied to it,
repeated until no such leaf is left (as Reddit shows threads: a deleted comment with replies stays because it holds the tree together). Bots and deleted comments that still have replies stay as nodes but are not counted as authors.
Per thread (post with >= MIN_N comments left after cleaning; comments whose parent is missing hang under the post):
 size n; max depth; mean depth; share of comments that are top-level (direct replies to the post); share of comments at depth >= 4 ('deep chains'); structural virality = mean shortest-path distance between all pairs of nodes (Goel et al. 2016; low = broadcast, high = long chains);
 distinct authors / n; share of comments written by the 3 most active authors; share of reply links that are reciprocal (B answers A, and A answered B earlier in the thread).
Tree shape depends strongly on size, so threads are compared WITHIN size bins (n in 20-49, 50-99, 100-199, 200+) and periods by the post's date (before 2024 / from 2024); medians with bootstrap 95% intervals over threads.
Reference: structural virality of a random recursive tree (each comment attaches to a uniformly chosen earlier node) of the same size, 200 simulations per bin median.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python seedoils/notebooks/thread_trees.py   (aggregates only)"""
import glob
import gzip
import json
from collections import defaultdict

import numpy as np
import pandas as pd

from seedoil_common import is_bot  # shared bot rule: AutoModerator + names ending in 'bot'

MIN_N = 20; CUT = 1704067200; rng = np.random.default_rng(0)


PT = {}


def ptype(u):
    """text = the post's own reddit page (self post); media = i.redd.it, v.redd.it, reddit gallery; link = everything else (articles, YouTube, papers, empty)."""
    h = u.split("/")[2].lower().removeprefix("www.") if u.startswith("http") and u.count("/") >= 2 else ""
    if h in ("i.redd.it", "v.redd.it") or "reddit.com/gallery/" in u: return "image/video"
    if h.endswith("reddit.com"): return "text"
    return "link"


def load(sub):
    rows = []
    with gzip.open(glob.glob(f"seedoils/data/raw_haoyu/*{sub}_comments.jsonl.gz")[0], "rt", encoding="utf-8") as f:
        for l in f:
            x = json.loads(l); a = x.get("author") or ""; dead = x.get("body") in ("[deleted]", "[removed]") or a == "[deleted]"; rows.append((x["id"], a, x["link_id"], x["parent_id"], int(x["created_utc"]), dead or is_bot(a)))
    P = {}; PT.clear()
    with gzip.open(glob.glob(f"seedoils/data/raw_haoyu/*{sub}_posts.jsonl.gz")[0], "rt", encoding="utf-8") as f:
        for l in f:
            x = json.loads(l); P["t3_" + x["id"]] = int(x["created_utc"]); PT["t3_" + x["id"]] = ptype(x.get("url") or "")
    D = pd.DataFrame(rows, columns=["id", "a", "link", "parent", "t", "drop"]); n0 = len(D)
    while True:  # prune bot / deleted leaves until stable
        has_child = set(D.parent[D.parent.str.startswith("t1_")].str[3:])
        leaf = D["drop"] & ~D.id.isin(has_child)
        if not leaf.any(): break
        D = D[~leaf]
    print(f"r/{sub}: {n0:,} comments, {n0 - len(D):,} bot/deleted leaves pruned, {int((D['drop']).sum()):,} bot/deleted kept as connectors")
    # connectors are not authors: blank their name so author measures skip them
    D.loc[D["drop"], "a"] = ""
    return D, P


def metrics(g):
    ids = g.id.values; idx = {"root": 0}; [idx.__setitem__(i, k + 1) for k, i in enumerate(ids)]
    n = len(ids); par = np.zeros(n + 1, int); orphans = 0
    for k, (p) in enumerate(g.parent.values):
        p = p[3:] if p.startswith("t1_") else "root"
        if p in idx: par[k + 1] = idx[p]
        else: par[k + 1] = 0; orphans += 1
    order = np.argsort(np.concatenate([[0], g.t.values]), kind="stable")  # parents are earlier than children in time
    depth = np.zeros(n + 1, int)
    for v in order:
        if v: depth[v] = depth[par[v]] + 1 if par[v] != v else 1
    if (depth[1:] == 0).any():  # a child sorted before its parent (same second): resolve by iteration
        for _ in range(60):
            new = depth.copy()
            for v in range(1, n + 1): new[v] = new[par[v]] + 1
            if (new == depth).all(): break
            depth = new
    size = np.ones(n + 1, int)
    for v in order[::-1]:
        if v: size[par[v]] += size[v]
    N = n + 1; W = sum(size[v] * (N - size[v]) for v in range(1, N)); sv = W / (N * (N - 1) / 2)
    au = g.a.values; real = au[(au != "[deleted]") & (au != "")]; c = pd.Series(real).value_counts()
    recip = 0; replies = 0; seen = set(); first_reply = {}
    for k in order:
        if not k: continue
        pa = g.a.values[par[k] - 1] if par[k] else None
        if par[k] and pa and au[k - 1] and pa != "[deleted]" and au[k - 1] != "[deleted]" and pa != au[k - 1]:
            replies += 1
            if (au[k - 1], pa) in seen: pass
            if (pa, au[k - 1]) in seen: recip += 1
            seen.add((au[k - 1], pa))
    return {"n": n, "maxdepth": int(depth.max()), "meandepth": float(depth[1:].mean()), "toplevel": float((depth[1:] == 1).mean()), "deep": float((depth[1:] >= 4).mean()), "virality": sv,
            "authors_per_comment": len(c) / max(len(real), 1), "top3": float(c.head(3).sum() / max(len(real), 1)), "reciprocal": recip / replies if replies else np.nan, "orphans": orphans / n}


def rrt_virality(n, reps=200):
    out = []
    for _ in range(reps):
        par = np.zeros(n + 1, int); par[1:] = [rng.integers(0, k) for k in range(1, n + 1)]
        size = np.ones(n + 1, int)
        for v in range(n, 0, -1): size[par[v]] += size[v]
        N = n + 1; out.append(sum(size[v] * (N - size[v]) for v in range(1, N)) / (N * (N - 1) / 2))
    return float(np.median(out))


BINS = [(20, 49), (50, 99), (100, 199), (200, 10 ** 6)]
for sub in ("StopEatingSeedOils", "ScientificNutrition"):
    C, P = load(sub); rows = []
    for link, g in C.groupby("link"):
        if len(g) < MIN_N or link not in P: continue
        m = metrics(g.sort_values("t")); m["post_t"] = P[link]; m["ptype"] = PT[link]; rows.append(m)
    T = pd.DataFrame(rows); T["period"] = np.where(T.post_t >= CUT, "from 2024", "before 2024")
    print(f"\n===== r/{sub}: {len(T):,} threads with >= {MIN_N} comments ({(T.period == 'before 2024').sum():,} before 2024, {(T.period == 'from 2024').sum():,} from 2024); share of comments with a missing parent: {T.orphans.mean():.1%}")
    print(f"{'size bin':<10}{'period':<13}{'threads':>8}{'max depth':>10}{'mean depth':>11}{'top-level':>10}{'deep>=4':>9}{'virality':>9}{'(random)':>9}{'authors/cmt':>12}{'top3 share':>11}{'reciprocal':>11}")
    for lo, hi in BINS:
        rv = rrt_virality(int(np.median(T[(T.n >= lo) & (T.n <= hi)].n))) if ((T.n >= lo) & (T.n <= hi)).any() else np.nan
        for per in ("before 2024", "from 2024"):
            s = T[(T.n >= lo) & (T.n <= hi) & (T.period == per)]
            if len(s) < 5: continue
            f = lambda c: s[c].median()
            def ci(c):
                b = [np.median(rng.choice(s[c].dropna().values, len(s[c].dropna()))) for _ in range(300)]; return np.percentile(b, 2.5), np.percentile(b, 97.5)
            lab = f"{lo}-{hi}" if hi < 10 ** 6 else f"{lo}+"
            print(f"{lab:<10}{per:<13}{len(s):>8}{f('maxdepth'):>10.0f}{f('meandepth'):>11.2f}{f('toplevel'):>10.2f}{f('deep'):>9.2f}{f('virality'):>9.2f}{rv:>9.2f}{f('authors_per_comment'):>12.2f}{f('top3'):>11.2f}{f('reciprocal'):>11.2f}")
    # a regression-free summary: difference in structural virality (from 2024 minus before) per bin with 95% interval
    print("difference in median structural virality (from 2024 minus before 2024), 95% interval:")
    for lo, hi in BINS:
        a = T[(T.n >= lo) & (T.n <= hi) & (T.period == "before 2024")].virality.values; b = T[(T.n >= lo) & (T.n <= hi) & (T.period == "from 2024")].virality.values
        if len(a) < 5 or len(b) < 5: continue
        d = [np.median(rng.choice(b, len(b))) - np.median(rng.choice(a, len(a))) for _ in range(1000)]
        print(f"  n {lo}-{hi if hi < 10 ** 6 else '+'}: {np.median(b) - np.median(a):+.2f} [{np.percentile(d, 2.5):+.2f}, {np.percentile(d, 97.5):+.2f}]")

    # --- stratified by post type (added 26 Nov): does the flattening survive within post type? (the post-type mix changed: media posts rose from 11% to 27% of posts)
    print(f"\n--- r/{sub}: by post type (thread counts; medians within size bins 20-99 and 100+; virality difference from 2024 minus before, 95% interval)")
    print(f"{'type':<12}{'size bin':<9}{'period':<13}{'threads':>8}{'mean depth':>11}{'top-level':>10}{'deep>=4':>9}{'virality':>9}{'authors/cmt':>12}")
    for pt in ("text", "image/video", "link"):
        for lo, hi, lab in ((20, 99, "20-99"), (100, 10 ** 6, "100+")):
            row = {}
            for per in ("before 2024", "from 2024"):
                q = T[(T.ptype == pt) & (T.n >= lo) & (T.n <= hi) & (T.period == per)]; row[per] = q
                if len(q) >= 5: print(f"{pt:<12}{lab:<9}{per:<13}{len(q):>8}{q.meandepth.median():>11.2f}{q.toplevel.median():>10.2f}{q.deep.median():>9.2f}{q.virality.median():>9.2f}{q.authors_per_comment.median():>12.2f}")
                else: print(f"{pt:<12}{lab:<9}{per:<13}{len(q):>8}   (< 5 threads)")
            a, b = row["before 2024"].virality.values, row["from 2024"].virality.values
            if len(a) >= 5 and len(b) >= 5:
                d = [np.median(rng.choice(b, len(b))) - np.median(rng.choice(a, len(a))) for _ in range(1000)]
                print(f"{'':<12}{'':<9}virality difference: {np.median(b) - np.median(a):+.2f} [{np.percentile(d, 2.5):+.2f}, {np.percentile(d, 97.5):+.2f}]")
    print("post-type mix of the threads (share of threads with >= 20 comments):", T.groupby("period").ptype.value_counts(normalize=True).round(2).to_dict())
