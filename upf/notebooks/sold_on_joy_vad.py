"""Amendment A1 (upf/PLAN.md): marketing language by VALENCE/AROUSAL (NRC VAD Lexicon v2.1, scores -1..1), reviews by EMOTIONS (EmoLex).
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/sold_on_joy_vad.py
Document score = mean valence (arousal) of its word tokens found in the VAD lexicon; PRIMARY excludes food words (ingredient-name tokens); 'all' includes them.
Same samples and within-category permutation design as sold_on_joy.py (marketing >= 10 words; H3 also >= 5 reviews). VAD: Mohammad (2025), non-commercial research use, not redistributed.
"""
import gzip, json, re, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import sold_on_joy as S

PROC = Path("upf/data/processed"); RAW = Path("upf/data/raw"); CACHE = PROC / "soj"
V = pd.read_csv(RAW / "nrc/NRC-VAD-Lexicon-v2.1/Unigrams/unigrams-NRC-VAD-Lexicon-v2.1.txt", sep="\t", keep_default_na=False)
val = dict(zip(V.term, V.valence)); aro = dict(zip(V.term, V.arousal))
_, food = S.lexicon()


def vad(text):
    sv = sa = n = svf = saf = nf = 0.0
    for w in re.findall(r"[a-z']+", text.lower()):
        w = w.strip("'")
        if w not in val and w.endswith("s") and w[:-1] in val: w = w[:-1]
        if w in val:
            sv += val[w]; sa += aro[w]; n += 1
            if w not in food: svf += val[w]; saf += aro[w]; nf += 1
    return sv, sa, n, svf, saf, nf


cache = CACHE / "vad_products.csv.gz"
if not cache.exists():
    M = pd.read_csv(PROC / "amazon_meta_compact.csv.gz", usecols=["parent_asin", "features", "description"]).drop_duplicates("parent_asin")
    P = pd.read_csv(CACHE / "products.csv.gz"); M = M[M.parent_asin.isin(set(P.parent_asin))]
    T = [vad((f if isinstance(f, str) else "") + " " + (d if isinstance(d, str) else "")) for f, d in zip(M.features, M.description)]
    M = pd.DataFrame({"parent_asin": M.parent_asin.values, "m_v_all": [t[0] / t[2] if t[2] else np.nan for t in T], "m_a_all": [t[1] / t[2] if t[2] else np.nan for t in T],
                      "m_v_nf": [t[3] / t[5] if t[5] else np.nan for t in T], "m_a_nf": [t[4] / t[5] if t[5] else np.nan for t in T], "m_vad_n_nf": [t[5] for t in T]})
    keep = set(M.parent_asin); acc = {}
    with gzip.open(RAW / "amazon/Grocery_and_Gourmet_Food.jsonl.gz", "rt") as f:
        for line in f:
            d = json.loads(line); a = d.get("parent_asin")
            if a not in keep: continue
            t = vad((d.get("title") or "") + " " + (d.get("text") or "")); x = acc.setdefault(a, np.zeros(6)); x += t
    R = pd.DataFrame.from_dict(acc, orient="index", columns=["sv", "sa", "n", "svf", "saf", "nf"])
    R["r_v_all"] = R.sv / R.n; R["r_v_nf"] = R.svf / R.nf.where(R.nf > 0); R["r_a_nf"] = R.saf / R.nf.where(R.nf > 0)
    M = M.merge(R[["r_v_all", "r_v_nf", "r_a_nf"]], left_on="parent_asin", right_index=True, how="left"); M.to_csv(cache, index=False)
M = pd.read_csv(cache)
P = pd.read_csv(CACHE / "products.csv.gz").merge(M, on="parent_asin", how="left"); P["u"] = P.nova == 4
P["gap_v_nf"] = P.m_v_nf - P.r_v_nf; P["gap_v_all"] = P.m_v_all - P.r_v_all
mk = P[(P.m_tokens >= 10) & P.m_v_nf.notna()]; h3 = mk[(mk.r_n >= 5) & mk.r_v_nf.notna()]
print(f"products with marketing >= 10 words and a valence score: {len(mk):,}; also >= 5 reviews: {len(h3):,}")
print("mean valence / arousal by NOVA (no food words; scale -1..1): marketing valence, marketing arousal, review valence")
print(P.groupby("nova")[["m_v_nf", "m_a_nf", "r_v_nf"]].mean().round(3).to_string())
res = {"A1-H1 marketing valence higher for NOVA 4": S.within(mk, "m_v_nf"),
       "A1-H1b marketing arousal differs (two-sided)": S.within(mk, "m_a_nf", two_sided=True),
       "A1-H3 valence gap marketing minus reviews larger for NOVA 4": S.within(h3, "gap_v_nf")}
adj = S.holm([v[1] for v in res.values()])
print("\n== AMENDMENT A1 TESTS (within category, 5,000 permutations; Holm over 3) ==")
for (k, v), q in zip(res.items(), adj):
    print(f"  {k}: estimate {v[0]:+.4f} (valence units, -1..1), p = {v[1]:.4f}, Holm p = {q:.4f}; categories {v[2]}, products {v[3]:,}")
print("\n== REVIEWS BY EMOTION (EmoLex, no food words): NOVA 4 minus NOVA 1-3 within category, share of review words (x100 = per 100 words); two-sided, Holm over 8 ==")
rv = P[(P.r_n >= 5) & (P.r_tokens > 0)].copy(); out = []
for e in ["anger", "anticipation", "disgust", "fear", "joy", "sadness", "surprise", "trust"]:
    rv[f"r_{e}_share"] = rv[f"r_{e}_nf"] / rv.r_tokens; out.append((e,) + S.within(rv, f"r_{e}_share", nperm=2000, two_sided=True))
qa = S.holm([o[2] for o in out])
for o, q in zip(out, qa): print(f"  {o[0]:12s} {100 * o[1]:+.3f} per 100 words, p = {o[2]:.4f}, Holm p = {q:.4f}")
print("\n== ROBUSTNESS (A1) ==")
hc = mk[mk.high_conf]; one = mk.sample(frac=1, random_state=7).drop_duplicates("brand"); one = one[one.brand.fillna("") != ""]
for nm, D in [("high-confidence matches", hc), ("one product per brand", one)]:
    r1 = S.within(D, "m_v_nf", nperm=2000); h = D[(D.r_n >= 5) & D.r_v_nf.notna()]; r3 = S.within(h, "gap_v_nf", nperm=2000)
    print(f"  {nm:24s}: A1-H1 {r1[0]:+.4f} (p {r1[1]:.3f}, {r1[3]:,}) | A1-H3 {r3[0]:+.4f} (p {r3[1]:.3f}, {r3[3]:,})")
r1 = S.within(P[(P.m_tokens >= 10) & P.m_v_all.notna()], "m_v_all", nperm=2000); h = P[(P.m_tokens >= 10) & (P.r_n >= 5) & P.gap_v_all.notna()]; r3 = S.within(h, "gap_v_all", nperm=2000)
print(f"  {'ALL words (incl. food)':24s}: A1-H1 {r1[0]:+.4f} (p {r1[1]:.3f}) | A1-H3 {r3[0]:+.4f} (p {r3[1]:.3f})")
print("  NOVA gradient: " + P.groupby("nova")[["m_v_nf", "gap_v_nf"]].mean().round(3).to_string().replace("\n", " | "))
