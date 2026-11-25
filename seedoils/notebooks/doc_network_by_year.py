"""Topics as communities of a document network, year by year (a network-science view of the topic structure, next to BERTopic).
For each year, a random sample of N_DOC topic-model documents (comments of 15+ words and self-posts, r/StopEatingSeedOils; equal sizes so years are comparable) becomes a network:
nodes = documents, each document linked to its K_NN most similar documents (cosine of the MiniLM embeddings), symmetrised, weights = similarity. Louvain (resolution 1) finds communities = data-driven topics for that year.
Per year (3 samples each): number of communities, how many hold >= 1% of the documents, modularity, share of documents in the 5 biggest, normalised entropy of community sizes; agreement with BERTopic's topic of the same documents (AMI);
and, from the first sample of each year, communities are matched to the previous year by the cosine of their embedding centroids (best match < MATCH_MIN = 'new' community) with the dominant BERTopic topics named.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python seedoils/notebooks/doc_network_by_year.py   (aggregates only)"""
import numpy as np
import pandas as pd
import networkx as nx
from networkx.algorithms.community import louvain_communities, modularity
from sklearn.metrics import adjusted_mutual_info_score as ami

P = "seedoils/data/processed/"; N_DOC = 7000; K_NN = 15; YEARS = [2022, 2023, 2024, 2025]; MATCH_MIN = 0.80; rng = np.random.default_rng(1)
V = np.load(P + "seso_vectors.npy").astype(np.float32); V /= np.linalg.norm(V, axis=1, keepdims=True)
D = pd.read_csv(P + "seso_docs.csv.gz", usecols=["id", "created_utc"], keep_default_na=False); T = pd.read_csv(P + "seso_doc_topics.csv.gz", usecols=["id", "topic"]); assert (D.id.values == T.id.values).all()
yr = pd.to_datetime(D.created_utc, unit="s").dt.year.values; bert = T.topic.values; I = pd.read_csv(P + "seso_topics_info.csv").set_index("topic")
lab = lambda t: ", ".join(I.loc[t, "top_words"].split(", ")[:3])


def knn_graph(X, k):
    S = X @ X.T; np.fill_diagonal(S, -1); nb = np.argpartition(-S, k, axis=1)[:, :k]; G = nx.Graph(); G.add_nodes_from(range(len(X)))
    for i in range(len(X)):
        for j in nb[i]: G.add_edge(i, int(j), weight=float(S[i, j]))
    return G


def run(idx, seed):
    G = knn_graph(V[idx], K_NN); comms = louvain_communities(G, weight="weight", seed=seed); lab_ = np.zeros(len(idx), int)
    for c, s in enumerate(comms): lab_[list(s)] = c
    return lab_, modularity(G, comms, weight="weight")


def summary(lab_, q, b):
    sz = np.bincount(lab_); share = np.sort(sz)[::-1] / sz.sum(); p = sz[sz > 0] / sz.sum()
    return {"communities": len(sz), "ge1pct": int((share >= .01).sum()), "modularity": q, "top5": float(share[:5].sum()), "entropy": float(-(p * np.log(p)).sum() / np.log(len(p))), "ami_bertopic": float(ami(lab_, b))}


rows = []; first = {}
for y in YEARS:
    pool = np.where(yr == y)[0]; n = min(N_DOC, len(pool))
    for s in range(3):
        idx = rng.choice(pool, n, replace=False); lab_, q = run(idx, s); r = summary(lab_, q, bert[idx]); r.update({"year": y, "sample": s, "n": n}); rows.append(r)
        if s == 0: first[y] = (idx, lab_)
R = pd.DataFrame(rows); out = R.groupby("year")[["communities", "ge1pct", "modularity", "top5", "entropy", "ami_bertopic"]].agg(["mean", "std"]).round(3)
print(f"equal samples of {N_DOC} documents per year, k = {K_NN}, 3 samples per year (mean and std):"); print(out.to_string())
print("\ndocuments available per year:", {y: int((yr == y).sum()) for y in YEARS})
cent = {y: {c: V[idx[lab_ == c]].mean(0) for c in np.unique(lab_) if (lab_ == c).sum() >= .01 * len(idx)} for y, (idx, lab_) in first.items()}
cent = {y: {c: v / np.linalg.norm(v) for c, v in d.items()} for y, d in cent.items()}
for y in YEARS[1:]:
    idx, lab_ = first[y]; prev = cent[y - 1]; pk = list(prev); pm = np.stack([prev[c] for c in pk]); print(f"\n== {y}: communities of >= 1% of documents, matched to {y - 1} (cosine of centroids)")
    rows = []
    for c, v in cent[y].items():
        s = pm @ v; j = int(np.argmax(s)); m = lab_ == c; tops = pd.Series(bert[idx[m]]).value_counts(normalize=True).head(2)
        rows.append((m.mean() * 100, float(s[j]), "; ".join(f"[{t}] {lab(t)} {p:.0%}" for t, p in tops.items())))
    for share, s, desc in sorted(rows, key=lambda r: r[1]): print(f"  {share:4.1f}% of docs | best match {s:.2f} {'NEW' if s < MATCH_MIN else '   '} | {desc}")
    print(f"  communities with no match >= {MATCH_MIN}: {sum(r[1] < MATCH_MIN for r in rows)} of {len(rows)}; their share of documents {sum(r[0] for r in rows if r[1] < MATCH_MIN):.1f}%")
