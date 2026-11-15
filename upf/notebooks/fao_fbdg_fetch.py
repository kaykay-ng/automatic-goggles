"""Download the FAO food-based dietary guideline (FBDG) country profiles and split them into sections.
Run from final_project/ with the NLP env:
  ./.venv-nlp/bin/python upf/notebooks/fao_fbdg_fetch.py fetch   # polite: one page at a time, 2 s apart, raw HTML kept in upf/data/raw/fao_fbdg/
  ./.venv-nlp/bin/python upf/notebooks/fao_fbdg_fetch.py parse   # -> upf/data/processed/fao_fbdg.csv (one row per country)
Source: https://www.fao.org/nutrition/education/food-dietary-guidelines/home/en/ (robots.txt allows these paths; checked 15 Nov 2026).
"""
import html, re, sys, time, urllib.request
from pathlib import Path
import pandas as pd

BASE = "https://www.fao.org/nutrition/education/food-dietary-guidelines"
RAW = Path("upf/data/raw/fao_fbdg"); RAW.mkdir(parents=True, exist_ok=True); OUT = Path("upf/data/processed")
UA = {"User-Agent": "Mozilla/5.0 (compatible; course-research-script)"}
SECTIONS = ["Official name", "Publication year", "Process and stakeholders", "Stakeholder involvement", "Products, resources and target audiences", "Products",
            "Development process", "Implementation", "Evaluation", "Sustainability", "Food guide", "Recommendations", "Messages", "Key messages",
            "Key additional messages", "Additional messages"]


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def fetch():
    home = get(f"{BASE}/home/en/"); (RAW / "_home.html").write_text(home)
    slugs = sorted(set(re.findall(r'food-dietary-guidelines/regions/countries/([a-z0-9\-]+)/', home)))
    print(f"{len(slugs)} country pages linked from the home page", flush=True)
    for k, s in enumerate(slugs, 1):
        f = RAW / f"{s}.html"
        if f.exists() and f.stat().st_size > 5000: continue
        try:
            f.write_text(get(f"{BASE}/regions/countries/{s}/en/")); print(f"  {k:3d} {s}", flush=True)
        except Exception as e:
            print(f"  {k:3d} {s} FAILED: {e}", flush=True)
        time.sleep(2)


def to_text(fragment):
    t = re.sub(r"<(br|/p|/li|/h\d|/tr|/td|/div)[^>]*>", "\n", fragment); t = html.unescape(re.sub(r"<[^>]+>", "", t))
    t = re.sub(r"[ \t\r\f\v\xa0]+", " ", t); return re.sub(r"\n\s*\n+", "\n", t).strip()


def parse():
    rows = []
    for f in sorted(RAW.glob("*.html")):
        if f.name.startswith("_"): continue
        s = f.read_text(errors="replace")
        title = re.search(r"Food-based dietary guidelines\s*-\s*([^<]+)</h1>", s)
        a = s.find("Official name"); a = a if a > 0 else (title.end() if title else 0)
        ends = [x for x in (s.find("Filter by country", a), s.find("Country resources", a), s.find("Previous versions", a)) if x > a]
        text = to_text(s[a: min(ends) if ends else a + 80000])
        lines = text.split("\n"); cur = "preamble"; sec = {}
        for ln in lines:
            h = ln.strip().rstrip(":")
            if h in SECTIONS: cur = h; continue
            sec.setdefault(cur, []).append(ln.strip())
        get_ = lambda *names: "\n".join(x for n in names for x in sec.get(n, []) if x)
        yr = re.findall(r"\b(19[5-9]\d|20[0-2]\d)\b", get_("Publication year"))
        rows.append(dict(slug=f.stem, country=(title.group(1).strip() if title else f.stem), n_chars=len(text),
                         official_name=get_("Official name")[:300], latest_year=max(map(int, yr)) if yr else None,
                         messages=get_("Recommendations", "Messages", "Key messages"), additional=get_("Key additional messages", "Additional messages"),
                         sustainability=get_("Sustainability"), food_guide=get_("Food guide"), full_text=text,
                         sections_found="|".join(k for k in sec if k != "preamble")))
    D = pd.DataFrame(rows); D.to_csv(OUT / "fao_fbdg.csv", index=False)
    D["msg_words"] = D.messages.fillna("").str.split().str.len(); D["full_words"] = D.full_text.str.split().str.len()
    print(f"countries parsed: {len(D)}; with a messages section: {(D.msg_words > 0).sum()}; median words: messages {int(D.msg_words.median())}, full page {int(D.full_words.median())}")
    print(f"latest publication year: median {D.latest_year.median()}, range {D.latest_year.min()}-{D.latest_year.max()}, missing {D.latest_year.isna().sum()}")
    print("pages WITHOUT a messages section:", list(D.slug[D.msg_words == 0]))
    print("section names seen (top):", pd.Series("|".join(D.sections_found).split("|")).value_counts().head(20).to_dict())


if __name__ == "__main__":
    {"fetch": fetch, "parse": parse}[sys.argv[1]]()
