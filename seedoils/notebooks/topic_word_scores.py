"""Topic word scores (BERTopic 'barchart' view). Recomputes the class-based TF-IDF (c-TF-IDF) score of every word in every topic exactly as seso_topics.py relabel does (the fitted model was not saved): one joined text per topic after bertopic_clean, CountVectorizer (English + Reddit filler stop words, 1-2 grams, min_df 20 topics), counts L1-normalised per topic times idf = log(1 + mean words per topic / total count of the word).
Checks that the top-10 words reproduce seso_topics_info.csv. Outputs: seedoils/data/processed/topic_word_scores.csv (topic, rank, word, score; words only, no text), seedoils/figures/topic_word_scores.png (12 topics, top 6 words each).
Run from final_project/:  PYTHONPATH=seedoils/notebooks ./.venv-nlp/bin/python seedoils/notebooks/topic_word_scores.py"""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
from sklearn.preprocessing import normalize
sys.path.insert(0, "seedoils/notebooks")
from seedoil_common import TOKEN_PATTERN, bertopic_clean
REDDIT_FILLER = {"just", "like", "don", "dont", "doesn", "didn", "isn", "ve", "ll", "re", "im", "ive", "youre", "thats", "really", "think", "know", "people", "thing", "things", "lot", "yeah", "yes", "actually", "pretty", "probably", "maybe", "said", "say", "going", "want", "make", "way", "got", "get", "good", "sure", "did", "does", "use", "used"}
R, P = "seedoils/data/processed_rebuild/", "seedoils/data/processed/"
D = pd.read_csv(R + "seso_docs.csv.gz", usecols=["id", "text"], keep_default_na=False).merge(pd.read_csv(R + "seso_doc_topics.csv.gz", usecols=["id", "topic"]), on="id")
topics = sorted(D.topic.unique()); print("cleaning", len(D), "documents (a few minutes)...", flush=True)
joined = D.groupby("topic").text.apply(lambda s: " ".join(bertopic_clean(t) for t in s)).reindex(topics).tolist()
cv = CountVectorizer(stop_words=list(ENGLISH_STOP_WORDS | REDDIT_FILLER), token_pattern=TOKEN_PATTERN, min_df=20, ngram_range=(1, 2))
C = sp.csr_matrix(cv.fit_transform(joined), dtype=np.float64); vocab = cv.get_feature_names_out()
idf = np.log(int(C.sum(axis=1).mean()) / np.maximum(np.asarray(C.sum(axis=0)).ravel(), 1) + 1); W = normalize(C, axis=1, norm="l1").multiply(idf).toarray()
rows = []; info = pd.read_csv(R + "seso_topics_info.csv").set_index("topic"); same = 0
for i, t in enumerate(topics):
    o = np.argsort(-W[i])[:10]; rows += [{"topic": t, "rank": r + 1, "word": vocab[j], "score": round(float(W[i, j]), 5)} for r, j in enumerate(o)]
    same += ", ".join(vocab[j] for j in o) == info.top_words[t]
S = pd.DataFrame(rows); S.to_csv(P + "topic_word_scores.csv", index=False); print(f"top-10 words identical to seso_topics_info.csv for {same} of {len(topics)} topics")
show = [0, 1, 5, 98, 47, 26, 73, 37, 27, 19, 3, 17]; n = D.topic.value_counts()
plt.rcParams.update({"font.size": 7}); fig, axs = plt.subplots(3, 4, figsize=(11, 6.4), constrained_layout=True)
for ax, t in zip(axs.ravel(), show):
    d = S[(S.topic == t) & (S["rank"] <= 6)].iloc[::-1]; ax.barh(d.word, d.score, color="#4682b4", height=0.65); ax.set_title(f"Topic {t}  ({n[t]:,} docs)", fontsize=8, loc="left"); ax.tick_params(axis="y", labelsize=7.5); ax.spines[["top", "right"]].set_visible(False)
    for y, v in enumerate(d.score): ax.text(v, y, f" {v:.3f}", va="center", fontsize=6, color="0.35")
    ax.set_xlim(0, d.score.max() * 1.28)
fig.suptitle("Topic word scores (class-based TF-IDF): top 6 words of 12 topics", fontsize=9); fig.savefig("seedoils/figures/topic_word_scores.png", dpi=170)
print(S[S.topic.isin([98, 47, 26])].groupby("topic").apply(lambda d: ", ".join(f"{w} {s:.3f}" for w, s in zip(d.word[:6], d.score[:6]))).to_string())
