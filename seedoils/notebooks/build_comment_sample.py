"""Comment sample for labelling each comment's position on seed oils (the online side of the alignment analysis).

Run from final_project/:  ../.venv/bin/python seedoils/notebooks/build_comment_sample.py
  -> seedoils/data/processed/comments_to_label.jsonl  (item_id, text; blind, no side; gitignored, holds Reddit text)
     seedoils/data/processed/comments_key.csv         (item_id, sample, side, period, doc_id, cited openalex ids; gitignored)

A. Opinion sample: comments (not posts) with >= MIN_WORDS words that mention a seed-oil term (SEED regex), from r/StopEatingSeedOils and
   r/ScientificNutrition, PER_CELL drawn at random per side x period (before / from 2024-01-01). Seed 11.
B. Citing sample: comments or self-posts that cite at least one paper of the four labelled seed-oil communities (citations.csv.gz resolved
   through OpenAlex), PER_SIDE_CITING drawn at random per side. Seed 12. Documents already in A keep one item and are flagged in both samples.
Text: quotes ('>' lines) kept but marked, URLs replaced by [link]; capped at MAX_WORDS words (most comments are shorter).
"""
import csv
import gzip
import json
import random
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
SUBS = ["StopEatingSeedOils", "ScientificNutrition"]
SPLIT = 1704067200
MIN_WORDS, MAX_WORDS = 15, 400
PER_CELL, PER_SIDE_CITING = 100, 150
SEED = re.compile(r"\b(seed ?oils?|vegetable oils?|veg oils?|canola|rapeseed|soybean oil|soy oil|sunflower oil|safflower|corn oil|"
                  r"cottonseed|linoleic|omega[- ]?6|n-6|pufas?|polyunsaturated)\b", re.I)
URL = re.compile(r"https?://\S+")
COMMS = {"2", "10", "4", "5"}


def clean(t):
    t = URL.sub("[link]", t or "")
    t = "\n".join(("[quote] " + l.lstrip("> ").strip()) if l.lstrip().startswith(">") else l for l in t.splitlines())
    w = t.split()
    return " ".join(w[:MAX_WORDS]) + (" ..." if len(w) > MAX_WORDS else "")


def main():
    docs = {}
    for s in SUBS:
        for kind, field in (("comments", "body"), ("posts", "selftext")):
            with gzip.open(RAW / f"{s}_{kind}.jsonl.gz", "rt", encoding="utf-8") as f:
                for line in f:
                    x = json.loads(line)
                    a = x.get("author") or ""
                    if a in ("[deleted]", "AutoModerator") or a.lower().endswith("bot"):
                        continue
                    body = x.get(field) or ""
                    if body.strip() in ("", "[removed]", "[deleted]"):
                        continue
                    if kind == "posts":
                        body = f"[POST TITLE] {x.get('title', '')}\n{body}"
                    docs[(s, x["id"])] = {"kind": kind[:-1], "t": int(x["created_utc"]), "body": body}
    # B candidates: documents citing a paper of the four communities
    works = {}
    with gzip.open(RAW / "openalex_works.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            for k in rec["_queried"]:
                if rec["work"]:
                    works[tuple(k)] = rec["work"]["id"]
    comm = {r["openalex_id"] for r in csv.DictReader(open(PROC / "cocite_node_communities.csv"))
            if r["network"] == "scholarly" and r["community"] in COMMS}
    cited = defaultdict(set)
    with gzip.open(PROC / "citations.csv.gz", "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            w = works.get((r["id_type"], r["id_value"]))
            if w in comm and (r["subreddit"], r["doc_id"]) in docs:
                cited[(r["subreddit"], r["doc_id"])].add(w)
    items = {}
    rng = random.Random(11)
    for s in SUBS:
        for period in ("pre2024", "from2024"):
            pool = [k for k, d in docs.items() if k[0] == s and d["kind"] == "comment" and (d["t"] >= SPLIT) == (period == "from2024")
                    and len(d["body"].split()) >= MIN_WORDS and SEED.search(d["body"])]
            for k in rng.sample(sorted(pool), min(PER_CELL, len(pool))):
                items[k] = {"samples": {"opinion"}, "period": period}
            print(f"A {s} {period}: {len(pool):,} eligible, drew {min(PER_CELL, len(pool))}")
    rng = random.Random(12)
    for s in SUBS:
        pool = sorted(k for k in cited if k[0] == s)
        for k in rng.sample(pool, min(PER_SIDE_CITING, len(pool))):
            period = "from2024" if docs[k]["t"] >= SPLIT else "pre2024"
            items.setdefault(k, {"samples": set(), "period": period})["samples"].add("citing")
        print(f"B {s}: {len(pool):,} citing documents, drew {min(PER_SIDE_CITING, len(pool))}")
    keys = sorted(items)
    random.Random(13).shuffle(keys)
    with open(PROC / "comments_to_label.jsonl", "w", encoding="utf-8") as f, open(PROC / "comments_key.csv", "w", newline="") as k:
        wk = csv.writer(k)
        wk.writerow(["item_id", "samples", "side", "period", "doc_id", "kind", "cited_works"])
        for i, key in enumerate(keys, 1):
            d, it = docs[key], items[key]
            f.write(json.dumps({"item_id": i, "text": clean(d["body"])}, ensure_ascii=False) + "\n")
            wk.writerow([i, "+".join(sorted(it["samples"])), key[0], it["period"], key[1], d["kind"], "|".join(sorted(cited.get(key, ())))])
    both = sum(len(it["samples"]) == 2 for it in items.values())
    print(f"{len(keys)} items ({both} in both samples) -> comments_to_label.jsonl (blind) + comments_key.csv")


if __name__ == "__main__":
    main()
