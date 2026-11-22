"""Emotion of seed-oil and nutrition comments by theme and period (the sentiment strand of the seed-oil project).

Run from final_project/ with the NLP env (slow; run in the background):
  ./.venv-nlp/bin/python seedoils/notebooks/emotions.py            -> seedoils/data/processed/emotion_scores.csv.gz (ids + scores, no text)
  ./.venv-nlp/bin/python seedoils/notebooks/emotions.py summary    -> seedoils/data/processed/emotion_summary.csv

Classifier: SamLowe/roberta-base-go_emotions (28 GoEmotions labels, trained on Reddit comments; multi-label, sigmoid scores). PROVISIONAL: the choice of
emotion classifier is still open with the course TAs (see upf/PLAN.md); this one was picked here because it is trained on Reddit text. Not validated by
hand on this corpus. Texts longer than 256 tokens are truncated.
Groups (per document, the maximum score within the group; 'share' = fraction of documents with that score >= 0.5, the standard sigmoid threshold):
  hostile = anger, annoyance, disapproval, disgust;  positive = admiration, approval, gratitude, joy, love, optimism, excitement, amusement, caring, pride, relief;
  inquisitive = curiosity, confusion;  fearful = fear, nervousness;  neutral = neutral.
Sample (documents as in seso_topics.py: comments and self-posts >= 15 words):
  r/StopEatingSeedOils: for each THEME (topic groups below) and period (before / from 2024-01-01) up to CAP documents (all if fewer), plus a random baseline of BASE
  documents per period.  r/ScientificNutrition: a random baseline of BASE documents per period.  Seed 5.
Topic ids are those of seedoils/data/processed/seso_doc_topics.csv.gz (BERTopic run of 18 Nov; see PLAN.md for what each topic is).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
SPLIT = 1704067200
CAP, BASE = 1200, 3000
MODEL = "SamLowe/roberta-base-go_emotions"
THEMES = {"politics (RFK, Trump, left/right)": [46, 117, 43, 68, 107], "vaccines & COVID": [20], "pharma, FDA, corporations": [10, 50, 80, 116],
          "omega-6 / PUFA biochemistry": [0, 79, 96], "keto, carbs, fasting": [1, 66], "studies & evidence": [23, 52, 53],
          "shopping (Costco, avocado oil, chips)": [17, 11, 9], "ingredient labels & processed food": [61, 92, 60]}
GROUPS = {"hostile": ["anger", "annoyance", "disapproval", "disgust"],
          "positive": ["admiration", "approval", "gratitude", "joy", "love", "optimism", "excitement", "amusement", "caring", "pride", "relief"],
          "inquisitive": ["curiosity", "confusion"], "fearful": ["fear", "nervousness"], "neutral": ["neutral"]}


def sample():
    rng = np.random.default_rng(5)
    parts = []
    for sub, pfx in (("StopEatingSeedOils", "seso"), ("ScientificNutrition", "scinut")):
        D = pd.read_csv(PROC / f"{pfx}_docs.csv.gz", usecols=["id", "kind", "created_utc", "text"])
        T = pd.read_csv(PROC / f"{pfx}_doc_topics.csv.gz", usecols=["id", "topic"])
        D = D.merge(T, on="id")
        D["period"] = np.where(D.created_utc >= SPLIT, "from2024", "pre2024")
        D["subreddit"] = sub
        for per in ("pre2024", "from2024"):
            P = D[D.period == per]
            base = P.sample(min(BASE, len(P)), random_state=int(rng.integers(1e9))).assign(theme="all (random)")
            parts.append(base)
            if sub == "StopEatingSeedOils":
                for name, ids in THEMES.items():
                    Q = P[P.topic.isin(ids)]
                    parts.append(Q.sample(min(CAP, len(Q)), random_state=int(rng.integers(1e9))).assign(theme=name))
    return pd.concat(parts, ignore_index=True)


def score():
    import torch
    from transformers import pipeline
    S = sample()
    print(f"{len(S):,} documents to score; by subreddit/period: {S.groupby(['subreddit', 'period']).size().to_dict()}", flush=True)
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    clf = pipeline("text-classification", model=MODEL, top_k=None, truncation=True, max_length=256, device=dev, batch_size=32)
    texts = S.text.tolist()
    rows = []
    for i in range(0, len(texts), 640):
        out = clf(texts[i:i + 640])
        rows += [{d["label"]: d["score"] for d in o} for o in out]
        print(f"  {min(i + 640, len(texts)):,}/{len(texts):,}", flush=True)
    E = pd.DataFrame(rows)
    R = pd.concat([S[["id", "subreddit", "period", "theme", "topic"]].reset_index(drop=True), E.round(4)], axis=1)
    R.to_csv(PROC / "emotion_scores.csv.gz", index=False)
    print("wrote emotion_scores.csv.gz", R.shape)


def summary():
    R = pd.read_csv(PROC / "emotion_scores.csv.gz")
    for g, labs in GROUPS.items():
        R[g] = R[labs].max(axis=1)
    out = []
    for (sub, theme, per), d in R.groupby(["subreddit", "theme", "period"]):
        row = {"subreddit": sub, "theme": theme, "period": per, "n": len(d)}
        for g in GROUPS:
            row[f"{g}_share"] = round(float((d[g] >= 0.5).mean()), 4)
            row[f"{g}_mean"] = round(float(d[g].mean()), 4)
        out.append(row)
    O = pd.DataFrame(out)
    O.to_csv(PROC / "emotion_summary.csv", index=False)
    pd.set_option("display.width", 220)
    print(O[["subreddit", "theme", "period", "n", "hostile_share", "positive_share", "inquisitive_share", "neutral_share"]].to_string(index=False))


if __name__ == "__main__":
    summary() if len(sys.argv) > 1 and sys.argv[1] == "summary" else score()
