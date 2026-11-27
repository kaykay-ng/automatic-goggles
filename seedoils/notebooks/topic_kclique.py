"""k-clique percolation vs Louvain on the topic co-writing network (user question 27 Nov). Network: topic_cooccurrence_network.json (topics as
nodes, a link when more people wrote in both topics than chance; 299 links). k-clique communities (Palla et al. 2005, networkx) for k = 3, 4, 5:
unions of k-cliques that share k-1 topics; a topic can be in several communities or in none. Compared with the Louvain communities of the same
network: topics covered, communities (2+ topics), topics in 2+ communities, agreement on the covered topics (AMI, each topic assigned to its
largest k-clique community), and where the five politics topics and the saturated-fat hub (topic 4) end up.
Output: data/processed/topic_kclique.json. Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/topic_kclique.py"""
import json
from collections import Counter
from pathlib import Path

import networkx as nx
from networkx.algorithms.community import k_clique_communities
from sklearn.metrics import adjusted_mutual_info_score as ami

P = Path("seedoils/data/processed")
T = json.loads((P / "topic_cooccurrence_network.json").read_text()); C = json.loads((P / "topic_network_centrality.json").read_text())
nodes = {n["topic"]: n for n in T["nodes"]}; names = {int(k): v for k, v in C["community_names"].items()}
G = nx.Graph(); G.add_nodes_from(nodes); G.add_edges_from((e["a"], e["b"]) for e in T["edges_all"])
linked = [v for v in G if G.degree(v) > 0]; louv = {v: nodes[v]["community"] for v in G}
POL = [v for v in G if nodes[v]["theme"] == "Politics"]
short = lambda v: ", ".join(nodes[v]["words"].split(", ")[:2])  # noqa: E731
out = {"linked_topics": len(linked), "louvain_communities_2plus": len({louv[v] for v in linked if sum(1 for u in linked if louv[u] == louv[v]) >= 2})}
for k in (3, 4, 5):
    comms = sorted([set(c) for c in k_clique_communities(G, k)], key=len, reverse=True)
    member = {}
    for i, c in enumerate(comms):
        for v in c:
            member.setdefault(v, []).append(i)
    covered = sorted(member); main = {v: max(member[v], key=lambda i: len(comms[i])) for v in covered}
    rows = []
    for i, c in enumerate(comms):
        lc = Counter(louv[v] for v in c).most_common(1)[0]
        rows.append({"size": len(c), "main_louvain": names.get(lc[0], f"community {lc[0]}"), "share_in_it_pct": round(100 * lc[1] / len(c)),
                     "politics_topics": sum(1 for v in c if v in POL), "examples": [short(v) for v in sorted(c, key=lambda v: -nodes[v]["docs"])[:4]]})
    out[f"k={k}"] = {"communities": len(comms), "topics_covered": len(covered), "covered_pct_of_linked": round(100 * len(covered) / len(linked), 1),
                     "topics_in_2plus": int(sum(1 for v in covered if len(member[v]) > 1)),
                     "ami_vs_louvain_on_covered": round(float(ami([louv[v] for v in covered], [main[v] for v in covered])), 3) if covered else None,
                     "politics_topics_covered": sum(1 for v in POL if v in member), "politics_in_one_community": len({main[v] for v in POL if v in member}) == 1,
                     "politics_communities_also_hold": sorted({short(u) for v in POL if v in member for i in member[v] for u in comms[i] if u not in POL})[:12],
                     "hub_topic4_in_communities": len(member.get(4, [])), "communities_list": rows}
(P / "topic_kclique.json").write_text(json.dumps(out, indent=1))
print(f"linked topics {out['linked_topics']}; Louvain communities (2+ topics) {out['louvain_communities_2plus']}")
for k in (3, 4, 5):
    r = out[f"k={k}"]
    print(f"\nk={k}: {r['communities']} communities, {r['topics_covered']} topics covered ({r['covered_pct_of_linked']}% of linked), {r['topics_in_2plus']} in 2+; AMI vs Louvain {r['ami_vs_louvain_on_covered']}; "
          f"politics covered {r['politics_topics_covered']}/5, in one community: {r['politics_in_one_community']}; hub in {r['hub_topic4_in_communities']} communities")
    for c in r["communities_list"][:8]:
        print(f"   size {c['size']:2d}  {c['share_in_it_pct']:3d}% {c['main_louvain'][:34]:34s} politics {c['politics_topics']}  {c['examples']}")
    print("   politics k-clique community also holds:", r["politics_communities_also_hold"])
