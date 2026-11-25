"""LDA (course week 6) against BERTopic on the same r/StopEatingSeedOils documents (topic corpus: comments and self-posts of 15+ words).
Words: the same counting rules as the topic labels (seedoil_common.bertopic_clean: names merged, negations marked no_x; English stop words + Reddit
filler removed), single words only, kept when in >= 20 documents and <= 40% of documents. The document-term matrix is cached (lda_dtm.npz).
LDA: scikit-learn LatentDirichletAllocation, online variational Bayes (batch 4,096, 10 passes), default priors (1/K). A document's LDA topic = its most
probable topic (LDA gives every document a MIXTURE; the argmax makes it comparable with BERTopic's one topic per document).
  fit K SEED   -> data/processed/lda/lda_k<K>_s<SEED>_doc_topics.csv.gz (id, topic, top_prob), _topics.csv (top words, share before / from 2024)
  compare      -> data/processed/lda_comparison.json:
     agreement with BERTopic (AMI, NMI; argmax topics vs BERTopic seed 42), LDA stability across its own seeds (AMI), coherence (mean NPMI of each
     topic's top 10 words, computed for both models on the same document-term matrix; BERTopic's top words recomputed as c-TF-IDF over this
     matrix so both use the same vocabulary), diversity (share of distinct words among all topics' top 10s), how mixed LDA documents are (mean
     top probability), and, once themes_confirmed.json exists, each theme's share before / from 2024 under LDA (LDA topics mapped to themes by
     majority overlap with the BERTopic themes) next to BERTopic.
Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/lda_compare.py fit 123 0 ; ... compare"""
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).parent))
import seso_topics as st  # noqa: E402
from seedoil_common import TOKEN_PATTERN, bertopic_clean  # noqa: E402

PROC = st.PROC; OUT = PROC / "lda"; SPLIT = 1704067200; DTM = OUT / "lda_dtm.npz"; MAP_MIN = 0.2


def dtm():
    OUT.mkdir(parents=True, exist_ok=True)
    D = pd.read_csv(PROC / "seso_docs.csv.gz", usecols=["id", "created_utc", "text"], keep_default_na=False)
    if DTM.exists():
        z = np.load(DTM, allow_pickle=True)
        return D, sp.csr_matrix((z["data"], z["indices"], z["indptr"]), shape=tuple(z["shape"])), z["vocab"]
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
    cv = CountVectorizer(preprocessor=bertopic_clean, token_pattern=TOKEN_PATTERN, stop_words=list(ENGLISH_STOP_WORDS | st.REDDIT_FILLER | {"emptydoc"}),
                         min_df=20, max_df=0.4)
    X = cv.fit_transform(D.text).tocsr(); vocab = cv.get_feature_names_out()
    np.savez_compressed(DTM, data=X.data, indices=X.indices, indptr=X.indptr, shape=X.shape, vocab=vocab)
    print(f"document-term matrix {X.shape[0]:,} x {X.shape[1]:,}, {X.nnz:,} non-zeros", flush=True)
    return D, X, vocab


def fit(K, seed):
    from sklearn.decomposition import LatentDirichletAllocation
    D, X, vocab = dtm(); t0 = time.time()
    lda = LatentDirichletAllocation(n_components=K, learning_method="online", batch_size=4096, max_iter=10, random_state=seed, n_jobs=2)
    theta = lda.fit_transform(X)
    top = theta.argmax(1); post = (D.created_utc >= SPLIT).values
    pd.DataFrame({"id": D.id, "topic": top, "top_prob": theta.max(1).round(3)}).to_csv(OUT / f"lda_k{K}_s{seed}_doc_topics.csv.gz", index=False)
    rows = [{"topic": k, "n_docs": int((top == k).sum()), "share_pre2024": round(float((top[~post] == k).mean()), 4), "share_from2024": round(float((top[post] == k).mean()), 4),
             "top_words": ", ".join(vocab[j] for j in np.argsort(-lda.components_[k])[:10])} for k in range(K)]
    pd.DataFrame(rows).sort_values("n_docs", ascending=False).to_csv(OUT / f"lda_k{K}_s{seed}_topics.csv", index=False)
    print(f"LDA K={K} seed={seed}: {time.time() - t0:.0f}s; perplexity {lda.perplexity(X):.0f}; empty topics {sum(r['n_docs'] == 0 for r in rows)}", flush=True)


def npmi(top_idx, Xb, N, df):
    sc = []
    for ws in top_idx:
        v = []
        for a, b in itertools.combinations(ws, 2):
            co = Xb[:, a].multiply(Xb[:, b]).sum()
            if co == 0:
                v.append(-1.0); continue
            pa, pb, pab = df[a] / N, df[b] / N, co / N
            v.append(math_log(pab / (pa * pb)) / -math_log(pab))
        sc.append(np.mean(v))
    return float(np.mean(sc))


def math_log(x):
    return float(np.log(x))


def compare():
    from sklearn.metrics import adjusted_mutual_info_score as ami, normalized_mutual_info_score as nmi
    from sklearn.preprocessing import normalize
    D, X, vocab = dtm(); N = X.shape[0]; Xb = (X > 0).astype(np.float64).tocsc(); df = np.asarray(Xb.sum(0)).ravel()
    B = pd.read_csv(PROC / "seso_doc_topics.csv.gz", usecols=["id", "topic"]).set_index("id").topic.reindex(D.id).values
    post = (D.created_utc >= SPLIT).values
    runs = {}
    for f in sorted(OUT.glob("lda_k*_s*_doc_topics.csv.gz")):
        K, s = f.name.split("_")[1][1:], f.name.split("_")[2][1:]
        runs[(int(K), int(s))] = pd.read_csv(f).set_index("id").reindex(D.id)
    # c-TF-IDF top words of the BERTopic topics over THIS matrix, so both models are scored on the same vocabulary
    ids = sorted(set(B)); M = sp.csr_matrix((np.ones(N), (np.searchsorted(ids, B), np.arange(N))), shape=(len(ids), N)) @ X
    C = sp.csr_matrix(M, dtype=float); idf = np.log(int(C.sum(1).mean()) / np.maximum(np.asarray(C.sum(0)).ravel(), 1) + 1)
    W = normalize(C, norm="l1", axis=1).multiply(idf).toarray(); b_top = [np.argsort(-w)[:10] for w in W]
    diversity = lambda tops: round(len({j for t in tops for j in t}) / (10 * len(tops)), 3)
    out = {"bertopic": {"topics": len(ids), "coherence_npmi": round(npmi(b_top, Xb, N, df), 3), "diversity": diversity(b_top)}, "lda": []}
    vidx = {w: i for i, w in enumerate(vocab)}
    for (K, s), R in sorted(runs.items()):
        T = pd.read_csv(OUT / f"lda_k{K}_s{s}_topics.csv")
        l_top = [[vidx[w.strip()] for w in tw.split(",")] for tw in T.top_words]
        out["lda"].append({"K": K, "seed": s, "used_topics": int((T.n_docs > 0).sum()), "ami_vs_bertopic": round(float(ami(B, R.topic.values)), 3),
                           "nmi_vs_bertopic": round(float(nmi(B, R.topic.values)), 3), "mean_top_prob": round(float(R.top_prob.mean()), 3),
                           "coherence_npmi": round(npmi(l_top, Xb, N, df), 3), "diversity": diversity(l_top)})
    stab = [{"K": K, "a": a, "b": b, "ami": round(float(ami(runs[(K, a)].topic.values, runs[(K, b)].topic.values)), 3)}
            for K in {k for k, _ in runs} for a, b in itertools.combinations(sorted(s for k, s in runs if k == K), 2)]
    out["lda_stability"] = stab
    tf = PROC / "themes_confirmed.json"
    if tf.exists():
        themes = json.loads(tf.read_text()); bt = pd.Series("other", index=range(N))
        for th, tids in themes.items():
            bt[np.isin(B, tids)] = th
        out["themes"] = {}
        for th in themes:
            row = {"bertopic": [round(float((bt.values[~post] == th).mean() * 100), 2), round(float((bt.values[post] == th).mean() * 100), 2)]}
            for (K, s), R in runs.items():
                # an LDA topic counts toward the theme holding the largest share of its documents, if that share is >= MAP_MIN (LDA topics are
                # mixtures, so a majority rule leaves almost every LDA topic unmapped; 30% leaves several themes without any LDA topic)
                df_ = pd.DataFrame({"t": R.topic.values, "th": bt.values}); n_t = df_.groupby("t").size()
                sh = df_[df_.th != "other"].groupby("t").th.value_counts().div(n_t, level=0)
                best = sh.groupby(level=0).idxmax().map(lambda x: x[1]); val = sh.groupby(level=0).max()
                mp = {t: best[t] for t in val.index if val[t] >= MAP_MIN}
                lt = np.array([mp.get(t, "other") for t in R.topic.values], dtype=object)
                row[f"lda_k{K}_s{s}"] = [round(float((lt[~post] == th).mean() * 100), 2), round(float((lt[post] == th).mean() * 100), 2)]
            out["themes"][th] = row
    (PROC / "lda_comparison.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "fit":
        fit(int(sys.argv[2]), int(sys.argv[3]))
    else:
        compare()
