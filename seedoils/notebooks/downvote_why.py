"""What goes with downvotes in r/StopEatingSeedOils? Splits comments (>= 15 words) by GoEmotions hostile (>=0.5), by whether the text mentions seed oil / vegetable oil / omega-6 etc. (a crude on-topic proxy, NOT a sentiment word list), by period and theme.
Downvoted = score <= 0. Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/downvote_why.py"""
import gzip, json
from pathlib import Path
import numpy as np, pandas as pd
PROC = Path("seedoils/data/processed"); RAW = next(Path("seedoils/data/raw").glob("*StopEatingSeedOils_comments.jsonl.gz")); CUT = pd.Timestamp("2024-01-01").timestamp()
LAB = list(pd.read_csv(PROC / "goemo_monthly.csv", nrows=1).columns[1:29]); H = ["anger", "annoyance", "disapproval", "disgust"]
sc = {}
with gzip.open(RAW, "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l)
        if x.get("score") is not None: sc[x["id"]] = int(x["score"])
D = pd.read_csv(PROC / "seso_docs.csv.gz", usecols=["id", "kind", "created_utc", "text"], keep_default_na=False)
z = np.load(PROC / "goemo_seso.npz", allow_pickle=True); assert (z["id"].astype(str) == D.id.astype(str).values).all()
L = pd.DataFrame(z["p"].astype(np.float32), columns=LAB); D["hostile"] = (L[H].max(axis=1) >= .5).values
D = D[D.kind == "comment"].merge(pd.read_csv(PROC / "seso_doc_topics.csv.gz", usecols=["id", "topic"]), on="id"); D["score"] = D.id.map(sc); D = D.dropna(subset=["score"])
D = D[D.created_utc < D.created_utc.max() - 3 * 86400].copy(); D["post"] = D.created_utc >= CUT; D["down"] = D.score <= 0
D["oil"] = D.text.astype(str).str.contains(r"seed[ -]?oil|vegetable oil|canola|soybean oil|linoleic|omega[ -]?6|pufa|industrial oil|rapeseed|sunflower oil", case=False)
print("share of comments mentioning seed/vegetable oil terms (proxy for on-topic): pre %.1f%% post %.1f%%" % (D[~D.post].oil.mean() * 100, D[D.post].oil.mean() * 100))
TH = {"Politics": [46, 117, 43, 68, 107], "Studies, evidence": [23, 52, 53], "Vaccines": [20], "Pharma": [10, 50, 80, 116], "Ingredient labels": [61, 92, 60], "Shopping": [17, 11, 9], "Omega-6": [0, 79, 96], "Keto": [1, 66]}
def rate(X): return f"{X.down.mean()*100:5.1f}% (n={len(X)})" if len(X) >= 30 else "  n<30"
print("\ndownvoted share (score<=0), all themes:")
for per, X in (("before 2024", D[~D.post]), ("from 2024", D[D.post])):
    print(f"  {per}: hostile {rate(X[X.hostile])} | not hostile {rate(X[~X.hostile])} || mentions oil {rate(X[X.oil])} | no oil mention {rate(X[~X.oil])}")
    print(f"    hostile & no oil mention {rate(X[X.hostile & ~X.oil])} | hostile & oil {rate(X[X.hostile & X.oil])} | not hostile & no oil {rate(X[~X.hostile & ~X.oil])} | not hostile & oil {rate(X[~X.hostile & X.oil])}")
print("\nfrom 2024 by theme: downvoted share | oil mention share | downvoted if hostile / if not | downvoted if oil mention / if not")
for th, ts in TH.items():
    X = D[D.post & D.topic.isin(ts)]
    print(f"  {th:<18} {X.down.mean()*100:5.1f}% | oil {X.oil.mean()*100:4.0f}% | hostile {rate(X[X.hostile])} vs {rate(X[~X.hostile])} | oil {rate(X[X.oil])} vs {rate(X[~X.oil])}")
print("\nhow much of the rise in downvoting is within groups? downvoted share before -> from 2024, by hostile / oil mention:")
for lab, m in (("hostile", D.hostile), ("not hostile", ~D.hostile), ("oil mention", D.oil), ("no oil mention", ~D.oil)):
    X = D[m]; print(f"  {lab:<15} {X[~X.post].down.mean()*100:4.1f}% -> {X[X.post].down.mean()*100:4.1f}%  (share of comments {X[~X.post].shape[0]/ (~D.post).sum()*100:.0f}% -> {X[X.post].shape[0]/D.post.sum()*100:.0f}%)")
