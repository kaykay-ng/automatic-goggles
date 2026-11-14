"""Option A: does what parliaments talk about track the country's position in the food system?

Run from final_project/:  ../.venv/bin/python notebooks/country_text_vs_food_system.py
Hypotheses and measures were PRE-DECLARED in PLAN.md ('OPTION A chosen'). Primary tests: P1, P2, P3 (Holm over these 3, using the
controlled p-value). Everything else is exploratory.
"""
import glob
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr, rankdata
import sys
sys.path.insert(0, str(Path(__file__).parent))
from gravity_null import REGION

PROC = Path("data/processed"); PM = PROC / "parlamint"
RNG = np.random.default_rng(2026)
YEARS = [f"Y{y}" for y in range(2015, 2023)]


def text_measures():
    rows = []
    for f in sorted(glob.glob(str(PM / "index_*.csv.gz"))):
        cc = Path(f).name.split("_")[1].split(".")[0]
        idx = pd.read_csv(f, usecols=["speech_id", "role", "topic", "words", "senti_mean"])
        idx = idx[(idx.words >= 50) & (idx.role != "Chairperson")]
        tf = pd.read_csv(str(PM / f"topic_flags_{cc}.csv.gz"), usecols=["speech_id", "n_agri", "n_food", "n_climate"])
        tf = tf.merge(idx[["speech_id", "senti_mean"]], on="speech_id", how="inner")      # same substantive, non-chair set
        N = len(idx)
        agri, food, clim = tf.n_agri > 0, tf.n_food > 0, tf.n_climate > 0
        rows.append(dict(
            iso=cc, n_speeches=N,
            attention_agri=1e4 * agri.sum() / N, attention_food=1e4 * food.sum() / N, attention_climate=1e4 * clim.sum() / N,
            climate_in_agri=(agri & clim).sum() / max(agri.sum(), 1), climate_in_food=(food & clim).sum() / max(food.sum(), 1),
            topic_label_agri=100 * (idx.topic == "Agriculture").mean(), topic_label_env=100 * idx.topic.isin(["Environment"]).mean(),
            senti_agri=tf.loc[agri, "senti_mean"].mean(), senti_climate=tf.loc[clim, "senti_mean"].mean(),
            senti_baseline=idx.senti_mean.mean()))
    return pd.DataFrame(rows).set_index("iso")


def country_vars():
    pop = pd.read_csv(PROC / "country_trade_emissions.csv", index_col=0)["pop"]
    w = pd.read_csv(PROC / "world_trade_meat_dairy_by_year.csv")
    w["t"] = w[YEARS].fillna(0).mean(axis=1)
    g = w.groupby(["iso", "Element"]).t.sum().unstack()
    netpc = (g["Export quantity"] - g["Import quantity"]) * 1000 / pop
    fp = pd.read_csv(PROC / "country_food_profile.csv", index_col=0)
    ss = np.log2(fp[[c for c in fp if c.startswith("SS_")]].clip(lower=0.25, upper=4)).clip(-2, 2)
    emb = pd.read_csv(PROC / "embodied_emissions_by_country.csv", index_col=0)
    V = pd.DataFrame({"net_animal_exports_pc": netpc, "food_selfsuff": ss.mean(axis=1), "shift_pct": emb.shift_pct,
                      "E_imp_pc": emb.E_imp_pc, "PBA_pc": emb.PBA_pc, "CBA_pc": emb.CBA_pc})
    V["log_pop"] = np.log10(pop)
    V["region"] = pd.Series(REGION)
    return V


def partial_rho(x, y, controls):
    X = np.column_stack([np.ones(len(x))] + [rankdata(c) for c in controls])
    res = lambda v: rankdata(v) - X @ np.linalg.lstsq(X, rankdata(v), rcond=None)[0]
    return np.corrcoef(res(x), res(y))[0, 1]


def permute_within(x, region):
    out = x.copy()
    for r in np.unique(region):
        i = np.where(region == r)[0]
        out[i] = RNG.permutation(x[i])
    return out


def test(x, y, logpop, region, n=5000):
    x, y, logpop, region = (np.asarray(a) for a in (x, y, logpop, region))
    ok = ~(np.isnan(x.astype(float)) | np.isnan(y.astype(float)))
    x, y, logpop, region = x[ok], y[ok], logpop[ok], region[ok]
    raw = spearmanr(x, y)[0]
    praw = (1 + sum(abs(spearmanr(RNG.permutation(x), y)[0]) >= abs(raw) for _ in range(n))) / (n + 1)
    par = partial_rho(x, y, [logpop])
    ppar = (1 + sum(abs(partial_rho(permute_within(x, region), y, [logpop])) >= abs(par) for _ in range(n))) / (n + 1)
    boot = [spearmanr(x[i], y[i])[0] for i in (RNG.integers(0, len(x), len(x)) for _ in range(2000))]
    return dict(n=int(len(x)), rho=raw, p_raw=praw, rho_partial=par, p_controlled=ppar,
                ci_lo=np.nanpercentile(boot, 2.5), ci_hi=np.nanpercentile(boot, 97.5))


def holm(ps):
    order = np.argsort(ps); m = len(ps); adj = np.empty(m); run = 0
    for rank, i in enumerate(order):
        run = max(run, (m - rank) * ps[i]); adj[i] = min(run, 1)
    return adj


if __name__ == "__main__":
    T = text_measures(); V = country_vars()
    D = T.join(V, how="inner")
    D.to_csv(PROC / "country_text_and_food_system.csv")
    pd.set_option("display.width", 220)
    print("== Country text measures (per 10,000 substantive non-chair speeches)")
    print(D[["n_speeches", "attention_agri", "attention_food", "attention_climate", "climate_in_agri", "senti_agri"]].round(2)
          .sort_values("climate_in_agri").to_string())

    print("\n== PRIMARY tests (pre-declared). controlled = log population partialled out, x permuted within regions")
    prim = [("P1", "climate_in_agri", "shift_pct", "negative"), ("P2", "attention_agri", "net_animal_exports_pc", "positive"),
            ("P3", "attention_food", "food_selfsuff", "negative")]
    res = []
    for name, y, x, pred in prim:
        r = test(D[x], D[y], D.log_pop, D.region); r.update(test=name, y=y, x=x, predicted=pred); res.append(r)
    R = pd.DataFrame(res)
    R["p_holm"] = holm(R.p_controlled.values)
    R["direction_ok"] = [(r.rho_partial < 0) == (r.predicted == "negative") for r in R.itertuples()]
    print(R[["test", "y", "x", "predicted", "n", "rho", "p_raw", "rho_partial", "p_controlled", "p_holm", "ci_lo", "ci_hi", "direction_ok"]]
          .round(3).to_string(index=False))

    print("\n== EXPLORATORY grid (Spearman rho; * = controlled p<0.05; NOT corrected, 7 x 6 = 42 tests)")
    ys = ["attention_agri", "attention_food", "attention_climate", "climate_in_agri", "topic_label_agri", "topic_label_env", "senti_agri"]
    xs = ["net_animal_exports_pc", "food_selfsuff", "shift_pct", "E_imp_pc", "PBA_pc", "CBA_pc"]
    grid = pd.DataFrame(index=ys, columns=xs, dtype=object)
    nsig = 0
    for y in ys:
        for x in xs:
            r = test(D[x], D[y], D.log_pop, D.region, n=1000)
            star = "*" if r["p_controlled"] < 0.05 else ""
            nsig += star == "*"
            grid.loc[y, x] = f"{r['rho']:+.2f}{star}"
    print(grid.to_string()); print(f"{nsig} of {len(ys)*len(xs)} exploratory cells significant (about {0.05*len(ys)*len(xs):.1f} expected by chance)")
