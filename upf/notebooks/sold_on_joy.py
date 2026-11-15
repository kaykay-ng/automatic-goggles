"""Story v1 'Sold on joy?' -- pre-declared tests H1-H4 (upf/PLAN.md 'STORY v1'). Run from final_project/ with the NLP env:
  ./.venv-nlp/bin/python upf/notebooks/sold_on_joy.py build    # products + marketing emotions + review emotions + reviewer pairs (cached, gitignored)
  ./.venv-nlp/bin/python upf/notebooks/sold_on_joy.py test     # H1-H4, Holm, robustness
Implementation choices fixed BEFORE results (not spelled out in the pre-declaration): emotion share = emotion-word tokens / all word tokens of the document;
'joy + anticipation' counts a token once if it carries either; H3 uses products with marketing text and >= 5 reviews; products without an Open Food Facts category form one group 'none'.
NRC EmoLex (Mohammad & Turney), non-commercial research use, not redistributed. Amazon Reviews 2023 (Hou et al. 2024). Open Food Facts (ODbL).
"""
import gzip, json, re, sys
from collections import defaultdict
from pathlib import Path
import numpy as np, pandas as pd

PROC = Path("upf/data/processed"); RAW = Path("upf/data/raw"); CACHE = PROC / "soj"; CACHE.mkdir(exist_ok=True)
EMO = ["anger", "anticipation", "disgust", "fear", "joy", "sadness", "surprise", "trust", "positive", "negative"]
RNG = np.random.default_rng(2611); NPERM = 5000


def lexicon():
    L = pd.read_csv(RAW / "nrc/NRC-Emotion-Lexicon/NRC-Emotion-Lexicon-Wordlevel-v0.92.txt", sep="\t", names=["w", "e", "v"]); L = L[L.v == 1]
    lex = defaultdict(set)
    for w, e in zip(L.w, L.e): lex[w].add(e)
    food = set()
    for s in pd.read_csv(PROC / "ingredient_nodes.csv").ingredient: food |= set(re.findall(r"[a-z]+", s))
    return lex, food


def score(text, lex, food):
    """returns n_tokens and, per emotion, counts without food words and with all words; plus joy|anticipation union counts"""
    toks = re.findall(r"[a-z']+", text.lower()); n = len(toks); c_nf = dict.fromkeys(EMO, 0); c_all = dict.fromkeys(EMO, 0); ja_nf = ja_all = 0
    for w in toks:
        w = w.strip("'")
        if w not in lex and w.endswith("s") and w[:-1] in lex: w = w[:-1]
        es = lex.get(w)
        if not es: continue
        isfood = w in food
        for e in es:
            c_all[e] += 1
            if not isfood: c_nf[e] += 1
        if "joy" in es or "anticipation" in es:
            ja_all += 1
            if not isfood: ja_nf += 1
    return n, c_nf, c_all, ja_nf, ja_all


def build():
    lex, food = lexicon()
    M = pd.read_csv(PROC / "amazon_meta_compact.csv.gz", dtype={"code13": str}, usecols=["parent_asin", "title", "store", "features", "description", "code13", "nova", "price"])
    M = M[M.nova.notna()].drop_duplicates("parent_asin")
    off = pd.read_csv(PROC / "off_products.csv.gz", usecols=["code", "main_category"], dtype={"code": str}); off["code13"] = off.code.str.lstrip("0").str.zfill(13)
    nm = pd.read_csv(PROC / "off_names_en.csv.gz", usecols=["code", "brands"], dtype={"code": str}); nm["code13"] = nm.code.str.lstrip("0").str.zfill(13)
    M = M.merge(off[["code13", "main_category"]].drop_duplicates("code13"), on="code13", how="left").merge(nm[["code13", "brands"]].drop_duplicates("code13"), on="code13", how="left")
    M["category"] = M.main_category.fillna("none").replace("", "none")
    b = M.brands.fillna("").str.split(",").str[0].str.strip().str.lower()
    hay = (M.title.fillna("") + " " + M.store.fillna("")).str.lower()
    M["brand"] = b; M["high_conf"] = [len(x) >= 3 and x in h for x, h in zip(b, hay)]
    txt = (M.features.fillna("") + " " + M.description.fillna("")).str.strip()
    S = [score(t, lex, food) for t in txt]
    M["m_tokens"] = [s[0] for s in S]
    for e in EMO:
        M[f"m_{e}_nf"] = [s[1][e] for s in S]; M[f"m_{e}_all"] = [s[2][e] for s in S]
    M["m_ja_nf"] = [s[3] for s in S]; M["m_ja_all"] = [s[4] for s in S]
    keep = set(M.parent_asin); agg = defaultdict(lambda: np.zeros(4 + 2 * len(EMO))); pairs = []
    with gzip.open(RAW / "amazon/Grocery_and_Gourmet_Food.jsonl.gz", "rt") as f:
        for k, line in enumerate(f):
            if '"parent_asin"' not in line: continue
            d = json.loads(line); a = d.get("parent_asin")
            if a not in keep: continue
            n, c_nf, c_all, ja_nf, ja_all = score((d.get("title") or "") + " " + (d.get("text") or ""), lex, food)
            v = agg[a]; v[0] += 1; v[1] += n; v[2] += ja_nf; v[3] += ja_all
            for i, e in enumerate(EMO): v[4 + i] += c_nf[e]; v[4 + len(EMO) + i] += c_all[e]
            pairs.append((d.get("user_id"), a))
            if k % 2_000_000 == 0: print(f"  reviews scanned {k:,}; matched kept {len(pairs):,}", flush=True)
    R = pd.DataFrame.from_dict(agg, orient="index", columns=["r_n", "r_tokens", "r_ja_nf", "r_ja_all"] + [f"r_{e}_nf" for e in EMO] + [f"r_{e}_all" for e in EMO])
    M = M.merge(R, left_on="parent_asin", right_index=True, how="left")
    M.drop(columns=["features", "description"]).to_csv(CACHE / "products.csv.gz", index=False)
    pd.DataFrame(pairs, columns=["user_id", "parent_asin"]).to_csv(CACHE / "reviewer_pairs.csv.gz", index=False)
    print(f"products {len(M):,}; with marketing text {(M.m_tokens > 0).sum():,}; with >= 5 reviews {(M.r_n >= 5).sum():,}; high-confidence matches {M.high_conf.mean():.0%}; reviews kept {len(pairs):,}")


def within(df, val, label="u", nperm=NPERM, two_sided=False):
    """product-weighted mean of within-category differences (NOVA 4 minus NOVA 1-3) + permutation p (labels shuffled within category)"""
    g = df.groupby("category")
    ok = g[label].agg(["sum", "size"]); ok = ok[(ok["sum"] >= 100) & (ok["size"] - ok["sum"] >= 100)].index
    d = df[df.category.isin(ok)].sort_values("category").reset_index(drop=True)
    cat = pd.factorize(d.category)[0]; y = d[val].values.astype(float); lab = d[label].values.astype(bool); ncat = cat.max() + 1
    w = np.bincount(cat).astype(float)
    def stat(lb):
        s4 = np.bincount(cat, weights=y * lb, minlength=ncat); n4 = np.bincount(cat, weights=lb.astype(float), minlength=ncat)
        s1 = np.bincount(cat, weights=y * ~lb, minlength=ncat); n1 = np.bincount(cat, weights=(~lb).astype(float), minlength=ncat)
        return float(np.sum(w * (s4 / n4 - s1 / n1)) / w.sum())
    obs = stat(lab); null = np.empty(nperm)
    for k in range(nperm):
        order = np.lexsort((RNG.random(len(lab)), cat)); null[k] = stat(lab[order])
    p = (1 + np.sum(np.abs(null) >= abs(obs))) / (nperm + 1) if two_sided else (1 + np.sum(null >= obs)) / (nperm + 1)
    return obs, p, len(ok), len(d)


def shopper_network(P, nperm=NPERM, subset=None):
    from scipy import sparse
    pr = pd.read_csv(CACHE / "reviewer_pairs.csv.gz").drop_duplicates()
    if subset is not None: pr = pr[pr.parent_asin.isin(subset)]
    k = pr.groupby("user_id").parent_asin.transform("size"); pr = pr[(k >= 2) & (k <= 50)]
    ui = pd.factorize(pr.user_id)[0]; pi, items = pd.factorize(pr.parent_asin)
    B = sparse.csr_matrix((np.ones(len(pr), np.float32), (ui, pi)), shape=(ui.max() + 1, len(items)))
    W = sparse.triu(B.T @ B, k=1).tocoo()
    i, j, wv = W.row, W.col, W.data.astype(float)
    s = np.bincount(i, wv, len(items)) + np.bincount(j, wv, len(items)); dg = np.bincount(i, minlength=len(items)) + np.bincount(j, minlength=len(items))
    a_i = (1 - wv / s[i]) ** (dg[i] - 1); a_j = (1 - wv / s[j]) ** (dg[j] - 1); keep = (a_i < 0.01) | (a_j < 0.01)
    i, j = i[keep], j[keep]
    info = P.set_index("parent_asin").loc[items]; lab = (info.nova.values == 4); cat = pd.factorize(info.category.fillna("none"))[0]
    def assort(lb):
        a, b = lb[i].astype(int), lb[j].astype(int); e = np.zeros((2, 2))
        np.add.at(e, (a, b), 1); np.add.at(e, (b, a), 1); e /= e.sum(); ar = e.sum(1); tr = np.trace(e); ss = np.sum(ar ** 2)
        return (tr - ss) / (1 - ss)
    obs = assort(lab); null = np.empty(nperm)
    for k in range(nperm):
        order = np.lexsort((RNG.random(len(lab)), cat)); null[k] = assort(lab[order])
    nodes = len(np.unique(np.r_[i, j]))
    return obs, (1 + np.sum(null >= obs)) / (nperm + 1), float(null.mean()), nodes, len(i), int(W.nnz)


def holm(ps):
    ps = np.asarray(ps); o = np.argsort(ps); adj = np.empty(len(ps)); run = 0
    for r, i in enumerate(o): run = max(run, (len(ps) - r) * ps[i]); adj[i] = min(run, 1)
    return adj


def test():
    P = pd.read_csv(CACHE / "products.csv.gz"); P["u"] = P.nova == 4
    for v in ("nf", "all"):
        P[f"m_ja_share_{v}"] = P[f"m_ja_{v}"] / P.m_tokens.where(P.m_tokens > 0); P[f"m_trust_share_{v}"] = P[f"m_trust_{v}"] / P.m_tokens.where(P.m_tokens > 0)
        P[f"r_ja_share_{v}"] = P[f"r_ja_{v}"] / P.r_tokens.where(P.r_tokens > 0); P[f"gap_{v}"] = P[f"m_ja_share_{v}"] - P[f"r_ja_share_{v}"]
    mk = P[P.m_tokens >= 10]; h3 = P[(P.m_tokens >= 10) & (P.r_n >= 5)]
    print(f"products {len(P):,}; with marketing text >= 10 words {len(mk):,}; with marketing text and >= 5 reviews {len(h3):,}")
    print("mean shares by NOVA (no food words; per 100 words): joy+anticipation in marketing / trust in marketing / joy+anticipation in reviews")
    print((100 * P.groupby("nova")[["m_ja_share_nf", "m_trust_share_nf", "r_ja_share_nf"]].mean()).round(2).to_string())
    res = {}
    res["H1 joy+anticipation in marketing (NOVA4 > 1-3)"] = within(mk, "m_ja_share_nf")
    res["H2 trust in marketing (two-sided)"] = within(mk, "m_trust_share_nf", two_sided=True)
    res["H3 promise-experience gap (NOVA4 larger)"] = within(h3, "gap_nf")
    a, p4, nm, nodes, edges, alle = shopper_network(P)
    res["H4 shopper-network assortativity (> null)"] = (a, p4, None, nodes)
    adj = holm([v[1] for v in res.values()])
    print("\n== PRE-DECLARED TESTS (within-category, 5,000 permutations within category; Holm over 4) ==")
    for (k, v), q in zip(res.items(), adj):
        unit = "" if k.startswith("H4") else " (difference in share; x100 = per 100 words)"
        extra = f"; categories {v[2]}, products {v[3]:,}" if v[2] is not None else f"; network nodes {nodes:,}, backbone edges {edges:,} of {alle:,}; null mean {nm:+.3f}"
        print(f"  {k}: estimate {v[0]:+.5f}{unit}, p = {v[1]:.4f}, Holm p = {q:.4f}{extra}")
    print("\n== ROBUSTNESS ==")
    hc = P[P.high_conf]; one = P.sample(frac=1, random_state=7).drop_duplicates("brand"); one = one[one.brand.fillna("") != ""]
    for nm2, D in [("high-confidence matches", hc), ("one product per brand", one)]:
        m2 = D[D.m_tokens >= 10]; h2 = D[(D.m_tokens >= 10) & (D.r_n >= 5)]
        r1 = within(m2, "m_ja_share_nf", nperm=2000); r2 = within(m2, "m_trust_share_nf", nperm=2000, two_sided=True); r3 = within(h2, "gap_nf", nperm=2000) if len(h2) > 500 else (np.nan, np.nan, 0, 0)
        print(f"  {nm2:24s}: H1 {r1[0]:+.5f} (p {r1[1]:.3f}, {r1[3]:,} products) | H2 {r2[0]:+.5f} (p {r2[1]:.3f}) | H3 {r3[0]:+.5f} (p {r3[1]:.3f}, {r3[3]:,})")
    r1 = within(mk, "m_ja_share_all", nperm=2000); r2 = within(mk, "m_trust_share_all", nperm=2000, two_sided=True); r3 = within(h3, "gap_all", nperm=2000)
    print(f"  {'ALL words (incl. food)':24s}: H1 {r1[0]:+.5f} (p {r1[1]:.3f}) | H2 {r2[0]:+.5f} (p {r2[1]:.3f}) | H3 {r3[0]:+.5f} (p {r3[1]:.3f})")
    a2, p2, n2, nd2, e2, _ = shopper_network(P, nperm=2000, subset=set(hc.parent_asin))
    print(f"  H4 on high-confidence matches: assortativity {a2:+.3f} (null {n2:+.3f}), p {p2:.4f}, nodes {nd2:,}, edges {e2:,}")
    print("  NOVA gradient (mean per 100 words, no food words):"); print((100 * mk.groupby("nova")[["m_ja_share_nf", "m_trust_share_nf"]].mean()).round(2).T.to_string())
    print("  " + (100 * h3.groupby("nova")["gap_nf"].mean()).round(2).to_string().replace("\n", " | "))


if __name__ == "__main__":
    {"build": build, "test": test}[sys.argv[1]]()
