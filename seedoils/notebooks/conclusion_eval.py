"""Compares the non-expert conclusion checks (conclusion_checks_<initials>.csv from check_conclusions.html) with the AI's paper direction labels.
Reported: per labeller agreement and Cohen's kappa on H/B/E/M (papers the labeller marked U = unclear are counted separately), agreement on
'harm vs not harm' (the split Figure 3a's harm shares use), a confusion table, and agreement between labellers if several.
Output: data/processed/conclusion_eval.json. Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/conclusion_eval.py"""
import csv
import glob
import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

P = Path("seedoils/data/processed")
AI = {}
for fn in ("paper_labels_omega6.csv", "paper_labels_satfat_rodent.csv", "paper_labels_ldl.csv"):
    for r in csv.DictReader(open(P / fn, encoding="utf-8")):
        AI[r["openalex_id"]] = r
D = {"harm": "H", "benefit": "B", "no_effect": "E", "mixed": "M"}
key = pd.read_csv(P / "conclusion_check_key.csv").set_index("item")
ai = key.openalex_id.map(lambda k: D.get(AI[k]["direction"], "U"))
files = sorted(glob.glob(str(P / "conclusion_checks_*.csv")))
if not files:
    raise SystemExit("no conclusion_checks_*.csv in data/processed/: export it from seedoils/check_conclusions.html first")
out = {"papers": int(len(key)), "conclusion_rule_counts": key.conclusion_rule.value_counts().to_dict(), "labellers": {}}
H = {}
for f in files:
    who = Path(f).stem.replace("conclusion_checks_", ""); h = pd.read_csv(f, dtype=str).fillna("").set_index("item").label; h.index = h.index.astype(int); h = h.reindex(key.index).fillna("")
    H[who] = h; ok = h.isin(list("HBEM")) & ai.isin(list("HBEM"))
    out["labellers"][who] = {"labelled": int((h != "").sum()), "unclear": int((h == "U").sum()), "compared": int(ok.sum()),
                             "agreement_pct": round(float((h[ok] == ai[ok]).mean() * 100), 1), "kappa_HBEM": round(float(cohen_kappa_score(h[ok], ai[ok])), 3),
                             "agreement_harm_vs_not_pct": round(float(((h[ok] == "H") == (ai[ok] == "H")).mean() * 100), 1),
                             "kappa_harm_vs_not": round(float(cohen_kappa_score(h[ok] == "H", ai[ok] == "H")), 3),
                             "confusion_ai_rows_hand_cols": pd.crosstab(ai[ok], h[ok]).to_dict(), "disagreement_items": [int(i) for i in key.index[ok & (h != ai)]]}
if len(H) >= 2:
    a, b = list(H.values())[:2]; ok = a.isin(list("HBEM")) & b.isin(list("HBEM"))
    out["between_labellers"] = {"pair": "-".join(list(H)[:2]), "compared": int(ok.sum()), "agreement_pct": round(float((a[ok] == b[ok]).mean() * 100), 1), "kappa": round(float(cohen_kappa_score(a[ok], b[ok])), 3)}
(P / "conclusion_eval.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
