"""Parse ParlaMint-en plain text into per-speech tables with keyword flags (2015-2022 only).

Run from final_project/:  ../.venv/bin/python notebooks/parse_parlamint.py
Outputs (data/processed/parlamint/):
  index_XX.csv.gz   one row per speech, NO text: ids, date, role, party, orientation, topic label, words,
                    mean sentence sentiment, keyword match counts (n_climate, n_food, n_livestock)
  flagged_XX.csv.gz speeches matching climate OR food/agri keywords, WITH text (for reading and hand-labelling)
The keyword lists are a FIRST SKIM, not a validated filter.
"""
import csv, gzip, re, sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

RAW = Path("data/raw/parlamint_en_txt")
OUT = Path("data/processed/parlamint"); OUT.mkdir(parents=True, exist_ok=True)
csv.field_size_limit(sys.maxsize)

CLIMATE = re.compile(r"\bclimate\b|\bgreenhouse\b|\bglobal warming\b|\bcarbon\b|\bemissions?\b|\bdecarboni[sz]|\bnet[- ]zero\b|\bfossil fuels?\b", re.I)
FOOD = re.compile(r"\bagricultur\w*|\bfarm(?:s|er|ers|ing)?\b|\bfood\b|\bcrops?\b|\bharvests?\b|\bfisher\w*|\bfertili[sz]\w*|\bcommon agricultural policy\b", re.I)
LIVESTOCK = re.compile(r"\blivestock\b|\bmeat\b|\bdairy\b|\bcattle\b|\bcows?\b|\bpigs?\b|\bpoultry\b|\bbeef\b|\bmilk\b|\bsheep\b", re.I)
MIN_DATE, MAX_DATE = "2015-01-01", "2022-12-31"


def read_tsv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


def process_country(cc):
    d = RAW / f"ParlaMint-{cc}-en.txt"
    n_err = 0
    idx_rows, flag_rows = [], []
    for txt in sorted(d.glob("[0-9][0-9][0-9][0-9]/*.txt")):
        year = txt.parent.name
        if not ("2015" <= year <= "2022"):
            continue
        stem = txt.name[:-4]
        try:
            meta = {r["ID"]: r for r in read_tsv(txt.with_name(stem + "-meta.tsv"))}
            sent = defaultdict(list)
            words = {}
            for r in read_tsv(txt.with_name(stem + "-ana-meta.tsv")):
                if r["Element"] == "s" and r["Senti_n"] not in ("-", ""):
                    sent[r["Parent_ID"]].append(float(r["Senti_n"]))
                elif r["Element"] == "u":
                    words[r["ID"]] = int(r["Words"] or 0)
            with open(txt, encoding="utf-8") as f:
                for line in f:
                    sid, _, text = line.rstrip("\n").partition("\t")
                    m = meta.get(sid)
                    if not m or not (MIN_DATE <= m["Date"] <= MAX_DATE):
                        continue
                    nc, nf, nl = len(CLIMATE.findall(text)), len(FOOD.findall(text)), len(LIVESTOCK.findall(text))
                    s = sent.get(sid)
                    row = [cc, sid, m["Date"], m["Speaker_role"], m["Speaker_MP"], m["Speaker_party"],
                           m["Party_orientation"], m["Topic"], words.get(sid, len(text.split())),
                           round(sum(s) / len(s), 3) if s else "", nc, nf, nl]
                    idx_rows.append(row)
                    if nc or nf:
                        flag_rows.append(row + [text])
        except Exception as e:  # keep going; count failures
            n_err += 1
            print(f"{cc} {stem}: {type(e).__name__}: {e}", flush=True)
    head = ["country", "speech_id", "date", "role", "mp", "party", "orientation", "topic", "words", "senti_mean",
            "n_climate", "n_food", "n_livestock"]
    for name, rows, hd in [(f"index_{cc}.csv.gz", idx_rows, head), (f"flagged_{cc}.csv.gz", flag_rows, head + ["text"])]:
        with gzip.open(OUT / name, "wt", encoding="utf-8", newline="") as f:
            w = csv.writer(f); w.writerow(hd); w.writerows(rows)
    print(f"{cc}: {len(idx_rows)} speeches, {len(flag_rows)} flagged, {n_err} errors", flush=True)
    return cc


if __name__ == "__main__":
    countries = sorted(p.name.split("-")[1] for p in RAW.glob("ParlaMint-*-en.txt"))
    with Pool(8) as pool:
        for _ in pool.imap_unordered(process_country, countries):
            pass
    print("ALL DONE", flush=True)
