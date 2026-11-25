"""SUPERSEDED by deepmoji_torch_time.py (torchMoji). This ONNX port agreed with torchMoji on the top emoji for only 44% of 600 comments (torchmoji_check.py),
so its scores (deepmoji_monthly_onnx.csv) should not be used.
DeepMoji (emoji-prediction model trained on 1.2 billion tweets; ONNX port 'deepmoji-onnx') on the comments and self-posts of r/StopEatingSeedOils and r/ScientificNutrition
(ALL documents: those of >= 15 words as in seso_topics.py plus the 1-14 word ones from short_docs.py). For each document the model gives a probability over 64 emojis; texts longer than 30 tokens are truncated by the model.
Outputs (local; scores only, no text): seedoils/data/processed/deepmoji_<sub>.npz (ids + created_utc + float16 probabilities, gitignored), deepmoji_monthly.csv (mean probability per emoji per month and subreddit).
Needs its own env (onnxruntime had no Python 3.14 wheel): python3.12 -m venv .venv-moji; .venv-moji/bin/pip install deepmoji-onnx pandas
Run from final_project/:  ./.venv-moji/bin/python seedoils/notebooks/deepmoji_time.py"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from deepmoji_onnx import DeepMojiONNX

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
dm = DeepMojiONNX.from_pretrained("fp32", providers=["CPUExecutionProvider"])
rows = []
for sub, pfx in (("r/StopEatingSeedOils", "seso"), ("r/ScientificNutrition", "scinut")):
    parts = []
    for part in ("", "_short"):  # '' = documents of >= 15 words (the topic corpus); '_short' = 1-14 words (short_docs.py); resumable per part
        f = PROC / f"deepmoji_{pfx}{part}.npz"
        D = pd.read_csv(PROC / f"{pfx}{part}_docs.csv.gz", usecols=["id", "created_utc", "text"], keep_default_na=False)
        if f.exists():
            P = np.load(f, allow_pickle=True)["p"]
        else:
            P = np.zeros((len(D), 64), dtype=np.float16)
            texts = D.text.astype(str).tolist()
            for i in range(0, len(texts), 1000):
                P[i:i + 1000] = dm.predict(texts[i:i + 1000]).astype(np.float16)
                if (i // 1000) % 20 == 0:
                    print(sub, part, i, len(texts), flush=True)
            np.savez_compressed(f, id=D.id.values.astype(str), t=D.created_utc.values, p=P)
        parts.append((D, P))
    P = np.concatenate([p for _, p in parts]); T = np.concatenate([d.created_utc.values for d, _ in parts])
    m = pd.to_datetime(T, unit="s").strftime("%Y-%m").values
    df = pd.DataFrame(P.astype(np.float32)); df["month"] = m
    g = df.groupby("month").mean(); g["n"] = df.groupby("month").size(); g["subreddit"] = sub
    rows.append(g.reset_index())
M = pd.concat(rows); M.to_csv(PROC / "deepmoji_monthly.csv", index=False); print("done", M.shape)
