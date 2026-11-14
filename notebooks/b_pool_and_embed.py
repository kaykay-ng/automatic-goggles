"""Angle B step 1: build the agriculture/food speech sample and embed it (week 7 recipe).

Run from final_project/ with the NLP environment:  ./.venv-nlp/bin/python notebooks/b_pool_and_embed.py
Pool: substantive (>=50 words), non-chair speeches 2015-2022 matching AGRI or FOOD (text taken from flagged_XX.csv.gz, so speeches that
only mention 'livestock'/'cattle' are missed). Up to N_MAX random speeches per country (seed 7).
Embedding: sentence-transformers all-MiniLM-L6-v2 (max_seq_length 256). Speeches are cut into passages of <=180 words on sentence
boundaries, each passage embedded (normalised), passage vectors averaged and re-normalised = speech vector.
Writes data/processed/b_pool.csv.gz (ids, metadata, text) and data/processed/b_speech_vectors.npy (row-aligned).
"""
import glob, re, sys, time
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from split_topics_patterns import AGRI, FOOD

PM = Path("data/processed/parlamint"); PROC = Path("data/processed")
N_MAX, SEED = 1500, 7
MODEL = "all-MiniLM-L6-v2"


def passages(text, max_words=180):
    out, cur, n = [], [], 0
    for sent in re.split(r"(?<=[.!?])\s+", text):
        w = len(sent.split())
        if cur and n + w > max_words:
            out.append(" ".join(cur)); cur, n = [], 0
        cur.append(sent); n += w
    if cur:
        out.append(" ".join(cur))
    return out


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    parts = []
    for f in sorted(glob.glob(str(PM / "flagged_*.csv.gz"))):
        d = pd.read_csv(f, usecols=["country", "speech_id", "date", "role", "party", "orientation", "words", "text"])
        d = d[(d.words >= 50) & (d.role != "Chairperson")]
        hit = d.text.fillna("").map(lambda t: bool(AGRI.search(t) or FOOD.search(t)))
        d = d[hit]
        n_all = len(d)
        d = d.sample(min(N_MAX, n_all), random_state=int(rng.integers(1e9)))
        d["pool_size"] = n_all
        parts.append(d)
        print(f"{d.country.iloc[0]}: pool {n_all:6d} -> sampled {len(d)}", flush=True)
    pool = pd.concat(parts, ignore_index=True)
    pool.to_csv(PROC / "b_pool.csv.gz", index=False)
    print("total speeches:", len(pool))

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL, device="mps")
    print("model:", MODEL, "| max_seq_length:", model.max_seq_length, "| dim:", model.get_sentence_embedding_dimension())
    chunks, owner = [], []
    for i, t in enumerate(pool.text):
        for p in passages(t):
            chunks.append(p); owner.append(i)
    owner = np.array(owner)
    print("passages:", len(chunks), "| mean passages per speech:", round(len(chunks) / len(pool), 2))
    t0 = time.time()
    E = model.encode(chunks, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
    print(f"encoded in {time.time()-t0:.0f}s")
    V = np.zeros((len(pool), E.shape[1]), dtype=np.float32)
    np.add.at(V, owner, E)
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    np.save(PROC / "b_speech_vectors.npy", V)
    print("saved vectors", V.shape)
