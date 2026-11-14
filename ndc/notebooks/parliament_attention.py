"""H13: parliamentary climate attention vs emission trend (ParlaMint, 2015-2022). Pre-declared in ndc/PLAN.md 'ROUND 4'.
Run from final_project/:  ./.venv-nlp/bin/python ndc/notebooks/parliament_attention.py
"""
import glob
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

PM = Path("data/processed/parlamint"); PROC = Path("ndc/data/processed")
ISO = dict(AT="AUT", BA="BIH", BE="BEL", BG="BGR", CZ="CZE", DK="DNK", EE="EST", ES="ESP", FI="FIN", FR="FRA", GB="GBR", GR="GRC", HR="HRV", HU="HUN",
           IS="ISL", IT="ITA", LV="LVA", NL="NLD", NO="NOR", PL="POL", PT="PRT", RS="SRB", SE="SWE", SI="SVN", TR="TUR", UA="UKR")
EU27 = {"AUT", "BEL", "BGR", "CZE", "DNK", "EST", "ESP", "FIN", "FRA", "GRC", "HRV", "HUN", "ITA", "LVA", "NLD", "POL", "PRT", "SVN", "SWE"}
rows = []
for f in sorted(glob.glob(str(PM / "index_*.csv.gz"))):
    d = pd.read_csv(f, usecols=["country", "date", "role", "words", "n_climate"])
    d = d[(d.words >= 50) & (d.role != "Chairperson")]
    d["year"] = d.date.str[:4].astype(int)
    g = d.groupby("year").agg(speeches=("words", "size"), climate=("n_climate", lambda x: (x > 0).sum()))
    g["share"] = g.climate / g.speeches; g["cc"] = d.country.iloc[0]
    rows.append(g.reset_index())
Y = pd.concat(rows); Y["iso"] = Y.cc.map(ISO)
Y.to_csv(PROC / "parliament_climate_attention_by_year.csv", index=False)
Y = Y[Y.speeches >= 200]                                    # drop thin country-years (partial coverage)

E = pd.read_csv(PROC / "emissions_cw_long.csv"); E = E[E.sector == "Total excluding LULUCF"].pivot_table(index="iso", columns="year", values="mtco2e")
C = pd.read_csv(PROC / "controls.csv").set_index("iso")
tr = lambda a, b: 100 * ((E[b] / E[a]) ** (1 / (b - a)) - 1)
A = Y.groupby("iso").apply(lambda g: pd.Series({
    "att_1519": g[g.year.between(2015, 2019)].share.mean(), "years_1519": g.year.between(2015, 2019).sum(),
    "att_1517": g[g.year.between(2015, 2017)].share.mean(), "att_2022": g[g.year.between(2020, 2022)].share.mean()}), include_groups=False)
A["t1519"] = tr(2015, 2019).reindex(A.index); A["t1722"] = tr(2017, 2022).reindex(A.index)
A["lgdp"] = np.log(C.loc[A.index, "gdppc_ppp"]); A["eu"] = A.index.isin(EU27)
A["d_att"] = A.att_2022 - A.att_1517
print(A.round(3).sort_values("att_1519").to_string())


def partial(x, y, z):
    R = stats.rankdata; M = np.column_stack([np.ones(len(x)), R(z)])
    ex = R(x) - M @ np.linalg.lstsq(M, R(x), rcond=None)[0]; ey = R(y) - M @ np.linalg.lstsq(M, R(y), rcond=None)[0]
    r = np.corrcoef(ex, ey)[0, 1]; df = len(x) - 3; t = r * np.sqrt(df / (1 - r * r)); return r, t, df


P = A.dropna(subset=["att_1519", "t1519", "lgdp"])
r0 = stats.spearmanr(P.att_1519, P.t1519)[0]; r, t, df = partial(P.att_1519.values, P.t1519.values, P.lgdp.values)
print(f"\n== H13 PRIMARY (n={len(P)}): attention 2015-19 vs emission trend 2015-19: raw Spearman {r0:+.2f}; partial on log GDPpc {r:+.2f}, one-sided p (negative) = {stats.t.cdf(t, df):.4f}")
print(f"   attention vs log GDPpc: Spearman {stats.spearmanr(P.att_1519, P.lgdp)[0]:+.2f};  trend vs log GDPpc {stats.spearmanr(P.t1519, P.lgdp)[0]:+.2f}")
for lab, g in [("EU members", P[P.eu]), ("non-EU", P[~P.eu])]:
    if len(g) >= 5: print(f"   {lab:10s} n={len(g):2d}: Spearman attention vs trend {stats.spearmanr(g.att_1519, g.t1519)[0]:+.2f}")
Q = A.dropna(subset=["d_att", "t1722", "lgdp"])
r2, t2, df2 = partial(Q.d_att.values, Q.t1722.values, Q.lgdp.values)
print(f"== H13 SECONDARY (n={len(Q)}): change in attention (2020-22 minus 2015-17) vs trend 2017-22: raw {stats.spearmanr(Q.d_att, Q.t1722)[0]:+.2f};"
      f" partial {r2:+.2f}, two-sided p = {2 * stats.t.sf(abs(t2), df2):.4f}")
print(f"   median attention 2015-17 {Q.att_1517.median():.3f} -> 2020-22 {Q.att_2022.median():.3f}; rose in {(Q.d_att > 0).sum()}/{len(Q)}")
A.to_csv(PROC / "parliament_attention_vs_trend.csv")
