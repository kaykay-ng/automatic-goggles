"""Baseline: design mix of the wider PubMed literature on linoleic acid / seed oils vs the papers Reddit cites. Counts only (PubMed E-utilities, esearch). Design proxies: MeSH 'Humans' / 'Animals' and publication types.
Term set approximates the project's relevance definition (seed oils, vegetable oils, linoleic acid, omega-6 / n-6 PUFA); it is broad and imperfect. Run from final_project/: python3 seedoils/notebooks/pubmed_baseline.py"""
import json, time, urllib.parse, urllib.request
TOPIC = '("linoleic acid"[tiab] OR "omega-6"[tiab] OR "n-6 polyunsaturated"[tiab] OR "n-6 PUFA"[tiab] OR "seed oil"[tiab] OR "seed oils"[tiab] OR "vegetable oil"[tiab] OR "vegetable oils"[tiab] OR "canola oil"[tiab] OR "soybean oil"[tiab] OR "corn oil"[tiab] OR "sunflower oil"[tiab] OR "safflower oil"[tiab])'
def count(term, lo, hi):
    q = urllib.parse.urlencode({"db": "pubmed", "term": term, "retmode": "json", "rettype": "count", "datetype": "pdat", "mindate": lo, "maxdate": hi, "tool": "socialgraphs_course"})
    for _ in range(3):
        try:
            r = json.load(urllib.request.urlopen("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + q, timeout=30)); time.sleep(0.4); return int(r["esearchresult"]["count"])
        except Exception as e:
            time.sleep(2)
    return None
DESIGNS = {"all": "", "human trials": ' AND ("Randomized Controlled Trial"[pt] OR "Clinical Trial"[pt])', "meta-analyses and systematic reviews": ' AND ("Meta-Analysis"[pt] OR "Systematic Review"[pt])',
           "animal studies": ' AND "Animals"[mh] NOT "Humans"[mh]', "human studies (any)": ' AND "Humans"[mh]', "reviews": ' AND "Review"[pt] NOT "Systematic Review"[pt] NOT "Meta-Analysis"[pt]'}
rows = []
for era, lo, hi in (("all years", "1900", "2026"), ("before 2000", "1900", "1999"), ("2000-2009", "2000", "2009"), ("2010 onwards", "2010", "2026")):
    r = {"era": era}
    for k, extra in DESIGNS.items(): r[k] = count(TOPIC + extra, lo, hi)
    rows.append(r); print(r)
json.dump(rows, open("seedoils/data/processed/pubmed_baseline.json", "w"), indent=1)
for r in rows:
    t = r["all"]; print(f"{r['era']:<13} total {t:>6}: human trials {r['human trials']/t*100:4.1f}% | meta-analyses+SRs {r['meta-analyses and systematic reviews']/t*100:4.1f}% | animal-only {r['animal studies']/t*100:4.1f}% | any human {r['human studies (any)']/t*100:4.1f}% | reviews {r['reviews']/t*100:4.1f}%")
