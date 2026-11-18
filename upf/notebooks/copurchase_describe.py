"""Describe the co-purchase communities (exploratory; copurchase_network.py): distinctive title words (TF-IDF over communities, Week 6) and UPF share vs expected from the community's
OFF category mix. Writes soj/copurchase_communities_described.csv and appends to data/processed/copurchase_network.txt.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/copurchase_describe.py
"""
import re
import numpy as np, pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
C = "upf/data/processed/soj/"
mem = pd.read_csv(C + "copurchase_membership.csv.gz")
P = pd.read_csv(C + "products.csv.gz", usecols=["parent_asin", "nova", "category", "title", "brand"]).drop_duplicates("parent_asin").set_index("parent_asin")
allp = P.copy(); allp["u"] = allp.nova == 4; catrate = allp.groupby("category").u.mean()
mem["u"] = (P.nova.reindex(mem.node).values == 4); mem["exp"] = catrate.reindex(P.category.reindex(mem.node).values).values
size = mem.community.value_counts(); top = size.index[:20]
brands = set(re.sub(r"[^a-z ]", " ", str(b).lower()).strip() for b in P.brand.dropna()) 
bw = set(w for b in brands for w in b.split() if len(w) > 2)
docs = []
for c in top:
    t = " ".join(P.title.reindex(mem.node[mem.community == c]).dropna().str.lower()); docs.append(re.sub(r"[^a-z ]", " ", t))
stop = list(bw | {"oz", "ounce", "ounces", "pack", "count", "pound", "lb", "bag", "box", "bottle", "jar", "can", "packs", "fl", "size", "case", "set", "of", "and", "the", "with", "for", "in"})
V = TfidfVectorizer(sublinear_tf=True, min_df=1, max_df=0.6, stop_words=stop, token_pattern=r"(?u)\b[a-z]{3,}\b"); X = V.fit_transform(docs); vocab = np.array(V.get_feature_names_out())
rows = []; out = ["\nDESCRIBED (TF-IDF of titles across the 20 largest communities; brand words removed; UPF vs expected from OFF category mix):"]
for k, c in enumerate(top):
    m = mem[mem.community == c]; words = vocab[np.argsort(-X[k].toarray().ravel())[:7]]
    rows.append(dict(rank=k + 1, products=len(m), upf=m.u.mean(), expected=m.exp.mean(), diff=m.u.mean() - m.exp.mean(), words=", ".join(words)))
    out.append(f"  C{k + 1:<2d} {len(m):5,} products  UPF {m.u.mean():.0%} (expected {m.exp.mean():.0%}, {100 * (m.u.mean() - m.exp.mean()):+.0f} pts)  words: {', '.join(words)}")
pd.DataFrame(rows).to_csv(C + "copurchase_communities_described.csv", index=False)
print("\n".join(out)); open("upf/data/processed/copurchase_network.txt", "a").write("\n".join(out) + "\n")
