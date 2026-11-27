"""BERTopic on r/StopEatingSeedOils: what does the seed-oil community talk about, and how did that shift in the 2024 surge?
The same steps run on r/ScientificNutrition by adding its name: `... seso_topics.py prep ScientificNutrition` (outputs scinut_*).

Run from final_project/ with the NLP env (steps 2-3 are slow; run in the background):
  ./.venv-nlp/bin/python seedoils/notebooks/seso_topics.py prep    # -> seso_docs.csv.gz (doc text, gitignored)
  ./.venv-nlp/bin/python seedoils/notebooks/seso_topics.py embed   # -> seso_vectors.npy (all-MiniLM-L6-v2, gitignored)
  ./.venv-nlp/bin/python seedoils/notebooks/seso_topics.py fit     # -> seso_doc_topics.csv.gz, seso_topics_info.csv, seso_topics_by_quarter.csv
  ./.venv-nlp/bin/python seedoils/notebooks/seso_topics.py relabel # topic words again from the SAVED assignments, hyphens kept (no refit; ids unchanged)
  ./.venv-nlp/bin/python seedoils/notebooks/seso_topics.py votes   # -> seso_topic_votes.csv (relative upvotes per topic, before vs from 2024)

Tokens (22 Nov): topic words keep hyphenated compounds whole ('omega-6', 'n-6', 'low-fat'); see seedoil_common.TOKEN_PATTERN and HyphenBERTopic.
Earlier runs used BERTopic's default clean-up, which deleted hyphens ('omega-6' -> 'omega6').
Note: BERTopic fits the vectorizer on ONE joined text per topic, so min_df=20 means a word must occur in at least 20 topics.

Relative upvotes (votes step): raw scores are not comparable (the subreddit grew; mean score ~2 in 2018-19, ~4.2 in 2024-25;
busy threads collect more votes). Each comment gets its PERCENTILE RANK of score WITHIN ITS THREAD AND LEVEL (top-level vs reply),
ties averaged (38% of comments sit at score 1). 0.5 = typical for its thread, 1 = the thread's best-voted. Reference set = ALL comments
in the thread, including those too short for the topic model, bots excluded. Threads with < MIN_THREAD comments at that level are left out.
Comments of every age are kept (decision 22 Nov), although the scores of comments from the last ~36 h before download were still settling. Self-posts are not scored this way.

Documents: comments with >= MIN_WORDS words after cleaning, plus self-posts (title + body) with >= MIN_WORDS words.
Cleaning: quoted lines ('> ...', usually the parent comment) and URLs removed; [removed]/[deleted], AutoModerator and *bot authors dropped.
Recipe as notebooks/b_topics.py and ndc/notebooks/climate_topics.py (course week 7): UMAP(5 dims, cosine, seed 42) + HDBSCAN + c-TF-IDF,
outliers then reassigned by embeddings. Unlike those scripts, proper nouns are KEPT: names (RFK, Knobbe, Ray Peat, Ancel Keys) are the point here.
"""
from seedoil_common import is_bot, not_bot, TOKEN_PATTERN, bertopic_clean, hyphen_bertopic, SPLIT_TS# shared bot rule: AutoModerator + names ending in 'bot'
import gzip
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
import os
# Defaults: the 18-19 Nov download and data/processed. To rebuild on the rerun data WITHOUT overwriting those files (26 Nov):
#   SEDOIL_RAW=seedoils/data/raw_haoyu SEDOIL_PROC=seedoils/data/processed_rebuild ./.venv-nlp/bin/python seedoils/notebooks/seso_topics.py prep|embed|fit
RAW = Path(os.environ["SEDOIL_RAW"]).resolve() if os.environ.get("SEDOIL_RAW") else ROOT / "data" / "raw"
PROC = Path(os.environ["SEDOIL_PROC"]).resolve() if os.environ.get("SEDOIL_PROC") else ROOT / "data" / "processed"
PREFIX = {"StopEatingSeedOils": "seso", "ScientificNutrition": "scinut"}  # output file prefix per subreddit
SUB = "StopEatingSeedOils"  # overridden by the optional 2nd command-line argument
PFX = PREFIX[SUB]
MIN_WORDS = 15
MODEL = "sentence-transformers/all-MiniLM-L6-v2"
URL = re.compile(r"https?://\S+|www\.\S+")
MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")  # [text](url) -> text
SKIP_AUTHORS = {"[deleted]", "AutoModerator"}
REDDIT_FILLER = {"just", "like", "don", "dont", "doesn", "didn", "isn", "ve", "ll", "re", "im", "ive", "youre", "thats", "really",
                 "think", "know", "people", "thing", "things", "lot", "yeah", "yes", "actually", "pretty", "probably", "maybe",
                 "said", "say", "going", "want", "make", "way", "got", "get", "good", "sure", "did", "does", "use", "used"}


def clean(text):
    text = "\n".join(l for l in (text or "").splitlines() if not l.lstrip().startswith(">"))
    text = URL.sub(" ", MD_LINK.sub(r"\1", text))
    return re.sub(r"\s+", " ", text).strip()


def prep():
    rows = []
    for kind in ("comments", "posts"):
        with gzip.open(RAW / f"{SUB}_{kind}.jsonl.gz", "rt", encoding="utf-8") as f:
            for line in f:
                x = json.loads(line)
                a = x.get("author") or ""
                if a in SKIP_AUTHORS or a.lower().endswith("bot"):
                    continue
                raw = x.get("body") if kind == "comments" else f"{x.get('title', '')}. {x.get('selftext') or ''}"
                if not raw or raw.strip() in ("[removed]", "[deleted]") or (kind == "posts" and (x.get("selftext") or "").strip() in ("", "[removed]", "[deleted]")):
                    continue
                t = clean(raw)
                if len(t.split()) >= MIN_WORDS:
                    rows.append((x["id"], kind[:-1], a, int(x["created_utc"]), x.get("score"), t))
    D = pd.DataFrame(rows, columns=["id", "kind", "author", "created_utc", "score", "text"]).sort_values("created_utc", ignore_index=True)
    PROC.mkdir(parents=True, exist_ok=True)
    D.to_csv(PROC / f"{PFX}_docs.csv.gz", index=False)
    print(f"{len(D):,} documents ({(D.kind == 'comment').sum():,} comments, {(D.kind == 'post').sum():,} self-posts); "
          f"median {int(D.text.str.split().str.len().median())} words; {D.author.nunique():,} authors")


def embed():
    import torch
    from sentence_transformers import SentenceTransformer
    D = pd.read_csv(PROC / f"{PFX}_docs.csv.gz")
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    m = SentenceTransformer(MODEL, device=dev)
    V = m.encode(D.text.tolist(), batch_size=256, show_progress_bar=True, normalize_embeddings=True, convert_to_numpy=True)
    np.save(PROC / f"{PFX}_vectors.npy", V.astype(np.float16))
    print(f"embedded {len(D):,} docs on {dev} -> {V.shape}")


def fit():
    from bertopic import BERTopic
    HyphenBERTopic = hyphen_bertopic()  # BERTopic, but hyphens survive its text clean-up
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
    from umap import UMAP
    D = pd.read_csv(PROC / f"{PFX}_docs.csv.gz")
    V = np.load(PROC / f"{PFX}_vectors.npy").astype(np.float32)
    docs = D.text.tolist()
    stop = list(ENGLISH_STOP_WORDS | REDDIT_FILLER)
    vec = lambda: CountVectorizer(stop_words=stop, token_pattern=TOKEN_PATTERN, min_df=20, ngram_range=(1, 2))
    tm = HyphenBERTopic(umap_model=UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=42),
                  hdbscan_model=HDBSCAN(min_cluster_size=150, min_samples=15, metric="euclidean", cluster_selection_method="eom", prediction_data=True),
                  vectorizer_model=vec(), calculate_probabilities=bool(os.environ.get("SEDOIL_PROBS")), verbose=True)  # SEDOIL_PROBS=1: also keep HDBSCAN's soft membership of every document in every topic
    topics, probs = tm.fit_transform(docs, embeddings=V)
    topics = np.array(topics)
    if probs is not None:  # documents x topics matrix (rows need not sum to 1); saved before outliers are reassigned
        np.savez_compressed(PROC / f"{PFX}_probs.npz", id=D.id.values.astype(str), p=np.asarray(probs).astype(np.float16)); print(f"probabilities saved: {np.asarray(probs).shape}", flush=True)
    n_out = int((topics == -1).sum())
    print(f"topics: {len(set(topics)) - (1 if -1 in topics else 0)} | outliers: {n_out:,} of {len(topics):,} ({n_out / len(topics):.0%})", flush=True)
    new = np.array(tm.reduce_outliers(docs, topics.tolist(), strategy="embeddings", embeddings=V))
    tm.update_topics(docs, topics=new.tolist(), vectorizer_model=vec())

    D["topic"], D["topic_before_outlier_fix"] = new, topics
    D[["id", "kind", "created_utc", "topic", "topic_before_outlier_fix"]].to_csv(PROC / f"{PFX}_doc_topics.csv.gz", index=False)
    D["year"] = pd.to_datetime(D.created_utc, unit="s").dt.year
    pre, post = D[D.created_utc < SPLIT_TS], D[D.created_utc >= SPLIT_TS]
    rows = []
    for t in sorted(set(new)):
        sel = D.topic == t
        rows.append({"topic": t, "n_docs": int(sel.sum()), "share_pre2024": round((pre.topic == t).mean(), 4),
                     "share_from2024": round((post.topic == t).mean(), 4),
                     "top_words": ", ".join(w for w, _ in tm.get_topic(t)[:10])})
    T = pd.DataFrame(rows)
    T["ratio_from2024_vs_pre"] = (T.share_from2024 / T.share_pre2024.replace(0, np.nan)).round(2)
    T.sort_values("n_docs", ascending=False).to_csv(PROC / f"{PFX}_topics_info.csv", index=False)
    D["quarter"] = pd.to_datetime(D.created_utc, unit="s").dt.to_period("Q").astype(str)
    Q = D.groupby(["quarter", "topic"]).size().unstack(fill_value=0)
    Q.div(Q.sum(axis=1), axis=0).round(4).to_csv(PROC / f"{PFX}_topics_by_quarter.csv")
    pd.set_option("display.width", 250, "display.max_colwidth", 120)
    print(T.sort_values("n_docs", ascending=False).to_string(index=False))


def relabel():
    """Rewrite the topic words in {PFX}_topics_info.csv from the SAVED topic assignments ({PFX}_doc_topics.csv.gz) with the hyphen-keeping
    tokenizer, without refitting: topic ids, sizes and shares stay exactly as they are. Reproduces BERTopic's own topic-word step:
    one joined text per topic (after bertopic_clean), CountVectorizer fitted on those texts (so min_df=20 means 'in >= 20 TOPICS'),
    c-TF-IDF = per-topic L1-normalised counts x log(1 + mean words per topic / total count of the word), top 10 words.
    The previous words are kept in a column top_words_before_relabel (first run only)."""
    import scipy.sparse as sp
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
    from sklearn.preprocessing import normalize
    D = pd.read_csv(PROC / f"{PFX}_docs.csv.gz", usecols=["id", "text"], keep_default_na=False)
    T = pd.read_csv(PROC / f"{PFX}_doc_topics.csv.gz", usecols=["id", "topic"])
    D = D.merge(T, on="id", how="inner")
    topics = sorted(D.topic.unique())
    joined = D.groupby("topic").text.apply(lambda s: " ".join(bertopic_clean(t) for t in s)).reindex(topics).tolist()
    cv = CountVectorizer(stop_words=list(ENGLISH_STOP_WORDS | REDDIT_FILLER), token_pattern=TOKEN_PATTERN, min_df=20, ngram_range=(1, 2))
    C = sp.csr_matrix(cv.fit_transform(joined), dtype=np.float64); vocab = cv.get_feature_names_out()
    idf = np.log(int(C.sum(axis=1).mean()) / np.maximum(np.asarray(C.sum(axis=0)).ravel(), 1) + 1)
    W = normalize(C, axis=1, norm="l1").multiply(idf).toarray()
    words = {t: ", ".join(vocab[j] for j in np.argsort(-W[i])[:10]) for i, t in enumerate(topics)}
    I = pd.read_csv(PROC / f"{PFX}_topics_info.csv")
    if "top_words_before_relabel" not in I.columns:
        I["top_words_before_relabel"] = I.top_words
    I["top_words"] = I.topic.map(words)
    I.to_csv(PROC / f"{PFX}_topics_info.csv", index=False)
    hy = sorted({w for w in vocab if "-" in w}, key=lambda w: -C[:, list(vocab).index(w)].sum())[:25]
    print(f"relabelled {len(topics)} topics from {len(D):,} documents; vocabulary {len(vocab):,} terms, {sum('-' in w for w in vocab):,} hyphenated, most common: {hy}")
    changed = I[I.top_words != I.top_words_before_relabel]
    print(f"{len(changed)} topics have different top-10 words; examples:")
    pd.set_option("display.width", 250, "display.max_colwidth", 110)
    print(changed[["topic", "top_words_before_relabel", "top_words"]].head(15).to_string(index=False))


def shares():
    """Recompute the before / from shares and their ratio in {PFX}_topics_info.csv from the saved assignments at the current SPLIT_TS
    (seedoil_common; 1 Jan 2024, decision 26 Nov), without refitting. Columns keep their names (share_pre2024 = before the split)."""
    D = pd.read_csv(PROC / f"{PFX}_doc_topics.csv.gz", usecols=["created_utc", "topic"])
    pre, post = D[D.created_utc < SPLIT_TS], D[D.created_utc >= SPLIT_TS]
    I = pd.read_csv(PROC / f"{PFX}_topics_info.csv")
    I["share_pre2024"] = I.topic.map(pre.topic.value_counts(normalize=True)).fillna(0).round(4)
    I["share_from2024"] = I.topic.map(post.topic.value_counts(normalize=True)).fillna(0).round(4)
    I["ratio_from2024_vs_pre"] = (I.share_from2024 / I.share_pre2024.replace(0, np.nan)).round(2)
    I.to_csv(PROC / f"{PFX}_topics_info.csv", index=False)
    print(f"{PFX}: shares recomputed at split {SPLIT_TS} ({len(pre):,} documents before, {len(post):,} from)")

MIN_THREAD = 5


def votes():
    rows = []
    with gzip.open(RAW / f"{SUB}_comments.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            x = json.loads(line)
            if is_bot(x.get("author")):
                continue
            rows.append((x["id"], x["link_id"], str(x.get("parent_id", "")).startswith("t3_"), int(x["created_utc"]), x.get("score")))
    C = pd.DataFrame(rows, columns=["id", "link_id", "top_level", "created_utc", "score"]).dropna(subset=["score"])
    g = C.groupby(["link_id", "top_level"]).score
    C["n_in_group"] = g.transform("size")
    C = C[C.n_in_group >= MIN_THREAD].copy()
    C["vote_pct"] = g.rank(method="average", pct=True).loc[C.index]
    C["top10"] = C.vote_pct >= 0.9
    T = pd.read_csv(PROC / f"{PFX}_doc_topics.csv.gz")
    T = T[T.kind == "comment"].merge(C[["id", "top_level", "vote_pct", "top10"]], on="id")
    T["period"] = np.where(T.created_utc >= SPLIT_TS, "from2024", "pre2024")
    out = (T.groupby(["topic", "period"]).agg(n=("vote_pct", "size"), mean_pct=("vote_pct", "mean"), share_top10=("top10", "mean"))
             .unstack("period"))
    out.columns = [f"{a}_{b}" for a, b in out.columns]
    out["n"] = out[["n_pre2024", "n_from2024"]].sum(axis=1)
    info = pd.read_csv(PROC / f"{PFX}_topics_info.csv")[["topic", "top_words"]]
    out = out.reset_index().merge(info, on="topic").round(3).sort_values("mean_pct_from2024", ascending=False)
    out.to_csv(PROC / f"{PFX}_topic_votes.csv", index=False)
    print(f"comments scored: {len(C):,} (of which in topic model: {len(T):,}); overall mean pct {T.vote_pct.mean():.3f}")
    pd.set_option("display.width", 250, "display.max_colwidth", 70, "display.max_rows", 300)
    big = out[(out.n_pre2024 >= 100) & (out.n_from2024 >= 100)]
    cols = ["topic", "n_pre2024", "n_from2024", "mean_pct_pre2024", "mean_pct_from2024", "share_top10_pre2024", "share_top10_from2024", "top_words"]
    print("topics with >= 100 scored comments in both periods, best received from 2024 first:")
    print(big[cols].head(20).to_string(index=False))
    print("...\nworst received from 2024:")
    print(big[cols].tail(12).to_string(index=False))


if __name__ == "__main__":
    if len(sys.argv) > 2:
        SUB = sys.argv[2]
        PFX = PREFIX[SUB]
    {"prep": prep, "embed": embed, "fit": fit, "relabel": relabel, "votes": votes, "shares": shares}[sys.argv[1]]()
