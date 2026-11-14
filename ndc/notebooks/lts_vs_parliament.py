"""LTS pathway profile vs parliament profile (pre-declared in ndc/PLAN.md). Run from final_project/ with the NLP env:
./.venv-nlp/bin/python ndc/notebooks/lts_vs_parliament.py"""
import glob, re
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
import sys; sys.path.insert(0, str(Path(__file__).parent))
from lts_extract import CX, CATS

PM = Path("data/processed/parlamint"); PROC = Path("ndc/data/processed"); RNG = np.random.default_rng(88)
GOAL = re.compile(r"climate[- ]neutral\w*|carbon[- ]neutral\w*|net[- ]zero|zero net|long[- ]term (?:climate )?(?:strategy|goal|target)s?", re.I)
K = r"(?:reduc\w*|neutral\w*|zero|emissions?|carbon|greenhouse|decarboni\w*)"
G2050 = re.compile(rf"{K}[^.]{{0,80}}\b2050\b|\b2050\b[^.]{{0,80}}{K}", re.I)       # identical to lts_parliament_means.py


def merged_windows(text, w=300):
    sp = [m.span() for m in GOAL.finditer(text)] + [m.span() for m in G2050.finditer(text)]
    sp = sorted((max(0, a - w), min(len(text), b + w)) for a, b in sp); out = []
    for a, b in sp:
        if out and a <= out[-1][1]: out[-1][1] = max(out[-1][1], b)
        else: out.append([a, b])
    return out


cache = PROC / "parliament_category_profiles.csv"
if cache.exists():
    P = pd.read_csv(cache, index_col=0)
else:
    rows = []
    for f in sorted(glob.glob(str(PM / "flagged_*.csv.gz"))):
        d = pd.read_csv(f, usecols=["country", "role", "words", "n_climate", "text"])
        d = d[(d.words >= 50) & (d.role != "Chairperson") & (d.n_climate > 0)]; cc = d.country.iloc[0]
        goal_counts = {k: 0 for k in CATS}; n_goal = 0; all_counts = {k: 0 for k in CATS}; nwords = 0
        for t in d.text.fillna(""):
            nwords += len(t.split())
            for k, rx in CX.items(): all_counts[k] += len(rx.findall(t))
            ws = merged_windows(t)
            if ws:
                n_goal += 1
                for a, b in ws:
                    seg = t[a:b]
                    for k, rx in CX.items(): goal_counts[k] += len(rx.findall(seg))
        r = dict(country=cc, climate_speeches=len(d), goal_speeches=n_goal, words=nwords)
        r.update({f"goal_{k}": v for k, v in goal_counts.items()}); r.update({f"all_{k}": v for k, v in all_counts.items()})
        rows.append(r); print(cc, len(d), n_goal, flush=True)
    P = pd.DataFrame(rows).set_index("country"); P.to_csv(cache)

cats = list(CATS)
use = {"AT": "AT_1", "CZ": "CZ_2", "DK": "DK_1", "FI": "FI_1", "FR": "FR_1", "GB": "GB_1", "HU": "HU_1", "IS": "IS_1", "LV": "LV_1", "NL": "NL_1",
       "NO": "NO_1", "PT": "PT_1", "RS": "RS_1", "SE": "SE_1", "SI": "SI_1", "TR": "TR_1", "UA": "UA_2", "BA": "BA_1"}
LP = pd.read_csv(PROC / "lts_profiles.csv").set_index("name")
rows = []
for cc, nm in use.items():
    if cc not in P.index: continue
    lts = LP.loc[nm, cats].astype(float); lts = lts / lts.sum()
    g = P.loc[cc, [f"goal_{k}" for k in cats]].astype(float); a = P.loc[cc, [f"all_{k}" for k in cats]].astype(float)
    rows.append(dict(cc=cc, n_goal=int(P.loc[cc, "goal_speeches"]), **{f"lts_{k}": lts[k] for k in cats},
                     **{f"par_goal_{k}": (g.iloc[i] / g.sum() if g.sum() > 0 else np.nan) for i, k in enumerate(cats)},
                     **{f"par_all_{k}": a.iloc[i] / a.sum() for i, k in enumerate(cats)}))
D = pd.DataFrame(rows).set_index("cc")
D.to_csv(PROC / "lts_vs_parliament_profiles.csv")
G = D[D.n_goal >= 30]
pd.set_option("display.width", 220)
print(f"\ncountries: {len(D)} with LTS profile; {len(G)} with >=30 strict goal speeches: {list(G.index)}; excluded for <30: {list(D.index[D.n_goal < 30])}")
print("\nMEAN SHARE BY CATEGORY (LTS document | parliament goal windows | parliament all climate speeches):")
tab = pd.DataFrame({"LTS": [G[f"lts_{k}"].mean() for k in cats], "parliament_goal_windows": [G[f"par_goal_{k}"].mean() for k in cats],
                    "parliament_all_climate": [G[f"par_all_{k}"].mean() for k in cats]}, index=cats).round(3); print(tab.to_string())


def pa(view, subset):
    rho = []
    for k in cats:
        x, y = subset[f"lts_{k}"], subset[f"par_{view}_{k}"]; rho.append(stats.spearmanr(x, y)[0])
    return np.array(rho)


for view, lab in [("goal", "parliament goal windows (pre-declared primary view)"), ("all", "parliament all climate speeches (second view)")]:
    S = G if view == "goal" else D
    rho = pa(view, S); med = np.nanmedian(rho)
    null = []
    for _ in range(5000):
        perm = RNG.permutation(len(S)); Sp = S.copy()
        for k in cats: Sp[f"par_{view}_{k}"] = S[f"par_{view}_{k}"].values[perm]
        null.append(np.nanmedian(pa(view, Sp)))
    print(f"\nP-A [{lab}], n={len(S)}: across-country rho per category: " + ", ".join(f"{k} {r:+.2f}" for k, r in zip(cats, rho)))
    print(f"    median rho = {med:+.2f}; permuted-country null mean {np.mean(null):+.2f}, sd {np.std(null):.2f}; one-sided p = {(1 + sum(n >= med for n in null)) / 5001:.4f}")
    # P-B within-country alignment
    wc = []; 
    L = S[[f"lts_{k}" for k in cats]].values; Pp = S[[f"par_{view}_{k}" for k in cats]].values
    mat = np.array([[stats.spearmanr(L[i], Pp[j])[0] for j in range(len(S))] for i in range(len(S))])
    own = np.diag(mat); off = mat[~np.eye(len(S), dtype=bool)]
    print(f"P-B within-country rho (own LTS vs own parliament): median {np.median(own):+.2f}; vs other countries' parliaments: median {np.median(off):+.2f}; own > mean of others in {int((own > (mat.sum(1) - own) / (len(S) - 1)).sum())}/{len(S)} countries")
    perm_med = []
    for _ in range(5000):
        p = RNG.permutation(len(S)); perm_med.append(np.median([mat[i, p[i]] for i in range(len(S))]))
    print(f"    permutation p (own beats random partners, median rho): {(1 + sum(m >= np.median(own) for m in perm_med)) / 5001:.4f}")
    print("    per country own rho: " + ", ".join(f"{c} {r:+.2f}" for c, r in zip(S.index, own)))

print("\nP-C gaps (goal-window view): log2(LTS share / parliament share), mean over countries; positive = stressed in strategies, rare in parliament:")
gap = pd.Series({k: np.nanmean(np.log2((G[f"lts_{k}"] + 1e-3) / (G[f"par_goal_{k}"] + 1e-3))) for k in cats}).sort_values(ascending=False)
print(gap.round(2).to_string())
fig, axs = plt.subplots(1, 2, figsize=(15, 5.5)); w = 0.38; x = np.arange(len(cats))
axs[0].bar(x - w / 2, tab["LTS"], w, label="strategy documents", color="#2a6f97"); axs[0].bar(x + w / 2, tab["parliament_goal_windows"], w, label="parliament, near long-term goals", color="#d1495b")
axs[0].set_xticks(x); axs[0].set_xticklabels(cats, rotation=35); axs[0].set_ylabel("share of theme mentions"); axs[0].legend(); axs[0].set_title("What strategies stress vs what parliaments discuss")
own = np.array([stats.spearmanr(G.loc[c, [f"lts_{k}" for k in cats]], G.loc[c, [f"par_goal_{k}" for k in cats]])[0] for c in G.index])
o = np.argsort(own); axs[1].barh(G.index[o], own[o], color="#66a182"); axs[1].axvline(0, color="k", lw=0.6)
axs[1].set_title("per country: rank correlation of the 9-theme profiles (strategy vs parliament)"); axs[1].set_xlabel("Spearman rho")
fig.tight_layout(); fig.savefig(Path("ndc/figures") / "lts_vs_parliament.png", dpi=130)
print("\nsaved ndc/figures/lts_vs_parliament.png")
