"""Compares the hand checks of the AI paper labels (paper_checks_<initials>.csv from check_papers.html) with the AI labels (paper_labels_*.csv).
Reported per labeller (and between labellers if several): agreement and Cohen's kappa on relevance (relevant = yes or partly, and the 3 levels),
on the conclusion (harm / benefit / no effect / mixed; 'unclear' left out) for papers both call relevant, and on the kind of evidence (the AI's
evidence type from its population + design, alignment.evidence_type); a confusion table for the conclusion; and the Figure 3a shares (harm /
benefit among human trials, among animal and cell studies) computed from the hand labels vs the AI labels on the same papers.
Output: data/processed/paper_eval.json (aggregates only). Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/paper_eval.py"""
import csv
import glob
import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

sys.path.insert(0, str(Path(__file__).parent))
from alignment import evidence_type  # noqa: E402

P = Path("seedoils/data/processed")
AI = {}
for fn in ("paper_labels_omega6.csv", "paper_labels_satfat_rodent.csv", "paper_labels_ldl.csv"):
    for r in csv.DictReader(open(P / fn, encoding="utf-8")):
        AI[r["openalex_id"]] = r
key = pd.read_csv(P / "paper_check_key.csv").set_index("item").openalex_id
REL = {"yes": "Y", "partly": "P", "no": "N"}; DIR = {"harm": "H", "benefit": "B", "no_effect": "E", "mixed": "M"}
EVI = {"human trials / meta of trials": "T", "human observational": "O", "review / statement": "R", "animal / cell": "A", "other": "X"}
ai = pd.DataFrame([{"item": i, "rel": REL.get(AI[k]["relevance"], ""), "dir": DIR.get(AI[k]["direction"], ""), "ev": EVI[evidence_type(AI[k])]} for i, k in key.items()]).set_index("item")
files = sorted(glob.glob(str(P / "paper_checks_*.csv")))
if not files:
    raise SystemExit("no paper_checks_*.csv in data/processed/: export it from seedoils/check_papers.html first")
out = {"papers": int(len(key)), "labellers": {}}


def comp(a, b, name):
    ok = (a != "") & (b != "")
    if ok.sum() < 2:
        return {"n": int(ok.sum())}
    return {"n": int(ok.sum()), "agreement_pct": round(float((a[ok] == b[ok]).mean() * 100), 1), "kappa": round(float(cohen_kappa_score(a[ok], b[ok])), 3)}


def fig3a(dirs, evs, rel):
    m = rel.isin(["Y", "P"]) & dirs.isin(list("HBEM"))
    res = {}
    for nm, code in (("human trials", "T"), ("animal / cell", "A"), ("human observational", "O")):
        s = dirs[m & (evs == code)]
        res[nm] = {"n": int(len(s)), "harm_pct": round(float((s == "H").mean() * 100), 1) if len(s) else None, "benefit_pct": round(float((s == "B").mean() * 100), 1) if len(s) else None}
    return res


H = {}
for f in files:
    who = Path(f).stem.replace("paper_checks_", "")
    h = pd.read_csv(f, dtype=str).fillna("").set_index("item"); h.index = h.index.astype(int); h = h.reindex(ai.index).fillna("")
    H[who] = h
    both_rel = ai.rel.isin(["Y", "P"]) & h.relevance.isin(["Y", "P"])
    d_ok = both_rel & ai.dir.isin(list("HBEM")) & h.direction.isin(list("HBEM"))
    out["labellers"][who] = {
        "done": int((h.relevance != "").sum()),
        "relevance_binary": comp(ai.rel.isin(["Y", "P"]).map({True: "rel", False: "not"}).where(h.relevance != "", ""), h.relevance.isin(["Y", "P"]).map({True: "rel", False: "not"}).where(h.relevance != "", ""), "rel2"),
        "relevance_3_levels": comp(ai.rel, h.relevance, "rel3"),
        "conclusion_on_papers_both_call_relevant": comp(ai.dir.where(d_ok, ""), h.direction.where(d_ok, ""), "dir"),
        "hand_unclear_among_relevant": int((both_rel & (h.direction == "U")).sum()),
        "evidence_type": comp(ai.ev.where(h.evidence != "", ""), h.evidence, "ev"),
        "conclusion_confusion_ai_rows_hand_cols": pd.crosstab(ai.dir[d_ok], h.direction[d_ok]).to_dict(),
        "fig3a_hand": fig3a(h.direction, h.evidence, h.relevance), "fig3a_ai_same_papers": fig3a(ai.dir, ai.ev, ai.rel),
        "disagreements_conclusion_items": [int(i) for i in ai.index[d_ok & (ai.dir != h.direction)]]}
if len(H) >= 2:
    ks = list(H); a, b = H[ks[0]], H[ks[1]]
    out["between_labellers"] = {"pair": f"{ks[0]}-{ks[1]}", "relevance_3_levels": comp(a.relevance, b.relevance, "r"),
                                "conclusion": comp(a.direction.where(a.direction.isin(list('HBEM')), ''), b.direction.where(b.direction.isin(list('HBEM')), ''), "d"),
                                "evidence_type": comp(a.evidence, b.evidence, "e")}
(P / "paper_eval.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
