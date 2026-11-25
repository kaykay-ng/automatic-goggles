"""Subreddit co-commenter network around the seed-oil debate.

Input:  seedoils/data/processed/seed_authors.csv          (from fetch_author_histories.py select)
        seedoils/data/raw/author_subreddit_counts.jsonl.gz  (from fetch_author_histories.py fetch)
Output: seedoils/data/processed/cocommenter_<period>_nodes.csv, _edges.csv, _summary.txt

Construction
1. Bipartite graph: seed author -- subreddit, kept when the author has >= --min-comments comments there
   (in the chosen period: all, pre2024 or from2024).
2. Subreddits kept when >= --min-authors seed authors post there.
3. One-mode projection onto subreddits. Edge weight = lift = S_ij * N / (k_i * k_j), where S_ij is the number of
   shared authors, k_i the authors in subreddit i and N all authors in the sample. Lift 1 = the overlap expected if
   authors picked subreddits independently. Kept: lift > 1 and S_ij >= --min-shared. Lift damps huge general
   subreddits (AskReddit etc.) that every author touches.
4. Louvain communities (networkx, weighted by lift, fixed seed), weighted PageRank, betweenness on distance 1/lift.
5. Lean of each subreddit: of its seed authors who belong to exactly one of StopEatingSeedOils / ScientificNutrition,
   the share from StopEatingSeedOils after dividing by each camp's size (so the bigger camp does not win by size):
   lean = (s - c) / (s + c), s and c the camp-size-normalised counts; +1 = only seed-oil commenters, -1 = only ScientificNutrition.

Caveat: the sample is the neighbourhood of the seed subreddits, not Reddit as a whole. The seed subreddits themselves
are in every author's list by construction; they are kept as labelled anchors but excluded from the lift statistics
with --drop-seeds.
"""

import argparse
import csv
import gzip
import json
import math
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
SEESO, SCINUT = "StopEatingSeedOils", "ScientificNutrition"
SEEDS = {SEESO, SCINUT}  # r/carnivore is no longer a seed (22 Nov): it is an ordinary subreddit here


def read_counts(counts_file):
    """Lines of the author-count file(s). counts_file may be a single file or a glob (the default reads the main file plus the
    parallel shard files). A file cut off mid-write yields its complete lines; duplicate authors across files are dropped."""
    paths = sorted(Path(counts_file).parent.glob(Path(counts_file).name)) if any(ch in str(counts_file) for ch in "*?[") else [Path(counts_file)]
    seen = set()
    for p in paths:
        try:
            with gzip.open(p, "rt", encoding="utf-8") as f:
                for line in f:
                    try:
                        a = json.loads(line)["author"]
                    except json.JSONDecodeError:
                        continue
                    if a not in seen:
                        seen.add(a)
                        yield line
        except (EOFError, OSError):
            continue


def load(seed_file, counts_file, period, min_comments):
    camps = defaultdict(set)
    with open(seed_file) as f:
        for r in csv.DictReader(f):
            camps[r["author"]].add(r["seed_subreddit"])
    subs_of = {}
    for line in read_counts(counts_file):
            rec = json.loads(line)
            if rec["author"] not in camps:
                continue
            total = Counter()
            for p, c in rec["counts"].items():
                if period == "all" or p == period:
                    total.update(c)
            keep = {s for s, n in total.items() if n >= min_comments}
            if keep:
                subs_of[rec["author"]] = keep
    return camps, subs_of


def build(args):
    camps, subs_of = load(args.seeds, args.counts, args.period, args.min_comments)
    authors_in = defaultdict(set)
    for a, subs in subs_of.items():
        for s in subs:
            authors_in[s].add(a)
    keep = {s for s, A in authors_in.items() if len(A) >= args.min_authors}
    if args.drop_seeds:
        keep -= SEEDS
    N = len(subs_of)
    shared = Counter()
    for a, subs in subs_of.items():
        for i, j in combinations(sorted(subs & keep), 2):
            shared[i, j] += 1

    G = nx.Graph()
    for s in keep:
        G.add_node(s, n_authors=len(authors_in[s]))
    for (i, j), S in shared.items():
        lift = S * N / (len(authors_in[i]) * len(authors_in[j]))
        if S >= args.min_shared and lift > 1:
            G.add_edge(i, j, shared=S, lift=lift, distance=1 / lift)
    G.remove_nodes_from([n for n in list(G) if G.degree(n) == 0])

    comms = nx.community.louvain_communities(G, weight="lift", seed=42)
    Q = nx.community.modularity(G, comms, weight="lift")
    comm_of = {n: k for k, c in enumerate(sorted(comms, key=len, reverse=True)) for n in c}
    pr = nx.pagerank(G, weight="lift")
    bt = nx.betweenness_centrality(G, weight="distance")

    def camp(a):
        """StopEatingSeedOils or ScientificNutrition if the author was seeded from exactly one of them, else None."""
        two = camps[a] & {SEESO, SCINUT}
        return next(iter(two)) if len(two) == 1 else None

    camp_size = Counter(camp(a) for a in subs_of if camp(a))
    rows = []
    for s in G:
        cs = Counter(camp(a) for a in authors_in[s] if camp(a))
        se = cs[SEESO] / camp_size[SEESO] if camp_size[SEESO] else 0
        sc = cs[SCINUT] / camp_size[SCINUT] if camp_size[SCINUT] else 0
        lean = (se - sc) / (se + sc) if se + sc else float("nan")
        rows.append({"subreddit": s, "n_authors": len(authors_in[s]), "community": comm_of[s], "pagerank": round(pr[s], 6),
                     "betweenness": round(bt[s], 6), "n_seso_only": cs[SEESO], "n_scinut_only": cs[SCINUT],
                     "lean_seso_vs_scinut": round(lean, 3) if not math.isnan(lean) else ""})

    PROC.mkdir(parents=True, exist_ok=True)
    stem = PROC / f"cocommenter_{args.period}"
    with open(f"{stem}_nodes.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["community"], -r["pagerank"])))
    with open(f"{stem}_edges.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source", "target", "shared_authors", "lift"])
        for i, j, d in G.edges(data=True):
            w.writerow([i, j, d["shared"], round(d["lift"], 3)])

    lines = [f"period={args.period} authors={N:,} camp sizes (single-camp) {dict(camp_size)}",
             f"subreddits kept={G.number_of_nodes():,} edges={G.number_of_edges():,} density={nx.density(G):.4f}",
             f"Louvain communities={len(comms)} modularity={Q:.3f}"]
    by = defaultdict(list)
    for r in rows:
        by[r["community"]].append(r)
    for k in sorted(by):
        rs = sorted(by[k], key=lambda r: -r["pagerank"])
        leans = [r["lean_seso_vs_scinut"] for r in rs if r["lean_seso_vs_scinut"] != ""]
        mean_lean = sum(leans) / len(leans) if leans else float("nan")
        lines.append(f"\ncommunity {k}: {len(rs)} subreddits, mean lean {mean_lean:+.2f}")
        lines.append("  top by PageRank: " + ", ".join(f"{r['subreddit']} ({r['lean_seso_vs_scinut']})" for r in rs[:12]))
    top_bt = sorted(rows, key=lambda r: -r["betweenness"])[:10]
    lines.append("\nbridges (betweenness): " + ", ".join(f"{r['subreddit']} c{r['community']}" for r in top_bt))
    open(f"{stem}_summary.txt", "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", default=str(PROC / "seed_authors.csv"))
    ap.add_argument("--counts", default=str(RAW / "author_subreddit_counts*.jsonl.gz"), help="file or glob (main file + shard files)")
    ap.add_argument("--period", choices=["all", "pre2024", "from2024"], default="all")
    ap.add_argument("--min-comments", type=int, default=3)
    ap.add_argument("--min-authors", type=int, default=25)
    ap.add_argument("--min-shared", type=int, default=5)
    ap.add_argument("--drop-seeds", action="store_true")
    build(ap.parse_args())
