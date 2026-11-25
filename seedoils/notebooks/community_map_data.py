"""Data for the community-level map (test page seedoils/artifact/community_map.html): the 12 Louvain communities of the ~130-topic commenter backbone as nodes, and for each pair of communities
the number of backbone links between them and the LIFT (observed links / links expected if each community's link ends were matched at random: L_ij / (D_i * D_j / 2E)); lift 1 = chance.
Inputs: data/processed/artifact/cn_nodes.json, cn_edges.json, cn_comms.json, nn_comms.json, nn_nodes.json, nn_months.json. Run from final_project/:  python3 seedoils/notebooks/community_map_data.py -> data/processed/artifact/community_map.json (aggregates only)."""
import json
from pathlib import Path
A = Path("seedoils/data/processed/artifact")
N = json.load(open(A / "cn_nodes.json"))["rows"]; E = json.load(open(A / "cn_edges.json"))["rows"]; C = json.load(open(A / "cn_comms.json"))["rows"]; O = {r["c"]: r for r in json.load(open(A / "nn_comms.json"))["rows"]}
K = len(C); L = [[0] * K for _ in range(K)]; deg = [0] * K
for e in E:
    a, b = N[e["s"]]["c"], N[e["t"]]["c"]; deg[a] += 1; deg[b] += 1
    L[min(a, b)][max(a, b)] += 1
tot = len(E); pairs = []
for i in range(K):
    for j in range(i, K):
        n = L[i][j]; exp = (deg[i] * deg[j] / (2 * tot)) * (1 if i != j else 0.5) if i != j else deg[i] * deg[i] / (4 * tot)
        pairs.append({"a": i, "b": j, "links": n, "lift": round(n / exp, 2) if exp else None})
comms = [{"id": c["id"], "label": c["label"], "short": c["short"], "people": c["size"], "long_pct": c["long_pct"], "within": L[c["id"]][c["id"]], "degree": deg[c["id"]],
          "h0": O[c["id"]]["h0"], "h1": O[c["id"]]["h1"], "v0": O[c["id"]]["v0"], "v1": O[c["id"]]["v1"], "n0": O[c["id"]]["n0"], "n1": O[c["id"]]["n1"]} for c in C]
NN = json.load(open(A / "nn_nodes.json"))["rows"]; MO = [r["m"] for r in json.load(open(A / "nn_months.json"))["rows"]]
cum = [[0] * K for _ in MO]
for n in NN:
    for m in range(n["fm"], len(MO)): cum[m][n["c"]] += 1
out = {"months": MO, "cum": cum, "comms": comms, "pairs": pairs, "links_total": tot, "overall": O[-2], "meta": [{"label": "community_map_data.py", "value": Path(__file__).read_text()}]}
(A / "community_map.json").write_text(json.dumps(out)); print(K, "communities;", tot, "links")
print("within-community share of links:", round(sum(L[i][i] for i in range(K)) / tot * 100), "%")
for p in sorted([p for p in pairs if p["a"] != p["b"]], key=lambda p: -p["lift"])[:12]: print(p, comms[p["a"]]["short"], "|", comms[p["b"]]["short"])
print("lift of off-diagonal pairs: min %s max %s; pairs with lift>=1.5: %d of %d" % (min(p["lift"] for p in pairs if p["a"] != p["b"]), max(p["lift"] for p in pairs if p["a"] != p["b"]), sum(1 for p in pairs if p["a"] != p["b"] and p["lift"] >= 1.5), K * (K - 1) // 2))
i23, i24 = MO.index("2023-12"), MO.index("2024-12")
print("people by end of 2023 -> end of 2024 (x):")
for c in comms: a, b = cum[i23][c["id"]], cum[i24][c["id"]]; print(f"  {c['short']:<18}{a:>5} -> {b:>4}  x{b / max(a, 1):.1f}   final {cum[-1][c['id']]}")
