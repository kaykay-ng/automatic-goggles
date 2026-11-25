"""Null models for the two co-citation networks: is their clustering and side segregation more than chance at their density?

Run from final_project/ after cocitation_network.py (slow; run in the background):
  ./.venv-nlp/bin/python seedoils/notebooks/cocitation_null.py [REPS] [--time-only]
  -> seedoils/data/processed/cocite_null_summary.txt, cocite_null_runs.csv

Why: modularity depends on density. The scholarly network is sparse (~8 links per paper), the Reddit network dense (~170), and sparse
random graphs already reach high modularity. So the observed values are compared with randomised versions of the SAME network.

Null 1 (structure), degree-preserving rewiring: double edge swaps (nswap = SWAPS_PER_EDGE x edges) keep every paper's number of links and
destroy everything else. For the weighted Reddit network the original edge weights are shuffled onto the rewired edges (keeps the weight
distribution; strengths only approximately). On each randomised graph: Louvain modularity (seed varies) and side assortativity.
Null 2 (labels), side-label permutation: keep the real network, shuffle which papers are SESO / SciNut / both. Tests whether same-side papers
link to each other more than chance given the real structure.
Reported: observed value, null mean and SD, z = (observed - mean) / SD, and the observed value minus the null mean.
"""
import csv
import random
import statistics
import sys
import time
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
SWAPS_PER_EDGE = 2
LABEL_REPS = 200


def load(kind, side):
    G = nx.Graph()
    with open(PROC / f"cocite_{kind}_edges.csv") as f:
        for r in csv.DictReader(f):
            G.add_edge(r["source"], r["target"], weight=float(r["weight"]))
    nx.set_node_attributes(G, {n: side[n] for n in G}, "side")
    return G


def louvain_Q(G, seed):
    c = nx.community.louvain_communities(G, weight="weight", seed=seed)
    return nx.community.modularity(G, c, weight="weight"), len(c)


def rewire(G, seed):
    H = G.copy()
    nx.double_edge_swap(H, nswap=SWAPS_PER_EDGE * H.number_of_edges(), max_tries=SWAPS_PER_EDGE * H.number_of_edges() * 20, seed=seed)
    w = [d["weight"] for _, _, d in G.edges(data=True)]
    random.Random(seed).shuffle(w)
    for (a, b), x in zip(H.edges(), w):
        H[a][b]["weight"] = x
    return H


def z(obs, vals):
    m, s = statistics.mean(vals), statistics.stdev(vals) if len(vals) > 1 else float("nan")
    return m, s, (obs - m) / s if s else float("nan")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    reps = int(args[0]) if args else 20
    time_only = "--time-only" in sys.argv
    side = {}
    with open(PROC / "cocite_nodes.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            side[r["openalex_id"]] = r["side"]
    lines, runs = [], []
    for kind in ("scholarly", "reddit"):
        G = load(kind, side)
        Q0, k0 = louvain_Q(G, 42)
        r0 = nx.attribute_assortativity_coefficient(G, "side")
        lines.append(f"\n== {kind}: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges, mean degree {2 * G.number_of_edges() / G.number_of_nodes():.1f}")
        lines.append(f"  observed: modularity {Q0:.3f} ({k0} communities), side assortativity {r0:.3f}")
        if time_only:
            t = time.time()
            H = rewire(G, 1)
            t1 = time.time() - t
            louvain_Q(H, 1)
            print(f"{kind}: one rewiring {t1:.0f}s, rewiring + Louvain {time.time() - t:.0f}s", flush=True)
            continue
        Qs, rs = [], []
        for i in range(reps):
            H = rewire(G, 1000 + i)
            q, k = louvain_Q(H, 1000 + i)
            r = nx.attribute_assortativity_coefficient(H, "side")
            Qs.append(q); rs.append(r)
            runs.append((kind, "rewire", i, round(q, 4), k, round(r, 4)))
            print(f"  {kind} rewire {i + 1}/{reps}: Q {q:.3f}, assortativity {r:.3f}", flush=True)
        m, s, zz = z(Q0, Qs)
        lines.append(f"  NULL 1 rewiring ({reps} reps): modularity {m:.3f} +/- {s:.3f} -> z = {zz:.1f}, observed - null = {Q0 - m:+.3f}")
        m, s, zz = z(r0, rs)
        lines.append(f"                              side assortativity {m:.3f} +/- {s:.3f} -> z = {zz:.1f}")
        labels = [side[n] for n in G]
        rl = []
        rng = random.Random(7)
        for i in range(LABEL_REPS):
            rng.shuffle(labels)
            nx.set_node_attributes(G, dict(zip(G.nodes(), labels)), "side_perm")
            rl.append(nx.attribute_assortativity_coefficient(G, "side_perm"))
        m, s, zz = z(r0, rl)
        lines.append(f"  NULL 2 label shuffle ({LABEL_REPS} reps): side assortativity {m:.3f} +/- {s:.3f} -> z = {zz:.1f}")
    if time_only:
        return
    with open(PROC / "cocite_null_runs.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["network", "null", "rep", "modularity", "n_communities", "side_assortativity"])
        w.writerows(runs)
    text = "\n".join(lines)
    (PROC / "cocite_null_summary.txt").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
