"""Do GoEmotions and torchMoji agree? (user question 25 Nov). Both scored the same documents (comments and self-posts of 15+ words, 256 tokens):
goemo_<pfx>.npz (28 label probabilities) and deepmoji_tm256_<pfx>.npz (64 emoji probabilities). Matched pairs of measures:
  disapproving tone   GoEmotions max(anger, annoyance, disapproval, disgust)    vs  torchMoji Anger family, and Anger + Skepticism
  positive            GoEmotions max(admiration, approval, gratitude, joy, love, optimism, caring, pride, relief, excitement)  vs  Love + Approval
  amusement           GoEmotions amusement                                       vs  Laughter
  sad                 GoEmotions max(sadness, disappointment, grief, remorse)    vs  Sadness
(emoji families as in deepmoji_chart_data.py). Three levels:
  1. per document: Spearman correlation; of the documents GoEmotions flags (>= 0.5), the share in torchMoji's top 10% for the family (10% = chance).
  2. per theme x period in r/StopEatingSeedOils (hand-picked themes, split at seedoil_common.SPLIT_TS): Spearman across the cells of the GoEmotions
     share flagged and the torchMoji mean family share; and whether the change from before to after the split has the same sign.
  3. per year x subreddit (2019-2025): Spearman across years within each subreddit, same-sign share of year-to-year changes, and the subreddit gap
     (SESO minus SciNut) per year: same sign or not.
Output: data/processed/emotion_model_agreement.json (aggregates only). Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/emotion_model_agreement.py"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).parent))
from seedoil_common import SPLIT_TS, THEMES_FILE  # noqa: E402

P = Path("seedoils/data/processed")
VEND = Path("vendor/torchMoji/data/emoji_codes.json")
CODES = json.load(open(VEND)); NAMES = [CODES[str(i)] for i in range(64)]
FAM = {"Laughter": [":joy:", ":sweat_smile:", ":grin:", ":smile:", ":wink:", ":stuck_out_tongue_winking_eye:", ":skull:"],
       "Love": [":heart_eyes:", ":heart:", ":two_hearts:", ":kissing_heart:", ":hearts:", ":blue_heart:", ":purple_heart:", ":sparkling_heart:", ":blush:"],
       "Approval": [":ok_hand:", ":thumbsup:", ":clap:", ":raised_hands:", ":100:", ":muscle:", ":v:", ":pray:", ":sunglasses:"],
       "Anger": [":rage:", ":angry:", ":punch:", ":imp:", ":triumph:"],
       "Sadness": [":sob:", ":cry:", ":broken_heart:", ":disappointed:", ":pensive:", ":weary:", ":tired_face:", ":persevere:", ":confounded:", ":sweat:"],
       "Skepticism": [":unamused:", ":smirk:", ":expressionless:", ":neutral_face:", ":eyes:", ":information_desk_person:", ":speak_no_evil:", ":no_good:", ":grimacing:", ":confused:"]}
LAB = list(pd.read_csv(P / "goemo_monthly.csv", nrows=1).columns[1:29])
GE = {"disapproving": ["anger", "annoyance", "disapproval", "disgust"],
      "positive": ["admiration", "approval", "gratitude", "joy", "love", "optimism", "caring", "pride", "relief", "excitement"],
      "amusement": ["amusement"], "sad": ["sadness", "disappointment", "grief", "remorse"]}
PAIRS = [("disapproving", ["Anger"]), ("disapproving", ["Anger", "Skepticism"]), ("positive", ["Love", "Approval"]), ("amusement", ["Laughter"]), ("sad", ["Sadness"])]


def load(pfx):
    g = np.load(P / f"goemo_{pfx}.npz", allow_pickle=True); t = np.load(P / f"deepmoji_tm256_{pfx}.npz", allow_pickle=True)
    G = pd.DataFrame({k: g["p"][:, [LAB.index(x) for x in v]].astype(np.float32).max(1) for k, v in GE.items()}); G["id"] = g["id"].astype(str); G["t"] = g["t"]
    T = pd.DataFrame({k: t["p"][:, [i for i, nm in enumerate(NAMES) if nm in v]].astype(np.float32).sum(axis=1) for k, v in FAM.items()}); T["id"] = t["id"].astype(str)
    return G.merge(T, on="id")


out = {"pairs": [f"{a} vs {'+'.join(b)}" for a, b in PAIRS]}
D = {pfx: load(pfx) for pfx in ("seso", "scinut")}
for pfx, d in D.items():
    d["year"] = pd.to_datetime(d.t, unit="s").dt.year
    lvl = []
    for a, fams in PAIRS:
        tm = d[fams].sum(axis=1); flag = d[a] >= .5; top = tm >= tm.quantile(.9)
        lvl.append({"pair": f"{a} vs {'+'.join(fams)}", "spearman": round(float(spearmanr(d[a], tm).statistic), 3), "flagged_by_goemotions": int(flag.sum()),
                    "share_of_flagged_in_torchmoji_top10pct": round(float(top[flag].mean() * 100), 1)})
    out[f"{pfx}_documents"] = {"n": int(len(d)), "pairs": lvl}
# level 2: themes x period (SESO)
th = json.loads((P / THEMES_FILE).read_text()); dt = pd.read_csv(P / "seso_doc_topics.csv.gz", usecols=["id", "topic"]); dt["id"] = dt.id.astype(str)
S = D["seso"].merge(dt, on="id"); S["post"] = S.t >= SPLIT_TS
cells = []
for name, ids in th.items():
    for post, g in S[S.topic.isin(ids)].groupby("post"):
        cells.append({"theme": name, "post": bool(post), "n": int(len(g)), **{f"ge_{a}": float((g[a] >= .5).mean() * 100) for a in GE}, **{f"tm_{f}": float(g[f].mean() * 100) for f in FAM}})
C = pd.DataFrame(cells); lv2 = []
for a, fams in PAIRS:
    tm = C[[f"tm_{f}" for f in fams]].sum(axis=1)
    w = C.assign(tm=tm).pivot(index="theme", columns="post", values=[f"ge_{a}", "tm"])
    dg, dm = w[(f"ge_{a}", True)] - w[(f"ge_{a}", False)], w[("tm", True)] - w[("tm", False)]
    lv2.append({"pair": f"{a} vs {'+'.join(fams)}", "spearman_across_theme_period_cells": round(float(spearmanr(C[f"ge_{a}"], tm).statistic), 3),
                "themes_with_same_direction_of_change": f"{int((np.sign(dg) == np.sign(dm)).sum())} of {len(dg)}",
                "change_by_theme": {t: {"goemotions_pts": round(float(dg[t]), 2), "torchmoji_pts": round(float(dm[t]), 2)} for t in dg.index}})
out["seso_themes"] = lv2
# level 3: years
Y = pd.concat([d.assign(sub=pfx) for pfx, d in D.items()]); Y = Y[(Y.year >= 2019) & (Y.year <= 2025)]
lv3 = []
for a, fams in PAIRS:
    Y["tm"] = Y[fams].sum(axis=1)
    A = Y.groupby(["sub", "year"]).agg(gev=(a, lambda s: (s >= .5).mean() * 100), tmv=("tm", lambda s: s.mean() * 100)).reset_index()
    r = {"pair": f"{a} vs {'+'.join(fams)}"}
    for pfx in ("seso", "scinut"):
        x = A[A["sub"] == pfx].sort_values("year")
        r[f"{pfx}_spearman_across_years"] = round(float(spearmanr(x.gev, x.tmv).statistic), 3)
        dg, dm = np.sign(x.gev.diff().dropna()), np.sign(x.tmv.diff().dropna())
        r[f"{pfx}_year_changes_same_direction"] = f"{int((dg == dm).sum())} of {len(dg)}"
        r[f"{pfx}_by_year"] = {int(y): {"goemotions_pct": round(float(g), 2), "torchmoji_pct": round(float(m), 2)} for y, g, m in zip(x.year, x.gev, x.tmv)}
    w = A.pivot(index="year", columns="sub", values=["gev", "tmv"])
    gg, gm = w[("gev", "seso")] - w[("gev", "scinut")], w[("tmv", "seso")] - w[("tmv", "scinut")]
    r["subreddit_gap_same_sign_years"] = f"{int((np.sign(gg) == np.sign(gm)).sum())} of {len(gg)}"
    r["gap_by_year"] = {int(y): {"goemotions_seso_minus_scinut": round(float(a_), 2), "torchmoji_seso_minus_scinut": round(float(b_), 2)} for y, a_, b_ in zip(gg.index, gg, gm)}
    lv3.append(r)
out["years"] = lv3
(P / "emotion_model_agreement.json").write_text(json.dumps(out, indent=1))
for k in ("seso_documents", "scinut_documents"):
    print(k, json.dumps(out[k]["pairs"]))
for r in lv2:
    print("THEMES", r["pair"], r["spearman_across_theme_period_cells"], r["themes_with_same_direction_of_change"])
for r in lv3:
    print("YEARS", r["pair"], {k: v for k, v in r.items() if "spearman" in k or "same" in k})
