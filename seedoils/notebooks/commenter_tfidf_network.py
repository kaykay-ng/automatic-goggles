"""Are the 12 commenter communities an artefact of BERTopic? (user question 25 Nov). Rebuilds the commenter similarity network of
commenter_topic_network_130.py with the SAME people (r/StopEatingSeedOils commenters with >= 10 topic-model comments), the SAME comments, the
SAME backbone (disparity filter, alpha 0.05) and the SAME Louvain settings (20 seeds, resolution 1), but each person's profile is the TF-IDF of
their own WORDS (all their comments joined, seedoil_common.bertopic_clean: names merged, absence negation, plural nouns singular; English stop
words + Reddit filler removed; terms used by >= 20 and <= 50% of people; sublinear tf; L2-normalised) instead of their BERTopic topic counts.
Reported: backbone size, modularity, stability across seeds (AMI), agreement with the topic-based communities (AMI, NMI, and a cross-table),
agreement with the quarter of each person's first comment (is it about time instead?), and each word community's most distinctive words
(mean TF-IDF in the community minus overall). Null: the same Louvain on a degree-preserving rewiring of the word backbone, AMI with the topic
communities (what agreement chance gives). Output: data/processed/commenter_tfidf_network.json (aggregates only).
Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/commenter_tfidf_network.py"""
import glob
import gzip
import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from networkx.algorithms.community import louvain_communities, modularity
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics import adjusted_mutual_info_score as ami, normalized_mutual_info_score as nmi

sys.path.insert(0, str(Path(__file__).parent))
from seedoil_common import TOKEN_PATTERN, bertopic_clean, not_bot  # noqa: E402
import seso_topics as st  # noqa: E402  (REDDIT_FILLER)

P = Path("seedoils/data/processed"); MIN_DOCS = 10
ALPHA = float(sys.argv[1]) if len(sys.argv) > 1 else 0.05  # backbone threshold; words give diffuse similarities, so also run looser values
raw = {}
with gzip.open(glob.glob("seedoils/data/raw/*StopEatingSeedOils_comments.jsonl.gz")[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); raw[x["id"]] = (x["author"], int(x["created_utc"]))
first = pd.DataFrame(list(raw.values()), columns=["a", "t"]).groupby("a").t.min()
D = pd.read_csv(P / "seso_doc_topics.csv.gz"); D = D[D.kind == "comment"]; D["a"] = D.id.map(lambda i: raw.get(i, (None,))[0])
D = D[D.a.notna() & (~D.a.isin(["[deleted]", "AutoModerator"]) & not_bot(D.a))]
n_docs = D.groupby("a").size(); users = np.array(sorted(n_docs[n_docs >= MIN_DOCS].index)); D = D[D.a.isin(users)]
TOP = pd.read_csv(P / "commenter_topic_network_130_nodes.csv"); assert len(TOP) == len(users), (len(TOP), len(users))
topic_comm = TOP.community.values
T = pd.read_csv(P / "seso_docs.csv.gz", usecols=["id", "text"], keep_default_na=False).set_index("id").text
text = D.assign(text=D.id.map(T).fillna("")).groupby("a").text.apply(lambda s: " ".join(s)).reindex(users)
print(f"people {len(users):,}; comments {len(D):,}; cleaning text ...", flush=True)
vec = TfidfVectorizer(preprocessor=bertopic_clean, token_pattern=TOKEN_PATTERN, stop_words=list(ENGLISH_STOP_WORDS | st.REDDIT_FILLER),
                      min_df=20, max_df=0.5, sublinear_tf=True, ngram_range=(1, 1))
X = vec.fit_transform(text.values); vocab = np.array(vec.get_feature_names_out()); print(f"vocabulary {len(vocab):,} terms")
S = (X @ X.T).toarray(); np.fill_diagonal(S, 0); S[S < 1e-9] = 0
s = S.sum(1, keepdims=True); k = (S > 0).sum(1, keepdims=True); p = np.divide(S, s, out=np.zeros_like(S), where=s > 0)
keep = (1 - p) ** np.maximum(k - 1, 1) < ALPHA; keep = np.triu(keep | keep.T, 1)
G = nx.Graph(); G.add_nodes_from(range(len(users))); ii, jj = np.where(keep); G.add_weighted_edges_from(zip(ii.tolist(), jj.tolist(), S[ii, jj].tolist()))
H = G.subgraph(max(nx.connected_components(G), key=len)).copy(); nodes = sorted(H.nodes)
runs = [louvain_communities(H, weight="weight", seed=sd) for sd in range(20)]; mods = [modularity(H, c, weight="weight") for c in runs]; ref = int(np.argmax(mods))
lab = lambda c: np.array([next(i for i, s_ in enumerate(sorted(c, key=len, reverse=True)) if v in s_) for v in nodes])  # noqa: E731
labs = [lab(c) for c in runs]; word_comm = labs[ref]
stab = [ami(word_comm, l_) for i, l_ in enumerate(labs) if i != ref]
tc = topic_comm[nodes]
fq = pd.Series(first.reindex(users[nodes]).values).pipe(lambda x: pd.to_datetime(x, unit="s").dt.to_period("Q").astype(str)).values
# null: degree-preserving rewiring of the word backbone, Louvain, agreement with the topic communities
null = []
for r in range(5):
    R = nx.Graph(H); nx.double_edge_swap(R, nswap=R.number_of_edges(), max_tries=R.number_of_edges() * 20, seed=r)
    c = louvain_communities(R, seed=r); m = {v: i for i, s_ in enumerate(c) for v in s_}; null.append(ami([m[v] for v in nodes], tc))
sizes = pd.Series(word_comm).value_counts().sort_index()
ct = pd.crosstab(pd.Series(word_comm, name="word"), pd.Series(tc, name="topic"))
Xd = X[nodes].toarray(); overall = Xd.mean(0)
top_words = {int(c): list(vocab[np.argsort(-(Xd[word_comm == c].mean(0) - overall))[:10]]) for c in sizes.index if sizes[c] >= 30}
best_match = {int(c): {"topic_community": int(ct.loc[c].idxmax()) + 1, "share": round(float(ct.loc[c].max() / ct.loc[c].sum()), 2)} for c in sizes.index if sizes[c] >= 30}
out = {"people": int(len(users)), "vocabulary": int(len(vocab)), "backbone_links": int(keep.sum()), "largest_component": int(len(nodes)),
       "communities": int(len(sizes)), "communities_30plus": int((sizes >= 30).sum()), "sizes": [int(x) for x in sizes.sort_values(ascending=False).values[:15]],
       "modularity_mean": round(float(np.mean(mods)), 3), "stability_ami_across_20_seeds": round(float(np.mean(stab)), 3),
       "ami_vs_topic_communities": round(float(ami(word_comm, tc)), 3), "nmi_vs_topic_communities": round(float(nmi(word_comm, tc)), 3),
       "ami_vs_topic_null_rewired": [round(float(x), 3) for x in null], "ami_vs_first_comment_quarter": round(float(ami(word_comm, fq)), 3),
       "topic_communities_vs_first_comment_quarter": round(float(ami(tc, fq)), 3),
       "word_community_top_words": top_words, "word_community_best_topic_match": best_match,
       "crosstab_word_rows_topic_cols": {int(r): {int(c) + 1: int(v) for c, v in row.items() if v} for r, row in ct.iterrows()}}
out["alpha"] = ALPHA
(P / f"commenter_tfidf_network{'' if ALPHA == 0.05 else '_alpha' + str(ALPHA)}.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k != "crosstab_word_rows_topic_cols"}, indent=1))
