"""Reply network among the 1,500 heaviest r/StopEatingSeedOils commenters (OLD = first comment before 2024, NEW = first from 2024; seed_authors.csv).
Edge A -> B (weight = count) when A's comment is a direct reply to B's comment or post, both in the heavy set, A != B. Built from the downloaded comments and posts.
Analyses (undirected weighted graph unless noted): size/density, mixing between cohorts and cohort assortativity against a label-shuffle null (200 shuffles), Louvain (20 seeds, best modularity),
directed PageRank, betweenness (distance = 1/weight), shortest paths within / across cohorts. Periods: 'all' and 'from2024' (replies written from 2024, when both cohorts are active).
Aggregates only are printed/written (no usernames). Run from final_project/:  ../.venv/bin/python seedoils/notebooks/network_heavy.py [period]"""
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
SPLIT = 1704067200
SUB = "StopEatingSeedOils"
A = pd.read_csv(PROC / "seed_authors.csv"); A = A[A.seed_subreddit == SUB]
cohort = {r.author: ("new" if r.first_utc >= SPLIT else "old") for r in A.itertuples()}


def load():
    author_of, rows = {}, []
    for line in gzip.open(RAW / f"{SUB}_posts.jsonl.gz", "rt"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        author_of["t3_" + d["id"]] = d.get("author")
    cm = []
    for line in gzip.open(RAW / f"{SUB}_comments.jsonl.gz", "rt"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        author_of["t1_" + d["id"]] = d.get("author"); cm.append((d.get("author"), d["parent_id"], int(d["created_utc"])))
    for a, p, t in cm:
        b = author_of.get(p)
        if a in cohort and b in cohort and a != b:
            rows.append((a, b, t))
    return rows


def build(rows, period):
    ds = nx.DiGraph()
    ds.add_nodes_from(cohort)
    c = Counter((a, b) for a, b, t in rows if period == "all" or t >= SPLIT)
    for (a, b), w in c.items():
        ds.add_edge(a, b, weight=w)
    return ds


def analyse(ds, period):
    nx.set_node_attributes(ds, cohort, "cohort")
    G = nx.Graph()
    G.add_nodes_from(ds.nodes(data=True))
    for a, b, d in ds.edges(data=True):
        w = d["weight"] + (G[a][b]["weight"] if G.has_edge(a, b) else 0)
        G.add_edge(a, b, weight=w)
    G.remove_nodes_from([n for n in list(G) if G.degree(n) == 0])
    lcc = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    lab = {n: cohort[n] for n in G}
    print(f"\n===== period {period}: {G.number_of_nodes()} commenters with a reply tie (of 1,500), {G.number_of_edges()} ties, {sum(d['weight'] for *_, d in G.edges(data=True)):,} replies; "
          f"largest component {lcc.number_of_nodes()}; density {nx.density(G):.4f}; new share {np.mean([v == 'new' for v in lab.values()]):.2f}")
    # mixing
    tie = Counter(tuple(sorted((lab[a], lab[b]))) for a, b in G.edges())
    tot = sum(tie.values()); print("ties by cohort pair:", {k: f"{v / tot:.1%}" for k, v in tie.items()})
    obs = nx.attribute_assortativity_coefficient(G, "cohort") if False else nx.attribute_assortativity_coefficient(nx.relabel_nodes(G, {n: n for n in G}), "cohort")
    rng = np.random.default_rng(1); nodes = list(G); vals = [lab[n] for n in nodes]; nul = []
    for _ in range(200):
        sh = rng.permutation(vals)
        for n, v in zip(nodes, sh):
            G.nodes[n]["sh"] = v
        nul.append(nx.attribute_assortativity_coefficient(G, "sh"))
    print(f"cohort assortativity {obs:.3f} vs shuffled labels {np.mean(nul):.3f} (sd {np.std(nul):.3f}; min {min(nul):.3f}, max {max(nul):.3f})")
    # communities
    from networkx.algorithms.community import louvain_communities, modularity
    best = max((louvain_communities(G, weight="weight", seed=s) for s in range(20)), key=lambda c: modularity(G, c, weight="weight"))
    print(f"Louvain: {len(best)} communities, modularity {modularity(G, best, weight='weight'):.3f}")
    for i, c in enumerate(sorted(best, key=len, reverse=True)[:6]):
        print(f"   community {i}: {len(c)} members, {np.mean([lab[n] == 'new' for n in c]):.0%} new")
    # centralities
    pr = nx.pagerank(ds.subgraph(G.nodes), weight="weight")
    for n in G.nodes():
        G.nodes[n]["d"] = 1
    H = lcc.copy()
    for a, b, d in H.edges(data=True):
        d["dist"] = 1 / d["weight"]
    bt = nx.betweenness_centrality(H, k=min(500, len(H)), weight="dist", seed=1, normalized=True)
    def top(score, name, n=30):
        t = sorted(score, key=score.get, reverse=True)[:n]
        print(f"top {n} by {name}: {np.mean([lab[x] == 'new' for x in t]):.0%} new (cohort share {np.mean([v == 'new' for v in lab.values()]):.0%})")
    top(pr, "PageRank (replied-to)"); top(bt, "betweenness")
    indeg = dict(ds.in_degree(weight="weight")); outdeg = dict(ds.out_degree(weight="weight"))
    for g in ("old", "new"):
        ns = [n for n in G if lab[n] == g]
        print(f"{g}: median replies received {np.median([indeg[n] for n in ns]):.0f}, written {np.median([outdeg[n] for n in ns]):.0f}; share of ns with a tie {len(ns) / sum(1 for n in cohort if cohort[n] == g):.0%}")
    # paths
    rs = np.random.default_rng(2); L = list(H)
    same, cross = [], []
    for _ in range(400):
        a, b = rs.choice(len(L), 2, replace=False); a, b = L[a], L[b]
        d = nx.shortest_path_length(H, a, b)
        (same if lab[a] == lab[b] else cross).append(d)
    print(f"average shortest path (unweighted, largest component): same-cohort pairs {np.mean(same):.2f}, cross-cohort pairs {np.mean(cross):.2f}; diameter estimate {max(same + cross)}")
    return pd.DataFrame({"cohort": [lab[n] for n in H], "pagerank": [pr[n] for n in H], "betweenness": [bt[n] for n in H], "degree": [H.degree(n) for n in H]})


if __name__ == "__main__":
    rows = load()
    print(f"{len(rows):,} replies between heavy commenters (all time)")
    for per in (sys.argv[1:] or ["all", "from2024"]):
        df = analyse(build(rows, per), per)
        df.to_csv(PROC / f"network_heavy_{per}_nodes.csv", index=False)
