"""Round-3 hypotheses H8 (firm vs hedged wording -> emission trend) and H10 (language neighbours share trajectories). Design pre-declared in ndc/PLAN.md 'ROUND 3'.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python ndc/notebooks/ndc_round3.py
"""
import re, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).parent))
import ndc_common as D
from ndc_embed import clean
import networkx as nx


def knn_graph(S, k=5):                                            # same as ndc_network.knn_graph (that module runs on import)
    G = nx.Graph(); G.add_nodes_from(range(S.shape[0]))
    for i in range(S.shape[0]):
        for j in [j for j in np.argsort(-S[i]) if j != i][:k]:
            G.add_edge(i, j)
    return G

RNG = np.random.default_rng(314)
nodes, PROC, TOT = D.nodes, D.PROC, D.TOT
E = pd.read_csv(PROC / "emissions_cw_long.csv"); E = E[E.sector == TOT].pivot_table(index="iso", columns="year", values="mtco2e")
E.loc["EUU"] = E.loc[[c for c in D.EU27 if c in E.index]].sum()


def trend(a, b):
    return 100 * ((E[b] / E[a]) ** (1 / (b - a)) - 1)


tr = pd.DataFrame({"t1519": trend(2015, 2019), "t1523": trend(2015, 2023), "t0515": trend(2005, 2015), "e15": E[2015]}).reindex(nodes)
big = (tr.e15 >= 1) & tr[["t1519", "t1523", "t0515"]].notna().all(1)
print(f"trend sample: {big.sum()} of {len(nodes)} nodes (dropped <1 Mt or missing: {sorted(tr.index[~big])})")

# ---------------- H8 ----------------
FIRM = [r"\bcommit(?:s|ted|ment|ments)?\b", r"\bunconditional(?:ly)?\b", r"\bbinding\b", r"\bnet[- ]zero\b|\bcarbon[- ]neutral\w*|\bclimate[- ]neutral\w*",
        r"\beconomy[- ]wide\b", r"\babsolute\b", r"\bwill (?:reduce|achieve|cut|limit)\b"]
HEDGE = [r"\bconditional\b", r"\bsubject to\b", r"\bprovided that\b", r"\binternational (?:support|finance|assistance|funding)\b",
         r"\bbusiness[- ]as[- ]usual\b|\bBAU\b", r"\bdepend(?:s|ent|ing)? on\b"]
T = pd.read_csv(PROC / "ndc_text_long.csv"); T = T[T.document == "first_ndc"]
docs = {}
for iso, g in T.groupby("iso"):
    seen, parts = set(), []
    for v in g.value:
        c = clean(v)
        if c and c not in seen: seen.add(c); parts.append(c)
    docs[iso] = " ".join(parts)
cnt = lambda pats, t: sum(len(re.findall(p, t, flags=re.I)) for p in pats)
F = pd.DataFrame({"firm": [cnt(FIRM, docs[i]) for i in nodes], "hedge": [cnt(HEDGE, docs[i]) for i in nodes],
                  "words": [len(docs[i].split()) for i in nodes]}, index=nodes)
F["firmness"] = np.log((F.firm + 1) / (F.hedge + 1))
F = F.join(tr); F["lgdp"] = D.lg; F["income"] = D.inc; F["region"] = D.reg


def partial_spearman(x, y, ctl):
    R = lambda v: stats.rankdata(v)
    A = np.column_stack([np.ones(len(x))] + [R(c) for c in ctl])
    ex = R(x) - A @ np.linalg.lstsq(A, R(x), rcond=None)[0]; ey = R(y) - A @ np.linalg.lstsq(A, R(y), rcond=None)[0]
    r = np.corrcoef(ex, ey)[0, 1]; df = len(x) - 2 - len(ctl); t = r * np.sqrt(df / (1 - r * r))
    return r, stats.t.cdf(t, df)                                  # one-sided p for NEGATIVE


S = F[big.values]
print(f"\n== H8 firm vs hedged wording (n={len(S)}); firm matches median {S.firm.median():.0f}, hedged {S.hedge.median():.0f}")
print(f"   firmness vs log GDPpc: Spearman {stats.spearmanr(S.firmness, S.lgdp)[0]:+.2f}; 2015-19 trend vs log GDPpc {stats.spearmanr(S.t1519, S.lgdp)[0]:+.2f}")
print(f"   raw Spearman firmness vs 2015-19 trend: {stats.spearmanr(S.firmness, S.t1519)[0]:+.2f}")
for col, lab in [("t1519", "PRIMARY 2015-19"), ("t1523", "secondary 2015-23")]:
    r, p = partial_spearman(S.firmness.values, S[col].values, [S.lgdp.values, S.t0515.values])
    print(f"   {lab}: partial rho (ctl log GDPpc, 2005-15 trend) = {r:+.3f}, one-sided p (negative) = {p:.4f}")
print("   by income group (raw Spearman firmness vs 2015-19 trend):")
for g, sg in S.groupby("income"):
    if len(sg) >= 10: print(f"      {g:22s} n={len(sg):3d} rho={stats.spearmanr(sg.firmness, sg.t1519)[0]:+.2f}  median firmness {sg.firmness.median():+.2f}")
# hand-check sample
rng = np.random.default_rng(5); rows = []
for kind, pats in [("firm", FIRM), ("hedge", HEDGE)]:
    hits = [(i, m.start()) for i in nodes for p in pats for m in re.finditer(p, docs[i], flags=re.I)]
    for k in rng.choice(len(hits), 10, replace=False):
        i, s = hits[k]; rows.append((kind, i, docs[i][max(0, s - 110): s + 110].replace("\n", " ")))
pd.DataFrame(rows, columns=["kind", "iso", "context"]).to_csv(PROC / "round3_h8_handcheck.csv", index=False)
F.to_csv(PROC / "round3_firmness.csv")

# exploratory: pledge type vs trend; firmness vs on-track
I = pd.read_csv(PROC / "ndc_indicators_long.csv"); ty = I[(I.document == "first_ndc") & (I.indicator == "GHG target type")].drop_duplicates("iso").set_index("iso").value
S2 = S.assign(type=[ty.get(i, "missing") for i in S.index])
S2["type"] = S2["type"].astype(str).str.replace(r"<[^>]+>", "", regex=True).str.slice(0, 40)
print("\n   EXPLORATORY: 2015-19 trend by first-NDC GHG target type (median %/yr, n):")
for t, g in S2.groupby("type"):
    if len(g) >= 4: print(f"      {t:42s} n={len(g):3d} median trend {g.t1519.median():+.2f}  median log GDPpc {g.lgdp.median():.2f}")
PP = pd.read_csv(PROC / "ndc_pledge_progress.csv")
if "on_track" in PP:
    pp = PP.set_index("iso").join(F[["firmness"]], how="inner")
    print(f"   EXPLORATORY: firmness among checkable pledges, on track vs not: {pp[pp.on_track == True].firmness.median():+.2f} (n={int((pp.on_track == True).sum())}) vs "
          f"{pp[pp.on_track != True].firmness.median():+.2f} (n={int((pp.on_track != True).sum())})")

# ---------------- H10 ----------------
idx = np.where(big.values)[0]
y = tr.t1519.values.copy(); lo, hi = np.nanpercentile(y[idx], [2.5, 97.5]); y = np.clip(y, lo, hi)
reg = D.reg


def neigh_stat(G, yv, sel):
    own, nb = [], []
    sset = set(sel)
    for i in sel:
        ns = [j for j in G.neighbors(i) if j in sset]
        if ns: own.append(yv[i]); nb.append(np.mean(yv[ns]))
    return np.corrcoef(own, nb)[0, 1]


def perm_test(G, label):
    obs = neigh_stat(G, y, idx)
    n1, n2 = [], []
    for _ in range(5000):
        yp = y.copy(); yp[idx] = RNG.permutation(y[idx]); n1.append(neigh_stat(G, yp, idx))
        yp = y.copy()
        for r in np.unique(reg[idx]):
            m = idx[reg[idx] == r]; yp[m] = RNG.permutation(y[m])
        n2.append(neigh_stat(G, yp, idx))
    n1, n2 = np.array(n1), np.array(n2)
    print(f"   {label}: r(own, neighbour mean) = {obs:+.3f} | NULL1 shuffle all: mean {n1.mean():+.3f}, p={(1 + (n1 >= obs).sum()) / 5001:.4f}"
          f" | NULL2 shuffle within region: mean {n2.mean():+.3f}, p={(1 + (n2 >= obs).sum()) / 5001:.4f}")
    return obs


print(f"\n== H10 do language neighbours share 2015-19 trends? (n={len(idx)}, winsorised to [{lo:.1f}, {hi:.1f}] %/yr)")
GL = knn_graph(D.L, 5); perm_test(GL, "language kNN (PRIMARY)")
GG = knn_graph(-D.dist, 5); perm_test(GG, "geography kNN (comparison)")
GE = knn_graph(D.M, 5); perm_test(GE, "emission-profile kNN (comparison)")
