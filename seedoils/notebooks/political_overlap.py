"""Group-level political-lean proxy: share of the heaviest commenters of r/StopEatingSeedOils (4,287 with fetched histories) who ALSO comment (>= MIN comments in a period) in partisan-coded subreddits.
The lists are hand-picked (ours, approximate); presence in a subreddit is not endorsement. Aggregates only; no individual is labelled or reported. Periods: pre2024 / from2024 as in author_subreddit_counts*.jsonl.gz.
Run from final_project/:  python3 seedoils/notebooks/political_overlap.py   (writes data/processed/political_overlap.csv)"""
from seedoil_common import HISTORY_GLOB  # author-history files for the analysis split
import glob, gzip, json
from pathlib import Path
import pandas as pd
RAW = Path("seedoils/data/raw"); MIN = 3
RIGHT = ["Conservative", "conservatives", "Republican", "trump", "AskTrumpSupporters", "walkaway", "AskConservatives", "tucker_carlson"]
LEFT = ["democrats", "Liberal", "socialism", "LateStageCapitalism", "WhitePeopleTwitter", "Trumpgret", "TheRightCantMeme", "TheDeprogram", "antiwork", "neoliberal", "Anarchism", "fuckcars"]
GENERAL = ["politics", "worldnews", "news", "PoliticalDiscussion", "moderatepolitics", "centrist", "Ask_Politics"]
OTHER = {"Libertarian": ["Libertarian", "Anarcho_Capitalism", "LibertarianUncensored"], "PoliticalCompassMemes": ["PoliticalCompassMemes"]}
auth = {}
for f in sorted(glob.glob(str(RAW / HISTORY_GLOB))):
    with gzip.open(f, "rt") as fh:
        for l in fh:
            x = json.loads(l); auth[x["author"]] = x["counts"]
def has(c, subs): return any(c.get(s, 0) >= MIN for s in subs)
rows = []
for per in ("pre2024", "from2024"):
    A = {a: c[per] for a, c in auth.items() if per in c and c[per] and sum(c[per].values()) >= 20}  # active elsewhere in the period
    n = len(A); r = {"period": per, "authors": n}
    for name, subs in (("right-coded", RIGHT), ("left-coded", LEFT), ("general politics and news", GENERAL), ("libertarian", OTHER["Libertarian"]), ("PoliticalCompassMemes", OTHER["PoliticalCompassMemes"])): r[name] = round(sum(has(c, subs) for c in A.values()) / n * 100, 1)
    R = {a for a, c in A.items() if has(c, RIGHT)}; L = {a for a, c in A.items() if has(c, LEFT)}
    r["right only"] = round(len(R - L) / n * 100, 1); r["left only"] = round(len(L - R) / n * 100, 1); r["both"] = round(len(R & L) / n * 100, 1); r["either"] = round(len(R | L) / n * 100, 1)
    r["right:left among those in either"] = round(len(R - L) / max(len(L - R), 1), 2); rows.append(r)
    sub_counts = {s: sum(c.get(s, 0) >= MIN for c in A.values()) for s in RIGHT + LEFT}
    print(per, "authors", n, {k: v for k, v in sub_counts.items() if v >= 8})
D = pd.DataFrame(rows); D.to_csv("seedoils/data/processed/political_overlap.csv", index=False); print(D.T.to_string())
