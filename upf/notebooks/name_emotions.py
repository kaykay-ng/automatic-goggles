"""EXPLORATORY: emotion words in the names of packaged foods, by NOVA group (NRC Word-Emotion Association Lexicon, EmoLex v0.92).
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/name_emotions.py
Lexicon: Mohammad & Turney (2010, 2013), National Research Council Canada; non-commercial research/education use; NOT redistributed (kept in upf/data/raw/nrc/, gitignored).
Steps: strip the brand from each name; lowercase word tokens (a trailing 's' is removed if only the singular is in the lexicon); a product 'has' an emotion if any word is associated with it.
FOOD-WORD TRAP: lexicon words that are also ingredient names (upf ingredient network nodes) or category names are flagged as food words; results are reported with and without them.
Within-category comparison: main categories with >= 300 NOVA-4 and >= 300 NOVA 1-3 products.
"""
import re
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np, pandas as pd

PROC = Path("upf/data/processed"); LEX = Path("upf/data/raw/nrc/NRC-Emotion-Lexicon/NRC-Emotion-Lexicon-Wordlevel-v0.92.txt")
EMO = ["anger", "anticipation", "disgust", "fear", "joy", "sadness", "surprise", "trust", "positive", "negative"]
L = pd.read_csv(LEX, sep="\t", names=["word", "emotion", "v"]); L = L[L.v == 1]
lex = defaultdict(set)
for w, e in zip(L.word, L.emotion): lex[w].add(e)
print(f"lexicon words with at least one association: {len(lex):,}")

D = pd.read_csv(PROC / "off_names_en.csv.gz")
food = set()
for s in pd.read_csv(PROC / "ingredient_nodes.csv").ingredient: food |= set(re.findall(r"[a-z]+", s))
import sys
FOOD_FROM_CATEGORIES = "--food-from-categories" in sys.argv          # default: ingredient names only (category names also contain marketing words such as organic, real, authentic, treat)
if FOOD_FROM_CATEGORIES:
    for s in D.main_category.dropna().unique(): food |= set(re.findall(r"[a-z]+", s.split(":", 1)[-1]))
print(f"food vocabulary (ingredient names{' + category names' if FOOD_FROM_CATEGORIES else ''}): {len(food):,} words; of them in the lexicon with an emotion: {len(food & set(lex)):,}")


def strip_brand(name, brands):
    n = name
    if isinstance(brands, str):
        for b in sorted(brands.split(","), key=len, reverse=True):
            b = b.strip()
            if len(b) >= 2: n = re.sub(re.escape(b), " ", n, flags=re.I)
    return n


def words(name):
    out = []
    for w in re.findall(r"[a-z']+", name.lower()):
        w = w.strip("'")
        if w not in lex and w.endswith("s") and w[:-1] in lex: w = w[:-1]
        out.append(w)
    return out


D["clean"] = [strip_brand(n, b) for n, b in zip(D.product_name, D.brands)]
W = D.clean.map(words)
hits_all = {e: np.zeros(len(D), bool) for e in EMO}; hits_nf = {e: np.zeros(len(D), bool) for e in EMO}
contrib = {e: Counter() for e in EMO}
for i, ws in enumerate(W):
    for w in ws:
        for e in lex.get(w, ()):
            hits_all[e][i] = True; contrib[e][w] += 1
            if w not in food: hits_nf[e][i] = True
D["any_emotion"] = np.any([hits_all[e] for e in EMO if e not in ("positive", "negative")], axis=0)
print(f"products: {len(D):,}; names with at least one emotion word (8 emotions): {D.any_emotion.mean():.1%}")

rows = []
for e in EMO:
    for nv in (1, 2, 3, 4):
        m = D.nova.values == nv
        rows.append(dict(emotion=e, nova=nv, share_all=hits_all[e][m].mean(), share_without_food_words=hits_nf[e][m].mean(), n=int(m.sum())))
R = pd.DataFrame(rows); R.to_csv(PROC / "emotion_by_nova.csv", index=False)
pv = R.pivot(index="emotion", columns="nova", values="share_all").round(3); pv2 = R.pivot(index="emotion", columns="nova", values="share_without_food_words").round(3)
print("\nshare of product names with a word for each emotion, by NOVA group (ALL words):"); print(pv.to_string())
print("\nsame, WITHOUT food words:"); print(pv2.to_string())
print("\ntop words per emotion (count; * = food word):")
TW = []
for e in EMO:
    top = contrib[e].most_common(12); TW += [(e, w, c, w in food) for w, c in contrib[e].most_common(40)]
    print(f"  {e:12s}: " + ", ".join(f"{w}{'*' if w in food else ''} {c}" for w, c in top))
pd.DataFrame(TW, columns=["emotion", "word", "count", "food_word"]).to_csv(PROC / "emotion_top_words.csv", index=False)

# within-category: NOVA 4 minus NOVA 1-3, words without food words
g = D.assign(**{f"h_{e}": hits_nf[e] for e in EMO}); g["u"] = g.nova == 4
cat = g.groupby("main_category").u.agg(["sum", "size"]); cat["other"] = cat["size"] - cat["sum"]; cats = cat[(cat["sum"] >= 300) & (cat.other >= 300)].index
rows = []
for c in cats:
    s = g[g.main_category == c]
    for e in EMO:
        rows.append(dict(category=c, emotion=e, nova4=s[s.u][f"h_{e}"].mean(), nova123=s[~s.u][f"h_{e}"].mean(), n4=int(s.u.sum()), n123=int((~s.u).sum())))
C = pd.DataFrame(rows); C["diff"] = C.nova4 - C.nova123; C.to_csv(PROC / "emotion_within_category.csv", index=False)
print(f"\nWITHIN-CATEGORY (without food words): {len(cats)} categories with >= 300 products on both sides")
for e in EMO:
    x = C[C.emotion == e]["diff"]; print(f"  {e:12s} median NOVA4 - NOVA1-3 difference {x.median():+.3f}; NOVA 4 higher in {int((x > 0).sum())}/{len(x)} categories")
