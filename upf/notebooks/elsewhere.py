"""H8/H9: what else do food shoppers review, how is it marketed, how do they write about it? Pre-declared in upf/PLAN.md 'WHAT ELSE DO FOOD SHOPPERS BUY'.
Run from final_project/ with the NLP env:
  ./.venv-nlp/bin/python upf/notebooks/elsewhere.py build   # stream reviews (group members) + metadata (marketing copy, titles); cached, gitignored
  ./.venv-nlp/bin/python upf/notebooks/elsewhere.py test    # H8, H9, per-department breakdown, emotion words, word plot, community names
Pseudonymous reviewer IDs only; aggregate results. VAD v2.1 / EmoLex (NRC, non-commercial research use, not redistributed).
"""
import gzip, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import sold_on_joy as S

PROC = Path("upf/data/processed"); CACHE = PROC / "soj"; OTHER = Path("upf/data/raw/amazon/other"); RAWN = Path("upf/data/raw/nrc"); FIG = Path("upf/figures")
DEPTS = ["Video_Games", "Toys_and_Games", "Sports_and_Outdoors", "Health_and_Household", "Baby_Products", "Pet_Supplies", "Health_and_Personal_Care"]
EMO = ["anger", "anticipation", "disgust", "fear", "joy", "sadness", "surprise", "trust"]
RNG = np.random.default_rng(808)
V = pd.read_csv(RAWN / "NRC-VAD-Lexicon-v2.1/Unigrams/unigrams-NRC-VAD-Lexicon-v2.1.txt", sep="\t", keep_default_na=False); VAL = dict(zip(V.term, V.valence))
LEX, FOOD = S.lexicon()
TOK = re.compile(r"[a-z']+")


def norm(w, d):
    w = w.strip("'")
    return w[:-1] if (w not in d and w.endswith("s") and w[:-1] in d) else w


def valence(text):
    s = n = 0
    for w in TOK.findall(text.lower()):
        w = norm(w, VAL)
        if w in VAL and w not in FOOD: s += VAL[w]; n += 1
    return (s / n if n else np.nan), n


def build():
    R = pd.read_csv(CACHE / "reviewer_categories.csv.gz", index_col=0, usecols=["user_id", "group", "stratum", "n"])
    R = R[R.group != "between"]; grp = R.group.to_dict()
    rows, emo = [], {g: Counter() for g in ("ALL-UPF", "MOSTLY-NOT")}; tok = Counter(); prod = set()
    for d in DEPTS:
        n0 = len(rows)
        with gzip.open(OTHER / f"{d}.jsonl.gz", "rt") as f:
            for line in f:
                i = line.find('"user_id": "'); uid = line[i + 12: line.find('"', i + 12)]
                g = grp.get(uid)
                if g is None: continue
                r = json.loads(line); text = (r.get("title") or "") + ". " + (r.get("text") or "")
                v, nv = valence(text); a = r.get("parent_asin"); prod.add(a)
                ws = TOK.findall(text.lower()); tok[g] += len(ws)
                for w in ws:
                    w = norm(w, LEX)
                    if w in LEX and w not in FOOD:
                        for e in LEX[w]:
                            if e in EMO: emo[g][(e, w)] += 1
                rows.append((uid, d, a, r.get("rating"), v, nv))
        print(f"  {d:26s}: {len(rows) - n0:,} reviews by the two groups", flush=True)
    pd.DataFrame(rows, columns=["user_id", "dept", "parent_asin", "rating", "r_val", "r_nval"]).to_csv(CACHE / "elsewhere_reviews.csv.gz", index=False)
    pd.DataFrame([(g, e, w, c) for g, C in emo.items() for (e, w), c in C.items()], columns=["group", "emotion", "word", "count"]).to_csv(CACHE / "elsewhere_emotion_words.csv.gz", index=False)
    pd.Series(tok).to_csv(CACHE / "elsewhere_tokens.csv")
    mixed = set(pd.read_csv(CACHE / "mixed_nodes.csv.gz").parent_asin)
    meta = []
    for d in DEPTS:
        with gzip.open(OTHER / f"meta_{d}.jsonl.gz", "rt") as f:
            for line in f:
                i = line.find('"parent_asin": "'); a = line[i + 16: line.find('"', i + 16)]
                if a not in prod and a not in mixed: continue
                m = json.loads(line); copy = (" ".join(m.get("features") or []) + " " + " ".join(x for x in (m.get("description") or []) if x not in ("Description", "Product Description"))).strip()
                v, nv = valence(copy) if len(copy.split()) >= 10 else (np.nan, 0)
                meta.append((a, d, (m.get("title") or "")[:200], (m.get("store") or "")[:60], v, nv, copy[:1500] if a in prod else ""))
        print(f"  meta {d}: {len(meta):,} products so far", flush=True)
    pd.DataFrame(meta, columns=["parent_asin", "dept", "title", "store", "m_val", "m_nval", "copy"]).to_csv(CACHE / "elsewhere_meta.csv.gz", index=False)
    print(f"reviews {len(rows):,}; products reviewed {len(prod):,}; metadata rows {len(meta):,}")


def test():
    R = pd.read_csv(CACHE / "reviewer_categories.csv.gz", index_col=0, usecols=["user_id", "group", "stratum"]); R = R[R.group != "between"]
    E = pd.read_csv(CACHE / "elsewhere_reviews.csv.gz"); M = pd.read_csv(CACHE / "elsewhere_meta.csv.gz", usecols=["parent_asin", "m_val", "m_nval", "title", "store"])
    E = E.merge(M[["parent_asin", "m_val"]].drop_duplicates("parent_asin"), on="parent_asin", how="left")
    print(f"reviews by the two groups in other departments: {len(E):,}; with marketing valence {E.m_val.notna().mean():.0%}; with review valence {E.r_val.notna().mean():.0%}")
    uix = {u: k for k, u in enumerate(R.index)}; lab0 = (R.group.values == "ALL-UPF"); strata = pd.factorize(R.stratum)[0]
    def table(col):
        t = E.dropna(subset=[col]).groupby(["user_id", "dept"])[col].mean().reset_index()
        return t.user_id.map(uix).values, pd.factorize(t.dept)[0], t[col].values, pd.factorize(t.dept)[1]
    def stat(lab, ui, di, y, nd):
        L = lab[ui]; s4 = np.bincount(di, y * L, nd); n4 = np.bincount(di, L.astype(float), nd); s1 = np.bincount(di, y * ~L, nd); n1 = np.bincount(di, (~L).astype(float), nd)
        w = n4 + n1; ok = (n4 > 0) & (n1 > 0); return float(np.sum((w * (s4 / np.maximum(n4, 1) - s1 / np.maximum(n1, 1)))[ok]) / w[ok].sum()), s4 / np.maximum(n4, 1), s1 / np.maximum(n1, 1), n4, n1
    out = {}
    for name, col, side in [("H8 marketing valence of reviewed products (ALL-UPF higher)", "m_val", "greater"), ("H9 valence of their own reviews (two-sided)", "r_val", "two")]:
        ui, di, y, depts = table(col); nd = len(depts); obs, a4, a1, n4, n1 = stat(lab0, ui, di, y, nd)
        null = np.array([stat(S.shuffle_within(lab0, strata), ui, di, y, nd)[0] for _ in range(2000)])
        p = (1 + (null >= obs).sum()) / 2001 if side == "greater" else (1 + (np.abs(null) >= abs(obs)).sum()) / 2001
        out[name] = (obs, p, null.mean())
        print(f"\n{name}: difference {obs:+.4f} (valence units, -1..1), null mean {null.mean():+.4f}, p = {p:.4f}")
        for k, d in enumerate(depts): print(f"    {d:26s} ALL-UPF {a4[k]:+.3f} (n {int(n4[k]):,}) vs MOSTLY-NOT {a1[k]:+.3f} (n {int(n1[k]):,}): {a4[k] - a1[k]:+.4f}")
    ps = [v[1] for v in out.values()]; adj = S.holm(ps); print("\nHolm:", {k[:3]: round(q, 4) for k, q in zip(out, adj)})
    st = E.dropna(subset=["rating"]).merge(R[["group"]], left_on="user_id", right_index=True)
    print("star ratings (mean) by department:", st.groupby(["dept", "group"]).rating.mean().unstack().round(2).to_dict("index"))
    # emotion words (descriptive) with artefact reading
    W = pd.read_csv(CACHE / "elsewhere_emotion_words.csv.gz"); T = pd.read_csv(CACHE / "elsewhere_tokens.csv", index_col=0).iloc[:, 0]
    print(f"\nEMOTION WORDS in other-department reviews (per 10,000 words; ALL-UPF tokens {int(T['ALL-UPF']):,}, MOSTLY-NOT {int(T['MOSTLY-NOT']):,}):")
    for e in EMO:
        w = W[W.emotion == e].pivot_table(index="word", columns="group", values="count", fill_value=0)
        ra, rb = 1e4 * w["ALL-UPF"] / T["ALL-UPF"], 1e4 * w["MOSTLY-NOT"] / T["MOSTLY-NOT"]; dlt = (ra - rb).sort_values()
        print(f"  {e:12s} total {ra.sum():.1f} vs {rb.sum():.1f} | most ALL-UPF: " + ", ".join(f"{x} {ra[x]:.1f}/{rb[x]:.1f}" for x in dlt.index[::-1][:6]) + " | most MOSTLY-NOT: " + ", ".join(f"{x} {ra[x]:.1f}/{rb[x]:.1f}" for x in dlt.index[:4]))
    # product lean + word plot of marketing copy
    G = E.merge(R[["group"]], left_on="user_id", right_index=True).drop_duplicates(["user_id", "parent_asin"])
    pl = G.groupby(["parent_asin", "dept"]).group.agg(n="size", upf=lambda x: (x == "ALL-UPF").mean()).reset_index(); pl = pl[pl.n >= 5]
    base = (R.group == "ALL-UPF").mean(); print(f"\nproducts with >= 5 group reviewers: {len(pl):,}; overall ALL-UPF share among group reviewers {base:.2f}")
    MM = pd.read_csv(CACHE / "elsewhere_meta.csv.gz", usecols=["parent_asin", "copy", "store", "title"]).drop_duplicates("parent_asin")
    pl = pl.merge(MM, on="parent_asin"); pl = pl[pl["copy"].fillna("").str.split().str.len() >= 10]
    parts = []
    for d, g in pl.groupby("dept"):
        q1, q3 = g.upf.quantile([.25, .75]); hi, lo = g[g.upf >= q3], g[g.upf <= q1]; n = min(len(hi), len(lo))
        if n >= 50: parts += [hi.sample(n, random_state=1).assign(side=1), lo.sample(n, random_state=1).assign(side=0)]
    B = pd.concat(parts); print(f"word plot: {len(B) // 2:,} products per side, balanced within {B.dept.nunique()} departments")
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    brandw = set(w for s in B.store.fillna("") for w in re.findall(r"[a-z]{3,}", s.lower()))
    STOP = set(ENGLISH_STOP_WORDS) | brandw | {"pack", "count", "size", "inch", "inches", "amazon", "product", "products", "item", "items", "br"}
    docs = {s: [set(w for w in re.findall(r"[a-z]{3,}", t.lower()) if w not in STOP) for t in B["copy"][B.side == s]] for s in (1, 0)}
    ca, cb = Counter(w for d in docs[1] for w in d), Counter(w for d in docs[0] for w in d); na, nb = len(docs[1]), len(docs[0])
    vocab = [w for w in set(ca) | set(cb) if ca[w] + cb[w] >= 30]; ya = np.array([ca[w] for w in vocab], float); yb = np.array([cb[w] for w in vocab], float)
    bg = ya + yb; al = 500 * bg / bg.sum(); a0 = al.sum(); Na, Nb = ya.sum(), yb.sum()
    z = (np.log((ya + al) / (Na + a0 - ya - al)) - np.log((yb + al) / (Nb + a0 - yb - al))) / np.sqrt(1 / (ya + al) + 1 / (yb + al))
    Wd = pd.DataFrame({"word": vocab, "pct_upf_lean": 100 * ya / na, "pct_not_lean": 100 * yb / nb, "z": z}).sort_values("z"); Wd.to_csv(PROC / "elsewhere_wordplot.csv", index=False)
    print("  words leaning to products of ALL-UPF reviewers: " + ", ".join(f"{r.word} ({r.z:.1f})" for r in Wd.tail(30).iloc[::-1].itertuples()))
    print("  words leaning to products of MOSTLY-NOT reviewers: " + ", ".join(f"{r.word} ({r.z:.1f})" for r in Wd.head(30).itertuples()))
    print("  top-leaning products (ALL-UPF): " + " | ".join(pl.sort_values(["upf", "n"], ascending=False).head(12).title.str[:45]))
    print("  top-leaning products (MOSTLY-NOT): " + " | ".join(pl.sort_values(["upf", "n"], ascending=[True, False]).head(12).title.str[:45]))
    # names for mixed-network communities
    N = pd.read_csv(CACHE / "mixed_nodes.csv.gz").merge(MM[["parent_asin", "title"]], on="parent_asin", how="left")
    Pg = pd.read_csv(CACHE / "products.csv.gz", usecols=["parent_asin", "title"]).rename(columns={"title": "gtitle"}); N = N.merge(Pg, on="parent_asin", how="left"); N["name"] = N.title.fillna(N.gtitle)
    print("\nMIXED-NETWORK COMMUNITIES, example product names:")
    for c in range(14):
        ex = N[(N.community == c) & N.name.notna()].sample(min(6, int(((N.community == c) & N.name.notna()).sum())), random_state=2).name.str[:40].tolist()
        print(f"  {c:2d}: " + " | ".join(ex))


if __name__ == "__main__":
    {"build": build, "test": test}[sys.argv[1]]()
