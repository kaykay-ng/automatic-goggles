"""Figure 3b from the hand labels (position_labels_<initials>.csv from label_positions.html; key position_sample_key.csv).
Per subreddit x period (40 comments each): counts of H harmful / N not harmful / M mixed / Q no position / X off the claim, and the share 'harmful'
among comments that take a position (H, N, M) with a Wilson 95% interval. One labeller: their labels; two: agreement (Cohen's kappa) and, for the
figure, only comments where they agree (disagreements reported); three or more: majority label (ties left out).
Writes data/processed/position_eval.json and data/processed/artifact/online.json (the dashboard's Figure 3b, now hand-labelled; the AI-labelled
version is kept as online_ai.json the first time). Aggregates only. Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/position_eval.py"""
import glob
import json
import math
import shutil
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

P = Path("seedoils/data/processed"); A = P / "artifact"
key = pd.read_csv(P / "position_sample_key.csv").set_index("item")
files = sorted(glob.glob(str(P / "position_labels_*.csv")))
if not files:
    raise SystemExit("no position_labels_*.csv in data/processed/: export it from seedoils/label_positions.html first")
labs = {}
for f in files:
    d = pd.read_csv(f, dtype=str).fillna(""); d["item"] = d.item.astype(int); labs[Path(f).stem.replace("position_labels_", "")] = d.set_index("item").label.reindex(key.index).fillna("")
L = pd.DataFrame(labs); out = {"labellers": list(labs), "comments": int(len(key))}
if len(labs) >= 2:
    out["agreement"] = []
    for i, a in enumerate(labs):
        for b in list(labs)[i + 1:]:
            ok = (L[a] != "") & (L[b] != "")
            out["agreement"].append({"pair": f"{a}-{b}", "n": int(ok.sum()), "percent": round(float((L[a][ok] == L[b][ok]).mean() * 100), 1),
                                     "kappa_5_labels": round(float(cohen_kappa_score(L[a][ok], L[b][ok])), 3),
                                     "kappa_harmful_vs_rest": round(float(cohen_kappa_score(L[a][ok] == "H", L[b][ok] == "H")), 3)})
if len(labs) == 1:
    ref = L.iloc[:, 0]; rule = "single labeller"
elif len(labs) == 2:
    ref = L.iloc[:, 0].where(L.iloc[:, 0] == L.iloc[:, 1], ""); rule = "both labellers agree"
else:
    def maj(r):
        c = Counter(x for x in r if x); top = c.most_common(2)
        return top[0][0] if top and (len(top) == 1 or top[0][1] > top[1][1]) else ""
    ref = L.apply(maj, axis=1); rule = "majority"
out["rule"] = rule; out["used"] = int((ref != "").sum())


def wilson(k, n):
    if n == 0:
        return [None, None]
    p, z = k / n, 1.96; c = (p + z * z / (2 * n)) / (1 + z * z / n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(100 * (c - h), 1), round(100 * (c + h), 1)]


rows, cells = [], []
for s, short in (("StopEatingSeedOils", "r/StopEatingSeedOils"), ("ScientificNutrition", "r/ScientificNutrition")):
    for per, pl in (("pre2024", "before 2024"), ("from2024", "from 2024")):
        r = ref[(key.side == s) & (key.period == per)]; c = Counter(r[r != ""]); npos = c["H"] + c["N"] + c["M"]
        rows.append({"community": short, "period": pl, "n": int(sum(c.values())), "harmful": c["H"], "mixed": c["M"], "no_position": c["Q"], "not_harmful": c["N"], "off_claim": c["X"]})
        cells.append({"community": short, "period": pl, "labelled": int(sum(c.values())), "counts": dict(c), "with_position": npos,
                      "harmful_among_positions_pct": round(100 * c["H"] / npos, 1) if npos else None, "ci95": wilson(c["H"], npos)})
out["cells"] = cells
(P / "position_eval.json").write_text(json.dumps(out, indent=1))
if not (A / "online_ai.json").exists() and (A / "online.json").exists():
    shutil.copy(A / "online.json", A / "online_ai.json")
meta = [{"label": "Labels", "value": f"Hand-labelled by {', '.join(labs)} ({rule}), blind to subreddit and date, codebook v2 (H harmful, N not harmful, M mixed, Q no position, X off the claim)."},
        {"label": "Sample", "value": "Fresh random sample (seed 31) of comments of 15+ words mentioning a seed-oil term, 40 per subreddit and period; bots left out. Replaces the earlier AI-labelled sample (kept as online_ai.json)."}]
(A / "online.json").write_text(json.dumps({"rows": rows, "meta": meta}))
print(json.dumps(out, indent=1))
