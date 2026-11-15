"""Profile the Amazon Reviews 2023 grocery files (McAuley Lab; cite Hou et al. 2024, arXiv:2403.03952). Research use only.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/amazon_profile.py
Metadata: how much marketing text (features + description), prices, 'bought together', and how many items carry a UPC/EAN that matches an Open Food Facts product with a NOVA group.
Reviews: counts, ratings, text length, years, reviews per item. Writes upf/data/processed/amazon_meta_compact.csv.gz (gitignored) and amazon_profile.txt.
"""
import gzip, json, re
from collections import Counter
from pathlib import Path
import numpy as np, pandas as pd

RAW = Path("upf/data/raw/amazon"); PROC = Path("upf/data/processed")
out = []
def say(s=""):
    print(s, flush=True); out.append(s)

rows, keys = [], Counter()
with gzip.open(RAW / "meta_Grocery_and_Gourmet_Food.jsonl.gz", "rt") as f:
    for line in f:
        d = json.loads(line); det = d.get("details") or {}; keys.update(det.keys())
        code = None
        for k, v in det.items():
            if re.search(r"\b(UPC|EAN|GTIN)\b", k, re.I) and isinstance(v, str):
                digs = re.findall(r"\d{8,14}", v)
                if digs: code = digs[0]; break
        feat = " ".join(d.get("features") or []); desc = " ".join(x for x in (d.get("description") or []) if x not in ("Description", "Product Description"))
        rows.append(dict(parent_asin=d.get("parent_asin"), title=d.get("title") or "", store=d.get("store"), price=d.get("price"),
                         n_feat_words=len(feat.split()), n_desc_words=len(desc.split()), features=feat[:3000], description=desc[:3000],
                         categories="|".join(d.get("categories") or []), bought_together=bool(d.get("bought_together")), code=code,
                         rating_number=d.get("rating_number"), average_rating=d.get("average_rating")))
M = pd.DataFrame(rows)
say(f"META items: {len(M):,}")
say(f"  with features: {(M.n_feat_words > 0).mean():.0%}; with description: {(M.n_desc_words > 0).mean():.0%}; median words (when present): features {int(M.n_feat_words[M.n_feat_words > 0].median())}, description {int(M.n_desc_words[M.n_desc_words > 0].median())}")
say(f"  price present: {M.price.notna().mean():.0%}; bought_together present: {M.bought_together.mean():.1%}; categories present: {(M.categories != '').mean():.0%}")
say(f"  most common detail keys: {dict(keys.most_common(15))}")
say(f"  items with a UPC/EAN/GTIN-like code: {M.code.notna().sum():,} ({M.code.notna().mean():.1%})")
# barcode match with Open Food Facts (OFF codes are EAN-13 / UPC-12 strings; compare as 13-digit zero-padded)
off = pd.read_csv(PROC / "off_products.csv.gz", usecols=["code", "nova"], dtype={"code": str})
pad = lambda s: s.lstrip("0").zfill(13) if isinstance(s, str) and s.isdigit() else None
offmap = dict(zip(off.code.map(pad), off.nova)); M["code13"] = M.code.map(pad); M["nova"] = M.code13.map(offmap)
say(f"  items whose code matches an Open Food Facts product with NOVA: {M.nova.notna().sum():,}; NOVA among matches: {M.nova.value_counts().sort_index().to_dict()}")
ex = M[(M.n_feat_words > 20)].sample(3, random_state=4)
for r in ex.itertuples(): say(f"  EXAMPLE features [{r.title[:60]}]: {r.features[:300]}")
M.to_csv(PROC / "amazon_meta_compact.csv.gz", index=False)

n = 0; ratings = Counter(); years = Counter(); lens = []; per_item = Counter(); verified = 0; rng = np.random.default_rng(1)
with gzip.open(RAW / "Grocery_and_Gourmet_Food.jsonl.gz", "rt") as f:
    for line in f:
        d = json.loads(line); n += 1; ratings[d.get("rating")] += 1; per_item[d.get("parent_asin")] += 1; verified += bool(d.get("verified_purchase"))
        years[pd.Timestamp(d.get("timestamp") or d.get("sort_timestamp") or 0, unit="ms").year] += 1
        if rng.random() < 0.02: lens.append(len((d.get("text") or "").split()))
say(f"\nREVIEWS: {n:,}; verified purchases {verified / n:.0%}; ratings {dict(sorted(ratings.items()))}")
say(f"  words per review (2% sample): median {int(np.median(lens))}, mean {np.mean(lens):.0f}; years: {dict(sorted(years.items()))}")
pi = np.array(list(per_item.values())); say(f"  items with reviews {len(pi):,}; reviews per item median {int(np.median(pi))}, items with >= 50 reviews {(pi >= 50).sum():,}")
matched = set(M.parent_asin[M.nova.notna()]); say(f"  reviews on items matched to a NOVA group: {sum(per_item[a] for a in matched):,}")
(PROC / "amazon_profile.txt").write_text("\n".join(out))
