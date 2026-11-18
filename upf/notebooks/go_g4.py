"""G4 of the GoEmotions pilot (upf/PLAN.md): the user's blind set-2 labels vs GoEmotions, Cardiff and EmoLex.
Needs upf/data/processed/soj/go_labels.csv (exported from upf/label_emotions_set2.html).
Rule (pre-declared): emotions the user ticks >= 10 times; GoEmotions macro-F1 >= 0.5; AND > Cardiff on shared (joy, love, anger, disgust, sadness, surprise);
 AND > EmoLex on shared (joy, anger, disgust, sadness, surprise). Disappointment F1 reported on its own.
Run from final_project/:  ./.venv-nlp/bin/python upf/notebooks/go_g4.py
"""
from pathlib import Path
import pandas as pd

C = Path("upf/data/processed/soj")
EMO = ["admiration", "approval", "gratitude", "joy", "love", "excitement", "disappointment", "annoyance", "anger", "disgust", "sadness", "surprise"]
lab = pd.read_csv(C / "go_labels.csv").dropna(subset=EMO, how="all").reset_index(drop=True)
G = pd.read_csv(C / "goemotions_pilot.csv.gz").iloc[lab.id.values].reset_index(drop=True)
O = pd.read_csv(C / "emotion_pilot.csv.gz").iloc[lab.id.values].reset_index(drop=True)
print(f"labelled reviews: {len(lab)}; None ticked {int(lab.none.sum())}; notes: {lab.note.dropna().tolist()[:10]}")


def f1(p, t):
    tp = (p & t).sum(); return 0.0 if tp == 0 else 2 * tp / (p.sum() + t.sum())


rows = []
for e in EMO:
    t = lab[e].fillna(0).astype(bool).values; g = (G[f"go_{e}"] >= .5).values
    c = (O[f"cls_{e}"] >= .5).values if f"cls_{e}" in O else None; l = (O[f"lex_{e}"] > 0).values if f"lex_{e}" in O else None
    rows.append(dict(emotion=e, you=int(t.sum()), go=int(g.sum()), F1_go=f1(g, t), F1_cardiff=None if c is None else f1(c, t), F1_emolex=None if l is None else f1(l, t)))
R = pd.DataFrame(rows); print(R.round(2).to_string(index=False))
q = R[R.you >= 10]; mg = q.F1_go.mean()
qc = q.dropna(subset=["F1_cardiff"]); ql = q.dropna(subset=["F1_emolex"])
gc, cc = (qc.F1_go.mean(), qc.F1_cardiff.astype(float).mean()) if len(qc) else (float("nan"), float("nan"))
gl, ll = (ql.F1_go.mean(), ql.F1_emolex.astype(float).mean()) if len(ql) else (float("nan"), float("nan"))
print(f"\nemotions ticked >= 10 times: {', '.join(q.emotion)}\nGoEmotions macro-F1 {mg:.3f} (bar >= 0.5)")
print(f"vs Cardiff on shared ({', '.join(qc.emotion) or 'none'}): {gc:.3f} vs {cc:.3f}\nvs EmoLex on shared ({', '.join(ql.emotion) or 'none'}): {gl:.3f} vs {ll:.3f}")
ok = mg >= .5 and (len(qc) == 0 or gc > cc) and (len(ql) == 0 or gl > ll)
print(f"disappointment F1 {R.set_index('emotion').F1_go['disappointment']:.2f}\nG4 {'PASSES' if ok else 'FAILS'}")
