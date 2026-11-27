"""Newcomers and the old guard on the topic co-writing network (user request 27 Nov). Topic network = topics as nodes, a link when more people
write in both topics than chance (topic_cooccurrence_network.py). Newcomer = first post or comment in r/StopEatingSeedOils on or after
seedoil_common.SPLIT_TS (1 Jan 2024), as in the reply network; old guard = first post or comment before. Three analyses:
  1. per topic, the newcomer share of the people who wrote in it from 2024 (node attribute), against the newcomer share of all writers from 2024;
  2. co-writing lift by theme pair for newcomers and for the old guard, both from their documents from 2024 (same period);
  3. the old guard before vs from 2024: (a) all old-guard people active in each period, (b) a panel of the old-guard people with documents in
     2+ topics in BOTH periods (same people).
Lift = people who wrote in both topics, summed over a set of topic pairs, divided by the number expected from the group's own curveball null
(N_NULL samples; every person's number of topics and every topic's number of people kept); 95% intervals from 400 bootstrap resamples of the
group's people (expected kept fixed). Documents = topic-model comments and self-posts (15+ words); people need documents in 2+ topics.
Output: data/processed/topic_network_cohorts.json (aggregates only). Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/topic_network_cohorts.py"""
import glob
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

sys.path.insert(0, str(Path(__file__).parent))
from seedoil_common import not_bot, SPLIT_TS, THEMES_FILE  # noqa: E402

P, RAW = Path("seedoils/data/processed"), Path("seedoils/data/raw")
N_NULL, N_BOOT = 500, 400
cauth, pauth, first = {}, {}, {}
with gzip.open(glob.glob(str(RAW / "*StopEatingSeedOils_comments.jsonl.gz"))[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); a = x["author"]; cauth[x["id"]] = a; t = int(x["created_utc"]); first[a] = min(first.get(a, t), t)
first_post = {}
with gzip.open(glob.glob(str(RAW / "*StopEatingSeedOils_posts.jsonl.gz"))[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); a = x.get("author") or ""; pauth[x["id"]] = a; t = int(x["created_utc"]); first_post[a] = min(first_post.get(a, t), t)
for a, t in first_post.items():  # 27 Nov: first POST OR COMMENT, the same definition as the reply network
    first[a] = min(first.get(a, t), t)
D = pd.read_csv(P / "seso_doc_topics.csv.gz", usecols=["id", "kind", "created_utc", "topic"]); D["id"] = D.id.astype(str)
D["a"] = np.where(D.kind == "comment", D.id.map(cauth), D.id.map(pauth))
D = D[D.a.notna() & (D.a != "") & ~D.a.isin(["[deleted]", "AutoModerator"]) & not_bot(D.a.fillna(""))].copy()
D["new"] = D.a.map(first) >= SPLIT_TS; D["post"] = D.created_utc >= SPLIT_TS
K = int(D.topic.max()) + 1; IU = np.triu_indices(K, 1)
TH = json.loads((P / THEMES_FILE).read_text()); theme_of = {int(t): n.split(" (")[0] for n, ids in TH.items() for t in ids}
NET = json.loads((P / "topic_cooccurrence_network.json").read_text()); words = {n["topic"]: n["words"] for n in NET["nodes"]}
ALL_LINKS = {(min(e["a"], e["b"]), max(e["a"], e["b"])) for e in NET["edges_all"]}


def person_rows(docs):
    s = docs.groupby("a").topic.apply(lambda x: sorted(set(int(t) for t in x))); return s[s.map(len) >= 2]


def matrix(rows):
    ri = np.repeat(np.arange(len(rows)), [len(r) for r in rows]); ci = np.fromiter((t for r in rows for t in r), dtype=np.int64)
    return csr_matrix((np.ones(len(ci), dtype=np.float32), (ri, ci)), shape=(len(rows), K))


def cooc(X, w=None):
    Xw = X if w is None else X.multiply(w[:, None]).tocsr(); return np.asarray((X.T @ Xw).todense())[IU]


def curveball_mean(rows, n, seed):
    rng = np.random.default_rng(seed); rows = [set(r) for r in rows]; m = len(rows); acc = np.zeros(len(IU[0]))

    def trades(k):
        for a, b in rng.integers(0, m, size=(k, 2)):
            if a == b:
                continue
            A, B = rows[a], rows[b]; ao, bo = A - B, B - A
            if not ao or not bo:
                continue
            pool = list(ao | bo); rng.shuffle(pool); kk = len(ao); rows[a] = (A & B) | set(pool[:kk]); rows[b] = (A & B) | set(pool[kk:])
    trades(10 * m)
    for _ in range(n):
        trades(2 * m); acc += cooc(matrix([sorted(r) for r in rows]))
    return acc / n


pair_theme = [(theme_of.get(int(i)), theme_of.get(int(j))) for i, j in zip(*IU)]
FOOD = {"Keto, carbs, fasting", "Other diets", "Specific oils", "Cooking and cooking fats", "Staple foods", "Shopping", "Ingredient labels and processed food"}
sel = lambda f: np.array([bool(f(a, b)) for a, b in pair_theme])  # noqa: E731
SETS = {
    "within the same theme": sel(lambda a, b: a == b),
    "Politics - Politics": sel(lambda a, b: a == b == "Politics"),
    "Politics - Distrust of industry, medicine and media": sel(lambda a, b: {a, b} == {"Politics", "Distrust of industry, medicine and media"}),
    "Politics - Vaccines and COVID": sel(lambda a, b: {a, b} == {"Politics", "Vaccines and COVID"}),
    "Politics - food, diet and shopping themes": sel(lambda a, b: (a == "Politics" and b in FOOD) or (b == "Politics" and a in FOOD)),
    "Omega-6 / PUFA - Omega-6 / PUFA": sel(lambda a, b: a == b == "Omega-6 / PUFA biochemistry"),
    "Omega-6 / PUFA - Keto, carbs, fasting": sel(lambda a, b: {a, b} == {"Omega-6 / PUFA biochemistry", "Keto, carbs, fasting"}),
    "Omega-6 / PUFA - Studies and evidence": sel(lambda a, b: {a, b} == {"Omega-6 / PUFA biochemistry", "Studies and evidence"}),
    "Saturated-fat topic (4) - all other topics": np.array([4 in (int(i), int(j)) for i, j in zip(*IU)]),
    "the 299 all-years links": np.array([(int(i), int(j)) in ALL_LINKS for i, j in zip(*IU)]),
}
assert all(m.sum() > 0 for m in SETS.values()), [k for k, m in SETS.items() if m.sum() == 0]


def lift_sets(rows, seed):
    rows = list(rows); X = matrix(rows); O = cooc(X); E = curveball_mean(rows, N_NULL, seed); rng = np.random.default_rng(seed + 100)
    B = np.array([cooc(X, np.bincount(rng.integers(0, len(rows), len(rows)), minlength=len(rows)).astype(np.float32)) for _ in range(N_BOOT)])
    out = {"people": len(rows), "sets": {}}
    for name, m in SETS.items():
        bl = B[:, m].sum(1) / E[m].sum()
        out["sets"][name] = {"observed": int(O[m].sum()), "lift": round(float(O[m].sum() / E[m].sum()), 2),
                             "ci95": [round(float(np.percentile(bl, 2.5)), 2), round(float(np.percentile(bl, 97.5)), 2)]}
    return out


res = {"n_null": N_NULL, "n_boot": N_BOOT}
# 1. newcomer share per topic (writers from 2024)
P24 = D[D.post]; W = P24.groupby(["topic", "a"]).new.first().reset_index()
base = float(P24.groupby("a").new.first().mean())
share = W.groupby("topic").new.agg(["mean", "size"])
res["newcomer_share_of_writers_from_2024"] = round(100 * base, 1)
res["topic_newcomer_share"] = {int(t): {"words": words[int(t)], "theme": theme_of.get(int(t)), "writers": int(r["size"]), "newcomer_pct": round(100 * float(r["mean"]), 1)} for t, r in share.iterrows()}
th = pd.DataFrame([{"theme": theme_of.get(int(t)), "writers": int(r["size"]), "new": float(r["mean"]) * r["size"]} for t, r in share.iterrows()]).groupby("theme").sum()
res["theme_newcomer_share"] = {k: round(100 * float(v.new / v.writers), 1) for k, v in th.sort_values("new").iterrows()}
# 2. newcomers vs old guard, both from 2024
res["from_2024_newcomers"] = lift_sets(person_rows(P24[P24.new]).values, 11)
res["from_2024_old_guard"] = lift_sets(person_rows(P24[~P24.new]).values, 12)
# 3. old guard before vs from 2024: all, and the panel present (2+ topics) in both periods
OG = D[~D.new]; before, after = person_rows(OG[~OG.post]), person_rows(OG[OG.post])
res["old_guard_before_2024"] = lift_sets(before.values, 21)
res["old_guard_from_2024"] = res["from_2024_old_guard"]
panel = sorted(set(before.index) & set(after.index))
res["panel_old_guard_before_2024"] = lift_sets(before.loc[panel].values, 31)
res["panel_old_guard_from_2024"] = lift_sets(after.loc[panel].values, 32)
(P / "topic_network_cohorts.json").write_text(json.dumps(res, indent=1, default=float))

print(f"newcomer share of all writers from 2024: {res['newcomer_share_of_writers_from_2024']}%")
print("by theme (newcomer % of writers from 2024):", res["theme_newcomer_share"])
ts = sorted(res["topic_newcomer_share"].items(), key=lambda kv: -kv[1]["newcomer_pct"]); big = [kv for kv in ts if kv[1]["writers"] >= 150]
print("most newcomer topics:", [(v["words"][:25], v["newcomer_pct"]) for _, v in big[:6]]); print("most old-guard topics:", [(v["words"][:25], v["newcomer_pct"]) for _, v in big[-6:]])
cols = [("from_2024_newcomers", "new, 2024+"), ("from_2024_old_guard", "old, 2024+"), ("old_guard_before_2024", "old, <2024"),
        ("panel_old_guard_before_2024", "panel <2024"), ("panel_old_guard_from_2024", "panel 2024+")]
print("\npeople:", {lab: res[k]["people"] for k, lab in cols})
print(f"{'set':50s}" + "".join(f"{lab:>20s}" for _, lab in cols))
for name in SETS:
    print(f"{name[:50]:50s}" + "".join(f"{res[k]['sets'][name]['lift']:6.2f} [{res[k]['sets'][name]['ci95'][0]:.2f},{res[k]['sets'][name]['ci95'][1]:.2f}]" for k, _ in cols))
