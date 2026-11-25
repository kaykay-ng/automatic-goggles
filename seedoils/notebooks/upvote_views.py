"""Three candidate views of upvotes (test page): (1) score bands per subreddit and period; (2) downvoted / 10+ share by theme (r/StopEatingSeedOils, comments >= 15 words); (3) score bands by cohort (newcomers = first comment in the subreddit from 2024; long-time = before 2024).
Score = net votes as archived by Arctic Shift (not final or possibly time-of-collection). Bands: <=0 downvoted, 1-2, 3-9, 10-49, 50+. Excludes last 3 days; excludes [deleted]/AutoModerator in cohort view.
Output: data/processed/artifact/upvote_views.json  (rows with view, subreddit, group, band, pct, n).  Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/upvote_views.py"""
import gzip, json
from pathlib import Path
import numpy as np, pandas as pd
RAW = Path("seedoils/data/raw"); PROC = Path("seedoils/data/processed"); CUT = pd.Timestamp("2024-01-01").timestamp()
BANDS = ["Downvoted (0 or less)", "1 to 2", "3 to 9", "10 to 49", "50 or more"]
def band(s): return pd.cut(s, [-10**9, 0, 2, 9, 49, 10**9], labels=BANDS)
def load(pat):
    rows = []
    with gzip.open(next(RAW.glob(pat)), "rt", encoding="utf-8") as f:
        for l in f:
            x = json.loads(l); rows.append((x["id"], int(x["created_utc"]), x.get("score"), len((x.get("body") or "").split()), x.get("author")))
    C = pd.DataFrame(rows, columns=["id", "t", "score", "words", "author"]).dropna(subset=["score"]); C["score"] = C.score.astype(int)
    first = C.groupby("author").t.min(); C = C[C.t < C.t.max() - 3 * 86400].copy()
    C["post"] = C.t >= CUT; C["band"] = band(C.score); C["new"] = C.author.map(first) >= CUT
    return C
out = []
def add(view, sub, group, X):
    vc = X.band.value_counts(normalize=True)
    for b in BANDS: out.append({"view": view, "subreddit": sub, "group": group, "band": b, "pct": round(float(vc.get(b, 0)) * 100, 2), "n": int(len(X))})
T = pd.read_csv(PROC / "seso_doc_topics.csv.gz", usecols=["id", "kind", "topic"]); T = T[T.kind == "comment"]
TH = {"Politics": [46, 117, 43, 68, 107], "Vaccines and COVID": [20], "Pharma, FDA, corporations": [10, 50, 80, 116], "Ingredient labels and processed food": [61, 92, 60], "Shopping": [17, 11, 9],
      "Studies and evidence": [23, 52, 53], "Keto, carbs, fasting": [1, 66], "Omega-6 / PUFA biochemistry": [0, 79, 96]}
for sub, pat in (("r/StopEatingSeedOils", "*StopEatingSeedOils_comments.jsonl.gz"), ("r/ScientificNutrition", "*ScientificNutrition_comments.jsonl.gz")):
    C = load(pat)
    for per, X in (("Before 2024", C[~C.post]), ("From 2024", C[C.post])): add("bands", sub, per, X)
    A = C[~C.author.isin(["[deleted]", "AutoModerator"])]
    add("cohort", sub, "Long-time commenters, before 2024", A[(~A.new) & (~A.post)]); add("cohort", sub, "Long-time commenters, from 2024", A[(~A.new) & A.post]); add("cohort", sub, "Newcomers, from 2024", A[A.new & A.post])
    if "Stop" in sub:
        M = C[C.words >= 15].merge(T[["id", "topic"]], on="id")
        for th, ts in TH.items():
            for per, X in (("Before 2024", M[(~M.post) & M.topic.isin(ts)]), ("From 2024", M[M.post & M.topic.isin(ts)])):
                add("theme", sub, f"{th}|{per}", X)
meta = [{"label": "upvote_views.py", "value": Path(__file__).read_text()}]
Path("seedoils/data/processed/artifact/upvote_views.json").write_text(json.dumps({"rows": out, "meta": meta}))
D = pd.DataFrame(out)
for v in ("bands", "cohort"):
    print(v); print(D[D.view == v].pivot_table(index=["subreddit", "group"], columns="band", values="pct", sort=False)[BANDS].round(1).to_string())
print("theme downvoted / 10+ :"); X = D[D.view == "theme"]; print(X[X.band.isin([BANDS[0], BANDS[3], BANDS[4]])].pivot_table(index="group", columns="band", values="pct", sort=False).round(1).to_string()[:1500])
