"""Our-data counterparts of the three analysis scripts of the GoEmotions repository (analyze_data, extract_words, ppca). The GoEmotions scripts run on its own human-rated dataset; ours run on the MODEL scores of our corpus (all 149,815 documents of r/StopEatingSeedOils, SamLowe/roberta-base-go_emotions, a label counts when its score >= 0.5).
 1. analyze_data analogue: documents per label, labels per document, and the correlation among labels (phi coefficient on the >= 0.5 flags) with within-group vs between-group averages for the GoEmotions groups.
 2. extract_words analogue: words associated with each label, as log-odds ratios with an informative Dirichlet prior (Monroe, Colaresi and Quinn 2008; z-scores), flagged vs not flagged documents.
 3. PPCA (Cowen et al. 2019) needs several raters per item and cannot be run here; plain PCA of the scores is shown instead and is NOT the same test.
Outputs: seedoils/data/processed/goemo_label_correlations.csv, goemo_label_words.csv (aggregated words only). Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/goemotions_analysis.py"""
import numpy as np, pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS
R, P = "seedoils/data/processed_rebuild/", "seedoils/data/processed/"
labs = list(pd.read_csv(P + "goemo_monthly.csv", nrows=1).columns[1:29]); g = np.load(R + "goemo_seso.npz", allow_pickle=True); pr = g["p"].astype(np.float32); ids = g["id"]
GR = {"positive": "admiration amusement approval caring desire excitement gratitude joy love optimism pride relief".split(), "negative": "anger annoyance disappointment disapproval disgust embarrassment fear grief nervousness remorse sadness".split(), "ambiguous": "confusion curiosity realization surprise".split()}
grp = {l: k for k, v in GR.items() for l in v}; grp["neutral"] = "neutral"; F = pr >= 0.5; N = len(F)
print("=== 1. analyze_data analogue")
cnt = F.sum(0); print(f"documents {N:,}; labels per document (>= 0.5): mean {F.sum(1).mean():.2f}; 0 labels {np.mean(F.sum(1) == 0):.1%}, 1 label {np.mean(F.sum(1) == 1):.1%}, 2+ labels {np.mean(F.sum(1) >= 2):.1%}")
print("documents per label (top 12):", ", ".join(f"{labs[j]} {cnt[j]:,}" for j in np.argsort(-cnt)[:12]))
act = [j for j in range(28) if cnt[j] >= 200]; C = np.corrcoef(F[:, act].T.astype(float)); names = [labs[j] for j in act]
pairs = sorted(((C[i, k], names[i], names[k]) for i in range(len(act)) for k in range(i + 1, len(act))), reverse=True)
print(f"correlation (phi) among the {len(act)} labels with >= 200 documents; strongest positive pairs:"); [print(f"   {a:<14}{b:<14}{r:+.2f}") for r, a, b in pairs[:8]]; print("   most negative pairs:", "; ".join(f"{a}-{b} {r:+.2f}" for r, a, b in pairs[-4:]))
within = [r for r, a, b in pairs if grp[a] == grp[b]]; between = [r for r, a, b in pairs if grp[a] != grp[b]]; print(f"mean correlation within the same GoEmotions group {np.mean(within):+.3f} (n pairs {len(within)}) vs between groups {np.mean(between):+.3f} (n {len(between)})")
pd.DataFrame(C, index=names, columns=names).round(3).to_csv(P + "goemo_label_correlations.csv")
print("\n=== 3. PCA of the 28 scores (not PPCA): share of variance of the first components:", np.round((lambda v: v[:6] / v.sum())(np.linalg.svd((pr - pr.mean(0))[::5], compute_uv=False) ** 2), 3).tolist())
print("\n=== 2. extract_words analogue (log-odds with informative Dirichlet prior, z > 1.96 reported as top words)")
D = pd.read_csv(R + "seso_docs.csv.gz", usecols=["id", "text"], keep_default_na=False).set_index("id").loc[ids].reset_index()
cv = CountVectorizer(stop_words=list(ENGLISH_STOP_WORDS | {"just", "like", "don", "dont", "people", "really", "think", "know", "going", "ve", "ll", "re"}), token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z'\-]{2,}\b", min_df=30, lowercase=True, binary=False)
X = cv.fit_transform(D.text.values); voc = cv.get_feature_names_out(); tot = np.asarray(X.sum(0)).ravel(); alpha = tot / tot.sum() * 500  # prior pseudo-counts total 500
rows = []
show = ["annoyance", "anger", "disapproval", "amusement", "curiosity", "gratitude", "confusion", "sadness"]
for l in labs:
    f = F[:, labs.index(l)]
    if f.sum() < 200: continue
    y1 = np.asarray(X[f].sum(0)).ravel() + alpha; y2 = np.asarray(X[~f].sum(0)).ravel() + alpha; n1, n2 = y1.sum(), y2.sum(); a0 = alpha.sum()
    delta = np.log(y1 / (n1 - y1)) - np.log(y2 / (n2 - y2)); z = delta / np.sqrt(1 / y1 + 1 / y2); o = np.argsort(-z)[:12]
    rows += [{"label": l, "word": voc[i], "z": round(float(z[i]), 1), "count_flagged": int(X[f][:, i].sum())} for i in o]
    if l in show: print(f"{l:<12} (n={int(f.sum()):,}): " + ", ".join(voc[i] for i in o[:10]))
pd.DataFrame(rows).to_csv(P + "goemo_label_words.csv", index=False)
