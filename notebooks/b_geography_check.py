"""How much of the trade-language link is just geography?  (angle B follow-up; NOT pre-declared: exploratory, report as such)

Run from final_project/ with the NLP environment:  ./.venv-nlp/bin/python notebooks/b_geography_check.py
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import b_language_network as B
from b_language_network import NODES, IU, RNG, FAMILY
from gravity_null import D as DIST, SAME_EU, REGION, CAP

PROC = Path("data/processed")
S = np.load(PROC / "b_language_similarity.npy")
logT = B.dyad_matrices()
n = len(NODES)
pop = pd.read_csv(PROC / "country_trade_emissions.csv", index_col=0)["pop"].reindex(NODES).values
reg = np.array([REGION[c] for c in NODES]); fam = np.array([FAMILY[c] for c in NODES])
lat = np.array([CAP[c][0] for c in NODES]); lon = np.array([CAP[c][1] for c in NODES])

def mat(f):
    return np.array([[f(i, j) for j in range(n)] for i in range(n)], float)

feat = {
    "log_trade": logT,
    "log_distance": np.log(DIST),
    "same_region": (reg[:, None] == reg[None, :]).astype(float),
    "same_family": ((fam[:, None] == fam[None, :]) & (fam[:, None] != "Mixed")).astype(float),
    "both_EU": SAME_EU,
    "abs_dlat": np.abs(lat[:, None] - lat[None, :]),
    "abs_dlon": np.abs(lon[:, None] - lon[None, :]),
    "log_pop_product": np.log10(pop[:, None] * pop[None, :]),
}
regpair = mat(lambda i, j: hash(tuple(sorted((reg[i], reg[j])))) % 100003)
pairs = sorted(set(regpair[IU]))
RP = np.column_stack([(regpair[IU] == p).astype(float) for p in pairs[1:]])      # region-pair fixed effects
NF = np.zeros((len(IU[0]), n - 1))                                              # node fixed effects (drop last)
for k, (i, j) in enumerate(zip(*IU)):
    for q in (i, j):
        if q < n - 1:
            NF[k, q] = 1
y = S[IU]; ys = (y - y.mean()) / y.std()


def col(name):
    return feat[name][IU]


def r2(cols):
    X = np.column_stack([np.ones(len(y))] + cols)
    res = ys - X @ np.linalg.lstsq(X, ys, rcond=None)[0]
    return 1 - (res ** 2).sum() / (ys ** 2).sum()


def dsp(cols_other, x, n_perm=5000):
    """coefficient on x (standardised) with Dekker DSP p-value, controls = cols_other (list of dyad vectors / 2-d blocks)."""
    others = np.column_stack([np.ones(len(y))] + [c if c.ndim == 2 else c[:, None] for c in cols_other]) if cols_other else np.ones((len(y), 1))
    o = np.column_stack([others[:, [0]]] + [(others[:, k] - others[:, k].mean()) / (others[:, k].std() + 1e-12)
                                           for k in range(1, others.shape[1])]) if others.shape[1] > 1 else others
    xs = (x - x.mean()) / x.std()
    xr = xs - o @ np.linalg.lstsq(o, xs, rcond=None)[0]
    b = (xr @ ys) / (xr @ xr)
    bp = []
    for _ in range(n_perm):
        p = RNG.permutation(n); yp = (S[p][:, p])[IU]; yp = (yp - yp.mean()) / yp.std()
        bp.append((xr @ yp) / (xr @ xr))
    return b, (1 + (np.abs(bp) >= abs(b)).sum()) / (n_perm + 1)


print("== A. How much of the language similarity can geography explain on its own? (R^2 across 325 country pairs)")
steps = [("log distance only", ["log_distance"]), ("+ same region", ["log_distance", "same_region"]),
         ("+ same language family", ["log_distance", "same_region", "same_family"]),
         ("+ both in EU", ["log_distance", "same_region", "same_family", "both_EU"]),
         ("+ log trade (full model)", ["log_distance", "same_region", "same_family", "both_EU", "log_trade"])]
prev = 0
for lab, names in steps:
    v = r2([col(k) for k in names])
    print(f"   {lab:28s} R^2 = {v:.3f}   (+{v-prev:.3f})"); prev = v
full = ["log_distance", "same_region", "same_family", "both_EU", "log_trade"]
print("   share of the full model's R^2 that trade ADDS beyond the four controls: "
      f"{(r2([col(k) for k in full]) - r2([col(k) for k in full[:-1]])) / r2([col(k) for k in full]):.1%}")
print("   trade ALONE (no controls): R^2 =", f"{r2([col('log_trade')]):.3f}", "| geography+family+EU WITHOUT trade:", f"{r2([col(k) for k in full[:-1]]):.3f}")

print("\n== B. How much of trade itself is geography/size? (R^2 of log trade on distance, region, EU, population product)")
tcols = ["log_distance", "same_region", "both_EU", "log_pop_product"]
Xt = np.column_stack([np.ones(len(y))] + [col(k) for k in tcols]); tt = col("log_trade")
bt = np.linalg.lstsq(Xt, tt, rcond=None)[0]; resid_trade = tt - Xt @ bt
print(f"   geography + size explain {1 - resid_trade.var() / tt.var():.1%} of the variation in log trade; correlation(log trade, log distance) = {np.corrcoef(tt, col('log_distance'))[0,1]:+.2f}")

print("\n== C. Coefficient on trade under progressively stricter geographic controls (standardised beta; DSP-MRQAP p, 5,000 perms)")
specs = [("no controls", []),
         ("distance only", ["log_distance"]),
         ("distance + region", ["log_distance", "same_region"]),
         ("+ language family + EU (the pre-declared model)", ["log_distance", "same_region", "same_family", "both_EU"]),
         ("+ population product (size)", ["log_distance", "same_region", "same_family", "both_EU", "log_pop_product"]),
         ("+ latitude/longitude gaps", ["log_distance", "same_region", "same_family", "both_EU", "log_pop_product", "abs_dlat", "abs_dlon"])]
for lab, names in specs:
    b, p = dsp([col(k) for k in names], col("log_trade"))
    print(f"   {lab:50s} beta={b:+.3f}  p={p:.4f}")
base = [col(k) for k in ["log_distance", "same_region", "same_family", "both_EU", "log_pop_product"]]
b, p = dsp(base + [RP], col("log_trade")); print(f"   {'+ region-PAIR fixed effects':50s} beta={b:+.3f}  p={p:.4f}")
b, p = dsp(base + [NF], col("log_trade")); print(f"   {'+ country fixed effects (each country its own baseline)':50s} beta={b:+.3f}  p={p:.4f}")
b, p = dsp(base + [RP, NF], col("log_trade")); print(f"   {'+ region-pair AND country fixed effects':50s} beta={b:+.3f}  p={p:.4f}")

print("\n== D. 'Excess trade': trade left over after geography and size are removed (gravity residual) vs language similarity")
b, p = dsp([], resid_trade); print(f"   excess trade alone:                 beta={b:+.3f}  p={p:.4f}")
b, p = dsp([col(k) for k in ["log_distance", "same_region", "same_family", "both_EU"]], resid_trade)
print(f"   excess trade + geography/family:    beta={b:+.3f}  p={p:.4f}")

print("\n== E. Is the trade link visible WITHIN regions and ACROSS regions? (partial Spearman controlling log distance)")
from scipy.stats import rankdata
def partial(mask):
    xr = rankdata(tt[mask]); yr = rankdata(y[mask]); dr = rankdata(col('log_distance')[mask])
    A = np.column_stack([np.ones(mask.sum()), dr])
    rx = xr - A @ np.linalg.lstsq(A, xr, rcond=None)[0]; ry = yr - A @ np.linalg.lstsq(A, yr, rcond=None)[0]
    return np.corrcoef(rx, ry)[0, 1]
same = col("same_region") == 1
print(f"   same-region dyads (n={same.sum()}): partial rho = {partial(same):+.2f} | cross-region dyads (n={(~same).sum()}): partial rho = {partial(~same):+.2f}")
for r in np.unique(reg):
    m = np.array([(reg[i] == r and reg[j] == r) for i, j in zip(*IU)])
    if m.sum() > 8:
        print(f"   inside {r:5s} (n={m.sum()}): partial rho = {partial(m):+.2f}")
