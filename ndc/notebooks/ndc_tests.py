"""NDC project: pre-declared tests H1-H3 (see ndc/PLAN.md 'DESIGN v1').
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python ndc/notebooks/ndc_tests.py
"""
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

PROC = Path("ndc/data/processed"); RNG = np.random.default_rng(2026)
ROUND = "first_ndc"
V = np.load(PROC / f"ndc_vectors_{ROUND}.npy"); IDX = pd.read_csv(PROC / f"ndc_index_{ROUND}.csv")
isos = list(IDX.iso); words = dict(zip(IDX.iso, IDX.n_words))

# ---- EU collapse: identical joint-INDC texts ----
S0 = V @ V.T; n0 = len(isos); i_eu = isos.index("EUU")
comp, stack = set(), [i_eu]
while stack:                                   # transitive closure: texts linked by cosine > 0.98 (as in ndc_validate.py)
    a = stack.pop()
    if a in comp: continue
    comp.add(a); stack += [j for j in range(n0) if S0[a, j] > 0.98 and j not in comp]
EU_GROUP = {isos[j] for j in comp}
EU27 = EU_GROUP - {"EUU", "GBR"}
print(f"EU joint-text group: {len(EU_GROUP)} entries (EU27 members {len(EU27)} + EUU + GBR in first_ndc) -> one node 'EUU'")

C = pd.read_csv(PROC / "controls.csv").set_index("iso")
E = pd.read_csv(PROC / "emissions_cw_long.csv"); E15 = E[E.year == 2015].pivot_table(index="iso", columns="sector", values="mtco2e")
SEC = {"energy": "Energy", "industry": "Industrial Processes", "agriculture": "Agriculture", "waste": "Waste",
       "land_forest": "Land Use, Land-Use Change and Forestry"}
TOT = "Total excluding LULUCF"
eu_em = E15.loc[[c for c in EU27 if c in E15.index]].sum()
E15.loc["EUU"] = eu_em
pop_eu = C.loc[[c for c in EU27 if c in C.index], "pop"]
C.loc["EUU"] = dict(name="European Union", region="Europe & Central Asia", income="High income", lat=50.85, lon=4.35, pop=pop_eu.sum(),
                    gdppc_ppp=float(np.average(C.loc[pop_eu.index, "gdppc_ppp"].fillna(C.loc[pop_eu.index, "gdppc_ppp"].mean()), weights=pop_eu)))
H = pd.read_csv(PROC / "happiness.csv").set_index("iso")
H.loc["EUU"] = H.loc[[c for c in EU27 if c in H.index]].mean()

keep = [i for i in isos if i not in EU_GROUP or i == "EUU"]
ok = [i for i in keep if i in E15.index and i in C.index and E15.loc[i, [TOT] + list(SEC.values())].notna().all() and E15.loc[i, TOT] > 0
      and pd.notna(C.loc[i, "gdppc_ppp"]) and pd.notna(C.loc[i, "lat"]) and pd.notna(C.loc[i, "pop"])]
print(f"nodes: {len(ok)} (of {len(keep)} after EU collapse; dropped for missing emissions/controls: {sorted(set(keep) - set(ok))})")
nodes = ok; n = len(nodes); row = {i: isos.index(i) for i in nodes}
Vn = V[[row[i] for i in nodes]]
Vc = Vn - Vn.mean(0); Vc /= np.linalg.norm(Vc, axis=1, keepdims=True); L = Vc @ Vc.T
iu = np.triu_indices(n, 1)


def z(x): return (x - np.nanmean(x, 0)) / np.nanstd(x, 0)
def eucl_sim(X): return -np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))
def pair(f): return np.array([[f(a, b) for b in range(n)] for a in range(n)], float)

em = E15.loc[nodes]
prof = np.column_stack([em["Energy"] / em[TOT], em["Industrial Processes"] / em[TOT], em["Agriculture"] / em[TOT], em["Waste"] / em[TOT],
                        np.clip(em[SEC["land_forest"]] / em[TOT], -1, 1)])
M = eucl_sim(z(prof))
lg = np.log(C.loc[nodes, "gdppc_ppp"].values)
reg = np.asarray(C.loc[nodes, "region"].astype(str).tolist(), dtype=object); inc = np.asarray(C.loc[nodes, "income"].astype(str).tolist(), dtype=object)
lat, lon = np.radians(C.loc[nodes, "lat"].values), np.radians(C.loc[nodes, "lon"].values)
def hav(a, b):
    h = np.sin((lat[b] - lat[a]) / 2) ** 2 + np.cos(lat[a]) * np.cos(lat[b]) * np.sin((lon[b] - lon[a]) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(h))
dist = np.maximum(pair(hav), 1.0)
lw = np.log10(np.array([words[i] for i in nodes], float)); lp = np.log10(C.loc[nodes, "pop"].values)
feat = {"emission_similarity": M, "income_gap": np.abs(lg[:, None] - lg[None, :]), "same_region": (reg[:, None] == reg[None, :]).astype(float),
        "same_income_group": (inc[:, None] == inc[None, :]).astype(float), "log_distance": np.log(dist),
        "log_pop_product": lp[:, None] + lp[None, :], "log_words_product": lw[:, None] + lw[None, :]}


def dsp(Smat, names, X, n_perm=5000):
    y = Smat[iu]; ys = (y - y.mean()) / y.std()
    Xs = (X - X.mean(0)) / X.std(0); A = np.column_stack([np.ones(len(ys)), Xs])
    coef = np.linalg.lstsq(A, ys, rcond=None)[0]; r2 = 1 - ((ys - A @ coef) ** 2).sum() / (ys ** 2).sum()
    Xr, nrm = [], []
    for k in range(Xs.shape[1]):
        oth = np.column_stack([np.ones(len(ys))] + [Xs[:, j] for j in range(Xs.shape[1]) if j != k])
        xr = Xs[:, k] - oth @ np.linalg.lstsq(oth, Xs[:, k], rcond=None)[0]; Xr.append(xr); nrm.append(xr @ xr)
    Xr = np.array(Xr); nrm = np.array(nrm); bobs = Xr @ ys / nrm
    cnt = np.zeros(len(names))
    for _ in range(n_perm):
        p = RNG.permutation(Smat.shape[0]); yp = (Smat[p][:, p])[iu]; yp = (yp - yp.mean()) / yp.std()
        cnt += np.abs(Xr @ yp / nrm) >= np.abs(bobs)
    return {nm: (coef[k + 1], (1 + cnt[k]) / (n_perm + 1)) for k, nm in enumerate(names)}, r2


def report(title, res, r2, focus):
    print(f"\n{title}   R^2={r2:.3f}   dyads={len(iu[0])}")
    for nm, (b, p) in res.items():
        print(f"   {nm:22s} beta={b:+.3f}  p={p:.4f}" + ("   <-- tested" if nm == focus else ""))


names = list(feat); X = np.column_stack([feat[k][iu] for k in names])
print(f"\nlanguage similarity (centred cosine): mean {L[iu].mean():+.3f}, sd {L[iu].std():.3f}; raw Spearman with emission similarity {stats.spearmanr(L[iu], M[iu])[0]:+.3f}")
res, r2 = dsp(L, names, X); report("H1: L ~ emission similarity + controls (predicted POSITIVE on emission_similarity)", res, r2, "emission_similarity")
for k in ["no controls"]:
    r, p = stats.spearmanr(L[iu], M[iu]); print(f"   (for reference) emission similarity alone: Spearman {r:+.3f}")

# ---- H2: happiness ----
hv = ["ladder", "f_gdp", "f_social", "f_health", "f_freedom", "f_generosity", "f_corruption"]
has = [k for k, i in enumerate(nodes) if i in H.index and H.loc[i, hv].notna().all()]
print(f"\nnodes with happiness data: {len(has)} of {n}")
sub = np.array(has); Hm = eucl_sim(z(H.loc[[nodes[k] for k in has], hv].values))
Ls = L[np.ix_(sub, sub)]; iu_s = np.triu_indices(len(sub), 1)
featS = {k: v[np.ix_(sub, sub)] for k, v in feat.items()}; featS["happiness_similarity"] = Hm
iu_save = iu; iu = iu_s
namesS = list(featS); XS = np.column_stack([featS[k][iu_s] for k in namesS])
resS, r2S = dsp(Ls, namesS, XS); report("H2: L ~ emission + HAPPINESS similarity + controls (TWO-SIDED test on happiness_similarity)", resS, r2S, "happiness_similarity")
base = [k for k in namesS if k != "happiness_similarity"]
resB, r2B = dsp(Ls, base, np.column_stack([featS[k][iu_s] for k in base]), n_perm=2000)
print(f"   same subset WITHOUT happiness: R^2={r2B:.3f}; emission_similarity beta={resB['emission_similarity'][0]:+.3f}; happiness raw Spearman with L: {stats.spearmanr(Ls[iu_s], Hm[iu_s])[0]:+.3f}; with income gap: {stats.spearmanr(featS['income_gap'][iu_s], Hm[iu_s])[0]:+.3f}")
iu = iu_save

# ---- H3: say vs do (country level) ----
SE = pd.read_csv(PROC / "ndc_sector_emphasis.csv"); SE = SE[SE["round"] == ROUND].set_index("iso")
print("\nH3: does NDC text emphasis on a sector follow the sector's actual share of emissions? (partial Spearman, controls log words + log GDPpc; Holm over 5)")
rows = []
for s, col in SEC.items():
    share = (em[col] / em[TOT]).values; emph = np.array([SE.loc[i, s] if i in SE.index else np.nan for i in nodes])
    ok_ = ~np.isnan(emph)
    ctl = np.column_stack([np.ones(ok_.sum()), stats.rankdata(lw[ok_]), stats.rankdata(lg[ok_])])
    rx = stats.rankdata(emph[ok_]); ry = stats.rankdata(share[ok_])
    ex = rx - ctl @ np.linalg.lstsq(ctl, rx, rcond=None)[0]; ey = ry - ctl @ np.linalg.lstsq(ctl, ry, rcond=None)[0]
    r = np.corrcoef(ex, ey)[0, 1]; df = ok_.sum() - 2 - 2; t = r * np.sqrt(df / (1 - r * r)); p1 = stats.t.sf(t, df)       # one-sided (predicted positive)
    rows.append((s, ok_.sum(), stats.spearmanr(emph[ok_], share[ok_])[0], r, p1))
ps = np.array([r[4] for r in rows]); order = np.argsort(ps); adj = np.empty(len(ps)); run = 0
for rank, i in enumerate(order):
    run = max(run, (len(ps) - rank) * ps[i]); adj[i] = min(run, 1)
for (s, nn, raw, par, p1), a in zip(rows, adj):
    print(f"   {s:12s} n={nn}  raw rho={raw:+.2f}  partial rho={par:+.2f}  one-sided p={p1:.4f}  Holm p={a:.4f}")

pd.DataFrame({"iso": nodes, "words": [words[i] for i in nodes], "region": reg, "income": inc, "gdppc": np.exp(lg)}).to_csv(PROC / "ndc_nodes.csv", index=False)
np.save(PROC / "ndc_language_similarity_first_ndc.npy", L)
