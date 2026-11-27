"""Deep dive into the four seed-oil communities of the scholarly co-citation network: who cites them, when, how it is received, in which
discussion topics, plus a blind stance-labelling sheet for the papers both sides cite.

Run from final_project/ after cocite_communities.py and the seso/scinut topic + votes steps:
  ../.venv/bin/python seedoils/notebooks/dive_communities.py
  -> seedoils/data/processed/dive_summary.txt
     seedoils/data/processed/stance_sheet.csv      (to label: item_id, paper, comment text, empty stance/focus/notes; gitignored, holds text)
     seedoils/data/processed/stance_key.csv        (item_id -> side, community, doc ids; gitignored; do NOT open while labelling)

Communities (scholarly reference partition, seed with the highest mean AMI; ids from cocite_node_communities.csv):
  2 omega-6 / linoleic acid, 10 rodent dietary-fat carcinogenesis, 4 saturated fat and CVD, 5 LDL / lipoproteins.
Per community x side: citing documents and distinct users, share of citing documents from 2024 on (compared with that side's share for
ALL its paper citations, so a community that grew faster than citing in general stands out), mean within-thread vote percentile of the
citing comments (as in seso_topics.py votes), and the discussion topics (BERTopic) the citing comments fall in.
Labelling sample: in each community, the papers with the most citing users on BOTH sides (ranked by the smaller of the two counts);
up to PER_SIDE comments per side per paper, drawn at random (seed 7); order shuffled; side hidden.
Stance codes to use: S = supports the paper's conclusion / uses it as evidence for its point; D = disputes it (methods, relevance, conclusion);
N = neutral mention / just a link; ? = cannot tell. Focus (optional, free text): which part of the paper the comment leans on.
"""
from seedoil_common import is_bot, not_bot, SPLIT_TS# shared bot rule: AutoModerator + names ending in 'bot'
import csv
import gzip
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from cited_papers import ids_in  # noqa: E402  (same identifier extraction as the citation table)

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
SESO, SCINUT = "StopEatingSeedOils", "ScientificNutrition"
PFX = {SESO: "seso", SCINUT: "scinut"}
COMMS = {2: "omega-6 / linoleic acid", 10: "rodent fat carcinogenesis", 4: "saturated fat & CVD", 5: "LDL / lipoproteins"}
SPLIT = SPLIT_TS  # 2024-01-01
PAPERS_PER_COMM, PER_SIDE = 8, 3


def vote_pct(sub):
    rows = []
    with gzip.open(RAW / f"{sub}_comments.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            x = json.loads(line)
            if is_bot(x.get("author")):
                continue
            rows.append((x["id"], x["link_id"], str(x.get("parent_id", "")).startswith("t3_"), int(x["created_utc"]), x.get("score")))
    C = pd.DataFrame(rows, columns=["id", "link_id", "top", "t", "score"]).dropna(subset=["score"])
    g = C.groupby(["link_id", "top"]).score
    C = C[g.transform("size") >= 5].copy()
    C["pct"] = C.groupby(["link_id", "top"]).score.rank(method="average", pct=True)
    return dict(zip(C.id, C.pct))


HALF_WINDOW = 150
URL_RE = re.compile(r"https?://[^\s\)\]>\"']+")


def citation_window(text, keys):
    """~2 x HALF_WINDOW words centred on the first link to this paper. The cited link becomes [[CITED STUDY LINK]], other links
    [other link]. Returns (window, anchor_found). Falls back to the first 2 x HALF_WINDOW words when no link to the paper is in the text."""
    words = text.split()
    anchor = None
    for j, w in enumerate(words):
        if any(ids_in(u) & keys for u in URL_RE.findall(w)):
            anchor = j
            break
    lo, hi = (max(0, anchor - HALF_WINDOW), anchor + HALF_WINDOW + 1) if anchor is not None else (0, 2 * HALF_WINDOW)
    out = []
    for j in range(lo, min(hi, len(words))):
        w = words[j]
        if j == anchor:
            w = URL_RE.sub("[[CITED STUDY LINK]]", w, count=1)
            w = URL_RE.sub("[other link]", w)
        else:
            w = URL_RE.sub("[other link]", w)
        out.append(w)
    prefix = "... " if lo > 0 else ""
    suffix = " ..." if hi < len(words) else ""
    return prefix + " ".join(out) + suffix, anchor is not None


def texts(sub, wanted):
    out = {}
    for kind, field in (("comments", "body"), ("posts", "selftext")):
        with gzip.open(RAW / f"{sub}_{kind}.jsonl.gz", "rt", encoding="utf-8") as f:
            for line in f:
                x = json.loads(line)
                if x["id"] in wanted:
                    t = x.get(field) or ""
                    if kind == "posts":
                        t = f"[POST] {x.get('title', '')}. {t}"
                    out[x["id"]] = re.sub(r"\s+", " ", t).strip()
    return out


def main():
    works = {}
    with gzip.open(RAW / "openalex_works.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            for k in rec["_queried"]:
                if rec["work"]:
                    works[tuple(k)] = rec["work"]["id"]
    comm_of = {}
    with open(PROC / "cocite_node_communities.csv") as f:
        for r in csv.DictReader(f):
            if r["network"] == "scholarly" and int(r["community"]) in COMMS:
                comm_of[r["openalex_id"]] = int(r["community"])
    nodes = {r["openalex_id"]: r for r in csv.DictReader(open(PROC / "cocite_nodes.csv", encoding="utf-8"))}
    cites = []
    with gzip.open(PROC / "citations.csv.gz", "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            w = works.get((r["id_type"], r["id_value"]))
            if w and r["author"] not in ("", "[deleted]") and not is_bot(r["author"]):
                cites.append({**r, "work": w, "comm": comm_of.get(w)})
    C = pd.DataFrame(cites).drop_duplicates(["subreddit", "doc_id", "work"])
    C["created_utc"] = C.created_utc.astype(int)
    C["from2024"] = C.created_utc >= SPLIT
    base = C.groupby("subreddit").from2024.mean()
    pct = {s: vote_pct(s) for s in (SESO, SCINUT)}
    C["vote_pct"] = [pct[s].get(d) for s, d in zip(C.subreddit, C.doc_id)]
    topic_of, words = {}, {}
    for s in (SESO, SCINUT):
        T = pd.read_csv(PROC / f"{PFX[s]}_doc_topics.csv.gz", usecols=["id", "topic"])
        topic_of[s] = dict(zip(T.id, T.topic))
        I = pd.read_csv(PROC / f"{PFX[s]}_topics_info.csv")
        words[s] = dict(zip(I.topic, I.top_words.str.split(", ").str[:4].str.join(", ")))
    lines = [f"baseline share of paper citations from 2024: SESO {base[SESO]:.0%}, SciNut {base[SCINUT]:.0%}"]
    for cid, name in COMMS.items():
        D = C[C.comm == cid]
        lines.append(f"\n== c{cid} {name}: {len(set(D.work))} cited papers with community membership")
        for s in (SESO, SCINUT):
            d = D[D.subreddit == s]
            if d.empty:
                lines.append(f"  {s}: no citations")
                continue
            v = d.vote_pct.dropna()
            tops = Counter(topic_of[s].get(x) for x in d.doc_id if topic_of[s].get(x) is not None).most_common(3)
            lines.append(f"  {s:20} {len(d):5,} citing docs, {d.author.nunique():4,} users; from 2024 {d.from2024.mean():.0%} (side baseline {base[s]:.0%}); "
                         f"vote pct {v.mean():.3f} (n={len(v)})")
            lines.append("      topics: " + "; ".join(f"[{words[s].get(t, '?')}] {k}" for t, k in tops))

    # blind stance-labelling sample
    rng = random.Random(7)
    items = []
    for cid in COMMS:
        D = C[C.comm == cid]
        u = D.groupby(["work", "subreddit"]).author.nunique().unstack(fill_value=0)
        if SESO not in u or SCINUT not in u:
            continue
        u["both_min"] = u[[SESO, SCINUT]].min(axis=1)
        top = u[u.both_min > 0].sort_values(["both_min", SESO], ascending=False).head(PAPERS_PER_COMM).index
        for w in top:
            for s in (SESO, SCINUT):
                docs = sorted(set(D[(D.work == w) & (D.subreddit == s)].doc_id))
                for doc in rng.sample(docs, min(PER_SIDE, len(docs))):
                    items.append({"community": cid, "work": w, "side": s, "doc_id": doc})
    need = defaultdict(set)
    for it in items:
        need[it["side"]].add(it["doc_id"])
    txt = {s: texts(s, need[s]) for s in need}
    keys_for = defaultdict(set)  # every identifier form under which this document cites this work (pmid, pmcid, doi)
    for r in cites:
        keys_for[(r["subreddit"], r["doc_id"], r["work"])].add((r["id_type"], r["id_value"]))
    rng.shuffle(items)
    found = 0
    with open(PROC / "stance_sheet.csv", "w", newline="", encoding="utf-8") as f, open(PROC / "stance_key.csv", "w", newline="") as k:
        ws, wk = csv.writer(f), csv.writer(k)
        ws.writerow(["item_id", "paper_title", "paper_year", "citation_window", "window_anchor_found", "comment_text", "stance (S/D/N/?)", "focus", "notes"])
        wk.writerow(["item_id", "side", "community", "openalex_id", "doc_id"])
        for i, it in enumerate(items, 1):
            n = nodes[it["work"]]
            full = txt[it["side"]].get(it["doc_id"], "")
            win, ok = citation_window(full, keys_for[(it["side"], it["doc_id"], it["work"])])
            found += ok
            ws.writerow([i, n["title"], n["year"], win, int(ok), full, "", "", ""])
            wk.writerow([i, it["side"], it["community"], it["work"], it["doc_id"]])
    per = Counter((it["community"], it["side"]) for it in items)
    lines.append(f"\nstance sheet: {len(items)} items -> stance_sheet.csv (blind; key in stance_key.csv). "
                 + ", ".join(f"c{c} {s[:4]} {per[(c, s)]}" for c in COMMS for s in (SESO, SCINUT)))
    lines.append(f"citation windows ({2 * HALF_WINDOW} words around the link to the paper): link found in {found} of {len(items)} items; "
                 "otherwise the window is the first words of the text (e.g. a post whose link is the post URL)")
    text = "\n".join(lines)
    (PROC / "dive_summary.txt").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
