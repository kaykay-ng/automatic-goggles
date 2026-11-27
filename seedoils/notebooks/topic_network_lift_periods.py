"""Before vs from 2024 on the topic network, by LIFT instead of link counts (user request 27 Nov). The all-years network
(topic_cooccurrence_network.py: all-years links) stays the structure; this script measures, separately in each period and with ALL
people active in that period (documents in 2+ topics in that period), how much more often than chance topic pairs are written by the same people.
Per period: observed O = people who wrote in both topics; expected E = mean over curveball randomisations of that period's person x topic
matrix (every person's number of topics and every topic's number of people kept; N_NULL samples). Lift = sum O / sum E over a set of topic
pairs (a theme pair, or the all-years links). 95% intervals: 400 bootstrap resamples of the period's people (O recomputed, E kept fixed:
the null mean is a property of the margins and changes little under resampling). No significance threshold, so weak co-writing is not thrown away.
Output: data/processed/topic_network_lift_periods.json (aggregates only).
Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/topic_network_lift_periods.py [n_null]"""
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

P, RAW = Path("seedoils/data/processed"), Path("seedoils/data/raw_haoyu")  # 27 Nov: reference raw data (the rerun); outliers.py table below
REB = Path("seedoils/data/processed_rebuild_prob")
N_NULL = int(sys.argv[1]) if len(sys.argv) > 1 else 200
N_BOOT = 400
cauth, pauth = {}, {}
with gzip.open(glob.glob(str(RAW / "*StopEatingSeedOils_comments.jsonl.gz"))[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); cauth[x["id"]] = x["author"]
with gzip.open(glob.glob(str(RAW / "*StopEatingSeedOils_posts.jsonl.gz"))[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); pauth[x["id"]] = x.get("author") or ""
D = pd.read_csv(REB / "seso_doc_topics_official005.csv.gz", usecols=["id", "created_utc", "topic"]); D["id"] = D.id.astype(str)
# 27 Nov: ONLY documents with a confident topic = BERTopic's reduce_outliers (probabilities strategy, threshold 0.05; outliers_official.py); outliers below it (topic -1, 28.8% of documents) are not used
D = D[D.topic >= 0].copy(); _k = pd.read_csv(REB / "seso_doc_topics.csv.gz", usecols=["id", "kind"]); D["kind"] = D.id.map(dict(zip(_k.id.astype(str), _k.kind)))
D["a"] = np.where(D.kind == "comment", D.id.map(cauth), D.id.map(pauth))
D = D[D.a.notna() & (D.a != "") & ~D.a.isin(["[deleted]", "AutoModerator"]) & not_bot(D.a.fillna(""))]
K = int(D.topic.max()) + 1; IU = np.triu_indices(K, 1)
TH = json.loads((P / THEMES_FILE).read_text()); theme_of = {int(t): n.split(" (")[0] for n, ids in TH.items() for t in ids}
NET = json.loads((P / "topic_cooccurrence_network.json").read_text())
ALL_LINKS = {(min(e["a"], e["b"]), max(e["a"], e["b"])) for e in NET["edges_all"]}
words = {n["topic"]: n["words"] for n in NET["nodes"]}


def rows_of(docs):
    s = docs.groupby("a").topic.apply(lambda x: sorted(set(int(t) for t in x))); return [r for r in s.values if len(r) >= 2]


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


def sel(f):
    return np.array([bool(f(a, b)) for a, b in pair_theme])


SETS = {
    "within the same theme": sel(lambda a, b: a is not None and a == b),
    "between different themes": sel(lambda a, b: a is not None and b is not None and a != b),
    "Politics - Politics": sel(lambda a, b: a == b == "Politics"),
    "Politics - Distrust of industry, medicine and media": sel(lambda a, b: {a, b} == {"Politics", "Distrust of industry, medicine and media"}),
    "Politics - Vaccines and COVID": sel(lambda a, b: {a, b} == {"Politics", "Vaccines and COVID"}),
    "Politics - Studies and evidence": sel(lambda a, b: {a, b} == {"Politics", "Studies and evidence"}),
    "Politics - food, diet and shopping themes": sel(lambda a, b: (a == "Politics" and b in FOOD) or (b == "Politics" and a in FOOD)),
    "Omega-6 / PUFA - Omega-6 / PUFA": sel(lambda a, b: a == b == "Omega-6 / PUFA biochemistry"),
    "Omega-6 / PUFA - Keto, carbs, fasting": sel(lambda a, b: {a, b} == {"Omega-6 / PUFA biochemistry", "Keto, carbs, fasting"}),
    "Omega-6 / PUFA - Studies and evidence": sel(lambda a, b: {a, b} == {"Omega-6 / PUFA biochemistry", "Studies and evidence"}),
    "Saturated-fat topic (4) - all other topics": np.array([4 in (int(i), int(j)) for i, j in zip(*IU)]),
    "the all-years links": np.array([(int(i), int(j)) in ALL_LINKS for i, j in zip(*IU)]),
}
# theme names in the selections above use the short theme name (text before " (")
for k in list(SETS):
    if SETS[k].sum() == 0:
        print("WARNING empty set:", k)

res, per_link = {}, {}
for label, docs, seed in (("before 2024", D[D.created_utc < SPLIT_TS], 1), ("from 2024", D[D.created_utc >= SPLIT_TS], 2)):
    rows = rows_of(docs); X = matrix(rows); O = cooc(X); E = curveball_mean(rows, N_NULL, seed)
    rng = np.random.default_rng(7); boots = []
    for _ in range(N_BOOT):
        w = np.bincount(rng.integers(0, len(rows), len(rows)), minlength=len(rows)).astype(np.float32); boots.append(cooc(X, w))
    Bt = np.array(boots)
    res[label] = {"people": len(rows), "sets": {}}
    for name, m in SETS.items():
        lift = O[m].sum() / E[m].sum(); bl = Bt[:, m].sum(1) / E[m].sum()
        res[label]["sets"][name] = {"pairs": int(m.sum()), "observed": int(O[m].sum()), "expected": round(float(E[m].sum()), 1), "lift": round(float(lift), 2),
                                    "ci95": [round(float(np.percentile(bl, 2.5)), 2), round(float(np.percentile(bl, 97.5)), 2)]}
    per_link[label] = {(int(i), int(j)): (float(O[k]), float(E[k])) for k, (i, j) in enumerate(zip(*IU)) if (int(i), int(j)) in ALL_LINKS}
    print(label, "people", len(rows), flush=True)

# the all-years links: change in lift per link (pairs with at least 3 expected co-writers in both periods)
rows = []
for (i, j) in ALL_LINKS:
    (o1, e1), (o2, e2) = per_link["before 2024"][(i, j)], per_link["from 2024"][(i, j)]
    if e1 >= 3 and e2 >= 3:
        rows.append({"a": i, "b": j, "words_a": words[i], "words_b": words[j], "theme_a": theme_of.get(i), "theme_b": theme_of.get(j),
                     "lift_before": round(o1 / e1, 2), "lift_from": round(o2 / e2, 2), "log2_change": round(float(np.log2((o2 / e2) / (o1 / e1))) if o1 > 0 and o2 > 0 else np.nan, 2)})
L = pd.DataFrame(rows).dropna(subset=["log2_change"]).sort_values("log2_change")
out = {"n_null": N_NULL, "n_boot": N_BOOT, "periods": res,
       "links_compared": int(len(L)), "links_stronger_pct": round(100 * float((L.log2_change > 0).mean()), 1),
       "median_log2_change": round(float(L.log2_change.median()), 2),
       "strengthened_most": L.tail(10).iloc[::-1].to_dict("records"), "weakened_most": L.head(10).to_dict("records")}
(P / "topic_network_lift_periods.json").write_text(json.dumps(out, indent=1, default=float))
print(f"\n{'set':55s} {'before 2024':>22s} {'from 2024':>22s}")
for name in SETS:
    a, b = res["before 2024"]["sets"][name], res["from 2024"]["sets"][name]
    print(f"{name:55s} {a['lift']:5.2f} [{a['ci95'][0]:.2f}, {a['ci95'][1]:.2f}] (O {a['observed']:>5}) {b['lift']:5.2f} [{b['ci95'][0]:.2f}, {b['ci95'][1]:.2f}] (O {b['observed']:>6})")
print(f"\nall-years links compared: {len(L)}; stronger from 2024: {out['links_stronger_pct']}%; median log2 change {out['median_log2_change']}")
for r in out["strengthened_most"][:6]:
    print("UP  ", r["words_a"][:25], "|", r["words_b"][:25], r["lift_before"], "->", r["lift_from"])
for r in out["weakened_most"][:6]:
    print("DOWN", r["words_a"][:25], "|", r["words_b"][:25], r["lift_before"], "->", r["lift_from"])
