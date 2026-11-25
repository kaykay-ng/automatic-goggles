"""Builds the aggregate datasets behind the 'Seed Oil Debate' artifact (six figures). Aggregates and paper titles only: no usernames, no comment text.

Run from final_project/ after the analyses it reads have run:
  ../.venv/bin/python seedoils/notebooks/artifact_data.py        -> seedoils/data/processed/artifact/<dataset>.json  ({"rows": [...], "meta": [...]})
Needs (all produced earlier in this project): cocite_nodes.csv, cocite_scholarly_edges.csv, cocite_node_communities.csv, cocite_communities_scholarly.csv,
cocite_null_runs.csv, cocite_null_summary.txt, openalex_works.jsonl.gz, paper_labels_*.csv, comment_labels_part1-3.csv, comments_key.csv,
seso_/scinut_ doc_topics + topics_info + topic_votes, emotion_summary.csv (optional), author_subreddit_counts*.jsonl.gz (partial is fine).

Datasets: facts, paper_nodes, paper_edges, paper_communities, community_links, bridges, null_summary, null_runs, science, online, matching,
topic_themes, emotion, cocomment_nodes, cocomment_edges, cocomment_share.
"""
import csv
import gzip
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from alignment import evidence_type  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
OUT = PROC / "artifact"
SPLIT = 1704067200
SESO, SCINUT = "StopEatingSeedOils", "ScientificNutrition"
COMM_NAMES = {0: "Meat and mortality cohorts", 1: "Keto and low-carb", 2: "Omega-6 / linoleic acid", 3: "Vegetarian and vegan diets",
              4: "Saturated fat and heart disease", 5: "LDL and lipoproteins", 6: "Sugar and metabolic health", 7: "Protein and muscle",
              8: "Hunter-gatherers and foods", 9: "Vitamin D and omega-3", 10: "Rodent fat and cancer studies", 11: "Fasting",
              12: "Oxidised oils and frying", 13: "Olive oil and Mediterranean diet", 99: "Smaller groups"}
SEED_COMMS = {2, 10, 4, 5}
SOURCE_TEXT = Path(__file__).read_text(encoding="utf-8")


def meta(*notes):
    m = [{"label": "artifact_data.py", "value": SOURCE_TEXT, "type": "code", "lang": "python"}]
    m += [{"label": a, "value": b} for a, b in notes]
    return m


def save(name, rows, *notes):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps({"rows": rows, "meta": meta(*notes)}, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(f"{name}: {len(rows):,} rows")


def f(x, nd=4):
    return round(float(x), nd)


# ---------------------------------------------------------------- papers / network
def papers_network():
    nodes = {r["openalex_id"]: r for r in csv.DictReader(open(PROC / "cocite_nodes.csv", encoding="utf-8"))}
    com = {r["openalex_id"]: int(r["community"]) for r in csv.DictReader(open(PROC / "cocite_node_communities.csv")) if r["network"] == "scholarly"}
    stab = {int(r["community"]): r for r in csv.DictReader(open(PROC / "cocite_communities_scholarly.csv", encoding="utf-8"))}
    G = nx.Graph()
    for r in csv.DictReader(open(PROC / "cocite_scholarly_edges.csv")):
        G.add_edge(r["source"], r["target"])
    total_nodes = G.number_of_nodes()
    G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    c = dict(com)
    for _ in range(6):  # nodes outside the big communities join the community most of their neighbours are in
        for n in G:
            if n not in c:
                cnt = Counter(c[m] for m in G[n] if m in c)
                if cnt:
                    c[n] = cnt.most_common(1)[0][0]
    for n in G:
        c.setdefault(n, 99)
    ids = sorted(set(c[n] for n in G))
    size = {k: sum(1 for n in G if c[n] == k) for k in ids}
    # bubble layout: communities placed by normalised cross-links, then pushed apart until circles no longer overlap
    CG = nx.Graph()
    cross = Counter()
    for a, b in G.edges():
        if c[a] != c[b]:
            cross[tuple(sorted((c[a], c[b])))] += 1
    for k in ids:
        CG.add_node(k)
    for (a, b), w in cross.items():
        CG.add_edge(a, b, weight=w / np.sqrt(size[a] * size[b]))
    cp = nx.spring_layout(CG, weight="weight", k=1.3, iterations=600, seed=4)
    centers = {k: np.array(cp[k]) * 1.0 for k in ids}
    radius = {k: 0.11 * np.sqrt(size[k]) / np.sqrt(60) * 1.0 for k in ids}
    for _ in range(400):
        for a in ids:
            for b in ids:
                if a < b:
                    d = centers[a] - centers[b]
                    dist = np.linalg.norm(d) + 1e-9
                    gap = radius[a] + radius[b] + 0.03 - dist
                    if gap > 0:
                        push = d / dist * gap / 2
                        centers[a] += push
                        centers[b] -= push
    allc = np.array(list(centers.values()))
    span = max(np.abs(allc).max() + max(radius.values()), 1e-6)
    scale = 0.95 / span
    pos = {}
    for k in ids:
        mem = [n for n in G if c[n] == k]
        sg = G.subgraph(mem)
        p = nx.spring_layout(sg, k=0.6 / np.sqrt(len(mem)), iterations=200, seed=1) if len(mem) > 2 else {n: np.array([0.0, 0.0]) for n in mem}
        P = np.array([p[n] for n in mem])
        P = P - P.mean(0)
        P = P / (np.linalg.norm(P, axis=1).max() or 1) * radius[k] * 0.9
        for n, q in zip(mem, P):
            pos[n] = (q + centers[k]) * scale
    rows = []
    idx = {}
    for i, n in enumerate(sorted(G, key=lambda n: (c[n], n))):
        idx[n] = i
        nd = nodes[n]
        rows.append({"i": i, "x": f(pos[n][0]), "y": f(pos[n][1]), "c": c[n], "title": nd["title"][:140], "year": int(nd["year"]) if nd["year"] else None,
                     "users_seso": int(nd["users_SESO"]), "users_scinut": int(nd["users_SciNut"]), "lean": float(nd["lean"]), "side": nd["side"],
                     "design": nd["design"]})
    edges = [{"s": idx[a], "t": idx[b]} for a, b in G.edges()]
    comm_rows = []
    for k in ids:
        mem = [n for n in G if c[n] == k]
        st = stab.get(k)
        comm_rows.append({"c": k, "name": COMM_NAMES.get(k, f"Group {k}"), "seed_oil_community": k in SEED_COMMS, "n_papers": len(mem),
                          "cx": f(centers[k][0] * scale), "cy": f(centers[k][1] * scale), "r": f(radius[k] * scale),
                          "mean_lean": f(np.mean([float(nodes[n]["lean"]) for n in mem]), 3),
                          "share_animal": f(np.mean([nodes[n]["design"] == "animal" for n in mem]), 3),
                          "stability": float(st["stability"]) if st else None})
    link_rows = [{"a": a, "b": b, "n_links": w} for (a, b), w in sorted(cross.items(), key=lambda kv: -kv[1])]
    note = ("Scholarly co-citation network of papers cited by at least 2 distinct Reddit users in r/StopEatingSeedOils or r/ScientificNutrition; two papers "
            "are linked when one cites the other (OpenAlex referenced works). Largest connected component only: "
            f"{G.number_of_nodes():,} of {total_nodes:,} papers. Communities = Louvain, reference run of 20 seeds (cocite_communities.py).")
    save("paper_nodes", rows, ("Network", note), ("Layout", "Community map: bubbles placed by normalised links between communities and pushed apart; papers placed inside "
                                                   "their bubble by a spring layout of their own links. Positions carry no other meaning."))
    save("paper_edges", edges, ("Network", note), ("Columns", "s and t are the i of the two papers in paper_nodes"))
    save("paper_communities", comm_rows, ("Stability", "Share of 20 Louvain runs that keep a community's paper pairs together (1 = always)."))
    save("community_links", link_rows, ("Network", "Number of paper-to-paper links between two communities."))
    return G, nodes, c, idx


def bridges(nodes, G):
    works = {}
    with gzip.open(RAW / "openalex_works.jsonl.gz", "rt", encoding="utf-8") as fh:
        for line in fh:
            w = json.loads(line)["work"]
            if w and w["id"] in nodes:
                works[w["id"]] = w
    D = nx.DiGraph()
    D.add_nodes_from(nodes)
    for n, w in works.items():
        for ref in w.get("referenced_works") or []:
            if ref in nodes and ref != n:
                D.add_edge(n, ref)  # citing -> cited: the cited paper receives rank
    pr = nx.pagerank(D, alpha=0.85)
    rows = {}
    top_b = sorted(nodes, key=lambda n: -float(nodes[n]["betweenness_reddit"]))[:12]
    top_p = sorted(nodes, key=lambda n: -pr[n])[:12]
    for n in dict.fromkeys(top_b + top_p):
        nd = nodes[n]
        rows[n] = {"title": nd["title"][:110], "year": int(nd["year"]) if nd["year"] else None, "side": nd["side"], "lean": float(nd["lean"]),
                   "users_seso": int(nd["users_SESO"]), "users_scinut": int(nd["users_SciNut"]), "betweenness": f(float(nd["betweenness_reddit"]), 5),
                   "pagerank": f(pr[n], 5), "top_betweenness": n in top_b, "top_pagerank": n in top_p}
    save("bridges", list(rows.values()), ("Betweenness", "Sampled (k=500) betweenness in the Reddit co-citation network (papers linked when the same user cited both)."),
         ("PageRank", "PageRank (alpha 0.85) on the directed citation graph among the network's papers: a paper gains rank when many papers cite it."))


def null_model():
    txt = (PROC / "cocite_null_summary.txt").read_text()
    out, runs = [], []
    for block in re.split(r"\n== ", txt):
        m = re.match(r"(?:== )?(scholarly|reddit):", block.strip())
        if not m:
            continue
        net = m.group(1)
        obs = re.search(r"observed: modularity ([\d.]+).*?side assortativity ([\d.-]+)", block)
        rew = re.search(r"modularity ([\d.]+) \+/- ([\d.]+).*?\n\s+side assortativity ([\d.-]+) \+/- ([\d.]+)", block, re.S)
        shuf = re.search(r"label shuffle \(\d+ reps\): side assortativity ([\d.-]+) \+/- ([\d.]+)", block)
        out.append({"network": net, "measure": "modularity", "observed": float(obs.group(1)), "null_mean": float(rew.group(1)), "null_sd": float(rew.group(2))})
        out.append({"network": net, "measure": "side assortativity", "observed": float(obs.group(2)), "null_mean": float(rew.group(3)), "null_sd": float(rew.group(4))})
        out.append({"network": net, "measure": "side assortativity (labels shuffled)", "observed": float(obs.group(2)), "null_mean": float(shuf.group(1)),
                    "null_sd": float(shuf.group(2))})
    for r in csv.DictReader(open(PROC / "cocite_null_runs.csv")):
        runs.append({"network": r["network"], "rep": int(r["rep"]), "modularity": float(r["modularity"]), "side_assortativity": float(r["side_assortativity"])})
    note = ("Null models of cocitation_null.py: degree-preserving rewiring (2 swaps per edge, 50 repetitions) and side-label shuffling (200 repetitions). "
            "Observed values from the networks of cocitation_network.py.")
    save("null_summary", out, ("Null models", note))
    save("null_runs", runs, ("Null models", note))
    return out


# ---------------------------------------------------------------- labels: science, online, matching
def alignment_data():
    papers = {}
    for fn in ("paper_labels_omega6.csv", "paper_labels_satfat_rodent.csv", "paper_labels_ldl.csv"):
        for r in csv.DictReader(open(PROC / fn, encoding="utf-8")):
            papers[r["openalex_id"]] = r
    rel = [p for p in papers.values() if p["relevance"] in ("yes", "partly")]
    groups = [("Human trials & meta-analyses", lambda p: evidence_type(p) == "human trials / meta of trials"),
              ("Human studies of deaths & disease", lambda p: p["population"] == "humans" and p["outcome"] == "hard"),
              ("Human observational studies", lambda p: evidence_type(p) == "human observational"),
              ("Reviews & statements", lambda p: evidence_type(p) == "review / statement"),
              ("Animal & cell studies", lambda p: evidence_type(p) == "animal / cell"),
              ("Other designs", lambda p: evidence_type(p) == "other")]
    sci = []
    for name, fn in groups:
        c = Counter(p["direction"] for p in rel if fn(p))
        n = sum(c[k] for k in ("harm", "mixed", "no_effect", "benefit"))
        sci.append({"evidence": name, "n": n, "harm": c["harm"], "mixed": c["mixed"], "no_effect": c["no_effect"], "benefit": c["benefit"]})
    key = {r["item_id"]: r for r in csv.DictReader(open(PROC / "comments_key.csv"))}
    lab = {}
    for i in (1, 2, 3):
        for r in csv.DictReader(open(PROC / f"comment_labels_part{i}.csv", encoding="utf-8")):
            lab[r["item_id"]] = r["position"]
    online = []
    for s, short in ((SESO, "r/StopEatingSeedOils"), (SCINUT, "r/ScientificNutrition")):
        for per, pl in (("pre2024", "before 2024"), ("from2024", "from 2024")):
            c = Counter(lab[i] for i, k in key.items() if "opinion" in k["samples"] and k["side"] == s and k["period"] == per and i in lab)
            online.append({"community": short, "period": pl, "n": sum(c.values()), "harmful": c["H"], "mixed": c["M"], "no_position": c["O"], "not_harmful": c["NH"]})
    matching = []
    for pos, name in (("H", "Comments saying seed oils are harmful"), ("NH", "Comments saying they are not harmful")):
        c, nc = Counter(), 0
        for i, k in key.items():
            if "citing" in k["samples"] and i in lab and lab[i] == pos:
                nc += 1
                for w in filter(None, k["cited_works"].split("|")):
                    if w in papers:
                        c[evidence_type(papers[w])] += 1
        matching.append({"comments": name, "n_comments": nc, "n_papers": sum(c.values()), "human_trials": c["human trials / meta of trials"],
                         "human_observational": c["human observational"], "animal_cell": c["animal / cell"], "review": c["review / statement"], "other": c["other"]})
    lbl = ("Labels", "Blind annotation by Claude subagents from abstracts (papers) and comment text (comments), with reasons and confidence; not validated by hand.")
    save("science", sci, lbl, ("Scope", f"{len(rel)} papers about seed oils, linoleic acid or polyunsaturated fat among the 499 in the four seed-oil communities. "
                                         "These are the papers Reddit users cite, not a sample of the literature. Rows overlap (deaths & disease is a subset)."))
    save("online", online, lbl, ("Sample", "Random comments (at least 15 words) mentioning seed oils, vegetable oils, canola, soybean oil, linoleic acid, omega-6 or PUFA; "
                                          "100 per row. Seed 11."))
    save("matching", matching, lbl, ("Sample", "150 documents per subreddit that link a paper of the four seed-oil communities; evidence type is from the paper labels."))
    return papers, sci, online, matching


# ---------------------------------------------------------------- topics
# Hand-picked topic ids per theme for the CURRENT topic models (refitted 22 Nov). Old ids are invalid after a refit, so they are read from files.
SESO_THEMES = json.loads((PROC / "themes_confirmed.json").read_text())
_SCI = PROC / "scinut_themes_confirmed.json"
SCINUT_THEMES = json.loads(_SCI.read_text()) if _SCI.exists() else {}  # TODO: r/ScientificNutrition themes not yet re-picked on the new topics


def topics():
    rows = []
    n_docs = {}
    for sub, pfx, themes in ((SESO, "seso", SESO_THEMES), (SCINUT, "scinut", SCINUT_THEMES)):
        T = pd.read_csv(PROC / f"{pfx}_doc_topics.csv.gz", usecols=["id", "created_utc", "topic"])
        T["per"] = np.where(T.created_utc >= SPLIT, "from2024", "pre2024")
        n_docs[sub] = len(T)
        V = pd.read_csv(PROC / f"{pfx}_topic_votes.csv").set_index("topic")
        tot = T.per.value_counts()
        for name, ids in themes.items():
            r = {"subreddit": f"r/{sub}", "theme": name}
            for per in ("pre2024", "from2024"):
                n = int(((T.per == per) & T.topic.isin(ids)).sum())
                r[f"n_{per}"] = n
                r[f"share_{per}_pct"] = f(100 * n / tot[per], 3)
                v = V.loc[[t for t in ids if t in V.index]]
                w = v[f"n_{per}"].fillna(0)
                r[f"vote_pct_{per}"] = f((v[f"mean_pct_{per}"].fillna(0) * w).sum() / w.sum(), 3) if w.sum() else None
            r["ratio"] = f(r["share_from2024_pct"] / r["share_pre2024_pct"], 2) if r["share_pre2024_pct"] else None
            rows.append(r)
    save("topic_themes", rows, ("Topics", "BERTopic (all-MiniLM-L6-v2, UMAP 5 dims, HDBSCAN min cluster 150, c-TF-IDF, outliers reassigned) on comments and self-posts of at least 15 "
                                          "words; a theme groups topics by hand (topic ids in the script). Share = documents in the theme / all documents of that period."),
         ("Reception", "vote_pct = mean within-thread percentile rank of a comment's score (same thread and level; 0.5 = typical); weighted by documents over the theme's topics."))
    return n_docs


# ---------------------------------------------------------------- emotion
def emotion():
    p = PROC / "emotion_summary.csv"
    if not p.exists():
        print("emotion_summary.csv missing: emotion dataset skipped")
        return None
    E = pd.read_csv(p)
    rows = []
    for r in E.itertuples():
        rows.append({"subreddit": f"r/{r.subreddit}", "theme": r.theme, "period": "from 2024" if r.period == "from2024" else "before 2024", "n": int(r.n),
                     "hostile_pct": f(100 * r.hostile_share, 1), "positive_pct": f(100 * r.positive_share, 1), "inquisitive_pct": f(100 * r.inquisitive_share, 1),
                     "neutral_pct": f(100 * r.neutral_share, 1), "hostile_mean": f(r.hostile_mean, 4)})
    save("emotion", rows, ("Classifier", "SamLowe/roberta-base-go_emotions (28 Reddit emotions, multi-label), text truncated to 256 tokens; share = documents whose group score is at least 0.5 "
                                     "(hostile_pct = disapproving tone: anger, annoyance, disapproval or disgust 0.5 or more; checked by hand on 150 comments: about 4 in 5 flagged comments are critical or hostile, about 1 in 4 hostile toward people)."),
         ("Sample", "r/StopEatingSeedOils: up to 1,200 documents per theme and period, plus a random baseline of 3,000 per period; r/ScientificNutrition: random 3,000 per period."))
    return rows


# ---------------------------------------------------------------- co-commenter network (partial fetch)
def cocommenter():
    paths = sorted(RAW.glob("author_subreddit_counts*.jsonl.gz"))
    seen, recs = set(), []
    for p in paths:
        try:
            with gzip.open(p, "rt", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        r = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if r["author"] not in seen:
                        seen.add(r["author"])
                        recs.append(r)
        except (EOFError, OSError):
            pass
    camps = defaultdict(set)
    for r in csv.DictReader(open(PROC / "seed_authors.csv")):
        camps[r["author"]].add(r["seed_subreddit"])
    fetched = Counter(s for r in recs for s in camps[r["author"]])
    print(f"co-commenter: {len(recs):,} authors fetched {dict(fetched)}")
    SEEDS_ = {SESO, SCINUT}  # r/carnivore no longer a seed (22 Nov)
    # an author is 'in' a subreddit with 3+ interactions (posts + comments) over the whole history; seed subreddits are left out
    subs_of = {}
    for r in recs:
        tot = Counter()
        for per in ("pre2024", "from2024"):
            tot.update(r["counts"].get(per, {}))
        subs_of[r["author"]] = {s for s, n in tot.items() if n >= 3 and s not in SEEDS_}
    N = sum(1 for v in subs_of.values() if v)
    n_auth = Counter(s for v in subs_of.values() for s in v)
    # share of seed authors active in each period (3+ interactions in the period) who also have 3+ interactions in the subreddit that period
    act = {"pre2024": 0, "from2024": 0}
    cnt = {"pre2024": Counter(), "from2024": Counter()}
    for r in recs:
        for per in act:
            cs = r["counts"].get(per, {})
            if sum(cs.values()) >= 3:
                act[per] += 1
                for s, n in cs.items():
                    if n >= 3:
                        cnt[per][s] += 1
    cand = [s for s, k in n_auth.items() if k >= 20]
    share = {s: (cnt["pre2024"][s], cnt["from2024"][s], 100 * cnt["pre2024"][s] / act["pre2024"], 100 * cnt["from2024"][s] / act["from2024"]) for s in cand}
    # subset that carries the story: the 30 subreddits with most seed authors, plus the 14 biggest risers and 14 biggest fallers (>= 60 authors)
    big = [s for s in cand if n_auth[s] >= 60]
    top = sorted(cand, key=lambda s: -n_auth[s])[:30]
    rise = sorted(big, key=lambda s: -(share[s][3] - share[s][2]))[:14]
    fall = sorted(big, key=lambda s: share[s][3] - share[s][2])[:14]
    keep = list(dict.fromkeys(top + rise + fall))
    kset = set(keep)
    pair = Counter()
    for v in subs_of.values():
        for a, b in __import__("itertools").combinations(sorted(v & kset), 2):
            pair[(a, b)] += 1
    allp = [(a, b, sh_, sh_ * N / (n_auth[a] * n_auth[b])) for (a, b), sh_ in pair.items()]
    F = nx.Graph()  # full overlap graph (lift > 1): used for the layout and the communities, so the picture is connected and meaningful
    F.add_nodes_from(keep)
    for a, b, sh_, lift in allp:
        if lift > 1:
            F.add_edge(a, b, weight=lift, dist=1 / lift)
    comms = nx.community.louvain_communities(F, weight="weight", seed=42)
    comm_of = {n: i for i, c in enumerate(sorted(comms, key=len, reverse=True)) for n in c}
    Q = nx.community.modularity(F, comms, weight="weight")
    pos = nx.kamada_kawai_layout(F, weight="dist")
    P = np.array([pos[n] for n in keep])
    P = (P - P.mean(0)) / (np.abs(P - P.mean(0)).max() or 1) * 0.9
    top = defaultdict(list)  # links drawn: each subreddit's 4 strongest (lift > 1, at least 4 shared commenters)
    for a, b, sh_, lift in allp:
        if sh_ >= 4 and lift > 1:
            top[a].append((lift, b, sh_))
            top[b].append((lift, a, sh_))
    drawn = {}
    for n, v in top.items():
        for lift, m, sh_ in sorted(v, reverse=True)[:4]:
            drawn[tuple(sorted((n, m)))] = (sh_, lift)
    G = nx.Graph()
    G.add_nodes_from(keep)
    G.add_edges_from(drawn)
    erows = [{"source": f"r/{a}", "target": f"r/{b}", "shared_authors": int(sh_), "lift": f(lift, 2)} for (a, b), (sh_, lift) in sorted(drawn.items(), key=lambda kv: -kv[1][1])]
    nrows = [{"subreddit": f"r/{s}", "x": f(x), "y": f(y), "community": comm_of[s], "n_authors": int(n_auth[s]), "degree": int(G.degree(s))} for s, (x, y) in zip(keep, P)]
    srows = [{"subreddit": f"r/{s}", "n_pre2024": share[s][0], "n_from2024": share[s][1], "share_pre2024_pct": f(share[s][2], 1), "share_from2024_pct": f(share[s][3], 1),
              "group": "riser" if s in rise else ("faller" if s in fall else "top by authors")} for s in keep]
    note = (f"PRELIMINARY. {len(recs):,} of the 4,292 selected commenters have been fetched so far ({', '.join(f'{k}: {v}' for k, v in fetched.items())} selected from each "
            "subreddit); the fetch runs from the most active r/StopEatingSeedOils commenters outward, so this is the neighbourhood of the heaviest seed-oil commenters. "
            "The seed subreddits themselves are left out (every selected author is in them by construction).")
    save("cocomment_nodes", nrows, ("Status", note), ("Subset", f"{len(keep)} of {len(cand):,} subreddits with at least 20 fetched commenters (3+ interactions each): the 30 with most commenters plus the 14 biggest "
                                                      f"risers and 14 biggest fallers in share from 2024 (at least 60 commenters). Lift = shared x all / (n_a x n_b). Layout: Kamada-Kawai on all pairs with lift > 1 (distance = 1 / lift); drawn links: each subreddit's 4 strongest (at least 4 shared). "
                                                      f" Groups = Louvain on all pairs with lift > 1 (seed 42, modularity {Q:.2f}: the groups overlap a lot, so read them as rough corners, not clean communities)."))
    save("cocomment_edges", erows, ("Status", note))
    save("cocomment_share", srows, ("Status", note), ("Share", f"Share of fetched commenters active in the period (3+ interactions) who also have 3+ interactions in the subreddit that period. "
                                                      f"Active before 2024: {act['pre2024']}; from 2024: {act['from2024']}."))
    return {"cocomment_fetched": len(recs), "cocomment_total": len(camps)}


# ---------------------------------------------------------------- facts
def who_stats():
    first, n_by = {}, defaultdict(Counter)
    author_of = {}
    for s in (SESO, SCINUT):  # r/carnivore comments no longer downloaded (22 Nov)
        with gzip.open(RAW / f"{s}_comments.jsonl.gz", "rt", encoding="utf-8") as fh:
            for line in fh:
                x = json.loads(line)
                a = x.get("author") or ""
                if a in ("[deleted]", "AutoModerator") or a.lower().endswith("bot"):
                    continue
                t = int(x["created_utc"])
                first[(s, a)] = min(first.get((s, a), t), t)
                n_by[s][(a, "from2024" if t >= SPLIT else "pre2024")] += 1
                if s != "carnivore":
                    author_of[(s, x["id"])] = a
    who = {s: {p: {a for (a, pp) in n_by[s] if pp == p} for p in ("pre2024", "from2024")} for s in n_by}
    ever = {s: who[s]["pre2024"] | who[s]["from2024"] for s in who}
    return who, ever, first, author_of


def facts(sci, online, matching, null, who, ever, first, author_of, topics_rows, extra):
    F = []

    def add(key, value, label, unit=""):
        F.append({"key": key, "value": value, "label": label, "unit": unit})

    S = {r["evidence"]: r for r in sci}
    pct = lambda r, k: round(100 * r[k] / r["n"])
    add("trial_benefit", pct(S["Human trials & meta-analyses"], "benefit"), "Human trials and meta-analyses concluding benefit", "%")
    add("trial_harm", pct(S["Human trials & meta-analyses"], "harm"), "Human trials and meta-analyses concluding harm", "%")
    add("hard_benefit", pct(S["Human studies of deaths & disease"], "benefit"), "Human studies of deaths and disease concluding benefit", "%")
    add("hard_harm", pct(S["Human studies of deaths & disease"], "harm"), "Human studies of deaths and disease concluding harm", "%")
    add("animal_harm", pct(S["Animal & cell studies"], "harm"), "Animal and cell studies concluding harm", "%")
    add("n_relevant", sum(r["n"] for r in sci if r["evidence"] != "Human studies of deaths & disease"), "Papers about seed oils, linoleic acid or polyunsaturated fat among the labelled papers", "")
    O = {(r["community"], r["period"]): r for r in online}
    among = lambda r, k: round(100 * r[k] / (r["harmful"] + r["not_harmful"] + r["mixed"]))
    add("seso_harm_pre", among(O[("r/StopEatingSeedOils", "before 2024")], "harmful"), "Share 'harmful' among positions, r/StopEatingSeedOils before 2024", "%")
    add("seso_harm_from", among(O[("r/StopEatingSeedOils", "from 2024")], "harmful"), "Share 'harmful' among positions, r/StopEatingSeedOils from 2024", "%")
    add("scinut_harm_pre", among(O[("r/ScientificNutrition", "before 2024")], "harmful"), "Share 'harmful' among positions, r/ScientificNutrition before 2024", "%")
    add("scinut_harm_from", among(O[("r/ScientificNutrition", "from 2024")], "harmful"), "Share 'harmful' among positions, r/ScientificNutrition from 2024", "%")
    add("scinut_notharm_from", among(O[("r/ScientificNutrition", "from 2024")], "not_harmful"), "Share 'not harmful' among positions, r/ScientificNutrition from 2024", "%")
    M = {r["comments"][:19]: r for r in matching}
    h, nh = matching[0], matching[1]
    add("harm_cites_animal", round(100 * h["animal_cell"] / h["n_papers"]), "Papers cited by 'harmful' comments that are animal or cell studies", "%")
    add("notharm_cites_trials", round(100 * nh["human_trials"] / nh["n_papers"]), "Papers cited by 'not harmful' comments that are human trials", "%")
    add("notharm_cites_animal", round(100 * nh["animal_cell"] / nh["n_papers"]), "Papers cited by 'not harmful' comments that are animal or cell studies", "%")
    sn, se = SCINUT, SESO
    pct1 = lambda a, b: round(100 * a / b, 1)
    add("scinut_new", round(100 * (1 - len(who[sn]["from2024"] & who[sn]["pre2024"]) / len(who[sn]["from2024"]))), "r/ScientificNutrition commenters from 2024 who had not commented there before", "%")
    add("seso_new", round(100 * (1 - len(who[se]["from2024"] & who[se]["pre2024"]) / len(who[se]["from2024"]))), "r/StopEatingSeedOils commenters from 2024 who had not commented there before", "%")
    # seso_carn_pre / seso_carn_from (overlap with r/carnivore only) removed 22 Nov: one diet subreddit biases the measure (people moved between
    # r/carnivore, r/carnivorediet, r/AnimalBased). TODO: replace with overlap with a pre-declared SET of diet subreddits from the author histories.
    add("seso_commenters_from", len(who[se]["from2024"]), "r/StopEatingSeedOils commenters from 2024", "")
    add("seso_commenters_pre", len(who[se]["pre2024"]), "r/StopEatingSeedOils commenters before 2024", "")
    N = {(r["network"], r["measure"]): r for r in null}
    add("mod_sch", round(N[("scholarly", "modularity")]["observed"], 2), "Modularity, scholarly citation network", "")
    add("mod_sch_null", round(N[("scholarly", "modularity")]["null_mean"], 2), "Modularity of random networks with the same degrees, scholarly", "")
    add("mod_red", round(N[("reddit", "modularity")]["observed"], 2), "Modularity, Reddit co-citation network", "")
    add("mod_red_null", round(N[("reddit", "modularity")]["null_mean"], 2), "Modularity of random networks with the same degrees, Reddit", "")
    add("assort_sch", round(N[("scholarly", "side assortativity")]["observed"], 2), "Side assortativity, scholarly network", "")
    add("assort_red", round(N[("reddit", "side assortativity")]["observed"], 2), "Side assortativity, Reddit co-citation network", "")
    T = {(r["subreddit"], r["theme"]): r for r in topics_rows}
    pol = T[("r/StopEatingSeedOils", "Politics (RFK, Trump, left/right)")]
    bio = T[("r/StopEatingSeedOils", "Omega-6 / PUFA biochemistry")]
    add("politics_ratio", round(pol["ratio"], 1), "Growth of politics talk in r/StopEatingSeedOils from 2024 (share ratio)", "x")
    add("biochem_ratio", round(bio["ratio"], 1), "Change in omega-6 biochemistry talk in r/StopEatingSeedOils from 2024 (share ratio)", "x")
    for k, t in extra.items():
        add(k, t[0], t[1], t[2] if len(t) > 2 else "")
    save("facts", F, ("Facts", "Single numbers quoted in the text of the page, each computed from the other datasets or from the downloaded comments (who_changed.py logic)."))


def main():
    G, nodes, c, idx = papers_network()
    bridges(nodes, G)
    null = null_model()
    papers, sci, online, matching = alignment_data()
    n_docs = topics()
    T = pd.read_csv(PROC / "seso_topics_info.csv")  # noqa: F841 (documented input)
    trows = json.loads((OUT / "topic_themes.json").read_text())["rows"]
    emo = emotion()
    co = cocommenter()
    who, ever, first, author_of = who_stats()
    extra = {"n_docs_seso": (n_docs[SESO], "Comments and self-posts of at least 15 words in r/StopEatingSeedOils used for the topic model"), "n_papers_net": (G.number_of_nodes(), "Papers in the citation network (largest connected component)"), "n_edges_net": (G.number_of_edges(), "Citation links among them"),
             "cocomment_fetched": (co["cocomment_fetched"], "Selected commenters whose subreddit activity has been fetched so far"), "cocomment_total": (co["cocomment_total"], "Selected commenters in all")}
    comm = json.loads((OUT / "paper_communities.json").read_text())["rows"]
    st = [r["stability"] for r in comm if r["seed_oil_community"] and r["stability"] is not None]
    extra["stab_min"] = (round(100 * min(st)), "Least stable of the four seed-oil communities: share of Louvain runs that keep its papers together", "%")
    extra["stab_max"] = (round(100 * max(st)), "Most stable of the four seed-oil communities", "%")
    if emo:
        E = {(r["subreddit"], r["theme"], r["period"]): r for r in emo}
        g = lambda sub, th, per: E[(sub, th, per)]["hostile_pct"]
        extra["host_seso_pre"] = (g("r/StopEatingSeedOils", "all (random)", "before 2024"), "Comments with a disapproving tone in r/StopEatingSeedOils before 2024", "%")
        extra["host_seso_from"] = (g("r/StopEatingSeedOils", "all (random)", "from 2024"), "Comments with a disapproving tone in r/StopEatingSeedOils from 2024", "%")
        extra["host_scinut_pre"] = (g("r/ScientificNutrition", "all (random)", "before 2024"), "Comments with a disapproving tone in r/ScientificNutrition before 2024", "%")
        extra["host_scinut_from"] = (g("r/ScientificNutrition", "all (random)", "from 2024"), "Comments with a disapproving tone in r/ScientificNutrition from 2024", "%")
        extra["host_evid_pre"] = (g("r/StopEatingSeedOils", "studies & evidence", "before 2024"), "Comments with a disapproving tone about studies and evidence in r/StopEatingSeedOils before 2024", "%")
        extra["host_evid_from"] = (g("r/StopEatingSeedOils", "studies & evidence", "from 2024"), "Comments with a disapproving tone about studies and evidence in r/StopEatingSeedOils from 2024", "%")
    facts(sci, online, matching, null, who, ever, first, author_of, trows, extra)


if __name__ == "__main__":
    main()
