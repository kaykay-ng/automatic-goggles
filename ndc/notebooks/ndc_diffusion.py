"""EXPLORATORY (not pre-declared; follows H9): which climate ideas spread between the first and third NDC, and did adopters have language-network
neighbours that had adopted earlier? Only the 36 text fields present in all rounds are used. Run:  ./.venv-nlp/bin/python ndc/notebooks/ndc_diffusion.py
"""
import re, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import ndc_common as D
from ndc_embed import clean
import networkx as nx

PROC = D.PROC; RNG = np.random.default_rng(55)
ROUNDS = ["indc", "first_ndc", "revised_first_ndc", "third_ndc"]
T = pd.read_csv(PROC / "ndc_text_long.csv"); T = T[T.document.isin(ROUNDS)]
common = set.intersection(*[set(T[T.document == r].indicator) for r in ROUNDS]); T = T[T.indicator.isin(common)]
# LIST FIX 15 Nov (ndc/PLAN.md KEYWORD-LIST REVIEW): drop Climate Watch tag-list rows ('End Use: ..., Fossil Fuels: Coal ...', 88 in revised, 54 in third round vs 16 in first)
# and the gas-list / GWP fields, which inflate 'hydrogen', 'coal' and 'methane' without meaning a policy mention.
T = T[~T.value.astype(str).str.contains(r"End Use:|Fossil Fuels:|Renewable Energy:|Energy: General")]
T = T[~T.indicator.isin(["Greenhouse gases covered", "Methods: Global warming potential (GWP) values"])]
TERMS = {"net zero / neutrality": r"net[- ]zero|carbon[- ]neutral|climate[- ]neutral",
         "1.5 degrees": r"1\.5\s?(?:°|degree|ºc|oc)",
         "just transition": r"just transition",
         "gender": r"\bgender",
         "methane": r"\bmethane\b",
         "nature-based solutions": r"nature[- ]based",
         "loss and damage": r"loss(?:es)? and damage",
         "Article 6 / carbon markets": r"article 6|carbon market|internationally transferred|\bitmos?\b",
         "coal": r"\bcoal\b",
         "electric vehicles": r"electric (?:vehicle|mobility|car|bus)|e-mobility",
         "hydrogen": r"hydrogen",
         "circular economy": r"circular economy"}
txt = {}
for rd in ROUNDS:
    for iso, g in T[T.document == rd].groupby("iso"):
        txt[(rd, iso)] = " ".join(dict.fromkeys(clean(str(v)) for v in g.value)).lower()
EU = D.EU27 | {"EUU"}
both = sorted(i for i in D.nodes if all((r, i) in txt for r in ROUNDS))
print(f"countries in all four rounds (D.nodes, EU as one): {len(both)}\n")
has = {(rd, t): np.array([bool(re.search(p, txt[(rd, i)].replace("eu ", "eu "))) for i in both]) for rd in ROUNDS for t, p in TERMS.items()}
print(f"{'idea':28s}" + "".join(f"{r:>19s}" for r in ROUNDS) + "   (share of these countries mentioning it)")
for t in TERMS:
    print(f"{t:28s}" + "".join(f"{has[(r, t)].mean():19.0%}" for r in ROUNDS))
pd.DataFrame([{"idea": t, **{r: round(100 * has[(r, t)].mean(), 1) for r in ROUNDS}, "n_countries": len(both)} for t in TERMS]).to_csv(PROC / "ndc_idea_diffusion.csv", index=False)

# neighbour exposure: language kNN on first NDC (all 154 nodes); adopters = absent in first_ndc, present in third_ndc
pos = {i: k for k, i in enumerate(D.nodes)}
G = nx.Graph()
for i in range(D.n):
    for j in [j for j in np.argsort(-D.L[i]) if j != i][:5]: G.add_edge(i, j)
reg = D.reg
print("\nEXPLORATORY neighbour exposure: among countries WITHOUT the idea in the first NDC, did those that adopted it by the third NDC have more")
print("language neighbours that already mentioned it in the revised first NDC?  (permutation of adoption WITHIN region, 5,000)")
early = {i: txt.get(("revised_first_ndc", i), "") for i in D.nodes}
for t, p in TERMS.items():
    at_risk = [k for k, i in enumerate(both) if not has[("first_ndc", t)][k]]
    if len(at_risk) < 15: continue
    adopt = np.array([has[("third_ndc", t)][k] for k in at_risk]);
    if adopt.sum() < 5 or (~adopt).sum() < 5: continue
    expo = np.array([np.mean([bool(re.search(p, early[D.nodes[j]])) for j in G.neighbors(pos[both[k]])]) for k in at_risk])
    obs = expo[adopt].mean() - expo[~adopt].mean(); rg = reg[[pos[both[k]] for k in at_risk]]; null = []
    for _ in range(5000):
        a = adopt.copy()
        for r in np.unique(rg):
            m = rg == r; a[m] = RNG.permutation(a[m])
        null.append(expo[a].mean() - expo[~a].mean())
    pv = (1 + (np.array(null) >= obs).sum()) / 5001
    print(f"   {t:28s} at risk {len(at_risk):3d}, adopted {adopt.sum():3d}: neighbour exposure adopters {expo[adopt].mean():.2f} vs non-adopters {expo[~adopt].mean():.2f}, p={pv:.3f}")
