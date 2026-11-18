"""2018 CO-PURCHASE NETWORK (pre-declared H4-CP in upf/PLAN.md, 18 Nov).
Products = our matched grocery products (NOVA known). Link = Amazon 'also bought' (2018 metadata), undirected; weight 2 if listed both ways.
2018 ASINs mapped to 2023 parent_asin with soj/asin_to_parent_2023.csv.gz.
Tests: NOVA assortativity vs labels shuffled within OFF category (1,000), robustness: no same-brand links; shuffle within brand; also_view network.
Exploratory: Louvain communities described by Amazon sub-category, brand concentration and UPF share.
Writes data/processed/copurchase_network.txt, soj/copurchase_edges.csv.gz, soj/copurchase_communities.csv.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/copurchase_network.py
"""
import gzip, json, re
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx

C = Path("upf/data/processed/soj"); OUT = Path("upf/data/processed/copurchase_network.txt"); RNG = np.random.default_rng(2018); NPERM = 1000
log = []
def say(s=""): print(s, flush=True); log.append(s)

mp = pd.read_csv(C / "asin_to_parent_2023.csv.gz").set_index("asin").parent_asin.to_dict(); to = lambda x: mp.get(x, x)
P = pd.read_csv(C / "products.csv.gz", usecols=["parent_asin", "nova", "category", "brand", "title"]).drop_duplicates("parent_asin").set_index("parent_asin")
ours = set(P.index)
M = pd.read_csv("upf/data/processed/amazon_meta_compact.csv.gz", usecols=["parent_asin", "categories"]).drop_duplicates("parent_asin").set_index("parent_asin").categories
rows = []
with gzip.open("upf/data/raw/amazon/2018/meta_Grocery_and_Gourmet_Food.json.gz", "rt") as f:
    for line in f:
        r = json.loads(line); a = to(r.get("asin"))
        if a in ours: rows.append((a, [to(b) for b in (r.get("also_buy") or [])], [to(b) for b in (r.get("also_view") or [])]))


def edges(k):
    e = pd.DataFrame([(a, b) for row in rows for a in [row[0]] for b in row[k] if b in ours and b != a], columns=["a", "b"])
    e["p"], e["q"] = e.min(axis=1), e.max(axis=1); return e.groupby(["p", "q"]).size().rename("w").reset_index()


Eb, Ev = edges(1), edges(2)
nodes = pd.Index(sorted(set(Eb.p) | set(Eb.q) | set(Ev.p) | set(Ev.q)))
upf = (P.nova.reindex(nodes).values == 4).astype(int); cat = P.category.reindex(nodes).fillna("none").values
norm = lambda s: re.sub(r"[^a-z]", "", str(s).lower())[:8] if pd.notna(s) and str(s).strip() else ""
brand = np.array([norm(b) for b in P.brand.reindex(nodes).values], dtype=object)
bgrp = np.where(brand == "", np.array([f"_nobrand{t}" for t in range(len(nodes))], dtype=object), brand)


def shuffle_within(lab, groups):
    pos = np.argsort(groups, kind="stable"); src = np.lexsort((RNG.random(len(lab)), groups)); out = np.empty_like(lab); out[pos] = lab[src]; return out


def assort(i, j, w, lab):
    a, b = lab[i], lab[j]; tot = w.sum(); e11 = w[(a == 1) & (b == 1)].sum() / tot; e00 = w[(a == 0) & (b == 0)].sum() / tot
    p1 = (np.bincount(a, w, 2) + np.bincount(b, w, 2)) / (2 * tot); sq = (p1 ** 2).sum(); return (e11 + e00 - sq) / (1 - sq)


def test(name, E, groups, nperm=NPERM):
    i, j, w = nodes.get_indexer(E.p), nodes.get_indexer(E.q), E.w.values.astype(float)
    obs = assort(i, j, w, upf); null = np.array([assort(i, j, w, shuffle_within(upf, groups)) for _ in range(nperm)])
    p = (1 + (null >= obs).sum()) / (nperm + 1); nn = len(set(i) | set(j))
    say(f"  {name}: {nn:,} products, {len(E):,} links; NOVA assortativity {obs:+.3f} vs null {null.mean():+.3f} (sd {null.std():.3f}), p = {p:.4f}"); return obs, null.mean(), p


say(f"matched products found in 2018: {len(rows):,}; also_buy links {len(Eb):,}, also_view links {len(Ev):,}")
i, j = nodes.get_indexer(Eb.p), nodes.get_indexer(Eb.q)
sb = (brand[i] == brand[j]) & (brand[i] != ""); sc = cat[i] == cat[j]; su = upf[i] == upf[j]
say(f"also_buy links: same brand {sb.mean():.0%}, same OFF category {sc.mean():.0%}, same processing level {su.mean():.0%} (products: {upf[np.unique(np.r_[i, j])].mean():.0%} UPF)")
say("\n== H4-CP (pre-declared): also_buy network, null = labels shuffled within OFF category ==")
test("also_buy, within-category null", Eb, cat)
say("== robustness ==")
test("also_buy without same-brand links, within-category null", Eb[~sb], cat)
test("also_buy, null shuffled within brand", Eb, bgrp)
test("also_view, within-category null", Ev, cat)

say("\n== exploratory: Louvain communities on the also_buy network ==")
G = nx.Graph(); G.add_weighted_edges_from(zip(Eb.p, Eb.q, Eb.w.astype(float)))
giant = G.subgraph(max(nx.connected_components(G), key=len)).copy()
say(f"components {nx.number_connected_components(G):,}; giant {giant.number_of_nodes():,} products ({giant.number_of_nodes() / G.number_of_nodes():.0%}), {giant.number_of_edges():,} links; "
    f"clustering {nx.average_clustering(giant):.3f}")
com = sorted(nx.community.louvain_communities(giant, weight="weight", seed=7), key=len, reverse=True)
say(f"Louvain on the giant component: {len(com)} communities, modularity {nx.community.modularity(giant, com, weight='weight'):.3f}; sizes {[len(c) for c in com[:15]]}")
from sklearn.metrics import adjusted_rand_score
base = {x: k for k, c in enumerate(com) for x in c}; ks = list(base); aris = []
for sd in range(5):
    cm = nx.community.louvain_communities(giant, weight="weight", seed=50 + sd); cc = {x: k for k, c in enumerate(cm) for x in c}
    aris.append(adjusted_rand_score([base[x] for x in ks], [cc[x] for x in ks]))
say(f"stability over 5 other seeds: adjusted Rand {np.mean(aris):.2f} (min {min(aris):.2f})")
sub = M.reindex(nodes).fillna("").str.split("|").apply(lambda x: x[2] if len(x) > 2 else "").values; subS = pd.Series(sub, index=nodes)
out = []
for k, c in enumerate(com[:20]):
    c = list(c); s = subS[c].value_counts(normalize=True); b = pd.Series(brand[nodes.get_indexer(c)]).replace("", np.nan).dropna().value_counts(normalize=True)
    u = upf[nodes.get_indexer(c)].mean(); ex = P.title.reindex(c).dropna().str[:40].sample(min(3, len(c)), random_state=1).tolist()
    out.append(dict(community=k, products=len(c), upf_share=round(u, 3), top_subcats="; ".join(f"{x} {v:.0%}" for x, v in s.head(4).items()), top_brand_share=round(b.iloc[0], 3) if len(b) else np.nan,
                    top_brand=b.index[0] if len(b) else ""))
    say(f"  C{k + 1:<2d} {len(c):5,} products, UPF {u:.0%}, top brand {b.index[0] if len(b) else '-'} {b.iloc[0] if len(b) else 0:.0%}; " + "; ".join(f"{x} {v:.0%}" for x, v in s.head(4).items()))
pd.DataFrame(out).to_csv(C / "copurchase_communities.csv", index=False)
Eb.to_csv(C / "copurchase_edges.csv.gz", index=False)
pd.DataFrame({"node": list(base), "community": [base[x] for x in base]}).to_csv(C / "copurchase_membership.csv.gz", index=False)
OUT.write_text("\n".join(log) + "\n"); print("saved", OUT)
