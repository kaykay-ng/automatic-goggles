"""Co-citation networks of the papers cited in r/StopEatingSeedOils and r/ScientificNutrition.

Run from final_project/ after cited_papers.py fetch:
  ../.venv/bin/python seedoils/notebooks/cocitation_network.py
  -> seedoils/data/processed/cocite_nodes.csv, cocite_reddit_edges.csv, cocite_scholarly_edges.csv, cocite_summary.txt

Nodes: OpenAlex works cited by >= MIN_USERS distinct Reddit users (both subreddits pooled; [deleted] excluded).
Two edge sets on the SAME nodes:
  reddit    : works linked when the same user cited both. Weight = sum over users of 1 / (k_u - 1), k_u = number of node works the user
              cited (Newman's collaboration weighting), so one user citing 1,000 papers does not dominate.
  scholarly : works linked when one references the other (OpenAlex referenced_works), undirected, unweighted. Independent of Reddit.
Node attributes: users_SESO, users_SciNut, lean = (s - c) / (s + c) with s, c the citing-user counts divided by each side's total
number of citing users (+1 = only seed-oil users cite it, -1 = only ScientificNutrition users), side label (SESO / SciNut / both),
study design from MeSH (as in cited_papers.py), year, OpenAlex cited_by_count.
Per network: Louvain (seed 42) communities with modularity, mean lean and design mix per community, assortativity of the side label,
and the agreement (adjusted mutual information) between the two partitions.
"""
from seedoil_common import is_bot, not_bot  # shared bot rule: AutoModerator + names ending in 'bot'
import csv
import gzip
import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import networkx as nx

sys.path.insert(0, str(Path(__file__).parent))
from cited_papers import design  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
SESO, SCINUT = "StopEatingSeedOils", "ScientificNutrition"
MIN_USERS = 2


def load():
    works = {}
    with gzip.open(RAW / "openalex_works.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            for k in rec["_queried"]:
                works[tuple(k)] = rec["work"]
    cited_by = defaultdict(lambda: {SESO: set(), SCINUT: set()})
    meta = {}
    with gzip.open(PROC / "citations.csv.gz", "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            w = works.get((r["id_type"], r["id_value"]))
            if not w or r["author"] in ("", "[deleted]") or is_bot(r["author"]):
                continue
            cited_by[w["id"]][r["subreddit"]].add(r["author"])
            meta[w["id"]] = w
    return cited_by, meta


def lean_and_side(users, totals):
    s = len(users[SESO]) / totals[SESO]
    c = len(users[SCINUT]) / totals[SCINUT]
    side = "both" if users[SESO] and users[SCINUT] else ("SESO" if users[SESO] else "SciNut")
    return round((s - c) / (s + c), 3), side


def describe(G, name, attrs, lines):
    comms = nx.community.louvain_communities(G, weight="weight", seed=42)
    comms = sorted(comms, key=len, reverse=True)
    Q = nx.community.modularity(G, comms, weight="weight")
    comm_of = {n: i for i, c in enumerate(comms) for n in c}
    r = nx.attribute_assortativity_coefficient(G, "side")
    lines.append(f"\n== {name}: nodes with edges {G.number_of_nodes():,}, edges {G.number_of_edges():,}, "
                 f"Louvain communities {len(comms)} (>= 20 works: {sum(len(c) >= 20 for c in comms)}), modularity {Q:.3f}, "
                 f"side assortativity {r:.3f}")
    for i, c in enumerate(comms):
        if len(c) < 20:
            continue
        L = [attrs[n]["lean"] for n in c]
        sides = Counter(attrs[n]["side"] for n in c)
        des = Counter(attrs[n]["design"] for n in c)
        top = sorted(c, key=lambda n: -(attrs[n]["users_SESO"] + attrs[n]["users_SciNut"]))[:5]
        lines.append(f"  c{i}: {len(c)} works, mean lean {sum(L) / len(L):+.2f}, sides {dict(sides)}, "
                     f"animal {des['animal'] / len(c):.0%}, humans-only {des['humans only'] / len(c):.0%}")
        for n in top:
            a = attrs[n]
            lines.append(f"      [{a['users_SESO']} SESO / {a['users_SciNut']} SciNut] {a['title'][:80]} ({a['year']})")
    return comm_of


def main():
    cited_by, meta = load()
    totals = {s: len({u for v in cited_by.values() for u in v[s]}) for s in (SESO, SCINUT)}
    nodes = [w for w, v in cited_by.items() if len(v[SESO] | v[SCINUT]) >= MIN_USERS]
    keep = set(nodes)
    attrs = {}
    for w in nodes:
        lean, side = lean_and_side(cited_by[w], totals)
        m = meta[w]
        attrs[w] = {"lean": lean, "side": side, "users_SESO": len(cited_by[w][SESO]), "users_SciNut": len(cited_by[w][SCINUT]),
                    "design": design(m), "year": m.get("publication_year"), "cited_by_count": m.get("cited_by_count"),
                    "title": (m.get("title") or "?").replace("\n", " ")}

    # Reddit co-citation, Newman-weighted
    papers_of = defaultdict(set)
    for w in nodes:
        for s in (SESO, SCINUT):
            for u in cited_by[w][s]:
                papers_of[u].add(w)
    R = nx.Graph()
    R.add_nodes_from((w, attrs[w]) for w in nodes)
    for u, P in papers_of.items():
        if len(P) < 2:
            continue
        wt = 1 / (len(P) - 1)
        for a, b in combinations(sorted(P), 2):
            R.add_edge(a, b, weight=R[a][b]["weight"] + wt if R.has_edge(a, b) else wt)
    R.remove_nodes_from([n for n in list(R) if R.degree(n) == 0])

    # scholarly: direct citations among the node works
    S = nx.Graph()
    S.add_nodes_from((w, attrs[w]) for w in nodes)
    for w in nodes:
        for ref in meta[w].get("referenced_works") or []:
            if ref in keep and ref != w:
                S.add_edge(w, ref, weight=1)
    S.remove_nodes_from([n for n in list(S) if S.degree(n) == 0])

    sides = Counter(a["side"] for a in attrs.values())
    lines = [f"works cited by >= {MIN_USERS} users: {len(nodes):,} {dict(sides)}; citing users SESO {totals[SESO]:,}, SciNut {totals[SCINUT]:,}; "
             f"users citing in both: {len({u for u in papers_of if any(u in cited_by[w][SESO] for w in papers_of[u]) and any(u in cited_by[w][SCINUT] for w in papers_of[u])})}"]
    cR = describe(R, "Reddit co-citation (same user cited both)", attrs, lines)
    cS = describe(S, "Scholarly citation (one references the other)", attrs, lines)

    common = [n for n in cR if n in cS]
    try:
        from sklearn.metrics import adjusted_mutual_info_score
        ami = adjusted_mutual_info_score([cR[n] for n in common], [cS[n] for n in common])
        lines.append(f"\nagreement of the two partitions on {len(common):,} shared nodes: AMI {ami:.3f} (0 = unrelated, 1 = identical)")
    except ImportError:
        pass
    bt = nx.betweenness_centrality(R, weight=None, k=min(500, len(R)), seed=42)
    by_side = defaultdict(list)
    for n, b in bt.items():
        by_side[attrs[n]["side"]].append(b)
    lines.append("Reddit network betweenness (sampled, k=500), mean by side: " +
                 ", ".join(f"{s} {sum(v) / len(v):.4f} (n={len(v)})" for s, v in sorted(by_side.items())))
    top_b = sorted(bt, key=bt.get, reverse=True)[:8]
    lines.append("  top bridges: " + "; ".join(f"{attrs[n]['title'][:60]} ({attrs[n]['side']})" for n in top_b))

    with open(PROC / "cocite_nodes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        cols = ["openalex_id", "title", "year", "design", "side", "lean", "users_SESO", "users_SciNut", "cited_by_count",
                "community_reddit", "community_scholarly", "betweenness_reddit"]
        w.writerow(cols)
        for n in nodes:
            a = attrs[n]
            w.writerow([n, a["title"], a["year"], a["design"], a["side"], a["lean"], a["users_SESO"], a["users_SciNut"], a["cited_by_count"],
                        cR.get(n, ""), cS.get(n, ""), round(bt.get(n, 0), 6)])
    for G, nm in ((R, "reddit"), (S, "scholarly")):
        with open(PROC / f"cocite_{nm}_edges.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["source", "target", "weight"])
            for a, b, d in G.edges(data=True):
                w.writerow([a, b, round(d["weight"], 4)])
    text = "\n".join(lines)
    (PROC / "cocite_summary.txt").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
