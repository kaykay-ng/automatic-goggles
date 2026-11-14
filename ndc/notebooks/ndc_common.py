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


