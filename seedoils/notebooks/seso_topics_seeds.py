"""Stability of the r/StopEatingSeedOils topic model across UMAP seeds (decision 22 Nov: 20 runs = the main seed 42 + seeds 1-19).
Same settings as seso_topics.py fit (UMAP 15 neighbours, 5 dims, cosine; HDBSCAN min_cluster_size 150, min_samples 15; outliers reassigned by embeddings);
only UMAP's random_state changes. Embeddings are reused (seso_vectors.npy), so the only randomness tested is UMAP's layout (HDBSCAN is deterministic).

  fit SEED [SEED ...]   -> data/processed/seeds/seso_seed<SEED>_doc_topics.csv.gz (id, topic, topic_before_outlier_fix); one line per run in seeds/runs.csv
  summary               -> data/processed/seso_seed_stability.json: topics and outlier share per run; pairwise AMI and NMI (all documents, and documents
                           HDBSCAN placed itself in both runs); and, once the hand-picked themes exist (themes_confirmed.json), each theme's share before /
                           from 2024 in every run. Topic ids differ between runs, so a run's topic counts toward a theme when most of its documents are in
                           that theme in the reference run (seed 42).
Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/seso_topics_seeds.py fit 1 2 3 ;  ... summary"""
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import seso_topics as st  # noqa: E402
from seedoil_common import TOKEN_PATTERN, hyphen_bertopic, SPLIT_TS, THEMES_FILE# noqa: E402

PROC = st.PROC
SEEDS_DIR = PROC / "seeds"
REF = 42
SPLIT = SPLIT_TS


def fit(seeds):
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
    from umap import UMAP
    HyphenBERTopic = hyphen_bertopic()
    SEEDS_DIR.mkdir(parents=True, exist_ok=True)
    D = pd.read_csv(PROC / "seso_docs.csv.gz", usecols=["id", "text"], keep_default_na=False)
    V = np.load(PROC / "seso_vectors.npy").astype(np.float32)
    docs = D.text.tolist(); stop = list(ENGLISH_STOP_WORDS | st.REDDIT_FILLER)
    for seed in seeds:
        out = SEEDS_DIR / f"seso_seed{seed}_doc_topics.csv.gz"
        if out.exists():
            print(f"seed {seed}: exists, skipped", flush=True); continue
        t0 = time.time()
        tm = HyphenBERTopic(umap_model=UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=seed),
                            hdbscan_model=HDBSCAN(min_cluster_size=150, min_samples=15, metric="euclidean", cluster_selection_method="eom", prediction_data=True),
                            vectorizer_model=CountVectorizer(stop_words=stop, token_pattern=TOKEN_PATTERN, min_df=20, ngram_range=(1, 2)),
                            calculate_probabilities=False, verbose=False)
        topics, _ = tm.fit_transform(docs, embeddings=V); topics = np.array(topics)
        new = np.array(tm.reduce_outliers(docs, topics.tolist(), strategy="embeddings", embeddings=V))
        pd.DataFrame({"id": D.id, "topic": new, "topic_before_outlier_fix": topics}).to_csv(out, index=False)
        n_top = len(set(new)); outl = float((topics == -1).mean())
        with open(SEEDS_DIR / "runs.csv", "a") as fh:
            fh.write(f"{seed},{n_top},{outl:.4f},{time.time() - t0:.0f}\n")
        print(f"seed {seed}: {n_top} topics, outliers {outl:.0%}, {time.time() - t0:.0f}s", flush=True)


def summary():
    from sklearn.metrics import adjusted_mutual_info_score as ami, normalized_mutual_info_score as nmi
    D = pd.read_csv(PROC / "seso_doc_topics.csv.gz", usecols=["id", "created_utc", "topic", "topic_before_outlier_fix"])
    runs = {REF: D.set_index("id")[["topic", "topic_before_outlier_fix"]]}
    for f in sorted(SEEDS_DIR.glob("seso_seed*_doc_topics.csv.gz")):
        runs[int(f.name[9:].split("_")[0])] = pd.read_csv(f).set_index("id")[["topic", "topic_before_outlier_fix"]]
    ids = D.id.values; seeds = sorted(runs)
    lab = {s: runs[s].topic.reindex(ids).values for s in seeds}; raw = {s: runs[s].topic_before_outlier_fix.reindex(ids).values for s in seeds}
    per_run = [{"seed": s, "topics": int(len(set(lab[s]))), "outliers": round(float((raw[s] == -1).mean()), 4)} for s in seeds]
    pairs = []
    for a, b in itertools.combinations(seeds, 2):
        both = (raw[a] != -1) & (raw[b] != -1)
        pairs.append({"a": a, "b": b, "ami": round(float(ami(lab[a], lab[b])), 3), "nmi": round(float(nmi(lab[a], lab[b])), 3),
                      "ami_confident": round(float(ami(raw[a][both], raw[b][both])), 3), "share_confident": round(float(both.mean()), 3)})
    P = pd.DataFrame(pairs)
    q = lambda c: {"mean": round(float(P[c].mean()), 3), "min": round(float(P[c].min()), 3), "max": round(float(P[c].max()), 3)}
    out = {"n_runs": len(seeds), "seeds": seeds, "per_run": per_run, "pairs": len(P), "ami": q("ami"), "nmi": q("nmi"), "ami_confident": q("ami_confident")}
    tf = PROC / THEMES_FILE
    if tf.exists():
        themes = json.loads(tf.read_text())  # {theme: [reference topic ids]}
        ref_theme = pd.Series("other", index=range(len(ids)))
        ref = lab[REF]
        for th, tids in themes.items():
            ref_theme[np.isin(ref, tids)] = th
        post = (D.created_utc >= SPLIT).values; res = {th: [] for th in themes}
        for s in seeds:
            maj = pd.DataFrame({"t": lab[s], "th": ref_theme.values}).groupby("t").th.agg(lambda x: x.value_counts().idxmax())
            th_s = pd.Series(lab[s]).map(maj).values
            for th in themes:
                a, b = (th_s[~post] == th).mean() * 100, (th_s[post] == th).mean() * 100
                res[th].append({"seed": s, "pre": round(float(a), 2), "from": round(float(b), 2), "ratio": round(float(b / a), 2) if a else None})
        out["themes"] = res
    (PROC / "seso_seed_stability.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k not in ("per_run", "themes")}, indent=1))
    print("topics per run:", [r["topics"] for r in per_run])


if __name__ == "__main__":
    if sys.argv[1] == "fit":
        fit([int(s) for s in sys.argv[2:]])
    else:
        summary()
