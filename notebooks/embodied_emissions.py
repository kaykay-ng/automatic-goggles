"""Do imports hide emissions? Production-based vs trade-adjusted ("consumption-based") emissions for meat, eggs, cereals.

Run from final_project/:  ../.venv/bin/python notebooks/embodied_emissions.py

Method (per country c, per food k, means over 2015-2022):
  PBA   = FAO farm-gate emissions of k produced in c                      (FAO 'Emissions (CO2eq) (AR5)', kt)
  E_imp = sum over exporter p of  imports(p -> c, k) * intensity(p, k)     (FAO emissions intensity, kg CO2eq/kg)
  E_exp = exports(c -> any, k) * intensity(c, k)
  CBA   = PBA - E_exp + E_imp                                             ("trade-adjusted footprint")
Foods covered: cattle, pig, sheep, goat, chicken, buffalo meat; hen eggs; cereals (incl. rice, primary).
NOT covered (no usable conversion): dairy products, fruit/veg, oilseeds, sugar, processed foods, fish, ducks/geese/turkey.
Known limits: intensities are FAO farm-gate (no feed production, no land-use change) so pig/poultry look cleaner than
life-cycle numbers; meat trade is product weight, intensities are per kg carcass-equivalent; re-exports (NL, BE) are treated as
production of the exporter's own intensity; missing partner intensities are filled with the item's median across countries.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
sys.path.insert(0, str(Path(__file__).parent))
from profile_faostat import CODE_BY_M49, M49, m49

RAW = Path("data/raw"); PROC = Path("data/processed")
YEARS = [f"Y{y}" for y in range(2015, 2023)]
ISO_BY_M49 = CODE_BY_M49

# trade CPC prefix -> intensity item name prefix
MAP = [("21111", "Meat of cattle"), ("21112", "Meat of buffalo"), ("21113", "Meat of pig"), ("21115", "Meat of sheep"),
       ("21116", "Meat of goat"), ("21121", "Meat of chickens"), ("0231", "Hen eggs"), ("0113", "Rice"),
       ("0111", "Cereals excluding rice"), ("0112", "Cereals excluding rice"), ("0114", "Cereals excluding rice"),
       ("0115", "Cereals excluding rice"), ("0116", "Cereals excluding rice"), ("0117", "Cereals excluding rice"),
       ("0118", "Cereals excluding rice"), ("0119", "Cereals excluding rice")]
KIND = {"Meat of cattle": "meat", "Meat of buffalo": "meat", "Meat of pig": "meat", "Meat of sheep": "meat",
        "Meat of goat": "meat", "Meat of chickens": "meat", "Hen eggs": "eggs", "Rice": "cereals",
        "Cereals excluding rice": "cereals"}


def intensity_tables():
    d = pd.read_csv(RAW / "Environment_Emissions_intensities_E_All_Data/Environment_Emissions_intensities_E_All_Data_NOFLAG.csv",
                    encoding="latin-1")
    d["m49"] = m49(d["Area Code (M49)"])
    d["k"] = d["Item"].map(lambda s: next((v for _, v in MAP if s.startswith(v) or s.replace(",", "").startswith(v)), None))
    d = d[d["k"].notna()]
    d["v"] = d[YEARS].mean(axis=1)
    get = lambda el: d[d.Element == el].groupby(["m49", "k"])["v"].mean()
    return get("Emissions intensity"), get("Emissions (CO2eq) (AR5)") * 1000, get("Production")   # I, PBA (t CO2eq), prod t


def trade_scan():
    f = PROC / "trade_covered_foods.csv"
    if f.exists():
        return pd.read_csv(f)
    ic = pd.read_csv(RAW / "Trade_DetailedTradeMatrix_E_All_Data/Trade_DetailedTradeMatrix_E_ItemCodes.csv", encoding="latin-1")
    ic["cpc"] = ic["CPC Code"].astype(str).str.lstrip("'")
    ic["k"] = ic["cpc"].map(lambda c: next((v for p, v in MAP if c.startswith(p)), None))
    kmap = ic.dropna(subset=["k"]).set_index("Item Code")["k"]
    print("trade items mapped:", len(kmap), "->", sorted(set(kmap)))
    cols = ["Reporter Country Code (M49)", "Partner Country Code (M49)", "Item Code", "Element", "Unit"] + YEARS
    parts = []
    for ch in pd.read_csv(RAW / "Trade_DetailedTradeMatrix_E_All_Data/Trade_DetailedTradeMatrix_E_All_Data_NOFLAG.csv",
                          usecols=cols, chunksize=500_000, encoding="latin-1", low_memory=False):
        ch["iso"] = m49(ch["Reporter Country Code (M49)"]).map(ISO_BY_M49)
        ch["k"] = ch["Item Code"].map(kmap)
        ch = ch[ch["iso"].notna() & ch["k"].notna() & (ch["Unit"] == "t") & ch["Element"].isin(["Import quantity", "Export quantity"])]
        ch["partner"] = m49(ch["Partner Country Code (M49)"])
        ch["t"] = ch[YEARS].fillna(0).mean(axis=1)
        parts.append(ch.groupby(["iso", "partner", "k", "Element"], as_index=False)["t"].sum())
    out = pd.concat(parts).groupby(["iso", "partner", "k", "Element"], as_index=False)["t"].sum()
    out.to_csv(f, index=False)
    return out


if __name__ == "__main__":
    I, PBA, PROD = intensity_tables()
    T = trade_scan()
    med = I.groupby("k").median()
    print("global median intensity (kg CO2eq/kg):", med.round(2).to_dict())

    iso_m49 = {v: k for k, v in CODE_BY_M49.items()}
    imp = T[T.Element == "Import quantity"].copy()
    exp = T[T.Element == "Export quantity"].copy()
    key = lambda df, col: list(zip(df[col], df.k))
    imp["I"] = [I.get(kk, np.nan) for kk in key(imp, "partner")]
    miss_share = imp.loc[imp.I.isna(), "t"].sum() / imp.t.sum()
    imp["I"] = imp["I"].fillna(imp.k.map(med))
    imp["emb"] = imp.t * imp.I
    exp["m49"] = exp.iso.map(iso_m49)
    exp["I"] = [I.get(kk, np.nan) for kk in zip(exp.m49, exp.k)]
    exp["I"] = exp["I"].fillna(exp.k.map(med))
    exp["emb"] = exp.t * exp.I
    print(f"import tonnage with imputed partner intensity: {miss_share:.1%}")

    rows = []
    for iso, m in iso_m49.items():
        for k in sorted(set(v for _, v in MAP)):
            pb = PBA.get((m, k), 0.0) or 0.0
            ei = imp[(imp.iso == iso) & (imp.k == k)].emb.sum()
            ee = exp[(exp.iso == iso) & (exp.k == k)].emb.sum()
            ti = imp[(imp.iso == iso) & (imp.k == k)].t.sum()
            te = exp[(exp.iso == iso) & (exp.k == k)].t.sum()
            ia = ei / ti if ti else np.nan
            rows.append(dict(iso=iso, k=k, kind=KIND[k], PBA=pb, E_imp=ei, E_exp=ee, imp_t=ti, exp_t=te,
                             prod_t=PROD.get((m, k), 0.0) or 0.0, I_dom=I.get((m, k), np.nan), I_imp_avg=ia))
    R = pd.DataFrame(rows)
    R["CBA"] = R.PBA - R.E_exp + R.E_imp
    R.to_csv(PROC / "embodied_emissions_by_food.csv", index=False)

    pop = pd.read_csv(PROC / "country_trade_emissions.csv", index_col=0)["pop"]
    C = R.groupby("iso")[["PBA", "E_imp", "E_exp", "CBA", "imp_t", "exp_t", "prod_t"]].sum()
    C["pop"] = pop
    for c in ("PBA", "CBA", "E_imp", "E_exp"):
        C[c + "_pc"] = C[c] * 1000 / C["pop"]        # kg CO2eq per person per year
    C["shift_pct"] = 100 * (C.CBA - C.PBA) / C.PBA
    C["import_dep"] = C.imp_t / (C.prod_t + C.imp_t - C.exp_t)
    C.to_csv(PROC / "embodied_emissions_by_country.csv")
    pd.set_option("display.width", 200)
    print("\n== Country table (kg CO2eq per person per year; covered foods only)")
    print(C[["PBA_pc", "E_imp_pc", "E_exp_pc", "CBA_pc", "shift_pct", "import_dep"]].round(1).sort_values("shift_pct").to_string())
    print("\nSpearman PBA_pc vs CBA_pc:", f"{spearmanr(C.PBA_pc, C.CBA_pc)[0]:+.2f}",
          "| rank movers:", C.assign(r0=C.PBA_pc.rank(ascending=False), r1=C.CBA_pc.rank(ascending=False))
          .assign(move=lambda d: d.r0 - d.r1).sort_values("move")["move"].astype(int).to_dict())
    print("\n== MECHANICAL check: import dependence vs adjustment (sign is built in):",
          f"{spearmanr(C.import_dep, C.shift_pct)[0]:+.2f}")

    print("\n== NOT mechanical: do importers buy from dirtier or cleaner producers than themselves? (import-weighted avg intensity / domestic)")
    S = R[(R.imp_t > 1000) & R.I_dom.notna()].copy()
    S["ratio"] = S.I_imp_avg / S.I_dom
    for k, g in S.groupby("k"):
        print(f"  {k:24s} median ratio {g.ratio.median():.2f}  (n={len(g)}; >1 = imports dirtier than home production; "
              f"{(g.ratio > 1).mean():.0%} of countries)")
    print("\nlargest share of footprint embodied in imports (E_imp / CBA):")
    C["imp_share"] = 100 * C.E_imp / C.CBA
    print(C.imp_share.sort_values(ascending=False).round(0).head(6).to_dict())
    print("by food kind, all 26 countries (Mt CO2eq):")
    print((R.groupby("kind")[["PBA", "E_imp", "E_exp", "CBA"]].sum() / 1e6).round(1).to_string())
