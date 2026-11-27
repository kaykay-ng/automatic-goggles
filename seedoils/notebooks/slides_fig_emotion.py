"""Small slide figure: share of ALL documents with a negative GoEmotions emotion per quarter (2022 Q1 - 2026 Q3), 95% Wilson band, dotted line at 1 Jan 2024 (the paper's split). Drawn at its final size (2.35 x 1.25 in). Output: paper/slides/slides_fig_emotion.pdf. Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/slides_fig_emotion.py"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as md, numpy as np, pandas as pd
import os
R, Rp, P = "seedoils/data/processed_rebuild/", "seedoils/data/processed_rebuild_prob/", "seedoils/data/processed/"
if not os.path.exists(R + "goemo_seso.npz"): R = P  # same files in data/processed on the other machine
if not os.path.exists(Rp + "seso_doc_topics_official005.csv.gz"): Rp = P
labs = list(pd.read_csv(P + "goemo_monthly.csv", nrows=1).columns[1:29]); g = np.load(R + "goemo_seso.npz", allow_pickle=True); pr = g["p"].astype(np.float32); ids = g["id"]
A = pd.read_csv(Rp + "seso_doc_topics_official005.csv.gz", usecols=["id", "created_utc"]).set_index("id").loc[ids].reset_index(); A["q"] = pd.to_datetime(A.created_utc, unit="s").dt.to_period("Q").dt.to_timestamp()
NEG = "anger annoyance disappointment disapproval disgust embarrassment fear grief nervousness remorse sadness".split(); flag = (pr[:, [labs.index(e) for e in NEG]] >= 0.5).any(axis=1)
tot = A.groupby("q").size(); keep = tot[(tot.index >= "2022-01-01") & (tot.index < "2026-10-01")].index; n = tot.loc[keep].values.astype(float); s = pd.Series(flag).groupby(A.q.values).mean().reindex(keep) * 100
p = s.values / 100; z = 1.96; d = 1 + z * z / n; ctr = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d; x = keep + pd.Timedelta(days=45)
print(s.round(1).tolist())
plt.rcParams.update({"font.size": 6.5, "axes.spines.top": False, "axes.spines.right": False, "font.family": "sans-serif"})
fig, ax = plt.subplots(figsize=(2.35, 0.95)); ax.fill_between(x, (ctr - h) * 100, (ctr + h) * 100, color="#b5482a", alpha=0.2, lw=0); ax.plot(x, s.values, color="#b5482a", lw=1.6, marker="o", ms=2)
for dd in ("2024-01-01",): ax.axvline(pd.Timestamp(dd), color="0.5", ls=":", lw=0.8)
ax.set_ylim(0, 11); ax.set_ylabel("% of documents"); ax.xaxis.set_major_locator(md.YearLocator(2)); ax.xaxis.set_major_formatter(md.DateFormatter("%Y")); ax.set_title("Negative emotion per quarter", loc="left", fontsize=6.8, fontweight="bold")
fig.savefig("paper/slides/slides_fig_emotion.pdf", bbox_inches="tight", pad_inches=0.02); fig.savefig("seedoils/figures/slides_fig_emotion.png", dpi=200, bbox_inches="tight", pad_inches=0.02)
