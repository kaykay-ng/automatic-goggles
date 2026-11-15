"""Keyword-list review: draw random matches from the real texts so they can be hand-labelled. Rules fixed in ndc/PLAN.md 'KEYWORD-LIST REVIEW'.
Run from final_project/ with the NLP env:
  ./.venv-nlp/bin/python ndc/notebooks/lists_review.py sample            # writes ndc/data/processed/lists_review_samples.csv (+ term shares)
  ./.venv-nlp/bin/python ndc/notebooks/lists_review.py show <list> [a b]  # prints numbered snippets (rows a..b) for reading
  ./.venv-nlp/bin/python ndc/notebooks/lists_review.py score              # reads labels in ndc/data/processed/lists_review_labels.json, prints precision
"""
import glob, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from lts_extract import CX, CATS
from ndc_embed import SECTORS, clean

PROC = Path("ndc/data/processed"); PM = Path("data/processed/parlamint")
OUT = PROC / "lists_review_samples.csv"; LAB = PROC / "lists_review_labels.json"
W = 70
GOAL = re.compile(r"climate[- ]neutral\w*|carbon[- ]neutral\w*|net[- ]zero|zero net|long[- ]term (?:climate )?(?:strategy|goal|target)s?", re.I)
K = r"(?:reduc\w*|neutral\w*|zero|emissions?|carbon|greenhouse|decarboni\w*)"
G2050 = re.compile(rf"{K}[^.]{{0,80}}\b2050\b|\b2050\b[^.]{{0,80}}{K}", re.I)
CLIMATE = re.compile(r"\bclimate\b|\bgreenhouse\b|\bglobal warming\b|\bcarbon\b|\bemissions?\b|\bdecarboni[sz]|\bnet[- ]zero\b|\bfossil fuels?\b", re.I)
SX = {k: re.compile(v, re.I) for k, v in SECTORS.items()}
TERMS = {"net zero / neutrality": r"net[- ]zero|carbon[- ]neutral|climate[- ]neutral", "1.5 degrees": r"1\.5\s?(?:°|degree|ºc|oc)", "just transition": r"just transition",
         "gender": r"\bgender", "methane": r"\bmethane\b", "nature-based solutions": r"nature[- ]based", "loss and damage": r"loss(?:es)? and damage",
         "Article 6 / carbon markets": r"article 6|carbon market|internationally transferred|\bitmos?\b", "coal": r"\bcoal\b",
         "electric vehicles": r"electric (?:vehicle|mobility|car|bus)|e-mobility", "hydrogen": r"hydrogen", "circular economy": r"circular economy"}
TX = {k: re.compile(v, re.I) for k, v in TERMS.items()}
rng = np.random.default_rng(2026)


def ctx(t, m, w=W):
    return (t[max(0, m.start() - w): m.start()].replace("\n", " "), m.group(0), t[m.end(): m.end() + w].replace("\n", " "))


def pick(items, n):
    if not items: return []
    return [items[i] for i in rng.choice(len(items), min(n, len(items)), replace=False)]


def sample():
    rows, shares = [], []
    # --- (2) CATS on strategy texts and on parliament goal windows
    use = ["AT_1", "CZ_2", "DK_1", "FI_1", "FR_1", "GB_1", "HU_1", "IS_1", "LV_1", "NL_1", "NO_1", "PT_1", "RS_1", "SE_1", "SI_1", "TR_1", "UA_2", "BA_1"]
    docs = {n: (PROC / "lts_text" / f"{n}.txt").read_text() for n in use if (PROC / "lts_text" / f"{n}.txt").exists()}
    for n in ("ES_1", "BE_1"): docs[n] = (PROC / "lts_text_translated" / f"{n}.txt").read_text()
    lts = defaultdict(list)
    for n, t in docs.items():
        for k, rx in CX.items():
            for m in rx.finditer(t): lts[k].append((n,) + ctx(t, m))
    par = defaultdict(list)
    goalw, climw = [], []
    for f in sorted(glob.glob(str(PM / "flagged_*.csv.gz"))):
        d = pd.read_csv(f, usecols=["country", "role", "words", "n_climate", "text"])
        d = d[(d.words >= 50) & (d.role != "Chairperson") & (d.n_climate > 0)]; cc = d.country.iloc[0]
        for t in d.text.fillna(""):
            sp = sorted((max(0, m.start() - 300), min(len(t), m.end() + 300)) for m in list(GOAL.finditer(t)) + list(G2050.finditer(t)))
            if not sp: continue
            merged = []
            for a, b in sp:
                if merged and a <= merged[-1][1]: merged[-1][1] = max(merged[-1][1], b)
                else: merged.append([a, b])
            for a, b in merged:
                seg = t[a:b]
                for k, rx in CX.items():
                    for m in rx.finditer(seg): par[k].append((cc,) + ctx(seg, m))
            m0 = next(iter(list(GOAL.finditer(t)) + list(G2050.finditer(t))))
            goalw.append((cc,) + ctx(t, m0, 150))
        # climate-flag precision needs a sample of flagged speeches' matches
        dd = d.sample(min(40, len(d)), random_state=1)
        for t in dd.text.fillna(""):
            m = CLIMATE.search(t)
            if m: climw.append((cc,) + ctx(t, m, 90))
    for k in CATS:
        for src, store in (("strategy", lts), ("parliament goal windows", par)):
            c = Counter(x[2].lower() for x in store[k]); tot = sum(c.values())
            shares.append((k, src, tot, "; ".join(f"{t} {v / tot:.0%}" for t, v in c.most_common(5))))
            for x in pick(store[k], 12): rows.append(("CATS " + src, k) + x)
    for x in pick(goalw, 20): rows.append(("GOAL windows", "goal") + x)
    for x in pick(climw, 25): rows.append(("CLIMATE flag", "climate") + x)
    # --- (1) NDC SECTORS and (5) idea TERMS on NDC texts
    T = pd.read_csv(PROC / "ndc_text_long.csv"); first = T[T.document == "first_ndc"]
    nd = {iso: " ".join(dict.fromkeys(clean(str(v)) for v in g.value)) for iso, g in first.groupby("iso")}
    for k, rx in SX.items():
        items = [(iso,) + ctx(t, m) for iso, t in nd.items() for m in rx.finditer(t)]
        c = Counter(x[2].lower() for x in items); tot = sum(c.values())
        shares.append((k, "NDC sectors", tot, "; ".join(f"{t} {v / tot:.0%}" for t, v in c.most_common(5))))
        for x in pick(items, 12): rows.append(("NDC SECTORS", k) + x)
    third = T[T.document.isin(["third_ndc", "revised_first_ndc"])]
    td = {(d, iso): " ".join(dict.fromkeys(clean(str(v)) for v in g.value)) for (d, iso), g in third.groupby(["document", "iso"])}
    for k, rx in TX.items():
        items = [(iso,) + ctx(t, m) for (d, iso), t in td.items() for m in rx.finditer(t)]
        for x in pick(items, 8): rows.append(("IDEAS", k) + x)
    df = pd.DataFrame(rows, columns=["list", "theme", "source", "left", "match", "right"])
    df["id"] = df.groupby("list").cumcount() + 1
    df.to_csv(OUT, index=False); pd.DataFrame(shares, columns=["theme", "source", "matches", "top_terms"]).to_csv(PROC / "lists_review_term_shares.csv", index=False)
    print(df.groupby(["list", "theme"]).size().to_string()); print("\nTOP TERMS per theme/source:")
    for s in shares: print(f"  {s[0]:14s} {s[1]:24s} n={s[2]:6d}  {s[3]}")


def show(lst, a=1, b=10 ** 6):
    df = pd.read_csv(OUT); df = df[(df["list"] == lst) & (df.id >= a) & (df.id <= b)]
    for r in df.itertuples():
        print(f"{r.id:3d} [{r.theme[:11]}] {str(r.left)[-W:]}«{r.match}»{str(r.right)[:W]}")


def score():
    df = pd.read_csv(OUT); lab = json.loads(LAB.read_text()); rows = []
    for lst, nonrel in lab.items():
        d = df[df["list"] == lst].copy(); d["ok"] = ~d.id.isin(nonrel)
        for th, g in d.groupby("theme"): rows.append((lst, th, len(g), int(g.ok.sum()), g.ok.mean()))
    R = pd.DataFrame(rows, columns=["list", "theme", "n", "relevant", "precision"]); R.to_csv(PROC / "lists_review_precision.csv", index=False)
    print(R.round(2).to_string(index=False))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "sample": sample()
    elif cmd == "show": show(sys.argv[2], *map(int, sys.argv[3:5]))
    elif cmd == "score": score()
