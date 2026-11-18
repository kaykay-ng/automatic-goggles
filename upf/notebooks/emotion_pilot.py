"""Emotion classifier pilot (upf/PLAN.md 'EMOTION CLASSIFIER PILOT', pre-declared checks C1-C3; C4 needs the user's hand labels).
Model: cardiffnlp/twitter-roberta-large-emotion-latest (MIT), read from the local Hugging Face cache only (offline; downloaded separately with the user's approval).
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/emotion_pilot.py
"""
import os, re, sys, time
os.environ["HF_HUB_OFFLINE"] = "1"; os.environ["TRANSFORMERS_OFFLINE"] = "1"
from pathlib import Path
import numpy as np, pandas as pd, torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
sys.path.insert(0, str(Path(__file__).parent))
import habits as H                                              # same seeds and sampling rule as the H11 and Yelp draws
import elsewhere as E                                           # EmoLex (LEX), food words (FOOD), tokenizer, VAD valence

MODEL = "cardiffnlp/twitter-roberta-large-emotion-latest"
POS = ["joy", "love", "optimism", "trust"]; NEGE = ["anger", "disgust", "sadness", "pessimism"]
PLUT = ["anger", "anticipation", "disgust", "fear", "joy", "sadness", "surprise", "trust"]
NEGW = {"not", "no", "never", "cannot", "none", "nothing", "nobody", "nowhere", "neither", "nor"}


def sample():
    """identical to yelp_pilot.py: 9% of matched-product reviews -> 200,000 -> 20,000"""
    import gzip, json
    P = pd.read_csv(H.CACHE / "products.csv.gz", usecols=["parent_asin"]); keep = set(P.parent_asin); rows = []
    with gzip.open(H.RAW / "Grocery_and_Gourmet_Food.jsonl.gz", "rt") as f:
        for line in f:
            i = line.find('"parent_asin": "'); a = line[i + 16: line.find('"', i + 16)]
            if a not in keep or H.RNG.random() > 0.09: continue
            r = json.loads(line); t = (r.get("title") or "") + ". " + (r.get("text") or "")
            if r.get("rating") is None or len(t.split()) < 3: continue
            rows.append((t, float(r["rating"])))
    D = pd.DataFrame(rows, columns=["text", "stars"]).sample(min(200_000, len(rows)), random_state=1).reset_index(drop=True)
    return D.sample(20_000, random_state=5).reset_index(drop=True)


def classify(texts, bs=32, model=MODEL):
    tok = AutoTokenizer.from_pretrained(model); mod = AutoModelForSequenceClassification.from_pretrained(model)
    dev = "mps" if torch.backends.mps.is_available() else "cpu"; mod.to(dev).eval()
    labels = [mod.config.id2label[i] for i in range(mod.config.num_labels)]
    order = np.argsort([len(t) for t in texts]); out = np.zeros((len(texts), len(labels)), dtype=np.float32); t0 = time.time()
    with torch.no_grad():
        for k in range(0, len(texts), bs):
            idx = order[k:k + bs]
            enc = tok([texts[i] for i in idx], truncation=True, max_length=512, padding=True, return_tensors="pt").to(dev)
            out[idx] = torch.sigmoid(mod(**enc).logits).float().cpu().numpy()
            if k % (bs * 100) == 0: print(f"  {k:,}/{len(texts):,} reviews, {time.time() - t0:.0f}s", flush=True)
    print(f"classified {len(texts):,} reviews in {time.time() - t0:.0f}s on {dev} ({len(texts) / (time.time() - t0):.1f} reviews/s)")
    return pd.DataFrame(out, columns=labels), (tok, mod, dev, labels)


def emolex(text):
    c = dict.fromkeys(PLUT, 0); n = 0
    for w in E.TOK.findall(text.lower()):
        w = E.norm(w, E.LEX); n += 1
        if w in E.LEX and w not in E.FOOD:
            for e in E.LEX[w] & set(PLUT): c[e] += 1
    return {e: c[e] / max(n, 1) for e in PLUT}


def has_neg(text):
    return any(w in NEGW or w.endswith("n't") for w in E.TOK.findall(text.lower()))


if __name__ == "__main__":
    S = sample()
    old = pd.read_csv(H.CACHE / "yelp_pilot.csv.gz")
    print(f"sample {len(S):,} reviews; identical to the Yelp pilot sample: {bool((old.stars.values == S.stars.values).all() and np.allclose(old.vad.values, [E.valence(t)[0] for t in S.text], equal_nan=True))}")
    C, (tok, mod, dev, labels) = classify(S.text.tolist())
    L = pd.DataFrame([emolex(t) for t in S.text]); S["neg"] = [has_neg(t) for t in S.text]; S["vad"] = old.vad.values
    S["cls_comp"] = C[POS].mean(1) - C[NEGE].mean(1); S["lex_comp"] = L[["joy", "trust"]].mean(1) - L[["anger", "disgust", "sadness"]].mean(1)
    m = ((S.stars <= 2) | (S.stars >= 4)).values; y = (S.stars >= 4).astype(int).values

    print("\n== C1 STARS == mean in 1-2 vs 4-5 star reviews (classifier probability | EmoLex share of words):")
    right = 0
    for e in POS + NEGE:
        lo, hi = C.loc[S.stars <= 2, e].mean(), C.loc[S.stars >= 4, e].mean(); ok = (hi > lo) if e in POS else (hi < lo); right += ok
        lx = f"{L.loc[S.stars <= 2, e].mean():.4f} -> {L.loc[S.stars >= 4, e].mean():.4f}" if e in L else "n/a (not in EmoLex)"
        print(f"  {e:10s} classifier {lo:.3f} -> {hi:.3f} {'OK' if ok else 'WRONG'} | EmoLex {lx}")
    a_cls = H.auc(S.cls_comp.values[m], y[m]); a_lex = H.auc(S.lex_comp.values[m], y[m]); mv = m & S.vad.notna().values; a_vad = H.auc(S.vad.values[mv], y[mv])
    print(f"  directions right {right}/8 (bar >= 7); composite AUC classifier {a_cls:.3f} | EmoLex {a_lex:.3f} | VAD valence {a_vad:.3f} (bar: classifier >= VAD)")
    print(f"  C1 {'PASSES' if right >= 7 and a_cls >= a_vad else 'FAILS'}")

    print("\n== C2 NEGATION ==")
    for nm, sel in (("with a negator", S.neg.values), ("without", ~S.neg.values)):
        mm = m & sel; ac, al = H.auc(S.cls_comp.values[mm], y[mm]), H.auc(S.lex_comp.values[mm], y[mm])
        print(f"  reviews {nm:15s} n={mm.sum():6,}: AUC classifier {ac:.3f} | EmoLex {al:.3f} | advantage {ac - al:+.3f}")
    bad = (S.stars <= 2).values & S.neg.values
    print(f"  1-2 star reviews with a negator (n={bad.sum():,}): joy classifier share present {np.mean(C.joy.values[bad] >= .5):.1%} | EmoLex share with any joy word {np.mean(L.joy.values[bad] > 0):.1%}")
    test = ["Not happy with the product.", "Not tasty at all.", "Not bad at all, I'd buy again.", "Great morning treat for the kids.", "Arrived broken and stale.", "I was afraid it would be too sweet but it's perfect."]
    enc = tok(test, padding=True, return_tensors="pt").to(dev)
    with torch.no_grad(): pr = torch.sigmoid(mod(**enc).logits).cpu().numpy()
    for t, p in zip(test, pr):
        top = sorted(zip(labels, p), key=lambda x: -x[1])[:3]; lx = {e: round(v, 2) for e, v in emolex(t).items() if v > 0}
        print(f"   {t!r:55s} classifier {', '.join(f'{a} {b:.2f}' for a, b in top)} | EmoLex {lx}")

    print("\n== C3 'TREAT' ==")
    tr = S.text.str.contains(r"\btreats?\b", case=False, regex=True).values
    for e in ("anger", "disgust", "fear"):
        print(f"  {e:8s} classifier: with 'treat' {C.loc[tr, e].mean():.3f} vs without {C.loc[~tr, e].mean():.3f} | EmoLex: {L.loc[tr, e].mean():.4f} vs {L.loc[~tr, e].mean():.4f}   (n with 'treat' {tr.sum():,}; mean stars {S.stars[tr].mean():.2f} vs {S.stars[~tr].mean():.2f})")

    print("\nshare of reviews where each emotion is present (p >= 0.5):", {e: f"{(C[e] >= .5).mean():.1%}" for e in labels})
    print("\nmost-joyful 1-star reviews by the classifier (where it may be fooled):")
    w = C.joy[(S.stars == 1)].sort_values(ascending=False).head(4)
    for i, p in w.items(): print(f"   {p:.2f} | {S.text[i][:140].replace(chr(10), ' ')}")
    out = pd.concat([S[["stars", "neg", "vad"]], C.add_prefix("cls_"), L.add_prefix("lex_")], axis=1); out.to_csv(H.CACHE / "emotion_pilot.csv.gz", index=False)
    print("saved", H.CACHE / "emotion_pilot.csv.gz")
