"""Table 1 of the paper, drawn as a small PDF (paper/figures/table1_fit.pdf): reading check of the outlier rule, per group fit rate with Wilson 95% interval, and fit-or-partly.
Reason: the PNAS class spread the rows of a LaTeX table over the column; a drawn table keeps its layout. Inputs (local, same as topic_fit_reading_score.py): the answers CSV (default ~/Downloads/topic_fit_reading_answers.csv), topic_fit_reading_key.csv and topic_fit_population.json in processed_rebuild_prob/.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/table1_fit_figure.py [answers.csv]"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
R = "seedoils/data/processed_rebuild_prob/"; f = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads" / "topic_fit_reading_answers.csv"
A = pd.read_csv(f).merge(pd.read_csv(R + "topic_fit_reading_key.csv"), on="id"); pop = json.load(open(R + "topic_fit_population.json")); A = A[A.answer.isin(["fits", "partly", "no"])]
def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)); return (c - h) / d, (c + h) / d
names = {"BASE (HDBSCAN topic)": "Placed by the clustering", "outlier p in [0.1, 1.01)": "Rescued, 0.10 or more", "outlier p in [0.05, 0.1)": "Rescued, 0.05 to 0.10", "outlier p in [0.02, 0.05)": "Rescued, 0.02 to 0.05", "outlier p in [0.01, 0.02)": "Rescued, 0.01 to 0.02"}
rows = [("Group", "Documents", "Fit (95% CI)", "Fit or partly")]
for b in pop:
    s = A[A.band == b]; n = len(s); k = int((s.answer == "fits").sum()); kp = int(s.answer.isin(["fits", "partly"]).sum()); lo, hi = wilson(k, n)
    rows.append((names[b], f"{pop[b]:,}", f"{k / n:.0%} ({lo:.0%}-{hi:.0%})".replace("%-", "-"), f"{kp / n:.0%}"))
print(rows)
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"], "font.size": 7, "pdf.fonttype": 42})
fig = plt.figure(figsize=(3.43, 0.17 * len(rows) + 0.06)); ax = fig.add_axes([0.005, 0.01, 0.99, 0.98]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(-0.05, len(rows) + 0.05)  # fixed size, no tight cropping: LaTeX includes it at its natural width, so the 7 pt font stays 7 pt
xs = {"l": 0.0, "r": 0.50, "c1": 0.685, "c2": 1.0}
for i, r in enumerate(rows):
    y = len(rows) - i - 0.5; w = "bold" if i == 0 else "normal"
    ax.text(xs["l"], y, r[0], ha="left", va="center", fontweight=w); ax.text(xs["r"], y, r[1], ha="right", va="center", fontweight=w)
    ax.text(xs["c1"], y, r[2], ha="center", va="center", fontweight=w); ax.text(xs["c2"], y, r[3], ha="right", va="center", fontweight=w)
for y, lw in ((len(rows), 0.8), (len(rows) - 1, 0.5), (0, 0.8)): ax.plot([0, 1], [y, y], color="black", lw=lw, clip_on=False)
fig.savefig("paper/figures/table1_fit.pdf"); fig.savefig("seedoils/figures/table1_fit.png", dpi=200)
