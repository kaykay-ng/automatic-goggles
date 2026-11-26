"""Score the threshold reading (threshold_reading.html). Input: the CSV downloaded from the page (default ~/Downloads/threshold_reading_answers.csv; columns id,answer with fits / partly / no) and threshold_reading_key.csv (id, theme, side, maxp).
Per theme and side (above 0.05 = reassigned, below = left unassigned): number read, share that FIT (strict: 'fits' only) and share fitting or partly, with Wilson 95% intervals; and the above-minus-below difference in strict fit with a bootstrap interval, overall and per theme.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/threshold_reading_score.py [answers.csv]"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ans = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("seedoils/data/processed/threshold_reading_answers.csv")  # the CSV downloaded from the reading page (ids and answers only; copied here)
K = pd.read_csv("seedoils/data/processed/threshold_reading_key.csv"); A = pd.read_csv(ans); A["answer"] = A.answer.fillna("").str.strip().str.lower()
D = K.merge(A, on="id"); print(f"{len(D)} answers read of {len(K)}; unanswered {int((D.answer == '').sum())}"); D = D[D.answer != ""]
D["fit"] = D.answer == "fits"; D["fit_or_partly"] = D.answer.isin(["fits", "partly"])
def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d; return (c - h, c + h)
rng = np.random.default_rng(0); rows = []
for (th, side), g in list(D.groupby(["theme", "side"])) + [(("ALL THREE", s), D[D.side == s]) for s in ("above", "below")]:
    lo, hi = wilson(int(g.fit.sum()), len(g)); rows.append({"theme": th[:34], "side": side, "n": len(g), "fits_%": round(100 * g.fit.mean()), "fits_95%": f"{100 * lo:.0f}-{100 * hi:.0f}", "fit_or_partly_%": round(100 * g.fit_or_partly.mean())})
pd.set_option("display.width", 200); print(pd.DataFrame(rows).sort_values(["theme", "side"]).to_string(index=False))
for th in [None] + sorted(D.theme.unique()):
    g = D if th is None else D[D.theme == th]; a, b = g[g.side == "above"].fit.values, g[g.side == "below"].fit.values
    if len(a) < 3 or len(b) < 3: continue
    bs = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(2000)]
    print(f"above minus below, strict fit: {100 * (a.mean() - b.mean()):+.0f} points [{100 * np.percentile(bs, 2.5):+.0f}, {100 * np.percentile(bs, 97.5):+.0f}]  ({'all three themes' if th is None else th[:40]})")
