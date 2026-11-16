"""Yelp lexicon pilot (upf/PLAN.md 'YELP LEXICON PILOT'): 20,000 of the H11 validation reviews scored with the NRC Yelp Restaurant Sentiment Lexicon vs our NRC VAD valence, against star ratings.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/yelp_pilot.py
Negation: a negated context runs from a negator (not, no, never, cannot, none, nothing, nobody, nowhere, neither, nor, or any word ending in n't) to the next punctuation mark.
 The first word after the negator is looked up as word_NEGFIRST, later ones as word_NEG; if that entry does not exist the word is SKIPPED (rule fixed before scoring).
Bigrams: consecutive word pairs, with '_NEG' attached to words in a negated context. Lexicon: Kiritchenko et al. 2014, research use, not redistributed.
"""
import gzip, json, re, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).parent))
import habits as H                                              # same RNG seed and sampling rule as the H11 draw
import elsewhere as E

Y = Path("upf/data/raw/nrc/yelp/Yelp-restaurant-reviews")
uni = dict(l.rstrip("\n").split("\t")[:2] for l in open(Y / "Yelp-restaurant-reviews-AFFLEX-NEGLEX-unigrams.txt", encoding="utf-8", errors="replace"))
big = dict(l.rstrip("\n").split("\t")[:2] for l in open(Y / "Yelp-restaurant-reviews-AFFLEX-NEGLEX-bigrams.txt", encoding="utf-8", errors="replace"))
uni = {k: float(v) for k, v in uni.items()}; big = {k: float(v) for k, v in big.items()}
NEG = {"not", "no", "never", "cannot", "none", "nothing", "nobody", "nowhere", "neither", "nor"}
TOK = re.compile(r"[a-z']+|[.,!?;:]")


def yelp(text):
    toks = TOK.findall(text.lower()); su = nu = sb = nb = n = 0; neg = False; first = False; prev = None
    for t in toks:
        if t in ".,!?;:": neg = False; prev = None; continue
        n += 1
        if t in NEG or t.endswith("n't"): neg = True; first = True; prev = t; continue
        key = (t + ("_NEGFIRST" if first else "_NEG")) if neg else t; first = False
        if key in uni: su += uni[key]; nu += 1
        bt = t + "_NEG" if neg else t
        if prev is not None:
            bk = f"{prev} {bt}"
            if bk in big: sb += big[bk]; nb += 1
        prev = bt
    return (su / nu if nu else np.nan), ((su + sb) / (nu + nb) if nu + nb else np.nan), nu / max(n, 1)


P = pd.read_csv(H.CACHE / "products.csv.gz", usecols=["parent_asin"]); keep = set(P.parent_asin); rows = []
with gzip.open(H.RAW / "Grocery_and_Gourmet_Food.jsonl.gz", "rt") as f:
    for line in f:
        i = line.find('"parent_asin": "'); a = line[i + 16: line.find('"', i + 16)]
        if a not in keep or H.RNG.random() > 0.09: continue
        r = json.loads(line); t = (r.get("title") or "") + ". " + (r.get("text") or "")
        if r.get("rating") is None or len(t.split()) < 3: continue
        rows.append((t, float(r["rating"])))
D = pd.DataFrame(rows, columns=["text", "stars"]).sample(min(200_000, len(rows)), random_state=1).reset_index(drop=True)
S = D.sample(20_000, random_state=5).reset_index(drop=True)
S["vad"] = [E.valence(t)[0] for t in S.text]
yy = [yelp(t) for t in S.text]; S["yelp_uni"] = [a for a, _, _ in yy]; S["yelp_unibi"] = [b for _, b, _ in yy]; S["yelp_cov"] = [c for _, _, c in yy]
m = (S.stars <= 2) | (S.stars >= 4); y = (S.stars[m] >= 4).astype(int).values
print(f"pilot sample {len(S):,} reviews (of the 200,000 H11 draw); 1-2 vs 4-5 star reviews used for AUC: {m.sum():,}")
for c in ("vad", "yelp_uni", "yelp_unibi"):
    ok = S[c].notna(); mm = m & ok
    print(f"  {c:11s}: AUC {H.auc(S.loc[mm, c].values, (S.stars[mm] >= 4).astype(int).values):.3f} | Spearman with stars {stats.spearmanr(S.loc[ok, c], S.stars[ok])[0]:+.3f} | reviews scored {ok.mean():.1%}")
print(f"  coverage: Yelp unigrams score {S.yelp_cov.mean():.0%} of tokens on average")
print("\nhow Yelp scores the known problem words:", {w: uni.get(w) for w in ["treat", "hot", "sweet", "happy", "happy_NEGFIRST", "good_NEGFIRST", "bad_NEGFIRST", "disappointed", "chocolate", "broken", "stale", "bland"]})
for txt in ["Not happy with the product.", "Not tasty", "Not bad at all", "Great morning treat", "hot sauce is great", "arrived broken"]:
    print(f"   {txt!r:32s} Yelp {yelp(txt)[1]:+.2f} | VAD {E.valence(txt)[0]:+.2f}")
w = S[(S.stars <= 2)].sort_values("yelp_unibi", ascending=False).head(4)
print("\n1-2 star reviews Yelp still scores most positive:"); [print("   ", round(r.yelp_unibi, 2), "|", r.text[:140].replace("\n", " ")) for r in w.itertuples()]
S.drop(columns="text").to_csv(H.CACHE / "yelp_pilot.csv.gz", index=False)
