"""Datasets for the artifact's Figures 8 and 9 (niche timeline and outcome overlay): nn_nodes, nn_comms, nn_months as {rows, meta} JSON (edges are cn_edges: same node order).
Input: data/processed/artifact/niche_network.json (niche_overlay_data.py). Run from final_project/:  python3 seedoils/notebooks/niche_network_datasets.py"""
import json
from pathlib import Path
A = Path("seedoils/data/processed/artifact"); d = json.load(open(A / "niche_network.json")); src = Path(__file__).read_text()
meta = lambda desc: [{"label": "niche_network_datasets.py", "value": src, "type": "code", "lang": "python"}, {"label": "What it is", "value": desc}]
def save(name, rows, desc): (A / f"{name}.json").write_text(json.dumps({"rows": rows, "meta": meta(desc)}))
save("nn_nodes", d["nodes"], "One row per commenter of the backbone (same order as cn_nodes): niche index c, long-time flag o, comments d, layout x and y, first-comment month index fm (0 = January 2022 or earlier), disapproving-tone share h and downvoted share v in percent (all time, h0 and v0 before 2024, h1 and v1 from 2024; shrunk toward the average by 15 pseudo-comments), comments before and after 2024 n0 and n1.")
rows = []
for r in d["comms"]:
    rows.append({"c": r["c"], "label": r["label"], "people": r["people"], "n0": r["n0"], "n1": r["n1"], "h0": r["h0"], "h1": r["h1"], "v0": r["v0"], "v1": r["v1"], "h_lo": r["hci"][0], "h_hi": r["hci"][1], "v_lo": r["vci"][0], "v_hi": r["vci"][1]})
o = d["overall"]; rows.append({"c": -2, "label": "All commenters", "people": sum(r["people"] for r in d["comms"]), "n0": None, "n1": None, "h0": o["h0"], "h1": o["h1"], "v0": o["v0"], "v1": o["v1"], "h_lo": None, "h_hi": None, "v_lo": None, "v_hi": None})
save("nn_comms", rows, "Per niche: plain shares of disapproving-tone (GoEmotions anger, annoyance, disapproval or disgust >= 0.5) and downvoted (score <= 0) comments before and from 2024, with the 95% interval of the change in percentage points from resampling people. c = -1 is the general core with no link, c = -2 all commenters.")
save("nn_months", [{"i": i, "m": m} for i, m in enumerate(d["months"])], "Month labels for the slider: index i, month m.")
print(len(d["nodes"]), len(rows), len(d["months"]))
