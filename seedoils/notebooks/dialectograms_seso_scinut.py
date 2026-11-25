"""Dialectogram-style comparison of r/StopEatingSeedOils and r/ScientificNutrition, after Enggaard, Lohse, Pedersen and Lehmann, 'Dialectograms: Machine Learning Differences between Discursive Communities' (arXiv 2302.05657; Scientific Reports 2024).
Their steps: one embedding per community, aligned into a common space; for a focal word the difference of its two embeddings is a direction; every other word is projected onto it in each space; the two projections are plotted against each other.
DIFFERENCES FROM THE PAPER (this is not a replication): embeddings are PPMI + truncated SVD of co-occurrence counts (window 10, weights 1/distance, context smoothing 0.75), not GloVe; our corpora are smaller (about 8M and 11M tokens); frequency bias is handled by comparing with a noise floor
and by frequency bins, not by their correction; 'sense separation' is not implemented.
Corpora: the topic-model documents (comments and posts of 15+ words, quotes and links removed) of each subreddit; authors with 3+ documents in BOTH subreddits are excluded from both (the paper excludes users active in both); exact duplicate texts seen 5+ times are dropped.
Vocabulary: words used 100+ times in EACH corpus. 'seed oil(s)' is merged into one token 'seedoil' and 'omega-6' into 'omega6'.
Outputs: data/processed/dialectogram_word_differences.csv (aggregates: word, counts, aligned cosine distance, noise floor, excess), figures/dialectogram_<word>.png/.pdf.
Noise floor: the same measure between two random halves of one subreddit (split by author), averaged over both subreddits; 'excess' = real distance minus that floor.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python seedoils/notebooks/dialectograms_seso_scinut.py   (aggregates only; figures show words, not comments)"""
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.linalg import orthogonal_procrustes
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from sklearn.utils.extmath import randomized_svd

P = Path("seedoils/data/processed"); FIG = Path("seedoils/figures"); MIN_COUNT = 100; WINDOW = 10; DIM = 300; rng = np.random.default_rng(0)
TOK = re.compile(r"[a-z]+")
def tokens(text):
    t = text.lower(); t = re.sub(r"seed[\s-]*oils?", " seedoil ", t); t = re.sub(r"omega[\s-]*6", " omega6 ", t); t = t.replace("'", "").replace("’", "")
    return TOK.findall(t)
def load(sub):
    D = pd.read_csv(P / f"{sub}_docs.csv.gz", usecols=["author", "text"], keep_default_na=False); D = D[~D.author.isin(["[deleted]", "AutoModerator"]) & ~D.author.str.lower().str.endswith("bot")]
    return D
S, N = load("seso"), load("scinut")
both = set(S.author.value_counts()[lambda s: s >= 3].index) & set(N.author.value_counts()[lambda s: s >= 3].index)
print(f"authors with 3+ documents in both subreddits (excluded): {len(both):,}")
def clean(D):
    n0 = len(D); D = D[~D.author.isin(both)]; dup = D.text.value_counts(); D = D[~D.text.isin(dup[dup >= 5].index)]; print(f"  kept {len(D):,} of {n0:,} documents"); return D
S, N = clean(S), clean(N)
ts = [tokens(x) for x in S.text]; tn = [tokens(x) for x in N.text]
cs, cn = Counter(w for d in ts for w in d), Counter(w for d in tn for w in d)
vocab = sorted(w for w in cs if cs[w] >= MIN_COUNT and cn.get(w, 0) >= MIN_COUNT); vi = {w: i for i, w in enumerate(vocab)}; V = len(vocab)
print(f"tokens: StopEatingSeedOils {sum(cs.values()):,}, ScientificNutrition {sum(cn.values()):,}; vocabulary (100+ in each): {V:,} words")
def cooc(docs):
    ids, doc = [], []
    for k, d in enumerate(docs):
        x = [vi[w] for w in d if w in vi]; ids += x; doc += [k] * len(x)
    ids = np.array(ids, dtype=np.int64); doc = np.array(doc); X = np.zeros((V, V), np.float32)
    for dist in range(1, WINDOW + 1):
        ok = doc[:-dist] == doc[dist:]; a = ids[:-dist][ok]; b = ids[dist:][ok]; w = np.full(len(a), 1.0 / dist)
        X += np.bincount(a * V + b, weights=w, minlength=V * V).reshape(V, V).astype(np.float32); X += np.bincount(b * V + a, weights=w, minlength=V * V).reshape(V, V).astype(np.float32)
    return X, np.bincount(ids, minlength=V)
def embed(X):
    tot = X.sum(); r = X.sum(1, keepdims=True); c = X.sum(0, keepdims=True) ** 0.75; c = c / c.sum()
    with np.errstate(divide="ignore", invalid="ignore"): pmi = np.log((X / tot) / ((r / tot) * c))
    pmi[~np.isfinite(pmi)] = 0; pmi = np.maximum(pmi, 0)
    U, s, _ = randomized_svd(pmi, DIM, n_iter=5, random_state=0); E = U * np.sqrt(s); return E / np.maximum(np.linalg.norm(E, axis=1, keepdims=True), 1e-9)
def align(E1, E2):
    A = E1 - E1.mean(0); B = E2 - E2.mean(0); A /= np.linalg.norm(A, axis=1, keepdims=True); B /= np.linalg.norm(B, axis=1, keepdims=True)
    R, _ = orthogonal_procrustes(B, A); B = B @ R; return A, B
def dist(E1, E2):
    A, B = align(E1, E2); return 1 - (A * B).sum(1), A, B
Xs, fs = cooc(ts); Xn, fn = cooc(tn); Es, En = embed(Xs), embed(Xn); d, A, B = dist(Es, En)
def halves(docs, authors):
    u = np.array(sorted(set(authors))); rng.shuffle(u); h = set(u[: len(u) // 2]); a = [x for x, au in zip(docs, authors) if au in h]; b = [x for x, au in zip(docs, authors) if au not in h]; return a, b
nulls = []
for docs, au in ((ts, S.author.tolist()), (tn, N.author.tolist())):
    a, b = halves(docs, au); Xa, _ = cooc(a); Xb, _ = cooc(b); nulls.append(dist(embed(Xa), embed(Xb))[0])
d0 = np.mean(nulls, axis=0); excess = d - d0
print(f"aligned cosine distance: median {np.median(d):.3f} (noise floor from split halves: median {np.median(d0):.3f}); words whose real distance exceeds the floor: {(excess > 0).mean():.0%}")
mf = np.sqrt(fs * fn); bins = pd.qcut(np.log(mf), 10, labels=False); z = np.zeros(V)
for b in range(10): m = bins == b; z[m] = (excess[m] - excess[m].mean()) / excess[m].std()
stop = set(ENGLISH_STOP_WORDS)
out = pd.DataFrame({"word": vocab, "n_seso": fs, "n_scinut": fn, "distance": d, "noise_floor": d0, "excess": excess, "excess_z_within_frequency_decile": z}); out["stopword"] = out.word.isin(stop)
out.sort_values("excess", ascending=False).to_csv(P / "dialectogram_word_differences.csv", index=False)
show = out[~out.stopword & (out.n_seso >= 300) & (out.n_scinut >= 300)]
print("\nwords used most differently (content words with 300+ uses in each corpus), by excess distance over the noise floor:")
for r in show.sort_values("excess", ascending=False).head(25).itertuples(): print(f"  {r.word:<16} excess {r.excess:.3f}  (distance {r.distance:.3f}, floor {r.noise_floor:.3f})  uses {r.n_seso:>6} / {r.n_scinut:>6}")
print("\nlowest excess (used most similarly):", ", ".join(show.sort_values("excess").head(12).word))
# dialectograms
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
FIG.mkdir(exist_ok=True)
def dialectogram(word, ax, topn=9):
    i = vi[word]; O = A[i] - B[i]; O = O / np.linalg.norm(O); a1, a2 = A @ O, B @ O
    co = (Xs[i] > 0) | (Xn[i] > 0); keep = co & ~out.stopword.values; keep[i] = False; top3 = np.argsort(-(fs + fn))[:3]; keep[top3] = False
    x, y, w = a1[keep], a2[keep], np.array(vocab)[keep]; size = 6 + 40 * (np.log(mf[keep]) - np.log(mf[keep]).min()) / np.ptp(np.log(mf[keep]))
    ax.axhline(0, color="#999", lw=.6); ax.axvline(0, color="#999", lw=.6); col = np.where((x > 0) & (y > 0), "#c4521a", np.where((x < 0) & (y < 0), "#3d5a73", "#9aa3ad"))
    ax.scatter(x, y, s=size, c=col, alpha=.55, linewidths=0)
    lim = np.abs(np.concatenate([x, y])).max() * 1.08; ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); placed = []
    for sel in (((x > 0) & (y > 0)), ((x < 0) & (y < 0)), ((x > 0) & (y < 0)), ((x < 0) & (y > 0))):
        idx = np.where(sel)[0]; idx = idx[np.argsort(-(np.abs(x[idx]) + np.abs(y[idx])))][:topn]
        for j in idx:
            if any(abs(x[j] - px) < lim * .12 and abs(y[j] - py) < lim * .05 for px, py in placed): continue
            placed.append((x[j], y[j])); ax.annotate(w[j], (x[j], y[j]), fontsize=7.5, xytext=(2, 2), textcoords="offset points")
    cos_o = float(A[i] @ B[i]); ax.set_title(f"'{word}'   (aligned cosine distance {1 - cos_o:.2f})", fontsize=9)
    ax.set_xlabel("projection in r/StopEatingSeedOils space", fontsize=8); ax.set_ylabel("projection in r/ScientificNutrition space", fontsize=8); ax.tick_params(labelsize=7)
FOCAL = [w for w in ("seedoil", "evidence", "natural", "processed", "toxic", "inflammation", "healthy", "study") if w in vi]
fig, axes = plt.subplots(2, 2, figsize=(11, 10))
for ax, w in zip(axes.ravel(), FOCAL[:4]): dialectogram(w, ax)
fig.suptitle("Dialectograms: how each subreddit uses a word (orange: characteristic use in r/StopEatingSeedOils, blue: in r/ScientificNutrition)", fontsize=10); fig.tight_layout(); fig.savefig(FIG / "dialectograms_four.png", dpi=170); fig.savefig(FIG / "dialectograms_four.pdf")
for w in FOCAL[4:]:
    f2, a2 = plt.subplots(figsize=(5.5, 5)); dialectogram(w, a2); f2.tight_layout(); f2.savefig(FIG / f"dialectogram_{w}.png", dpi=150); plt.close(f2)
print("\nfocal words drawn:", FOCAL, "| figures in seedoils/figures/")
