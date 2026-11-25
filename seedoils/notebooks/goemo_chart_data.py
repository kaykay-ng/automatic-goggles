"""Dataset 'goemo' for the artifact: GoEmotions (SamLowe/roberta-base-go_emotions) group shares per quarter and subreddit, ALL comments (long + short).
Value = percent of documents with at least one label of the group scored >= 0.5. Groups are ours (see emotions.py GROUPS); neutral omitted.
Run after emotions_full.py:  python seedoils/notebooks/goemo_chart_data.py -> seedoils/data/processed/artifact/goemo.json. Quarters with < 300 documents dropped."""
import json
from pathlib import Path
import pandas as pd
PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
LAB = {"hostile": "Hostile", "positive": "Positive", "inquisitive": "Inquisitive", "fearful": "Fearful"}
NOTE = {"hostile": "anger, annoyance, disapproval, disgust", "positive": "admiration, approval, gratitude, joy, love, optimism, excitement, amusement, caring, pride, relief", "inquisitive": "curiosity, confusion", "fearful": "fear, nervousness"}
M = pd.read_csv(PROC / "goemo_monthly.csv")
M["q"] = pd.PeriodIndex(M.month, freq="M").asfreq("Q").astype(str)
rows = []
for (sub, q), g in M.groupby(["subreddit", "q"]):
    n = int(g.n.sum())
    if n < 300 or q < "2020Q1":
        continue
    for k, name in LAB.items():
        rows.append({"subreddit": sub, "quarter": q, "group": name, "pct": round((g[f"{k}_share"] * g.n).sum() / n * 100, 2), "n": n, "labels": NOTE[k]})
meta = [{"label": "goemo_chart_data.py", "value": Path(__file__).read_text()}]
(PROC / "artifact" / "goemo.json").write_text(json.dumps({"rows": rows, "meta": meta}))
print(len(rows), "rows")
d = pd.DataFrame(rows); print(d[d.subreddit.str.contains("StopEating")].pivot(index="quarter", columns="group", values="pct").round(1).iloc[::3])
