"""Do the 'stretched' commenters (links in two communities) have high betweenness in the backbone? Exact betweenness (unweighted hops) on the Figure 7 backbone (1,830 commenters).
Stretched = degree >= 6 and >= 25% of links go to a community other than their own. Aggregates only. Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/niche_bridges.py"""
import json, collections
import numpy as np, networkx as nx
from scipy.stats import spearmanr
J = json.load(open("seedoils/data/processed/artifact/commenter_network.json")); nodes = J["nodes"]; edges = J["edges"]
G = nx.Graph(); G.add_nodes_from(range(len(nodes))); G.add_edges_from(map(tuple, edges))
bt = nx.betweenness_centrality(G); b = np.array([bt[i] for i in range(len(nodes))]); deg = np.array([G.degree(i) for i in range(len(nodes))])
ext = np.array([sum(nodes[j]["c"] != nodes[i]["c"] for j in G[i]) / max(1, G.degree(i)) for i in range(len(nodes))])
stretched = (deg >= 6) & (ext >= 0.25); print(f"nodes {len(nodes)}, stretched (deg>=6 and >=25% links outside own community): {stretched.sum()}")
rank = (-b).argsort().argsort() + 1
print(f"betweenness: stretched median rank {np.median(rank[stretched]):.0f} of {len(nodes)} vs others {np.median(rank[~stretched]):.0f}; mean betweenness x1000: stretched {b[stretched].mean()*1000:.2f} vs others {b[~stretched].mean()*1000:.2f}")
print(f"stretched nodes in the top 5% by betweenness: {(rank[stretched] <= len(nodes)*0.05).mean()*100:.0f}% (expected 5% by chance); share of top-5% nodes that are stretched: {stretched[rank <= len(nodes)*0.05].mean()*100:.0f}%")
print("Spearman: betweenness vs share of links outside own community (deg>=6 only): %.2f ; betweenness vs degree: %.2f" % (spearmanr(b[deg >= 6], ext[deg >= 6])[0], spearmanr(b, deg)[0]))
top = (-b).argsort()[:12]; print("\ntop 12 by betweenness: degree | share of links outside own community | own community | comments | long-time")
for i in top: print(f"  {deg[i]:>3} | {ext[i]*100:3.0f}% | C{nodes[i]['c']} | {nodes[i]['d']:>3} | {'long-time' if nodes[i]['o'] else 'newcomer'}")
print("\nbetweenness by community (mean x1000):", {c: round(float(b[[i for i, n in enumerate(nodes) if n['c'] == c]].mean() * 1000), 2) for c in range(10)})
print("share of nodes whose links are all inside their own community: %.0f%%" % ((ext == 0).mean() * 100))
