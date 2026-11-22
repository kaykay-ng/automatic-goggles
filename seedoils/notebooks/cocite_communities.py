"""Stable, labelled communities in the two co-citation networks.

Run from final_project/ after cocitation_network.py:
  ./.venv-nlp/bin/python seedoils/notebooks/cocite_communities.py
  -> seedoils/data/processed/cocite_communities_<network>.csv (one row per community), cocite_node_communities.csv,
     cocite_communities_summary.txt

1. Stability: Louvain with SEEDS different seeds on the same graph (edges loaded in a fixed order). Pairwise adjusted mutual information
   (AMI) between runs; the REFERENCE partition is the run with the highest mean AMI to all others (the most typical run).
2. Per reference community, stability = for each pair of its papers, the share of runs that also put them together, averaged over pairs
   (sampled to MAX_PAIRS pairs for big communities). 1 = always together; low = the community is an accident of one run.
3. Labels: most common OpenAlex primary topics (display names), and the title words most distinctive of the community: c-TF-IDF over
   titles with English stopwords removed, min_df 3, words and bigrams (as in BERTopic). Plus side mix, design mix (MeSH), median year,
   most-cited papers by number of distinct citing users.
"""
import csv
import gzip
import json
import random
import statistics
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import networkx as nx
import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
from sklearn.metrics import adjusted_mutual_info_score

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
SEEDS = 20
MIN_SIZE = 20
MAX_PAIRS = 3000
STOP = ENGLISH_STOP_WORDS | {"study", "studies", "effect", "effects", "review", "systematic", "analysis", "association", "associations",
                             "risk", "trial", "randomized", "controlled", "meta", "humans", "human", "based", "versus", "results", "use"}


def load_nodes():
    with open(PROC / "cocite_nodes.csv", encoding="utf-8") as f:
        nodes = {r["openalex_id"]: r for r in csv.DictReader(f)}
    topic = {}
    with gzip.open(RAW / "openalex_works.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            w = json.loads(line)["work"]
            if w and w["id"] in nodes:
                topic[w["id"]] = ((w.get("primary_topic") or {}).get("display_name")) or "?"
    return nodes, topic


def load_graph(kind):
    G = nx.Graph()
    with open(PROC / f"cocite_{kind}_edges.csv") as f:
        rows = sorted(csv.DictReader(f), key=lambda r: (r["source"], r["target"]))  # fixed order across runs
    for r in rows:
        G.add_edge(r["source"], r["target"], weight=float(r["weight"]))
    return G


def ctfidf_labels(groups, nodes, k=8):
    ids = sorted(groups)
    docs = [" ".join(nodes[n]["title"] for n in groups[c]) for c in ids]
    cv = CountVectorizer(stop_words=list(STOP), min_df=3, ngram_range=(1, 2), token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z\-]{2,}\b")
    X = cv.fit_transform(docs).toarray().astype(float)
    tf = X / np.maximum(X.sum(axis=1, keepdims=True), 1)
    avg = X.sum() / len(ids)
    idf = np.log(1 + avg / np.maximum(X.sum(axis=0), 1))
    S = tf * idf
    vocab = np.array(cv.get_feature_names_out())
    return {c: ", ".join(vocab[np.argsort(-S[i])[:k]]) for i, c in enumerate(ids)}


def analyse(kind, nodes, topic, lines, node_rows):
    G = load_graph(kind)
    runs = []
    for s in range(SEEDS):
        comms = nx.community.louvain_communities(G, weight="weight", seed=s)
        runs.append(({n: i for i, c in enumerate(comms) for n in c}, nx.community.modularity(G, comms, weight="weight"), len(comms)))
    order = list(G)
    labels = [[r[0][n] for n in order] for r in runs]
    ami = np.ones((SEEDS, SEEDS))
    for i, j in combinations(range(SEEDS), 2):
        ami[i, j] = ami[j, i] = adjusted_mutual_info_score(labels[i], labels[j])
    ref = int(np.argmax(ami.mean(axis=1)))
    off = ami[np.triu_indices(SEEDS, 1)]
    Qs, ks = [r[1] for r in runs], [r[2] for r in runs]
    lines.append(f"\n== {kind}: {SEEDS} Louvain seeds; modularity {min(Qs):.3f}-{max(Qs):.3f}; communities {min(ks)}-{max(ks)} "
                 f"(>= {MIN_SIZE} papers: {min(sum(1 for v in Counter(r[0].values()).values() if v >= MIN_SIZE) for r in runs)}-"
                 f"{max(sum(1 for v in Counter(r[0].values()).values() if v >= MIN_SIZE) for r in runs)}); "
                 f"pairwise AMI mean {off.mean():.3f} (min {off.min():.3f}); reference = seed {ref}")
    refmap = runs[ref][0]
    groups = defaultdict(list)
    for n, c in refmap.items():
        groups[c].append(n)
    ranked = sorted(groups, key=lambda c: -len(groups[c]))
    renum = {c: i for i, c in enumerate(ranked)}
    big = {renum[c]: groups[c] for c in ranked if len(groups[c]) >= MIN_SIZE}
    words = ctfidf_labels(big, nodes)
    rng = random.Random(0)
    out = []
    for cid, members in big.items():
        pairs = list(combinations(members, 2))
        if len(pairs) > MAX_PAIRS:
            pairs = rng.sample(pairs, MAX_PAIRS)
        stab = statistics.mean(sum(r[0][a] == r[0][b] for r in runs) / SEEDS for a, b in pairs)
        sides = Counter(nodes[n]["side"] for n in members)
        des = Counter(nodes[n]["design"] for n in members)
        leans = [float(nodes[n]["lean"]) for n in members]
        years = sorted(int(nodes[n]["year"]) for n in members if nodes[n]["year"])
        tops = Counter(topic.get(n, "?") for n in members).most_common(3)
        users = lambda n: int(nodes[n]["users_SESO"]) + int(nodes[n]["users_SciNut"])
        best = sorted(members, key=lambda n: -users(n))[:4]
        row = {"network": kind, "community": cid, "n_papers": len(members), "stability": round(stab, 3),
               "mean_lean": round(statistics.mean(leans), 3), "n_SESO_only": sides["SESO"], "n_both": sides["both"], "n_SciNut_only": sides["SciNut"],
               "share_animal": round(des["animal"] / len(members), 3), "share_humans_only": round(des["humans only"] / len(members), 3),
               "median_year": years[len(years) // 2] if years else "", "top_topics": "; ".join(f"{t} ({k})" for t, k in tops),
               "distinctive_title_words": words[cid],
               "top_papers": " | ".join(f"[{nodes[n]['users_SESO']}/{nodes[n]['users_SciNut']}] {nodes[n]['title'][:70]} ({nodes[n]['year']})" for n in best)}
        out.append(row)
        for n in members:
            node_rows.append((kind, n, cid))
    with open(PROC / f"cocite_communities_{kind}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    for r in sorted(out, key=lambda r: -r["mean_lean"]):
        lines.append(f"  c{r['community']}: {r['n_papers']} papers, stability {r['stability']:.2f}, lean {r['mean_lean']:+.2f} "
                     f"(SESO-only {r['n_SESO_only']}, both {r['n_both']}, SciNut-only {r['n_SciNut_only']}), animal {r['share_animal']:.0%}, "
                     f"median year {r['median_year']}")
        lines.append(f"      words: {r['distinctive_title_words']}")
        lines.append(f"      topics: {r['top_topics']}")
        lines.append(f"      papers [SESO/SciNut users]: {r['top_papers']}")


def main():
    nodes, topic = load_nodes()
    lines, node_rows = [], []
    for kind in ("scholarly", "reddit"):
        analyse(kind, nodes, topic, lines, node_rows)
    with open(PROC / "cocite_node_communities.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["network", "openalex_id", "community"])
        w.writerows(node_rows)
    text = "\n".join(lines)
    (PROC / "cocite_communities_summary.txt").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
