"""Paper figure: the topic co-occurrence network, all years, ALL 123 topics (user requests 27 Nov). The 85 topics of the main connected component keep
the layout of the results page (topic_network_centrality.json: Kamada-Kawai); the 32 topics without a significant link and the two small separate
groups sit on an outer ring around it (ordered by theme, so related topics are neighbours; the small groups keep their links). Colours = the three
largest Louvain topic communities, grey = all others; circle area = documents. Text rendered by LaTeX in Latin Modern (lmodern, T1), the font of
paper/preview.tex. Labels (two top words) for: the 6 largest topics of each coloured community, the 3 largest of every other community with 2+
topics, the hubs, and every topic on the ring. Labels are placed by search: candidate positions on rings around the node, from near to far; a
position is accepted only if the label box touches no circle, no link, no other label, no leader line and stays inside the frame, and its leader
line touches no other circle, label or leader; among accepted positions the fewest crossed links (then the nearest) wins. Labels that find no spot
are reported, not forced. Output: seedoils/figures/topic_network_all_years.pdf and .png.
Run from the repo root:  PATH=/Library/TeX/texbin:$PATH ./.venv-nlp/bin/python seedoils/notebooks/topic_network_figure.py"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

plt.rcParams.update({"text.usetex": __import__("shutil").which("latex") is not None, "font.family": "serif", "font.serif": ["cmr10", "DejaVu Serif"], "axes.formatter.use_mathtext": True, "font.size": 8,
                     "text.latex.preamble": r"\usepackage[T1]{fontenc}\usepackage{lmodern}"})
P = Path("seedoils/data/processed")
T = json.loads((P / "topic_cooccurrence_network.json").read_text()); C = json.loads((P / "topic_network_centrality.json").read_text())
nodes = {n["topic"]: n for n in T["nodes"]}; lay = {int(k): np.array(v, float) for k, v in C["layout"].items()}
# 27 Nov (after the 0.05 rerun): colour the four large Louvain communities and the politics community, named as in the paper's Results
# (the saved names/colours in topic_network_centrality.json predate the rerun). Palette checked with the dataviz validator (CVD-safe).
_cnt = {}
for _v in C["layout"]:
    _c = nodes[int(_v)]["community"]; _cnt[_c] = _cnt.get(_c, 0) + 1
_big = sorted(_cnt, key=lambda c: -_cnt[c])[:4]
_pol = max(_cnt, key=lambda c: sum(1 for _v in C["layout"] if nodes[int(_v)]["community"] == c and nodes[int(_v)]["theme"] == "Politics"))
COLOURED = _big + ([_pol] if _pol not in _big else [])
COL = dict(zip(COLOURED, ["#2a78d6", "#eb6834", "#1baf7a", "#8e5bd0", "#c9334f"])); GREY, EDGE = "#b9b8b0", "#cfcec7"
NAMES = {}  # filled from each community's topics below (matches the Results text)
SPREAD = 0.3  # after the relayout, each community also moved outward a little as a block: position + SPREAD * (community centre - network centre)
INTER = 0.25  # relayout: a link between two communities pulls with this weight, a link inside a community with 1 (spring layout started from the saved layout)
FS = 6.8  # label size (pt)
LINKS_OK = "--no-isolates" in sys.argv and "--reply" not in sys.argv  # paper figure: a label may sit over links (white background, penalised) so central topics get short leaders
NO_ISO = "--no-isolates" in sys.argv  # second version: without the 32 isolated topics (the two small linked groups kept)
OUT = "topic_network_main" if NO_ISO else "topic_network_all_years"
REPLY = "--reply" in sys.argv  # 27 Nov: the topic REPLY network (topic_reply_network.py) drawn the same way; colours stay the co-writing communities
if REPLY:
    import networkx as nx
    RJ = json.loads((P / "topic_reply_network.json").read_text())["reply_topic_network"]; NO_ISO = True; OUT = "topic_reply_network"
    T["edges_all"] = [{"a": e["a"], "b": e["b"], "lift": e["lift"]} for e in RJ["edges"]]
    Gr = nx.Graph(); Gr.add_nodes_from(nodes); Gr.add_edges_from((e["a"], e["b"], {"dist": 1 / e["lift"]}) for e in T["edges_all"])
    comps = sorted(nx.connected_components(Gr), key=len, reverse=True); core_ = Gr.subgraph(comps[0])
    kk = nx.kamada_kawai_layout(core_, weight="dist"); lay = {int(v): np.array(kk[v], float) for v in core_}
    C = dict(C); C["small_components"] = [sorted(int(x) for x in c) for c in comps[1:] if len(c) > 1]
    nodes = {t: dict(n, degree_all=Gr.degree(t)) for t, n in nodes.items()}
    print(f"reply network: {len(T['edges_all'])} links; main component {len(lay)} topics; small groups {C['small_components']}; isolated {sum(1 for c in comps if len(c) == 1)}")

# ---- layout (27 Nov, user: more horizontal): the main component's Kamada-Kawai layout rotated so its longest direction (first principal axis)
# is horizontal, oriented with the diet communities on the left and politics on the right, and stretched to ASPECT (width / height)
gadj = {}
for e in T["edges_all"]:
    gadj.setdefault(e["a"], set()).add(e["b"]); gadj.setdefault(e["b"], set()).add(e["a"])


def chain(g):  # order a small group along its links (start at an end)
    g = set(g); order = [min(g, key=lambda t: (len(gadj[t] & g), -nodes[t]["docs"]))]
    while len(order) < len(g):
        nxt = [u for u in gadj[order[-1]] & g if u not in order] or [u for u in g if u not in order]; order.append(nxt[0])
    return order


ASPECT = 2.3
if not REPLY:  # community-aware relayout: same links, communities drawn as visible groups that stay connected
    import networkx as nx
    Gm = nx.Graph(); Gm.add_nodes_from(lay)
    for e in T["edges_all"]:
        if e["a"] in lay and e["b"] in lay:
            Gm.add_edge(e["a"], e["b"], w=1.0 if nodes[e["a"]]["community"] == nodes[e["b"]]["community"] else INTER)
    lay = {int(k): np.array(v, float) for k, v in nx.spring_layout(Gm, pos={v: lay[v] for v in lay}, weight="w", iterations=300, seed=1, k=1.6 / np.sqrt(len(lay))).items()}
mvs = sorted(lay); M = np.array([lay[v] for v in mvs]); X = M - M.mean(0)
evec = np.linalg.eigh(np.cov(X.T))[1][:, ::-1]; Y = X @ evec
if np.mean([Y[i, 0] for i, v in enumerate(mvs) if nodes[v]["theme"] == "Politics"]) < 0:
    Y[:, 0] *= -1  # politics on the right
if np.mean([Y[i, 1] for i, v in enumerate(mvs) if nodes[v]["theme"] == "Politics"]) > 0:
    Y[:, 1] *= -1  # and at the bottom, as before
w0, h0 = np.ptp(Y[:, 0]), np.ptp(Y[:, 1])
if w0 / h0 < ASPECT:
    Y[:, 0] *= ASPECT * h0 / w0
Y /= np.ptp(Y[:, 1])  # height 1
pos = {v: Y[i].copy() for i, v in enumerate(mvs)}
if SPREAD and not REPLY:  # spread the communities apart without breaking them up: each keeps its own shape and all links are kept
    g0 = np.mean([pos[v] for v in mvs], axis=0); cc = {}
    for v in mvs:
        cc.setdefault(nodes[v]["community"], []).append(v)
    for c_, vs in cc.items():
        d_ = np.mean([pos[v] for v in vs], axis=0) - g0
        for v in vs:
            pos[v] = pos[v] + SPREAD * d_
    Y = np.array([pos[v] for v in mvs]); Y -= Y.mean(0); sc_ = np.ptp(Y[:, 1]); Y /= sc_; pos = {v: Y[i].copy() for i, v in enumerate(mvs)}
xmin, ymin = Y.min(0); xmax, ymax = Y.max(0); cen = np.array([(xmin + xmax) / 2, (ymin + ymax) / 2]); WD, HT = xmax - xmin, ymax - ymin
groups = sorted(C["small_components"], key=len)
iso = [n["topic"] for n in T["nodes"] if n["degree_all"] == 0]
GD = 0.085  # spacing inside a small group


def mini(g):  # small group as a zigzag along its links, centred on 0
    o = chain(g); n = len(o); return {t: np.array([(i - (n - 1) / 2) * GD, 0.3 * GD * (1 if i % 2 == 0 else -1)]) for i, t in enumerate(o)}


def seg_dist(p_, a_, b_):
    d = b_ - a_; L2 = d @ d; t = 0.0 if L2 == 0 else max(0.0, min(1.0, (p_ - a_) @ d / L2)); return np.linalg.norm(a_ + t * d - p_)


if NO_ISO:  # each small group goes to the emptiest spot inside the frame: farthest from every circle and link already placed
    items = []
    for g in groups:
        rel = mini(g); best = None
        for cx in np.linspace(xmin + 0.15, xmax - 0.15, 40):
            for cy in np.linspace(ymin + 0.05, ymax - 0.05, 20):
                pts = [np.array([cx, cy]) + r for r in rel.values()]
                ed = [(pos[a], pos[b]) for a in pos for b in gadj.get(a, ()) if b in pos and a < b]
                sc = min(min(np.linalg.norm(p_ - q) for q in pos.values() for p_ in pts), min((seg_dist(p_, a_, b_) for p_ in pts for a_, b_ in ed), default=9))
                if best is None or sc > best[0]:
                    best = (sc, cx, cy)
        for t, r in rel.items():
            pos[t] = np.array([best[1], best[2]]) + r
        items.append(chain(g))
else:  # isolated topics and the two small groups on two curved arcs following the network's outline (right, then left), ordered by theme
    items = [[t] for t in sorted(iso, key=lambda t: (nodes[t]["theme"], -nodes[t]["docs"]))]
    for g in groups:
        th = max(set(nodes[t]["theme"] for t in g), key=lambda x: sum(nodes[t]["theme"] == x for t in g))
        k = max([i for i, it in enumerate(items) if nodes[it[0]]["theme"] == th], default=len(items) - 1) + 1; items.insert(k, chain(g))
    seq = []
    for it in items:
        seq += it + [None]
    seq = seq[:-1]; half = len(seq) // 2
    while seq[half - 1] is not None and half < len(seq) - 1:
        half += 1
    right, left = (seq[:half - 1] if seq[half - 1] is None else seq[:half]), seq[half:]
    EA, EB, ARC = WD / 2 + 0.16, HT / 2 * 1.5, np.deg2rad(70)
    for side, sl in ((1, right), (-1, left)):
        n = len(sl)
        for i, t in enumerate(sl):
            if t is not None:
                a = ARC - 2 * ARC * i / max(n - 1, 1); pos[t] = cen + np.array([side * EA * np.cos(a), EB * np.sin(a)])
edges = [(e["a"], e["b"]) for e in T["edges_all"] if e["a"] in pos and e["b"] in pos]
P_ = np.array(list(pos.values())); PADX, PADY = (0.30, 0.07) if NO_ISO else (0.62, 0.07)
x_lo, x_hi = P_[:, 0].min() - PADX, P_[:, 0].max() + PADX; y_lo, y_hi = P_[:, 1].min() - PADY, P_[:, 1].max() + PADY
W_IN = 7.0; AX_H = W_IN * (y_hi - y_lo) / (x_hi - x_lo); LEG = 0.45; H_IN = AX_H + LEG
fig = plt.figure(figsize=(W_IN, H_IN)); ax = fig.add_axes([0.0, LEG / H_IN, 1.0, AX_H / H_IN]); ax.set_aspect("equal"); ax.axis("off")
ax.set_xlim(x_lo, x_hi); ax.set_ylim(y_lo, y_hi)
size = {v: 6 + 0.03 * nodes[v]["docs"] for v in pos}  # marker area in pt^2
# ---- no stacked circles: push overlapping circles apart (pairwise, half each) until every pair has a 2 px gap
fig.canvas.draw(); scale = ax.transData.transform((1, 0))[0] - ax.transData.transform((0, 0))[0]  # pixels per data unit
rr = {v: (np.sqrt(size[v]) / 2 * fig.dpi / 72 + 2.0) / scale for v in pos}
mv = sorted(pos); orig = {v: pos[v].copy() for v in mv}; rng_ = np.random.default_rng(0)
for it_ in range(3000):
    moved = False
    for i_, a in enumerate(mv):
        for b in mv[i_ + 1:]:
            d = pos[b] - pos[a]; dist = np.hypot(*d); need = rr[a] + rr[b]
            if dist < need - 1e-6:
                u = d / dist if dist > 1e-9 else rng_.normal(size=2) / np.sqrt(2)
                pos[a] = pos[a] - u * (need - dist) / 2; pos[b] = pos[b] + u * (need - dist) / 2; moved = True
    if not moved:
        break
shift = [np.hypot(*(pos[v] - orig[v])) * scale for v in mv]
left_ = sum(1 for i_, a in enumerate(mv) for b in mv[i_ + 1:] if np.hypot(*(pos[b] - pos[a])) < rr[a] + rr[b] - 4.0 / scale)
print(f"circles still overlapping after the push-apart step: {left_} pairs; circles moved {sum(x > 0.5 for x in shift)} of {len(mv)}, largest move {max(shift):.0f} px")
for a, b in edges:
    ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color=EDGE, lw=0.5, zorder=1, solid_capstyle="round")
for v in sorted(pos, key=lambda v: -nodes[v]["docs"]):
    ax.scatter(*pos[v], s=size[v], color=COL.get(nodes[v]["community"], GREY), edgecolors="white", linewidths=0.6, zorder=2)

# ---- which topics get a label
comm = {}
for v in lay:
    comm.setdefault(nodes[v]["community"], []).append(v)
main_labels = []
for c_, vs in sorted(comm.items(), key=lambda kv: -len(kv[1])):
    if len(vs) >= 2:
        main_labels += sorted(vs, key=lambda v: -nodes[v]["docs"])[:6 if c_ in COL else 3]
HUBS = [4, 1, 14, 0, 24, 9, 17, 37, 47, 12]
if REPLY:  # label the most connected topics of the reply network, plus the politics anchors
    HUBS = [t for t in sorted(lay, key=lambda t: -nodes[t]["degree_all"])[:8]] + [t for t in (47, 98, 17) if t in lay]
    HUBS = list(dict.fromkeys(HUBS))
main_labels = HUBS + [v for v in sorted(set(main_labels) - set(HUBS), key=lambda v: -nodes[v]["docs"])]
ring_labels = [t for it in items for t in it]

fig.canvas.draw(); R = fig.canvas.get_renderer(); tr = ax.transData
px = {v: tr.transform(pos[v]) for v in pos}
rad = {v: np.sqrt(size[v]) / 2 * fig.dpi / 72 + 1.5 for v in pos}
seg = [(px[a], px[b]) for a, b in edges]
fx0, fy0, fx1, fy1 = ax.bbox.x0, ax.bbox.y0, ax.bbox.x1, ax.bbox.y1
cpx = tr.transform(cen)


def box_hits_circle(bx, c, r):
    x = min(max(c[0], bx[0]), bx[2]); y = min(max(c[1], bx[1]), bx[3]); return (x - c[0]) ** 2 + (y - c[1]) ** 2 < r * r


def seg_hits_box(p, q, bx):
    t0, t1 = 0.0, 1.0; dx, dy = q[0] - p[0], q[1] - p[1]
    for pp, qq in ((-dx, p[0] - bx[0]), (dx, bx[2] - p[0]), (-dy, p[1] - bx[1]), (dy, bx[3] - p[1])):
        if pp == 0:
            if qq < 0:
                return False
        else:
            t = qq / pp
            if pp < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return True


def seg_circle(p, q, c, r):
    p, q, c = np.asarray(p), np.asarray(q), np.asarray(c); d = q - p; L2 = d @ d
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, (c - p) @ d / L2)); return np.linalg.norm(p + t * d - c) < r


def seg_cross(p1, p2, p3, p4):
    d = lambda a, b, c: (c[0] - a[0]) * (b[1] - a[1]) - (c[1] - a[1]) * (b[0] - a[0])  # noqa: E731
    d1, d2, d3, d4 = d(p3, p4, p1), d(p3, p4, p2), d(p1, p2, p3), d(p1, p2, p4)
    return (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0)


placed, leaders, PAD, missing = [], [], 1.5, []
tex = (lambda w: w.replace("&", r"\&").replace("_", r"\_")) if plt.rcParams["text.usetex"] else (lambda w: w)  # noqa: E731


def place(v, max_dist, outward=False, relax=False):
    txt = tex(", ".join(nodes[v]["words"].split(", ")[:2]))
    t = ax.text(0, 0, txt, fontsize=FS); b = t.get_window_extent(R); w, h = b.width, b.height; t.remove()
    c = px[v]; best = None
    out_ang = np.arctan2(c[1] - cpx[1], c[0] - cpx[0])
    side = 0.0 if c[0] >= cpx[0] else np.pi  # ring topics: label straight out to the side, next to the circle
    angs = np.deg2rad(np.arange(0, 360, 10)) if not outward else side + np.deg2rad(np.array([0, 8, -8, 16, -16]))
    for dist in np.arange(rad[v] + 2, max_dist, 3):
        for ang in angs:
            ux, uy = np.cos(ang), np.sin(ang); ax_ = c[0] + ux * dist; ay_ = c[1] + uy * dist
            x0 = ax_ if ux >= -0.2 else ax_ - w
            if abs(ux) < 0.2:
                x0 = ax_ - w / 2
            y0 = ay_ - h / 2 + uy * h / 2
            bx = (x0 - PAD, y0 - PAD, x0 + w + PAD, y0 + h + PAD)
            if bx[0] < fx0 or bx[1] < fy0 or bx[2] > fx1 or bx[3] > fy1:
                continue
            if any(box_hits_circle(bx, px[u], rad[u]) for u in pos):
                continue
            over = sum(seg_hits_box(p, q, bx) for p, q in seg) if LINKS_OK else 0
            if over and not LINKS_OK:
                continue
            if any(not (bx[2] < o[0] or bx[0] > o[2] or bx[3] < o[1] or bx[1] > o[3]) for o in placed) or any(seg_hits_box(a_, b_, bx) for a_, b_ in leaders):
                continue
            anchor = (min(max(c[0], bx[0]), bx[2]), min(max(c[1], bx[1]), bx[3])); start = (c[0] + ux * rad[v], c[1] + uy * rad[v])
            if not relax and any(seg_circle(start, anchor, px[u], rad[u]) for u in pos if u != v):
                continue  # (relax: a leader may pass behind circles; leaders are drawn under the circles)
            if any(seg_cross(start, anchor, a_, b_) for a_, b_ in leaders) or any(seg_hits_box(start, anchor, o) for o in placed):
                continue
            cross = sum(seg_cross(start, anchor, p, q) for p, q in seg if not (np.allclose(p, c) or np.allclose(q, c)))
            if not LINKS_OK and any(seg_hits_box(p, q, bx) for p, q in seg):
                continue
            score = (cross * 25 + over * 12 + dist, cross + over)
            if best is None or score < best[0]:
                best = (score, bx, start, anchor, dist)
        if best is not None and best[0][1] == 0:
            break
    if best is None:
        if not relax:
            return place(v, max_dist, outward, relax=True)
        missing.append(v); return
    _, bx, start, anchor, dist = best; placed.append(bx)
    inv = tr.inverted(); tx, ty = inv.transform((bx[0] + PAD, bx[1] + PAD))
    ax.text(tx, ty, txt, fontsize=FS, ha="left", va="bottom", zorder=4, color="#0b0b0b", bbox=dict(facecolor="white", edgecolor="none", pad=0.4, alpha=0.9) if LINKS_OK else None)
    if dist > rad[v] + 7:
        leaders.append((start, anchor)); (sx_, sy_), (ex_, ey_) = inv.transform(start), inv.transform(anchor)
        ax.plot([sx_, ex_], [sy_, ey_], color="#7a7974", lw=0.45, zorder=1.5)  # above the links, below the circles


for v in ring_labels:  # ring first, close to their circles and outward, so the inside stays free for the network labels
    place(v, rad[v] + (60 if NO_ISO else 16), outward=not NO_ISO)
for v in main_labels:
    place(v, 110 if NO_ISO else 170)  # full version: shorter leaders, so no label ends up far from its circle
print("small groups along their links:", [chain(g) for g in groups], "| non-neighbour links:", sum(1 for g in groups for x in g for y in gadj[x] & set(g) if abs(chain(g).index(x) - chain(g).index(y)) > 1) // 2)
print(f"labels placed: {len(placed)} of {len(ring_labels) + len(main_labels)}; leaders {len(leaders)}; no spot for: "
      + ", ".join(f"[{v}] {nodes[v]['words'].split(', ')[0]}" for v in missing))

def cname(c):  # name from the community's topics, as in the Results text
    w = {nodes[v]["words"].split(", ")[0] for v in lay if nodes[v]["community"] == c}
    if "rfk-jr" in w or "trump" in w: return "Politics and vaccines"
    if "pufa" in w and "olive-oil" in w: return "Specific oils and omega-6"
    if "ldl" in w and "keto" in w: return "Keto, saturated fat, cholesterol and calories"
    if "seed-oil" in w and "science" in w: return "Seed-oil talk, science, doctors and money"
    if "butter" in w and "tallow" in w: return "Cooking fats, other diets and shopping"
    return f"community {c}"
names = {c: cname(c) for c in COLOURED}
hand = [Line2D([], [], marker="o", ls="", ms=5, color=COL[c], label=names[c]) for c in COLOURED] + \
       [Line2D([], [], marker="o", ls="", ms=5, color=GREY, label="other topic communities" + ("" if NO_ISO else " (at the sides: topics with no significant link)"))]
fig.legend(handles=hand, loc="lower center", ncol=3, frameon=False, fontsize=8, bbox_to_anchor=(0.5, 0.0), handletextpad=0.3, columnspacing=2.0)
for ext in ("pdf", "png"):
    fig.savefig(f"seedoils/figures/{OUT}.{ext}", dpi=300)
print(f"wrote seedoils/figures/{OUT}.pdf / .png")
