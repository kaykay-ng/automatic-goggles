"""DeepMoji via the torchMoji port (huggingface/torchMoji with the Uberduck/torchmoji weights; two one-line patches, see torchmoji_check.py) on ALL comments and self-posts
(>= 15 words as in seso_topics.py plus the 1-14 word ones from short_docs.py) of r/StopEatingSeedOils and r/ScientificNutrition.
Replaces the ONNX-port scores, which did not agree with torchMoji (see torchmoji_check.py: 44% same top-1 emoji on 600 comments). Old monthly table kept as deepmoji_monthly_onnx.csv.
Outputs (local, scores only): data/processed/deepmoji_tm_<sub><part>.npz (gitignored) and deepmoji_monthly.csv (same layout as before: mean probability per emoji id 0-63 per month and subreddit).
Run from final_project/:  ./.venv-torchmoji/bin/python seedoils/notebooks/deepmoji_torch_time.py"""
import sys, warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from torchmoji_check import score  # noqa: E402
PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
rows = []
for sub, pfx in (("r/StopEatingSeedOils", "seso"), ("r/ScientificNutrition", "scinut")):
    parts = []
    for part in ("", "_short"):
        f = PROC / f"deepmoji_tm_{pfx}{part}.npz"
        D = pd.read_csv(PROC / f"{pfx}{part}_docs.csv.gz", usecols=["id", "created_utc", "text"], keep_default_na=False)
        if f.exists():
            P = np.load(f, allow_pickle=True)["p"]
        else:
            P = np.zeros((len(D), 64), dtype=np.float16); texts = D.text.astype(str).tolist()
            for i in range(0, len(texts), 5000):
                P[i:i + 5000] = score(texts[i:i + 5000]).astype(np.float16); print(sub, part, i, len(texts), flush=True)
            np.savez_compressed(f, id=D.id.values.astype(str), t=D.created_utc.values, p=P)
        parts.append((D, P))
    P = np.concatenate([p for _, p in parts]); T = np.concatenate([d.created_utc.values for d, _ in parts])
    df = pd.DataFrame(P.astype(np.float32)); df["month"] = pd.to_datetime(T, unit="s").strftime("%Y-%m").values
    g = df.groupby("month").mean(); g["n"] = df.groupby("month").size(); g["subreddit"] = sub; rows.append(g.reset_index())
M = pd.concat(rows); M.to_csv(PROC / "deepmoji_monthly.csv", index=False); print("done", M.shape)
