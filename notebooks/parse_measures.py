"""Re-parse raw ParlaMint text: country-year counts for topic keywords + 'direct talk' about outsourced emissions.

Run from final_project/:  ../.venv/bin/python notebooks/parse_measures.py
Outputs (data/processed/parlamint/):
  measures_country_year.csv     country, year, n_speeches (substantive >=50 words, non-chair) and speech counts per measure
  direct_matches_XX.csv.gz      every speech matching a direct term, WITH text, for reading/validation
Keyword lists as pre-declared in PLAN.md (ROUND 2). Agri/food/climate lists are identical to split_topics.py.
"""
import csv, gzip, re, sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

RAW = Path("data/raw/parlamint_en_txt")
OUT = Path("data/processed/parlamint"); OUT.mkdir(parents=True, exist_ok=True)
csv.field_size_limit(sys.maxsize)

AGRI = re.compile(r"\bagricultur\w*|\bfarm(?:s|er|ers|ing)?\b|\bcrops?\b|\bharvests?\b|\bfertili[sz]\w*|\blivestock\b|\bcattle\b|\bcommon agricultural policy\b|\bfisher\w*", re.I)
FOOD = re.compile(r"\bfood\b|\bfoods\b|\bnutrition\w*|\bhunger\b|\bdiets?\b|\bgrocer\w*|\bsupermarkets?\b|\bfood security\b", re.I)
CLIM = re.compile(r"\bclimate\b|\bgreenhouse\b|\bglobal warming\b|\bcarbon\b|\bemissions?\b|\bdecarboni[sz]|\bnet[- ]zero\b|\bfossil fuels?\b", re.I)
# --- v2 patterns (v1 failed the reading check: 'import*' matched 'important'; footprint/deforestation matched generic uses) ---
IMP = r"\bimport(?:s|ed|ing|ers?|ation)?\b"
IMPN = r"(?:imports?|imported|importing|importers?|abroad|overseas|outsourc\w*|supply chains?|trade)"
LEAK = re.compile(r"carbon leakage|\b(?:carbon|CO2|climate|emissions?) border\b|\bborder (?:carbon|CO2)\b|\bborder adjustment mechanism\b|\bCBAM\b", re.I)
FOOT = re.compile(r"consumption[- ]based (?:emission\w*|CO2|carbon|footprint|account\w*)|embodied (?:carbon|emission\w*)|embedded (?:carbon|emission\w*)|imported (?:emission\w*|carbon|deforestation)|emissions? (?:abroad|elsewhere|overseas)|\bfootprint\b(?:\W+\w+){0,12}?\W+" + IMPN + r"\b|\b" + IMPN + r"\b(?:\W+\w+){0,12}?\W+footprint\b", re.I)
DEFOR = re.compile(r"\bdeforestation\b(?:\W+\w+){0,15}?\W+(?:imports?|imported|supply chains?|soy|soya|palm|beef|commodit\w+|trade|Amazon|Brazil\w*|Indonesia\w*)\b|\b(?:imports?|imported|supply chains?|soy|soya|palm|beef|commodit\w+|trade|Amazon|Brazil\w*|Indonesia\w*)\b(?:\W+\w+){0,15}?\W+deforestation\b", re.I)
NEAR = re.compile(IMP + r"(?:\W+\w+){0,12}?\W+(?:emission\w*|carbon|climate|greenhouse)\b|\b(?:emission\w*|carbon|climate|greenhouse)\b(?:\W+\w+){0,12}?\W+" + IMP, re.I)


def read_tsv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


def process_country(cc):
    d = RAW / f"ParlaMint-{cc}-en.txt"
    agg = defaultdict(lambda: defaultdict(int))
    matches = []
    for txt in sorted(d.glob("[0-9][0-9][0-9][0-9]/*.txt")):
        year = txt.parent.name
        if not ("2015" <= year <= "2022"):
            continue
        stem = txt.name[:-4]
        try:
            meta = {r["ID"]: r for r in read_tsv(txt.with_name(stem + "-meta.tsv"))}
            with open(txt, encoding="utf-8") as f:
                for line in f:
                    sid, _, text = line.rstrip("\n").partition("\t")
                    m = meta.get(sid)
                    if not m or not ("2015-01-01" <= m["Date"] <= "2022-12-31") or m["Speaker_role"] == "Chairperson":
                        continue
                    if len(text.split()) < 50:
                        continue
                    a = agg[m["Date"][:4]]
                    a["n_speeches"] += 1
                    ag, fo, cl = bool(AGRI.search(text)), bool(FOOD.search(text)), bool(CLIM.search(text))
                    a["n_agri"] += ag; a["n_food"] += fo; a["n_climate"] += cl
                    a["n_agri_climate"] += ag and cl; a["n_food_climate"] += fo and cl
                    lk, ft, df = bool(LEAK.search(text)), bool(FOOT.search(text)), bool(DEFOR.search(text))
                    nr = cl and ("import" in text.lower()) and bool(NEAR.search(text))
                    a["n_leak"] += lk; a["n_foot"] += ft; a["n_defor"] += df; a["n_import_climate"] += nr
                    if lk or ft or df or nr:
                        a["n_direct_any"] += 1
                        matches.append([cc, sid, m["Date"], int(lk), int(ft), int(df), int(nr), text])
        except Exception as e:
            print(f"{cc} {stem}: {type(e).__name__}: {e}", flush=True)
    with gzip.open(OUT / f"direct_matches_{cc}.csv.gz", "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["country", "speech_id", "date", "leak", "foot", "defor", "import_climate", "text"]); w.writerows(matches)
    print(f"{cc}: {sum(v['n_speeches'] for v in agg.values())} speeches, {len(matches)} direct matches", flush=True)
    return [(cc, y, dict(v)) for y, v in sorted(agg.items())]


if __name__ == "__main__":
    countries = sorted(p.name.split("-")[1] for p in RAW.glob("ParlaMint-*-en.txt"))
    rows = []
    with Pool(8) as pool:
        for r in pool.imap_unordered(process_country, countries):
            rows += r
    cols = ["n_speeches", "n_agri", "n_food", "n_climate", "n_agri_climate", "n_food_climate", "n_leak", "n_foot", "n_defor",
            "n_import_climate", "n_direct_any"]
    with open(OUT / "measures_country_year.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["country", "year"] + cols)
        for cc, y, v in sorted(rows):
            w.writerow([cc, y] + [v.get(c, 0) for c in cols])
    print("ALL DONE", flush=True)
