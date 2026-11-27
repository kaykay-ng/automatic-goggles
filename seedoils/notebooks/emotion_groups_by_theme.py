"""GoEmotions groups by TOPIC GROUP and over time, r/StopEatingSeedOils, on the REBUILT rerun topics (26 Nov; seedoils/data/processed_rebuild, made with seso_topics.py prep|embed|fit on seedoils/data/raw_haoyu).
Check done first: the rebuilt BERTopic reproduces the teammate's 123 topics (same sizes, 122 of 123 identical top-10 words at the same id), so her themes_confirmed.json applies unchanged.
Scores: goemo_seso.npz (SamLowe/roberta-base-go_emotions, 28 labels, sigmoid, 256 tokens, 15+ word documents, scored 19 Nov); the 83 rebuilt documents without a stored score are scored here with the same model (offline cache) and everything is saved to processed_rebuild/goemo_seso.npz.
Groups (GoEmotions taxonomy): positive / negative / ambiguous = at least one emotion of the group >= 0.5; neutral = neutral is the top label; 'disapproving-tone flag' = anger, annoyance, disapproval or disgust >= 0.5.
Topic groups: Politics | Vaccines and distrust (themes 'Vaccines and COVID' + 'Distrust of industry, medicine and media') | Other nine-theme topics | Outside the nine themes (72% of documents).
Writes seedoils/data/processed/emotion_groups_by_theme.csv and paper/figures/emotion_groups_by_theme.pdf, seedoils/figures/emotion_groups_by_theme.png.
Run from final_project/:  HF_HUB_OFFLINE=1 ./.venv-nlp/bin/python seedoils/notebooks/emotion_groups_by_theme.py"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from emotions import MODEL  # noqa: E402

OLD, NEW = Path("seedoils/data/processed"), Path("seedoils/data/processed_rebuild")
labs = list(pd.read_csv(OLD / "goemo_monthly.csv", nrows=1).columns[1:29])
D = pd.read_csv(NEW / "seso_docs.csv.gz", usecols=["id", "created_utc", "text"], keep_default_na=False)
f = NEW / "goemo_seso.npz"
if not f.exists():
    z = np.load(OLD / "goemo_seso.npz", allow_pickle=True); zid, zp = z["id"], z["p"]  # load each array ONCE (an npz member is decompressed on every access)
    have = dict(zip(zid, range(len(zid))))
    P = np.zeros((len(D), 28), dtype=np.float16); miss = []
    for i, x in enumerate(D.id.astype(str)):
        if x in have: P[i] = zp[have[x]]
        else: miss.append(i)
    print(f"{len(D) - len(miss):,} scores reused, {len(miss)} documents scored now")
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL); mod = AutoModelForSequenceClassification.from_pretrained(MODEL).to(dev).eval()
    assert [mod.config.id2label[i] for i in range(28)] == labs, "label order differs from goemo_monthly.csv"
    for s in range(0, len(miss), 32):
        idx = miss[s:s + 32]
        enc = tok([str(D.text[i]) for i in idx], truncation=True, max_length=256, padding=True, return_tensors="pt").to(dev)
        with torch.no_grad(): P[idx] = torch.sigmoid(mod(**enc).logits).float().cpu().numpy().astype(np.float16)
    np.savez_compressed(f, id=D.id.values.astype(str), t=D.created_utc.values, p=P)
z = np.load(f, allow_pickle=True); P = z["p"].astype(float)
G = {"positive": "admiration amusement approval caring desire excitement gratitude joy love optimism pride relief".split(),
     "negative": "anger annoyance disappointment disapproval disgust embarrassment fear grief nervousness remorse sadness".split(),
     "ambiguous": "confusion curiosity realization surprise".split()}
d = pd.DataFrame({"id": z["id"], "t": pd.to_datetime(z["t"], unit="s")})
for g, ls in G.items(): d[g] = (P[:, [labs.index(l) for l in ls]] >= 0.5).any(1)
d["neutral"] = P.argmax(1) == labs.index("neutral"); d["flag"] = (P[:, [labs.index(l) for l in "anger annoyance disapproval disgust".split()]] >= 0.5).any(1)
T = pd.read_csv(NEW / "seso_doc_topics.csv.gz", usecols=["id", "topic"]); d = d.merge(T, on="id", how="left"); assert d.topic.notna().all()
th = json.load(open(OLD / "themes_confirmed.json")); inv = {int(i): k for k, v in th.items() for i in v}
g2 = {"Politics (RFK, Trump, left/right)": "Politics", "Vaccines and COVID": "Vaccines and distrust", "Distrust of industry, medicine and media": "Vaccines and distrust"}
d["group"] = d.topic.map(lambda t: g2.get(inv[int(t)], "Other nine-theme topics") if int(t) in inv else "Outside the nine themes")
d["per"] = pd.cut(d.t, [pd.Timestamp("2000-01-01"), pd.Timestamp("2024-01-01"), pd.Timestamp("2024-08-01"), pd.Timestamp("2030-01-01")], labels=["before 2024", "2024 Jan-Jul", "from Aug 2024"], right=False)
cols = ["negative", "flag", "positive", "ambiguous", "neutral"]
tab = d.groupby(["group", "per"], observed=True)[cols].mean().mul(100).round(1); tab["n"] = d.groupby(["group", "per"], observed=True).size()
tab.to_csv(OLD / "emotion_groups_by_theme.csv"); print(tab.to_string())
print("\nALL\n", d.groupby("per", observed=True)[cols].mean().mul(100).round(1).to_string())
# bootstrap interval for the change in the negative-group share, before 2024 -> from Aug 2024, per group
rng = np.random.default_rng(0); print("\nchange in negative-group share, before 2024 -> from Aug 2024 (points), 95% bootstrap interval:")
for grp, s in d.groupby("group"):
    a = s[s.per == "before 2024"].negative.values; b = s[s.per == "from Aug 2024"].negative.values
    bs = [rng.choice(b, len(b)).mean() - rng.choice(a, len(a)).mean() for _ in range(500)]
    print(f"  {grp:<26} {100 * (b.mean() - a.mean()):+.1f} [{100 * np.percentile(bs, 2.5):+.1f}, {100 * np.percentile(bs, 97.5):+.1f}]  (n {len(a):,} -> {len(b):,})")
# quarterly negative-group share by topic group
d["q"] = d.t.dt.to_period("Q").dt.start_time
plt.rcParams.update({"font.size": 7, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})
C = {"Politics": "#b5482a", "Vaccines and distrust": "#6a4c93", "Other nine-theme topics": "#2a6f97", "Outside the nine themes": "#7a8794"}
fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.5), constrained_layout=True)
for grp, c in C.items():
    s = d[(d.group == grp) & (d.t >= "2021-07-01")]
    q = s.groupby("q").agg(neg=("negative", "mean"), flag=("flag", "mean"), n=("id", "size")); q = q[q.n >= 100]
    ax[0].plot(q.index, q.neg, color=c, lw=1.4, label=grp); ax[1].plot(q.index, q.flag, color=c, lw=1.4)
ax[0].set_ylabel("Negative-group share of documents (quarterly)"); ax[1].set_ylabel("Disapproving-tone flag share (quarterly)")
for a, lab in zip(ax, "AB"):
    a.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0)); a.xaxis.set_major_locator(mdates.YearLocator()); a.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    for dt in ("2024-01-01", "2024-08-01"): a.axvline(pd.Timestamp(dt), color="0.45", ls=":", lw=0.8)
    a.text(-0.02, 1.05, lab, transform=a.transAxes, fontweight="bold", fontsize=8)
ax[0].legend(frameon=False, fontsize=6, loc="upper left")
fig.savefig("paper/figures/emotion_groups_by_theme.pdf"); fig.savefig("seedoils/figures/emotion_groups_by_theme.png", dpi=200)
