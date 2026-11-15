"""BERTopic on ALL climate passages (stored MiniLM vectors) as the selector of 'about climate' passages. Design in ndc/PLAN.md 'CLIMATE PASSAGES: CUTOFF RESULT' (fallback).
Run from final_project/ with the NLP env, in the background (long):
  ./.venv-nlp/bin/python ndc/notebooks/climate_topics.py fit        # writes passage topics + topic table to READ
  ./.venv-nlp/bin/python ndc/notebooks/climate_topics.py validate   # AFTER the KEEP list is recorded in PLAN.md: precision of kept topics against the user's labels
Week 7 recipe as in notebooks/b_topics.py: UMAP(5 dims, cosine, seed 42) + HDBSCAN + c-TF-IDF; proper nouns and procedural words removed; outliers reassigned by embeddings.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "notebooks")); sys.path.insert(0, str(Path(__file__).parent))
from b_topics import proper_nouns, PROCEDURAL

PROC = Path("ndc/data/processed")
KEEP_FILE = PROC / "climate_topics_keep.txt"


def fit():
    from bertopic import BERTopic
    from umap import UMAP
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS
    P = pd.read_csv(PROC / "climate_passages.csv.gz"); V = np.load(PROC / "climate_passages_vectors.npy").astype(np.float32)
    prop = proper_nouns(P.text); print("proper-noun-like words removed:", len(prop), flush=True)
    stop = list(ENGLISH_STOP_WORDS | prop | PROCEDURAL)
    tm = BERTopic(umap_model=UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=42),
                  hdbscan_model=HDBSCAN(min_cluster_size=150, min_samples=15, metric="euclidean", cluster_selection_method="eom", prediction_data=True),
                  vectorizer_model=CountVectorizer(stop_words=stop, min_df=20, ngram_range=(1, 2)), calculate_probabilities=False, verbose=True)
    topics, _ = tm.fit_transform(P.text.tolist(), embeddings=V); topics = np.array(topics)
    print("topics:", len(set(topics)) - (1 if -1 in topics else 0), "| outliers:", int((topics == -1).sum()), "of", len(topics), flush=True)
    new = np.array(tm.reduce_outliers(P.text.tolist(), topics.tolist(), strategy="embeddings", embeddings=V))
    tm.update_topics(P.text.tolist(), topics=new.tolist(), vectorizer_model=CountVectorizer(stop_words=stop, min_df=20, ngram_range=(1, 2)))
    pd.DataFrame({"pid": P.pid, "topic": new, "topic_before_outlier_fix": topics}).to_csv(PROC / "climate_passage_topics.csv.gz", index=False)
    rows = [(t, int((new == t).sum()), ", ".join(w for w, _ in tm.get_topic(t)[:10])) for t in tm.get_topic_info().Topic if t != -1]
    T = pd.DataFrame(rows, columns=["topic", "n_passages", "top_words"]); T.to_csv(PROC / "climate_topics_info.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 150); print(T.to_string(index=False))


def validate():
    keep = [int(x) for x in KEEP_FILE.read_text().split()]
    P = pd.read_csv(PROC / "climate_passages.csv.gz", usecols=["pid", "country", "date", "speech_id", "score"]); S = pd.read_csv(PROC / "climate_passage_topics.csv.gz")
    P = P.merge(S, on="pid"); P["kept"] = P.topic.isin(keep)
    k = pd.read_csv(PROC / "cutoff_labelling_key.csv"); s = pd.read_csv(PROC / "cutoff_labelling_sheet_labelled.csv")
    L = k.merge(s[["id", "label"]], on="id").merge(P[["pid", "topic", "kept"]], on="pid"); L["ok"] = L.label.astype(str).str.strip().eq("1")
    print(f"KEEP topics: {len(keep)}; kept passages {int(P.kept.sum())} of {len(P)} ({P.kept.mean():.0%})")
    for nm, g in [("kept topics", L[L.kept]), ("dropped topics", L[~L.kept])]:
        print(f"labelled passages in {nm}: n={len(g)}, precision {g.ok.mean():.2f}" if len(g) else f"{nm}: none")
    print("kept-topic labelled misses (label, topic):", [(r.label, r.topic) for r in L[L.kept & ~L.ok].itertuples()])
    t = pd.DataFrame({"passages": P.groupby("country").size(), "kept": P[P.kept].groupby("country").size()}).fillna(0).astype(int); t["kept_share"] = (t.kept / t.passages).round(2)
    print(t.to_string()); print("countries with < 200 kept passages:", list(t.index[t.kept < 200]))
    P[P.kept][["pid", "country", "date", "speech_id", "topic"]].to_csv(PROC / "climate_passages_kept.csv.gz", index=False)


if __name__ == "__main__":
    {"fit": fit, "validate": validate}[sys.argv[1]]()
