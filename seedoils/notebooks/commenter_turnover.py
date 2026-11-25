"""Commenters per calendar year and the share who commented there for the first time that year (excludes [deleted] and AutoModerator). Appends/replaces facts in data/processed/artifact/facts.json.
Replaces the misleading '91% of commenters from 2024 had not commented before' framing (a three-year window against a small base) with per-year counts.
Run from final_project/ after artifact_data.py:  ./.venv-nlp/bin/python seedoils/notebooks/commenter_turnover.py"""
from seedoil_common import is_bot, not_bot  # shared bot rule: AutoModerator + names ending in 'bot'
import glob, gzip, json
from pathlib import Path
import pandas as pd
F = Path("seedoils/data/processed/artifact/facts.json"); d = json.loads(F.read_text()); rows = {r["key"]: r for r in d["rows"]}
def yearly(sub):
    r = []
    with gzip.open(glob.glob(f"seedoils/data/raw/*{sub}_comments.jsonl.gz")[0], "rt", encoding="utf-8") as f:
        for l in f:
            x = json.loads(l); r.append((x["author"], int(x["created_utc"])))
    C = pd.DataFrame(r, columns=["a", "t"]); C = C[(~C.a.isin(["[deleted]", "AutoModerator"]) & not_bot(C.a))]; C["y"] = pd.to_datetime(C.t, unit="s").dt.year
    fy = C.groupby("a").y.min(); n = {y: C[C.y == y].a.nunique() for y in range(2021, 2027)}; new = {y: round(100 * (fy[C[C.y == y].a.unique()] == y).mean()) for y in n}
    return n, new
def add(k, v, label, unit=""): rows[k] = {"key": k, "value": v, "label": label, "unit": unit}
n, new = yearly("StopEatingSeedOils"); sn, _ = yearly("ScientificNutrition")
add("seso_people_2023", n[2023], "People who commented in r/StopEatingSeedOils in 2023"); add("seso_people_2024", n[2024], "People who commented in r/StopEatingSeedOils in 2024")
add("seso_new_2022", new[2022], "r/StopEatingSeedOils commenters in 2022 whose first comment there was that year", "%"); add("seso_new_2023", new[2023], "r/StopEatingSeedOils commenters in 2023 whose first comment there was that year", "%")
add("seso_new_2024", new[2024], "r/StopEatingSeedOils commenters in 2024 whose first comment there was that year", "%")
add("scinut_people_2023", sn[2023], "People who commented in r/ScientificNutrition in 2023"); add("scinut_people_2024", sn[2024], "People who commented in r/ScientificNutrition in 2024")
d["rows"] = list(rows.values()); F.write_text(json.dumps(d)); print({k: rows[k]["value"] for k in rows if "people" in k or k.startswith("seso_new_")})
