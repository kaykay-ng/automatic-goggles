"""GoEmotions (SamLowe/roberta-base-go_emotions, 28 labels, multi-label sigmoid scores) on ALL documents of r/StopEatingSeedOils and r/ScientificNutrition
(comments and self-posts: those of >= 15 words as in seso_topics.py plus the 1-14 word ones from short_docs.py; texts truncated to 256 tokens). Same classifier as emotions.py (which scored a sample); still PROVISIONAL.
Outputs (scores only, no text): seedoils/data/processed/goemo_<sub>.npz (ids, created_utc, float16 scores; gitignored), goemo_monthly.csv (per month and subreddit: n, mean score per label,
share of documents with the group score >= 0.5 for hostile/positive/inquisitive/fearful/neutral as in emotions.py GROUPS).
Resumable per subreddit (skips one whose npz exists). Run from final_project/ with the NLP env, in the background:  ./.venv-nlp/bin/python seedoils/notebooks/emotions_full.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from emotions import GROUPS, MODEL  # noqa: E402

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"


def main():
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL); mod = AutoModelForSequenceClassification.from_pretrained(MODEL).to(dev).eval()
    labels = [mod.config.id2label[i] for i in range(mod.config.num_labels)]
    out = []
    for sub, pfx in (("r/StopEatingSeedOils", "seso"), ("r/ScientificNutrition", "scinut")):
        PS, TS = [], []
        for part in ("",):  # 15+ words only (decision 22 Nov: emotions use the topic corpus); the 1-14 word scores (goemo_*_short.npz) are kept but not used
            f = PROC / f"goemo_{pfx}{part}.npz"
            D = pd.read_csv(PROC / f"{pfx}{part}_docs.csv.gz", usecols=["id", "created_utc", "text"], keep_default_na=False)
            if f.exists():
                P = np.load(f, allow_pickle=True)["p"]
            else:
                texts = D.text.astype(str).tolist(); order = np.argsort([len(t) for t in texts]); P = np.zeros((len(D), len(labels)), dtype=np.float16)
                for s in range(0, len(order), 64):
                    idx = order[s:s + 64]
                    enc = tok([texts[i] for i in idx], truncation=True, max_length=256, padding=True, return_tensors="pt").to(dev)
                    with torch.no_grad():
                        P[idx] = torch.sigmoid(mod(**enc).logits).float().cpu().numpy().astype(np.float16)
                    if (s // 64) % 200 == 0:
                        print(sub, part, s, len(order), flush=True)
                np.savez_compressed(f, id=D.id.values.astype(str), t=D.created_utc.values, p=P)
            PS.append(P); TS.append(D.created_utc.values)
        P = np.concatenate(PS); T = np.concatenate(TS)
        df = pd.DataFrame(P.astype(np.float32), columns=labels)
        for g, ls in GROUPS.items():
            df[f"{g}_share"] = (df[ls].max(axis=1) >= 0.5).astype(float)
        df["month"] = pd.to_datetime(T, unit="s").strftime("%Y-%m").values
        g = df.groupby("month").mean(); g["n"] = df.groupby("month").size(); g["subreddit"] = sub; out.append(g.reset_index())
    M = pd.concat(out); M.to_csv(PROC / "goemo_monthly.csv", index=False); print("done", M.shape)


if __name__ == "__main__":
    main()
