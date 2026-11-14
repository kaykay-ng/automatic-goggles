"""BERTopic on the agriculture/food speech sample, then: what do trading / neighbouring countries talk ALIKE about?
EXPLORATORY (not pre-declared). Run from final_project/ with the NLP environment:
  ./.venv-nlp/bin/python notebooks/b_topics.py fit        # topic model + topic table to READ and label
  ./.venv-nlp/bin/python notebooks/b_topics.py analyze    # topic profiles per country, similarity, trade link per topic
Week 7 recipe: reuse the precomputed all-MiniLM-L6-v2 speech vectors; UMAP(5 dims, cosine, seed 42) + HDBSCAN; c-TF-IDF topic words with a
stop-word list that also drops names (mostly-capitalised words) and procedural words, otherwise topics come back as names/'the, and, of'.
"""
import re, sys, glob
from collections import Counter
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))

PROC = Path("data/processed")
PROCEDURAL = set("""mr mrs ms madam madame president vice minister ministers member members honourable hon gentleman gentlemen lady lord lords
chamber commissioner rapporteur committee thank thanks think said say says would could also like one two many much just really want need
government parliament house question answer speaker colleagues dear ladies""".split())


def proper_nouns(texts):
    low, cap = Counter(), Counter()
    for t in texts:
        for w in re.findall(r"[A-Za-z][A-Za-z'-]+", t):
            (cap if w[0].isupper() else low)[w.lower()] += 1
    return {w for w, c in cap.items() if c >= 5 and c / (c + low.get(w, 0)) > 0.6}


def fit():
    from bertopic import BERTopic
    from umap import UMAP
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS
    pool = pd.read_csv(PROC / "b_pool.csv.gz", usecols=["country", "speech_id", "text"])
    V = np.load(PROC / "b_speech_vectors.npy")
    prop = proper_nouns(pool.text)
    print("proper-noun-like words removed:", len(prop))
    stop = list(ENGLISH_STOP_WORDS | prop | PROCEDURAL)
    tm = BERTopic(
        umap_model=UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=42),
        hdbscan_model=HDBSCAN(min_cluster_size=80, min_samples=10, metric="euclidean", cluster_selection_method="eom", prediction_data=True),
        vectorizer_model=CountVectorizer(stop_words=stop, min_df=10, ngram_range=(1, 2)),
        calculate_probabilities=False, verbose=False)
    topics, _ = tm.fit_transform(pool.text.tolist(), embeddings=V)
    topics = np.array(topics)
    print("topics found:", len(set(topics)) - (1 if -1 in topics else 0), "| outliers (topic -1):", int((topics == -1).sum()), "of", len(topics))
    new = tm.reduce_outliers(pool.text.tolist(), topics.tolist(), strategy="embeddings", embeddings=V)
    tm.update_topics(pool.text.tolist(), topics=new, vectorizer_model=CountVectorizer(stop_words=stop, min_df=10, ngram_range=(1, 2)))
    new = np.array(new)
    pd.DataFrame({"speech_id": pool.speech_id, "country": pool.country, "topic": new, "topic_before_outlier_fix": topics}).to_csv(
        PROC / "b_speech_topics.csv.gz", index=False)
    info = tm.get_topic_info()
    rows = []
    for t in info.Topic:
        if t == -1:
            continue
        words = ", ".join(w for w, _ in tm.get_topic(t)[:10])
        rows.append((t, int((new == t).sum()), words))
    T = pd.DataFrame(rows, columns=["topic", "n_speeches", "top_words"])
    T.to_csv(PROC / "b_topics_info.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 140)
    print(T.to_string(index=False))


KEEP = [9, 44, 82, 59, 69, 7, 19, 56, 61, 70, 3, 38, 26, 1, 71, 25, 68, 74, 83, 63, 29, 37, 39, 46, 52, 58, 85,
        20, 23, 43, 6, 8, 5, 57, 84, 34, 41, 0, 78, 73]            # fixed in PLAN.md before any topic-level trade result


def analyze():
    import b_language_network as B
    from b_language_network import NODES, IU, RNG
    pool = pd.read_csv(PROC / "b_pool.csv.gz", usecols=["country", "speech_id", "date", "text"])
    V = np.load(PROC / "b_speech_vectors.npy")
    st = pd.read_csv(PROC / "b_speech_topics.csv.gz")
    assert (st.speech_id.values == pool.speech_id.values).all()
    topic = st.topic.values; cc = pool.country.values
    info = pd.read_csv(PROC / "b_topics_info.csv").set_index("topic")
    keep = np.isin(topic, KEEP)
    print(f"kept {keep.sum()} of {len(keep)} speeches ({keep.mean():.0%}) in {len(KEEP)} topics")
    k = pd.Series(keep).groupby(cc).agg(["sum", "size"]); k["share"] = k["sum"] / k["size"]
    print("kept share per country:", {c: f"{r['sum']}/{r['size']}" for c, r in k.iterrows()})
    # (0) are the dropped topics country-style? share of each topic from its biggest country
    top = pd.crosstab(topic, cc); frac = (top.max(axis=1) / top.sum(axis=1)); who = top.idxmax(axis=1)
    cs = frac[frac > 0.6].sort_values(ascending=False)
    print(f"\ntopics where >60% of speeches come from ONE country: {len(cs)} (kept: {sum(int(t) in KEEP for t in cs.index)})")
    print("   " + ", ".join(f"{int(t)}:{who[t]} {v:.0%}{'*' if int(t) in KEEP else ''}" for t, v in cs.items()), " (* = in keep-list)")

    # (a) primary test restricted to kept-topic speeches
    Sfull = np.load(PROC / "b_language_similarity.npy")
    C = B.country_vectors(V, cc, keep); S = B.sim_matrix(C)
    iu = IU
    print(f"\n(a) similarity from kept-topic speeches only vs similarity from all speeches: Mantel r = {np.corrcoef(S[iu], Sfull[iu])[0,1]:.2f}")
    names, X = B.design(B.dyad_matrices())
    out, r2 = B.dsp_mrqap(S, names, X, n_perm=5000)
    print(f"    PRIMARY MODEL re-run on kept-topic speeches (R^2={r2:.3f}):")
    for nm, b, bo, p in out:
        print(f"      {nm:18s} beta={b:+.3f}  p={p:.4f}")
    np.save(PROC / "b_language_similarity_kept.npy", S)

    # (c) topic-profile similarity (second language measure)
    kt = [t for t in KEEP]
    share = pd.DataFrame({t: pd.Series(((topic == t) & keep)).groupby(cc).sum() for t in kt}).reindex(NODES)
    share = share.div(share.sum(axis=1), axis=0)
    Pm = share.values
    BC = np.array([[np.minimum(Pm[i], Pm[j]).sum() for j in range(len(NODES))] for i in range(len(NODES))])
    print(f"\n(c) topic-profile overlap (Bray-Curtis similarity, 40 kept topics): correlation with embedding similarity {np.corrcoef(BC[iu], Sfull[iu])[0,1]:.2f} (all) / {np.corrcoef(BC[iu], S[iu])[0,1]:.2f} (kept)")
    out2, r22 = B.dsp_mrqap(BC, names, X, n_perm=5000)
    print(f"    topic-profile overlap ~ trade + controls (R^2={r22:.3f}):")
    for nm, b, bo, p in out2:
        print(f"      {nm:18s} beta={b:+.3f}  p={p:.4f}")

    # (b) per-topic: which topics' overlap rises with trade?
    print("\n(b) per-topic overlap min(share_i, share_j) ~ log trade + controls (DSP p, 1,000 perms; Holm over 40):")
    rows = []
    Xs = (X - X.mean(0)) / X.std(0)
    for j, t in enumerate(kt):
        M = np.minimum.outer(Pm[:, j], Pm[:, j])
        yv = M[iu]; ysd = (yv - yv.mean()) / (yv.std() + 1e-12)
        oth = np.column_stack([np.ones(len(ysd)), Xs[:, 1:]])
        xr = Xs[:, 0] - oth @ np.linalg.lstsq(oth, Xs[:, 0], rcond=None)[0]
        b = (xr @ ysd) / (xr @ xr); bp = []
        for _ in range(1000):
            p_ = RNG.permutation(len(NODES)); v = (M[p_][:, p_])[iu]; v = (v - v.mean()) / (v.std() + 1e-12)
            bp.append((xr @ v) / (xr @ xr))
        rows.append((t, b, (1 + (np.abs(bp) >= abs(b)).sum()) / 1001, float(Pm[:, j].mean())))
    R = pd.DataFrame(rows, columns=["topic", "beta_trade", "p", "mean_share"]).sort_values("p")
    ps = R.p.values; order = np.argsort(ps); adj = np.empty(len(ps)); run = 0
    for rank, i in enumerate(order):
        run = max(run, (len(ps) - rank) * ps[i]); adj[i] = min(run, 1)
    R["p_holm"] = adj[np.argsort(order)] if False else pd.Series(adj, index=R.index).values
    R["words"] = [info.loc[t, "top_words"][:60] for t in R.topic]
    print(R.round(3).head(12).to_string(index=False))
    print("   topics with beta_trade < 0 (more trade, LESS shared attention):", int((R.beta_trade < 0).sum()), "of", len(R))
    R.to_csv(PROC / "b_topic_trade_overlap.csv", index=False)

    # (d) regional drivers: where is each kept topic over-represented?
    from gravity_null import REGION
    reg = pd.Series({c: REGION[c] for c in NODES})
    sh = share.copy(); sh["region"] = reg
    mean_by_region = sh.groupby("region").mean()
    print("\n(d) for each region, the 4 kept topics most over-represented relative to the overall mean share:")
    overall = share.mean()
    for r in mean_by_region.index:
        d = (mean_by_region.loc[r] / overall).sort_values(ascending=False).head(4)
        print(f"   {r:5s}: " + "; ".join(f"{int(t)} ({info.loc[int(t), 'top_words'].split(',')[0]}, x{v:.1f})" for t, v in d.items()))

    # sampling sheet for hand review (kept AND dropped topics)
    rng = np.random.default_rng(11); rows = []
    for t in sorted(set(topic)):
        idx = np.where(topic == t)[0]; pick = rng.choice(idx, min(4, len(idx)), replace=False)
        for i in pick:
            rows.append(dict(topic=t, kept=t in KEEP, top_words=info.loc[t, "top_words"][:70], country=cc[i], date=pool.date[i][:7],
                             excerpt=pool.text[i][:450].replace("\n", " "), your_label=""))
    pd.DataFrame(rows).to_csv(PROC / "b_topic_samples.csv", index=False)
    print("\nwrote data/processed/b_topic_samples.csv (4 random speeches per topic; column your_label empty for manual review)")


if __name__ == "__main__":
    {"fit": fit, "analyze": analyze}[sys.argv[1]]()
