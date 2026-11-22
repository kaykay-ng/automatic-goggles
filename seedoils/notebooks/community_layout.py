"""Display layout for Figures 2 and 3 on the ~130-topic backbone. The first export used networkx's spring (force-directed) layout on the whole backbone, which is driven by ALL links;
about 36% of links cross communities, so communities interleave. Here the same force-directed layout is run with links INSIDE a community given MULT times the weight of links between communities
(positions are for display only; communities and links are unchanged). Prints a tightness score per MULT: mean distance of a person to their community's centre / mean distance to the overall centre (lower = tighter).
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python seedoils/notebooks/community_layout.py [MULT]   (no argument = compare 1, 4, 12; with MULT = write x, y into cn_nodes.json and nn_nodes.json)"""
import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np

A = Path("seedoils/data/processed/artifact")
CN = json.load(open(A / "cn_nodes.json")); NN = json.load(open(A / "nn_nodes.json")); E = json.load(open(A / "cn_edges.json"))["rows"]
c = np.array([r["c"] for r in CN["rows"]]); n = len(c)


def layout(mult):
    G = nx.Graph(); G.add_nodes_from(range(n))
    for e in E:
        G.add_edge(e["s"], e["t"], weight=mult if c[e["s"]] == c[e["t"]] else 1.0)
    pos = nx.spring_layout(G, weight="weight", k=0.12, iterations=400, seed=2)
    xy = np.array([pos[i] for i in range(n)]); lo, hi = xy.min(0), xy.max(0)
    return (xy - lo) / (hi - lo)


def tight(xy):
    cen = np.array([xy[c == k].mean(0) for k in range(c.max() + 1)])
    return float(np.mean(np.linalg.norm(xy - cen[c], axis=1)) / np.mean(np.linalg.norm(xy - xy.mean(0), axis=1)))


if len(sys.argv) == 1:
    for m in (1, 4, 12):
        print("MULT", m, "tightness", round(tight(layout(m)), 3), flush=True)
else:
    m = float(sys.argv[1]); xy = layout(m); print("MULT", m, "tightness", round(tight(xy), 3))
    for d in (CN, NN):
        for i, r in enumerate(d["rows"]): r["x"], r["y"] = round(float(xy[i, 0]), 4), round(float(xy[i, 1]), 4)
        d["meta"][1:] = d["meta"][1:]
    (A / "cn_nodes.json").write_text(json.dumps(CN)); (A / "nn_nodes.json").write_text(json.dumps(NN)); print("written")
