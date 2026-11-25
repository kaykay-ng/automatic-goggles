"""Stance of citing comments towards the papers both sides cite: summarise the hand labels, then test a zero-shot model against them.

Run from final_project/ AFTER labelling (seedoils/label_stance.html -> seedoils/data/processed/stance_labels.csv):
  ./.venv-nlp/bin/python seedoils/notebooks/stance_eval.py summary    # hand labels by side x community (joins the blind key)
  ./.venv-nlp/bin/python seedoils/notebooks/stance_eval.py zeroshot   # zero-shot NLI model on the same items -> agreement with the hand labels
Outputs: seedoils/data/processed/stance_summary.txt, stance_zeroshot.csv (item_id, model label, scores; no comment text).

Zero-shot model: MoritzLaurer/deberta-v3-large-zeroshot-v2.0 (Hugging Face; ~1.7 GB download on first use), via the transformers
zero-shot pipeline. The premise is the ~300-word CITATION WINDOW around the link to the paper (same text the labeller sees first), with the
link shown as '[link to the cited study]'; the three candidate hypotheses name the cited paper:
  'The author uses the study "<title>" as evidence for their own point.' / '... attacks or discredits ...' / '... mentions ... without taking a position.'
  (Worded like the hand-labelling codes: how the commenter treats the paper.)
~300 words fits the model's 512-token limit; when the link was not found the window is the start of the text.
Agreement: accuracy and Cohen's kappa on items the human labelled S, D or N (U excluded), plus a confusion table.
Rule of thumb before scaling to all citing comments: kappa >= 0.6.
"""
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
COMMS = {"2": "omega-6 / linoleic acid", "10": "rodent fat carcinogenesis", "4": "saturated fat & CVD", "5": "LDL / lipoproteins"}
MODEL = "MoritzLaurer/deberta-v3-large-zeroshot-v2.0"


LABELS = "stance_labels.csv"  # human labels; pass --labels stance_labels_claude.csv for the LLM reference labels (19 Nov)


def load():
    p = PROC / LABELS
    labels = {r["item_id"]: r for r in csv.DictReader(open(p, encoding="utf-8"))} if p.exists() else {}
    key = {r["item_id"]: r for r in csv.DictReader(open(PROC / "stance_key.csv"))}
    sheet = {r["item_id"]: r for r in csv.DictReader(open(PROC / "stance_sheet.csv", encoding="utf-8"))}
    return labels, key, sheet


def summary():
    labels, key, _ = load()
    done = {i: r["stance"] for i, r in labels.items() if r["stance"]}
    lines = [f"labelled {len(done)} of {len(key)} items; overall {dict(Counter(done.values()))}"]
    for c, name in COMMS.items():
        lines.append(f"\n{name}:")
        for side in ("StopEatingSeedOils", "ScientificNutrition"):
            s = Counter(done[i] for i, k in key.items() if k["community"] == c and k["side"] == side and i in done)
            n = sum(s.values())
            lines.append(f"  {side:20} n={n:3}  " + "  ".join(f"{k} {s[k]:2} ({s[k] / n:.0%})" if n else f"{k} -" for k in "SDNU"))
            if any("claim" in labels[i] for i in labels):
                cl = Counter(labels[i]["claim"] for i, k in key.items()
                             if k["community"] == c and k["side"] == side and done.get(i) == "S")
                if cl:
                    lines.append(f"  {'':20} claims when S: " + ", ".join(f"{k} {v}" for k, v in cl.most_common()))
    for side in ("StopEatingSeedOils", "ScientificNutrition"):
        cl = Counter(labels[i].get("claim") for i, k in key.items() if k["side"] == side and done.get(i) == "S")
        if any(cl):
            n = sum(cl.values())
            lines.append(f"\nALL communities, {side}, claim accuracy when the paper is used as evidence (n={n}): "
                         + ", ".join(f"{k} {v} ({v / n:.0%})" for k, v in cl.most_common()))
    lines.insert(0, f"labels file: {LABELS}")
    text = "\n".join(lines)
    (PROC / "stance_summary.txt").write_text(text + "\n")
    print(text)


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(a) | set(b)) / n ** 2
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def zeroshot():
    from transformers import pipeline
    labels, key, sheet = load()
    clf = pipeline("zero-shot-classification", model=MODEL, device="mps")
    rows, human, model = [], [], []
    for i, r in sheet.items():
        t = r["paper_title"]
        cands = {f'The author uses the study "{t}" as evidence for their own point.': "S",
                 f'The author attacks or discredits the study "{t}".': "D",
                 f'The author mentions the study "{t}" without taking a position on it.': "N"}
        text = r["citation_window"].replace("[[CITED STUDY LINK]]", "[link to the cited study]")
        out = clf(text, list(cands), hypothesis_template="{}", multi_label=False)
        lab = cands[out["labels"][0]]
        sc = {cands[l]: round(s, 3) for l, s in zip(out["labels"], out["scores"])}
        rows.append((i, lab, sc["S"], sc["D"], sc["N"]))
        h = labels.get(i, {}).get("stance", "")
        if h in ("S", "D", "N"):
            human.append(h); model.append(lab)
    with open(PROC / "stance_zeroshot.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item_id", "model_label", "p_support", "p_dispute", "p_neutral"])
        w.writerows(rows)
    if human:
        acc = sum(a == b for a, b in zip(human, model)) / len(human)
        print(f"items with a human S/D/N label: {len(human)}; accuracy {acc:.2f}; Cohen's kappa {kappa(human, model):.2f}")
        conf = Counter(zip(human, model))
        print("confusion (rows human, columns model):\n       S    D    N")
        for h in "SDN":
            print(f"  {h}  " + " ".join(f"{conf[(h, m)]:4}" for m in "SDN"))
    else:
        print("no hand labels yet; model labels written to stance_zeroshot.csv")


if __name__ == "__main__":
    if "--labels" in sys.argv:
        LABELS = sys.argv[sys.argv.index("--labels") + 1]
    {"summary": summary, "zeroshot": zeroshot}[sys.argv[1]]()
