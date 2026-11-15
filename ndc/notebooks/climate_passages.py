"""Concordance + cosine selection of climate passages from ParlaMint. Design and cutoff rule fixed in ndc/PLAN.md 'CLIMATE PASSAGES'.
Run from final_project/ with the NLP env:
  ./.venv-nlp/bin/python ndc/notebooks/climate_passages.py build [--only AT]   # stage 1 + embeddings + scores + blind labelling sheet
  ./.venv-nlp/bin/python ndc/notebooks/climate_passages.py cutoff              # AFTER you return the labelled sheet: applies the pre-declared rule
Writes (ndc/data/processed/): climate_passages.csv.gz (+ _vectors.npy, both gitignored), cutoff_labelling_sheet.csv (blind, for hand labels), cutoff_labelling_key.csv (scores; do not open before labelling).
"""
import glob, re, sys
from pathlib import Path
import numpy as np, pandas as pd

PM = Path("data/processed/parlamint"); PROC = Path("ndc/data/processed")
CLIMATE = re.compile(r"\bclimate\b|\bgreenhouse\b|\bglobal warming\b|\bcarbon\b|\bemissions?\b|\bdecarboni[sz]|\bnet[- ]zero\b|\bfossil fuels?\b", re.I)
SPLIT = re.compile(r"(?<=[.!?])\s+")
MAXW = 150


def passages_of(text):
    s = [x for x in SPLIT.split(text.strip()) if x]
    hit = [i for i, x in enumerate(s) if CLIMATE.search(x)]
    if not hit: return []
    wins = []
    for i in hit:
        a, b = max(0, i - 1), min(len(s) - 1, i + 1)
        if wins and a <= wins[-1][1] + 1: wins[-1][1] = max(wins[-1][1], b)
        else: wins.append([a, b])
    out = []
    for a, b in wins:
        w = " ".join(s[a: b + 1]).split()
        out.append(" ".join(w[:MAXW]))
    return out


def build(only=None):
    rows = []
    for f in sorted(glob.glob(str(PM / "flagged_*.csv.gz"))):
        d = pd.read_csv(f, usecols=["country", "speech_id", "date", "role", "words", "n_climate", "text"])
        if only and d.country.iloc[0] != only: continue
        d = d[(d.words >= 50) & (d.role != "Chairperson") & (d.n_climate > 0)]
        for r in d.itertuples():
            for k, p in enumerate(passages_of(str(r.text) if isinstance(r.text, str) else "")):
                rows.append((r.country, r.speech_id, k, r.date, len(p.split()), p))
        print(r.country if len(d) else f, "speeches", len(d), "passages so far", len(rows), flush=True)
    P = pd.DataFrame(rows, columns=["country", "speech_id", "k", "date", "n_words", "text"]); P["pid"] = np.arange(len(P))
    print("passages:", len(P), "| median words", int(P.n_words.median()))
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2", device="mps"); model.max_seq_length = 256
    V = model.encode(P.text.tolist(), batch_size=128, normalize_embeddings=True, show_progress_bar=False).astype(np.float32)
    ref = []
    for rd in ["indc", "first_ndc", "revised_first_ndc", "second_ndc", "third_ndc"]:
        m = np.load(PROC / f"ndc_passvec_{rd}.npy").mean(0); ref.append(m / np.linalg.norm(m))
    ref = np.mean(ref, 0); ref /= np.linalg.norm(ref)
    P["score"] = V @ ref
    sfx = f"_{only}" if only else ""
    P.to_csv(PROC / f"climate_passages{sfx}.csv.gz", index=False); np.save(PROC / f"climate_passages_vectors{sfx}.npy", V.astype(np.float16))
    print(P.score.describe().round(3).to_string()); print("by country (n, median score):"); print(P.groupby("country").score.agg(["size", "median"]).round(3).T.to_string())
    # blind labelling sheet: 10 random passages from each decile of score, shuffled
    rng = np.random.default_rng(2026); P["decile"] = pd.qcut(P.score, 10, labels=False)
    pick = pd.concat([g.sample(min(10, len(g)), random_state=int(rng.integers(1e9))) for _, g in P.groupby("decile")]).sample(frac=1, random_state=7).reset_index(drop=True)
    pick["id"] = np.arange(1, len(pick) + 1)
    pick[["id", "country", "text"]].assign(label="", note="").to_csv(PROC / f"cutoff_labelling_sheet{sfx}.csv", index=False)
    pick[["id", "pid", "score", "decile"]].to_csv(PROC / f"cutoff_labelling_key{sfx}.csv", index=False)
    print("sheet rows", len(pick))


def cutoff():
    P = pd.read_csv(PROC / "climate_passages.csv.gz"); key = pd.read_csv(PROC / "cutoff_labelling_key.csv"); sh = pd.read_csv(PROC / "cutoff_labelling_sheet_labelled.csv")
    sh["ok"] = sh.label.astype(str).str.strip().isin(["1", "1.0"]); L = key.merge(sh[["id", "ok", "label"]], on="id")
    print("labelled:", len(L), "| unlabelled:", int((~sh.label.astype(str).str.strip().isin(["0", "1", "?", "0.0", "1.0"])).sum()))
    print("precision by score decile:"); print(L.groupby("decile").agg(n=("ok", "size"), precision=("ok", "mean"), min_score=("score", "min")).round(3).to_string())
    best = None
    for c in sorted(L.score):
        above = L[L.score >= c]
        if len(above) >= 30 and above.ok.mean() >= 0.90: best = c; break
    if best is None: print("NO cutoff meets precision >= 0.90 with >= 30 labelled above it; reading needed"); return
    keep = P[P.score >= best]; above = L[L.score >= best]
    print(f"\nCUTOFF c* = {best:.3f}: labelled precision above = {above.ok.mean():.2f} (n={len(above)}); kept {len(keep)} of {len(P)} passages ({len(keep) / len(P):.0%})")
    t = pd.DataFrame({"passages": P.groupby("country").size(), "kept": keep.groupby("country").size()}).fillna(0).astype(int); t["kept_share"] = (t.kept / t.passages).round(2)
    print(t.to_string()); print("countries with < 200 kept passages:", list(t.index[t.kept < 200]))
    nxt = np.quantile(P.score, [i / 10 for i in range(1, 10)]); nxt = nxt[nxt > best][:1]
    print("robustness cutoff (next decile boundary above c*):", nxt.round(3) if len(nxt) else "none")
    pd.DataFrame({"cutoff": [best]}).to_csv(PROC / "climate_passages_cutoff.csv", index=False)


if __name__ == "__main__":
    if sys.argv[1] == "build": build(sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--only" else None)
    else: cutoff()
