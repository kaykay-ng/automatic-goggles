"""BERTopic dynamic topic modeling (topics_over_time) on the saved fitted model (seedoils/data/processed_rebuild_model/seso_bertopic_model; the model was fitted once on all 149,815 documents, 123 topics).
topics_over_time recomputes each topic's class-based TF-IDF words for every time bin from the documents of that topic and bin, so we can see whether the WORDS of a topic change over time; it does not refit or re-cluster. Settings: documents from 2022-01-01 on (earlier months are sparse), MONTHLY bins (each document is stamped with the first day of its month, nr_bins=None so every calendar month is one bin; the BERTopic page warns that more than about 50 unique timestamps can hurt the representations), global_tuning OFF with evolution_tuning on, and, for comparison, both off.
Set-up notes: the safetensors model loads as plain BERTopic without our vectorizer, so (1) BERTopic's own text clean-up is replaced by seedoil_common.bertopic_clean applied to the joined text of each topic (and bin), as HyphenBERTopic did in the original fit; (2) the vectorizer is re-fitted on the per-topic joined texts cleaned the same way, and its vocabulary size is checked against the saved c-TF-IDF matrix (123 x 12,071).
Outputs (local; words only, no text): seedoils/data/processed/topics_over_time.csv (key topics) and seedoils/figures/topics_over_time_top10_monthly.html. Run from final_project/:  PYTHONPATH=seedoils/notebooks ./.venv-nlp/bin/python seedoils/notebooks/topics_over_time.py"""
import sys, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from bertopic import BERTopic
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
sys.path.insert(0, "seedoils/notebooks")
from seedoil_common import TOKEN_PATTERN, bertopic_clean
REDDIT_FILLER = {"just", "like", "don", "dont", "doesn", "didn", "isn", "ve", "ll", "re", "im", "ive", "youre", "thats", "really", "think", "know", "people", "thing", "things", "lot", "yeah", "yes", "actually", "pretty", "probably", "maybe", "said", "say", "going", "want", "make", "way", "got", "get", "good", "sure", "did", "does", "use", "used"}
M, P = "seedoils/data/processed_rebuild_model/", "seedoils/data/processed/"
D = pd.read_csv(M + "seso_docs.csv.gz", usecols=["id", "created_utc", "text"], keep_default_na=False).merge(pd.read_csv(M + "seso_doc_topics.csv.gz", usecols=["id", "topic"]), on="id")
m = BERTopic.load(M + "seso_bertopic_model", embedding_model=None); m._preprocess_text = lambda docs: [bertopic_clean(str(d)) for d in docs]  # what HyphenBERTopic does: our clean-up applied to the JOINED text of a topic (and bin)
topics = sorted(D.topic.unique()); joined = [bertopic_clean(x) for x in D.groupby("topic").text.apply(" ".join).reindex(topics).tolist()]  # cleaned after joining, as in the original fit
cv = CountVectorizer(stop_words=list(ENGLISH_STOP_WORDS | REDDIT_FILLER), token_pattern=TOKEN_PATTERN, min_df=20, ngram_range=(1, 2)); cv.fit(joined); m.vectorizer_model = cv
print("vocabulary", len(cv.get_feature_names_out()), "| saved c-TF-IDF shape", m.c_tf_idf_.shape, flush=True)
S = D[pd.to_datetime(D.created_utc, unit="s") >= "2022-01-01"]; ts = pd.to_datetime(S.created_utc, unit="s").dt.to_period("M").dt.to_timestamp().tolist(); docs = S.text.tolist(); tp = S.topic.tolist()
TOP10 = list(D.topic.value_counts().head(10).index)  # the 10 largest topics (documents assigned), not a hand-picked list
KEY = TOP10
print("running topics_over_time (monthly bins, global_tuning off, evolution_tuning off)", flush=True)
T = m.topics_over_time(docs, ts, topics=tp, nr_bins=None, global_tuning=False, evolution_tuning=False)
T.to_csv(P + "topics_over_time_monthly_all_topics.csv", index=False)
f = m.visualize_topics_over_time(T, topics=TOP10, width=1100, height=560); f.write_html("seedoils/figures/topics_over_time_top10_monthly.html", include_plotlyjs="cdn")
T["ts"] = pd.to_datetime(T.Timestamp); info = pd.read_csv(M + "seso_topics_info.csv").set_index("topic"); pts = ["2022-01", "2022-07", "2023-01", "2023-07", "2024-01", "2024-08", "2025-01", "2025-07", "2026-01", "2026-07"]
for t in TOP10:
    print(f"\n=== topic {t} ({int((D.topic == t).sum()):,} documents; overall words: {', '.join(info.top_words[t].split(', ')[:4])})")
    a = T[T.Topic == t].set_index(T[T.Topic == t].ts.dt.strftime("%Y-%m"))
    for p in pts:
        if p in a.index: print(f"  {p}  n={int(a.loc[p].Frequency):>4}  {', '.join(a.loc[p].Words.split(', ')[:5])}")
