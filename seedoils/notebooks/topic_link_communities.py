"""Link communities of the topic co-occurrence network (user request 27 Nov; Ahn, Bagrow and Lehmann 2010, Nature 466:761). Communities of LINKS,
so a topic can belong to several: the overlap shows which topics bridge parts of the conversation. Reads data/processed/topic_cooccurrence_network.json.
Similarity of two links e_ik, e_jk that share topic k = Jaccard of the inclusive neighbourhoods of i and j (a topic and its neighbours); links that
share no topic have similarity 0. Single-linkage clustering (links merged from the most to the least similar, ties merged together); the dendrogram
is cut at the maximum partition density D = 2/M * sum_c m_c (m_c - (n_c - 1)) / ((n_c - 2)(n_c - 1)) (m_c links and n_c topics in community c).
Also the same with the weighted similarity (Tanimoto of lift vectors, as in the paper's weighted version).
Reported: number of link communities (all, and with 3+ links), partition density, share of links in communities of 3+ links, topics in more than
one community (overlap), the topics in the most communities, the main link community of each topic (where most of its links are) against the
Louvain communities and the 14 themes (AMI), and the largest link communities with their topics and themes.
Output: data/processed/topic_link_communities.json. Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/topic_link_communities.py"""
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
from sklearn.metrics import adjusted_mutual_info_score as ami

P = Path("seedoils/data/processed")
d = json.loads((P / "topic_cooccurrence_network.json").read_text())
nodes = {n["topic"]: n for n in d["nodes"]}
E = [(min(e["a"], e["b"]), max(e["a"], e["b"])) for e in d["edges_all"]]; W = {(min(e["a"], e["b"]), max(e["a"], e["b"])): e["lift"] for e in d["edges_all"]}
nb = defaultdict(set)
for a, b in E:
    nb[a].add(b); nb[b].add(a)
inc = {v: nb[v] | {v} for v in nb}
M = len(E); eid = {e: i for i, e in enumerate(E)}


def wvec(v):
    x = {u: W[(min(u, v), max(u, v))] for u in nb[v]}; x[v] = float(np.mean(list(x.values())))  # self weight = mean of its links (Ahn et al.)
    return x


WV = {v: wvec(v) for v in nb}


def sim(i, j, weighted):
    if not weighted:
        return len(inc[i] & inc[j]) / len(inc[i] | inc[j])
    a, b = WV[i], WV[j]; dot = sum(a[k] * b[k] for k in a.keys() & b.keys()); na, nb_ = sum(x * x for x in a.values()), sum(x * x for x in b.values())
    return dot / (na + nb_ - dot)


def link_communities(weighted):
    pairs = []
    for k in nb:
        for i, j in combinations(sorted(nb[k]), 2):
            pairs.append((sim(i, j, weighted), eid[(min(i, k), max(i, k))], eid[(min(j, k), max(j, k))]))
    pairs.sort(key=lambda x: -x[0])
    parent = list(range(M)); members = {i: {i} for i in range(M)}
    nodes_of = {i: set(E[i]) for i in range(M)}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x

    def dc(m, n):
        return 0.0 if n <= 2 else m * (m - (n - 1)) / ((n - 2) * (n - 1))
    total = sum(dc(1, 2) for _ in range(M)); best = (total * 2 / M, None, {i: i for i in range(M)})
    k = 0
    while k < len(pairs):
        s = pairs[k][0]
        while k < len(pairs) and pairs[k][0] == s:  # merge all ties at this level
            _, x, y = pairs[k]; rx, ry = find(x), find(y)
            if rx != ry:
                total -= dc(len(members[rx]), len(nodes_of[rx])) + dc(len(members[ry]), len(nodes_of[ry]))
                if len(members[rx]) < len(members[ry]):
                    rx, ry = ry, rx
                parent[ry] = rx; members[rx] |= members.pop(ry); nodes_of[rx] |= nodes_of.pop(ry)
                total += dc(len(members[rx]), len(nodes_of[rx]))
            k += 1
        D = total * 2 / M
        if D > best[0]:
            best = (D, s, {i: find(i) for i in range(M)})
    D, s_cut, lab = best
    comm = defaultdict(list)
    for i, c in lab.items():
        comm[c].append(i)
    comms = sorted(comm.values(), key=len, reverse=True)
    topic_comms = defaultdict(Counter)
    for ci, links in enumerate(comms):
        for i in links:
            for v in E[i]:
                topic_comms[v][ci] += 1
    big = [c for c in comms if len(c) >= 3]
    main = {v: cnt.most_common(1)[0][0] for v, cnt in topic_comms.items()}
    vs = sorted(main); louv = [nodes[v]["community"] for v in vs]; th = [nodes[v]["theme"] for v in vs]; mc = [main[v] for v in vs]
    in_big = {v: sum(1 for ci, n in topic_comms[v].items() if len(comms[ci]) >= 3) for v in topic_comms}
    out = {"partition_density": round(D, 3), "cut_similarity": round(float(s_cut), 3) if s_cut is not None else None, "links": M,
           "link_communities": len(comms), "link_communities_3plus": len(big), "links_in_3plus_pct": round(100 * sum(len(c) for c in big) / M, 1),
           "topics": len(topic_comms), "topics_in_2plus_communities_3plus": int(sum(1 for v in in_big if in_big[v] >= 2)),
           "ami_main_link_community_vs_louvain": round(float(ami(louv, mc)), 3), "ami_main_link_community_vs_themes": round(float(ami(th, mc)), 3),
           "ami_louvain_vs_themes_same_topics": round(float(ami(th, louv)), 3),
           "most_overlapping_topics": [{"topic": int(v), "words": nodes[v]["words"], "theme": nodes[v]["theme"], "link_communities_3plus": int(in_big[v]),
                                        "links": len(nb[v])} for v in sorted(in_big, key=lambda v: (-in_big[v], -len(nb[v])))[:12]],
           "largest": []}
    for ci, links in enumerate(comms[:12]):
        tv = sorted({v for i in links for v in E[i]}, key=lambda v: -nodes[v]["docs"])
        out["largest"].append({"links": len(links), "topics": len(tv), "themes": dict(Counter(nodes[v]["theme"].split(" (")[0] for v in tv).most_common(4)),
                               "topic_words": [", ".join(nodes[v]["words"].split(", ")[:2]) for v in tv[:6]], "topic_ids": [int(v) for v in tv]})
    return out


res = {"unweighted": link_communities(False), "weighted": link_communities(True)}
(P / "topic_link_communities.json").write_text(json.dumps(res, indent=1))
for k, r in res.items():
    print(k, json.dumps({x: y for x, y in r.items() if x not in ("largest", "most_overlapping_topics")}))
    for t in r["most_overlapping_topics"][:8]:
        print("   overlap", t)
    for c in r["largest"][:8]:
        print("   comm", c["links"], c["topics"], c["themes"], c["topic_words"][:4])
