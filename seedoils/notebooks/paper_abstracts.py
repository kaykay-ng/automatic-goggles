"""Abstracts for the papers of the four seed-oil communities (scholarly co-citation network), for labelling each paper's conclusion.

Run from final_project/ (standard library only):  ../.venv/bin/python seedoils/notebooks/paper_abstracts.py
  -> seedoils/data/raw/community_abstracts.json  {openalex_id: abstract}
     seedoils/data/processed/papers_to_label.jsonl  (openalex_id, community, title, year, design from MeSH, abstract; no Reddit data)
Sources: OpenAlex abstract_inverted_index (batches of 50 ids); papers without one are filled from PubMed efetch when a PMID exists.
No API key or contact email is sent to either service.
Communities (ids from cocite_node_communities.csv, scholarly): 2 omega-6 / linoleic acid, 10 rodent fat carcinogenesis,
4 saturated fat & CVD, 5 LDL / lipoproteins.
"""
import csv
import gzip
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
COMMS = {2: "omega-6 / linoleic acid", 10: "rodent fat carcinogenesis", 4: "saturated fat & CVD", 5: "LDL / lipoproteins"}
UA = {"User-Agent": "research-script (course project)"}


def get(url, as_json=True):
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                b = r.read()
            return json.loads(b) if as_json else b.decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001 - retry any network error, then give up loudly
            last = e
            time.sleep(5 * (i + 1))
    raise SystemExit(f"giving up: {last}")


def main():
    comm = {}
    with open(PROC / "cocite_node_communities.csv") as f:
        for r in csv.DictReader(f):
            if r["network"] == "scholarly" and int(r["community"]) in COMMS:
                comm[r["openalex_id"]] = int(r["community"])
    nodes = {r["openalex_id"]: r for r in csv.DictReader(open(PROC / "cocite_nodes.csv", encoding="utf-8"))}
    out_path = RAW / "community_abstracts.json"
    abstracts = json.loads(out_path.read_text()) if out_path.exists() else {}
    todo = [w for w in comm if w not in abstracts]
    print(f"{len(comm)} papers, {len(todo)} to fetch", flush=True)
    pmid = {}
    for i in range(0, len(todo), 50):
        batch = [w.rsplit("/", 1)[-1] for w in todo[i:i + 50]]
        q = urllib.parse.urlencode({"filter": "openalex:" + "|".join(batch), "select": "id,ids,abstract_inverted_index", "per_page": 50})
        for w in get("https://api.openalex.org/works?" + q)["results"]:
            inv = w.get("abstract_inverted_index") or {}
            pos = {p: t for t, ps in inv.items() for p in ps}
            abstracts[w["id"]] = " ".join(pos[k] for k in sorted(pos))
            if not abstracts[w["id"]] and (w.get("ids") or {}).get("pmid"):
                pmid[w["id"]] = w["ids"]["pmid"].rsplit("/", 1)[-1]
        time.sleep(0.3)
    print(f"OpenAlex: {sum(bool(abstracts.get(w)) for w in comm)} with abstract; trying PubMed for {len(pmid)}", flush=True)
    for w, p in pmid.items():
        x = get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={p}&rettype=abstract&retmode=xml", as_json=False)
        parts = re.findall(r'<AbstractText(?:\s+Label="([^"]*)")?[^>]*>(.*?)</AbstractText>', x, re.S)
        abstracts[w] = " ".join((f"{lab.upper()}: " if lab else "") + re.sub(r"<[^>]+>", "", t) for lab, t in parts).strip()
        time.sleep(0.4)
    out_path.write_text(json.dumps(abstracts))
    n = 0
    with open(PROC / "papers_to_label.jsonl", "w", encoding="utf-8") as f:
        for w, c in sorted(comm.items(), key=lambda kv: (kv[1], kv[0])):
            nd = nodes[w]
            f.write(json.dumps({"openalex_id": w, "community": COMMS[c], "title": nd["title"], "year": nd["year"],
                                "design_mesh": nd["design"], "abstract": abstracts.get(w, "")}, ensure_ascii=False) + "\n")
            n += 1
    have = sum(bool(abstracts.get(w)) for w in comm)
    print(f"done: {have} of {len(comm)} papers have an abstract ({have / len(comm):.0%}); {n} rows -> papers_to_label.jsonl")


if __name__ == "__main__":
    main()
