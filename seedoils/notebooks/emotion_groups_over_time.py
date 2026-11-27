"""GoEmotions groups over time (positive / negative / ambiguous, plus neutral), r/StopEatingSeedOils vs r/ScientificNutrition.
Scores: seedoils/data/processed/goemo_<sub>.npz (SamLowe/roberta-base-go_emotions, 28 labels, sigmoid scores; documents of 15+ words, scored 19 Nov on the 18-19 Nov document set: 149,732 and 121,672 documents; the rerun corpus has a few documents more).
Group of a document = it has at least one emotion of that group scored >= 0.5 (a document can be in several; 'neutral' = neutral is its top label). Groups follow the GoEmotions paper taxonomy:
 positive: admiration amusement approval caring desire excitement gratitude joy love optimism pride relief | negative: anger annoyance disappointment disapproval disgust embarrassment fear grief nervousness remorse sadness | ambiguous: confusion curiosity realization surprise.
'Disapproving tone' flag (anger, annoyance, disapproval, disgust >= 0.5) is shown for comparison. Months with fewer than 100 documents are left out.
PER-TOPIC-GROUP SPLITS ARE NOT DONE HERE: seso_doc_topics.csv.gz on this machine is the 18 Nov file (129 topics), not the rerun's 123-topic assignment.
Writes paper/figures/emotion_groups_over_time.pdf, seedoils/figures/emotion_groups_over_time.png, seedoils/data/processed/emotion_groups_monthly.csv.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/emotion_groups_over_time.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROC = "seedoils/data/processed/"
labs = list(pd.read_csv(PROC + "goemo_monthly.csv", nrows=1).columns[1:29])
G = {"positive": "admiration amusement approval caring desire excitement gratitude joy love optimism pride relief".split(),
     "negative": "anger annoyance disappointment disapproval disgust embarrassment fear grief nervousness remorse sadness".split(),
     "ambiguous": "confusion curiosity realization surprise".split()}
FLAG = "anger annoyance disapproval disgust".split()
COL = {"negative": "#b5482a", "positive": "#2a7f62", "ambiguous": "#d19a2a", "neutral": "#7a8794"}
rows = []; out = {}
for sub, pfx in (("StopEatingSeedOils", "seso"), ("ScientificNutrition", "scinut")):
    z = np.load(PROC + f"goemo_{pfx}.npz", allow_pickle=True); P = z["p"].astype(float)
    d = pd.DataFrame({"month": pd.to_datetime(z["t"], unit="s").to_period("M").to_timestamp()})
    for g, ls in G.items(): d[g] = (P[:, [labs.index(l) for l in ls]] >= 0.5).any(1)
    d["neutral"] = P.argmax(1) == labs.index("neutral"); d["flag"] = (P[:, [labs.index(l) for l in FLAG]] >= 0.5).any(1)
    m = d.groupby("month").mean(); m["n"] = d.groupby("month").size(); m = m[m.n >= 100]; m["sub"] = sub; rows.append(m.reset_index()); out[sub] = m
pd.concat(rows).to_csv(PROC + "emotion_groups_monthly.csv", index=False)

plt.rcParams.update({"font.size": 7, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})
fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.5), sharey=True, constrained_layout=True)
for a, (sub, m), lab in zip(ax, out.items(), "AB"):
    sm = m[["negative", "positive", "ambiguous", "neutral"]].rolling(3, center=True, min_periods=1).mean()
    for g in ("neutral", "positive", "ambiguous", "negative"): a.plot(sm.index, sm[g], color=COL[g], lw=1.5, label=g)
    a.plot(sm.index, m.flag.rolling(3, center=True, min_periods=1).mean(), color=COL["negative"], lw=1.0, ls="--", label="disapproving-tone flag")
    for dt in ("2024-01-01", "2024-08-01"): a.axvline(pd.Timestamp(dt), color="0.45", ls=":", lw=0.8)
    a.set_title(f"r/{sub}", fontsize=7.5, loc="left", pad=8); a.set_xlim(pd.Timestamp("2019-06-01"), pd.Timestamp("2026-12-01"))
    a.xaxis.set_major_locator(mdates.YearLocator(2)); a.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    a.text(-0.02, 1.12, lab, transform=a.transAxes, fontweight="bold", fontsize=8)
ax[0].set_ylabel("Share of documents (3-month mean)"); ax[0].yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
ax[1].legend(frameon=False, fontsize=6, loc="center right", bbox_to_anchor=(1.0, 0.62))
fig.savefig("paper/figures/emotion_groups_over_time.pdf"); fig.savefig("seedoils/figures/emotion_groups_over_time.png", dpi=200)
for sub, m in out.items():
    for lab, a, b in (("2022-23", "2022-01", "2023-12"), ("2024 Jan-Jul", "2024-01", "2024-07"), ("2024 Aug-Dec", "2024-08", "2024-12"), ("2025-26", "2025-01", "2026-11")):
        s = m[(m.index >= a) & (m.index <= pd.Timestamp(b + "-28"))]
        print(f"r/{sub} {lab:<13} months {len(s):>2}  negative {s.negative.mean():.1%}  flag {s.flag.mean():.1%}  positive {s.positive.mean():.1%}  ambiguous {s.ambiguous.mean():.1%}  neutral {s.neutral.mean():.1%}")
