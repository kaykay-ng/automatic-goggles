"""H11 sentiment validation, H10 rich-get-richer, and hub products. Pre-declared in upf/PLAN.md 'THREE MORE'.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/habits.py validate | rich | hubs
"""
import gzip, json, re, sys
from collections import Counter
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).parent))

PROC = Path("upf/data/processed"); CACHE = PROC / "soj"; RAW = Path("upf/data/raw/amazon"); FIG = Path("upf/figures"); RNG = np.random.default_rng(3030)


def auc(score, y):
    r = stats.rankdata(score); n1 = y.sum(); n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def validate():
    import elsewhere as E                                   # reuses its VAD + EmoLex + food-word set
    P = pd.read_csv(CACHE / "products.csv.gz", usecols=["parent_asin"]); keep = set(P.parent_asin)
    rows = []
    with gzip.open(RAW / "Grocery_and_Gourmet_Food.jsonl.gz", "rt") as f:
        for line in f:
            i = line.find('"parent_asin": "'); a = line[i + 16: line.find('"', i + 16)]
            if a not in keep or RNG.random() > 0.09: continue
            r = json.loads(line); t = (r.get("title") or "") + ". " + (r.get("text") or "")
            if r.get("rating") is None or len(t.split()) < 3: continue
            rows.append((t, float(r["rating"])))
    D = pd.DataFrame(rows, columns=["text", "stars"]).sample(min(200_000, len(rows)), random_state=1).reset_index(drop=True)
    vv = [E.valence(t) for t in D.text]; D["val"] = [v for v, _ in vv]; D["nval"] = [n for _, n in vv]
    pos = neg = None
    def pn(t):
        p = n = m = 0
        for w in E.TOK.findall(t.lower()):
            w = E.norm(w, E.LEX)
            if w in E.LEX and w not in E.FOOD:
                p += "positive" in E.LEX[w]; n += "negative" in E.LEX[w]
            m += 1
        return (p - n) / max(m, 1)
    D["emolex"] = [pn(t) for t in D.text]
    print(f"reviews {len(D):,}; stars {D.stars.value_counts().sort_index().to_dict()}; with a valence score {D.val.notna().mean():.1%}")
    d = D.dropna(subset=["val"]); y = (d.stars >= 4).astype(int).values; m = (d.stars <= 2) | (d.stars >= 4); yy = (d.stars[m] >= 4).astype(int).values
    print(f"\n== H11 ==\n  Spearman(valence, stars) = {stats.spearmanr(d.val, d.stars)[0]:+.3f}")
    a_v = auc(d.val[m].values, yy); a_e = auc(d.emolex[m].values, yy); a_null = np.mean([auc(d.val[m].values, RNG.permutation(yy)) for _ in range(200)])
    print(f"  AUC 1-2 vs 4-5 stars (n={m.sum():,}): VAD valence {a_v:.3f} | EmoLex pos-neg {a_e:.3f} | shuffled stars {a_null:.3f}   (pre-set bar: >= 0.70)")
    print("  mean valence by stars:", d.groupby("stars").val.mean().round(3).to_dict())
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    t = D[(D.stars <= 2) | (D.stars >= 4)].sample(frac=1, random_state=2); cut = int(0.8 * len(t)); ylab = (t.stars >= 4).astype(int).values
    vec = TfidfVectorizer(min_df=5, ngram_range=(1, 2), max_features=200_000, sublinear_tf=True); Xtr = vec.fit_transform(t.text[:cut]); Xte = vec.transform(t.text[cut:])
    clf = LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced").fit(Xtr, ylab[:cut]); p = clf.predict_proba(Xte)[:, 1]
    print(f"  TF-IDF + logistic regression (held-out 20%, n={len(p):,}): AUC {auc(p, ylab[cut:]):.3f}  (upper benchmark)")
    coef = clf.coef_[0]; names = np.array(vec.get_feature_names_out()); o = np.argsort(coef)
    print("  most negative features:", ", ".join(names[o[:15]])); print("  most positive features:", ", ".join(names[o[::-1][:15]]))
    # where the lexicon fails: 1-2 star reviews it scores most positive
    w = d[d.stars <= 2].sort_values("val", ascending=False).head(6)
    print("  1-2 star reviews with the HIGHEST valence (where the lexicon is fooled):"); [print("    ", round(r.val, 2), "|", r.text[:160].replace("\n", " ")) for r in w.itertuples()]


def rich():
    t0, t1 = pd.Timestamp("2018-01-01").value // 10 ** 6, pd.Timestamp("2019-01-01").value // 10 ** 6
    before, during = Counter(), Counter()
    with gzip.open(RAW / "Grocery_and_Gourmet_Food.jsonl.gz", "rt") as f:
        for line in f:
            i = line.find('"parent_asin": "'); a = line[i + 16: line.find('"', i + 16)]
            j = line.find('"timestamp": '); ts = int(re.match(r"\d+", line[j + 13:]).group(0))
            if ts < t0: before[a] += 1
            elif ts < t1: during[a] += 1
    k0 = pd.Series(before); dk = pd.Series(during).reindex(k0.index).fillna(0)
    total = pd.Series(before) + pd.Series(during).reindex(pd.Series(before).index).fillna(0)
    print(f"products with >= 1 review before 2018: {len(k0):,}; new reviews in 2018 on them: {int(dk.sum()):,}; products with no 2018 review: {(dk == 0).mean():.0%}")
    allc = Counter()
    with gzip.open(RAW / "Grocery_and_Gourmet_Food.jsonl.gz", "rt") as f:
        for line in f:
            i = line.find('"parent_asin": "'); allc[line[i + 16: line.find('"', i + 16)]] += 1
    c = np.array(list(allc.values())); q = [1, 10, 100, 1000, 10000]
    print("review-count distribution (all grocery products): share with >= k reviews: " + ", ".join(f"k={k}: {np.mean(c >= k):.4f}" for k in q) + f"; max {c.max():,}")
    def fit(k, d):
        bins = np.unique(np.round(np.logspace(0, np.log10(k.max() + 1), 25)).astype(int)); idx = np.digitize(k, bins)
        g = pd.DataFrame({"k": k, "d": d, "b": idx}).groupby("b").agg(k=("k", "mean"), d=("d", "mean"), n=("d", "size")); g = g[(g.n >= 20) & (g.d > 0)]
        return np.polyfit(np.log(g.k), np.log(g.d), 1)[0], g
    k = k0.values.astype(float); d = dk.values.astype(float)
    a, g = fit(k, d); boots = []
    for _ in range(1000):
        s = RNG.integers(0, len(k), len(k)); boots.append(fit(k[s], d[s])[0])
    null = RNG.multinomial(int(d.sum()), np.ones(len(k)) / len(k)).astype(float); a0, _ = fit(k, null)
    print(f"\n== H10 == attachment exponent alpha = {a:.3f} (95% CI {np.percentile(boots, 2.5):.3f} to {np.percentile(boots, 97.5):.3f}); uniform-attachment null alpha = {a0:.3f}")
    print("  mean new 2018 reviews by prior reviews:", {int(r.k): round(r.d, 2) for r in g.iloc[::3].itertuples()})
    P = pd.read_csv(CACHE / "products.csv.gz", usecols=["parent_asin", "nova"]).drop_duplicates("parent_asin").set_index("parent_asin").nova
    for nm, sel in [("NOVA 4", P[P == 4].index), ("NOVA 1-3", P[P < 4].index)]:
        m = k0.index.isin(sel); aa, _ = fit(k[m], d[m]); print(f"  exploratory {nm:8s}: products {m.sum():,}, alpha {aa:.3f}")
    pd.DataFrame({"k0": k0, "dk": dk}).to_csv(CACHE / "rich_2018.csv.gz")
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    cc = np.sort(c)[::-1]; ax[0].loglog(cc, np.arange(1, len(cc) + 1) / len(cc), color="#2a78d6", lw=1.5); ax[0].set_xlabel("reviews per product"); ax[0].set_ylabel("share of products with at least this many"); ax[0].set_title("A  Review counts are heavy-tailed", loc="left")
    ax[1].loglog(g.k, g.d, "o", color="#eb6834"); xs = np.array([g.k.min(), g.k.max()]); ax[1].loglog(xs, np.exp(np.polyfit(np.log(g.k), np.log(g.d), 1)[1]) * xs ** a, color="#0b0b0b", lw=1)
    ax[1].set_xlabel("reviews before 2018"); ax[1].set_ylabel("mean new reviews in 2018"); ax[1].set_title(f"B  Rich get richer: alpha = {a:.2f}", loc="left")
    for x in ax: x.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(FIG / "rich_get_richer.png", dpi=160); print("saved upf/figures/rich_get_richer.png")


def hubs():
    import networkx as nx
    G = nx.read_edgelist(CACHE / "mixed_edges.txt", data=[("weight", float)])
    N = pd.read_csv(CACHE / "mixed_nodes.csv.gz").set_index("parent_asin")
    M = pd.read_csv(CACHE / "elsewhere_meta.csv.gz", usecols=["parent_asin", "title"]).drop_duplicates("parent_asin").set_index("parent_asin").title
    Pg = pd.read_csv(CACHE / "products.csv.gz", usecols=["parent_asin", "title"]).drop_duplicates("parent_asin").set_index("parent_asin").title
    name = lambda a: str(M.get(a, Pg.get(a, "?")))[:55]
    pr = nx.pagerank(G, alpha=0.85, weight="weight"); ev = nx.eigenvector_centrality_numpy(G, weight="weight"); deg = dict(G.degree())
    T = pd.DataFrame({"pagerank": pr, "eigen": pd.Series(ev), "degree": pd.Series(deg)}); T["dept"] = N.dept.reindex(T.index); T["nova"] = N.nova.reindex(T.index)
    print(f"network: {G.number_of_nodes():,} products, {G.number_of_edges():,} links")
    print(f"Spearman PageRank vs degree {stats.spearmanr(T.pagerank, T.degree)[0]:+.3f}; eigenvector vs degree {stats.spearmanr(T.eigen, T.degree)[0]:+.3f}")
    for col in ("pagerank", "eigen"):
        top = T.sort_values(col, ascending=False).head(15)
        print(f"\nTOP 15 by {col}:"); [print(f"  {r.dept[:18]:18s} {name(a)}  (degree {int(r.degree)}{', NOVA ' + str(int(r.nova)) if pd.notna(r.nova) else ''})") for a, r in top.iterrows()]
    b = np.polyfit(np.log(T.degree), np.log(T.pagerank), 1); T["resid"] = np.log(T.pagerank) - np.polyval(b, np.log(T.degree))
    print("\nHUBS BEYOND THEIR DEGREE (highest PageRank residual, degree >= 10):")
    for a, r in T[T.degree >= 10].sort_values("resid", ascending=False).head(12).iterrows(): print(f"  {r.dept[:18]:18s} {name(a)}  (degree {int(r.degree)}, residual {r.resid:+.2f})")
    print("\nshare of the top-100 PageRank products by department:", T.sort_values("pagerank", ascending=False).head(100).dept.value_counts().to_dict())
    g = T[T.dept == "Grocery"]; print(f"groceries: top-100 PageRank among groceries, NOVA-4 share {(g.sort_values('pagerank', ascending=False).head(100).nova == 4).mean():.2f} vs all network groceries {(g.nova == 4).mean():.2f}")
    T.to_csv(CACHE / "mixed_hubs.csv.gz")


if __name__ == "__main__":
    {"validate": validate, "rich": rich, "hubs": hubs}[sys.argv[1]]()
