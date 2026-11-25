"""Datasets for the artifact's Figure 7 (commenter backbone): cn_nodes, cn_edges, cn_comms as {rows, meta} JSON files, and extra facts merged into facts.json.
Input: data/processed/artifact/commenter_network.json (from commenter_topic_network.py --export). Community names are ours (read from each community's most over-represented topics).
cn_ami, cn_perm_p and cn_null_max are results printed by commenter_topic_network.py and by the permutation test run after it (20 Louvain seeds; 5 label-shuffle reps; 2,000 permutations); update them if that analysis is rerun.
Run from final_project/:  python3 seedoils/notebooks/commenter_network_datasets.py"""
import json
from pathlib import Path
A = Path("seedoils/data/processed/artifact"); d = json.load(open(A / "commenter_network.json")); src = Path(__file__).read_text()
LAB = ['Condiments, snacks, bread', 'Olive oil and other oils', 'Politics (RFK, Trump)', 'Eggs and raw milk', 'Bread, butter, nuts', 'Organic, protein, soy', 'Ingredient labels, ice cream', 'Sugar, carbs, weight', 'Vaccines, fluoride', 'LDL and cholesterol', 'Skin and sun', 'Infant formula', 'Coffee, plastics, sushi', 'Tallow and fries', 'MSG', 'Vitamins, supplements']
SH = ['Condiments, snacks', 'Olive oil', 'Politics', 'Eggs, raw milk', 'Bread, butter', 'Organic, protein', 'Labels, ice cream', 'Sugar, carbs', 'Vaccines', 'LDL', 'Skin, sun', 'Infant formula', 'Coffee, plastics', 'Tallow, fries', 'MSG', 'Vitamins']
meta = lambda desc: [{"label": "commenter_network_datasets.py", "value": src, "type": "code", "lang": "python"}, {"label": "What it is", "value": desc}]
def save(name, rows, desc): (A / f"{name}.json").write_text(json.dumps({"rows": rows, "meta": meta(desc)}))
save("cn_nodes", [{"c": n["c"], "o": n["o"], "d": n["d"], "x": n["x"], "y": n["y"]} for n in d["nodes"]], "One row per commenter linked by the backbone: community index, 1 if long-time (first comment before 2024), comments in the topic model, layout position (display only).")
save("cn_edges", [{"s": a, "t": b} for a, b in d["edges"]], "Backbone links (disparity filter, alpha 0.05); s and t are row numbers of cn_nodes.")
rows = []
for c in d["comms"]:
    rows.append({"id": c["id"], "label": LAB[c["id"]], "short": SH[c["id"]], "size": c["size"], "long_pct": c["long"], "docs_per_person": c["dpu"], "talk": "; ".join(f'{t["w"]} ({t["s"]}% of their comments, {t["o"]}% overall)' for t in c["topics"][:2])})
save("cn_comms", rows, "One row per Louvain community of the backbone: our name, size, share of long-time commenters, comments per person, and the two topics it talks about more than others.")
F = Path("seedoils/data/processed/artifact/facts.json"); f = json.loads(F.read_text()); R = {r["key"]: r for r in f["rows"]}
def add(k, v, label, unit=""): R[k] = {"key": k, "value": v, "label": label, "unit": unit}
nodes = d["nodes"]; avg = round(sum(n["d"] for n in nodes) / len(nodes))
add("cn_users", d["n_users"], "Commenters with 10 or more comments in the topic model (r/StopEatingSeedOils)"); add("cn_links_full", d["links_full"], "Possible topic-similarity links between those commenters")
add("cn_links_kept", d["links_kept"], "Links kept by the disparity filter"); add("cn_kept_pct", round(d["links_kept"] / d["links_full"] * 100, 2), "Share of links kept", "%")
add("cn_isolated", d["iso"]["n"], "Commenters with no link left"); add("cn_iso_pct", round(d["iso"]["n"] / d["n_users"] * 100), "Share of commenters with no link left", "%")
add("cn_iso_docs", d["iso"]["docs"], "Comments per commenter, those with no link left"); add("cn_drawn_docs", avg, "Comments per commenter, those with a link"); add("cn_drawn", len(nodes), "Commenters with at least one backbone link")
add("cn_iso_gen", d["iso"]["gen_share"], "Share of comments in the general seed-oil topic, commenters with no link", "%"); add("cn_drawn_gen", d["iso"]["gen_share_linked"], "Same, commenters with a link", "%"); add("cn_gen_all", d["iso"]["gen_all"], "Share of all comments in the general seed-oil topic", "%")
add("cn_long_all", d["long_all"], "Long-time commenters among the commenters", "%"); add("cn_pol_long", rows[2]["long_pct"], "Long-time commenters in the politics community", "%"); add("cn_eggs_long", rows[3]["long_pct"], "Long-time commenters in the eggs and raw milk community", "%")
add("cn_alpha", d["alpha"], "Significance level of the disparity filter"); add("cn_communities", len(rows), "Communities found"); add("cn_comm100", sum(r["size"] >= 100 for r in rows), "Communities of 100 or more people")
add("cn_ami", 0.95, "Agreement between 20 Louvain runs (adjusted mutual information, mean)"); add("cn_perm_p", 0.013, "Permutation test p-value: do communities differ in long-time share beyond chance"); add("cn_null_max", 44, "Most links kept by the filter when topic labels are shuffled (5 repetitions)")
f["rows"] = list(R.values()); F.write_text(json.dumps(f)); print({k: R[k]["value"] for k in R if k.startswith("cn_")})
