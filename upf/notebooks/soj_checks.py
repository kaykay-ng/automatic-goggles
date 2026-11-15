"""Checks before the 'Sold on joy?' results count as findings (upf/PLAN.md TO DO). Run from final_project/ with the NLP env:
  ./.venv-nlp/bin/python upf/notebooks/soj_checks.py brand     # H4 shopper network: brand confound
  ./.venv-nlp/bin/python upf/notebooks/soj_checks.py words     # which review words drive the emotion differences; sample passages to READ
Brand = Open Food Facts first brand, else the Amazon store field (lowercased).
"""
import gzip, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import sold_on_joy as S

PROC = Path("upf/data/processed"); RAW = Path("upf/data/raw"); CACHE = PROC / "soj"; RNG = np.random.default_rng(77)


def backbone(P):
    from scipy import sparse
    pr = pd.read_csv(CACHE / "reviewer_pairs.csv.gz").drop_duplicates()
    k = pr.groupby("user_id").parent_asin.transform("size"); pr = pr[(k >= 2) & (k <= 50)]
    ui = pd.factorize(pr.user_id)[0]; pi, items = pd.factorize(pr.parent_asin)
    B = sparse.csr_matrix((np.ones(len(pr), np.float32), (ui, pi)), shape=(ui.max() + 1, len(items)))
    W = sparse.triu(B.T @ B, k=1).tocoo(); i, j, w = W.row, W.col, W.data.astype(float)
    s = np.bincount(i, w, len(items)) + np.bincount(j, w, len(items)); dg = np.bincount(i, minlength=len(items)) + np.bincount(j, minlength=len(items))
    keep = ((1 - w / s[i]) ** (dg[i] - 1) < 0.01) | ((1 - w / s[j]) ** (dg[j] - 1) < 0.01)
    info = P.drop_duplicates("parent_asin").set_index("parent_asin").loc[items]
    return i[keep], j[keep], info


def assort(lb, i, j):
    a, b = lb[i].astype(int), lb[j].astype(int); e = np.zeros((2, 2)); np.add.at(e, (a, b), 1); np.add.at(e, (b, a), 1); e /= e.sum()
    ar = e.sum(1); ss = np.sum(ar ** 2); return (np.trace(e) - ss) / (1 - ss)


def null_test(lab, groups, i, j, nperm=2000):
    obs = assort(lab, i, j); null = np.empty(nperm)
    for k in range(nperm):
        null[k] = assort(S.shuffle_within(lab, groups), i, j)      # FIXED 15 Nov (first version shuffled across all products)
    return obs, null.mean(), (1 + np.sum(null >= obs)) / (nperm + 1)


def brand():
    P = pd.read_csv(CACHE / "products.csv.gz")
    i, j, info = backbone(P)
    lab = (info.nova.values == 4)
    br = info.brand.fillna("").astype(str); br = br.where(br.str.len() >= 2, info.store.fillna("").astype(str).str.lower().str.strip())
    br = br.replace("", np.nan); brand_id = pd.factorize(br.fillna(pd.Series([f"_none{x}" for x in range(len(br))], index=br.index)))[0]
    cat = pd.factorize(info.category.fillna("none"))[0]
    same_b = (br.values[i] == br.values[j]) & pd.notna(br.values[i]); same_c = cat[i] == cat[j]
    print(f"backbone edges {len(i):,} among {len(np.unique(np.r_[i, j])):,} products; same-brand edges {same_b.mean():.0%}; same-category edges {same_c.mean():.0%}; products with a brand {br.notna().mean():.0%}")
    rows = [("all edges, null = shuffle within category", lab, cat, i, j),
            ("all edges, null = shuffle within BRAND", lab, brand_id, i, j),
            ("different-brand edges only, null within category", lab, cat, i[~same_b], j[~same_b]),
            ("different brand AND different category, null within category", lab, cat, i[~same_b & ~same_c], j[~same_b & ~same_c])]
    for nm, lb, g, a, b in rows:
        obs, nm_, p = null_test(lb, g, a, b); print(f"  {nm:62s}: assortativity {obs:+.3f}  (null mean {nm_:+.3f}), p = {p:.4f}, edges {len(a):,}")
    print(f"  share NOVA 4 among network products: {lab.mean():.0%}; in the full matched set: {(P.nova == 4).mean():.0%}")


def words():
    lex, food = S.lexicon()
    P = pd.read_csv(CACHE / "products.csv.gz"); nova = dict(zip(P.parent_asin, P.nova)); cat = dict(zip(P.parent_asin, P.category))
    EM = ["anger", "disgust", "fear", "trust"]; cnt = {g: Counter() for g in (4, 1)}; tok = {4: 0, 1: 0}; snippets = defaultdict(list)
    with gzip.open(RAW / "amazon/Grocery_and_Gourmet_Food.jsonl.gz", "rt") as f:
        for line in f:
            d = json.loads(line); a = d.get("parent_asin")
            if a not in nova or RNG.random() > 0.25: continue                       # 25% sample of matched reviews
            g = 4 if nova[a] == 4 else 1; text = (d.get("title") or "") + ". " + (d.get("text") or "")
            ws = re.findall(r"[a-z']+", text.lower()); tok[g] += len(ws)
            for w in ws:
                w = w.strip("'")
                if w not in lex and w.endswith("s") and w[:-1] in lex: w = w[:-1]
                es = lex.get(w)
                if es and w not in food:
                    for e in es:
                        if e in EM: cnt[g][(e, w)] += 1
                    if len(snippets[(g, w)]) < 40 and RNG.random() < 0.05:
                        m = re.search(r"[^.!?]{0,90}\b" + re.escape(w) + r"[a-z']*\b[^.!?]{0,90}", text, flags=re.I)
                        if m: snippets[(g, w)].append((cat.get(a, ""), m.group(0).strip()))
    print(f"review tokens sampled: NOVA 4 {tok[4]:,}; NOVA 1-3 {tok[1]:,}")
    for e in EM:
        rate = lambda g, w: 1e4 * cnt[g][(e, w)] / tok[g]
        ws = {w for (ee, w) in list(cnt[4]) + list(cnt[1]) if ee == e}
        diff = sorted(((rate(4, w) - rate(1, w), w) for w in ws), reverse=(e != "trust"))
        top = diff[:12]
        print(f"\n{e.upper()}: words with the biggest {'excess in NOVA 4' if e != 'trust' else 'excess in NOVA 1-3'} reviews (per 10,000 words, NOVA4 vs NOVA1-3):")
        print("  " + ", ".join(f"{w} {rate(4, w):.1f}/{rate(1, w):.1f}" for _, w in top))
        g = 4 if e != "trust" else 1
        for _, w in top[:4]:
            ex = snippets.get((g, w), [])[:3]
            for c, s in ex: print(f"    [{w} | {c[3:30]}] ...{s[:170]}...")


if __name__ == "__main__":
    if sys.argv[1] in ("brand", "words"): {"brand": brand, "words": words}[sys.argv[1]]()


def valence_words():
    """Which words drive the valence differences (A1). Contribution of word w to the NOVA 4 minus NOVA 1-3 difference in mean valence:
    c_w = v_w * (f4_w - f1_w), with f = share of the group's lexicon-matched non-food tokens that are w (sums exactly to the pooled difference)."""
    _, food = S.lexicon()
    V = pd.read_csv(RAW / "nrc/NRC-VAD-Lexicon-v2.1/Unigrams/unigrams-NRC-VAD-Lexicon-v2.1.txt", sep="\t", keep_default_na=False); val = dict(zip(V.term, V.valence))
    P = pd.read_csv(CACHE / "products.csv.gz"); nova = dict(zip(P.parent_asin, P.nova))
    def norm(w):
        w = w.strip("'")
        return w[:-1] if (w not in val and w.endswith("s") and w[:-1] in val) else w
    def contrib(texts_by_group, label, snip_src):
        cnt = {g: Counter() for g in (4, 1)}
        for g, ts in texts_by_group.items():
            for t in ts:
                for w in re.findall(r"[a-z']+", t.lower()):
                    w = norm(w)
                    if w in val and w not in food: cnt[g][w] += 1
        n = {g: sum(cnt[g].values()) for g in cnt}; mean = {g: sum(val[w] * c for w, c in cnt[g].items()) / n[g] for g in cnt}
        c = sorted(((val[w] * (cnt[4][w] / n[4] - cnt[1][w] / n[1]), w) for w in set(cnt[4]) | set(cnt[1])), reverse=True)
        print(f"\n{label}: mean valence NOVA 4 {mean[4]:+.4f}, NOVA 1-3 {mean[1]:+.4f}, pooled difference {mean[4] - mean[1]:+.4f} (lexicon tokens {n[4]:,} / {n[1]:,})")
        print("  pushing NOVA 4 UP (word valence, rate per 1,000 lexicon words NOVA4/NOVA1-3, contribution):")
        print("   " + "; ".join(f"{w} {val[w]:+.2f} {1e3 * cnt[4][w] / n[4]:.1f}/{1e3 * cnt[1][w] / n[1]:.1f} {x:+.4f}" for x, w in c[:20]))
        print("  pushing NOVA 4 DOWN:")
        print("   " + "; ".join(f"{w} {val[w]:+.2f} {1e3 * cnt[4][w] / n[4]:.1f}/{1e3 * cnt[1][w] / n[1]:.1f} {x:+.4f}" for x, w in c[::-1][:15]))
        top = [w for _, w in c[:6]]
        for w in top:
            ex = [s for s in snip_src.get(w, [])][:2]
            for s in ex: print(f"    [{w}] ...{s[:180]}...")
        return c
    M = pd.read_csv(PROC / "amazon_meta_compact.csv.gz", usecols=["parent_asin", "features", "description"]).drop_duplicates("parent_asin")
    M = M[M.parent_asin.isin(nova)]; M["g"] = np.where(M.parent_asin.map(nova) == 4, 4, 1)
    txt = (M.features.fillna("") + " " + M.description.fillna("")).str.strip()
    groups = {g: txt[M.g == g].tolist() for g in (4, 1)}
    snip = defaultdict(list)
    for t in txt[M.g == 4].sample(frac=0.2, random_state=3):
        for w in set(re.findall(r"[a-z']+", t.lower())):
            if len(snip[w]) < 2:
                m = re.search(r"[^.!?]{0,80}\b" + re.escape(w) + r"\b[^.!?]{0,80}", t, flags=re.I)
                if m: snip[w].append(m.group(0).strip())
    contrib(groups, "MARKETING (features + description)", snip)
    rev = {4: [], 1: []}; rsnip = defaultdict(list)
    with gzip.open(RAW / "amazon/Grocery_and_Gourmet_Food.jsonl.gz", "rt") as f:
        for line in f:
            d = json.loads(line); a = d.get("parent_asin")
            if a not in nova or RNG.random() > 0.15: continue
            g = 4 if nova[a] == 4 else 1; t = (d.get("title") or "") + ". " + (d.get("text") or ""); rev[g].append(t)
    for t in rev[4][:200000]:
        for w in set(re.findall(r"[a-z']+", t.lower())):
            if len(rsnip[w]) < 2 and RNG.random() < 0.02:
                m = re.search(r"[^.!?]{0,80}\b" + re.escape(w) + r"\b[^.!?]{0,80}", t, flags=re.I)
                if m: rsnip[w].append(m.group(0).strip())
    contrib(rev, "REVIEWS (15% sample)", rsnip)


if __name__ == "__main__" and sys.argv[1] == "valence":
    valence_words()
