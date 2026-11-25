"""What research does each side cite? Paper links in r/StopEatingSeedOils and r/ScientificNutrition, resolved in OpenAlex.

Run from final_project/ (standard library only):
  python seedoils/notebooks/cited_papers.py extract    # -> seedoils/data/processed/citations.csv.gz (one row per document x paper id)
  python seedoils/notebooks/cited_papers.py fetch      # -> seedoils/data/raw/openalex_works.jsonl.gz (resumable)
  python seedoils/notebooks/cited_papers.py summarise  # -> seedoils/data/processed/cited_papers_summary.txt, cited_works.csv

Identifiers extracted from post URLs, post bodies and comment bodies (URL-decoded first):
  PubMed IDs (pubmed.ncbi.nlm.nih.gov/<n>, ncbi.nlm.nih.gov/[m/]pubmed/<n>), PMC IDs (PMC<n> in ncbi URLs),
  DOIs (10.<registrant>/<suffix> anywhere in a URL: doi.org, Frontiers, Wiley, AHA, T&F, Sage, PLOS, Springer...),
  nature.com/articles/<id> -> 10.1038/<id>.
NOT resolved (no identifier in the URL): ScienceDirect (PII), MDPI, Oxford Academic, JAMA, most BMJ links, ResearchGate.
  The summary reports how many scholarly links fall in that unresolved group, per subreddit.
OpenAlex: api.openalex.org/works, batch filters of 50 ids; no API key or contact email is sent. Fields kept include MeSH terms
(PubMed-indexed papers), used to tag 'Humans' vs animal/in-vitro research, and publication types such as Randomized Controlled Trial.
"""
from seedoil_common import is_bot, not_bot  # shared bot rule: AutoModerator + names ending in 'bot'
import csv
import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
SUBS = ["StopEatingSeedOils", "ScientificNutrition"]
URL = re.compile(r"https?://[^\s\)\]>\"']+")
PMID = re.compile(r"ncbi\.nlm\.nih\.gov/(?:m/)?(?:pubmed/)?(\d{6,9})(?:[/\-?#]|$)")
PMCID = re.compile(r"(PMC\d{5,9})", re.I)
DOI = re.compile(r"(10\.\d{4,9}/[^\s?#&]+)")
NATURE = re.compile(r"nature\.com/articles/([a-z0-9.\-]+)", re.I)
SCHOLARLY_NOID = ("sciencedirect", "mdpi.com", "academic.oup.com", "jamanetwork", "bmj.com", "researchgate", "thelancet",
                  "cell.com", "nejm.org", "cochranelibrary", "karger", "sagepub", "tandfonline", "wiley", "springer", "plos")
API = "https://api.openalex.org/works"
SELECT = "id,doi,ids,title,publication_year,type,cited_by_count,is_retracted,primary_topic,primary_location,mesh,referenced_works"
ANIMAL_MESH = {"Animals", "Mice", "Rats", "Swine", "Cattle", "Dogs", "Chickens", "Rabbits", "Disease Models, Animal",
               "Mice, Inbred C57BL", "Rats, Sprague-Dawley", "Rats, Wistar", "Cricetinae", "Drosophila", "Caenorhabditis elegans"}
CELL_MESH = {"Cell Line", "Cells, Cultured", "Cell Line, Tumor", "In Vitro Techniques", "HepG2 Cells", "Caco-2 Cells"}


def ids_in(url):
    u = urllib.parse.unquote(url).rstrip(".,;:")
    out = set()
    if "ncbi.nlm.nih.gov" in u:
        out |= {("pmcid", m.upper()) for m in PMCID.findall(u)}
        if not out:
            out |= {("pmid", m) for m in PMID.findall(u)}
    for m in DOI.findall(u.replace("\\_", "_").replace("\\", "")):  # Reddit markdown escapes underscores as \_
        m = re.split(r"[,|\"']", m)[0]  # commas/pipes are OpenAlex filter syntax and never part of a real DOI here
        m = re.split(r"/(?:mediaobjects|figures|tables|supplementary|suppl_file|metrics|references)\b", m)[0]
        d = re.sub(r"/(full|abstract|epdf|pdf|htm|html|meta|fulltext)$", "", m.rstrip(".,;:)/-").lower())
        if len(d) > 9:
            out.add(("doi", d))
    for m in NATURE.findall(u):
        out.add(("doi", "10.1038/" + m.lower()))
    return out


def extract():
    PROC.mkdir(parents=True, exist_ok=True)
    rows, stats = [], {}
    for sub in SUBS:
        st = Counter()
        for kind, fields in (("comments", ("body",)), ("posts", ("url", "selftext"))):
            with gzip.open(RAW / f"{sub}_{kind}.jsonl.gz", "rt", encoding="utf-8") as f:
                for line in f:
                    x = json.loads(line)
                    if is_bot(x.get("author")):
                        continue
                    found = set()
                    for fld in fields:
                        for url in URL.findall(x.get(fld) or ""):
                            got = ids_in(url)
                            if got:
                                found |= got
                            elif any(k in url.lower() for k in SCHOLARLY_NOID):
                                st["scholarly_link_unresolved"] += 1
                    st["docs_with_resolvable_paper"] += bool(found)
                    for typ, val in found:
                        rows.append((sub, kind[:-1], x["id"], x.get("author") or "", int(x["created_utc"]), x.get("score"), typ, val))
        stats[sub] = st
    with gzip.open(PROC / "citations.csv.gz", "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["subreddit", "kind", "doc_id", "author", "created_utc", "score", "id_type", "id_value"])
        w.writerows(rows)
    for sub in SUBS:
        r = [x for x in rows if x[0] == sub]
        print(f"{sub}: {len(r):,} citations, {len({(x[6], x[7]) for x in r}):,} distinct ids, "
              f"{stats[sub]['docs_with_resolvable_paper']:,} docs with an id; unresolvable scholarly links {stats[sub]['scholarly_link_unresolved']:,}")


class BadRequest(Exception):
    pass


def get(url, tries=6):
    last = None
    for i in range(tries):
        wait = 5 * (i + 1)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "research-script (course project)"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code == 400:
                raise BadRequest(url)  # a malformed id in the batch; the caller splits the batch
            if e.code == 429:
                wait = max(wait, int(e.headers.get("Retry-After") or 60))
                print(f"  rate limited, waiting {wait}s", flush=True)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = e
        time.sleep(wait)
    raise SystemExit(f"giving up after {tries} tries: {last} (rerun to resume)")


def norm_keys(work):
    ids = work.get("ids") or {}
    keys = set()
    if work.get("doi"):
        keys.add(("doi", work["doi"].lower().replace("https://doi.org/", "")))
    if ids.get("pmid"):
        keys.add(("pmid", ids["pmid"].rsplit("/", 1)[-1]))
    if ids.get("pmcid"):
        keys.add(("pmcid", ids["pmcid"].rsplit("/", 1)[-1].upper()))
    return keys


def fetch():
    with gzip.open(PROC / "citations.csv.gz", "rt", encoding="utf-8") as f:
        wanted = {(r["id_type"], r["id_value"]) for r in csv.DictReader(f)}
    out = RAW / "openalex_works.jsonl.gz"
    done = set()
    if out.exists():
        with gzip.open(out, "rt", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                done |= {tuple(k) for k in rec["_queried"]}
    todo = defaultdict(list)
    for typ, val in sorted(wanted - done):
        todo[typ].append(val)
    print(f"{len(wanted):,} ids, {len(done):,} already queried, {sum(map(len, todo.values())):,} to query", flush=True)
    filt = {"doi": "doi", "pmid": "ids.pmid", "pmcid": "ids.pmcid"}
    n_req = 0
    bad = []

    def query(typ, batch):
        """Works for a batch; on HTTP 400 split the batch in half until the malformed id is isolated (recorded as not found)."""
        nonlocal n_req
        q = urllib.parse.urlencode({"filter": f"{filt[typ]}:" + "|".join(batch), "select": SELECT, "per_page": 50})
        try:
            n_req += 1
            return get(f"{API}?{q}").get("results", [])
        except BadRequest:
            if len(batch) == 1:
                bad.append(batch[0])
                return []
            h = len(batch) // 2
            return query(typ, batch[:h]) + query(typ, batch[h:])

    for typ, vals in todo.items():
        for i in range(0, len(vals), 50):
            batch = vals[i:i + 50]
            found = {}
            for w in query(typ, batch):
                for k in norm_keys(w):
                    found[k] = w
            with gzip.open(out, "at", encoding="utf-8") as f:
                for v in batch:
                    w = found.get((typ, v.lower() if typ == "doi" else v))
                    f.write(json.dumps({"_queried": [[typ, v]], "work": w}) + "\n")
            if n_req % 20 == 0:
                print(f"  {n_req} requests, {typ} {i + len(batch):,}/{len(vals):,}", flush=True)
            time.sleep(0.2)
    print(f"done, {n_req} requests -> {out}; ids OpenAlex rejected as malformed: {len(bad)} {bad[:5]}")


def design(w):
    mesh = {m.get("descriptor_name") for m in (w.get("mesh") or [])}
    if not mesh:
        return "no MeSH"
    human = "Humans" in mesh
    animal = bool(mesh & ANIMAL_MESH)
    cell = bool(mesh & CELL_MESH)
    if human and not animal and not cell:
        return "humans only"
    if human:
        return "humans + animal/cell"
    if animal:
        return "animal"
    if cell:
        return "cell/in vitro"
    return "other MeSH"


def summarise():
    works = {}
    with gzip.open(RAW / "openalex_works.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            for k in rec["_queried"]:
                works[tuple(k)] = rec["work"]
    with gzip.open(PROC / "citations.csv.gz", "rt", encoding="utf-8") as f:
        C = list(csv.DictReader(f))
    lines, per_work = [], defaultdict(lambda: {"n": Counter(), "authors": defaultdict(set)})
    for sub in SUBS:
        rows = [r for r in C if r["subreddit"] == sub]
        hit = [(r, works.get((r["id_type"], r["id_value"]))) for r in rows]
        res = [(r, w) for r, w in hit if w]
        uniq = {w["id"]: w for _, w in res}
        for r, w in res:
            per_work[w["id"]]["n"][sub] += 1
            per_work[w["id"]]["authors"][sub].add(r["author"])
        lines.append(f"\n== {sub}: {len(rows):,} citations -> resolved {len(res):,} ({len(res) / max(len(rows), 1):.0%}); {len(uniq):,} distinct works")
        cit_w = [w for _, w in res]  # citation-weighted: each mention counts
        for label, fn in [("design (MeSH)", design), ("OpenAlex type", lambda w: w.get("type") or "?"),
                          ("field", lambda w: ((w.get("primary_topic") or {}).get("field") or {}).get("display_name", "?")),
                          ("decade", lambda w: f"{(w.get('publication_year') or 0) // 10 * 10}s")]:
            c = Counter(fn(w) for w in cit_w)
            lines.append(f"  {label}: " + ", ".join(f"{k} {v / len(cit_w):.0%}" for k, v in c.most_common(8)))
        rct = sum(any(m.get("descriptor_name") == "Randomized Controlled Trials as Topic" or m.get("qualifier_name") == "Randomized Controlled Trial"
                      for m in (w.get("mesh") or [])) for w in cit_w)
        lines.append(f"  retracted works cited: {sum(bool(w.get('is_retracted')) for w in uniq.values())}; "
                     f"median times cited (OpenAlex) of cited works: {sorted(w.get('cited_by_count') or 0 for w in uniq.values())[len(uniq) // 2] if uniq else 0}")
        top = sorted(uniq.values(), key=lambda w: -len(per_work[w["id"]]["authors"][sub]))[:15]
        lines.append("  most widely cited (distinct citing users): " + "; ".join(
            f"[{len(per_work[w['id']]['authors'][sub])}] {(w.get('title') or '?')[:70]} ({w.get('publication_year')})" for w in top))
    both = [k for k, v in per_work.items() if all(v["n"][s] for s in SUBS)]
    lines.append(f"\nworks cited in both subreddits: {len(both):,}")
    out = PROC / "cited_works.csv"
    meta = {w["id"]: w for w in works.values() if w}
    with open(out, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["openalex_id", "doi", "title", "year", "type", "design", "field", "cited_by_count", "is_retracted"]
                    + [f"n_{s}" for s in SUBS] + [f"users_{s}" for s in SUBS])
        for k, v in per_work.items():
            w = meta[k]
            wr.writerow([k, w.get("doi"), w.get("title"), w.get("publication_year"), w.get("type"), design(w),
                         ((w.get("primary_topic") or {}).get("field") or {}).get("display_name"), w.get("cited_by_count"), w.get("is_retracted")]
                        + [v["n"][s] for s in SUBS] + [len(v["authors"][s]) for s in SUBS])
    text = "\n".join(lines)
    (PROC / "cited_papers_summary.txt").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    {"extract": extract, "fetch": fetch, "summarise": summarise}[sys.argv[1]]()
