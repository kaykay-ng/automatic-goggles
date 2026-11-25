"""Checks the AI's evidence type for the 242 relevant cited papers against independent, expert-assigned tags: PubMed MeSH descriptors (assigned
by NLM indexers, in the OpenAlex records) and the OpenAlex work type (article / review). The AI saw only a coarse MeSH population tag
(design_mesh: humans / animal / cell), so the population part is not independent; the trial vs observational vs review split is.
MeSH-based evidence type (first rule that applies):
  review       OpenAlex type 'review', or MeSH 'Review Literature as Topic' / 'Meta-Analysis as Topic' without trial descriptors
  animal/cell  MeSH Animals / Rats / Mice / Cells, Cultured / In Vitro Techniques and NOT Humans
  trial        Humans + 'Randomized Controlled Trials as Topic', 'Cross-Over Studies', 'Double-Blind Method', 'Single-Blind Method', 'Controlled Clinical Trials as Topic'
  observational Humans + 'Cohort Studies', 'Prospective Studies', 'Case-Control Studies', 'Follow-Up Studies', 'Longitudinal Studies', 'Cross-Sectional Studies'
  unknown      otherwise (no MeSH, or no design descriptor)
Output: data/processed/paper_mesh_check.json (agreement, Cohen's kappa on papers with a known MeSH type, confusion table). Aggregates only.
Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/paper_mesh_check.py"""
import csv
import gzip
import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

sys.path.insert(0, str(Path(__file__).parent))
from alignment import evidence_type  # noqa: E402

P, RAW = Path("seedoils/data/processed"), Path("seedoils/data/raw")
AI = {}
for fn in ("paper_labels_omega6.csv", "paper_labels_satfat_rodent.csv", "paper_labels_ldl.csv"):
    for r in csv.DictReader(open(P / fn, encoding="utf-8")):
        AI[r["openalex_id"]] = r
rel = {k: r for k, r in AI.items() if r["relevance"] in ("yes", "partly")}
W = {}
with gzip.open(RAW / "openalex_works.jsonl.gz", "rt", encoding="utf-8") as f:
    for l in f:
        w = json.loads(l).get("work") or {}
        if w.get("id") in rel:
            W[w["id"]] = w
TRIAL = {"Randomized Controlled Trials as Topic", "Cross-Over Studies", "Double-Blind Method", "Single-Blind Method", "Controlled Clinical Trials as Topic"}
OBS = {"Cohort Studies", "Prospective Studies", "Case-Control Studies", "Follow-Up Studies", "Longitudinal Studies", "Cross-Sectional Studies"}
ANIMAL = {"Animals", "Rats", "Mice", "Cells, Cultured", "In Vitro Techniques", "Rats, Sprague-Dawley", "Rats, Wistar", "Mice, Inbred C57BL", "Cell Line"}


def mesh_type(w):
    d = {m["descriptor_name"] for m in (w.get("mesh") or [])}
    if w.get("type") == "review" or ({"Review Literature as Topic", "Meta-Analysis as Topic"} & d and not TRIAL & d):
        return "review / statement"
    if ANIMAL & d and "Humans" not in d:
        return "animal / cell"
    if "Humans" in d and TRIAL & d:
        return "human trials / meta of trials"
    if "Humans" in d and OBS & d:
        return "human observational"
    return "unknown"


rows = [{"ai": evidence_type(r), "mesh": mesh_type(W.get(k, {}))} for k, r in rel.items()]
D = pd.DataFrame(rows); K = D[D.mesh != "unknown"]
# the AI's 'review' includes meta-analyses of trials when no new data; compare on 4 shared classes, AI 'other' kept as a mismatch
out = {"relevant_papers": int(len(D)), "with_openalex_record": int(len(W)), "mesh_type_known": int(len(K)),
       "mesh_type_counts": D.mesh.value_counts().to_dict(), "agreement_pct": round(float((K.ai == K.mesh).mean() * 100), 1),
       "kappa": round(float(cohen_kappa_score(K.ai, K.mesh)), 3), "confusion_ai_rows_mesh_cols": pd.crosstab(K.ai, K.mesh).to_dict()}
(P / "paper_mesh_check.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k != "confusion_ai_rows_mesh_cols"}, indent=1)); print(pd.crosstab(K.ai, K.mesh, margins=True))
