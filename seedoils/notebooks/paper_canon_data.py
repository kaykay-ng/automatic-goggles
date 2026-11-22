"""Data for the 'paper canon' figure: the scholarly citation network among Reddit-cited papers, coloured by which subreddit's commenters cite them.
Nodes: papers cited by >= 2 people in the two subreddits (cocite_nodes.csv, 1,985). Edges: one paper cites another (OpenAlex referenced works, cocite_scholarly_edges.csv). Camp: SESO-only / both / SciNut-only by people citing.
Evidence type from OpenAlex MeSH tags (humans only / animal or cell / mixed / not tagged): a coarse proxy, not the labelled design. Displayed: papers cited by >= 4 people, plus SESO-only papers cited by >= 3. Layout: spring layout of the scholarly edges (display only).
Output: data/processed/artifact/paper_canon.json. Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/paper_canon_data.py"""
import json
from pathlib import Path
import networkx as nx, numpy as np, pandas as pd
P = Path("seedoils/data/processed")
N = pd.read_csv(P / "cocite_nodes.csv"); E = pd.read_csv(P / "cocite_scholarly_edges.csv")
G = nx.Graph(); G.add_nodes_from(N.openalex_id); G.add_edges_from(zip(E.source, E.target))
N["deg"] = N.openalex_id.map(dict(G.degree())); N["core"] = N.openalex_id.map(nx.core_number(G))
import gzip
ids = set(N.openalex_id); DG = nx.DiGraph(); DG.add_nodes_from(ids)
with gzip.open("seedoils/data/raw/openalex_works.jsonl.gz", "rt", encoding="utf-8") as fh:
    for l in fh:
        r = json.loads(l); w = r.get("work")
        if w and w["id"] in ids:
            for ref in w.get("referenced_works") or []:
                if ref in ids and ref != w["id"]: DG.add_edge(w["id"], ref)  # citing -> cited; the cited paper receives rank
N["pr"] = N.openalex_id.map(nx.pagerank(DG, alpha=0.85)); N["bw"] = N.betweenness_reddit
N["rp"] = N.pr.rank(ascending=False, method="first").astype(int); N["rb"] = N.bw.rank(ascending=False, method="first").astype(int)
N["camp"] = N.side.map({"SESO": "seso", "both": "both", "SciNut": "scinut"})
N["ev"] = N.design.map({"humans only": "human", "animal": "animal", "humans + animal/cell": "mixed"}).fillna("other")
N["total"] = N.users_SESO + N.users_SciNut
stats = []
for camp, g in N.groupby("camp"):
    stats.append({"camp": camp, "papers": int(len(g)), "mean_links": round(g.deg.mean(), 1), "isolated_pct": round((g.deg == 0).mean() * 100), "mean_core": round(g.core.mean(), 1), "animal_pct": round(g.ev.isin(["animal", "mixed"]).mean() * 100), "median_scholarly_cites": float(g.cited_by_count.median())})
ev = [{"ev": e, "papers": int(len(g)), "mean_links": round(g.deg.mean(), 1), "seso_only_pct": round((g.camp == "seso").mean() * 100, 1)} for e, g in N.groupby("ev")]
S = N[(N.total >= 4) | ((N.camp == "seso") & (N.users_SESO >= 3))].copy(); H = G.subgraph(S.openalex_id).copy()
big = max(nx.connected_components(H), key=len); pos = nx.spring_layout(H.subgraph(big), seed=3, k=0.35, iterations=300)
xy = np.array(list(pos.values())); lo, hi = xy.min(0), xy.max(0); pos = {k: ((v - lo) / (hi - lo)).tolist() for k, v in pos.items()}
rest = [n for n in H.nodes if n not in pos]; cols = 18
for i, n in enumerate(sorted(rest, key=lambda n: -S.set_index("openalex_id").total[n])): pos[n] = [(i % cols + 0.5) / cols, 1.12 + (i // cols) * 0.06]
S = S.reset_index(drop=True); idx = {o: i for i, o in enumerate(S.openalex_id)}
nodes = [{"t": str(r.title)[:140], "y": int(r.year) if pd.notna(r.year) else None, "c": r.camp, "e": r.ev, "s": int(r.users_SESO), "n": int(r.users_SciNut), "k": int(r.cited_by_count), "d": int(r.deg), "x": round(pos[r.openalex_id][0], 4), "yy": round(pos[r.openalex_id][1], 4), "iso": r.openalex_id in rest, "p": round(r.pr * 1000, 3), "b": round(r.bw * 1000, 3), "rp": int(r.rp), "rb": int(r.rb)} for r in S.itertuples()]
edges = [[idx[a], idx[b]] for a, b in H.edges]
def top(col, n=10):
    return [{"t": str(r.title)[:120], "y": int(r.year), "c": r.camp, "e": r.ev, "s": int(r.users_SESO), "n": int(r.users_SciNut), "k": int(r.cited_by_count), "v": round(getattr(r, col) * 1000, 2)} for r in N.sort_values(col, ascending=False).head(n).itertuples()]
out = {"top_pr": top("pr"), "top_bw": top("bw"), "nodes": nodes, "edges": edges, "stats": stats, "ev": ev, "n_all": int(len(N)), "meta": [{"label": "paper_canon_data.py", "value": Path(__file__).read_text()}]}
(P / "artifact" / "paper_canon.json").write_text(json.dumps(out)); print(len(nodes), "nodes", len(edges), "edges", "isolated", len(rest)); print(stats); print(ev)
