"""C4 of the emotion pilot (upf/PLAN.md): the user's blind hand labels vs the classifier and EmoLex.
Needs upf/data/processed/soj/emotion_labels.csv (exported from upf/label_emotions.html).
Rule (pre-declared): for each emotion the user ticked >= 10 times, F1 of classifier (p >= .5) and of EmoLex (any word with that emotion);
 PASS if classifier macro-F1 >= 0.5 and higher than EmoLex's. EmoLex has no love / optimism / pessimism, so it is compared on the shared emotions only.
Run from final_project/:  ./.venv-nlp/bin/python upf/notebooks/emotion_c4.py
"""
from pathlib import Path
import numpy as np, pandas as pd

C = Path("upf/data/processed/soj")
lab = pd.read_csv(C / "emotion_labels.csv"); key = pd.read_csv(C / "emotion_label_ids.csv"); pil = pd.read_csv(C / "emotion_pilot.csv.gz")
EMO = ["joy", "love", "optimism", "trust", "anticipation", "surprise", "anger", "disgust", "sadness", "fear", "pessimism"]
lab = lab.dropna(subset=EMO, how="all"); P = pil.iloc[lab.id.values].reset_index(drop=True); lab = lab.reset_index(drop=True)
print(f"labelled reviews: {len(lab)} (stars {key.set_index('id').stars.reindex(lab.id).value_counts().sort_index().to_dict()}); ticked None: {int(lab.none.sum())}")


def f1(pred, true):
    tp = (pred & true).sum(); p = tp / max(pred.sum(), 1); r = tp / max(true.sum(), 1)
    return 0.0 if tp == 0 else 2 * p * r / (p + r)


rows = []
for e in EMO:
    t = lab[e].fillna(0).astype(bool).values; n = t.sum()
    c = (P[f"cls_{e}"] >= 0.5).values
    l = (P[f"lex_{e}"] > 0).values if f"lex_{e}" in P else None
    rows.append(dict(emotion=e, you=int(n), classifier=int(c.sum()), F1_classifier=f1(c, t), EmoLex=None if l is None else int(l.sum()), F1_EmoLex=None if l is None else f1(l, t)))
R = pd.DataFrame(rows); print("\nper emotion (counts = reviews where it is present):"); print(R.round(2).to_string(index=False))
q = R[R.you >= 10]; sh = q.dropna(subset=["F1_EmoLex"])
mc = q.F1_classifier.mean(); ms_c = sh.F1_classifier.mean(); ms_l = sh.F1_EmoLex.astype(float).mean()
print(f"\nemotions you ticked >= 10 times: {', '.join(q.emotion)}")
print(f"classifier macro-F1 over them: {mc:.3f} (bar >= 0.5)")
print(f"on the emotions EmoLex also has ({', '.join(sh.emotion)}): classifier {ms_c:.3f} vs EmoLex {ms_l:.3f}")
print(f"C4 {'PASSES' if mc >= 0.5 and ms_c > ms_l else 'FAILS'}")
dis = [(i, e) for e in q.emotion for i in range(len(lab)) if bool(lab.at[i, e]) != bool(P.at[i, f'cls_{e}'] >= .5)]
print(f"\ndisagreements with the classifier: {len(dis)} (review, emotion); first 12 by review id:")
for i, e in sorted(dis)[:12]: print(f"  review {lab.id[i]:6d} {e:9s} you {int(lab.at[i, e])} | classifier p={P.at[i, f'cls_{e}']:.2f} | {lab.text[i][:90]!r}")
