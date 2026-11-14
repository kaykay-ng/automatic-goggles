"""Profile FAOSTAT files and extract the ParlaMint-country subset.

Run from final_project/:  ../.venv/bin/python notebooks/profile_faostat.py
Writes small files to data/processed/. Raw files stay untouched.
"""
import pandas as pd
from pathlib import Path

RAW = Path("data/raw")
OUT = Path("data/processed")
OUT.mkdir(parents=True, exist_ok=True)
YEARS = [f"Y{y}" for y in range(2015, 2023)]

# Sovereign countries in ParlaMint 5.0 (regional corpora ES-CT/ES-GA/ES-PV folded into Spain).
# Germany, Ireland, Switzerland etc. are NOT in ParlaMint.
M49 = {"AT": 40, "BA": 70, "BE": 56, "BG": 100, "CZ": 203, "DK": 208, "EE": 233, "ES": 724,
       "FI": 246, "FR": 250, "GB": 826, "GR": 300, "HR": 191, "HU": 348, "IS": 352, "IT": 380,
       "LV": 428, "NL": 528, "NO": 578, "PL": 616, "PT": 620, "RS": 688, "SE": 752, "SI": 705,
       "TR": 792, "UA": 804}
CODE_BY_M49 = {v: k for k, v in M49.items()}


def m49(series):
    return pd.to_numeric(series.astype(str).str.lstrip("'"), errors="coerce")


def profile_emissions():
    d = pd.read_csv(RAW / "Emissions_Totals_E_All_Data/Emissions_Totals_E_All_Data_NOFLAG.csv", encoding="latin-1")
    d["iso"] = m49(d["Area Code (M49)"]).map(CODE_BY_M49)
    sub = d[d["iso"].notna() & (d["Element"] == "Emissions (CO2eq) (AR5)")
            & d["Source"].isin(["FAO TIER 1"])]
    print("EMISSIONS countries found:", sorted(sub["iso"].unique()), len(sub["iso"].unique()))
    print("EMISSIONS sources:", d["Source"].unique())
    print("EMISSIONS agrifood items:", sorted(d.loc[d["Item"].str.contains("Food|Farm|Agrifood|Land-use", regex=True), "Item"].unique()))
    keep = sub[["iso", "Area", "Item", "Unit"] + YEARS]
    keep.to_csv(OUT / "emissions_co2eq_parlamint.csv", index=False)
    print("emissions rows kept:", len(keep), "missing in 2015-22:", keep[YEARS].isna().mean().round(2).to_dict())


def profile_fbs():
    d = pd.read_csv(RAW / "FoodBalanceSheets_E_All_Data/FoodBalanceSheets_E_All_Data_NOFLAG.csv", encoding="latin-1")
    d["iso"] = m49(d["Area Code (M49)"]).map(CODE_BY_M49)
    sub = d[d["iso"].notna()]
    print("FBS countries found:", sorted(sub["iso"].unique()), len(sub["iso"].unique()))
    print("FBS items:", d["Item"].nunique(), "e.g.", list(d["Item"].unique()[:12]))
    sub[["iso", "Area", "Item", "Element", "Unit"] + YEARS].to_csv(OUT / "fbs_parlamint.csv", index=False)


def profile_trade():
    path = RAW / "Trade_DetailedTradeMatrix_E_All_Data/Trade_DetailedTradeMatrix_E_All_Data_NOFLAG.csv"
    cols = ["Reporter Country Code (M49)", "Partner Country Code (M49)", "Item Code", "Item",
            "Element", "Unit"] + YEARS
    parts, n = [], 0
    for ch in pd.read_csv(path, usecols=cols, chunksize=500_000, encoding="latin-1", low_memory=False):
        n += len(ch)
        r = m49(ch["Reporter Country Code (M49)"]).map(CODE_BY_M49)
        p = m49(ch["Partner Country Code (M49)"]).map(CODE_BY_M49)
        keep = ch[r.notna() & p.notna() & (r != p)].copy()
        keep.insert(0, "reporter", r[keep.index])
        keep.insert(1, "partner", p[keep.index])
        parts.append(keep.drop(columns=["Reporter Country Code (M49)", "Partner Country Code (M49)"]))
    t = pd.concat(parts)
    print("TRADE total rows scanned:", n, "kept (ParlaMint pairs):", len(t))
    print("TRADE elements:", t["Element"].value_counts().to_dict())
    print("TRADE items kept:", t["Item"].nunique())
    imp = t[t["Element"] == "Import quantity"]
    print("pairs with any import qty:", imp.groupby(["reporter", "partner"]).ngroups, "of", 26 * 25)
    print("reporters:", sorted(t["reporter"].unique()))
    t.to_csv(OUT / "trade_parlamint_pairs.csv", index=False)


if __name__ == "__main__":
    profile_emissions()
    profile_fbs()
    profile_trade()
