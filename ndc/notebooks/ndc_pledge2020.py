"""Did countries meet their 2020 pledges? Hand-extracted pledges (see ndc/PLAN.md '2020 PLEDGES') vs Climate Watch emissions in 2019 and 2020.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python ndc/notebooks/ndc_pledge2020.py"""
import json, urllib.request
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROC = Path("ndc/data/processed")
E = pd.read_csv(PROC / "emissions_cw_long.csv")
P = pd.read_csv(PROC / "ndc_pledges_parsed.csv")
EU28 = set(P[P.eu_joint].iso) - {"EUU"}
PLEDGES = {"AUS": (5, 2000), "BLR": (5, 1990), "CAN": (17, 2005), "CHE": (20, 1990), "EUU": (20, 1990), "ISL": (30, 1990), "JPN": (3.8, 2005),
           "KAZ": (15, 1990), "MDA": (25, 1990), "NOR": (30, 1990), "NZL": (5, 1990), "RUS": (15, 1990), "UKR": (20, 1990), "USA": (17, 2005)}


def series(sector):
    W = E[E.sector == sector].pivot_table(index="iso", columns="year", values="mtco2e")
    W.loc["EUU"] = W.loc[[c for c in EU28 if c in W.index]].sum(min_count=1)
    return W


rows = []
for lab, sec in [("excl", "Total excluding LULUCF"), ("incl", "Total including LULUCF")]:
    W = series(sec)
    for iso, (r, by) in PLEDGES.items():
        Eb = W.loc[iso, by]; Et = Eb * (1 - r / 100)
        rows.append(dict(iso=iso, basis=lab, pledge_pct=r, base_year=by, E_base=Eb, E_target=Et, E_2019=W.loc[iso, 2019], E_2020=W.loc[iso, 2020],
                         change_2019=100 * (W.loc[iso, 2019] / Eb - 1), change_2020=100 * (W.loc[iso, 2020] / Eb - 1),
                         met_2019=bool(W.loc[iso, 2019] <= Et), met_2020=bool(W.loc[iso, 2020] <= Et)))
R = pd.DataFrame(rows); Rx = R[R.basis == "excl"].set_index("iso"); Ri = R[R.basis == "incl"].set_index("iso")


def get(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)


gdp = {"CHN": {}, "IND": {}}
G = pd.read_csv("ndc/data/raw/owid_gdp.csv")      # Our World in Data copy of the World Bank series NY.GDP.MKTP.KD (constant 2015 US$); the World Bank API itself timed out
for r in G[G.code.isin(["CHN", "IND"])].itertuples():
    gdp[r.code][int(r.year)] = float(r.ny_gdp_mktp_kd)
cw = get("https://www.climatewatchdata.org/api/v1/data/historical_emissions?source_ids[]=274&gas_ids[]=556&sector_ids[]=3208&regions[]=CHN&page=1&per_page=5")["data"]
co2_chn = {e["year"]: e["value"] for e in cw[0]["emissions"]}
W = series("Total excluding LULUCF"); A = E[E.sector == "Agriculture"].pivot_table(index="iso", columns="year", values="mtco2e")
inten = []
for iso, num, r, label in [("CHN", lambda y: co2_chn[y], 40, "CO2 per GDP"), ("IND", lambda y: W.loc["IND", y] - A.loc["IND", y], 20, "GHG excl. agriculture per GDP")]:
    i05 = num(2005) / gdp[iso][2005]; tgt = i05 * (1 - r / 100)
    inten.append(dict(iso=iso, measure=label, pledge_pct=r, change_2019=100 * (num(2019) / gdp[iso][2019] / i05 - 1), change_2020=100 * (num(2020) / gdp[iso][2020] / i05 - 1),
                      met_2019=num(2019) / gdp[iso][2019] <= tgt, met_2020=num(2020) / gdp[iso][2020] <= tgt))
I = pd.DataFrame(inten)

pd.set_option("display.width", 220)
print("== ABSOLUTE PLEDGES (total GHG excl. LULUCF): change vs base year in 2019 and 2020 against the pledge")
show = Rx[["pledge_pct", "base_year", "E_base", "E_target", "E_2019", "E_2020", "change_2019", "change_2020", "met_2019", "met_2020"]].copy()
show[["E_base", "E_target", "E_2019", "E_2020"]] = show[["E_base", "E_target", "E_2019", "E_2020"]].round(0)
show[["change_2019", "change_2020"]] = show[["change_2019", "change_2020"]].round(1)
print(show.sort_values("change_2020").to_string())
print("\n== INTENSITY PLEDGES"); print(I.round(1).to_string(index=False))
print(f"\nH6: met in 2020: {int(Rx.met_2020.sum())}/{len(Rx)} absolute pledges (+ {int(I.met_2020.sum())}/{len(I)} intensity pledges)")
print(f"H7: met in 2019 (pre-COVID): {int(Rx.met_2019.sum())}/{len(Rx)}; met in 2020: {int(Rx.met_2020.sum())}/{len(Rx)}; met only in 2020 (COVID-assisted?): {list(Rx.index[(~Rx.met_2019) & Rx.met_2020])}; met in 2019 but not 2020: {list(Rx.index[Rx.met_2019 & ~Rx.met_2020])}")
print(f"    median shortfall/overshoot vs target in 2019 and 2020 (% of base-year emissions): {np.median((Rx.E_2019 - Rx.E_target) / Rx.E_base * 100):+.1f} / {np.median((Rx.E_2020 - Rx.E_target) / Rx.E_base * 100):+.1f}")
diff = Rx.index[Rx.met_2020 != Ri.met_2020.reindex(Rx.index)]
print(f"SENSITIVITY incl. LULUCF: met-in-2020 verdict changes for {len(diff)}: {list(diff)}; met in 2020 incl. LULUCF: {int(Ri.met_2020.sum())}/{len(Ri)}")
# did the ones that met it also keep their word in the 2015 NDC (first NDC)? side-by-side with the 2015 pledge results
try:
    N = pd.read_csv(PROC / "ndc_pledge_progress.csv").set_index("iso")
    both = Rx.index.intersection(N.index)
    print("\nSAME COUNTRIES, two pledges: 2020 pledge met in 2020?  vs  2015 NDC (2025/2030) on track at 2023?")
    print(pd.DataFrame({"met_2020_pledge": Rx.loc[both, "met_2020"], "ndc2015_on_track_2023": N.loc[both, "on_track"]}).to_string())
except Exception as e:
    print("no comparison:", e)
fig, ax = plt.subplots(figsize=(9, 7))
x = -Rx.pledge_pct; y19 = Rx.change_2019; y20 = Rx.change_2020
ax.plot([-45, 5], [-45, 5], color="#999", ls="--", lw=0.8)
ax.scatter(x, y20, s=45, color="#d1495b", label="2020 (COVID year)", zorder=3); ax.scatter(x, y19, s=45, color="#2a6f97", marker="s", label="2019", zorder=3)
for iso in Rx.index: ax.annotate(iso, (x[iso], y20[iso]), fontsize=8, xytext=(4, 3), textcoords="offset points")
for iso in Rx.index: ax.plot([x[iso], x[iso]], [y19[iso], y20[iso]], color="#ccc", lw=0.7, zorder=1)
ax.set_xlabel("pledged change vs base year (%)"); ax.set_ylabel("actual change vs base year (%)")
ax.set_title("2020 pledges: actual emission change vs pledge (points below the dashed line met the pledge)")
ax.legend(); fig.tight_layout(); fig.savefig(Path("ndc/figures") / "pledge2020_vs_outcome.png", dpi=140)
Rx.to_csv(PROC / "ndc_pledge2020_outcomes.csv"); print("\nsaved ndc/figures/pledge2020_vs_outcome.png and data/processed/ndc_pledge2020_outcomes.csv")
