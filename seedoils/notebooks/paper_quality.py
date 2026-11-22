"""Are the papers Reddit cites 'academically strong'? Scorecard per subreddit and period, over (person, paper) citations.
Quality signals (all proxies; none says a paper is right or wrong): (1) relevance to the seed-oil question (labelled papers only: the 499 papers of the four seed-oil communities), (2) kind of evidence (labelled papers),
(3) scholarly citations (OpenAlex cited_by_count), (4) venue tier from OpenAlex source lists (core journal, MEDLINE, level 2-3 national lists), (5) retraction, (6) age.
A citation = one author citing one paper at least once in the subreddit and period. Output: data/processed/paper_quality.csv (aggregates only).
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/paper_quality.py"""
import glob, gzip, json
from pathlib import Path
import numpy as np, pandas as pd
P = Path("seedoils/data/processed"); CUT = pd.Timestamp("2024-01-01").timestamp()
meta, idmap = {}, {}
with gzip.open("seedoils/data/raw/openalex_works.jsonl.gz", "rt") as fh:
    for l in fh:
        rec = json.loads(l)
        if not rec.get("work"):
            continue
        w = rec["work"]; oid = w["id"]; src = ((w.get("primary_location") or {}).get("source")) or {}; lists = set(src.get("listed_in") or [])
        meta[oid] = dict(cites=w.get("cited_by_count") or 0, retracted=bool(w.get("is_retracted")), year=w.get("publication_year"), has_src=bool(src), core=bool(src.get("is_core")),
                         medline="medline" in lists, top=any(x in lists for x in ("jufo-2", "jufo-3", "norway-2", "ki-jl-3", "dongbi-a", "doyens", "vabb-shw")), type=w.get("type"))
        ids = w.get("ids") or {}
        for k, v in ids.items():
            if v and k in ("doi", "pmid", "pmcid"): idmap[(k, str(v).lower().replace("https://doi.org/", "").replace("https://pubmed.ncbi.nlm.nih.gov/", "").strip("/").replace("https://www.ncbi.nlm.nih.gov/pmc/articles/", "").strip("/"))] = oid
C = pd.read_csv(P / "citations.csv.gz", keep_default_na=False)
C["key"] = [(t, str(v).lower().strip("/")) for t, v in zip(C.id_type, C.id_value)]; C["oid"] = C.key.map(idmap)
print("citation rows", len(C), "resolved to a work", C.oid.notna().mean().round(3))
C = C[C.oid.notna()].copy()
C["period"] = np.where(C.created_utc >= CUT, "from 2024", "before 2024"); C = C.drop_duplicates(["subreddit", "period", "author", "oid"])
M = pd.DataFrame.from_dict(meta, orient="index"); C = C.join(M, on="oid")
lab = pd.concat([pd.read_csv(P / f) for f in ("paper_labels_omega6.csv", "paper_labels_satfat_rodent.csv", "paper_labels_ldl.csv")]).drop_duplicates("openalex_id").set_index("openalex_id")
C = C.join(lab[["relevance", "direction", "population", "design"]], on="oid")
def ev(r):
    if pd.isna(r.population): return None
    if r.population == "humans" and r.design in ("rct", "meta_trials"): return "human trials"
    if r.population == "humans" and r.design in ("cohort", "meta_observational"): return "human observational"
    if r.population in ("animals", "cells") or r.design in ("animal_experiment", "in_vitro"): return "animal or cell"
    return "review or other"
C["evidence"] = C.apply(ev, axis=1); rows = []
for (s, p), g in C.groupby(["subreddit", "period"]):
    L = g[g.relevance.notna()]; R = L[L.relevance == "yes"]
    rows.append({"subreddit": s, "period": p, "citations": len(g), "papers": g.oid.nunique(), "authors": g.author.nunique(),
                 "labelled_share": round(len(L) / len(g) * 100, 1), "relevant_share_of_labelled": round((L.relevance == "yes").mean() * 100, 1) if len(L) else None,
                 "animal_cell_share_of_relevant": round((R.evidence == "animal or cell").mean() * 100, 1) if len(R) else None, "human_trial_share_of_relevant": round((R.evidence == "human trials").mean() * 100, 1) if len(R) else None,
                 "median_scholarly_cites": float(g.cites.median()), "share_under_50_cites": round((g.cites < 50).mean() * 100, 1), "share_core_journal": round(g.core.mean() * 100, 1),
                 "share_medline": round(g.medline.mean() * 100, 1), "share_top_tier_list": round(g.top.mean() * 100, 1), "share_no_source": round((~g.has_src).mean() * 100, 1),
                 "retracted": int(g.retracted.sum()), "median_age_years": float((2026 - g.year).median())})
R = pd.DataFrame(rows); R.to_csv(P / "paper_quality.csv", index=False); pd.set_option("display.width", 250, "display.max_columns", 30); print(R.T.to_string())
