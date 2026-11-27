"""What gets upvoted on each side? Comment features vs within-thread vote percentile, r/StopEatingSeedOils vs r/ScientificNutrition.

Run from final_project/:  python seedoils/notebooks/vote_features.py   -> seedoils/data/processed/vote_features.txt
Vote percentile as in seso_topics.py votes: rank of score within thread x level (top-level / reply), ties averaged,
groups with >= 5 comments; bots dropped; comments of any age kept (scores of the last ~3 days were still settling). Features are simple text markers, not stance labels.
"""
from seedoil_common import is_bot, not_bot, SPLIT_TS# shared bot rule: AutoModerator + names ending in 'bot'
import gzip
import json
import re
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message="This pattern is interpreted as a regular expression")

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
SUBS = ["StopEatingSeedOils", "ScientificNutrition"]
PAPER = re.compile(r"ncbi\.nlm\.nih\.gov|doi\.org|/doi/10\.|sciencedirect|nature\.com/articles|frontiersin|mdpi\.com|academic\.oup|"
                   r"jamanetwork|bmj\.com|thelancet|nejm\.org|ahajournals|wiley\.com|springer|tandfonline|plos\.org|cochrane", re.I)
URL = re.compile(r"https?://", re.I)
STUDY_WORDS = re.compile(r"\b(stud(y|ies)|trial|rct|meta-?analys[ie]s|cohort|evidence|data|p ?[<=] ?0\.\d)\b", re.I)
HEDGE = re.compile(r"\b(may|might|could|suggests?|likely|unclear|uncertain|associat\w*|correlat\w*)\b", re.I)
DISTRUST = re.compile(r"\b(big (food|pharma|ag)|industry|propaganda|corrupt\w*|lobby\w*|fda|cdc|shill\w*|paid|funded by|agenda)\b", re.I)
SEED_BAD = re.compile(r"\b(toxic|poison\w*|inflammat\w*|rancid|oxidi[sz]ed|industrial|engine oil|lubricant)\b", re.I)
QUESTION = re.compile(r"\?")


def load(sub):
    rows = []
    with gzip.open(RAW / f"{sub}_comments.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            x = json.loads(line)
            b = x.get("body") or ""
            if b.strip() in ("[removed]", "[deleted]") or is_bot(x.get("author")):
                continue
            rows.append((x["link_id"], str(x.get("parent_id", "")).startswith("t3_"), int(x["created_utc"]), x.get("score"), b))
    C = pd.DataFrame(rows, columns=["link_id", "top_level", "created_utc", "score", "body"]).dropna(subset=["score"])
    g = C.groupby(["link_id", "top_level"]).score
    C = C[g.transform("size") >= 5].copy()
    C["pct"] = C.groupby(["link_id", "top_level"]).score.rank(method="average", pct=True)
    words = C.body.str.split().str.len()
    C["length"] = pd.cut(words, [0, 5, 15, 40, 100, 10**6], labels=["1-5", "6-15", "16-40", "41-100", "100+"])
    C["paper_link"] = C.body.str.contains(PAPER)
    C["other_link"] = C.body.str.contains(URL) & ~C.paper_link
    C["study_words"] = C.body.str.contains(STUDY_WORDS)
    C["hedging"] = C.body.str.contains(HEDGE)
    C["distrust_words"] = C.body.str.contains(DISTRUST)
    C["seed_oils_bad_words"] = C.body.str.contains(SEED_BAD)
    C["question"] = C.body.str.contains(QUESTION)
    C["period"] = (C.created_utc >= SPLIT_TS).map({False: "pre2024", True: "from2024"})
    return C


def main():
    lines = []
    for sub in SUBS:
        C = load(sub)
        lines.append(f"\n== {sub}: {len(C):,} scored comments; mean percentile {C.pct.mean():.3f} (0.5 + tie effects)")
        lines.append("  by length (words): " + ", ".join(f"{k} {v:.3f}" for k, v in C.groupby("length", observed=True).pct.mean().items()))
        for feat in ["paper_link", "other_link", "study_words", "hedging", "distrust_words", "seed_oils_bad_words", "question"]:
            # compare within the 16-100 word band so length does not drive the contrast
            M = C[C.length.isin(["16-40", "41-100"])]
            a, b = M[M[feat]].pct, M[~M[feat]].pct
            by_p = M.groupby(["period", feat]).pct.mean().unstack()
            per = "; ".join(f"{p}: {by_p.loc[p, True] - by_p.loc[p, False]:+.3f}" for p in ["pre2024", "from2024"] if p in by_p.index and True in by_p.columns)
            lines.append(f"  {feat:20} share {M[feat].mean():5.1%} | with {a.mean():.3f} vs without {b.mean():.3f} -> {a.mean() - b.mean():+.3f}  ({per})")
    text = "\n".join(lines)
    (PROC / "vote_features.txt").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
