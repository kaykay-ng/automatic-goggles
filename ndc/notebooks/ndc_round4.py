"""Round-4 hypotheses H8b (firm list v2), H11 (did pledges firm up?), H12 (hedging within income x region strata). Design pre-declared in ndc/PLAN.md 'ROUND 4'.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python ndc/notebooks/ndc_round4.py
"""
import re, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).parent))
import ndc_common as D
from ndc_embed import clean

RNG = np.random.default_rng(4242)
nodes, PROC, TOT = D.nodes, D.PROC, D.TOT
FIRM2 = [r"\bcommit(?:s|ted)? to\b", r"\bcommitment to (?:reduc|achiev|limit|cut)", r"\bunconditional(?:ly)?\b", r"\bbinding\b",
         r"\bnet[- ]zero\b|\bcarbon[- ]neutral\w*|\bclimate[- ]neutral\w*", r"\beconomy[- ]wide\b", r"\bwill (?:reduce|achieve|cut|limit)\b"]
HEDGE = [r"\bconditional\b", r"\bsubject to\b", r"\bprovided that\b", r"\binternational (?:support|finance|assistance|funding)\b",
         r"\bbusiness[- ]as[- ]usual\b|\bBAU\b", r"\bdepend(?:s|ent|ing)? on\b"]
cnt = lambda pats, t: sum(len(re.findall(p, t, flags=re.I)) for p in pats)
firmness = lambda t: np.log((cnt(FIRM2, t) + 1) / (cnt(HEDGE, t) + 1))

E = pd.read_csv(PROC / "emissions_cw_long.csv"); E = E[E.sector == TOT].pivot_table(index="iso", columns="year", values="mtco2e")
E.loc["EUU"] = E.loc[[c for c in D.EU27 if c in E.index]].sum()
trend = lambda a, b: 100 * ((E[b] / E[a]) ** (1 / (b - a)) - 1)
tr = pd.DataFrame({"t1519": trend(2015, 2019), "t1523": trend(2015, 2023), "t0515": trend(2005, 2015), "e15": E[2015]}).reindex(nodes)
big = ((tr.e15 >= 1) & tr[["t1519", "t1523", "t0515"]].notna().all(axis=1)).values

T = pd.read_csv(PROC / "ndc_text_long.csv")


def docs_for(rd, fields=None):
    S = T[T.document == rd]
    if fields is not None: S = S[S.indicator.isin(fields)]
    out = {}
    for iso, g in S.groupby("iso"):
        out[iso] = " ".join(dict.fromkeys(c for c in (clean(str(v)) for v in g.value) if c))
    return out


def partial_spearman(x, y, ctl):
    R = stats.rankdata; A = np.column_stack([np.ones(len(x))] + [R(c) for c in ctl])
    ex = R(x) - A @ np.linalg.lstsq(A, R(x), rcond=None)[0]; ey = R(y) - A @ np.linalg.lstsq(A, R(y), rcond=None)[0]
    r = np.corrcoef(ex, ey)[0, 1]; df = len(x) - 2 - len(ctl); t = r * np.sqrt(df / (1 - r * r))
    return r, stats.t.cdf(t, df)


# ---------------- H8b ----------------
d1 = docs_for("first_ndc")
F = pd.DataFrame({"firmness_v2": [firmness(d1[i]) for i in nodes], "firm_v2": [cnt(FIRM2, d1[i]) for i in nodes], "hedge": [cnt(HEDGE, d1[i]) for i in nodes]}, index=nodes).join(tr)
F["lgdp"] = D.lg; F["income"] = D.inc; F["region"] = D.reg
S = F[big]
print(f"== H8b firm list v2 (n={len(S)}): firm v2 matches median {S.firm_v2.median():.0f} (countries with 0: {(S.firm_v2 == 0).sum()}), hedged median {S.hedge.median():.0f}")
for col, lab in [("t1519", "PRIMARY 2015-19"), ("t1523", "secondary 2015-23")]:
    r, p = partial_spearman(S.firmness_v2.values, S[col].values, [S.lgdp.values, S.t0515.values])
    print(f"   {lab}: partial rho = {r:+.3f}, one-sided p = {p:.4f}")
rng = np.random.default_rng(8); hits = [(i, m.start()) for i in nodes for p in FIRM2 for m in re.finditer(p, d1[i], flags=re.I)]
rows = [(hits[k][0], d1[hits[k][0]][max(0, hits[k][1] - 110): hits[k][1] + 110]) for k in rng.choice(len(hits), 10, replace=False)]
pd.DataFrame(rows, columns=["iso", "context"]).to_csv(PROC / "round4_firm_v2_handcheck.csv", index=False)

# ---------------- H12 ----------------
Sx = S.copy()
A = np.column_stack([np.ones(len(Sx)), Sx.t0515]); Sx["resid"] = Sx.t1519 - A @ np.linalg.lstsq(A, Sx.t1519, rcond=None)[0]
obs = stats.spearmanr(Sx.firmness_v2, Sx.resid)[0]
strata = (Sx.income + "|" + Sx.region).values; fv = Sx.firmness_v2.values; null = []
for _ in range(5000):
    f = fv.copy()
    for s in np.unique(strata):
        m = strata == s
        if m.sum() >= 2: f[m] = RNG.permutation(f[m])
    null.append(stats.spearmanr(f, Sx.resid)[0])
null = np.array(null)
print(f"\n== H12 within income x region strata ({len(np.unique(strata))} strata): Spearman(firmness v2, trend residual) = {obs:+.3f};"
      f" null mean {null.mean():+.3f}; one-sided p = {(1 + (null <= obs).sum()) / 5001:.4f}")

# ---------------- H11 ----------------
Tc = T[T.document.isin(["indc", "first_ndc", "revised_first_ndc", "third_ndc"])]
common = set.intersection(*[set(Tc[Tc.document == r].indicator) for r in ["indc", "first_ndc", "revised_first_ndc", "third_ndc"]])
f1, f3, fr = docs_for("first_ndc", common), docs_for("third_ndc", common), docs_for("revised_first_ndc", common)
eu = D.EU27 | {"EUU"}
pairs = [i for i in nodes if i in f1 and i in f3 and len(f1[i].split()) >= 50 and len(f3[i].split()) >= 50]
P = pd.DataFrame({"first": [firmness(f1[i]) for i in pairs], "third": [firmness(f3[i]) for i in pairs],
                  "revised": [firmness(fr[i]) if i in fr else np.nan for i in pairs],
                  "w1": [len(f1[i].split()) for i in pairs], "w3": [len(f3[i].split()) for i in pairs]}, index=pairs)
P["change"] = P.third - P["first"]
w = stats.wilcoxon(P.third, P["first"], alternative="greater")
print(f"\n== H11 firmness first -> third NDC (36 shared fields; n={len(P)} countries, EU as one)")
print(f"   median firmness first {P['first'].median():+.2f} -> revised {P.revised.median():+.2f} -> third {P.third.median():+.2f}; firmer in third: {(P.change > 0).sum()}/{len(P)}, "
      f"same {(P.change == 0).sum()}; PRIMARY paired Wilcoxon one-sided p = {w.pvalue:.4f}")
print(f"   persistence: Spearman first vs third = {stats.spearmanr(P['first'], P.third)[0]:+.2f}")
P["tercile"] = pd.qcut(P["first"].rank(method="first"), 3, labels=["most hedged", "middle", "firmest"])
for t, g in P.groupby("tercile", observed=True):
    print(f"   first-NDC {t:12s} n={len(g):2d}: median change {g.change.median():+.2f}  (REGRESSION TO THE MEAN WARNING: not a test)")
cc = [i for i in P.index if i in tr.index and big[nodes.index(i)]]
if len(cc) > 15:
    print(f"   EXPLORATORY: change in firmness vs 2015-23 trend: Spearman {stats.spearmanr(P.loc[cc, 'change'], tr.loc[cc, 't1523'])[0]:+.2f} (n={len(cc)})")
F.to_csv(PROC / "round4_firmness_v2.csv"); P.to_csv(PROC / "round4_firmness_rounds.csv")
