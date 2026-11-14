"""Deep dive: do net exporters of meat / dairy emit more livestock emissions per person? How robust is it?

Run from final_project/:  ../.venv/bin/python notebooks/meat_dairy_deep_dive.py
Checks: (a) bootstrap CI, (b) leave-one-country-out, (c) drop re-export hubs NL/BE, (d) each year 2015-22,
(e) alternative emissions measure (enteric fermentation + manure management only),
(f) control for own consumption (animal protein supply per person) via partial Spearman,
(g) control for region (partial, rank residuals on region dummies).
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr, rankdata
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).parent))
from build_trade_networks import PREFIX2GROUP
from profile_faostat import CODE_BY_M49, m49
from gravity_null import REGION

RAW = Path("data/raw/Trade_DetailedTradeMatrix_E_All_Data")
PROC = Path("data/processed"); FIG = Path("figures")
YEARS = [f"Y{y}" for y in range(2015, 2023)]
RNG = np.random.default_rng(3)


def yearly_trade():
    f = PROC / "world_trade_meat_dairy_by_year.csv"
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
        ch["group"] = ch["Item Code"].map(gmap)
        ch = ch[ch["iso"].notna() & (ch["Unit"] == "t") & ch["group"].isin(["meat", "dairy_eggs"])
                & ch["Element"].isin(["Export quantity", "Import quantity"])]
        parts.append(ch.groupby(["iso", "group", "Element"])[YEARS].sum().reset_index())
    out = pd.concat(parts).groupby(["iso", "group", "Element"], as_index=False)[YEARS].sum()
    out.to_csv(f, index=False)
    return out


def rho(a, b):
    return spearmanr(a, b)[0]


def partial_rho(a, b, controls):
    """Spearman partial: rank-transform, regress out controls (columns), correlate residuals."""
    X = np.column_stack([np.ones(len(a))] + [rankdata(c) for c in controls])
    res = lambda y: rankdata(y) - X @ np.linalg.lstsq(X, rankdata(y), rcond=None)[0]
    return np.corrcoef(res(a), res(b))[0, 1]


def perm_p(a, b, stat, n=5000):
    obs = stat(a, b)
    return obs, (1 + sum(abs(stat(a, RNG.permutation(b))) >= abs(obs) for _ in range(n))) / (n + 1)


if __name__ == "__main__":
    Y = yearly_trade()
    em = pd.read_csv(PROC / "emissions_co2eq_parlamint.csv").set_index(["iso", "Item"])
    f = pd.read_csv(PROC / "fbs_parlamint.csv")
    T = pd.read_csv(PROC / "country_trade_emissions.csv", index_col=0)
    pop = T["pop"]
    mean = lambda item: em.xs(item, level="Item")[YEARS].mean(axis=1) * 1000
    live_pc = mean("Emissions from livestock") / pop
    enteric_pc = (mean("Enteric Fermentation") + mean("Manure Management")) / pop
    prot = f[(f.Item == "Animal Products") & (f.Element == "Protein supply quantity (g/capita/day)")] \
        .set_index("iso")[YEARS].mean(axis=1)
    reg = pd.Series(REGION)

    def net_pc(groups, years=YEARS):
        d = Y[Y.group.isin(groups)]
        tot = lambda el: d[d.Element == el].groupby("iso")[years].sum().mean(axis=1)
        return (tot("Export quantity") - tot("Import quantity")) * 1000 / pop

    cases = {"meat": ["meat"], "dairy_eggs": ["dairy_eggs"], "meat+dairy": ["meat", "dairy_eggs"]}
    rows = []
    for name, groups in cases.items():
        x = net_pc(groups).reindex(live_pc.index); y = live_pc
        print(f"\n===== {name}: net exports per capita (kg/person) vs livestock emissions per capita (t CO2eq/person)")
        r, p = perm_p(x.values, y.values, rho)
        boot = [rho(x.values[i], y.values[i]) for i in (RNG.integers(0, len(x), len(x)) for _ in range(5000))]
        print(f"(a) Spearman rho={r:+.2f}, permutation p={p:.4f}, bootstrap 95% CI [{np.nanpercentile(boot, 2.5):+.2f}, {np.nanpercentile(boot, 97.5):+.2f}]")
        loo = {c: rho(x.drop(c).values, y.drop(c).values) for c in x.index}
        lo, hi = min(loo, key=loo.get), max(loo, key=loo.get)
        print(f"(b) leave-one-out range: {loo[lo]:+.2f} (without {lo}) .. {loo[hi]:+.2f} (without {hi})")
        k = [c for c in x.index if c not in ("NL", "BE")]
        print(f"(c) without re-export hubs NL, BE: rho={rho(x[k], y[k]):+.2f}")
        yr = [rho(net_pc(groups, [yy]).reindex(y.index), y) for yy in YEARS]
        print("(d) by year 2015..2022: " + " ".join(f"{v:+.2f}" for v in yr))
        print(f"(e) enteric+manure-management only: rho={rho(x, enteric_pc):+.2f}")
        print(f"(f) controlling for own consumption (animal protein g/person/day): partial rho="
              f"{partial_rho(x.values, y.values, [prot.reindex(x.index).values]):+.2f}")
        R = pd.get_dummies(reg.reindex(x.index)).astype(float).values[:, :3].T
        print(f"(g) controlling for region (North/West/South/East): partial rho={partial_rho(x.values, y.values, list(R)):+.2f}")
        print(f"(f+g) both controls: partial rho={partial_rho(x.values, y.values, [prot.reindex(x.index).values, *R]):+.2f}")
        rows.append(dict(case=name, rho=r, p=p))

        fig, ax = plt.subplots(figsize=(6.5, 5))
        ax.scatter(x, y, s=30, color="#2a6f97")
        for c in x.index:
            ax.annotate(c, (x[c], y[c]), fontsize=8, xytext=(3, 3), textcoords="offset points")
        ax.axvline(0, color="#999", lw=0.6)
        ax.set_xlabel(f"net exports of {name}, kg per person per year (negative = net importer)")
        ax.set_ylabel("livestock emissions, t CO2eq per person per year")
        ax.set_title(f"{name}: rho={r:+.2f} (n=26)", fontsize=10)
        fig.tight_layout(); fig.savefig(FIG / f"netexp_vs_livestock_{name.replace('+', '_')}.png", dpi=150); plt.close(fig)
