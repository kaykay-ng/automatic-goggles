"""How reliable is the GoEmotions 'hostile' flag behind Figure 3, and do Figure 3's conclusions depend on how it is defined?
Model: SamLowe/roberta-base-go_emotions (28 labels, multi-label probabilities). The page's flag: max(anger, annoyance, disapproval, disgust) >= 0.5.
Checks (comments of the 2,618 network members, as in Figure 3):
 (1) What the flag is made of: which of the four labels is the highest in flagged comments.
 (2) Alternative definitions: threshold 0.3 / 0.5 / 0.7; 'strong' = anger or disgust only; disapproval only; argmax of all 28 labels is one of the four. For each: share of comments flagged, overlap with the page's flag (Jaccard),
     overall change pre-2024 -> from 2024, and whether the community ranking by hostility and by change stays the same (Spearman rank correlation with the page's definition).
 (3) Writes a blinded sample (150 comments, stratified by the page's score band) for hand labelling, data/processed/hostility_sample_to_label.csv (text, so gitignored; ids only in the key file).
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python seedoils/notebooks/hostility_robustness.py"""
from seedoil_common import community_labels, SPLIT_TS# community names from data/processed/community_names.json (hand-written)
from seedoil_common import is_bot, not_bot  # shared bot rule: AutoModerator + names ending in 'bot'
import glob
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

P = Path("seedoils/data/processed"); CUT = SPLIT_TS; rng = np.random.default_rng(7)
raw = {}
with gzip.open(glob.glob("seedoils/data/raw/*StopEatingSeedOils_comments.jsonl.gz")[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); raw[x["id"]] = (x["author"], int(x["created_utc"]))
D = pd.read_csv(P / "seso_doc_topics.csv.gz"); D = D[D.kind == "comment"].copy(); D["a"] = D.id.map(lambda i: raw.get(i, (None,))[0])
D = D[D.a.notna() & (~D.a.isin(["[deleted]", "AutoModerator"]) & not_bot(D.a))]; nd = D.groupby("a").size(); U = np.array(sorted(nd[nd >= 10].index)); N = pd.read_csv(P / "commenter_topic_network_130_nodes.csv"); assert len(U) == len(N)
D = D[D.a.isin(set(U))].copy(); D["c"] = D.a.map(dict(zip(U, N.community))); D["post"] = D.created_utc >= CUT
LABS = list(pd.read_csv(P / "goemo_monthly.csv", nrows=1).columns[1:29]); ix = {k: LABS.index(k) for k in LABS}; H4 = [ix[k] for k in ("anger", "annoyance", "disapproval", "disgust")]
docs = pd.read_csv(P / "seso_docs.csv.gz", usecols=["id", "text"], keep_default_na=False); z = np.load(P / "goemo_seso.npz", allow_pickle=True); assert (z["id"].astype(str) == docs.id.astype(str).values).all()
pos = pd.Series(np.arange(len(docs)), index=docs.id.astype(str).values); row = D.id.map(pos).astype(int).values; p = z["p"][row].astype(np.float32); D = D.reset_index(drop=True)
mx = p[:, H4].max(1); am = p.argmax(1); who = np.array(H4)[p[:, H4].argmax(1)]
fl = mx >= .5
print(f"comments {len(D):,}; flagged by the page's definition {fl.mean():.1%}")
print("(1) among flagged comments, the highest of the four labels is:", {LABS[k]: f"{(who[fl] == k).mean():.0%}" for k in H4})
print(f"    flagged comments whose single most likely label (of all 28) is NOT one of the four: {(~np.isin(am[fl], H4)).mean():.0%}; flagged with score between 0.5 and 0.7: {((mx >= .5) & (mx < .7)).sum() / fl.sum():.0%}")
defs = {"page: max of 4 >= 0.5": mx >= .5, "threshold 0.3": mx >= .3, "threshold 0.7": mx >= .7,
        "anger or disgust >= 0.5": np.maximum(p[:, ix["anger"]], p[:, ix["disgust"]]) >= .5, "disapproval only >= 0.5": p[:, ix["disapproval"]] >= .5, "argmax is one of the four": np.isin(am, H4)}
base_rate = None; res = {}
print("\n(2) definitions: share flagged | overlap with page flag (Jaccard) | overall pre -> from 2024 (pts) | community rank corr with page (level, change)")
for nm, f_ in defs.items():
    D["f"] = f_.astype(float); g = D.groupby(["c", "post"]).f.mean().unstack() * 100; lev = D.groupby("c").f.mean(); chg = g[True] - g[False]
    if base_rate is None: base_rate = (lev, chg)
    jac = (f_ & fl).sum() / (f_ | fl).sum(); pre, post = D[~D.post].f.mean() * 100, D[D.post].f.mean() * 100
    rl = spearmanr(lev, base_rate[0])[0]; rc = spearmanr(chg, base_rate[1])[0]; res[nm] = (chg, lev)
    print(f"  {nm:<28} {f_.mean():6.1%} | {jac:.2f} | {pre:.2f}% -> {post:.2f}% ({post - pre:+.2f}) | {rl:+.2f}, {rc:+.2f}")
print("\ncommunity change (pts) under each definition:")
K = int(D.c.max()) + 1; names = community_labels(K)[1]
print(f"  {'community':<20}" + "".join(f"{k[:18]:>20}" for k in res)); [print(f"  {names[c]:<20}" + "".join(f"{res[k][0].get(c, float('nan')):>20.2f}" for k in res)) for c in range(K)]
# (3) sample for hand labelling, stratified by page score band
bands = [(0, .1), (.1, .3), (.3, .5), (.5, .7), (.7, 1.01)]; samp = []
for lo, hi in bands:
    idx = np.where((mx >= lo) & (mx < hi))[0]; samp += list(rng.choice(idx, 30, replace=False))
samp = rng.permutation(samp); S = D.iloc[samp][["id"]].copy(); S["text"] = docs.set_index(docs.id.astype(str)).text.reindex(S.id.astype(str)).values
S["score_band"] = [next(f"{lo}-{min(hi, 1):.1f}" for lo, hi in bands if lo <= mx[i] < hi) for i in samp]; S["item"] = range(1, len(S) + 1)
if (P / "hostility_sample_to_label.csv").exists():
    print("hand-label sample already exists: NOT overwritten (delete it by hand to draw a new one)"); raise SystemExit
S[["item", "text"]].assign(hostile_toward_person_or_group="", disagreement_or_complaint_only="", neither="", notes="").to_csv(P / "hostility_sample_to_label.csv", index=False)
S[["item", "id", "score_band"]].to_csv(P / "hostility_sample_key.csv", index=False); print("\nwrote blinded sample of", len(S), "comments (30 per score band: 0-0.1, 0.1-0.3, 0.3-0.5, 0.5-0.7, 0.7-1.0)")
