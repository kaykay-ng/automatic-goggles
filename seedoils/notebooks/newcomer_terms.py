"""Scattertext-style comparison: which words and phrases set newcomers apart from the old guard in r/StopEatingSeedOils?
Documents: topic-model documents (comments of >= 15 words, quotes and links removed) from 2024-01-01 on, so both groups are compared in the SAME period (a before/after comparison would mix time with group).
Groups: old guard = the author's first comment in the subreddit is before 2024; newcomer = first comment from 2024 on (computed over all their comments). [deleted] and AutoModerator removed.
Terms: unigrams and bigrams counted once per comment (so a word repeated inside one comment counts once), (as in the topic model: English stop words + Reddit filler removed), used by at least MIN_AUTHORS different authors in each of the two groups combined (so one person's habit cannot make a term).
Score: weighted log-odds with an informative Dirichlet prior (Monroe, Colaresi and Quinn 2008): the prior is the term's overall frequency, so rare terms are not over-read; z > 0 = newcomers, z < 0 = old guard.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python seedoils/notebooks/newcomer_terms.py  -> data/processed/artifact/newcomer_terms.json ({rows, meta}). Aggregates only: terms and counts, no text, no usernames."""
import glob
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).parent))
import seso_topics as st  # noqa: E402

P = Path("seedoils/data/processed"); CUT = 1704067200; MIN_AUTHORS = 15; ALPHA0 = 500
raw_first = {}
with gzip.open(glob.glob("seedoils/data/raw/*StopEatingSeedOils_comments.jsonl.gz")[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); a = x["author"]; t = int(x["created_utc"])
        if a not in raw_first or t < raw_first[a]: raw_first[a] = t
D = pd.read_csv(P / "seso_docs.csv.gz", keep_default_na=False); D = D[(D.kind == "comment") & (D.created_utc >= CUT) & ~D.author.isin(["[deleted]", "AutoModerator"])].copy()
D["new"] = (D.author.map(raw_first) >= CUT).astype(int)
print(f"documents from 2024: {len(D):,} (old guard {int((D.new == 0).sum()):,} by {D[D.new == 0].author.nunique():,} authors; newcomers {int((D.new == 1).sum()):,} by {D[D.new == 1].author.nunique():,} authors)")
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
cv = CountVectorizer(stop_words=list(ENGLISH_STOP_WORDS | st.REDDIT_FILLER), ngram_range=(1, 2), min_df=30, binary=True)
X = cv.fit_transform(D.text.tolist()).tocsr(); V = cv.get_feature_names_out()
G = sp.csr_matrix((np.ones(len(D)), (D.new.values, np.arange(len(D)))), shape=(2, len(D)))
C = np.asarray((G @ X).todense()); old, new = C[0], C[1]
au = pd.factorize(D.author)[0]; A = sp.csr_matrix((np.ones(len(D)), (au, np.arange(len(D)))), shape=(au.max() + 1, len(D)))
users_old = np.asarray(((A[:, D.new.values == 0] @ X[D.new.values == 0]) > 0).sum(0)).ravel(); users_new = np.asarray(((A[:, D.new.values == 1] @ X[D.new.values == 1]) > 0).sum(0)).ravel()
keep = (users_old + users_new >= MIN_AUTHORS) & (old + new >= 30)
old, new, V, users_old, users_new = old[keep], new[keep], V[keep], users_old[keep], users_new[keep]
tot = old + new; prior = tot / tot.sum() * ALPHA0; n1, n2 = new.sum(), old.sum()
d = np.log((new + prior) / (n1 + ALPHA0 - new - prior)) - np.log((old + prior) / (n2 + ALPHA0 - old - prior))
var = 1 / (new + prior) + 1 / (old + prior); z = d / np.sqrt(var)
rows = [{"t": V[i], "o": int(old[i]), "n": int(new[i]), "z": round(float(z[i]), 2), "uo": int(users_old[i]), "un": int(users_new[i])} for i in range(len(V))]
print(f"terms kept: {len(rows):,}; |z| > 3.1: {int((np.abs(z) > 3.1).sum()):,}; tokens old {int(n2):,}, new {int(n1):,}")
o = np.argsort(z)
print("\nOLD GUARD (most negative z):"); [print(f"  {V[i]:<28} z {z[i]:6.1f}  old {int(old[i]):>5} new {int(new[i]):>5}  authors {users_old[i]}/{users_new[i]}") for i in o[:25]]
print("\nNEWCOMERS (most positive z):"); [print(f"  {V[i]:<28} z {z[i]:6.1f}  old {int(old[i]):>5} new {int(new[i]):>5}  authors {users_old[i]}/{users_new[i]}") for i in o[::-1][:25]]
meta = [{"label": "newcomer_terms.py", "value": Path(__file__).read_text()}]
(P / "artifact" / "newcomer_terms.json").write_text(json.dumps({"rows": rows, "meta": meta, "tokens_old": int(n2), "tokens_new": int(n1), "docs_old": int((D.new == 0).sum()), "docs_new": int((D.new == 1).sum())}))
