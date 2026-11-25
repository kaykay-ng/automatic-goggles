"""LDA next to BERTopic on the same r/StopEatingSeedOils documents (comments of >= 15 words plus self-posts, quotes and links removed; seso_docs.csv.gz).
LDA = scikit-learn LatentDirichletAllocation (online variational Bayes), unigrams, English stop words + the topic model's Reddit filler, words in 30..30% of documents (max_df drops words nearly every comment uses: seed, oil, fat, food ...).
For k in KS and two seeds each:
 - coherence: mean NPMI of each topic's top-10 words over documents (same function as the k-sweep), BERTopic's ~130 topics scored the same way on their top unigrams;
 - seed stability: adjusted mutual information (AMI) of the dominant-topic labels between the two seeds;
 - growth: each topic's mean share (sum of document-topic weights) before 2024 and from 2024, ratio, topics with >= 1% share kept;
 - agreement with BERTopic: AMI of dominant LDA topic vs BERTopic topic, and where the five fastest-growing BERTopic topics (46 rfk/trump, 43 trump/vote, 20 vaccines/covid, 68, 107 political/left-right) land.
Run from final_project/ with the NLP env (slow; background):  ./.venv-nlp/bin/python seedoils/notebooks/lda_compare_k20_k40.py   -> data/processed/lda_compare_summary.json, lda_k<k>_topics.csv. No text written."""
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
from sklearn.metrics import adjusted_mutual_info_score as ami

sys.path.insert(0, str(Path(__file__).parent))
import seso_topics as st  # noqa: E402

P = Path("seedoils/data/processed"); CUT = 1704067200; KS = [20, 40]; SEEDS = [0, 1]
D = pd.read_csv(P / "seso_docs.csv.gz", keep_default_na=False); T = pd.read_csv(P / "seso_doc_topics.csv.gz", usecols=["id", "topic"]); assert (D.id.values == T.id.values).all()
bert = T.topic.values; post = (D.created_utc >= CUT).values; n = len(D)
cv = CountVectorizer(stop_words=list(ENGLISH_STOP_WORDS | st.REDDIT_FILLER), min_df=30, max_df=0.30, ngram_range=(1, 1))
X = cv.fit_transform(D.text.tolist()).tocsr(); V = cv.get_feature_names_out(); print(f"documents {n:,}; vocabulary {len(V):,} words (30 docs min, 30% max)", flush=True)
Xb = (X > 0).astype(np.float64).tocsc(); df = np.asarray(Xb.sum(0)).ravel(); vi = {w: i for i, w in enumerate(V)}
def npmi(words):
    ids = [vi[w] for w in words if w in vi][:10]; sc = []
    for a, b in itertools.combinations(ids, 2):
        co = Xb[:, a].multiply(Xb[:, b]).sum()
        if co == 0: sc.append(-1.0); continue
        pa, pb, pab = df[a] / n, df[b] / n, co / n; sc.append(np.log(pab / (pa * pb)) / -np.log(pab))
    return float(np.mean(sc)) if sc else np.nan
# BERTopic topics scored the same way (top unigrams that are in this vocabulary)
info = pd.read_csv(P / "seso_topics_info.csv"); bc = []
for w in info.top_words:
    uni = [x.strip() for x in w.split(",") if " " not in x.strip() and x.strip() in vi]
    if len(uni) >= 5: bc.append(npmi(uni))
print(f"BERTopic ({len(info)} topics; {len(bc)} with >= 5 top unigrams in this vocabulary): mean NPMI {np.nanmean(bc):.3f}", flush=True)
out = {"bertopic_npmi": float(np.nanmean(bc)), "runs": []}
top5 = {46: "rfk, trump", 43: "trump, vote", 20: "vaccines, covid", 68: "political, right wing", 107: "left, political"}
for k in KS:
    labs = []; th = []
    for s in SEEDS:
        t0 = time.time(); lda = LatentDirichletAllocation(n_components=k, learning_method="online", batch_size=4096, max_iter=8, random_state=s, n_jobs=-1, evaluate_every=-1)
        W = lda.fit_transform(X); W = W / W.sum(1, keepdims=True); comp = lda.components_ / lda.components_.sum(1, keepdims=True)
        tops = [[V[j] for j in np.argsort(-comp[t])[:10]] for t in range(k)]; coh = [npmi(w) for w in tops]
        lab = W.argmax(1); labs.append(lab); th.append((W, tops, coh)); print(f"k={k} seed {s}: fitted in {time.time() - t0:.0f}s; mean NPMI {np.mean(coh):.3f}", flush=True)
    stab = ami(labs[0], labs[1]); a_b = [ami(l, bert) for l in labs]; print(f"k={k}: seed stability AMI {stab:.3f}; AMI with BERTopic labels {a_b[0]:.3f}, {a_b[1]:.3f}", flush=True)
    W, tops, coh = th[0]; share_pre, share_post = W[~post].mean(0) * 100, W[post].mean(0) * 100; ratio = share_post / share_pre
    rows = [{"topic": t, "share_pre": round(share_pre[t], 2), "share_post": round(share_post[t], 2), "ratio": round(ratio[t], 2), "npmi": round(coh[t], 3), "top_words": ", ".join(tops[t])} for t in range(k)]
    pd.DataFrame(rows).sort_values("ratio", ascending=False).to_csv(P / f"lda_k{k}_topics.csv", index=False)
    print(f"k={k} (seed 0) topics by growth:", flush=True)
    for r in sorted(rows, key=lambda r: -r["ratio"])[:6]: print(f"   x{r['ratio']:<5} share {r['share_pre']}% -> {r['share_post']}%  npmi {r['npmi']}  {r['top_words']}", flush=True)
    for r in sorted(rows, key=lambda r: r["ratio"])[:3]: print(f"   x{r['ratio']:<5} share {r['share_pre']}% -> {r['share_post']}%  npmi {r['npmi']}  {r['top_words']}", flush=True)
    land = {}
    for b, nm in top5.items():
        m = bert == b; c = pd.Series(labs[0][m]).value_counts(normalize=True); land[nm] = (int(c.index[0]), round(float(c.iloc[0]), 2)); print(f"   BERTopic {nm}: {int(m.sum())} docs, {c.iloc[0]:.0%} fall in LDA topic {int(c.index[0])} ({', '.join(tops[int(c.index[0])][:5])})", flush=True)
    out["runs"].append({"k": k, "npmi": [float(np.mean(t[2])) for t in th], "stability_ami": float(stab), "ami_bertopic": [float(x) for x in a_b], "landing": land})
(P / "lda_compare_summary.json").write_text(json.dumps(out, indent=1)); print("done", flush=True)
