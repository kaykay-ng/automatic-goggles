"""Are the biggest food exporters the biggest emitters, once size and own consumption are considered?

Run from final_project/:  ../.venv/bin/python notebooks/exporters_vs_emitters.py
Step 1 scans the raw FAOSTAT trade matrix for WORLDWIDE exports/imports (all partners, not only the 26) of each of the
26 countries, by commodity group, tonnes/yr (mean 2015-22). Step 2 relates them to production-side emissions (FAO
'Farm gate', 'Emissions from livestock') and domestic food supply.
Caveats built in: summing tonnes over raw + processed items double counts; NL/BE are re-export hubs (exports != own
production); emissions are production-based (not embodied in what is eaten).
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
sys.path.insert(0, str(Path(__file__).parent))
from build_trade_networks import PREFIX2GROUP, GROUPS
from profile_faostat import CODE_BY_M49, m49

RAW = Path("data/raw/Trade_DetailedTradeMatrix_E_All_Data")
PROC = Path("data/processed")
YEARS = [f"Y{y}" for y in range(2015, 2023)]


def world_totals():
    f = PROC / "world_trade_totals.csv"
    if f.exists():
        return pd.read_csv(f)
    ic = pd.read_csv(RAW / "Trade_DetailedTradeMatrix_E_ItemCodes.csv", encoding="latin-1")
    ic["group"] = ic["CPC Code"].astype(str).str.lstrip("'").str[:3].map(PREFIX2GROUP)
    gmap = ic.set_index("Item Code")["group"]
    cols = ["Reporter Country Code (M49)", "Item Code", "Element", "Unit"] + YEARS
    parts = []
    for ch in pd.read_csv(RAW / "Trade_DetailedTradeMatrix_E_All_Data_NOFLAG.csv", usecols=cols,
                          chunksize=500_000, encoding="latin-1", low_memory=False):
        ch["iso"] = m49(ch["Reporter Country Code (M49)"]).map(CODE_BY_M49)
        ch = ch[ch["iso"].notna() & (ch["Unit"] == "t") & ch["Element"].isin(["Export quantity", "Import quantity"])]
        ch["group"] = ch["Item Code"].map(gmap)
        ch = ch[ch["group"].notna()]
        ch["t"] = ch[YEARS].fillna(0).mean(axis=1)
        parts.append(ch.groupby(["iso", "group", "Element"], as_index=False)["t"].sum())
    out = pd.concat(parts).groupby(["iso", "group", "Element"], as_index=False)["t"].sum()
    out.to_csv(f, index=False)
    return out


def resid(y, x):
    b = np.polyfit(x, y, 1)
    return y - np.polyval(b, x)


def sp(a, b):
    r, p = spearmanr(a, b)
    return f"rho={r:+.2f} (p={p:.3f})"


if __name__ == "__main__":
    W = world_totals()
    P = W.pivot_table(index="iso", columns="Element", values="t", aggfunc="sum")
    A = pd.read_csv(PROC / "country_attributes.csv", index_col=0)
    em = pd.read_csv(PROC / "emissions_co2eq_parlamint.csv").set_index(["iso", "Item"])
    f = pd.read_csv(PROC / "fbs_parlamint.csv")
    pop = f[f.Item == "Population"].set_index("iso")[YEARS].mean(axis=1) * 1000
    mean = lambda item: em.xs(item, level="Item")[YEARS].mean(axis=1) * 1000      # t CO2eq
    T = pd.DataFrame({"pop": pop, "exports_t": P["Export quantity"], "imports_t": P["Import quantity"],
                      "farmgate_t": mean("Farm gate"), "livestock_t": mean("Emissions from livestock"),
                      "agrifood_t": mean("Agrifood systems")})
    T["net_exp_kg_pc"] = (T.exports_t - T.imports_t) * 1000 / T["pop"]
    T["exports_kg_pc"] = T.exports_t * 1000 / T["pop"]
    T["farmgate_pc"] = T.farmgate_t / T["pop"]
    kcal_yr = A["kcal_pc_day"] * T["pop"] * 365
    T["farmgate_g_per_1000kcal_eaten"] = T.farmgate_t * 1e6 / (kcal_yr / 1000)
    T.to_csv(PROC / "country_trade_emissions.csv")
    lp = np.log10(T["pop"])

    print("== Top 8 exporters (worldwide tonnes) and where they rank on farm-gate emissions (1 = highest)")
    r = T.assign(exp_rank=T.exports_t.rank(ascending=False), em_rank=T.farmgate_t.rank(ascending=False),
                 net_rank=T.net_exp_kg_pc.rank(ascending=False))
    print(r.sort_values("exports_t", ascending=False).head(8)[
        ["exports_t", "farmgate_t", "exp_rank", "em_rank", "net_exp_kg_pc"]].assign(
        exports_Mt=lambda d: d.exports_t / 1e6, farmgate_Mt=lambda d: d.farmgate_t / 1e6).round(1)[
        ["exports_Mt", "farmgate_Mt", "exp_rank", "em_rank", "net_exp_kg_pc"]].to_string())

    print("\n== Q1 Absolute: exporters vs emitters (size drives both)")
    print("exports vs farm-gate emissions:", sp(T.exports_t, T.farmgate_t))
    print("population vs farm-gate emissions:", sp(T["pop"], T.farmgate_t), "| population vs exports:", sp(T["pop"], T.exports_t))
    print("exports vs farm-gate, size removed (residuals on log pop):",
          sp(resid(np.log10(T.exports_t), lp), resid(np.log10(T.farmgate_t), lp)))

    print("\n== Q2 Per person / own consumption")
    print("exports per capita vs farm-gate emissions per capita:", sp(T.exports_kg_pc, T.farmgate_pc))
    print("NET exports per capita vs farm-gate emissions per capita:", sp(T.net_exp_kg_pc, T.farmgate_pc))
    print("NET exports per capita vs farm-gate emissions per 1000 kcal eaten domestically:",
          sp(T.net_exp_kg_pc, T.farmgate_g_per_1000kcal_eaten))
    print("\nTop/bottom 5 by net exports per capita (kg/person) and emissions per 1000 kcal eaten (g CO2eq):")
    s = T.sort_values("net_exp_kg_pc", ascending=False)[["net_exp_kg_pc", "farmgate_pc", "farmgate_g_per_1000kcal_eaten"]].round(1)
    print(pd.concat([s.head(5), s.tail(5)]).to_string())

    print("\n== Q3 By commodity group: net exports per capita vs the matching emissions")
    G = W.pivot_table(index=["iso"], columns=["group", "Element"], values="t", aggfunc="sum")
    for grp, em_col, label in [("meat", "livestock_t", "livestock emissions pc"), ("dairy_eggs", "livestock_t", "livestock emissions pc"),
                               ("cereals", "farmgate_t", "farm-gate emissions pc")]:
        ne = (G[(grp, "Export quantity")] - G[(grp, "Import quantity")]) * 1000 / T["pop"]
        print(f"{grp:11s} net exports pc vs {label}:", sp(ne, T[em_col] / T["pop"]),
              "| top net exporters:", list(ne.sort_values(ascending=False).head(4).index))
