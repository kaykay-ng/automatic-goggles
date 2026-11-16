"""Mixed product network across departments (groceries + 7 Amazon departments), linked by shared pseudonymous reviewers. Design and H6 in upf/PLAN.md 'MIXED PRODUCT NETWORK'.
Run from final_project/ with the NLP env:
  ./.venv-nlp/bin/python upf/notebooks/mixed_network.py collect   # (user, product, department) pairs for our reviewers + sampled review text (cached, gitignored)
  ./.venv-nlp/bin/python upf/notebooks/mixed_network.py build     # backbone, communities, labels, bridges, H6
"""
import gzip, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
sys.path.insert(0, str(Path(__file__).parent))
import sold_on_joy as S

PROC = Path("upf/data/processed"); CACHE = PROC / "soj"; RAW = Path("upf/data/raw/amazon"); RNG = np.random.default_rng(616)
DEPTS = ["Video_Games", "Toys_and_Games", "Sports_and_Outdoors", "Health_and_Household", "Baby_Products", "Pet_Supplies", "Health_and_Personal_Care"]
MAXTXT = 12                                                         # review texts kept per product (for community labels)


def collect():
    pr = pd.read_csv(CACHE / "reviewer_pairs.csv.gz").drop_duplicates()
    k = pr.groupby("user_id").size(); users = set(k[(k >= 2) & (k <= 50)].index)
    rows, txt, ntxt = [], defaultdict(list), Counter()
    for d in DEPTS:
        n0 = len(rows)
        with gzip.open(RAW / "other" / f"{d}.jsonl.gz", "rt") as f:
            for line in f:
                i = line.find('"user_id": "'); uid = line[i + 12: line.find('"', i + 12)]
                if uid not in users: continue
                r = json.loads(line); a = r.get("parent_asin"); rows.append((uid, a, d))
                if ntxt[a] < MAXTXT and RNG.random() < 0.5:
                    txt[a].append(((r.get("title") or "") + ". " + (r.get("text") or ""))[:600]); ntxt[a] += 1
        print(f"  {d:26s}: {len(rows) - n0:,} reviews by our reviewers", flush=True)
    gro = pr[pr.user_id.isin(users)].assign(dept="Grocery")[["user_id", "parent_asin", "dept"]]
    A = pd.concat([pd.DataFrame(rows, columns=["user_id", "parent_asin", "dept"]), gro]).drop_duplicates(["user_id", "parent_asin"])
    A.to_csv(CACHE / "mixed_pairs.csv.gz", index=False)
    # grocery review text sample for labels
    keep = set(gro.parent_asin)
    with gzip.open(RAW / "Grocery_and_Gourmet_Food.jsonl.gz", "rt") as f:
        for line in f:
            i = line.find('"parent_asin": "'); a = line[i + 16: line.find('"', i + 16)]
            if a in keep and ntxt[a] < MAXTXT and RNG.random() < 0.3:
                r = json.loads(line); txt[a].append(((r.get("title") or "") + ". " + (r.get("text") or ""))[:600]); ntxt[a] += 1
    pd.DataFrame([(a, t) for a, ts in txt.items() for t in ts], columns=["parent_asin", "text"]).to_csv(CACHE / "mixed_texts.csv.gz", index=False)
    print(f"pairs {len(A):,}; reviewers {A.user_id.nunique():,}; products {A.parent_asin.nunique():,}; by dept: {A.dept.value_counts().to_dict()}")


def build():
    from scipy import sparse
    from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS
    A = pd.read_csv(CACHE / "mixed_pairs.csv.gz")
    nondept = A[A.dept != "Grocery"].groupby("user_id").size(); power = set(nondept[nondept > 200].index)
    A = A[~A.user_id.isin(power)]
    pc = A.groupby("parent_asin").user_id.nunique(); A = A[A.parent_asin.isin(pc[pc >= 10].index)]
    print(f"after filters: reviewers {A.user_id.nunique():,} (dropped {len(power):,} power reviewers); products {A.parent_asin.nunique():,}; {A.dept.value_counts().to_dict()}")
    ui = pd.factorize(A.user_id)[0]; pi, items = pd.factorize(A.parent_asin)
    dept = A.drop_duplicates("parent_asin").set_index("parent_asin").dept.loc[items].values
    B = sparse.csr_matrix((np.ones(len(A), np.float32), (ui, pi)), shape=(ui.max() + 1, len(items)))
    W = sparse.triu(B.T @ B, k=1).tocoo(); i, j, w = W.row, W.col, W.data.astype(float)
    s = np.bincount(i, w, len(items)) + np.bincount(j, w, len(items)); dg = np.bincount(i, minlength=len(items)) + np.bincount(j, minlength=len(items))
    keep = ((1 - w / s[i]) ** (dg[i] - 1) < 0.01) | ((1 - w / s[j]) ** (dg[j] - 1) < 0.01)
    G = nx.Graph(); G.add_weighted_edges_from(zip(i[keep].tolist(), j[keep].tolist(), w[keep].tolist()))
    H = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    print(f"co-review pairs {W.nnz:,}; backbone edges {G.number_of_edges():,}; largest component {H.number_of_nodes():,} products, {H.number_of_edges():,} links")
    P = pd.read_csv(CACHE / "products.csv.gz", usecols=["parent_asin", "nova", "category", "title"]).drop_duplicates("parent_asin").set_index("parent_asin")
    nodes = list(H.nodes()); asin = items[nodes]; dep = dept[nodes]
    nova = np.array([P.nova.get(a, np.nan) for a in asin]); gcat = np.array([P.category.get(a, "") if d == "Grocery" else "" for a, d in zip(asin, dep)], dtype=object)
    idx = {n: k for k, n in enumerate(nodes)}
    # department mixing
    e = np.array([(idx[a], idx[b]) for a, b in H.edges()]); same = np.mean(dep[e[:, 0]] == dep[e[:, 1]])
    print(f"links within the same department: {same:.0%}; product counts: {pd.Series(dep).value_counts().to_dict()}")
    comm = sorted(nx.community.louvain_communities(H, weight="weight", seed=7), key=len, reverse=True); lab = np.zeros(len(nodes), int)
    for c, m in enumerate(comm):
        for n in m: lab[idx[n]] = c
    print(f"Louvain: {len(comm)} communities, modularity {nx.community.modularity(H, comm, weight='weight'):.3f}; sizes {[len(c) for c in comm[:12]]}")
    T = pd.read_csv(CACHE / "mixed_texts.csv.gz"); T = T[T.parent_asin.isin(set(asin))]
    a2c = dict(zip(asin, lab)); T["c"] = T.parent_asin.map(a2c)
    docs = T.groupby("c").text.apply(lambda x: " ".join(x)); stop = list(ENGLISH_STOP_WORDS | {"br", "product", "love", "great", "good", "like", "just", "really", "use", "used", "bought", "buy", "amazon", "item", "price", "works", "work", "time", "nice", "best", "little", "dont", "does", "did", "got"})
    cv = CountVectorizer(stop_words=stop, min_df=2, token_pattern=r"(?u)\b[a-z][a-z]{2,}\b"); X = cv.fit_transform(docs.values).astype(float)
    tf = X.multiply(1 / X.sum(1)); idf = np.log(1 + X.shape[0] / (np.asarray((X > 0).sum(0)).ravel() + 1)); ctf = tf.multiply(idf).tocsr(); vocab = np.array(cv.get_feature_names_out())
    rows = []
    for c in range(min(len(comm), 14)):
        m = lab == c; dd = pd.Series(dep[m]).value_counts(normalize=True); g = m & (dep == "Grocery")
        words = ", ".join(vocab[np.argsort(-ctf[list(docs.index).index(c)].toarray().ravel())[:10]]) if c in docs.index else ""
        rows.append((c, int(m.sum()), "; ".join(f"{k} {v:.0%}" for k, v in dd.head(3).items()), int(g.sum()), np.nanmean(nova[g] == 4) if g.sum() else np.nan, words))
    C = pd.DataFrame(rows, columns=["community", "products", "top departments", "groceries", "NOVA4 share of groceries", "c-TF-IDF words"])
    pd.set_option("display.width", 250, "display.max_colwidth", 120); print(C.round(2).to_string(index=False)); C.to_csv(PROC / "mixed_communities.csv", index=False)
    btw = nx.betweenness_centrality(H, k=min(500, len(nodes)), seed=3); top = sorted(btw, key=btw.get, reverse=True)[:12]
    print("bridges (betweenness): " + "; ".join(f"{dep[idx[n]]}/{(P.title.get(items[n], '') or '')[:35]} {btw[n]:.3f}" for n in top))
    # H6: UPF lean of non-food products
    isg = dep == "Grocery"; u4 = (nova == 4) & isg; gcat_id = pd.factorize(pd.Series(gcat))[0]
    nbr = [np.array([idx[x] for x in H.neighbors(n)]) for n in nodes]
    nf = np.where(~isg)[0]; nf = np.array([k for k in nf if isg[nbr[k]].sum() >= 3])
    grp = np.array(["games/toys" if dep[k] in ("Video_Games", "Toys_and_Games") else "sports/household" if dep[k] in ("Sports_and_Outdoors", "Health_and_Household") else "other" for k in nf])
    def lean(lab4):
        return np.array([lab4[nbr[k][isg[nbr[k]]]].mean() for k in nf])
    def stat(lab4):
        L = lean(lab4); return L[grp == "games/toys"].mean() - L[grp == "sports/household"].mean()
    obs = stat(u4); gi = np.where(isg)[0]; null = []
    for _ in range(2000):
        lb = u4.copy(); lb[gi] = S.shuffle_within(u4[gi], gcat_id[gi]); null.append(stat(lb))
    null = np.array(null); L = lean(u4)
    print(f"\nH6: non-food products with >= 3 grocery neighbours: {len(nf):,} (games/toys {(grp == 'games/toys').sum():,}, sports/household {(grp == 'sports/household').sum():,})")
    print(f"  mean UPF lean: games/toys {L[grp == 'games/toys'].mean():.3f}, sports/household {L[grp == 'sports/household'].mean():.3f}, other {L[grp == 'other'].mean():.3f}; difference {obs:+.3f}; null mean {null.mean():+.3f}; one-sided p = {(1 + (null >= obs).sum()) / 2001:.4f}")
    pd.DataFrame({"parent_asin": asin, "dept": dep, "nova": nova, "community": lab, "x": 0}).to_csv(CACHE / "mixed_nodes.csv.gz", index=False)
    nx.write_edgelist(nx.relabel_nodes(H, {n: items[n] for n in nodes}), CACHE / "mixed_edges.txt", data=["weight"])


if __name__ == "__main__":
    {"collect": collect, "build": build}[sys.argv[1]]()
