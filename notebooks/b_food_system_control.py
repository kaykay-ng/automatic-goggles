"""Common-cause test (explanation A): is the trade-language link explained by countries having SIMILAR FOOD SYSTEMS?
EXPLORATORY (not pre-declared). Run from final_project/ with the NLP environment:
  ./.venv-nlp/bin/python notebooks/b_food_system_control.py
Food-system distance between two countries = Euclidean distance between standardised profiles from FAOSTAT food balance sheets:
  diet_distance   : kcal shares by food group (cereals, roots, sugar, pulses/nuts, veg/fruit, oils, alcohol, meat, dairy/eggs, fish)
  supply_distance : self-sufficiency, feed, export, import and loss shares (country_food_profile.csv, 12 features)
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import b_language_network as B
from b_language_network import NODES, IU, RNG, FAMILY
from gravity_null import D as DIST, SAME_EU, REGION

PROC = Path("data/processed")
S = np.load(PROC / "b_language_similarity.npy"); logT = B.dyad_matrices(); n = len(NODES)
F = pd.read_csv(PROC / "country_food_profile.csv", index_col=0).reindex(NODES)
F = F.fillna(F.median())
diet_cols = [c for c in F if c.startswith("kcal_")]; supply_cols = [c for c in F if not c.startswith("kcal_")]
Z = (F - F.mean()) / F.std(ddof=0)


def pdist(cols):
    X = Z[cols].values
    return np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))


reg = np.array([REGION[c] for c in NODES]); fam = np.array([FAMILY[c] for c in NODES])
feat = {"log_trade": logT, "log_distance": np.log(DIST), "same_region": (reg[:, None] == reg[None, :]).astype(float),
        "same_family": ((fam[:, None] == fam[None, :]) & (fam[:, None] != "Mixed")).astype(float), "both_EU": SAME_EU,
        "diet_distance": pdist(diet_cols), "supply_distance": pdist(supply_cols)}
col = lambda k: feat[k][IU]
y = S[IU]; ys = (y - y.mean()) / y.std()


def fit(names, n_perm=5000):
    X = np.column_stack([col(k) for k in names]); Xs = (X - X.mean(0)) / X.std(0)
    A = np.column_stack([np.ones(len(ys)), Xs]); coef = np.linalg.lstsq(A, ys, rcond=None)[0]
    r2 = 1 - ((ys - A @ coef) ** 2).sum() / (ys ** 2).sum()
    perms = [RNG.permutation(n) for _ in range(n_perm)]
    Yp = []
    for p in perms:
        v = (S[p][:, p])[IU]; Yp.append((v - v.mean()) / v.std())
    res = {}
    for k, nm in enumerate(names):
        oth = np.column_stack([np.ones(len(ys))] + [Xs[:, j] for j in range(len(names)) if j != k])
        xr = Xs[:, k] - oth @ np.linalg.lstsq(oth, Xs[:, k], rcond=None)[0]
        b = (xr @ ys) / (xr @ xr); bp = np.array([(xr @ v) / (xr @ xr) for v in Yp])
        res[nm] = (b, (1 + (np.abs(bp) >= abs(b)).sum()) / (n_perm + 1))
    return res, r2


base = ["log_distance", "same_region", "same_family", "both_EU"]
print("correlations among dyad variables (Pearson): trade vs diet distance %+.2f | trade vs supply distance %+.2f | language similarity vs diet distance %+.2f | vs supply distance %+.2f" % (
    np.corrcoef(col("log_trade"), col("diet_distance"))[0, 1], np.corrcoef(col("log_trade"), col("supply_distance"))[0, 1],
    np.corrcoef(y, col("diet_distance"))[0, 1], np.corrcoef(y, col("supply_distance"))[0, 1]))
models = [("M1 pre-declared model", ["log_trade"] + base),
          ("M2 + diet distance", ["log_trade"] + base + ["diet_distance"]),
          ("M3 + supply-profile distance", ["log_trade"] + base + ["supply_distance"]),
          ("M4 + both food-system distances", ["log_trade"] + base + ["diet_distance", "supply_distance"])]
out = {}
for lab, names in models:
    res, r2 = fit(names); out[lab] = res
    print(f"\n{lab}   R^2={r2:.3f}")
    for nm in names:
        b, p = res[nm]
        if nm in ("log_trade", "diet_distance", "supply_distance"):
            print(f"   {nm:16s} beta={b:+.3f}  p={p:.4f}")
b1 = out[models[0][0]]["log_trade"][0]; b4 = out[models[3][0]]["log_trade"][0]
print(f"\ntrade coefficient: {b1:+.3f} (M1) -> {b4:+.3f} (M4), change {100*(b4-b1)/b1:+.0f}%  (a big drop would point to a common cause; no drop means food-system similarity does not explain the trade link)")
