"""DeepMoji via the torchMoji port (huggingface/torchMoji with the Uberduck/torchmoji weights; two one-line patches, see torchmoji_check.py) on ALL comments and self-posts
(>= 15 words as in seso_topics.py plus the 1-14 word ones from short_docs.py) of r/StopEatingSeedOils and r/ScientificNutrition.
Replaces the ONNX-port scores, which did not agree with torchMoji (see torchmoji_check.py: 44% same top-1 emoji on 600 comments). Old monthly table kept as deepmoji_monthly_onnx.csv.
Token limit: MAXLEN from torchmoji_check.py (256 DeepMoji tokens since 22 Nov; was 30). Outputs (local, scores only): data/processed/deepmoji_tm<MAXLEN>_<sub><part>.npz (gitignored;
the 30-token run is deepmoji_tm_<sub><part>.npz) and deepmoji_monthly.csv (mean probability per emoji id 0-63 per month and subreddit). The 30-token monthly table is kept as
deepmoji_monthly_tm30.csv the first time this runs.
Run from final_project/:  ./.venv-torchmoji/bin/python seedoils/notebooks/deepmoji_torch_time.py"""
import sys, warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from torchmoji_check import MAXLEN, score  # noqa: E402
PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
rows = []
for sub, pfx in (("r/StopEatingSeedOils", "seso"), ("r/ScientificNutrition", "scinut")):
    parts = []
    for part in ("",):  # 15+ words only, as for GoEmotions (decision 22 Nov); the 1-14 word scores (deepmoji_tm256_*_short.npz) are kept but not used
        f = PROC / f"deepmoji_tm{MAXLEN}_{pfx}{part}.npz"  # new name per limit: the loop skips files that exist
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
old, keep = PROC / "deepmoji_monthly.csv", PROC / "deepmoji_monthly_tm30.csv"
if old.exists() and not keep.exists():
    old.rename(keep)  # the previous (30-token) table
M = pd.concat(rows); M["maxlen"] = MAXLEN; M.to_csv(PROC / "deepmoji_monthly.csv", index=False); print("done", M.shape, "maxlen", MAXLEN)
