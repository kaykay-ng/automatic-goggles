"""Two-labeller hand check of the GoEmotions groups (27 Nov). Z.W.N. (emotion_label_answers.csv) and H.-Y.C. (emotion_label_answers_HC.csv) labelled
the same 130 comments blind and independently (emotion_label_page_second.py). The sample key and population counts (emotion_label_sample.py writes
them on Kaykay's machine only) are rebuilt here from the local scores: stratum = what the model flags at score >= 0.5 (negative only, positive only,
ambiguous only, none, mixed = 2+ groups), period = before 2024 / from Aug 2024 (the periods the sample was drawn from). Weights as in
emotion_label_score.py: documents in the stratum and period / comments sampled there, so results describe the whole corpus.
Reported per group: (1) agreement between the two labellers (raw agreement, Cohen's kappa; unweighted on the 130 and population-weighted);
(2) model vs each labeller and vs the consensus (a group counts when BOTH ticked it; also 'either'): model and human prevalence, precision, recall,
kappa, with 95% intervals from resampling comments within strata (1,000 draws).
Output: data/processed/emotion_label_score_two.json. Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/emotion_label_score_two.py"""
import json
from pathlib import Path
import numpy as np, pandas as pd

P = Path("seedoils/data/processed")
LAB = list(pd.read_csv(P / "goemo_monthly.csv", nrows=1).columns[1:29])
GR = {"neg": "anger annoyance disappointment disapproval disgust embarrassment fear grief nervousness remorse sadness".split(),
      "pos": "admiration amusement approval caring desire excitement gratitude joy love optimism pride relief".split(), "amb": "confusion curiosity realization surprise".split()}
NAME = {"neg": "negative", "pos": "positive", "amb": "ambiguous"}
g = np.load(P / "goemo_seso.npz", allow_pickle=True); pr = g["p"].astype(np.float32)
M = pd.DataFrame({"id": g["id"].astype(str)})
for k, ls in GR.items(): M["m_" + k] = (pr[:, [LAB.index(l) for l in ls]] >= 0.5).any(1).astype(int)
T = pd.read_csv(P / "seso_doc_topics.csv.gz", usecols=["id", "created_utc"]); T["id"] = T.id.astype(str); M = M.merge(T, on="id"); t = pd.to_datetime(M.created_utc, unit="s")
M["period"] = np.where(t < "2024-01-01", "before 2024", np.where(t >= "2024-08-01", "from Aug 2024", "skip")); ng = M[["m_neg", "m_pos", "m_amb"]].sum(1)
M["stratum"] = np.select([ng >= 2, (ng == 1) & (M.m_neg == 1), (ng == 1) & (M.m_pos == 1), (ng == 1) & (M.m_amb == 1), ng == 0], ["mixed", "negative", "positive", "ambiguous", "none"], "x")
pop = M[M.period != "skip"].groupby(["stratum", "period"]).size()
A = pd.read_csv(P / "emotion_label_answers.csv"); B = pd.read_csv(P / "emotion_label_answers_HC.csv")
for d in (A, B): d["id"] = d.id.astype(str)
D = M.merge(A[["id", "neg", "pos", "amb", "neutral"]].add_prefix("k_").rename(columns={"k_id": "id"}), on="id").merge(B[["id", "neg", "pos", "amb", "neutral"]].add_prefix("h_").rename(columns={"h_id": "id"}), on="id")
assert len(D) == 130 and (D.period != "skip").all(), len(D)
print("sample per stratum/period:", D.groupby(["stratum", "period"]).size().to_dict())
D["w"] = [pop[(s, p)] for s, p in zip(D.stratum, D.period)] / D.groupby(["stratum", "period"]).id.transform("size")
for k in GR: D["both_" + k] = D["k_" + k] * D["h_" + k]; D["either_" + k] = ((D["k_" + k] + D["h_" + k]) > 0).astype(int)


def kappa(a, b, w):
    po = (w * (a == b)).sum() / w.sum(); pa, pb = (w * a).sum() / w.sum(), (w * b).sum() / w.sum(); pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else np.nan


def metrics(d, human):
    out = {}
    for k in GR:
        m, h, w = d["m_" + k].values.astype(float), d[f"{human}_{k}"].values.astype(float), d.w.values; tp = (w * m * h).sum()
        out[k] = {"model_pct": 100 * (w * m).sum() / w.sum(), "human_pct": 100 * (w * h).sum() / w.sum(), "precision": tp / max((w * m).sum(), 1e-9),
                  "recall": tp / max((w * h).sum(), 1e-9), "kappa": kappa(m, h, w)}
    return out


def inter(d):
    out = {}
    for k in GR:
        a, b = d["k_" + k].values, d["h_" + k].values; one = np.ones(len(d))
        out[k] = {"agree_pct": 100 * (a == b).mean(), "kappa": kappa(a, b, one), "agree_pct_weighted": 100 * (d.w * (a == b)).sum() / d.w.sum(), "kappa_weighted": kappa(a, b, d.w.values),
                  "zwn_pct_weighted": 100 * (d.w * a).sum() / d.w.sum(), "hyc_pct_weighted": 100 * (d.w * b).sum() / d.w.sum()}
    a, b = d.k_neutral.values, d.h_neutral.values; out["neutral_or_none"] = {"agree_pct": 100 * (a == b).mean(), "kappa": kappa(a, b, np.ones(len(d)))}
    return out


rng = np.random.default_rng(0); idx = D.groupby(["stratum", "period"]).indices
boots = [D.iloc[np.concatenate([rng.choice(v, len(v)) for v in idx.values()])] for _ in range(1000)]
res = {"n": len(D), "between_labellers": inter(D), "model_vs": {}}
bi = [inter(b) for b in boots]
for k in GR:
    for key in ("kappa", "kappa_weighted"):
        res["between_labellers"][k][key + "_ci"] = list(np.nanpercentile([x[k][key] for x in bi], [2.5, 97.5]))
for human, label in (("k", "Z.W.N."), ("h", "H.-Y.C."), ("both", "consensus (both ticked)"), ("either", "either ticked")):
    r = metrics(D, human); bm = [metrics(b, human) for b in boots]
    for k in GR:
        for key in ("precision", "recall", "kappa"):
            r[k][key + "_ci"] = list(np.nanpercentile([x[k][key] for x in bm], [2.5, 97.5]))
    res["model_vs"][label] = r
rnd = lambda o: {k: rnd(v) for k, v in o.items()} if isinstance(o, dict) else ([round(float(x), 3) for x in o] if isinstance(o, list) else round(float(o), 3))
res = rnd(res); (P / "emotion_label_score_two.json").write_text(json.dumps(res, indent=1))
print("\nBETWEEN LABELLERS (130 comments; weighted = population weights)")
for k, v in res["between_labellers"].items():
    print(f"  {NAME.get(k, k):16s} agree {v['agree_pct']:5.1f}%  kappa {v['kappa']:.2f}" + (f" [{v['kappa_ci'][0]:.2f},{v['kappa_ci'][1]:.2f}]  weighted agree {v['agree_pct_weighted']:.1f}% kappa {v['kappa_weighted']:.2f} [{v['kappa_weighted_ci'][0]:.2f},{v['kappa_weighted_ci'][1]:.2f}]  prevalence ZWN {v['zwn_pct_weighted']:.1f}% HYC {v['hyc_pct_weighted']:.1f}%" if k in GR else ""))
for label, r in res["model_vs"].items():
    print(f"\nMODEL vs {label}  (population-weighted)")
    for k in GR:
        v = r[k]; print(f"  {NAME[k]:10s} model {v['model_pct']:5.1f}%  human {v['human_pct']:5.1f}%  precision {v['precision']:.2f} [{v['precision_ci'][0]:.2f},{v['precision_ci'][1]:.2f}]  recall {v['recall']:.2f} [{v['recall_ci'][0]:.2f},{v['recall_ci'][1]:.2f}]  kappa {v['kappa']:.2f} [{v['kappa_ci'][0]:.2f},{v['kappa_ci'][1]:.2f}]")
