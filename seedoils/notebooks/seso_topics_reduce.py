"""k-sweep with BERTopic's OWN reduce_topics (replaces the hand-written average-linkage merge in seso_topics_k_sweep.py as the main method).
Why the first attempt failed (19 Nov): reduce_topics refits the vectorizer on ONE text per topic (K texts). With CountVectorizer(min_df=20) and K < 20 texts,
sklearn raises "max_df corresponds to < documents than min_df". Fix: after the normal fit (identical to seso_topics.py), freeze the vectorizer's vocabulary (taken from the fitted vectorizer, i.e. after BERTopic's own
text clean-up) so no document-frequency pruning is applied when it is refitted on K texts; the word set is identical to the original fit. (A vocabulary built from raw comments gave
infinite c-TF-IDF: BERTopic strips punctuation, so some raw-comment terms never occur in its cleaned text.) Nothing else is changed.
Per UMAP seed: fit as in seso_topics.py, reassign outliers, update_topics, then call tm.reduce_topics(docs, nr_topics=k) for k in descending order
(the default procedure merges step by step, so going 50 -> 30 -> ... is the same as going straight to each k). Per k: stability (mean pairwise AMI between seeds)
and coherence (mean NPMI of top-10 words, same function as the hand merge), so the two methods are directly comparable.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/seso_topics_reduce.py
 -> data/processed/seso_red_k_sweep.csv, seso_red_k<k>_topics_info.csv, seso_red_k<k>_doc_topics.csv.gz (first seed). No text written."""
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).parent))
import seso_topics as st  # noqa: E402
from seso_topics_k_sweep import SEEDS, ctfidf, npmi_coherence  # noqa: E402

PROC = st.PROC
KS = [50, 30, 20, 12, 8, 6, 3, 2]


def main():
    from bertopic import BERTopic
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
    from sklearn.metrics import adjusted_mutual_info_score as ami
    from umap import UMAP
    D = pd.read_csv(PROC / "seso_docs.csv.gz")
    V = np.load(PROC / "seso_vectors.npy").astype(np.float32)
    docs = D.text.tolist()
    stop = list(ENGLISH_STOP_WORDS | st.REDDIT_FILLER)
    cvx = CountVectorizer(stop_words=stop, min_df=20, ngram_range=(1, 2))
    X = cvx.fit_transform(docs).tocsr(); vocab = cvx.get_feature_names_out()
    Xb = (X > 0).astype(np.float64).tocsc(); N = X.shape[0]; df = np.asarray(Xb.sum(axis=0)).ravel()
    orig = lambda: CountVectorizer(stop_words=stop, min_df=20, ngram_range=(1, 2))  # exactly the vectorizer of seso_topics.py fit()
    fixed = lambda v: CountVectorizer(stop_words=stop, ngram_range=(1, 2), vocabulary=list(v))
    pre, post = (D.created_utc < 1704067200).values, (D.created_utc >= 1704067200).values
    labels, coh = {}, {}
    for seed in SEEDS:
        tm = BERTopic(umap_model=UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=seed),
                      hdbscan_model=HDBSCAN(min_cluster_size=150, min_samples=15, metric="euclidean", cluster_selection_method="eom", prediction_data=True),
                      vectorizer_model=orig(), calculate_probabilities=False, verbose=False)
        topics, _ = tm.fit_transform(docs, embeddings=V)
        base = np.array(tm.reduce_outliers(docs, list(topics), strategy="embeddings", embeddings=V))
        # BERTopic's own text clean-up (strips punctuation) happens inside the fit, so the vocabulary must come from the FITTED vectorizer, not from raw comments
        tm.update_topics(docs, topics=base.tolist(), vectorizer_model=orig())
        topic_vocab = tm.vectorizer_model.get_feature_names_out()
        tm.vectorizer_model = fixed(topic_vocab)
        print(f"seed {seed}: {len(set(base))} initial topics", flush=True)
        for k in KS:
            if k >= len(set(tm.topics_)):
                continue
            try:
                tm.reduce_topics(docs, nr_topics=k)
            except Exception as e:  # report, do not hide
                print(f"  seed {seed} k {k}: reduce_topics FAILED: {type(e).__name__}: {e}", flush=True); continue
            lab = np.array(tm.topics_)
            ids = sorted(set(lab)); pos = {t: i for i, t in enumerate(ids)}; new = np.array([pos[t] for t in lab])
            Mk = sp.csr_matrix((np.ones(N), (new, np.arange(N))), shape=(new.max() + 1, N))
            W = ctfidf(Mk @ X)
            labels[(seed, k)] = new; coh[(seed, k)] = npmi_coherence(W, Xb, N, df)
            print(f"  seed {seed} k {k}: {len(ids)} topics, coherence {coh[(seed, k)]:.3f}", flush=True)
            if seed == SEEDS[0]:
                info = [{"topic": t, "n_docs": int((new == t).sum()), "share_pre2024": round(float((new[pre] == t).mean()), 4), "share_from2024": round(float((new[post] == t).mean()), 4),
                         "top_words": ", ".join(vocab[j] for j in np.argsort(-W[t])[:12])} for t in sorted(set(new))]
                pd.DataFrame(info).to_csv(PROC / f"seso_red_k{k}_topics_info.csv", index=False)
                out = D[["id", "kind", "created_utc"]].copy(); out["topic"] = new; out.to_csv(PROC / f"seso_red_k{k}_doc_topics.csv.gz", index=False)
    rows = []
    for k in KS:
        have = [s for s in SEEDS if (s, k) in labels]
        if len(have) < 2:
            continue
        a = [ami(labels[(p, k)], labels[(q, k)]) for p, q in itertools.combinations(have, 2)]
        rows.append({"k": k, "seeds": len(have), "stability_ami": round(float(np.mean(a)), 3), "coherence_npmi": round(float(np.mean([coh[(s, k)] for s in have])), 3)})
    R = pd.DataFrame(rows); R.to_csv(PROC / "seso_red_k_sweep.csv", index=False)
    print(R.to_string(index=False))


if __name__ == "__main__":
    main()
