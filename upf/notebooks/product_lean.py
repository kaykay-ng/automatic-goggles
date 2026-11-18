"""PRODUCT LEAN (pre-declared in upf/PLAN.md, 16 Nov): which grocery products are reviewed mostly by hobby-minded vs health-minded shoppers.
Reviewer lean = (health-coded - hobby non-food reviews) / all non-food reviews. Product lean = mean lean of its reviewers (>= 20 of our 58,391).
Null: reviewer leans shuffled within activity strata. L1: NOVA 4 minus NOVA 1-3 product lean within Amazon grocery categories.
Bipartite view: products and reviewers; a product's position is the average of its reviewer neighbours (neighbour averaging).
Outputs: soj/product_lean.csv.gz, data/processed/product_lean.txt.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/product_lean.py
"""
from pathlib import Path
import numpy as np, pandas as pd
from scipy import sparse

C = Path("upf/data/processed/soj"); OUT = Path("upf/data/processed/product_lean.txt"); RNG = np.random.default_rng(2611); NPERM = 1000; MINREV = 20
SETS = {
    "narrow": dict(health={("Health_and_Household", "Vitamins, Minerals & Supplements"), ("Health_and_Household", "Diet & Sports Nutrition"),
                           ("Health_and_Household", "Wellness & Relaxation"), ("Sports_and_Outdoors", "Exercise & Fitness")},
                   hobby={("Toys_and_Games", s) for s in ("Toy Figures & Playsets", "Collectible Toys", "Games & Accessories", "Puzzles", "Building Toys", "Novelty & Gag Toys")}
                   | {("Sports_and_Outdoors", "Fan Shop"), ("Sports_and_Outdoors", "Memorabilia Display & Storage")}, hobby_depts={"Video_Games"}),
}
SETS["wide"] = dict(health=SETS["narrow"]["health"] | {("Health_and_Household", "Oral Care"), ("Health_and_Household", "Vision")},
                    hobby=SETS["narrow"]["hobby"], hobby_depts={"Video_Games", "Toys_and_Games"})

T = pd.read_csv(C / "shopper_types.csv.gz").set_index("user_id")
E = pd.read_csv(C / "elsewhere_reviews.csv.gz", usecols=["user_id", "parent_asin"]); E = E[E.user_id.isin(T.index)]
S = pd.read_csv(C / "all_subcategories.csv.gz", index_col=0); E["d"] = S.dept.reindex(E.parent_asin).values; E["s"] = S["sub"].reindex(E.parent_asin).values
P = pd.read_csv(C / "products.csv.gz", usecols=["parent_asin", "nova"]).drop_duplicates("parent_asin").set_index("parent_asin").nova
M = pd.read_csv("upf/data/processed/amazon_meta_compact.csv.gz", usecols=["parent_asin", "categories"]).drop_duplicates("parent_asin").set_index("parent_asin").categories
pr = pd.read_csv(C / "reviewer_pairs.csv.gz").drop_duplicates(); pr = pr[pr.user_id.isin(T.index)]
cnt = pr.groupby("parent_asin").user_id.nunique(); keep = cnt.index[(cnt >= MINREV) & P.reindex(cnt.index).notna().values]
pr = pr[pr.parent_asin.isin(keep)]
users = pd.Index(T.index); prods = pd.Index(keep)
B = sparse.csr_matrix((np.ones(len(pr)), (prods.get_indexer(pr.parent_asin), users.get_indexer(pr.user_id))), shape=(len(prods), len(users)))
deg = np.asarray(B.sum(1)).ravel()
strata = T.stratum.reindex(users).astype(str).values; groups = [np.where(strata == s)[0] for s in np.unique(strata)]
lvl = M.reindex(prods).fillna("").str.split("|")
cat = pd.Series([f"{x[1]} > {x[2]}" if len(x) > 2 else "" for x in lvl], index=prods)
nova = P.reindex(prods).values; upf = nova == 4
log = []


def say(s=""): print(s); log.append(s)


def l1(lean_p):
    num = den = 0.0
    for c, ix in cat.groupby(cat).groups.items():
        if not c: continue
        ix = prods.get_indexer(ix); a, b = ix[upf[ix]], ix[~upf[ix]]
        if len(a) < 3 or len(b) < 3: continue
        w = min(len(a), len(b)); num += w * (lean_p[a].mean() - lean_p[b].mean()); den += w
    return num / den


res = {}
for name, st in SETS.items():
    tot = E.groupby("user_id").size()
    h = E[[(d, s) in st["health"] for d, s in zip(E.d, E.s)]].groupby("user_id").size()
    b = E[[(d, s) in st["hobby"] or d in st["hobby_depts"] for d, s in zip(E.d, E.s)]].groupby("user_id").size()
    lean = ((h.reindex(users, fill_value=0) - b.reindex(users, fill_value=0)) / tot.reindex(users)).fillna(0).values
    obs = B @ lean / deg; ob1 = l1(obs)
    null = np.empty((NPERM, len(prods))); nl1 = np.empty(NPERM)
    for k in range(NPERM):
        sh = lean.copy()
        for g in groups: sh[g] = lean[RNG.permutation(g)]
        null[k] = B @ sh / deg; nl1[k] = l1(null[k])
    mu, sd = null.mean(0), null.std(0); z = (obs - mu) / sd
    p = (1 + (np.abs(null - mu) >= np.abs(obs - mu)).sum(0)) / (NPERM + 1)
    o = np.argsort(p); q = np.empty_like(p); q[o] = np.minimum.accumulate((p[o] * len(p) / np.arange(1, len(p) + 1))[::-1])[::-1]
    pl1 = (1 + (np.abs(nl1 - nl1.mean()) >= abs(ob1 - nl1.mean())).sum()) / (NPERM + 1)
    res[name] = dict(lean=obs, expected=mu, z=z, q=q, l1=ob1, l1_null=nl1, p_l1=pl1)
    say(f"[{name}] reviewers: mean lean {lean.mean():+.3f}; all-hobby side (<= -.5) {np.mean(lean <= -.5):.1%}, health side (>= .5) {np.mean(lean >= .5):.1%}, zero {np.mean(lean == 0):.1%}")
    say(f"[{name}] products {len(prods):,} (UPF {upf.sum():,}); flagged at FDR 5%: {np.sum(q < .05):,} (hobby side {np.sum((q < .05) & (z < 0)):,}, health side {np.sum((q < .05) & (z > 0)):,})")
    say(f"[{name}] L1 within-category UPF minus less processed product lean = {ob1:+.4f} (null mean {nl1.mean():+.4f}, sd {nl1.std():.4f}), p = {pl1:.4f}")

r = res["narrow"]
D = pd.DataFrame({"parent_asin": prods, "cat": cat.values, "nova": nova, "reviewers": deg.astype(int), "lean": r["lean"], "expected": r["expected"], "z": r["z"], "q": r["q"],
                  "lean_wide": res["wide"]["lean"], "z_wide": res["wide"]["z"]})
D.to_csv(C / "product_lean.csv.gz", index=False)
say("\nPer category (narrow; categories with >= 15 products): mean (lean - expected) for UPF vs less processed")
D["ex"] = D.lean - D.expected
g = D[D.cat != ""].groupby("cat"); big = g.size()[g.size() >= 15].index
tab = D[D.cat.isin(big)].groupby(["cat", D.nova.eq(4).map({True: "UPF", False: "less"})]).ex.agg(["mean", "size"]).unstack()
say(tab.round(4).to_string())
OUT.write_text("\n".join(log) + "\n"); print("saved", OUT)
