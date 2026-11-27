"""For each topic and each of its top 10 c-TF-IDF words: how concentrated is the word's count in a single document? c-TF-IDF counts every occurrence, so a comment that repeats a word inflates it.
Reports per (topic, word): total count in the topic, number of documents containing it, share of the count from the single largest document. Flags words with >= 50% of their count from one document and >= 20 occurrences.
Output (words and counts only, no text): seedoils/data/processed/topic_word_concentration.csv. Run from final_project/: PYTHONPATH=seedoils/notebooks ./.venv-nlp/bin/python seedoils/notebooks/topic_word_concentration.py"""
import sys; sys.path.insert(0, "seedoils/notebooks")
import numpy as np, pandas as pd, scipy.sparse as sp
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
from seedoil_common import TOKEN_PATTERN, bertopic_clean
REDDIT_FILLER = {"just", "like", "don", "dont", "doesn", "didn", "isn", "ve", "ll", "re", "im", "ive", "youre", "thats", "really", "think", "know", "people", "thing", "things", "lot", "yeah", "yes", "actually", "pretty", "probably", "maybe", "said", "say", "going", "want", "make", "way", "got", "get", "good", "sure", "did", "does", "use", "used"}
M = "seedoils/data/processed_rebuild_model/"
D = pd.read_csv(M + "seso_docs.csv.gz", usecols=["id", "text"], keep_default_na=False).merge(pd.read_csv(M + "seso_doc_topics.csv.gz", usecols=["id", "topic"]), on="id")
info = pd.read_csv(M + "seso_topics_info.csv").set_index("topic"); info = info[info.index >= 0]
words = {t: [w.strip() for w in info.top_words[t].split(", ")][:10] for t in info.index}; vocab = sorted({w for v in words.values() for w in v})
cv = CountVectorizer(vocabulary=vocab, token_pattern=TOKEN_PATTERN, ngram_range=(1, 2), stop_words=list(ENGLISH_STOP_WORDS | REDDIT_FILLER))
X = cv.transform([bertopic_clean(str(x)) for x in D.text]).tocsc(); idx = {w: i for i, w in enumerate(cv.get_feature_names_out())}; rows = []
for t in info.index:
    r = np.where(D.topic.values == t)[0]
    for w in words[t]:
        c = X[r, idx[w]].toarray().ravel() if w in idx else np.zeros(len(r)); tot = int(c.sum())
        if tot: rows.append(dict(topic=t, word=w, count=tot, docs_with_word=int((c > 0).sum()), max_one_doc=int(c.max()), share_from_top_doc=round(c.max() / tot, 3), topic_docs=len(r)))
R = pd.DataFrame(rows); R.to_csv("seedoils/data/processed/topic_word_concentration.csv", index=False)
F = R[(R.share_from_top_doc >= 0.5) & (R["count"] >= 20)].sort_values("max_one_doc", ascending=False)
print("topic-word pairs:", len(R), "| flagged (>=50% of >=20 occurrences from one document):", len(F), "in", F.topic.nunique(), "of", R.topic.nunique(), "topics")
print(F.head(25).to_string(index=False))
print("\nmedian share of a top word's count from its single biggest document:", round(R.share_from_top_doc.median(), 3), "| 90th pct:", round(R.share_from_top_doc.quantile(.9), 3))
