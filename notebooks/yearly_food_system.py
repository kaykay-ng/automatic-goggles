"""Yearly (2015-2022) food-system variables per country, for the country-year panel.

Run from final_project/:  ../.venv/bin/python notebooks/yearly_food_system.py
Writes data/processed/country_year_food_system.csv with: net_animal_exports_pc (kg per person, meat+dairy+eggs trade groups,
worldwide partners), food_selfsuff (mean log2 production/supply over cereals, veg, fruit, meat, milk, eggs; clipped),
agrifood_tCO2eq_pc (FAO agrifood systems emissions per person), pop.
Yearly hidden-emission shift is NOT computed (the embodied estimate is an 8-year mean).
"""
from pathlib import Path
import numpy as np, pandas as pd
import sys
sys.path.insert(0, str(Path(__file__).parent))
from profile_faostat import CODE_BY_M49, m49
from food_use_profile import GROUP

PROC = Path("data/processed")
YEARS = [f"Y{y}" for y in range(2015, 2023)]

raw = pd.read_csv("data/raw/FoodBalanceSheets_E_All_Data/FoodBalanceSheets_E_All_Data_NOFLAG.csv", encoding="latin-1",
                  usecols=["Area Code (M49)", "Item Code (FBS)", "Element"] + YEARS)
raw["iso"] = m49(raw["Area Code (M49)"]).map(CODE_BY_M49)
raw["grp"] = raw["Item Code (FBS)"].str.lstrip("'").map(GROUP)
fb = raw[raw.iso.notna() & raw.grp.notna()]
pr = pd.read_csv("data/raw/FoodBalanceSheets_E_All_Data/FoodBalanceSheets_E_All_Data_NOFLAG.csv", encoding="latin-1",
                 usecols=["Area Code (M49)", "Element"] + YEARS)
pr["iso"] = m49(pr["Area Code (M49)"]).map(CODE_BY_M49)
pop = pr[pr.iso.notna() & (pr.Element == "Total Population - Both sexes")].groupby("iso")[YEARS].sum() * 1000

rows = []
for y in YEARS:
    yr = int(y[1:])
    P = fb.pivot_table(index="iso", columns=["grp", "Element"], values=y)
    ss = {}
    for g in ["cereals", "veg", "fruit", "meat", "milk", "eggs"]:
        ss[g] = np.log2((P[(g, "Production")] / P[(g, "Domestic supply quantity")]).clip(0.25, 4)).clip(-2, 2)
    s = pd.DataFrame(ss).mean(axis=1)
    for iso in P.index:
        rows.append(dict(iso=iso, year=yr, food_selfsuff=s[iso], pop=pop.loc[iso, y]))
Y = pd.DataFrame(rows)

w = pd.read_csv(PROC / "world_trade_meat_dairy_by_year.csv")
long = w.melt(id_vars=["iso", "group", "Element"], value_vars=YEARS, var_name="y", value_name="t").fillna({"t": 0})
long["year"] = long.y.str[1:].astype(int)
g = long.groupby(["iso", "year", "Element"]).t.sum().unstack()
g["net_t"] = g["Export quantity"] - g["Import quantity"]
Y = Y.merge(g[["net_t"]].reset_index(), on=["iso", "year"], how="left")
Y["net_animal_exports_pc"] = Y.net_t * 1000 / Y["pop"]

em = pd.read_csv(PROC / "emissions_co2eq_parlamint.csv")
em = em[em.Item == "Agrifood systems"].melt(id_vars=["iso"], value_vars=YEARS, var_name="y", value_name="kt")
em["year"] = em.y.str[1:].astype(int)
Y = Y.merge(em[["iso", "year", "kt"]], on=["iso", "year"], how="left")
Y["agrifood_tCO2eq_pc"] = Y.kt * 1000 / Y["pop"]
Y.drop(columns=["net_t", "kt"]).to_csv(PROC / "country_year_food_system.csv", index=False)
print(Y.groupby("year")[["net_animal_exports_pc", "food_selfsuff", "agrifood_tCO2eq_pc"]].mean().round(2).to_string())
print("within-country sd vs between-country sd (net_animal_exports_pc):",
      round(Y.groupby("iso").net_animal_exports_pc.std().mean(), 1), "vs", round(Y.groupby("iso").net_animal_exports_pc.mean().std(), 1))
print("food_selfsuff:", round(Y.groupby("iso").food_selfsuff.std().mean(), 3), "vs", round(Y.groupby("iso").food_selfsuff.mean().std(), 3))
