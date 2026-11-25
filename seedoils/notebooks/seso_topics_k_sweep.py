"""EXPERIMENT (19 Nov): how many topic buckets? For several UMAP seeds, fit the usual BERTopic (seso_topics.py settings), reassign outliers to their nearest topic, and then MERGE
the topics hierarchically to each k. The merge is done here directly (BERTopic.reduce_topics failed on the fixed vocabulary): topics are represented by their c-TF-IDF vectors
(BERTopic's formula: tf x log(1 + A / word frequency)), joined by average-linkage on cosine distance, and cut at k clusters. Per k we report
  (1) STABILITY = mean pairwise adjusted mutual information (AMI) of the document partitions between seeds (as for Louvain),
  (2) COHERENCE = mean NPMI of each merged topic's top-10 words over the documents (higher = the words belong together),
and keep the merge distances. Seed-1 merges are saved per k for charting.
Run from final_project/ with the NLP env (slow: one full fit per seed; run in the background):
  ./.venv-nlp/bin/python seedoils/notebooks/seso_topics_k_sweep.py
  -> seedoils/data/processed/seso_k_sweep.csv, seso_k_sweep_merges.csv, seso_k<k>_topics_info.csv, seso_k<k>_doc_topics.csv.gz (first seed). No text written."""
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).parent))
import seso_topics as st  # noqa: E402

PROC = st.PROC
SEEDS = [42, 7, 99]
KS = [6, 8, 12, 20, 30, 50]


def ctfidf(C):
    """C: topics x words count matrix -> BERTopic-style class-based tf-idf (dense array)."""
    C = sp.csr_matrix(C, dtype=np.float64)
    tf = sp.diags(1.0 / np.maximum(np.asarray(C.sum(axis=1)).ravel(), 1)) @ C
    freq = np.maximum(np.asarray(C.sum(axis=0)).ravel(), 1)
    A = np.asarray(C.sum(axis=1)).mean()
    return (tf.multiply(np.log(1 + A / freq))).toarray()


def npmi_coherence(W, Xb, N, df, topn=10):
    out = []
    for row in W:
        ws = np.argsort(-row)[:topn]
        sc = []
        for a, b in itertools.combinations(ws, 2):
            co = Xb[:, a].multiply(Xb[:, b]).sum()
            if co == 0:
                sc.append(-1.0); continue
            pa, pb, pab = df[a] / N, df[b] / N, co / N
            sc.append(np.log(pab / (pa * pb)) / -np.log(pab))
        out.append(np.mean(sc))
    return float(np.mean(out))


def main():
    from bertopic import BERTopic
    from hdbscan import HDBSCAN
    from scipy.cluster.hierarchy import fcluster, linkage
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
    from sklearn.metrics import adjusted_mutual_info_score as ami
    from umap import UMAP
    D = pd.read_csv(PROC / "seso_docs.csv.gz")
    V = np.load(PROC / "seso_vectors.npy").astype(np.float32)
    docs = D.text.tolist()
    stop = list(ENGLISH_STOP_WORDS | st.REDDIT_FILLER)
    vec = lambda: CountVectorizer(stop_words=stop, min_df=20, ngram_range=(1, 2))
    cvx = CountVectorizer(stop_words=stop, min_df=20, ngram_range=(1, 2))
    X = cvx.fit_transform(docs).tocsr(); vocab = cvx.get_feature_names_out()
    Xb = (X > 0).astype(np.float64).tocsc(); N = X.shape[0]; df = np.asarray(Xb.sum(axis=0)).ravel()
    pre, post = (D.created_utc < 1704067200).values, (D.created_utc >= 1704067200).values
    labels, coh, merges = {}, {}, []
    for seed in SEEDS:
        tm = BERTopic(umap_model=UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=seed),
                      hdbscan_model=HDBSCAN(min_cluster_size=150, min_samples=15, metric="euclidean", cluster_selection_method="eom", prediction_data=True),
                      vectorizer_model=vec(), calculate_probabilities=False, verbose=False)
        topics, _ = tm.fit_transform(docs, embeddings=V)
        base = np.array(tm.reduce_outliers(docs, list(topics), strategy="embeddings", embeddings=V))
        ids = sorted(set(base)); pos = {t: i for i, t in enumerate(ids)}; n0 = len(ids)
        print(f"seed {seed}: {n0} initial topics", flush=True)
        M = sp.csr_matrix((np.ones(N), (np.array([pos[t] for t in base]), np.arange(N))), shape=(n0, N))
        C = M @ X
        Z = linkage(ctfidf(C), method="average", metric="cosine")
        merges.append(pd.DataFrame({"seed": seed, "step": np.arange(len(Z)), "distance": Z[:, 2], "clusters_left": n0 - np.arange(len(Z)) - 1}))
        for k in KS:
            if k >= n0:
                continue
            cl = fcluster(Z, k, criterion="maxclust") - 1
            new = cl[np.array([pos[t] for t in base])]
            Mk = sp.csr_matrix((np.ones(N), (new, np.arange(N))), shape=(new.max() + 1, N))
            W = ctfidf(Mk @ X)
            labels[(seed, k)] = new; coh[(seed, k)] = npmi_coherence(W, Xb, N, df)
            print(f"  seed {seed} k {k}: {len(set(new))} topics, coherence {coh[(seed, k)]:.3f}", flush=True)
            if seed == SEEDS[0]:
                info = [{"topic": t, "n_docs": int((new == t).sum()), "share_pre2024": round(float((new[pre] == t).mean()), 4), "share_from2024": round(float((new[post] == t).mean()), 4),
                         "top_words": ", ".join(vocab[j] for j in np.argsort(-W[t])[:12])} for t in sorted(set(new))]
                pd.DataFrame(info).to_csv(PROC / f"seso_k{k}_topics_info.csv", index=False)
                out = D[["id", "kind", "created_utc"]].copy(); out["topic"] = new; out.to_csv(PROC / f"seso_k{k}_doc_topics.csv.gz", index=False)
    rows = []
    for k in KS:
        have = [s for s in SEEDS if (s, k) in labels]
        if len(have) < 2:
            continue
        a = [ami(labels[(p, k)], labels[(q, k)]) for p, q in itertools.combinations(have, 2)]
        rows.append({"k": k, "seeds": len(have), "stability_ami": round(float(np.mean(a)), 3), "coherence_npmi": round(float(np.mean([coh[(s, k)] for s in have])), 3)})
    R = pd.DataFrame(rows); R.to_csv(PROC / "seso_k_sweep.csv", index=False)
    pd.concat(merges).to_csv(PROC / "seso_k_sweep_merges.csv", index=False)
    print(R.to_string(index=False))


if __name__ == "__main__":
    main()
