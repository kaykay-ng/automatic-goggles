"""FINAL theme analysis (26 Nov 2026): 13 themes (themes_full.json) on the rebuilt BERTopic, outliers handled as BERTopic's documentation describes:
an HDBSCAN outlier is moved to its highest-probability topic only if that probability >= THRESHOLD (0.05, the docs' example value); other outliers stay UNASSIGNED and are left out. Clustered documents keep their topic.
Saves the assignment (ids only, no text or names) to seedoils/data/processed_rebuild_prob/seso_doc_topics_prob005.csv.gz.
Per theme: documents, share of assigned documents before 2024 / from 2024 and the ratio; GoEmotions groups (positive / negative / ambiguous = any emotion of the group >= 0.5; neutral = top label neutral; 'disapproving tone' flag = anger, annoyance, disapproval, disgust >= 0.5)
before 2024, 2024 Jan-Jul and from Aug 2024, with a 95% bootstrap interval for the change in the negative-group share (before 2024 -> from Aug 2024).
Outputs: seedoils/data/processed/themes_final_summary.csv, paper/figures/themes_final_negative.pdf, seedoils/figures/themes_final_negative.png.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/themes_final.py"""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

THRESHOLD = 0.05
R, P, Q = "seedoils/data/processed_rebuild_prob/", "seedoils/data/processed/", "seedoils/data/processed_rebuild/"
z = np.load(R + "seso_probs.npz", allow_pickle=True); pr = z["p"].astype(np.float32); T = pd.read_csv(R + "seso_doc_topics.csv.gz"); assert (T.id.values == z["id"]).all()
T["maxp"] = pr.max(1); T["arg"] = pr.argmax(1)
T["topic_final"] = np.where(T.topic_before_outlier_fix != -1, T.topic_before_outlier_fix, np.where(T.maxp >= THRESHOLD, T.arg, -1))
TAG = os.environ.get("SEDOIL_TAG", "")  # e.g. _v2 with SEDOIL_THEMES=seedoils/data/processed/themes_full_v2.json
th = json.load(open(os.environ.get("SEDOIL_THEMES", P + "themes_full.json"))); m = {int(i): k for k, v in th.items() for i in v}; names = list(th); T["theme"] = T.topic_final.map(m)
T[["id", "created_utc", "topic_final", "theme"]].to_csv(R + f"seso_doc_topics_prob005{TAG}.csv.gz", index=False)
T["t"] = pd.to_datetime(T.created_utc, unit="s"); T["per"] = pd.cut(T.t, [pd.Timestamp("2000-01-01"), pd.Timestamp("2024-01-01"), pd.Timestamp("2024-08-01"), pd.Timestamp("2030-01-01")], labels=["before 2024", "2024 Jan-Jul", "from Aug 2024"], right=False)
g = np.load(Q + "goemo_seso.npz", allow_pickle=True); labs = list(pd.read_csv(P + "goemo_monthly.csv", nrows=1).columns[1:29]); Pm = g["p"].astype(float)
G = {"positive": "admiration amusement approval caring desire excitement gratitude joy love optimism pride relief".split(), "negative": "anger annoyance disappointment disapproval disgust embarrassment fear grief nervousness remorse sadness".split(), "ambiguous": "confusion curiosity realization surprise".split()}
E = pd.DataFrame({"id": g["id"]}); 
for k, ls in G.items(): E[k] = (Pm[:, [labs.index(l) for l in ls]] >= 0.5).any(1)
E["neutral"] = Pm.argmax(1) == labs.index("neutral"); E["flag"] = (Pm[:, [labs.index(l) for l in "anger annoyance disapproval disgust".split()]] >= 0.5).any(1); T = T.merge(E, on="id")
K = T[T.theme.notna()]; print(f"documents {len(T):,}; in a theme {len(K):,} ({len(K) / len(T):.1%}); unassigned {len(T) - len(K):,} ({1 - len(K) / len(T):.1%})")
rng = np.random.default_rng(0); rows = []
for k in names:
    s = K[K.theme == k]; a, b, c = (s[s.per == p] for p in ("before 2024", "2024 Jan-Jul", "from Aug 2024")); sh0 = len(s[s.per == "before 2024"]) / (K.per == "before 2024").sum() * 100; sh1 = len(s[s.per != "before 2024"]) / (K.per != "before 2024").sum() * 100
    bs = [rng.choice(c.negative.values, len(c)).mean() - rng.choice(a.negative.values, len(a)).mean() for _ in range(400)]
    rows.append({"theme": k, "docs": len(s), "share_before": round(sh0, 2), "share_from24": round(sh1, 2), "ratio": round(sh1 / sh0, 2), "neg_before": round(100 * a.negative.mean(), 1), "neg_jan_jul": round(100 * b.negative.mean(), 1), "neg_from_aug": round(100 * c.negative.mean(), 1),
                 "neg_change": round(100 * (c.negative.mean() - a.negative.mean()), 1), "ci_lo": round(100 * np.percentile(bs, 2.5), 1), "ci_hi": round(100 * np.percentile(bs, 97.5), 1), "flag_before": round(100 * a.flag.mean(), 1), "flag_from_aug": round(100 * c.flag.mean(), 1),
                 "positive_from_aug": round(100 * c.positive.mean(), 1), "ambiguous_from_aug": round(100 * c.ambiguous.mean(), 1), "neutral_from_aug": round(100 * c.neutral.mean(), 1), "n_before": len(a), "n_from_aug": len(c)})
S = pd.DataFrame(rows); S.to_csv(P + f"themes_final_summary{TAG}.csv", index=False); pd.set_option("display.width", 300, "display.max_colwidth", 50); print(S.assign(theme=S.theme.str[:42])[["theme", "docs", "share_before", "share_from24", "ratio", "neg_before", "neg_jan_jul", "neg_from_aug", "neg_change", "ci_lo", "ci_hi", "n_before", "n_from_aug"]].to_string(index=False))
allk = K.groupby("per", observed=True)[["negative", "flag", "positive", "ambiguous", "neutral"]].mean().mul(100).round(1); print("\nall themes together:\n", allk.to_string())
# figure: negative-group share before vs from Aug 2024 per theme
plt.rcParams.update({"font.size": 7, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})
D = S.sort_values("neg_from_aug"); fig, ax = plt.subplots(figsize=(3.6, 3.4), constrained_layout=True)
for i, r in enumerate(D.itertuples()):
    sig = (r.ci_lo > 0) or (r.ci_hi < 0); ax.plot([r.neg_before, r.neg_from_aug], [i, i], color="#b5482a" if sig else "0.65", lw=1.4, zorder=1)
    ax.scatter([r.neg_before], [i], s=14, color="white", edgecolor="0.3", zorder=2); ax.scatter([r.neg_from_aug], [i], s=14, color="#b5482a" if sig else "0.55", zorder=3)
ax.set_yticks(range(len(D))); ax.set_yticklabels([n.split(" (")[0][:30] for n in D.theme]); ax.set_xlabel("Negative-group share of documents (%)")
ax.text(0.99, 0.02, "open = before 2024, filled = from Aug 2024\nred = change interval excludes 0", transform=ax.transAxes, ha="right", va="bottom", fontsize=5.5, color="0.35")
fig.savefig(f"paper/figures/themes_final_negative{TAG}.pdf"); fig.savefig(f"seedoils/figures/themes_final_negative{TAG}.png", dpi=200)
