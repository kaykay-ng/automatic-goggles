"""Data for the niche timeline and outcome overlay: the Figure 7 backbone with (1) each person's first-comment month (people appear as the slider moves) and (2) outcomes per person: share of hostile comments (GoEmotions hostile group >= 0.5) and share downvoted (score <= 0),
before 2024 / from 2024 / all time. Per-person shares are shrunk toward the average (m = 15 pseudo-comments) because people have 10-30 comments; per-niche numbers are plain shares.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/niche_overlay_data.py  -> data/processed/artifact/niche_network.json"""
import gzip, glob, json
from pathlib import Path
import numpy as np, pandas as pd
P = Path("seedoils/data/processed"); CUT = pd.Timestamp("2024-01-01").timestamp(); M_SHRINK = 15
J = json.load(open(P / "artifact" / "commenter_network.json")); nodes = J["nodes"]
raw = {}
with gzip.open(glob.glob("seedoils/data/raw/*StopEatingSeedOils_comments.jsonl.gz")[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); raw[x["id"]] = (x["author"], int(x["created_utc"]), x.get("score"))
R = pd.DataFrame([(i, a, t, s) for i, (a, t, s) in raw.items()], columns=["id", "a", "t", "score"]); first = R.groupby("a").t.min()
D = pd.read_csv(P / "seso_k50_doc_topics.csv.gz"); D = D[D.kind == "comment"]; D["a"] = D.id.map(lambda i: raw.get(i, (None,))[0]); D = D[D.a.notna() & ~D.a.isin(["[deleted]", "AutoModerator"])]
nd = D.groupby("a").size(); U = np.array(sorted(nd[nd >= 10].index)); N = pd.read_csv(P / "commenter_topic_network_nodes.csv"); assert len(U) == len(N)
LABS = list(pd.read_csv(P / "goemo_monthly.csv", nrows=1).columns[1:29]); HOST = ["anger", "annoyance", "disapproval", "disgust"]
docs = pd.read_csv(P / "seso_docs.csv.gz", usecols=["id"], keep_default_na=False); z = np.load(P / "goemo_seso.npz", allow_pickle=True); assert (z["id"].astype(str) == docs.id.astype(str).values).all()
hostile = pd.Series((pd.DataFrame(z["p"].astype(np.float32), columns=LABS)[HOST].max(axis=1) >= .5).values, index=docs.id.astype(str).values)
D = D[D.a.isin(U)].copy(); D["host"] = D.id.map(hostile).astype(float); D["down"] = (D.id.map(lambda i: raw[i][2]).astype(float) <= 0).astype(float); D["post"] = D.created_utc >= CUT; D = D.dropna(subset=["host"])
comm = dict(zip(U, N.community)); D["c"] = D.a.map(comm)
prior = {k: D[col].mean() for k, col in (("host", "host"), ("down", "down"))}; prior_p = {(k, p): D[D.post == p][k].mean() for k in ("host", "down") for p in (False, True)}
g = D.groupby("a"); idxU = [u for u, c in zip(U, N.community) if c >= 0]; assert len(idxU) == len(nodes)
def shrunk(sub, k, pri): n = len(sub); return None if n == 0 else round(float((sub[k].sum() + M_SHRINK * pri) / (n + M_SHRINK)) * 100, 1)
months = pd.period_range("2022-01", "2026-10", freq="M"); mi = {str(m): i for i, m in enumerate(months)}
out_nodes = []
for n, u in zip(nodes, idxU):
    sub = g.get_group(u); fm = str(pd.to_datetime(first[u], unit="s").to_period("M")); sp, sq = sub[~sub.post], sub[sub.post]
    out_nodes.append({"c": n["c"], "o": n["o"], "d": n["d"], "x": n["x"], "y": n["y"], "fm": max(0, mi.get(fm, -1)) if fm >= "2022-01" else 0,
                      "h": shrunk(sub, "host", prior["host"]), "h0": shrunk(sp, "host", prior_p[("host", False)]), "h1": shrunk(sq, "host", prior_p[("host", True)]),
                      "v": shrunk(sub, "down", prior["down"]), "v0": shrunk(sp, "down", prior_p[("down", False)]), "v1": shrunk(sq, "down", prior_p[("down", True)]), "n0": int(len(sp)), "n1": int(len(sq))})
LAB = ['Condiments, snacks, bread', 'Olive oil and other oils', 'Politics (RFK, Trump)', 'Eggs and raw milk', 'Bread, butter, nuts', 'Organic, protein, soy', 'Ingredient labels, ice cream', 'Sugar, carbs, weight', 'Vaccines, fluoride', 'LDL and cholesterol', 'Skin and sun', 'Infant formula', 'Coffee, plastics, sushi', 'Tallow and fries', 'MSG', 'Vitamins, supplements']
SH = ['Condiments, snacks', 'Olive oil', 'Politics', 'Eggs, raw milk', 'Bread, butter', 'Organic, protein', 'Labels, ice cream', 'Sugar, carbs', 'Vaccines', 'LDL', 'Skin, sun', 'Infant formula', 'Coffee, plastics', 'Tallow, fries', 'MSG', 'Vitamins']
rng = np.random.default_rng(0)
def change_ci(s, k, reps=400):
    """95% interval of the change (from 2024 minus before, percentage points), resampling people."""
    g = s.groupby("a").apply(lambda x: pd.Series({"s0": x[~x.post][k].sum(), "n0": (~x.post).sum(), "s1": x[x.post][k].sum(), "n1": x.post.sum()}))
    A = g.values.astype(float); out = []
    for _ in range(reps):
        r = A[rng.integers(0, len(A), len(A))].sum(0)
        if r[1] > 0 and r[3] > 0: out.append((r[2] / r[3] - r[0] / r[1]) * 100)
    return [round(float(np.percentile(out, 2.5)), 1), round(float(np.percentile(out, 97.5)), 1)] if len(out) > 50 else [None, None]
rows = []
for c in list(range(16)) + [-1]:
    s = D[D.c == c]; a, b = s[~s.post], s[s.post]; pct = lambda x, k: round(float(x[k].mean() * 100), 1) if len(x) >= 30 else None
    rows.append({"c": c, "label": LAB[c] if c >= 0 else "General core (no link)", "people": int(s.a.nunique()), "n0": int(len(a)), "n1": int(len(b)), "h0": pct(a, "host"), "h1": pct(b, "host"), "v0": pct(a, "down"), "v1": pct(b, "down"), "hci": change_ci(s, "host") if len(a) >= 30 and len(b) >= 30 else [None, None], "vci": change_ci(s, "down") if len(a) >= 30 and len(b) >= 30 else [None, None]})
allp = lambda k, p: round(float(D[D.post == p][k].mean() * 100), 1)
out = {"months": [str(m) for m in months], "nodes": out_nodes, "edges": J["edges"], "comms": rows, "short": SH, "overall": {"h0": allp("host", False), "h1": allp("host", True), "v0": allp("down", False), "v1": allp("down", True)}, "shrink": M_SHRINK,
       "meta": [{"label": "niche_overlay_data.py", "value": Path(__file__).read_text()}]}
(P / "artifact" / "niche_network.json").write_text(json.dumps(out)); print(len(out_nodes), "nodes", len(J["edges"]), "edges; overall", out["overall"])
for r in rows: print(f"  {r['label']:<30} people {r['people']:>4} | hostile {r['h0']} -> {r['h1']} CI {r['hci']} (n {r['n0']}/{r['n1']}) | downvoted {r['v0']} -> {r['v1']} CI {r['vci']}")
