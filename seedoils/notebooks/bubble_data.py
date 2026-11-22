"""Dataset 'topic_bubbles' for the bubble figure: the 30 biggest BERTopic topics per subreddit, share of comments before / from 2024.
Run from final_project/:  ../.venv/bin/python seedoils/notebooks/bubble_data.py -> seedoils/data/processed/artifact/topic_bubbles.json
Reads seso_/scinut_topics_info.csv (seso_topics.py). Shares are percent of all documents (comments and self-posts >= 15 words) in the period. No text, no usernames.
'theme' = the hand-made theme groups of emotions.py for r/StopEatingSeedOils (topic ids), blank otherwise."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
THEMES = {"Politics": [46, 117, 43, 68, 107], "Vaccines and COVID": [20], "Pharma, FDA, corporations": [10, 50, 80, 116], "Omega-6 / PUFA biochemistry": [0, 79, 96],
          "Keto, carbs, fasting": [1, 66], "Studies and evidence": [23, 52, 53], "Shopping": [17, 11, 9], "Ingredient labels and processed food": [61, 92, 60]}
T2TH = {t: k for k, v in THEMES.items() for t in v}
rows = []
for sub, pfx in (("r/StopEatingSeedOils", "seso"), ("r/ScientificNutrition", "scinut")):
    I = pd.read_csv(PROC / f"{pfx}_topics_info.csv")
    I = I[I.topic >= 0].copy()
    I["mx"] = I[["share_pre2024", "share_from2024"]].max(axis=1)
    for _, r in I.sort_values("mx", ascending=False).head(30).iterrows():
        rows.append({"subreddit": sub, "topic": int(r.topic), "words": r.top_words, "share_pre2024": round(r.share_pre2024 * 100, 2), "share_from2024": round(r.share_from2024 * 100, 2),
                     "ratio": float(r.ratio_from2024_vs_pre), "theme": T2TH.get(int(r.topic), "") if pfx == "seso" else ""})
meta = [{"label": "bubble_data.py", "value": Path(__file__).read_text()}]
(PROC / "artifact" / "topic_bubbles.json").write_text(json.dumps({"rows": rows, "meta": meta}))
print(len(rows))
