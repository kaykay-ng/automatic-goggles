"""Score the hand check of the GoEmotions groups (emotion_label_page.html). Input: the CSV downloaded from the page (id,neg,pos,amb,neutral,note; default seedoils/data/processed/emotion_label_answers.csv) and the key/population files written by emotion_label_sample.py.
Population weights: each sampled comment stands for (documents in its stratum and period) / (comments sampled there), so results describe the whole corpus. For each group (negative, positive, ambiguous): model prevalence, human prevalence, precision (human ticked it when the model flagged it), recall (model flagged it when the human ticked it), Cohen's kappa; overall and by period; 95% intervals by resampling comments within strata (1,000 draws). Also the share of comments where the human ticked 2+ groups against the model's share.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/emotion_label_score.py [answers.csv]"""
import json, sys
import numpy as np, pandas as pd
Rp = "seedoils/data/processed_rebuild_prob/"; ans = sys.argv[1] if len(sys.argv) > 1 else "seedoils/data/processed/emotion_label_answers.csv"
K = pd.read_csv(Rp + "emotion_label_key.csv").rename(columns={"neg": "m_neg", "pos": "m_pos", "amb": "m_amb"}); A = pd.read_csv(ans); pop = json.load(open(Rp + "emotion_label_population.json")); D = K.merge(A, on="id")  # key columns = what the model flagged; answer columns = what the reader ticked
for c in ("m_neg", "m_pos", "m_amb"): D[c] = D[c].astype(int)
print(f"{len(D)} answers read of {len(K)}"); n_s = D.groupby(["stratum", "period"]).id.transform("size"); D["w"] = [pop[f"{s}|{p}"] for s, p in zip(D.stratum, D.period)] / n_s
G = {"negative": ("m_neg", "neg"), "positive": ("m_pos", "pos"), "ambiguous": ("m_amb", "amb")}
def metrics(d):
    out = {}
    for k, (mc, hc) in G.items():
        m, h, w = d[mc].values.astype(float), d[hc].values.astype(float), d.w.values; tp = (w * m * h).sum(); out[k] = {"model_%": 100 * (w * m).sum() / w.sum(), "human_%": 100 * (w * h).sum() / w.sum(), "precision": tp / max((w * m).sum(), 1e-9), "recall": tp / max((w * h).sum(), 1e-9)}
        po = ((w * (m == h)).sum()) / w.sum(); pm, ph = (w * m).sum() / w.sum(), (w * h).sum() / w.sum(); pe = pm * ph + (1 - pm) * (1 - ph); out[k]["kappa"] = (po - pe) / (1 - pe) if pe < 1 else np.nan
    mm = (d[["m_neg", "m_pos", "m_amb"]].sum(1) >= 2).values; hh = (d[["neg", "pos", "amb"]].sum(1) >= 2).values; out["two_or_more_groups"] = {"model_%": 100 * (d.w * mm).sum() / d.w.sum(), "human_%": 100 * (d.w * hh).sum() / d.w.sum()}
    return out
def table(d, label):
    r = metrics(d); rng = np.random.default_rng(0); bs = []
    for _ in range(1000): bs.append(metrics(d.groupby(["stratum", "period"], group_keys=False).apply(lambda x: x.sample(len(x), replace=True, random_state=int(rng.integers(1e9))))))
    print(f"\n=== {label} (n={len(d)})"); print(f"{'group':<11}{'model %':>8}{'human %':>9}{'precision':>16}{'recall':>16}{'kappa':>16}")
    for k in G:
        f = lambda key: (r[k][key], np.nanpercentile([b[k][key] for b in bs], 2.5), np.nanpercentile([b[k][key] for b in bs], 97.5))
        p, rc, ka = f("precision"), f("recall"), f("kappa"); print(f"{k:<11}{r[k]['model_%']:>8.1f}{r[k]['human_%']:>9.1f}{p[0]:>8.2f} [{p[1]:.2f},{p[2]:.2f}]{rc[0]:>6.2f} [{rc[1]:.2f},{rc[2]:.2f}]{ka[0]:>6.2f} [{ka[1]:.2f},{ka[2]:.2f}]")
    t = r["two_or_more_groups"]; print(f"two or more groups: model {t['model_%']:.1f}% vs human {t['human_%']:.1f}% of comments")
    print(f"neutral/none: human ticked 'neutral or none' for {100 * (d.w * d.neutral).sum() / d.w.sum():.1f}% of comments; the model has no group at >= 0.5 for {100 * (d.w * (d[['m_neg', 'm_pos', 'm_amb']].sum(1) == 0)).sum() / d.w.sum():.1f}%")
table(D, "all comments")
for p in ("before 2024", "from Aug 2024"): table(D[D.period == p], p)
