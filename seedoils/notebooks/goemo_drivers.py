"""What drives the 2024 shifts in GoEmotions hostile / inquisitive shares (all comments + self-posts, long and short).
1 label composition; 2 mix shift (length bucket, post vs comment) vs within-group change; 3 old vs new commenters (same people before/after vs newcomers);
4 bootstrap over commenters for the change. Cutoff 2024-01-01; threshold 0.5 as in emotions.py GROUPS. Output: data/processed/goemo_drivers.json + printed tables (no text).
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/goemo_drivers.py"""
from seedoil_common import is_bot, not_bot, SPLIT_TS# shared bot rule: AutoModerator + names ending in 'bot'
import json
from pathlib import Path
import numpy as np, pandas as pd
PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
LAB = [c for c in pd.read_csv(PROC / "goemo_monthly.csv", nrows=1).columns[1:29]]
H = ["anger", "annoyance", "disapproval", "disgust"]; Q = ["curiosity", "confusion"]
CUT = SPLIT_TS; rng = np.random.default_rng(0); out = {}
def load(pfx):
    Ds, Ps = [], []
    for part in ("",):  # 15+ words only (decision 22 Nov)
        D = pd.read_csv(PROC / f"{pfx}{part}_docs.csv.gz", usecols=["id", "kind", "author", "created_utc", "text"], keep_default_na=False)
        z = np.load(PROC / f"goemo_{pfx}{part}.npz", allow_pickle=True); assert (z["id"].astype(str) == D.id.astype(str).values).all()
        Ds.append(D); Ps.append(z["p"].astype(np.float32))
    D = pd.concat(Ds, ignore_index=True); P = np.concatenate(Ps); L = pd.DataFrame(P, columns=LAB)
    D["post"] = D.created_utc >= CUT; D["hostile"] = (L[H].max(axis=1) >= .5).values; D["inq"] = (L[Q].max(axis=1) >= .5).values
    for l in H + Q: D[l] = (L[l] >= .5).values
    D["words"] = D.text.astype(str).str.split().str.len(); D["bucket"] = pd.cut(D.words, [0, 7, 14, 39, 10**6], labels=["1-7", "8-14", "15-39", "40+"])
    return D
for sub, pfx in (("r/StopEatingSeedOils", "seso"), ("r/ScientificNutrition", "scinut")):
    D = load(pfx); o = out[sub] = {}; pre, post = D[~D.post], D[D.post]
    print("\n=====", sub, "n pre", len(pre), "n post", len(post))
    o["labels"] = {l: [round(pre[l].mean() * 100, 2), round(post[l].mean() * 100, 2)] for l in H + Q}; print("1 labels (pre, post %):", o["labels"])
    for g in ("hostile", "inq"):
        r = D.groupby(["bucket", "post"], observed=True)[g].agg(["mean", "size"]).unstack()
        mixpre = pre.bucket.value_counts(normalize=True); mixpost = post.bucket.value_counts(normalize=True)
        rpre, rpost = r["mean"][False], r["mean"][True]
        actual = post[g].mean() - pre[g].mean(); within = (mixpre * (rpost - rpre)).sum(); mix = ((mixpost - mixpre) * rpost).sum()
        o["mix_" + g] = {"actual_pts": round(actual * 100, 2), "within_bucket_pts": round(within * 100, 2), "mix_shift_pts": round(mix * 100, 2),
                         "bucket_share_pre": mixpre.round(3).to_dict(), "bucket_share_post": mixpost.round(3).to_dict(), "bucket_rate_pre": (rpre * 100).round(2).to_dict(), "bucket_rate_post": (rpost * 100).round(2).to_dict()}
        print("2", g, {k: v for k, v in o["mix_" + g].items() if "pts" in k}); print(r["mean"].mul(100).round(1).T.to_string())
    k = D.groupby("kind")[["hostile", "inq"]].mean().mul(100).round(1); print("kind rates", k.to_dict()); print("post share by period", D.groupby("post").kind.value_counts(normalize=True).round(3).to_dict())
    A = D[(~D.author.isin(["[deleted]", "AutoModerator"]) & not_bot(D.author))]; first = A.groupby("author").created_utc.min(); A = A.assign(new=A.author.map(first) >= CUT)
    old_pre, old_post, new_post = A[(~A.new) & (~A.post)], A[(~A.new) & A.post], A[A.new & A.post]
    o["cohort"] = {g: {"old_before": round(old_pre[g].mean() * 100, 2), "old_from2024": round(old_post[g].mean() * 100, 2), "new_from2024": round(new_post[g].mean() * 100, 2)} for g in ("hostile", "inq")}
    o["cohort"]["n_docs"] = {"old_before": len(old_pre), "old_from2024": len(old_post), "new_from2024": len(new_post)}
    o["cohort"]["share_of_post_docs_by_new"] = round(len(new_post) / len(A[A.post]), 3); print("3 cohort", o["cohort"])
    # 4 bootstrap over commenters (cluster) of the pre->post change, all docs with a real author
    g_ = A.groupby("author"); idx = {a: v for a, v in g_.indices.items()}; auth = np.array(list(idx)); post_arr = A.post.values
    cnt = {g: np.array([[A[g].values[v][~post_arr[v]].sum(), (~post_arr[v]).sum(), A[g].values[v][post_arr[v]].sum(), post_arr[v].sum()] for v in idx.values()]) for g in ("hostile", "inq")}
    for g in ("hostile", "inq"):
        c = cnt[g]; d = []
        for _ in range(500):
            s = c[rng.integers(0, len(c), len(c))].sum(axis=0); d.append((s[2] / s[3] - s[0] / s[1]) * 100)
        o["boot_" + g] = {"change_pts": round((c[:, 2].sum() / c[:, 3].sum() - c[:, 0].sum() / c[:, 1].sum()) * 100, 2), "ci95": [round(float(np.percentile(d, 2.5)), 2), round(float(np.percentile(d, 97.5)), 2)]}
        print("4", g, o["boot_" + g])
(PROC / "goemo_drivers.json").write_text(json.dumps(out, indent=1))
