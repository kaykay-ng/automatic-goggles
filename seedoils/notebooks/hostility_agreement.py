"""How well does the GoEmotions 'hostile' flag (max of anger, annoyance, disapproval, disgust >= 0.5) match what a person reads? Uses the hand labels from label_hostility.html.
Inputs: data/processed/hostility_labels_<coder>.csv (item, label in hostile / complaint / neither / unsure, notes), one or two coders; hostility_sample_key.csv (item, comment id, score band).
Sample design: 30 comments from each of five score bands (0-0.1, 0.1-0.3, 0.3-0.5, 0.5-0.7, 0.7-1) of the model's score, drawn from the 106,783 topic-model comments of the 2,618 network members.
Because bands are not equally common, precision and recall are WEIGHTED by each band's real share of those comments (bootstrap 95% intervals over the sampled comments).
Two readings of the human label: strict = 'hostile toward a person or group'; broad = 'hostile' or 'disagreement or complaint'. 'Cannot tell' items are left out and counted.
With two coders: Cohen's kappa between them (3 classes and strict/not) and the results are shown for each coder separately and for the consensus (items where they agree).
Run from final_project/ with the NLP env, after labelling:  ./.venv-nlp/bin/python seedoils/notebooks/hostility_agreement.py [--key hostility_sample_key_rerun_matched.csv] [--demo]
--key: item -> comment id file for the sample that was labelled (default: the 21 Nov sample). The rerun sample's file was rebuilt by matching its texts to our documents (all 150 found, 30 per band); band shares of the frame differ by under 1 point between all comments and the network members' comments.
Labels: hostile/H, complaint/C, neither/N, unsure/U.   (--demo: simulated labels, to test the script only)"""
import csv
import glob
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

P = Path("seedoils/data/processed"); rng = np.random.default_rng(5); DEMO = "--demo" in sys.argv
KEYFILE = sys.argv[sys.argv.index("--key") + 1] if "--key" in sys.argv else "hostility_sample_key.csv"
key = pd.read_csv(P / KEYFILE); LABS = list(pd.read_csv(P / "goemo_monthly.csv", nrows=1).columns[1:29]); H4 = [LABS.index(k) for k in ("anger", "annoyance", "disapproval", "disgust")]
z = np.load(P / "goemo_seso.npz", allow_pickle=True); pos = pd.Series(np.arange(len(z["id"])), index=z["id"].astype(str)); sc = z["p"][:, H4].max(1)
key["score"] = sc[pos.reindex(key.id.astype(str)).values.astype(int)]; key["flag"] = key.score >= .5
bands = [(0, .1), (.1, .3), (.3, .5), (.5, .7), (.7, 1.01)]; key["band"] = [next(i for i, (lo, hi) in enumerate(bands) if lo <= s < hi) for s in key.score]
# real band shares in the sampling frame (comments of the 2,618 network members)
raw = {}
with gzip.open(glob.glob("seedoils/data/raw/*StopEatingSeedOils_comments.jsonl.gz")[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); raw[x["id"]] = x["author"]
Dt = pd.read_csv(P / "seso_doc_topics.csv.gz", usecols=["id", "kind"]); Dt = Dt[Dt.kind == "comment"].copy(); Dt["a"] = Dt.id.map(raw); Dt = Dt[Dt.a.notna() & ~Dt.a.isin(["[deleted]", "AutoModerator"])]
nd = Dt.groupby("a").size(); Dt = Dt[Dt.a.isin(set(nd[nd >= 10].index))]; s_all = sc[pos.reindex(Dt.id.astype(str)).values.astype(int)]
wb = np.array([np.mean((s_all >= lo) & (s_all < hi)) for lo, hi in bands]); print("share of comments in each score band (frame):", np.round(wb * 100, 1).tolist(), "| flagged by the page's definition:", f"{wb[3] + wb[4]:.1%}")
files = sorted(glob.glob(str(P / "hostility_labels_*.csv")))
if DEMO:
    p = {"hostile": [0, 0, .05, .25, .6], "complaint": [.05, .15, .4, .5, .3]}; fake = []
    for b in key.band: u = rng.random(); fake.append("hostile" if u < p["hostile"][b] else ("complaint" if u < p["hostile"][b] + p["complaint"][b] else "neither"))
    DF = {"demo": pd.DataFrame({"item": key.item, "label": fake})}
else:
    CODE = {"H": "hostile", "C": "complaint", "N": "neither", "U": "unsure"}  # the second labelling page uses H/C/N/U
    DF = {}
    for f in files:
        d_ = pd.read_csv(f, keep_default_na=False); d_["label"] = d_.label.astype(str).str.strip().map(lambda v: CODE.get(v.upper(), v.lower())); DF[Path(f).stem.replace("hostility_labels_", "")] = d_
if not DF: sys.exit("no hostility_labels_<coder>.csv found in data/processed")
def table(lab, name):
    d = key.merge(lab[["item", "label"]], on="item"); d = d[d.label.isin(["hostile", "complaint", "neither"])].copy()
    print(f"\n== {name}: {len(d)} labelled items used ({int((~lab.label.isin(['hostile', 'complaint', 'neither'])).sum())} unsure or missing, left out)")
    print("   label share by score band (hostile / complaint / neither, %):")
    for b, (lo, hi) in enumerate(bands):
        s = d[d.band == b]; print(f"     {lo:.1f}-{min(hi, 1):.1f}  n={len(s):>3}  " + "  ".join(f"{(s.label == k).mean() * 100:5.0f}" for k in ("hostile", "complaint", "neither")))
    for reading, pos_set in (("strict (hostile toward a person or group)", {"hostile"}), ("broad (hostile or complaint)", {"hostile", "complaint"})):
        d["y"] = d.label.isin(pos_set); w = d.band.map(dict(enumerate(wb / d.groupby("band").size().reindex(range(5)).values)))
        def stats(dd, ww):
            tp = (ww * (dd.flag & dd.y)).sum(); fp = (ww * (dd.flag & ~dd.y)).sum(); fn = (ww * (~dd.flag & dd.y)).sum(); tn = (ww * (~dd.flag & ~dd.y)).sum()
            pr, rc = tp / (tp + fp), tp / (tp + fn); po = tp + tn; pe = (tp + fp) * (tp + fn) + (fn + tn) * (fp + tn); return pr, rc, 2 * pr * rc / (pr + rc), (po - pe) / (1 - pe)
        base = stats(d, w); groups = [np.where(d.band.values == b)[0] for b in range(5)]; bs = []
        for _ in range(1000):  # stratified bootstrap: resample within each score band so the band weights stay valid
            idx = np.concatenate([rng.choice(g, len(g), replace=True) for g in groups]); dd = d.iloc[idx]
            if dd.y.any(): bs.append(stats(dd, w.iloc[idx]))
        bs = np.array(bs)
        ci = lambda j: f"[{np.nanpercentile(bs[:, j], 2.5):.2f}, {np.nanpercentile(bs[:, j], 97.5):.2f}]"
        print(f"   {reading}: precision {base[0]:.2f} {ci(0)}, recall {base[1]:.2f} {ci(1)}, F1 {base[2]:.2f}, kappa {base[3]:.2f} {ci(3)}  (weighted to real band shares)")
for n, lab in DF.items(): table(lab, n)
if len(DF) >= 2:
    (a, A), (b, B) = list(DF.items())[:2]; m = A.merge(B, on="item", suffixes=("_a", "_b")); m = m[m.label_a.isin(["hostile", "complaint", "neither"]) & m.label_b.isin(["hostile", "complaint", "neither"])]
    def kappa(x, y):
        cats = sorted(set(x) | set(y)); po = np.mean(x == y); pe = sum(np.mean(x == c) * np.mean(y == c) for c in cats); return (po - pe) / (1 - pe) if pe < 1 else 1.0
    print(f"\n== between {a} and {b}: {len(m)} items both labelled; agreement {np.mean(m.label_a == m.label_b):.0%}; Cohen's kappa (3 classes) {kappa(m.label_a.values, m.label_b.values):.2f}; strict hostile or not {kappa((m.label_a == 'hostile').values, (m.label_b == 'hostile').values):.2f}")
    cons = m[m.label_a == m.label_b][["item", "label_a"]].rename(columns={"label_a": "label"}); table(cons, f"consensus of {a} and {b}")
