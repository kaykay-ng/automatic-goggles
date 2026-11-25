"""Corpus statistics for both subreddits (course weeks 5-6): lengths raw vs after preprocessing, vocabulary and hapax legomena, Zipf's law
(rank-frequency), Heaps' law (vocabulary growth), top words by frequency vs TF-IDF, collocations by PMI, and a concordance of key terms.
Output: data/processed/corpus_stats.json (aggregates only: counts, words, fits) for the results page, and data/processed/concordance_<sub>.txt
(verbatim keyword-in-context lines: Reddit text, gitignored, for reading only).
Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/corpus_stats.py

Definitions (all lowercased):
  words      = whitespace-separated pieces (lengths).
  tokens     = seedoil_common._tokens without punctuation: letters of any alphabet incl. accents, hyphenated compounds whole, apostrophes
               deleted ("don't" -> "dont"); no stop-word removal, no name merging, no negation marking (Zipf, Heaps, hapax).
  content    = bertopic_clean (names merged, negations marked no_x) minus English stop words + Reddit filler: the tokens topic words are built
               from (top words, TF-IDF, PMI).
Raw = comment bodies and self-post titles + bodies as downloaded ([removed]/[deleted]/empty and bots dropped; link posts left out).
Cleaned = after quote/URL removal (all lengths); topic corpus = cleaned documents of 15+ words."""
import gzip
import json
import math
import random
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import seso_topics as st  # noqa: E402
from seedoil_common import _PUNCT, TOKEN_PATTERN, _tokens, bertopic_clean, is_bot  # noqa: E402

PROC, RAW = st.PROC, st.RAW
SUBS = {"StopEatingSeedOils": "seso", "ScientificNutrition": "scinut"}
KWIC_TERMS = ["seed oils", "omega-6", "inflammatory"]
PMI_MIN = 30
rng = random.Random(0)


def stopset():
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    return set(ENGLISH_STOP_WORDS) | st.REDDIT_FILLER


def describe(lengths):
    a = np.asarray(lengths)
    return {"n": int(len(a)), "mean": round(float(a.mean()), 1), "median": int(np.median(a)), "p90": int(np.percentile(a, 90))} if len(a) else None


def raw_lengths(sub):
    out = {"comment": [], "post": []}
    for kind in ("comments", "posts"):
        with gzip.open(RAW / f"{sub}_{kind}.jsonl.gz", "rt", encoding="utf-8") as f:
            for line in f:
                x = json.loads(line)
                if is_bot(x.get("author")) or x.get("author") == "[deleted]":
                    continue
                if kind == "comments":
                    b = x.get("body") or ""
                    if b.strip() in ("", "[removed]", "[deleted]"):
                        continue
                    out["comment"].append(len(b.split()))
                else:
                    s = x.get("selftext") or ""
                    if s.strip() in ("", "[removed]", "[deleted]"):
                        continue
                    out["post"].append(len(f"{x.get('title', '')}. {s}".split()))
    return out


def loglog_fit(x, y):
    b, a = np.polyfit(np.log10(x), np.log10(y), 1)
    return float(b), float(10 ** a)


def main():
    stop = stopset(); res = {}
    for sub, pfx in SUBS.items():
        print(sub, flush=True)
        D = pd.read_csv(PROC / f"{pfx}_docs.csv.gz", usecols=["id", "kind", "created_utc", "text"], keep_default_na=False)
        S = pd.read_csv(PROC / f"{pfx}_short_docs.csv.gz", usecols=["kind", "text"], keep_default_na=False)
        R = raw_lengths(sub)
        lens = {}
        for k in ("comment", "post"):
            dk, sk = D[D.kind == k].text.str.split().str.len(), S[S.kind == k].text.str.split().str.len()
            lens[k] = {"raw": describe(R[k]), "cleaned_all": describe(pd.concat([dk, sk])), "topic_corpus": describe(dk)}
        # tokens (topic corpus, chronological order as saved)
        toks = [[t for t in _tokens(x) if t not in _PUNCT] for x in D.text]
        freq = Counter(t for d in toks for t in d)
        N, V = sum(freq.values()), len(freq); hapax = sum(1 for c in freq.values() if c == 1); dis = sum(1 for c in freq.values() if c == 2)
        # content tokens (counting pipeline)
        cpat = re.compile(TOKEN_PATTERN)
        content = [[t for t in cpat.findall(bertopic_clean(x)) if t not in stop and t != "emptydoc"] for x in D.text]
        for k in ("comment", "post"):
            lens[k]["content_tokens"] = describe([len(c) for c, kk in zip(content, D.kind) if kk == k])
        # Zipf: rank-frequency, fit over ranks 10..10,000
        f_sorted = np.array(sorted(freq.values(), reverse=True)); ranks = np.arange(1, len(f_sorted) + 1)
        sel = (ranks >= 10) & (ranks <= 10_000); s_zipf, c_zipf = loglog_fit(ranks[sel], f_sorted[sel])
        pick = np.unique(np.round(np.logspace(0, math.log10(len(f_sorted)), 70)).astype(int)) - 1
        zipf_pts = [[int(ranks[i]), int(f_sorted[i])] for i in pick]
        # Heaps: vocabulary vs tokens as documents accumulate in time order
        seen, n_tok, heaps = set(), 0, []
        marks = set(np.unique(np.round(np.logspace(2, math.log10(len(toks)), 60)).astype(int)) - 1)
        for i, d in enumerate(toks):
            seen.update(d); n_tok += len(d)
            if i in marks:
                heaps.append([n_tok, len(seen)])
        beta, k_heaps = loglog_fit([h[0] for h in heaps], [h[1] for h in heaps])
        # top words: raw frequency (all tokens), content frequency, mean TF-IDF
        cfreq = Counter(t for d in content for t in d)
        from sklearn.feature_extraction.text import TfidfVectorizer
        tv = TfidfVectorizer(analyzer=lambda d: d, min_df=20)  # documents are already content-token lists
        X = tv.fit_transform(content); terms = tv.get_feature_names_out(); m = np.asarray(X.mean(axis=0)).ravel()
        top_tfidf = [[terms[i], round(float(m[i]), 4), int(cfreq[terms[i]])] for i in np.argsort(-m)[:25]]
        # PMI of adjacent content tokens
        uni = cfreq; Nu = sum(uni.values()); bi = Counter((a, b) for d in content for a, b in zip(d, d[1:])); Nb = sum(bi.values())
        pmi = sorted(((math.log2((c / Nb) / ((uni[a] / Nu) * (uni[b] / Nu))), a, b, c) for (a, b), c in bi.items() if c >= PMI_MIN), reverse=True)
        top_bi = bi.most_common(15)
        # concordance: collocates (aggregate, for the page) + KWIC lines (local file)
        kwic, coll = [], {}
        for term in KWIC_TERMS:
            tt = term.split(); L, Rr = Counter(), Counter(); hits = []
            for d, x in zip(toks, D.text):
                for j in range(len(d) - len(tt) + 1):
                    if d[j:j + len(tt)] == tt:
                        if j > 0 and d[j - 1] not in stop: L[d[j - 1]] += 1
                        if j + len(tt) < len(d) and d[j + len(tt)] not in stop: Rr[d[j + len(tt)]] += 1
                        hits.append((d, j))
            coll[term] = {"hits": len(hits), "left": L.most_common(10), "right": Rr.most_common(10)}
            for d, j in rng.sample(hits, min(25, len(hits))):
                left, right = " ".join(d[max(0, j - 8):j]), " ".join(d[j + len(tt):j + len(tt) + 8])
                kwic.append(f"{left:>60}  [{term}]  {right}")
        (PROC / f"concordance_{pfx}.txt").write_text(f"Keyword in context, r/{sub}, 25 random hits per term (Reddit text: do not commit or publish)\n\n" + "\n".join(kwic) + "\n")
        res[sub] = {"lengths": lens, "tokens": N, "types": V, "hapax": hapax, "dis_legomena": dis, "ttr": round(V / N, 4),
                    "zipf": {"s": round(-s_zipf, 3), "fit_ranks": [10, 10000], "points": zipf_pts},
                    "heaps": {"beta": round(beta, 3), "K": round(k_heaps, 2), "points": heaps},
                    "top_freq_all": freq.most_common(15), "top_freq_content": cfreq.most_common(25), "top_tfidf": top_tfidf,
                    "pmi": [[a, b, round(p, 2), c] for p, a, b, c in pmi[:20]], "pmi_min_count": PMI_MIN, "top_bigrams": [[a, b, c] for (a, b), c in top_bi],
                    "concordance": coll}
        print(f"  tokens {N:,}, types {V:,}, hapax {hapax:,} ({hapax / V:.0%}), Zipf s={-s_zipf:.2f}, Heaps beta={beta:.2f}", flush=True)
    (PROC / "corpus_stats.json").write_text(json.dumps(res))
    print("wrote corpus_stats.json")


if __name__ == "__main__":
    main()
