"""Extract text from the hand-downloaded LTS PDFs and build a sector/measure profile per strategy.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python ndc/notebooks/lts_extract.py
Expects ndc/data/raw/lts_pdfs/<CC>_<n>.pdf as listed in ndc/lts_download_list.md. Writes ndc/data/processed/lts_text/<name>.txt and lts_profiles.csv.
SHARED CATEGORY LISTS (also used on the parliament side, see ndc/PLAN.md 'LTS vs PARLIAMENT, pathway comparison'):
energy, transport, buildings, industry, agriculture, land_forest, waste, instruments, removals.
"""
import re, sys
from pathlib import Path
import pandas as pd
from pypdf import PdfReader

RAW = Path("ndc/data/raw/lts_pdfs"); OUT = Path("ndc/data/processed/lts_text"); OUT.mkdir(parents=True, exist_ok=True)
PROC = Path("ndc/data/processed")
CATS = {"energy": r"renewable\w*|\bwind\b|solar|photovoltaic|nuclear|hydropower|biomass|biogas|geothermal|energy transition|electrif\w*|energy efficiency|coal|power sector|electricity",
        "transport": r"electric (?:vehicle|car)s?|\bEVs?\b|charging|public transport|railway|cycling|combustion engine|electromobility|transport sector|aviation|shipping",
        "buildings": r"heat pumps?|insulation|renovation|retrofit\w*|district heating|buildings?\b",
        "industry": r"hydrogen|\bsteel\b|\bcement\b|industrial|industry",
        "agriculture": r"agricultur\w*|livestock|fertili[sz]\w*|farm\w*|manure|\bcrops?\b",
        "land_forest": r"forest\w*|afforestation|reforestation|\bpeat\w*|land use|lulucf|carbon sink\w*|wetland\w*",
        "waste": r"\bwaste\b|landfill|recycl\w*|circular economy|wastewater",
        "instruments": r"carbon (?:price|pricing|tax)|emissions? trading|\bETS\b|carbon border|subsid\w*|tax(?:es|ation)?\b",
        "removals": r"carbon (?:capture|removal)|\bCCS\b|\bCCUS\b|negative emissions|direct air capture|sequestration"}
CX = {k: re.compile(v, re.I) for k, v in CATS.items()}
EN = set("the and of to in for is are with that this on by as be from will which has have".split())
FR = set("de la le les des et en du un une pour dans que qui est sur par au aux".split())


def extract(path):
    r = PdfReader(str(path)); pages = []
    for p in r.pages:
        try: pages.append(p.extract_text() or "")
        except Exception: pages.append("")
    return pages


if __name__ == "__main__":
    links = pd.read_csv(PROC / "lts_links.csv"); n = {}; rows = []; missing = []
    for r in links.itertuples():
        n[r.cc] = n.get(r.cc, 0) + 1; name = f"{r.cc}_{n[r.cc]}"; f = RAW / f"{name}.pdf"
        if not f.exists() or f.stat().st_size < 5000 or f.read_bytes()[:5] != b"%PDF-":
            missing.append(name); continue
        pages = extract(f); text = "\n".join(pages); (OUT / f"{name}.txt").write_text(text)
        w = re.findall(r"[a-zà-ÿ']+", text.lower()); nw = max(len(w), 1)
        en, fr = sum(x in EN for x in w) / nw, sum(x in FR for x in w) / nw
        row = dict(name=name, cc=r.cc, title=r.title[:60], date=r.date, pages=len(pages), words=nw, chars_per_page=len(text) // max(len(pages), 1),
                   lang="en" if en > fr else "fr/other")
        for k, rx in CX.items():
            row[k] = 1e4 * len(rx.findall(text)) / nw
        rows.append(row)
    print(f"extracted {len(rows)} documents; missing or not a PDF: {missing}")
    if rows:
        D = pd.DataFrame(rows); D.to_csv(PROC / "lts_profiles.csv", index=False)
        pd.set_option("display.width", 220)
        print(D[["name", "pages", "words", "chars_per_page", "lang"] + list(CATS)].round(0).to_string(index=False))
        scanned = D[D.chars_per_page < 300]
        if len(scanned): print("WARNING: likely scanned/image PDFs (little text):", list(scanned.name))
