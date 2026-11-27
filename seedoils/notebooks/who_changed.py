"""Did different people arrive in 2024? Tests for two surprising findings, using only the downloaded comments (no API).

Run from final_project/:  ../.venv/bin/python seedoils/notebooks/who_changed.py  -> seedoils/data/processed/who_changed.txt (aggregates only)

Finding 1: r/ScientificNutrition was split on seed oils before 2024 and moved towards 'not harmful' from 2024.
  Q1a turnover: how many of its from-2024 commenters already commented there before 2024?
  Q1b crossover: what share of its commenters also comment in r/StopEatingSeedOils, per period?
  Q1c who wrote its 'harmful' vs 'not harmful' comments (opinion sample): are they also r/StopEatingSeedOils commenters?
Finding 6: 'not harmful' rose inside r/StopEatingSeedOils from 2024 (3% -> 13%).
  Q6a who wrote those comments: newcomers (first SESO comment in 2024 or later)? also r/ScientificNutrition commenters?
  Q6b the same comparison for the 'harmful' comments.
'Also comments in X' = at least one comment in X at any time in the downloaded histories ([deleted], AutoModerator, *bot excluded).
Positions are the blind LLM labels of the opinion sample (comments_key.csv + comment_labels_part1-3.csv).
"""
from seedoil_common import SPLIT_TS  # analysis split: 1 Jan 2024 (decision 26 Nov)
import csv
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
SUBS = {"StopEatingSeedOils": "SESO", "ScientificNutrition": "SciNut"}  # r/carnivore dropped 22 Nov (comments no longer downloaded)
SPLIT = SPLIT_TS


def main():
    first, n_by = {}, defaultdict(Counter)  # first[(sub, author)] = first comment time; n_by[sub][(author, period)] = comments
    author_of = {}
    for s in SUBS:
        with gzip.open(RAW / f"{s}_comments.jsonl.gz", "rt", encoding="utf-8") as f:
            for line in f:
                x = json.loads(line)
                a = x.get("author") or ""
                if a in ("[deleted]", "AutoModerator") or a.lower().endswith("bot"):
                    continue
                t = int(x["created_utc"])
                k = (s, a)
                first[k] = min(first.get(k, t), t)
                n_by[s][(a, "from2024" if t >= SPLIT else "pre2024")] += 1
                if s != "carnivore":
                    author_of[(s, x["id"])] = a
    who = {s: {p: {a for (a, pp) in n_by[s] if pp == p} for p in ("pre2024", "from2024")} for s in SUBS}
    ever = {s: who[s]["pre2024"] | who[s]["from2024"] for s in SUBS}
    L = []
    sn, se = "ScientificNutrition", "StopEatingSeedOils"
    for s in (sn, se):
        pre, post = who[s]["pre2024"], who[s]["from2024"]
        L.append(f"{SUBS[s]}: commenters before 2024 {len(pre):,}, from 2024 {len(post):,}; from-2024 commenters already active before: "
                 f"{len(post & pre):,} ({len(post & pre) / len(post):.0%})")
    L.append("\nQ1b crossover, share of each period's commenters who EVER comment in the other subreddit:")
    for s, others in ((sn, (se,)), (se, (sn,))):
        for p in ("pre2024", "from2024"):
            A = who[s][p]
            L.append(f"  {SUBS[s]:7} {p:9} n={len(A):6,}: " + ", ".join(f"also {SUBS[o]} {len(A & ever[o]) / len(A):.1%}" for o in others))
    # weight by comments: share of each period's COMMENTS written by crossover authors
    L.append("  share of each period's COMMENTS written by people who ever comment in the other subreddit:")
    for s, o in ((sn, se), (se, sn)):
        for p in ("pre2024", "from2024"):
            tot = sum(v for (a, pp), v in n_by[s].items() if pp == p)
            cross = sum(v for (a, pp), v in n_by[s].items() if pp == p and a in ever[o])
            L.append(f"  {SUBS[s]:7} {p:9}: by {SUBS[o]} commenters {cross / tot:.1%} of {tot:,} comments")

    key = {r["item_id"]: r for r in csv.DictReader(open(PROC / "comments_key.csv"))}
    lab = {}
    for i in (1, 2, 3):
        for r in csv.DictReader(open(PROC / f"comment_labels_part{i}.csv", encoding="utf-8")):
            lab[r["item_id"]] = r["position"]
    L.append("\nQ1c / Q6: authors of the opinion-sample comments, by position (H harmful, NH not harmful)")
    for s, o in ((sn, se), (se, sn)):
        for p in ("pre2024", "from2024"):
            for pos in ("H", "NH"):
                A = [author_of.get((s, k["doc_id"])) for i, k in key.items()
                     if "opinion" in k["samples"] and k["side"] == s and k["period"] == p and lab.get(i) == pos]
                A = [a for a in A if a]
                if not A:
                    continue
                also_o = sum(a in ever[o] for a in A)
                newcomer = sum(first[(s, a)] >= SPLIT for a in A)
                L.append(f"  {SUBS[s]:7} {p:9} {pos:2} n={len(A):3}: authors also commenting in {SUBS[o]} {also_o / len(A):.0%}; "
                         f"first comment in {SUBS[s]} from 2024 on: {newcomer / len(A):.0%}")
    text = "\n".join(L)
    (PROC / "who_changed.txt").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
