"""How well does the GoEmotions 'hostile' flag match hand labels? Reads every data/processed/hostility_labels_<initials>.csv (from label_hostility.html)
and hostility_sample_key.csv (item -> comment id, score band), and the GoEmotions scores (goemo_seso.npz).
Labels: H hostile toward a person or group, C critical but civil, N neither, U can't tell (U items are left out).
Reported:
  per labeller: label counts, and the share of H (and of H or C) in each model-score band (does the hand label rise with the score?);
  agreement between labellers when there are two or more files: percent agreement and Cohen's kappa (H/C/N), and on H vs not-H;
  the model against the hand labels (consensus where labellers agree; with one labeller, that labeller): precision, recall and F1 of the page's
  flag (max of anger/annoyance/disapproval/disgust >= 0.5) and of the alternatives in hostility_robustness.py, for 'hostile' = H (strict) and
  = H or C (lenient). The sample has 30 comments per score band, not a random sample, so precision and recall are also re-weighted by how many
  r/StopEatingSeedOils documents (15+ words) fall in each band ('population-weighted').
Output: data/processed/hostility_eval.json (aggregates only). Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/hostility_eval.py"""
import glob
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

P = Path("seedoils/data/processed")
BANDS = [(0, .1), (.1, .3), (.3, .5), (.5, .7), (.7, 1.01)]
key = pd.read_csv(P / "hostility_sample_key.csv"); key["id"] = key.id.astype(str)
files = sorted(glob.glob(str(P / "hostility_labels_*.csv")))
if not files:
    raise SystemExit("no hostility_labels_*.csv in data/processed/: export them from seedoils/label_hostility.html first")
labs = {}
for f in files:
    d = pd.read_csv(f, dtype={"label": str}).fillna({"label": ""}); who = Path(f).stem.replace("hostility_labels_", "")
    labs[who] = d.set_index("item").label.str.upper().reindex(key.item).values
z = np.load(P / "goemo_seso.npz", allow_pickle=True); LAB = list(pd.read_csv(P / "goemo_monthly.csv", nrows=1).columns[1:29])
S = pd.DataFrame(z["p"].astype(np.float32), columns=LAB); S["id"] = z["id"].astype(str); S = S.set_index("id")
H4 = ["anger", "annoyance", "disapproval", "disgust"]
allmx = S[H4].max(axis=1).values; band_w = np.histogram(allmx, bins=[b[0] for b in BANDS] + [1.01])[0] / len(allmx)
sc = S.reindex(key.id); mx = sc[H4].max(axis=1).values; am = sc[LAB].values.argmax(1)
defs = {"page: max of 4 >= 0.5": mx >= .5, "threshold 0.3": mx >= .3, "threshold 0.7": mx >= .7,
        "anger or disgust >= 0.5": np.maximum(sc.anger.values, sc.disgust.values) >= .5, "disapproval only >= 0.5": sc.disapproval.values >= .5,
        "argmax is one of the four": np.isin(np.array(LAB)[am], H4)}
band = np.array([next(k for k, (lo, hi) in enumerate(BANDS) if lo <= v < hi) for v in mx])
out = {"labellers": list(labs), "n_items": int(len(key)), "per_labeller": {}}
for who, l in labs.items():
    ok = np.isin(l, ["H", "C", "N"])
    out["per_labeller"][who] = {"counts": {k: int((l == k).sum()) for k in ("H", "C", "N", "U", "")},
                                "by_band": [{"band": f"{lo}-{min(hi, 1):.1f}", "n": int((ok & (band == k)).sum()), "H_pct": round(float((l[ok & (band == k)] == "H").mean() * 100), 1) if (ok & (band == k)).any() else None,
                                             "H_or_C_pct": round(float(np.isin(l[ok & (band == k)], ["H", "C"]).mean() * 100), 1) if (ok & (band == k)).any() else None} for k, (lo, hi) in enumerate(BANDS)]}
if len(labs) >= 2:
    out["agreement"] = []
    for a, b in itertools.combinations(labs, 2):
        ok = np.isin(labs[a], ["H", "C", "N"]) & np.isin(labs[b], ["H", "C", "N"])
        out["agreement"].append({"pair": f"{a}-{b}", "n": int(ok.sum()), "percent": round(float((labs[a][ok] == labs[b][ok]).mean() * 100), 1),
                                 "kappa_HCN": round(float(cohen_kappa_score(labs[a][ok], labs[b][ok])), 3),
                                 "kappa_H_vs_rest": round(float(cohen_kappa_score(labs[a][ok] == "H", labs[b][ok] == "H")), 3)})
L = np.array(list(labs.values())); valid = np.isin(L, ["H", "C", "N"]).all(0)
# reference per target: a comment counts when every labeller gave H/C/N and they agree on the yes/no question being tested (H vs not; H or C vs N)
TARGETS = {"strict: H": ["H"], "lenient: H or C": ["H", "C"]}
REF = {}
for t, pos in TARGETS.items():
    yes = np.isin(L, pos); agree = valid & (yes == yes[0]).all(0); REF[t] = (agree, yes[0])
out["reference"] = {t: int(a.sum()) for t, (a, _) in REF.items()} | {"rule": "labellers agree on the yes/no question" if len(labs) > 1 else "single labeller"}
if len(labs) >= 2:
    for d in out["agreement"]:
        a, b = d["pair"].split("-"); okp = np.isin(labs[a], ["H", "C", "N"]) & np.isin(labs[b], ["H", "C", "N"])
        d["kappa_HorC_vs_N"] = round(float(cohen_kappa_score(np.isin(labs[a][okp], ["H", "C"]), np.isin(labs[b][okp], ["H", "C"]))), 3)
        d["crosstab"] = pd.crosstab(pd.Series(labs[a], name=a), pd.Series(labs[b], name=b)).to_dict()
def scores(pred, truth, w=None):
    w = np.ones(len(truth)) if w is None else w
    tp, fp, fn = (w * (pred & truth)).sum(), (w * (pred & ~truth)).sum(), (w * (~pred & truth)).sum()
    pr = tp / (tp + fp) if tp + fp else float("nan"); rc = tp / (tp + fn) if tp + fn else float("nan")
    return {"precision": round(float(pr), 3), "recall": round(float(rc), 3), "f1": round(float(2 * pr * rc / (pr + rc)), 3) if pr + rc else None}
wt = band_w[band] / np.bincount(band, minlength=5)[band]  # each band's comments stand for its share of all documents
out["model_vs_hand"] = []
for nm, pred in defs.items():
    for target, (ok, truth) in REF.items():
        out["model_vs_hand"].append({"definition": nm, "hostile_means": target, "flagged_in_sample": int(pred[ok].sum()), "items": int(ok.sum()),
                                     "sample": scores(pred[ok], truth[ok]), "population_weighted": scores(pred[ok], truth[ok], wt[ok])})
out["band_population_share"] = [round(float(x), 4) for x in band_w]
# whole-subreddit share of hand-labelled H (and H or C): band shares weighted by how many documents fall in each band; 2,000 bootstraps within bands
# each comment's value = share of labellers (with a H/C/N label) who said yes, so disagreements count as half with two labellers
rng = np.random.default_rng(0); est = {}
for nm, pos in (("H", ["H"]), ("H_or_C", ["H", "C"])):
    v = np.isin(L, ["H", "C", "N"]); t = np.where(v.any(0), (np.isin(L, pos) & v).sum(0) / np.maximum(v.sum(0), 1), np.nan); okv = v.any(0)
    idx = [np.where(okv & (band == k))[0] for k in range(5)]
    pt = sum(band_w[k] * t[idx[k]].mean() for k in range(5))
    bs = [sum(band_w[k] * t[rng.choice(idx[k], len(idx[k]))].mean() for k in range(5)) for _ in range(2000)]
    est[nm] = {"pct": round(float(pt * 100), 1), "ci95": [round(float(np.percentile(bs, 2.5) * 100), 1), round(float(np.percentile(bs, 97.5) * 100), 1)]}
est["flagged_by_page_definition_pct"] = round(float((allmx >= .5).mean() * 100), 1)
out["population_estimate"] = est
(P / "hostility_eval.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k != "model_vs_hand"}, indent=1))
print(pd.DataFrame([{"definition": r["definition"], "hostile =": r["hostile_means"], **{f"{k} (sample)": v for k, v in r["sample"].items()},
                     **{f"{k} (weighted)": v for k, v in r["population_weighted"].items()}} for r in out["model_vs_hand"]]).to_string(index=False))
