"""Paper / slide figure (one column, 8.7 cm; 27 Nov, user option 2): the topic co-writing network summarised by community. Each of the six
main Louvain communities of the topic network is one circle (area ~ number of topics) at the same place on the ring as in
topic_network_communities_figure.py; a band between two circles = the links between their topics (width ~ sqrt(number), number written on it).
Under each circle: its name, number of topics and links inside, and three example topics (largest first). The five politics topics are
marked in the politics circle's text. Reads data/processed/topic_network_communities_layout.json (written by topic_network_communities_figure.py).
Output: paper/figures/topic_communities_summary.pdf, seedoils/figures/topic_communities_summary.png.
Run from the repo root:  PATH=/Library/TeX/texbin:$PATH ./.venv-nlp/bin/python seedoils/notebooks/topic_community_summary_figure.py"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

plt.rcParams.update({"text.usetex": True, "font.family": "serif", "font.size": 6.5,
                     "text.latex.preamble": r"\usepackage[T1]{fontenc}\usepackage{lmodern}"})
P = Path("seedoils/data/processed")
L = json.loads((P / "topic_network_communities_layout.json").read_text())
T = json.loads((P / "topic_cooccurrence_network.json").read_text()); nodes = {n["topic"]: n for n in T["nodes"]}
MAIN = [c for c, n in L["topics"].items() if n >= 5]
cen = {c: np.array(L["centres"][c]) for c in MAIN}
EXAMPLES = {"Politics, distrust and evidence": "5 politics topics,\ndistrust, studies"}
WRAP = {"Diet, weight and saturated fat": ["Diet, weight and", "saturated fat"], "Politics, distrust and evidence": ["Politics, distrust", "and evidence"],
        "Oils and cooking fats": ["Oils and", "cooking fats"]}
short = lambda t: nodes[t]["words"].split(", ")[0].replace("-", " ").replace("_", " ")  # noqa: E731

fig, ax = plt.subplots(figsize=(3.42, 3.0)); ax.set_aspect("equal"); ax.axis("off")
P_ = np.array(list(cen.values())); ring_c = P_.mean(0)
ax.set_xlim(P_[:, 0].min() - 1.0, P_[:, 0].max() + 1.0); ax.set_ylim(P_[:, 1].min() - 0.75, P_[:, 1].max() + 0.6)
rad = {c: 0.09 * np.sqrt(L["topics"][c]) for c in MAIN}
fig.canvas.draw(); R = fig.canvas.get_renderer(); placed = []
overlap = lambda b1, b2: not (b1.x1 < b2.x0 or b1.x0 > b2.x1 or b1.y1 < b2.y0 or b1.y0 > b2.y1)  # noqa: E731
segs = []
for a_, b_, n in L["bands"]:
    a_, b_ = str(a_), str(b_)
    if a_ in cen and b_ in cen:
        pa, pb = cen[a_], cen[b_]; u = (pb - pa) / np.linalg.norm(pb - pa); qa, qb = pa + u * rad[a_], pb - u * rad[b_]
        ax.plot([qa[0], qb[0]], [qa[1], qb[1]], color="#b9b8b0", lw=0.9 * np.sqrt(n), solid_capstyle="butt", zorder=1); segs.append((qa, qb, n))
for c in MAIN:  # circles with the number of topics inside
    ax.add_patch(plt.Circle(cen[c], rad[c], facecolor=L["colours"][c], edgecolor="white", lw=0.8, zorder=2))
    ax.text(*cen[c], str(L["topics"][c]), ha="center", va="center", fontsize=6.5, color="white", zorder=4)
fig.canvas.draw()
for c in MAIN:  # text outward from the ring centre, so it never points into the bands
    nm = L["names"][c]; d = cen[c] - ring_c; d = d / np.linalg.norm(d)
    ex = EXAMPLES.get(nm) or ", ".join(short(t) for t in sorted(L["members"][c], key=lambda t: -nodes[t]["docs"])[:3])
    lines = [r"\textbf{" + x + "}" for x in WRAP.get(nm, [nm])] + [f"{L['inside_links'][c]} links inside"] + [r"\textit{" + x + "}" for x in ex.split("\n")]
    txt = "\n".join(lines)
    q = cen[c] + d * (rad[c] + 0.08)
    ha = "left" if d[0] > 0.35 else ("right" if d[0] < -0.35 else "center"); va = "bottom" if d[1] > 0.3 else ("top" if d[1] < -0.3 else "center")
    t = ax.text(*q, txt, ha=ha, va=va, fontsize=5.8, linespacing=1.15, multialignment=ha if ha != "center" else "center", zorder=4)
    placed.append(t.get_window_extent(R))
for qa, qb, n in segs:  # band counts: first spot along the band that is free
    for fr in (0.5, 0.4, 0.6, 0.3, 0.7, 0.22, 0.78):
        t = ax.text(*(qa + fr * (qb - qa)), str(n), ha="center", va="center", fontsize=5.8, zorder=3, bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="#b9b8b0", lw=0.3))
        bb = t.get_window_extent(R)
        if not any(overlap(bb, o) for o in placed):
            placed.append(bb); break
        t.remove()
fig.savefig("paper/figures/topic_communities_summary.pdf", bbox_inches="tight", pad_inches=0.02)
fig.savefig("seedoils/figures/topic_communities_summary.png", dpi=300, bbox_inches="tight", pad_inches=0.02)
print("wrote paper/figures/topic_communities_summary.pdf")
