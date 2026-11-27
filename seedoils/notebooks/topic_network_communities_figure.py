"""Paper figure (27 Nov, user: make the communities clearer): the topic co-writing network with a COMMUNITY LAYOUT. Same network as
topic_network_figure.py (topics as nodes, a link when more people wrote in both topics than chance), main connected component (85 topics).
Layout: each Louvain community is laid out on its own (Kamada-Kawai inside the community) inside a disc whose size grows with the number of
topics; the discs start at the communities' centres in the all-years layout (rotated so politics is on the right), are pushed apart until they
do not overlap, and the picture is stretched to a wide format. Each community is drawn with a shaded outline and its name (identity is not
carried by colour alone: the three-colour palette is validated for three hues only); links inside a community are darker than links between
communities. Labels: the five politics topics, the hubs and the largest topic of each community, placed by the same collision search as the
other network figures (no label on a circle, link, other label or leader line). Text by LaTeX in Latin Modern.
Output: seedoils/figures/topic_network_communities.pdf/.png and paper/figures/topic_network_communities.pdf.
Run from the repo root:  PATH=/Library/TeX/texbin:$PATH ./.venv-nlp/bin/python seedoils/notebooks/topic_network_communities_figure.py"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402
from scipy.spatial import ConvexHull  # noqa: E402

plt.rcParams.update({"text.usetex": True, "font.family": "serif", "font.size": 8,
                     "text.latex.preamble": r"\usepackage[T1]{fontenc}\usepackage{lmodern}"})
P = Path("seedoils/data/processed")
T = json.loads((P / "topic_cooccurrence_network.json").read_text()); C = json.loads((P / "topic_network_centrality.json").read_text())
nodes = {n["topic"]: n for n in T["nodes"]}; lay0 = {int(k): np.array(v, float) for k, v in C["layout"].items()}
names = {int(k): v for k, v in C["community_names"].items()}
COL = dict(zip(C["coloured_communities"], ["#2a78d6", "#eb6834", "#1baf7a"])); GREY, FS = "#9d9c95", 6.6
G = nx.Graph(); G.add_nodes_from(lay0); G.add_edges_from((e["a"], e["b"], {"lift": e["lift"]}) for e in T["edges_all"] if e["a"] in lay0 and e["b"] in lay0)
comm = {v: nodes[v]["community"] for v in lay0}; groups = {}
for v, c in comm.items():
    groups.setdefault(c, []).append(v)
groups = dict(sorted(groups.items(), key=lambda kv: -len(kv[1])))

# ---- community centres from the all-years layout, rotated (politics right, bottom) as in the other figures
M = np.array([lay0[v] for v in lay0]); mu = M.mean(0); evec = np.linalg.eigh(np.cov((M - mu).T))[1][:, ::-1]
rot = lambda p: (p - mu) @ evec  # noqa: E731
pol = [v for v in lay0 if nodes[v]["theme"] == "Politics"]
sx = -1 if np.mean([rot(lay0[v])[0] for v in pol]) < 0 else 1; sy = -1 if np.mean([rot(lay0[v])[1] for v in pol]) > 0 else 1
cen = {c: np.mean([rot(lay0[v]) * [sx, sy] for v in vs], axis=0) for c, vs in groups.items()}
RAD = {c: 0.135 * np.sqrt(len(vs)) for c, vs in groups.items()}  # disc radius grows with the number of topics
# inside each community: Kamada-Kawai on its own links (distance 1/lift), scaled into its disc
pos = {}
for c, vs in groups.items():
    H = G.subgraph(vs)
    if len(vs) == 1:
        loc = {vs[0]: np.zeros(2)}
    else:
        Hd = nx.Graph(H); Hd.add_edges_from((a, b, {"d": 1 / d["lift"]}) for a, b, d in H.edges(data=True))
        loc = nx.kamada_kawai_layout(Hd, weight="d") if nx.is_connected(Hd) else nx.spring_layout(Hd, seed=1)
        P_ = np.array(list(loc.values())); P_ -= P_.mean(0); P_ /= max(np.abs(P_).max(), 1e-9); loc = {v: P_[i] for i, v in enumerate(loc)}
    for v, q in loc.items():
        pos[v] = q * RAD[c] * 0.85
# push the discs apart (keep them near their start), then stretch horizontally
# 27 Nov: communities on a RING (ellipse), ordered so that strongly linked communities are neighbours; the bands between non-neighbours
# then run as chords through the empty middle instead of across other communities. Order (clockwise from bottom right): Politics, Diet,
# Omega-6, Oils, Shopping, Home cooking -- every neighbour pair is a real link.
RING = ["Politics, distrust and evidence", "Diet, weight and saturated fat", "Omega-6 and animal foods", "Oils and cooking fats", "Shopping", "Home cooking and sugar"]
ANG = dict(zip(RING, np.deg2rad([-25, 35, 95, 150, 210, 270])))
byname = {names.get(c): c for c in groups}
EA, EB = 2.25, 1.22
for nm, a_ in ANG.items():
    if nm in byname:
        cen[byname[nm]] = np.array([EA * np.cos(a_), EB * np.sin(a_)])
GAP = 0.09
for _ in range(400):
    moved = False
    for a in groups:
        for b in groups:
            if a < b:
                d = cen[b] - cen[a]; dist = np.hypot(*d); need = RAD[a] + RAD[b] + GAP
                if dist < need:
                    u = d / dist if dist > 1e-9 else np.array([1.0, 0]); cen[a] = cen[a] - u * (need - dist) / 2; cen[b] = cen[b] + u * (need - dist) / 2; moved = True
    if not moved:
        break
for v in pos:
    pos[v] = pos[v] + cen[comm[v]]
# the two small groups linked only among themselves (27 Nov, user: move them further so it is clear): short zigzags, each in the emptiest
# spot that is at least FAR away from every topic and link of the main network
FAR = 0.42; SMALL_NAMES = {}
links_all = [(e["a"], e["b"], e["lift"]) for e in T["edges_all"]]
for g in sorted(C["small_components"], key=len):
    g = sorted(g, key=lambda t: -nodes[t]["docs"]); adj = {t: {b_ for a_, b_, _ in links_all if a_ == t and b_ in g} | {a_ for a_, b_, _ in links_all if b_ == t and a_ in g} for t in g}
    order = [min(g, key=lambda t: len(adj[t]))]
    while len(order) < len(g):
        nx_ = [u for u in adj[order[-1]] if u not in order] or [u for u in g if u not in order]; order.append(nx_[0])
    rel = {t: np.array([(i - (len(order) - 1) / 2) * 0.13, 0.04 * (1 if i % 2 == 0 else -1)]) for i, t in enumerate(order)}
    P0 = np.array([pos[v] for v in pos if v in lay0]); lo, hi = P0.min(0), P0.max(0); best = None
    k_small = sum(1 for c in groups if c not in [nodes[t]["community"] for t in lay0])  # groups already placed
    shop = cen[byname["Shopping"]]  # in the empty space below Shopping, left of Home cooking, one above the other
    best = (0, shop[0] + 0.05, shop[1] - 0.62 - 0.42 * k_small)
    segs = [(pos[a_], pos[b_]) for a_, b_ in G.edges()]
    for cx in np.linspace(lo[0] - 0.2, hi[0] + 0.2, 60):
        for cy in np.linspace(lo[1] - 0.45, hi[1] + 0.1, 40):
            pts = [np.array([cx, cy]) + r for r in rel.values()]
            dmin = min(min(np.linalg.norm(q - v_) for v_ in P0) for q in pts)
            dseg = min(min(np.linalg.norm(a_ + max(0, min(1, (q - a_) @ (b_ - a_) / max((b_ - a_) @ (b_ - a_), 1e-12))) * (b_ - a_) - q) for a_, b_ in segs) for q in pts)
            sc = min(dmin, dseg + 0.1)
            if False:
                best = (abs(cy - lo[1]) + 0.3 * abs(cx - lo[0]), cx, cy)
    for t, r in rel.items():
        pos[t] = np.array([best[1], best[2]]) + r; comm[t] = nodes[t]["community"]
    c_ = nodes[g[0]]["community"]; groups[c_] = g
    SMALL_NAMES[c_] = "Separate group: skin, ice cream and additives" if 10 in g else "Separate group: mayo and dressing" if 7 in g else \
        "Separate group: " + " and ".join(nodes[t]["words"].split(", ")[0] for t in order[:2])
    G.add_nodes_from(g); G.add_edges_from((a_, b_, {"lift": l_}) for a_, b_, l_ in links_all if a_ in g and b_ in g)
names.update(SMALL_NAMES)
P_ = np.array(list(pos.values())); x_lo, y_lo = P_.min(0) - 0.22; x_hi, y_hi = P_.max(0) + 0.22
W_IN = 7.0; AX_H = W_IN * (y_hi - y_lo) / (x_hi - x_lo); LEG = 0.15; H_IN = AX_H + LEG
fig = plt.figure(figsize=(W_IN, H_IN)); ax = fig.add_axes([0, LEG / H_IN, 1, AX_H / H_IN]); ax.set_aspect("equal"); ax.axis("off")
ax.set_xlim(x_lo, x_hi); ax.set_ylim(y_lo, y_hi)
size = {v: 6 + 0.03 * nodes[v]["docs"] for v in pos}
fig.canvas.draw(); scale = ax.transData.transform((1, 0))[0] - ax.transData.transform((0, 0))[0]
rr = {v: (np.sqrt(size[v]) / 2 * fig.dpi / 72 + 2.0) / scale for v in pos}
for _ in range(3000):  # no stacked circles (inside communities)
    moved = False; vs_ = list(pos)
    for i_, a in enumerate(vs_):
        for b in vs_[i_ + 1:]:
            d = pos[b] - pos[a]; dist = np.hypot(*d); need = rr[a] + rr[b]
            if dist < need - 1e-6:
                u = d / dist if dist > 1e-9 else np.array([1.0, 0]); pos[a] = pos[a] - u * (need - dist) / 2; pos[b] = pos[b] + u * (need - dist) / 2; moved = True
    if not moved:
        break
col = lambda c: COL.get(c, GREY)  # noqa: E731
# community outlines (convex hull of the circles, padded) with names
hull_boxes = []; HULL = {}
for c, vs in groups.items():
    pts = np.array([pos[v] + (rr[v] + 0.03) * np.array([np.cos(t), np.sin(t)]) for v in vs for t in np.linspace(0, 2 * np.pi, 16, endpoint=False)])
    hpts = pts[ConvexHull(pts).vertices]; HULL[c] = hpts
    ax.add_patch(Polygon(hpts, closed=True, facecolor=col(c), alpha=0.10, edgecolor=col(c), linewidth=0.8, joinstyle="round", zorder=0))
    ax.add_patch(Polygon(hpts, closed=True, facecolor="none", edgecolor=col(c), alpha=0.6, linewidth=0.8, joinstyle="round", zorder=0.5))
# option 1 (27 Nov): links INSIDE a community drawn one by one; links BETWEEN two communities bundled into one band (width ~ sqrt(number of links))
MAIN = [c for c, vs in groups.items() if len(vs) >= 5]
intra = [(a, b) for a, b in G.edges() if comm[a] == comm[b]]
for a, b in intra:
    ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color=col(comm[a]), lw=0.6, alpha=0.55, zorder=1)
from collections import Counter  # noqa: E402
BAND = Counter(tuple(sorted((comm[a], comm[b]))) for a, b in G.edges() if comm[a] != comm[b] and comm[a] in MAIN and comm[b] in MAIN)
ccen = {c: np.mean([pos[v] for v in groups[c]], axis=0) for c in groups}


def exit_point(c, q):  # where the straight line from community c's centre towards q leaves c's outline
    o = ccen[c]; d = q - o; best_t = 1.0; H = HULL[c]
    for k in range(len(H)):
        p1, p2 = H[k], H[(k + 1) % len(H)]; e = p2 - p1; den = d[0] * e[1] - d[1] * e[0]
        if abs(den) < 1e-12:
            continue
        t = ((p1[0] - o[0]) * e[1] - (p1[1] - o[1]) * e[0]) / den; u = ((p1[0] - o[0]) * d[1] - (p1[1] - o[1]) * d[0]) / den
        if 0 <= t <= 1 and 0 <= u <= 1:
            best_t = min(best_t, t)
    return o + best_t * d


BANDS = []
for (a, b), n in BAND.items():
    pa, pb = exit_point(a, ccen[b]), exit_point(b, ccen[a]); lw = 1.3 * np.sqrt(n)
    ax.plot([pa[0], pb[0]], [pa[1], pb[1]], color="#b9b8b0", lw=lw, alpha=0.75, solid_capstyle="butt", zorder=0.6); BANDS.append((a, b, n, pa, pb, lw))
for v in sorted(pos, key=lambda v: -nodes[v]["docs"]):
    pol_ = nodes[v]["theme"] == "Politics"  # the five politics topics: dark ring, so they stand out inside their community
    ax.scatter(*pos[v], s=size[v], color=col(comm[v]), edgecolors="#0b0b0b" if pol_ else "white", linewidths=1.0 if pol_ else 0.6, zorder=2)
fig.canvas.draw(); R = fig.canvas.get_renderer(); tr = ax.transData; inv = tr.inverted()
px = {v: tr.transform(pos[v]) for v in pos}; rad = {v: np.sqrt(size[v]) / 2 * fig.dpi / 72 + 1.5 for v in pos}
seg = [(px[a], px[b]) for a, b in intra]
for a, b, n, pa, pb, lw in BANDS:  # a band is wide: keep labels off its whole width
    A_, B_ = tr.transform(pa), tr.transform(pb); d = B_ - A_; nrm = np.array([-d[1], d[0]]) / max(np.hypot(*d), 1e-9); half = lw * fig.dpi / 72 / 2 + 1
    seg += [(A_ + k * half * nrm, B_ + k * half * nrm) for k in (-1, 0, 1)]
fx0, fy0, fx1, fy1 = ax.bbox.x0, ax.bbox.y0, ax.bbox.x1, ax.bbox.y1


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


def free(bx):
    if bx[0] < fx0 or bx[1] < fy0 or bx[2] > fx1 or bx[3] > fy1:
        return False
    if any(box_hits_circle(bx, px[u], rad[u]) for u in pos) or any(seg_hits_box(p, q, bx) for p, q in seg):
        return False
    return not any(not (bx[2] < o[0] or bx[0] > o[2] or bx[3] < o[1] or bx[1] > o[3]) for o in placed) and not any(seg_hits_box(a_, b_, bx) for a_, b_ in leaders)


# number of links on each band, in a small white box at its middle (the band's own label)
band_bad = 0
for a_, b_, n, pa, pb, lw in BANDS:
    for fr in (0.5, 0.42, 0.58, 0.34, 0.66, 0.26, 0.74, 0.2, 0.8):
        q = pa + fr * (pb - pa); t = ax.text(*q, str(n), fontsize=6.4, ha="center", va="center", zorder=3, bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="#b9b8b0", lw=0.4))
        bb = t.get_window_extent(R); box = (bb.x0 - 1, bb.y0 - 1, bb.x1 + 1, bb.y1 + 1)
        ok_ = not any(box_hits_circle(box, px[u], rad[u]) for u in pos) and not any(not (box[2] < o[0] or box[0] > o[2] or box[3] < o[1] or box[1] > o[3]) for o in placed)
        if ok_:
            placed.append(box); break
        t.remove()
    else:
        band_bad += 1
# check: does any band cross the outline of a third community?
from matplotlib.path import Path as MPath  # noqa: E402
cross_bad = [(names.get(a_), names.get(b_), names.get(c)) for a_, b_, n, pa, pb, lw in BANDS for c in MAIN if c not in (a_, b_)
             if MPath(HULL[c]).contains_points([pa + f * (pb - pa) for f in np.linspace(0.02, 0.98, 60)]).any()]
print("bands crossing a third community:", cross_bad or "none", "| band counts without a free spot:", band_bad)
# community names: bold, placed just outside the top of each outline (search upward / sideways for a free spot)
for c, vs in groups.items():
    txt = r"\textbf{" + names.get(c, "").replace("&", r"\&") + "}" if c in names else None
    if not txt:
        continue
    t = ax.text(0, 0, txt, fontsize=7.4); b = t.get_window_extent(R); w, h = b.width, b.height; t.remove()
    top = max(pos[v][1] + rr[v] for v in vs); bot = min(pos[v][1] - rr[v] for v in vs); cx = np.mean([pos[v][0] for v in vs])
    btop, bbot = tr.transform((cx, top)), tr.transform((cx, bot)); done = False
    cands = [(btop[0] + dx, btop[1] + dy) for dy in np.arange(6, 90, 3) for dx in (0, -30, 30, -60, 60, -100, 100, -150, 150)] + \
            [(bbot[0] + dx, bbot[1] - dy - h) for dy in np.arange(6, 90, 3) for dx in (0, -30, 30, -60, 60, -100, 100, -150, 150)]
    for x_, y_ in cands:
        bx = (x_ - w / 2 - PAD, y_ - PAD, x_ + w / 2 + PAD, y_ + h + PAD)
        if free(bx):
            placed.append(bx); tx, ty = inv.transform((bx[0] + PAD, bx[1] + PAD)); ax.text(tx, ty, txt, fontsize=7.4, color="#0b0b0b", zorder=5); done = True; break
    if not done:
        missing.append(f"name of community {c}")


def place(v, max_dist=110):  # short leaders only: a label that does not fit near its circle is left out
    txt = ", ".join(nodes[v]["words"].split(", ")[:2]).replace("&", r"\&").replace("_", r"\_")
    t = ax.text(0, 0, txt, fontsize=FS); b = t.get_window_extent(R); w, h = b.width, b.height; t.remove(); c = px[v]; best = None
    for relax in (False, True):
        for dist in np.arange(rad[v] + 2, max_dist, 3):
            for ang in np.deg2rad(np.arange(0, 360, 10)):
                ux, uy = np.cos(ang), np.sin(ang); ax_, ay_ = c[0] + ux * dist, c[1] + uy * dist
                x0 = ax_ - w / 2 if abs(ux) < 0.2 else (ax_ if ux > 0 else ax_ - w); y0 = ay_ - h / 2 + uy * h / 2
                bx = (x0 - PAD, y0 - PAD, x0 + w + PAD, y0 + h + PAD)
                if not free(bx):
                    continue
                anchor = (min(max(c[0], bx[0]), bx[2]), min(max(c[1], bx[1]), bx[3])); start = (c[0] + ux * rad[v], c[1] + uy * rad[v])
                if not relax and any(seg_circle(start, anchor, px[u], rad[u]) for u in pos if u != v):
                    continue
                if any(seg_cross(start, anchor, a_, b_) for a_, b_ in leaders) or any(seg_hits_box(start, anchor, o) for o in placed):
                    continue
                cross = sum(seg_cross(start, anchor, p, q) for p, q in seg if not (np.allclose(p, c) or np.allclose(q, c)))
                sc = (cross * 25 + dist, cross)
                if best is None or sc < best[0]:
                    best = (sc, bx, start, anchor, dist)
            if best is not None and best[0][1] == 0:
                break
        if best is not None:
            break
    if best is None:
        missing.append(txt); return
    _, bx, start, anchor, dist = best; placed.append(bx); tx, ty = inv.transform((bx[0] + PAD, bx[1] + PAD))
    ax.text(tx, ty, txt, fontsize=FS, color="#0b0b0b", zorder=4)
    if dist > rad[v] + 7:
        leaders.append((start, anchor)); (sx_, sy_), (ex_, ey_) = inv.transform(start), inv.transform(anchor); ax.plot([sx_, ex_], [sy_, ey_], color="#7a7974", lw=0.45, zorder=1.5)


POL = [v for v in pos if nodes[v]["theme"] == "Politics"]
HUBS = [4, 1, 14, 0, 24, 9, 17, 37, 12, 2]
TOPS = [max(vs, key=lambda v: nodes[v]["docs"]) for vs in groups.values() if len(vs) >= 3]
SMALL = [t for g in C["small_components"] for t in g]
for v in list(dict.fromkeys(POL + HUBS + TOPS + SMALL)):
    place(v, 170 if v in HUBS else 110)  # hubs may reach a little further
print(f"communities drawn: {[(names.get(c, c), len(vs)) for c, vs in groups.items()]}; labels missing: {missing}")
json.dump({"centres": {int(c): [float(x) for x in ccen[c]] for c in groups}, "topics": {int(c): len(vs) for c, vs in groups.items()},
           "inside_links": {int(c): int(sum(1 for a_, b_ in intra if comm[a_] == c)) for c in groups},
           "bands": [[int(a_), int(b_), int(n)] for a_, b_, n, *_ in BANDS], "names": {int(c): names.get(c, "") for c in groups},
           "colours": {int(c): col(c) for c in groups}, "members": {int(c): [int(v) for v in vs] for c, vs in groups.items()}},
          open(P / "topic_network_communities_layout.json", "w"), indent=1)
for out in ("seedoils/figures/topic_network_communities.pdf", "seedoils/figures/topic_network_communities.png", "paper/figures/topic_network_communities.pdf"):
    fig.savefig(out, dpi=300)
print("wrote seedoils/figures/topic_network_communities.pdf/.png and paper/figures/topic_network_communities.pdf")
