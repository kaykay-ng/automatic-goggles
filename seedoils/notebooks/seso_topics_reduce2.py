"""Does removing the shared vocabulary make BERTopic's own reduce_topics work better?
Shared words = terms occurring in more than SHARED_DF (5%) of all comments (found mechanically from document frequency; printed at run time, not chosen by looking at which topics grow).
Why: nearly every comment says oil / seed / fat / food / eat, so topics look alike and the merge folds everything into one catch-all topic.
Per UMAP seed: fit as in seso_topics.py, reassign outliers, then for each variant re-represent the topics with a FIXED vocabulary (see seso_topics_reduce.py for why) and call
tm.reduce_topics(docs, nr_topics=k, use_ctfidf=True) so that the merge is decided by the c-TF-IDF word weights, the thing the shared words dominate:
  A: full vocabulary (control)    B: vocabulary without the shared words
Per variant and k: stability (mean pairwise AMI between seeds) and coherence (mean NPMI of top-10 words, shared words excluded from the top-10 in both so they are comparable),
plus the share of comments in the largest topic. Topic tables for seed 42 are saved.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/seso_topics_reduce2.py
 -> data/processed/seso_red2_sweep.csv, seso_red2_<A|B>_k<k>_topics_info.csv. No text written."""
from seedoil_common import TOKEN_PATTERN, bertopic_clean, hyphen_bertopic, SPLIT_TS# hyphen-keeping tokenizer (omega-6 stays whole)
import copy
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
KS = [50, 30, 20, 12, 8, 6]
SHARED_DF = 0.05


def main():
    from bertopic import BERTopic
    HyphenBERTopic = hyphen_bertopic()  # BERTopic, but hyphens survive its text clean-up
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
    from sklearn.metrics import adjusted_mutual_info_score as ami
    from umap import UMAP
    D = pd.read_csv(PROC / "seso_docs.csv.gz")
    V = np.load(PROC / "seso_vectors.npy").astype(np.float32)
    docs = D.text.tolist()
    stop = list(ENGLISH_STOP_WORDS | st.REDDIT_FILLER)
    cvx = CountVectorizer(stop_words=stop, token_pattern=TOKEN_PATTERN, min_df=20, ngram_range=(1, 2))
    X = cvx.fit_transform([bertopic_clean(d) for d in docs]).tocsr(); vocab = cvx.get_feature_names_out()
    Xb = (X > 0).astype(np.float64).tocsc(); N = X.shape[0]; df = np.asarray(Xb.sum(axis=0)).ravel()
    shared = set(vocab[df / N > SHARED_DF])
    print(f"shared words (in >{SHARED_DF:.0%} of comments): {len(shared)}: {sorted(shared)}", flush=True)
    keep_col = np.array([w not in shared for w in vocab])
    pre, post = (D.created_utc < SPLIT_TS).values, (D.created_utc >= SPLIT_TS).values
    orig = lambda: CountVectorizer(stop_words=stop, token_pattern=TOKEN_PATTERN, min_df=20, ngram_range=(1, 2))
    fixed = lambda v: CountVectorizer(stop_words=stop, token_pattern=TOKEN_PATTERN, ngram_range=(1, 2), vocabulary=list(v))
    labels, coh, big = {}, {}, {}
    for seed in SEEDS:
        tm = HyphenBERTopic(umap_model=UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=seed),
                      hdbscan_model=HDBSCAN(min_cluster_size=150, min_samples=15, metric="euclidean", cluster_selection_method="eom", prediction_data=True),
                      vectorizer_model=orig(), calculate_probabilities=False, verbose=False)
        topics, _ = tm.fit_transform(docs, embeddings=V)
        base = np.array(tm.reduce_outliers(docs, list(topics), strategy="embeddings", embeddings=V))
        tm.update_topics(docs, topics=base.tolist(), vectorizer_model=orig())
        topic_vocab = list(tm.vectorizer_model.get_feature_names_out())
        print(f"seed {seed}: {len(set(base))} initial topics", flush=True)
        for var, vv in (("A", topic_vocab), ("B", [w for w in topic_vocab if w not in shared])):
            tv = copy.deepcopy(tm)  # fresh copy per variant: BERTopic keeps topic vectors from an earlier reduction, which breaks the next one
            tv.update_topics(docs, topics=base.tolist(), vectorizer_model=fixed(vv))
            for k in KS:
                if k >= len(set(tv.topics_)):
                    continue
                tv.reduce_topics(docs, nr_topics=k, use_ctfidf=True)
                lab = np.array(tv.topics_)
                ids = sorted(set(lab)); pos = {t: i for i, t in enumerate(ids)}; new = np.array([pos[t] for t in lab])
                Mk = sp.csr_matrix((np.ones(N), (new, np.arange(N))), shape=(new.max() + 1, N))
                W = ctfidf(Mk @ X) * keep_col
                labels[(var, seed, k)] = new; coh[(var, seed, k)] = npmi_coherence(W, Xb, N, df); big[(var, seed, k)] = 100 * np.bincount(new).max() / N
                print(f"  {var} seed {seed} k {k}: coherence {coh[(var, seed, k)]:.3f}, largest topic {big[(var, seed, k)]:.0f}%", flush=True)
                if seed == SEEDS[0] and k in (50, 20, 12, 8):
                    info = [{"topic": t, "n_docs": int((new == t).sum()), "share_pre2024": round(float((new[pre] == t).mean()), 4), "share_from2024": round(float((new[post] == t).mean()), 4),
                             "top_words": ", ".join(vocab[j] for j in np.argsort(-W[t])[:12])} for t in sorted(set(new))]
                    pd.DataFrame(info).to_csv(PROC / f"seso_red2_{var}_k{k}_topics_info.csv", index=False)
    rows = []
    for var in "AB":
        for k in KS:
            have = [s for s in SEEDS if (var, s, k) in labels]
            if len(have) < 2:
                continue
            a = [ami(labels[(var, p, k)], labels[(var, q, k)]) for p, q in itertools.combinations(have, 2)]
            rows.append({"variant": var, "k": k, "stability_ami": round(float(np.mean(a)), 3), "coherence_npmi": round(float(np.mean([coh[(var, s, k)] for s in have])), 3),
                         "largest_topic_pct": round(float(np.mean([big[(var, s, k)] for s in have])), 0)})
    R = pd.DataFrame(rows); R.to_csv(PROC / "seso_red2_sweep.csv", index=False)
    print(R.to_string(index=False))


if __name__ == "__main__":
    main()
