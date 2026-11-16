"""Type-level bridge from The Complete Journey product types to Open Food Facts categories, household ultra-processed estimates, and H7. Rules in upf/PLAN.md 'TYPE-LEVEL BRIDGE'.
Run from final_project/ with the NLP env:
  ./.venv-nlp/bin/python upf/notebooks/cj_bridge.py match    # type -> category matches + 40-type hand-check sheet printed
  ./.venv-nlp/bin/python upf/notebooks/cj_bridge.py test     # household estimates, H7a/H7b, exploratory
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd, pyreadr
from scipy import stats

R = Path("upf/data/raw/completejourney"); PROC = Path("upf/data/processed"); OUT = PROC / "cj"; OUT.mkdir(exist_ok=True); RNG = np.random.default_rng(1717)
FOOD = {"GROCERY", "PRODUCE", "MEAT", "MEAT-PCKGD", "DELI", "PASTRY", "NUTRITION", "SEAFOOD", "SEAFOOD-PCKGD", "SALAD BAR", "FROZEN GROCERY", "CHEF SHOPPE"}
rd = lambda f: list(pyreadr.read_r(str(R / f)).values())[0]


def match():
    from sentence_transformers import SentenceTransformer
    P = rd("products.rda"); P = P[P.department.isin(FOOD)]
    types = P[["department", "product_category", "product_type"]].dropna().drop_duplicates(["product_category", "product_type"])
    types["text"] = (types.product_category.str.lower() + ": " + types.product_type.str.lower()).str.replace(r"\s+", " ", regex=True)
    off = pd.read_csv(PROC / "off_products.csv.gz", usecols=["nova", "countries", "main_category"])
    off = off[off.countries.fillna("").str.contains("en:united-states") & off.main_category.fillna("").str.startswith("en:")]
    ref = off.groupby("main_category").nova.agg(n="size", nova4=lambda x: (x == 4).mean()); ref = ref[ref.n >= 30].reset_index()
    ref["name"] = ref.main_category.str[3:].str.replace("-", " ")
    m = SentenceTransformer("all-MiniLM-L6-v2", device="mps")
    A = m.encode(types.text.tolist(), normalize_embeddings=True, batch_size=256); B = m.encode(ref.name.tolist(), normalize_embeddings=True, batch_size=256)
    S = A @ B.T; best = S.argmax(1)
    types["category"] = ref.name.values[best]; types["cosine"] = S.max(1); types["nova4_share"] = ref.nova4.values[best]; types["ref_n"] = ref.n.values[best]
    types["matched"] = types.cosine >= 0.50
    types.drop(columns="text").to_csv(OUT / "type_matches.csv", index=False)
    print(f"food product types: {len(types):,}; reference categories: {len(ref):,}; matched (cosine >= .50): {types.matched.sum():,} ({types.matched.mean():.0%})")
    print("cosine quartiles:", types.cosine.quantile([.25, .5, .75]).round(2).tolist())
    s = types[types.matched].sample(40, random_state=4)
    print("\nHAND-CHECK SHEET (40 random matched types): type -> category (cosine, NOVA-4 share)")
    for k, r in enumerate(s.itertuples(), 1):
        print(f"{k:2d}. {r.product_category.lower()}: {r.product_type.lower()}  ->  {r.category}  ({r.cosine:.2f}, {r.nova4_share:.2f})")
    u = types[~types.matched].sample(10, random_state=4)
    print("\nexamples of UNMATCHED types:", "; ".join(f"{r.product_type.lower()} -> {r.category} ({r.cosine:.2f})" for r in u.itertuples()))


def test():
    P = rd("products.rda"); T = rd("transactions.rds"); D = rd("demographics.rda")
    M = pd.read_csv(OUT / "type_matches.csv")
    t = T.merge(P[["product_id", "department", "brand", "product_category", "product_type"]], on="product_id", how="left"); t = t[t.department.isin(FOOD)]
    t = t.merge(M[["product_category", "product_type", "matched", "nova4_share"]], on=["product_category", "product_type"], how="left")
    t["matched"] = t.matched.fillna(False).astype(bool)
    h = t.groupby("household_id").agg(food_lines=("product_id", "size"), matched_lines=("matched", "sum"), private=("brand", lambda x: (x == "Private").mean()))
    h["upf_est"] = t[t.matched].groupby("household_id").nova4_share.mean(); h["coverage"] = h.matched_lines / h.food_lines
    print(f"food purchase lines {len(t):,}; matched {t.matched.mean():.0%}; households {len(h):,}; median coverage {h.coverage.median():.0%}")
    print(f"estimated UPF share: mean {h.upf_est.mean():.3f}, quartiles {h.upf_est.quantile([.25, .5, .75]).round(3).tolist()}")
    H = h.join(D.set_index("household_id"), how="inner").dropna(subset=["upf_est"])
    H["kids"] = pd.to_numeric(H.kids_count.astype(str).str.extract(r"(\d)")[0], errors="coerce").fillna(0) > 0
    order = ["Under 15K", "15-24K", "25-34K", "35-49K", "50-74K", "75-99K", "100-124K", "125-149K", "150-174K", "175-199K", "200-249K", "250K+"]
    H["inc_rank"] = H.income.astype(str).map({k: i for i, k in enumerate(order)})
    print(f"\nhouseholds with demographics and an estimate: {len(H)}; with kids {H.kids.sum()}; income bands seen: {sorted(H.income.astype(str).unique())}")
    y = H.upf_est.values; k = H.kids.values
    obs_a = y[k].mean() - y[~k].mean(); null = np.array([(lambda p: y[p].mean() - y[~p].mean())(RNG.permutation(k)) for _ in range(5000)])
    pa = (1 + (null >= obs_a).sum()) / 5001
    ok = H.inc_rank.notna().values; yi, ri = y[ok], H.inc_rank.values[ok]
    obs_b = stats.spearmanr(ri, yi)[0]; nb = np.array([stats.spearmanr(RNG.permutation(ri), yi)[0] for _ in range(5000)]); pb = (1 + (nb <= obs_b).sum()) / 5001
    q = np.minimum(1, np.array(sorted([pa, pb])) * np.array([2, 1])); qa, qb = (q[0], q[1]) if pa <= pb else (q[1], q[0]); qa, qb = max(qa, 0), max(qb, qa if pa <= pb else 0)
    holm = dict(zip(["a", "b"], [min(1, 2 * min(pa, pb)) if pa <= pb else max(min(1, 2 * min(pa, pb)), pa), max(min(1, 2 * min(pa, pb)), pb) if pa <= pb else min(1, 2 * min(pa, pb))]))
    print("\n== H7 (pre-declared; 5,000 permutations; Holm over 2) ==")
    print(f"  H7a kids vs no kids: {y[k].mean():.3f} vs {y[~k].mean():.3f}, difference {obs_a:+.4f}, one-sided p = {pa:.4f}, Holm p = {holm['a']:.4f}")
    print(f"  H7b income: Spearman {obs_b:+.3f} (n={ok.sum()}), one-sided p = {pb:.4f}, Holm p = {holm['b']:.4f}")
    print("  by income band:", H.groupby("income", observed=True).upf_est.agg(["size", "mean"]).round(3).to_dict("index"))
    print(f"\nEXPLORATORY: private-label share vs estimated UPF share (all {len(h):,} households): Spearman {stats.spearmanr(h.private, h.upf_est, nan_policy='omit')[0]:+.3f}")
    h.to_csv(OUT / "household_estimates.csv")


if __name__ == "__main__":
    {"match": match, "test": test}[sys.argv[1]]()
