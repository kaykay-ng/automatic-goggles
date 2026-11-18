"""GoEmotions pilot (upf/PLAN.md 'GOEMOTIONS PILOT'): checks G1, G2 and the descriptive comparison with the old C4 labels. G4 runs in emotion_c4.py go.
Model: SamLowe/roberta-base-go_emotions (MIT), read offline from the local Hugging Face cache.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/goemotions_pilot.py
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import emotion_pilot as EP

GO = "SamLowe/roberta-base-go_emotions"
POS = ["admiration", "approval", "gratitude", "joy", "love", "excitement"]; NEG = ["disappointment", "annoyance", "anger", "disgust", "sadness"]

S = EP.sample(); old = pd.read_csv(EP.H.CACHE / "emotion_pilot.csv.gz")
assert (old.stars.values == S.stars.values).all(); print(f"sample {len(S):,} reviews, identical to the earlier pilots")
G, _ = EP.classify(S.text.tolist(), model=GO)
y = (S.stars >= 4).astype(int).values; m = ((S.stars <= 2) | (S.stars >= 4)).values
comp = (G[POS].mean(1) - G[NEG].mean(1)).values; lex = (old[["lex_joy", "lex_trust"]].mean(1) - old[["lex_anger", "lex_disgust", "lex_sadness"]].mean(1)).values

print("\n== G1 STARS == mean probability in 1-2 vs 4-5 star reviews:")
right = 0
for e in POS + NEG:
    lo, hi = G.loc[S.stars <= 2, e].mean(), G.loc[S.stars >= 4, e].mean(); ok = (hi > lo) if e in POS else (hi < lo); right += ok
    print(f"  {e:15s} {lo:.3f} -> {hi:.3f} {'OK' if ok else 'WRONG'}")
mv = m & old.vad.notna().values
a_go, a_vad = EP.H.auc(comp[m], y[m]), EP.H.auc(old.vad.values[mv], y[mv])
print(f"  directions right {right}/11 (bar >= 10); composite AUC GoEmotions {a_go:.3f} | VAD {a_vad:.3f} (bar: >= VAD) | Cardiff {EP.H.auc(old[[f'cls_{e}' for e in EP.POS]].mean(1).values[m] - old[[f'cls_{e}' for e in EP.NEGE]].mean(1).values[m], y[m]):.3f}")
print(f"  G1 {'PASSES' if right >= 10 and a_go >= a_vad else 'FAILS'}")

print("\n== G2 NEGATION ==")
for nm, sel in (("with a negator", old.neg.values), ("without", ~old.neg.values)):
    mm = m & sel; ag, al = EP.H.auc(comp[mm], y[mm]), EP.H.auc(lex[mm], y[mm])
    print(f"  reviews {nm:15s} n={mm.sum():6,}: AUC GoEmotions {ag:.3f} | EmoLex {al:.3f} | advantage {ag - al:+.3f}")

pres = (G >= .5).mean().sort_values(ascending=False)
print("\nshare of reviews where each label is present (p >= .5):", {k: f"{v:.1%}" for k, v in pres.items()})
print("share of 1-2 star reviews with disappointment present:", f"{(G.disappointment[S.stars <= 2] >= .5).mean():.1%}", "| with any of the 5 negative labels:", f"{(G.loc[S.stars <= 2, NEG] >= .5).any(axis=1).mean():.1%}")

print("\n== DESCRIPTIVE: GoEmotions vs the OLD C4 labels (not a test) ==")
lab = pd.read_csv(EP.H.CACHE / "emotion_labels.csv"); P = G.iloc[lab.id.values].reset_index(drop=True); O = old.iloc[lab.id.values].reset_index(drop=True)
def f1(p, t):
    tp = (p & t).sum(); return 0.0 if tp == 0 else 2 * tp / (p.sum() + t.sum())
for e in ["joy", "love", "anger", "disgust", "sadness", "surprise", "fear"]:
    t = lab[e].astype(bool).values
    print(f"  {e:9s} you {t.sum():2d} | GoEmotions {int((P[e] >= .5).sum()):2d} F1 {f1((P[e] >= .5).values, t):.2f} | Cardiff F1 {f1((O['cls_' + e] >= .5).values, t):.2f}")
t = lab.sadness.astype(bool).values | lab.note.fillna("").str.contains("disappoint").values
print(f"  GoEmotions 'disappointment' vs your sadness-or-'disappointment'-note ({t.sum()}): F1 {f1((P.disappointment >= .5).values, t):.2f}")
G.add_prefix("go_").to_csv(EP.H.CACHE / "goemotions_pilot.csv.gz", index=False); print("saved", EP.H.CACHE / "goemotions_pilot.csv.gz")
