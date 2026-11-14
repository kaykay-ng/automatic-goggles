"""Who delivered the EU's reductions? Member-state decomposition of the joint pledges. Run from final_project/ with the NLP env:
./.venv-nlp/bin/python ndc/notebooks/ndc_eu_members.py"""
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROC = Path("ndc/data/processed")
E = pd.read_csv(PROC / "emissions_cw_long.csv"); P = pd.read_csv(PROC / "ndc_pledges_parsed.csv")
members = sorted(set(P[P.eu_joint].iso) - {"EUU"})                    # 27 members + GBR (EU28 in the 2015 INDC)
W = E[E.sector == "Total excluding LULUCF"].pivot_table(index="iso", columns="year", values="mtco2e").loc[members]
pop = pd.read_csv(PROC / "controls.csv").set_index("iso")["pop"]
names = pd.read_csv(PROC / "controls.csv").set_index("iso")["name"]
T = pd.DataFrame({"E1990": W[1990], "E2005": W[2005], "E2015": W[2015], "E2019": W[2019], "E2020": W[2020], "E2023": W[2023]})
T["chg90_19"] = 100 * (T.E2019 / T.E1990 - 1); T["chg90_20"] = 100 * (T.E2020 / T.E1990 - 1)
T["cut15_23"] = 100 * (1 - T.E2023 / T.E2015)
T["delta_Mt_90_19"] = T.E2019 - T.E1990
eu = T[["E1990", "E2005", "E2015", "E2019", "E2020", "E2023"]].sum()
print(f"EU28 total: 1990 {eu.E1990:.0f} Mt -> 2019 {eu.E2019:.0f} ({100*(eu.E2019/eu.E1990-1):+.1f}%) -> 2020 {eu.E2020:.0f} ({100*(eu.E2020/eu.E1990-1):+.1f}%) | 2015 {eu.E2015:.0f} -> 2023 {eu.E2023:.0f}: cut {100*(1-eu.E2023/eu.E2015):.1f}% (22.3% needed by 2030, i.e. 11.9% by 2023 on a straight line)")
tot = T.delta_Mt_90_19.sum(); REQ_FULL = 22.3; REQ_2023 = REQ_FULL * 8 / 15      # straight line 2015 -> 2030: by 2023, 8 of 15 years, i.e. 11.9% (same rule as the EU-level check)
T["share_of_eu_cut_pct"] = 100 * T.delta_Mt_90_19 / tot
T["per_capita_2019_t"] = T.E2019 * 1e6 / pop.reindex(T.index)
pd.set_option("display.width", 220)
print("\nMEMBER TABLE (Mt CO2e excl. LULUCF), sorted by change 1990 -> 2019:")
print(T.sort_values("chg90_19")[["E1990", "E2019", "chg90_19", "chg90_20", "delta_Mt_90_19", "share_of_eu_cut_pct", "cut15_23", "per_capita_2019_t"]].round(1).to_string())
print(f"\nmembers whose own emissions were below -20% of 1990 in 2019: {int((T.chg90_19 <= -20).sum())}/28; in 2020: {int((T.chg90_20 <= -20).sum())}/28; members ABOVE their 1990 level in 2019: {list(T.index[T.chg90_19 > 0])}")
big4 = T.sort_values("delta_Mt_90_19").head(5)
print(f"largest contributors to the EU28 cut 1990->2019: " + ", ".join(f"{i} {r.delta_Mt_90_19:.0f} Mt ({r.share_of_eu_cut_pct:.0f}%)" for i, r in big4.iterrows()))
print(f"top 3 contributors account for {T.sort_values('delta_Mt_90_19').head(3).share_of_eu_cut_pct.sum():.0f}% of the net EU28 reduction; members that INCREASED added {T[T.delta_Mt_90_19>0].delta_Mt_90_19.sum():.0f} Mt")
ahead = T[T.cut15_23 >= REQ_2023]
print(f"\n2030 pace (straight line from 2015: {REQ_2023:.1f}% cut needed by 2023): members at or above it: {len(ahead)}/28: {list(ahead.sort_values('cut15_23', ascending=False).index)}")
print("members BELOW that pace:", {i: round(v, 1) for i, v in T[T.cut15_23 < REQ_2023].sort_values('cut15_23', ascending=False).cut15_23.items()})
print("members whose emissions in 2023 were HIGHER than in 2015:", list(T.index[T.cut15_23 < 0]))
print("\nspread of per-member change 1990->2019: min %.0f%% (%s), max %+.0f%% (%s), median %.0f%%" % (T.chg90_19.min(), T.chg90_19.idxmin(), T.chg90_19.max(), T.chg90_19.idxmax(), T.chg90_19.median()))
T.to_csv(PROC / "eu_members_pledge_decomposition.csv")

fig, axs = plt.subplots(1, 3, figsize=(19, 8.5))
o = T.sort_values("chg90_19")
axs[0].barh(o.index, o.chg90_19, color=["#2a6f97" if v <= -20 else "#d1495b" for v in o.chg90_19])
axs[0].axvline(-20, color="k", ls="--", lw=0.9); axs[0].text(-19, 0.2, "EU-wide pledge\n-20% by 2020", fontsize=8)
axs[0].set_title("change vs 1990 by 2019 (blue = beyond the EU-wide -20%)"); axs[0].set_xlabel("%")
o2 = T.sort_values("delta_Mt_90_19")
axs[1].barh(o2.index, o2.delta_Mt_90_19, color=["#2a6f97" if v < 0 else "#d1495b" for v in o2.delta_Mt_90_19])
axs[1].set_title("contribution to the EU28 change 1990-2019 (Mt CO2e)"); axs[1].set_xlabel("Mt (negative = reduction)")
o3 = T.sort_values("cut15_23", ascending=False)
axs[2].barh(o3.index, o3.cut15_23, color=["#2a6f97" if v >= REQ_2023 else "#d1495b" for v in o3.cut15_23])
axs[2].axvline(REQ_2023, color="k", ls="--", lw=0.9); axs[2].text(REQ_2023 + 0.5, 0.2, "11.9% cut by 2023 = straight line\nto -40% by 2030", fontsize=8)
axs[2].set_title("cut 2015-2023 (blue = at or above the straight-line pace)"); axs[2].set_xlabel("%")
for ax in axs: ax.tick_params(labelsize=8); ax.invert_yaxis()
fig.suptitle("Behind the EU's joint pledges: member states' own emissions (Climate Watch, excl. LULUCF; 27 members + UK as in the 2015 EU28)")
fig.tight_layout(); fig.savefig(Path("ndc/figures") / "eu_members_decomposition.png", dpi=130)
print("\nsaved ndc/figures/eu_members_decomposition.png")
