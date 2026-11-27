"""Where do the emotion changes sit? Decomposition of the change in the share of ALL documents with a negative (or positive) GoEmotions group, before 2024 -> from Aug 2024, by BERTopic theme (themes_full_v3.json, outlier rule 0.05); documents without a confident topic form their own group 'Unassigned' so the whole corpus (149,815 documents) is covered.
Group of a document = at least one emotion of the group scored >= 0.5 (negative: anger annoyance disappointment disapproval disgust embarrassment fear grief nervousness remorse sadness; positive: admiration amusement approval caring desire excitement gratitude joy love optimism pride relief).
Overall change = sum over groups k of  within_k + mix_k  (midpoint decomposition):  within_k = mean share of docs in k x (rate_post_k - rate_pre_k);  mix_k = (share_post_k - share_pre_k) x (mean rate_k - overall mean rate) (centred, so a theme only raises the overall share by growing if its rate is above average, or by shrinking if it is below average; the centring does not change the total). 'within' = documents of that theme became more/less emotional; 'mix' = the theme grew/shrank.
95% intervals: resampling THREADS (1,000 draws). Outputs: seedoils/data/processed/emotion_theme_decomposition_{negative,positive}.csv, seedoils/figures/emotion_theme_decomposition.png.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/emotion_by_theme_decomposition.py"""
import gzip, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

R, Rp, P = "seedoils/data/processed_rebuild/", "seedoils/data/processed_rebuild_prob/", "seedoils/data/processed/"
labs = list(pd.read_csv(P + "goemo_monthly.csv", nrows=1).columns[1:29]); g = np.load(R + "goemo_seso.npz", allow_pickle=True); pr = g["p"].astype(np.float32); ids = g["id"]
G = {"negative": "anger annoyance disappointment disapproval disgust embarrassment fear grief nervousness remorse sadness".split(), "positive": "admiration amusement approval caring desire excitement gratitude joy love optimism pride relief".split()}
A = pd.read_csv(Rp + "seso_doc_topics_prob005_v3.csv.gz").set_index("id").loc[ids].reset_index(); A["t"] = pd.to_datetime(A.created_utc, unit="s")
L = {}
for x in map(json.loads, gzip.open("seedoils/data/raw_haoyu/StopEatingSeedOils_comments.jsonl.gz", "rt")): L[x["id"]] = x["link_id"][3:]
A["thread"] = A.id.map(lambda i: L.get(i, i)); A["theme"] = A.theme.fillna("Unassigned (no confident topic)")
keep = ((A.t < "2024-01-01") | (A.t >= "2024-08-01")).values; A = A[keep].reset_index(drop=True); pre = (A.t < "2024-01-01").values; pr = pr[keep]
names = sorted(A.theme.unique()); K = len(names); th = A.theme.map({n: i for i, n in enumerate(names)}).values; tix = A.thread.astype("category").cat.codes.values; nT = tix.max() + 1
short = lambda s: s.split(" (")[0].replace("Distrust of industry, medicine and media", "Distrust of industry & media").replace("Ingredient labels and processed food", "Ingredient labels").replace("Omega-6 / PUFA biochemistry", "Omega-6 / PUFA").replace("Keto, carbs, fasting", "Keto, carbs, fasting")
print(f"documents: before 2024 {pre.sum():,}; from Aug 2024 {(~pre).sum():,} (Jan-Jul 2024 left out)")
def stats(flag):
    def agg(sel):  # per theme x thread: n and flagged counts
        n = np.zeros((K, nT)); f = np.zeros((K, nT)); np.add.at(n, (th[sel], tix[sel]), 1); np.add.at(f, (th[sel], tix[sel]), flag[sel]); return n, f
    return agg(pre), agg(~pre)
def decomp(npre, fpre, npost, fpost):
    Npre, Npost = npre.sum(), npost.sum(); wpre, wpost = npre.sum(1) / Npre, npost.sum(1) / Npost; rpre = fpre.sum(1) / np.maximum(npre.sum(1), 1); rpost = fpost.sum(1) / np.maximum(npost.sum(1), 1)
    Rbar = 0.5 * (fpre.sum() / Npre + fpost.sum() / Npost); within = 0.5 * (wpre + wpost) * (rpost - rpre); mix = (wpost - wpre) * (0.5 * (rpre + rpost) - Rbar); return 100 * within, 100 * mix, 100 * rpre, 100 * rpost, 100 * wpre, 100 * wpost
rng = np.random.default_rng(0); out = {}
for grp, ls in G.items():
    flag = (pr[:, [labs.index(l) for l in ls]] >= 0.5).any(1).astype(float); (npre, fpre), (npost, fpost) = stats(flag)
    w, m, rpre, rpost, wpre, wpost = decomp(npre, fpre, npost, fpost); tot = (w + m)
    bs = np.zeros((1000, K, 2))
    for b in range(1000):
        p = rng.integers(0, nT, nT); ww, mm, *_ = decomp(npre[:, p], fpre[:, p], npost[:, p], fpost[:, p]); bs[b, :, 0] = ww; bs[b, :, 1] = mm
    D = pd.DataFrame({"theme": names, "share_docs_before_%": wpre.round(1), "share_docs_from_Aug24_%": wpost.round(1), "rate_before_%": rpre.round(1), "rate_from_Aug24_%": rpost.round(1), "within": w.round(2), "within_lo": np.percentile(bs[:, :, 0], 2.5, axis=0).round(2), "within_hi": np.percentile(bs[:, :, 0], 97.5, axis=0).round(2), "mix": m.round(2), "total": tot.round(2)})
    D["total_lo"] = np.percentile(bs.sum(2), 2.5, axis=0).round(2); D["total_hi"] = np.percentile(bs.sum(2), 97.5, axis=0).round(2); out[grp] = D; D.to_csv(P + f"emotion_theme_decomposition_{grp}.csv", index=False)
    print(f"\n=== {grp} group: overall share of ALL documents {100 * fpre.sum() / npre.sum():.1f}% -> {100 * fpost.sum() / npost.sum():.1f}% (change {tot.sum():+.2f} points = within {w.sum():+.2f} + mix {m.sum():+.2f})")
    pd.set_option("display.width", 250); print(D.assign(theme=D.theme.map(short)).sort_values("total", ascending=False)[["theme", "share_docs_before_%", "share_docs_from_Aug24_%", "rate_before_%", "rate_from_Aug24_%", "within", "mix", "total", "total_lo", "total_hi"]].to_string(index=False))
plt.rcParams.update({"font.size": 7, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 2, figsize=(7.4, 3.4), sharey=True, constrained_layout=True)
order = out["negative"].assign(n=lambda d: d.theme.map(short)).sort_values("total").theme.tolist()
for a, grp, col in zip(ax, ("negative", "positive"), ("#b5482a", "#2a7f62")):
    D = out[grp].set_index("theme").loc[order]; y = np.arange(len(D))
    a.barh(y, D.within, color=col, label="within theme (rate changed)", height=0.7); a.barh(y, D.mix, left=np.where(D.mix * D.within > 0, D.within, 0), color=col, alpha=0.4, label="mix (theme grew or shrank)", height=0.7)
    a.errorbar(D.total, y, xerr=[D.total - D.total_lo, D.total_hi - D.total], fmt="o", color="k", ms=2.5, lw=0.8, label="total, 95% interval")
    a.axvline(0, color="0.4", lw=0.8); a.set_xlabel(f"Contribution to change in {grp} share (points)"); a.set_title(grp.capitalize(), loc="left", fontsize=8, color=col, fontweight="bold")
ax[0].set_yticks(range(len(order))); ax[0].set_yticklabels([short(o) for o in order]); ax[1].legend(frameon=False, fontsize=5.8, loc="lower right")
fig.savefig("seedoils/figures/emotion_theme_decomposition.png", dpi=200)
