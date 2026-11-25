"""Critical check of the newcomer-vs-old-guard word comparison (newcomer_terms.py). Questions:
 (1) How different are the two vocabularies at all (cosine similarity, Jensen-Shannon divergence, share of terms used at nearly the same rate)?
 (2) Is the difference about OLD vs NEW, or about HEAVY vs LIGHT commenters (old guard = 1,599 people with ~19 comments each; newcomers = 14,013 people with ~6 each)?
     Null: shuffle the cohort label among authors of similar activity (20 activity bins, number of old-guard authors per bin kept) and recompute the divergence and the number of 'strongly tilted' terms.
 (3) Compare only HEAVY commenters (>= 10 comments from 2024 on) in both groups.
Same documents, terms and score as newcomer_terms.py. Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python seedoils/notebooks/newcomer_terms_check.py   (aggregates only)"""
from seedoil_common import is_bot, not_bot, TOKEN_PATTERN, bertopic_clean, hyphen_bertopic  # shared bot rule: AutoModerator + names ending in 'bot'
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
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer  # noqa: E402

P = Path("seedoils/data/processed"); CUT = 1704067200; MIN_AUTHORS = 15; ALPHA0 = 500; rng = np.random.default_rng(0)
first = {}
with gzip.open(glob.glob("seedoils/data/raw/*StopEatingSeedOils_comments.jsonl.gz")[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); a = x["author"]; t = int(x["created_utc"])
        if a not in first or t < first[a]: first[a] = t
D = pd.read_csv(P / "seso_docs.csv.gz", keep_default_na=False); D = D[(D.kind == "comment") & (D.created_utc >= CUT) & (~D.author.isin(["[deleted]", "AutoModerator"]) & not_bot(D.author))].copy()
cv = CountVectorizer(stop_words=list(ENGLISH_STOP_WORDS | st.REDDIT_FILLER), token_pattern=TOKEN_PATTERN, preprocessor=bertopic_clean, ngram_range=(1, 2), min_df=30, binary=True)
X = cv.fit_transform(D.text.tolist()).tocsr(); V = cv.get_feature_names_out()
au, uniq = pd.factorize(D.author); A = sp.csr_matrix((np.ones(len(D)), (au, np.arange(len(D)))), shape=(len(uniq), len(D)))
AT = (A @ X).tocsr()                                    # authors x terms: comments with the term
n_com = np.asarray(A.sum(1)).ravel(); is_old = np.array([first[a] < CUT for a in uniq]); users_with = np.asarray((AT > 0).sum(0)).ravel()
print(f"authors {len(uniq):,}: old guard {is_old.sum():,} ({n_com[is_old].sum():,.0f} comments, {n_com[is_old].mean():.1f} per person, median {np.median(n_com[is_old]):.0f}); newcomers {(~is_old).sum():,} ({n_com[~is_old].sum():,.0f} comments, {n_com[~is_old].mean():.1f} per person, median {np.median(n_com[~is_old]):.0f})")
keep = (users_with >= MIN_AUTHORS) & (np.asarray(X.sum(0)).ravel() >= 30); AT = AT[:, keep].toarray(); V = V[keep]

def stats(old_mask, sub=None):
    m = np.ones(len(uniq), bool) if sub is None else sub
    o = AT[old_mask & m].sum(0); n = AT[~old_mask & m].sum(0); tot = o + n; ok = tot >= 30
    o, n = o[ok], n[ok]; tot = tot[ok]; prior = tot / tot.sum() * ALPHA0; n1, n2 = n.sum(), o.sum()
    d = np.log((n + prior) / (n1 + ALPHA0 - n - prior)) - np.log((o + prior) / (n2 + ALPHA0 - o - prior)); z = d / np.sqrt(1 / (n + prior) + 1 / (o + prior))
    po, pn = o / o.sum(), n / n.sum(); mm = (po + pn) / 2
    from scipy.special import rel_entr; jsd = float(0.5 * rel_entr(po, mm).sum() + 0.5 * rel_entr(pn, mm).sum()) / np.log(2); cos = float(po @ pn / np.linalg.norm(po) / np.linalg.norm(pn))
    big = tot >= 200; ratio = (pn[big] / po[big]); close = float(np.mean((ratio > 1 / 1.5) & (ratio < 1.5)))
    return {"terms": int(ok.sum()), "strong": int((np.abs(z) > 3.1).sum()), "jsd": float(jsd), "cos": cos, "close": close, "maxratio": float(np.exp(np.abs(np.log(ratio)).max())), "top": (V[ok][np.argsort(z)[:6]].tolist(), V[ok][np.argsort(-z)[:6]].tolist()), "z": z, "ok": ok}

obs = stats(is_old)
print(f"\n(1) OBSERVED, all authors: {obs['terms']:,} terms; strongly tilted (|z| > 3.1): {obs['strong']} ({obs['strong'] / obs['terms']:.1%}); cosine similarity of the two term-use profiles {obs['cos']:.3f}; Jensen-Shannon divergence {obs['jsd']:.4f} bits (0 = identical, 1 = no overlap)")
print(f"    among terms used in >= 200 comments: {obs['close']:.0%} are used at rates within 1.5x of each other; the most lopsided term differs {obs['maxratio']:.1f}x")
print("    top old-guard terms:", obs["top"][0], "| top newcomer terms:", obs["top"][1])
# (2) null: shuffle cohort among authors of similar activity
bins = pd.qcut(pd.Series(n_com).rank(method="first"), 20, labels=False).values; J, S = [], []
for r in range(20):
    lab = np.zeros(len(uniq), bool)
    for b in range(20):
        idx = np.where(bins == b)[0]; k = int(is_old[idx].sum()); lab[rng.choice(idx, k, replace=False)] = True
    s = stats(lab); J.append(s["jsd"]); S.append(s["strong"])
print(f"\n(2) NULL: cohort label shuffled among authors with the same activity (20 reps): strongly tilted terms {np.mean(S):.0f} (range {min(S)}-{max(S)}) vs observed {obs['strong']}; JSD {np.mean(J):.4f} (range {min(J):.4f}-{max(J):.4f}) vs observed {obs['jsd']:.4f}")
# (3) heavy commenters only
heavy = n_com >= 10; h = stats(is_old, heavy)
print(f"\n(3) HEAVY commenters only (>= 10 comments from 2024): old guard {int((is_old & heavy).sum()):,} people, newcomers {int((~is_old & heavy).sum()):,} people")
print(f"    strongly tilted terms {h['strong']} of {h['terms']:,} ({h['strong'] / h['terms']:.1%}); cosine {h['cos']:.3f}; JSD {h['jsd']:.4f}; top old-guard:", h["top"][0], "| top newcomer:", h["top"][1])
common = obs["ok"] & h["ok"]
print(f"    correlation of the scores, all authors vs heavy only (terms in both): {np.corrcoef(obs['z'][common[obs['ok']]], h['z'][common[h['ok']]])[0, 1]:.2f}" if False else "")
# person-level: share of authors using the key terms
for t in ("pufa", "linoleic acid", "omega", "avocado oil", "organic", "rfk-jr", "lol"):  # rfk -> rfk-jr since the name list (22 Nov)
    if t not in set(V):
        print(f"    {t:<14} not in the vocabulary"); continue
    i = list(V).index(t); u = AT[:, i] > 0; print(f"    {t:<14} used by {u[is_old].mean() * 100:4.1f}% of old-guard people vs {u[~is_old].mean() * 100:4.1f}% of newcomers; among heavy commenters {u[is_old & heavy].mean() * 100:4.1f}% vs {u[~is_old & heavy].mean() * 100:4.1f}%")
