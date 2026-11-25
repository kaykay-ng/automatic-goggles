"""Alignment of the online and scientific communities on seed oils.

Run from final_project/ after the LLM labels exist:
  ../.venv/bin/python seedoils/notebooks/alignment.py   -> seedoils/data/processed/alignment_summary.txt (aggregates only, no Reddit text)

Inputs (labels are blind LLM annotations with reasons; see seedoils/PLAN.md):
  paper_labels_omega6.csv, paper_labels_satfat_rodent.csv, paper_labels_ldl.csv  (what each paper concludes about seed oils / LA / PUFA)
  comment_labels_part1-3.csv + comments_key.csv                                  (each comment's position: H harmful, NH not harmful, M mixed, O other)
1. Science: direction (harm / no_effect / benefit / mixed) of the papers relevant to the question, overall and split by population (humans vs
   animals/cells) and by evidence type (human trials and meta-analyses of trials; human observational; animal/cell; narrative reviews).
2. Online: position shares per subreddit x period in the OPINION sample (random seed-oil-relevant comments), among comments that take a
   position (H/NH/M) and including O.
3. Matching (CITING sample): for comments that say 'harmful' (H) and 'not harmful' (NH), what the papers they cite conclude and what kind of
   evidence they are. A cited paper counts once per citing comment.
"""
import csv
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
SUBS = ["StopEatingSeedOils", "ScientificNutrition"]


def evidence_type(p):
    if p["population"] == "humans" and p["design"] in ("rct", "meta_trials"):
        return "human trials / meta of trials"
    if p["population"] == "humans" and p["design"] in ("cohort", "meta_observational"):
        return "human observational"
    if p["population"] in ("animals", "cells") or p["design"] in ("animal_experiment", "in_vitro"):
        return "animal / cell"
    if p["design"] == "narrative_review":
        return "review / statement"
    return "other"


def share(c, keys):
    n = sum(c[k] for k in keys)
    return ", ".join(f"{k} {c[k]} ({c[k] / n:.0%})" for k in keys) + f"  [n={n}]" if n else "n=0"


def main():
    papers = {}
    for f in ("paper_labels_omega6.csv", "paper_labels_satfat_rodent.csv", "paper_labels_ldl.csv"):
        for r in csv.DictReader(open(PROC / f, encoding="utf-8")):
            papers[r["openalex_id"]] = r
    rel = {k: p for k, p in papers.items() if p["relevance"] in ("yes", "partly")}
    D = ["harm", "no_effect", "benefit", "mixed"]
    L = [f"SCIENCE: {len(papers)} labelled papers, {len(rel)} relevant to seed oils / LA / PUFA "
         f"(yes {sum(p['relevance'] == 'yes' for p in rel.values())}, partly {sum(p['relevance'] == 'partly' for p in rel.values())})",
         "  all relevant papers:          " + share(Counter(p["direction"] for p in rel.values()), D)]
    by = defaultdict(Counter)
    for p in rel.values():
        by[evidence_type(p)][p["direction"]] += 1
    for t in ("human trials / meta of trials", "human observational", "animal / cell", "review / statement", "other"):
        L.append(f"  {t:30} " + share(by[t], D))
    hard = Counter(p["direction"] for p in rel.values() if p["population"] == "humans" and p["outcome"] == "hard")
    L.append("  human studies, hard outcomes: " + share(hard, D))
    for o in ("hard", "intermediate", "mechanistic", "other"):
        L.append(f"  outcome {o:12}              " + share(Counter(p["direction"] for p in rel.values() if p["outcome"] == o), D))
    # sensitivity: harm verdicts resting only on intermediate markers (e.g. lower omega-3 status) set aside
    sens = Counter(p["direction"] for p in rel.values() if not (p["direction"] == "harm" and p["outcome"] == "intermediate"))
    L.append("  sensitivity, without harm-by-intermediate-marker: " + share(sens, D))

    key = {r["item_id"]: r for r in csv.DictReader(open(PROC / "comments_key.csv"))}
    lab = {}
    for i in (1, 2, 3):
        for r in csv.DictReader(open(PROC / f"comment_labels_part{i}.csv", encoding="utf-8")):
            lab[r["item_id"]] = r
    P = ["H", "NH", "M", "O"]
    L.append(f"\nONLINE (opinion sample; {sum(1 for k in key.values() if 'opinion' in k['samples'])} random seed-oil-relevant comments): "
             "H harmful, NH not harmful, M mixed, O no position")
    for s in SUBS:
        for per in ("pre2024", "from2024"):
            c = Counter(lab[i]["position"] for i, k in key.items() if "opinion" in k["samples"] and k["side"] == s and k["period"] == per and i in lab)
            L.append(f"  {s:20} {per:9} " + share(c, P))
            L.append(f"  {'':20} {'':9} among positions: " + share(c, ["H", "NH", "M"]))

    L.append("\nMATCHING (citing sample): what the papers cited by each comment position conclude, and what evidence they are")
    for s in SUBS + ["both sides"]:
        for pos in ("H", "NH"):
            dirs, ev, n_c = Counter(), Counter(), 0
            for i, k in key.items():
                if "citing" not in k["samples"] or i not in lab or lab[i]["position"] != pos or (s != "both sides" and k["side"] != s):
                    continue
                n_c += 1
                for w in filter(None, k["cited_works"].split("|")):
                    p = papers.get(w)
                    if p is None:
                        continue
                    dirs[p["direction"] if p["relevance"] != "no" else "not about seed oils"] += 1
                    ev[evidence_type(p)] += 1
            if n_c:
                L.append(f"  {s:20} comments '{pos}' (n={n_c}): cited papers conclude " + share(dirs, D + ["not about seed oils"]))
                L.append(f"  {'':20} {'':16} evidence type: " + share(ev, ["human trials / meta of trials", "human observational",
                                                                           "animal / cell", "review / statement", "other"]))
    conf = Counter(r["confidence"] for r in lab.values())
    pconf = Counter(p["confidence"] for p in papers.values())
    L.append(f"\nlabel confidence: comments {dict(conf)}; papers {dict(pconf)}")
    text = "\n".join(L)
    (PROC / "alignment_summary.txt").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
