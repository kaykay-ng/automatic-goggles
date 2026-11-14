"""Round 2 tests (pre-declared in PLAN.md 'ROUND 2'): D1 cross-section with the direct measure, PP1-PP3 country-year panel.

Run from final_project/:  ../.venv/bin/python notebooks/round2_tests.py
"""
from pathlib import Path
import numpy as np, pandas as pd
import sys
sys.path.insert(0, str(Path(__file__).parent))
from country_text_vs_food_system import test, holm, country_vars

PROC = Path("data/processed")
RNG = np.random.default_rng(99)
pd.set_option("display.width", 220)

M = pd.read_csv(PROC / "parlamint/measures_country_year.csv")
Y = pd.read_csv(PROC / "country_year_food_system.csv").rename(columns={"iso": "country"})

# ---------- D1: cross-section, direct measure (v2: LEAK or FOOT or DEFOR; NEAR dropped after the precision check) ----------
import glob, re
from split_topics_patterns import AGRI, FOOD
MT = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(str(PROC / "parlamint/direct_matches_*.csv.gz")))], ignore_index=True)
MT["year"] = MT.date.str[:4].astype(int)
MT["direct3"] = ((MT.leak + MT["foot"] + MT.defor) > 0).astype(int)
MT["agrifood"] = MT.text.map(lambda t: bool(AGRI.search(t) or FOOD.search(t))).astype(int)
MT["direct3_af"] = MT.direct3 * MT.agrifood
add = MT.groupby(["country", "year"])[["direct3", "direct3_af"]].sum().reset_index().rename(columns={"direct3": "n_direct3", "direct3_af": "n_direct3_af"})
M = M.merge(add, on=["country", "year"], how="left").fillna({"n_direct3": 0, "n_direct3_af": 0})
C = M.groupby("country")[["n_speeches", "n_climate", "n_direct3", "n_direct3_af", "n_leak", "n_foot", "n_defor"]].sum()
C["n_direct_any"] = C.n_direct3
C["per1000clim_direct_any"] = 1000 * C.n_direct3 / C.n_climate
C["per1000clim_direct_af"] = 1000 * C.n_direct3_af / C.n_climate
for c in ["n_leak", "n_foot", "n_defor"]:
    C[c.replace("n_", "per1000clim_")] = 1000 * C[c] / C.n_climate
V = country_vars()
D = C.join(V, how="inner")
print("== Direct measure by country (speeches per 1,000 climate speeches); n_direct = number of matching speeches")
print(D[["n_climate", "n_direct3", "n_direct3_af", "per1000clim_direct_any", "per1000clim_direct_af", "per1000clim_leak",
         "per1000clim_foot", "per1000clim_defor", "shift_pct"]].round(1).sort_values("per1000clim_direct_any").to_string())

print("\n== D1 (pre-declared): direct_share vs shift_pct, predicted POSITIVE")
r = test(D.shift_pct, D.per1000clim_direct_any, D.log_pop, D.region)
print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
big = D[D.n_direct3 >= 30]
r2 = test(big.shift_pct, big.per1000clim_direct_any, big.log_pop, big.region)
print(f"sensitivity, only countries with >=30 direct matches (n={len(big)}):",
      {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r2.items()})
ra = test(D.shift_pct, D.per1000clim_direct_af, D.log_pop, D.region)
print("EXPLORATORY: direct matches that also mention agriculture/food:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in ra.items()})
print("components vs shift_pct (EXPLORATORY, Spearman rho):",
      {c: round(float(D[c].corr(D.shift_pct, method='spearman')), 2) for c in
       ["per1000clim_leak", "per1000clim_foot", "per1000clim_defor", "per1000clim_direct_af"]})

# ---------- Panel ----------
P = M.merge(Y, on=["country", "year"], how="inner")
P["climate_in_agri"] = P.n_agri_climate / P.n_agri.replace(0, np.nan)
P["attention_agri"] = 1e4 * P.n_agri / P.n_speeches
P["attention_food"] = 1e4 * P.n_food / P.n_speeches
print(f"\npanel: {len(P)} country-years, {P.country.nunique()} countries, years {P.year.min()}-{P.year.max()}")


def demean2(df, cols, g1="country", g2="year", iters=200):
    X = df[cols].astype(float).copy()
    for _ in range(iters):
        before = X.values.copy()
        X = X - X.groupby(df[g1]).transform("mean")
        X = X - X.groupby(df[g2]).transform("mean")
        if np.nanmax(np.abs(X.values - before)) < 1e-10:
            break
    return X


def fe_slope(df, y, x):
    d = df.dropna(subset=[y, x])
    Z = demean2(d, [y, x])
    b = (Z[x] * Z[y]).sum() / (Z[x] ** 2).sum()
    return b, Z[x].std(), Z[y].std(), len(d)


def fe_boot(df, y, x, B=2000):
    d = df.dropna(subset=[y, x])
    b0, sx, sy, n = fe_slope(d, y, x)
    countries = d.country.unique(); bs = []
    for _ in range(B):
        pick = RNG.choice(countries, len(countries))
        samp = pd.concat([d[d.country == c].assign(country=f"{c}_{k}") for k, c in enumerate(pick)])
        try:
            bs.append(fe_slope(samp, y, x)[0])
        except Exception:
            pass
    bs = np.array(bs)
    p = min(1.0, 2 * min((bs <= 0).mean(), (bs >= 0).mean()))
    std_beta = b0 * sx / sy
    return dict(n=n, beta=b0, std_beta=std_beta, ci_lo=np.percentile(bs, 2.5) * sx / sy, ci_hi=np.percentile(bs, 97.5) * sx / sy,
                p_boot=max(p, 1 / B), within_sd_x=sx, within_sd_y=sy)


tests = [("PP1", "climate_in_agri", "net_animal_exports_pc", "positive"), ("PP2", "attention_agri", "net_animal_exports_pc", "positive"),
         ("PP3", "attention_food", "food_selfsuff", "negative")]
res = []
for name, y, x, pred in tests:
    r = fe_boot(P, y, x); r.update(test=name, y=y, x=x, predicted=pred); res.append(r)
R = pd.DataFrame(res)
R["p_holm"] = holm(R.p_boot.values)
R["direction_ok"] = [(r.beta < 0) == (r.predicted == "negative") for r in R.itertuples()]
print("\n== PANEL tests (pre-declared). std_beta = change in y (in within-country SDs of y) per 1 within-country SD of x; CI by cluster bootstrap")
print(R[["test", "y", "x", "predicted", "n", "std_beta", "ci_lo", "ci_hi", "p_boot", "p_holm", "within_sd_x", "direction_ok"]].round(3).to_string(index=False))
print("\nhow much do these vary within a country across years?  within-country SD of x:",
      {t: round(float(P.groupby('country')[x].std().mean()), 2) for t, x in [("net_animal_exports_pc", "net_animal_exports_pc"), ("food_selfsuff", "food_selfsuff")]})
D.to_csv(PROC / "country_direct_measure.csv")
