"""MARKETING WORD NETWORK (pre-declared W1 in upf/PLAN.md, 18 Nov). Split-half: word lean from half A, co-occurrence network (PPMI) from half B.
Writes data/processed/word_network.txt, soj/word_nodes.csv, soj/word_edges.csv.gz.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/word_network.py
"""
import re, sys
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
from scipy import sparse
from sklearn.metrics import adjusted_rand_score
sys.path.insert(0, "upf/notebooks")
import sold_on_joy as SJ

PROC = Path("upf/data/processed"); C = PROC / "soj"; OUT = PROC / "word_network.txt"; RNG = np.random.default_rng(1918)
log = []
def say(s=""): print(s, flush=True); log.append(s)

P = pd.read_csv(C / "products.csv.gz", usecols=["parent_asin", "nova", "category"])
M = pd.read_csv(PROC / "amazon_meta_compact.csv.gz", usecols=["parent_asin", "features", "description"]).drop_duplicates("parent_asin")
D = P.merge(M, on="parent_asin"); D["text"] = (D.features.fillna("") + " " + D.description.fillna("")).str.strip()
D = D[D.text.str.split().str.len() >= 10]; D["u"] = D.nova == 4
c = D.groupby("category").u.agg(["sum", "size"]); cats = c[(c["sum"] >= 100) & (c["size"] - c["sum"] >= 100)].index
rng = np.random.default_rng(31); parts = []                                                  # identical sample to marketing_wordplot.py
for k in cats:
    s = D[D.category == k]; n = min(int(s.u.sum()), int((~s.u).sum()))
    parts += [s[s.u].sample(n, random_state=int(rng.integers(1e9))), s[~s.u].sample(n, random_state=int(rng.integers(1e9)))]
B = pd.concat(parts).reset_index(drop=True)
_, FOOD = SJ.lexicon()
W = pd.read_csv(PROC / "marketing_wordplot.csv"); vocab = [w for w in W.word if w not in FOOD]
vid = {w: k for k, w in enumerate(vocab)}; tok = re.compile(r"[a-z]+")
rows, cols = [], []
for d, t in enumerate(B.text.str.lower()):
    for w in set(tok.findall(t)):
        k = vid.get(w)
        if k is not None: rows.append(d); cols.append(k)
X = sparse.csr_matrix((np.ones(len(rows), np.float32), (rows, cols)), shape=(len(B), len(vocab)))
say(f"listings {len(B):,} ({B.u.mean():.0%} NOVA 4); words {len(vocab):,} (word-plot vocabulary minus {len(W) - len(vocab)} ingredient words)")
half = RNG.random(len(B)) < 0.5; XA, XB, uA = X[half], X[~half], B.u.values[half]


def logodds(Xh, u):
    a = np.asarray(Xh[u].sum(0)).ravel(); b = np.asarray(Xh[~u].sum(0)).ravel(); pri = (a + b) / (a + b).sum() * 500
    na, nb, n0 = a.sum(), b.sum(), pri.sum()
    d = np.log((a + pri) / (na + n0 - a - pri)) - np.log((b + pri) / (nb + n0 - b - pri)); v = 1 / (a + pri) + 1 / (b + pri); return d / np.sqrt(v)


zA = logodds(XA, uA)
co = (XB.T @ XB).tocoo(); m = co.row < co.col; i, j, n_ab = co.row[m], co.col[m], co.data[m]
nB = np.asarray(XB.sum(0)).ravel(); N = XB.shape[0]
pmi = np.log(n_ab * N / (nB[i] * nB[j])); keep = (n_ab >= 15) & (pmi > 0); i, j, w = i[keep], j[keep], pmi[keep]
say(f"half B: {N:,} listings; links (>= 15 co-occurring listings, PMI > 0): {len(i):,}; words with a link {len(np.unique(np.r_[i, j])):,}")


def wcorr(z):
    a, b = np.r_[z[i], z[j]], np.r_[z[j], z[i]]; ww = np.r_[w, w]; ma = np.average(a, weights=ww)
    return np.average((a - ma) * (b - ma), weights=ww) / np.average((a - ma) ** 2, weights=ww)


obs = wcorr(zA); null = np.array([wcorr(RNG.permutation(zA)) for _ in range(1000)]); p = (1 + (null >= obs).sum()) / 1001
say(f"W1 word-lean assortativity (A-half lean across B-half links): {obs:+.3f} vs null {null.mean():+.3f} (sd {null.std():.3f}), p = {p:.4f}")

G = nx.Graph(); G.add_weighted_edges_from(zip(i.tolist(), j.tolist(), w.tolist()))
com = sorted(nx.community.louvain_communities(G, weight="weight", seed=7, resolution=1.0), key=len, reverse=True)
say(f"Louvain: {len(com)} communities, modularity {nx.community.modularity(G, com, weight='weight'):.3f}; sizes {[len(c) for c in com[:12]]}")
lab = {x: k for k, c in enumerate(com) for x in c}; ks = list(lab); ar = []
for sd in range(5):
    cm = nx.community.louvain_communities(G, weight="weight", seed=70 + sd); cc = {x: k for k, c in enumerate(cm) for x in c}; ar.append(adjusted_rand_score([lab[x] for x in ks], [cc[x] for x in ks]))
say(f"stability over 5 seeds: adjusted Rand {np.mean(ar):.2f} (min {min(ar):.2f})")
strength = dict(G.degree(weight="weight")); freq = np.asarray(X.sum(0)).ravel()
rows_out = []
for k, cset in enumerate(com):
    if len(cset) < 10: continue
    ws = sorted(cset, key=lambda x: -freq[x]); z = zA[list(cset)]
    say(f"\n[W{k + 1}] {len(cset)} words; mean lean {z.mean():+.2f} (+ = ultra-processed); leaning UPF (z>=2) {np.mean(z >= 2):.0%}, leaning less processed (z<=-2) {np.mean(z <= -2):.0%}")
    say("   most used: " + ", ".join(vocab[x] for x in ws[:22]))
    say("   most UPF-leaning: " + ", ".join(vocab[x] for x in np.array(list(cset))[np.argsort(-z)][:8]) + " | most less-processed-leaning: " + ", ".join(vocab[x] for x in np.array(list(cset))[np.argsort(z)][:8]))
nodes = pd.DataFrame({"word": vocab, "z_halfA": zA, "z_full": W.set_index("word").z.reindex(vocab).values, "listings": freq.astype(int), "community": [lab.get(k, -1) for k in range(len(vocab))]})
nodes.to_csv(C / "word_nodes.csv", index=False); pd.DataFrame({"a": [vocab[x] for x in i], "b": [vocab[x] for x in j], "n": n_ab[keep], "pmi": w}).to_csv(C / "word_edges.csv.gz", index=False)
OUT.write_text("\n".join(log) + "\n"); print("saved", OUT)
