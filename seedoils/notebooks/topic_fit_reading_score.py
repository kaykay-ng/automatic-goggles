"""Score the topic-fit reading (topic_fit_reading.html). Input: CSV downloaded from the page (default ~/Downloads/topic_fit_reading_answers.csv; columns id,answer = fits / partly / no), topic_fit_reading_key.csv and topic_fit_population.json.
Per band: n read, share that FIT (strict) and share fitting or partly, Wilson 95% intervals. Then, for each candidate threshold t in {0.10, 0.05, 0.02, 0.01}: the population-weighted fit of ALL outliers moved at t (bands at or above t weighted by their number of documents), the number moved, and the share of all documents that would carry a topic, with bootstrap 95% intervals (2000 resamples of the reads inside each band).
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/topic_fit_reading_score.py [answers.csv]"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
R = "seedoils/data/processed_rebuild_prob/"; f = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads" / "topic_fit_reading_answers.csv"
A = pd.read_csv(f).merge(pd.read_csv(R + "topic_fit_reading_key.csv"), on="id"); pop = json.load(open(R + "topic_fit_population.json")); A = A[A.answer.isin(["fits", "partly", "no"])]
A["fit"] = (A.answer == "fits").astype(float); A["fitp"] = A.answer.isin(["fits", "partly"]).astype(float)
def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)); return ((c - h) / d, (c + h) / d)
order = list(pop); print("answers read:", len(A))
for b in order:
    s = A[A.band == b]; n = len(s); k = int(s.fit.sum()); kp = int(s.fitp.sum()); lo, hi = wilson(k, n)
    print(f"{b:<28} n={n:>3}  FIT {k / max(n, 1):.0%} [{lo:.0%}, {hi:.0%}]   fit or partly {kp / max(n, 1):.0%}  (documents in band {pop[b]:,})")
rng = np.random.default_rng(0); outl = [b for b in order if b != order[0]]; edges = {"0.10": outl[:1], "0.05": outl[:2], "0.02": outl[:3], "0.01": outl[:4]}; Nall = 149815  # all documents, including the 14,738 outliers below 0.01 that no band covers; print()
for t, bs in edges.items():
    w = np.array([pop[b] for b in bs], float); moved = int(w.sum())
    def est(col):
        ps = np.array([A[A.band == b][col].mean() for b in bs]); return float((ps * w).sum() / w.sum())
    bt = []
    for _ in range(2000):
        ps = np.array([A[A.band == b].fit.sample(frac=1, replace=True, random_state=int(rng.integers(1e9))).mean() for b in bs]); bt.append((ps * w).sum() / w.sum())
    print(f"threshold {t}: moves {moved:>6,} outliers; fit of the moved set {est('fit'):.0%} [{np.percentile(bt, 2.5):.0%}, {np.percentile(bt, 97.5):.0%}] (fit or partly {est('fitp'):.0%}); documents with a topic then {(pop[order[0]] + moved) / Nall:.1%}")
