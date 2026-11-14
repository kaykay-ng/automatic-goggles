"""Where does the food go? Self-sufficiency, use and diet profiles for the 26 ParlaMint countries (FAOSTAT food balance
sheets, mean 2015-2022), then: do countries group by SUPPLY profile / DIET the way they group by TRADE?

Run from final_project/:  ../.venv/bin/python notebooks/food_use_profile.py
Writes data/processed/country_food_profile.csv.
Notes: FBS aggregates are in primary-commodity equivalents (1000 t). Self-sufficiency = production / domestic supply
(>1 for net exporters). Residuals/stock changes are left out, so shares do not sum to exactly 1.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist, squareform
sys.path.insert(0, str(Path(__file__).parent))
from profile_faostat import CODE_BY_M49, m49
from gravity_null import REGION

PROC = Path("data/processed")
YEARS = [f"Y{y}" for y in range(2015, 2023)]
RNG = np.random.default_rng(11)
GROUP = {"S2905": "cereals", "S2907": "roots", "S2911": "pulses", "S2912": "nuts", "S2913": "oilcrops",
         "S2914": "vegoils", "S2918": "veg", "S2919": "fruit", "S2909": "sugar", "S2924": "alcohol",
         "S2943": "meat", "S2945": "offals", "S2946": "animalfats", "S2948": "milk", "S2949": "eggs",
         "S2960": "fish", "S2901": "TOTAL"}


def load():
    raw = pd.read_csv("data/raw/FoodBalanceSheets_E_All_Data/FoodBalanceSheets_E_All_Data_NOFLAG.csv",
                      encoding="latin-1", usecols=["Area Code (M49)", "Item Code (FBS)", "Element"] + YEARS)
    raw["iso"] = m49(raw["Area Code (M49)"]).map(CODE_BY_M49)
    raw["grp"] = raw["Item Code (FBS)"].str.lstrip("'").map(GROUP)
    raw = raw[raw["iso"].notna() & raw["grp"].notna()]
    raw["v"] = raw[YEARS].mean(axis=1)
    return raw.pivot_table(index="iso", columns=["grp", "Element"], values="v")


def ratio(a, b):
    return a / b.replace(0, np.nan)


def build(P):
    g = lambda grp, el: P[(grp, el)]
    F = pd.DataFrame(index=P.index)
    for grp in ["cereals", "veg", "fruit", "meat", "milk", "eggs"]:
        F[f"SS_{grp}"] = ratio(g(grp, "Production"), g(grp, "Domestic supply quantity"))
    F["cereal_feed_share"] = ratio(g("cereals", "Feed"), g("cereals", "Domestic supply quantity"))
    F["cereal_export_share"] = ratio(g("cereals", "Export quantity"), g("cereals", "Production"))
    F["meat_export_share"] = ratio(g("meat", "Export quantity"), g("meat", "Production"))
    F["milk_export_share"] = ratio(g("milk", "Export quantity"), g("milk", "Production"))
    fv_sup = g("veg", "Domestic supply quantity") + g("fruit", "Domestic supply quantity")
    F["fruitveg_import_dep"] = (g("veg", "Import quantity") + g("fruit", "Import quantity")) / fv_sup
    F["fruitveg_losses_share"] = (g("veg", "Losses") + g("fruit", "Losses")) / fv_sup
    kc = lambda grp: P[(grp, "Food supply (kcal/capita/day)")]
    tot = kc("TOTAL")
    diet = pd.DataFrame({
        "kcal_cereals": kc("cereals") / tot, "kcal_roots": kc("roots") / tot, "kcal_sugar": kc("sugar") / tot,
        "kcal_pulses_nuts": (kc("pulses") + kc("nuts")) / tot, "kcal_veg_fruit": (kc("veg") + kc("fruit")) / tot,
        "kcal_oils": kc("vegoils") / tot, "kcal_alcohol": kc("alcohol") / tot,
        "kcal_meat": (kc("meat") + kc("offals")) / tot, "kcal_dairy_eggs": (kc("milk") + kc("eggs") + kc("animalfats")) / tot,
        "kcal_fish": kc("fish") / tot})
    return F, diet


def zs(X):
    return (X - X.mean()) / X.std(ddof=0)


def silhouette(D, labels):
    n, s = len(labels), []
    for i in range(n):
        same = (labels == labels[i]) & (np.arange(n) != i)
        if same.sum() == 0:
            s.append(0); continue
        a = D[i, same].mean()
        b = min(D[i, labels == c].mean() for c in np.unique(labels) if c != labels[i])
        s.append((b - a) / max(a, b))
    return float(np.mean(s))


def cluster(X, ks=(2, 3, 4, 5)):
    Z = zs(X).values
    L = linkage(Z, "ward"); D = squareform(pdist(Z))
    best = None
    for k in ks:
        lab = fcluster(L, k, "maxclust")
        s = silhouette(D, lab)
        print(f"   k={k}: silhouette={s:.2f}")
        if best is None or s > best[1]:
            best = (k, s, lab)
    return best


def ari(x, y):
    ct = pd.crosstab(pd.Series(x), pd.Series(y)).values
    c2 = lambda a: a * (a - 1) / 2
    sij, sa, sb = c2(ct).sum(), c2(ct.sum(1)).sum(), c2(ct.sum(0)).sum()
    exp = sa * sb / c2(ct.sum())
    return (sij - exp) / ((sa + sb) / 2 - exp)


def ari_perm(x, y, n=5000):
    obs = ari(x, y)
    return obs, (1 + sum(ari(x, RNG.permutation(y)) >= obs for _ in range(n))) / (n + 1)


if __name__ == "__main__":
    P = load(); F, diet = build(P)
    pd.concat([F, diet], axis=1).to_csv(PROC / "country_food_profile.csv")
    pd.set_option("display.width", 200)
    print("== SELF-SUFFICIENCY (production / domestic supply; >1 = net exporter), mean 2015-22")
    print(F[[c for c in F if c.startswith("SS_")]].round(2).to_string())
    print("\n== Countries with extreme values")
    for c in ["SS_cereals", "SS_meat", "SS_milk", "SS_fruit"]:
        s = F[c].sort_values()
        print(f"{c}: lowest {dict(s.head(3).round(2))} | highest {dict(s.tail(3).round(2))}")

    comm = {}
    for name in ["all_food", "meat", "dairy_eggs", "cereals", "fruit_veg"]:
        G = nx.read_graphml(PROC / f"networks/trade_{name}.graphml")
        comm[name] = {n: int(d["community"]) for n, d in G.nodes(data=True)}
    region = pd.Series(REGION)

    for title, X in [("SUPPLY profile (self-sufficiency, feed, exports, losses)", F), ("DIET profile (kcal shares by food group)", diet)]:
        print(f"\n==== CLUSTERS on {title}")
        X = X.dropna()
        k, s, lab = cluster(X)
        lab = pd.Series(lab, index=X.index)
        print(f" chosen k={k} (silhouette {s:.2f})  [silhouette < 0.25 = weak structure]")
        for c in sorted(lab.unique()):
            members = list(lab[lab == c].index)
            print(f"  cluster {c} ({len(members)}): {' '.join(members)}")
            print("     means:", dict(zs(X).loc[members].mean().round(1)[lambda v: v.abs() >= 0.8]))
        idx = list(X.index)
        print(" agreement with other groupings (ARI; permutation p):")
        for nm, cm in list(comm.items()) + [("REGION", region.to_dict())]:
            a, p = ari_perm(lab.values, np.array([cm[i] if isinstance(cm[i], int) else hash(cm[i]) % 10**6 for i in idx]))
            print(f"   vs {nm:10s}: ARI={a:+.2f} p={p:.3f}")
