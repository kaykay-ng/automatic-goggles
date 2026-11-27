"""Co-thread communities of r/StopEatingSeedOils commenters: who shows up in the same threads, WITHOUT using topics or text (rerun data seedoils/data/raw_haoyu; bots and [deleted] removed).
Network: authors with >= MIN_T distinct threads (a thread = a post and its comments; an author is in a thread if they wrote a comment there). Two authors are linked by the sum over shared threads of 1/(n-1), n = number of kept authors in that thread
(Newman's weighting: a 300-person thread links people far more weakly than a 5-person thread). Backbone: disparity filter, alpha 0.05 (a link is kept if it is significant for at least one end). Louvain on the largest component, N_SEEDS seeds; the run with the highest modularity is the reference.
Checks: stability (AMI between seeds), null model (bipartite swap: author-thread incidences shuffled, author thread counts and thread sizes kept approximately; same filter and Louvain), old guard vs newcomers (newcomer = first comment from 2024-01-01).
Sub-niches: each community's over-represented topic GROUPS (the 14 groups of topic_tree.py on the rebuilt BERTopic) - topics were NOT used to build the communities, so this is a description, not a circular test.
Ingroup test (non-circular): communities are built from HALF of the threads (thread id parity) and tested on reply links in the OTHER half: share of replies where replier and target are in the same community, against the share expected if the replier had answered a random other participant of the same thread (controls for who is in the thread); 95% interval by resampling threads.
Output: seedoils/data/processed/cothread_communities.csv (per community), cothread_stats.json; membership with hashed names in seedoils/data/processed_rebuild/cothread_membership.csv (no usernames).
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/cothread_communities.py"""
import gzip, hashlib, json, sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.metrics import adjusted_mutual_info_score as ami

sys.path.insert(0, str(Path(__file__).parent))
from seedoil_common import is_bot  # noqa: E402

S, MIN_T, ALPHA, N_SEEDS, CUT = "StopEatingSeedOils", 3, 0.05, 8, pd.Timestamp("2024-01-01").timestamp()
RAW, PRO, REB = Path("seedoils/data/raw_haoyu"), Path("seedoils/data/processed"), Path("seedoils/data/processed_rebuild")
rng = np.random.default_rng(0)
ok = lambda a: isinstance(a, str) and a not in ("", "[deleted]") and not is_bot(a)

posts = {"t3_" + x["id"]: x.get("author") or "" for x in map(json.loads, gzip.open(RAW / f"{S}_posts.jsonl.gz", "rt"))}
rows = [(x["id"], x.get("author") or "", x["link_id"], x["parent_id"], int(x["created_utc"])) for x in map(json.loads, gzip.open(RAW / f"{S}_comments.jsonl.gz", "rt"))]
C = pd.DataFrame(rows, columns=["id", "a", "thread", "parent", "t"]); cauth = dict(zip("t1_" + C.id, C.a))
C["pa"] = [cauth.get(p) if p.startswith("t1_") else posts.get(p) for p in C.parent]
first = C[C.a.map(ok)].groupby("a").t.min(); old_author = (first < CUT)
CC = C[C.a.map(ok)]; pairs = CC[["a", "thread"]].drop_duplicates()
nthreads = pairs.groupby("a").size(); keep = nthreads[nthreads >= MIN_T].index
print(f"commenters {len(nthreads):,}; with >= {MIN_T} threads {len(keep):,} ({len(keep) / len(nthreads):.0%}); their comments {CC.a.isin(keep).mean():.0%} of all non-bot comments")
P = pairs[pairs.a.isin(keep)]; tsize = P.groupby("thread").a.nunique(); P = P[P.thread.isin(tsize[tsize >= 2].index)]
authors = np.array(sorted(P.a.unique())); aix = {a: i for i, a in enumerate(authors)}; threads = np.array(sorted(P.thread.unique())); tix = {t: i for i, t in enumerate(threads)}
E = np.column_stack([P.a.map(aix).values, P.thread.map(tix).values]); N = len(authors)
print(f"network input: {N:,} authors, {len(threads):,} threads, {len(E):,} author-thread pairs")


def weights(E, N, T):
    B = sp.csr_matrix((np.ones(len(E)), (E[:, 0], E[:, 1])), shape=(N, T)); n = np.asarray(B.sum(0)).ravel(); w = np.where(n > 1, 1 / np.maximum(n - 1, 1), 0)
    M = sp.triu((B @ sp.diags(w) @ B.T).tocsr(), k=1).tocoo(); return M.row, M.col, M.data


def backbone(i, j, w, N, alpha=ALPHA):
    s = np.bincount(i, w, N) + np.bincount(j, w, N); k = np.bincount(i, minlength=N) + np.bincount(j, minlength=N)
    ai = np.where(k[i] > 1, (1 - w / s[i]) ** (k[i] - 1), 1.0); aj = np.where(k[j] > 1, (1 - w / s[j]) ** (k[j] - 1), 1.0)
    m = (ai < alpha) | (aj < alpha); return i[m], j[m], w[m]


def louvain_runs(i, j, w, seeds):
    G = nx.Graph(); G.add_weighted_edges_from(zip(i.tolist(), j.tolist(), w.tolist())); cc = max(nx.connected_components(G), key=len); H = G.subgraph(cc).copy()
    runs = [nx.community.louvain_communities(H, weight="weight", seed=s) for s in seeds]; mods = [nx.community.modularity(H, c, weight="weight") for c in runs]; return H, runs, mods


def labels(H, comm):
    nodes = sorted(H.nodes); lab = {v: k for k, c in enumerate(sorted(comm, key=len, reverse=True)) for v in c}; return np.array(nodes), np.array([lab[v] for v in nodes])


i, j, w = weights(E, N, len(threads)); full = len(i); bi, bj, bw = backbone(i, j, w, N)
print(f"links: {full:,} -> {len(bi):,} kept by the disparity filter (alpha {ALPHA}); nodes with a kept link {len(set(bi) | set(bj)):,} of {N:,}")
H, runs, mods = louvain_runs(bi, bj, bw, range(N_SEEDS)); ref = int(np.argmax(mods)); nodes, lab = labels(H, runs[ref])
others = [labels(H, r)[1] for k, r in enumerate(runs) if k != ref]; amis = [ami(lab, o) for o in others]
sizes = np.bincount(lab); print(f"largest component {H.number_of_nodes():,} nodes ({H.number_of_nodes() / N:.0%} of authors), {H.number_of_edges():,} links; Louvain {N_SEEDS} seeds: modularity {np.mean(mods):.3f} ({min(mods):.3f}-{max(mods):.3f}); AMI across seeds {np.mean(amis):.2f} ({min(amis):.2f}-{max(amis):.2f}); communities {len(sizes)}; sizes {sizes[:14].tolist()}")
# null: bipartite swap
nm = []
for r in range(3):
    En = E.copy()
    for _ in range(6):
        p = rng.permutation(len(En)); h = len(En) // 2; a, b = p[:h], p[h:2 * h]; t = En[a, 1].copy(); En[a, 1] = En[b, 1]; En[b, 1] = t
    En = np.unique(En, axis=0); ni, nj, nw = backbone(*weights(En, N, len(threads)), N)
    if len(ni): _, rr, mm = louvain_runs(ni, nj, nw, [0]); nm.append(mm[0])
print(f"null (author-thread swaps x3): modularity {np.round(nm, 3).tolist()}, links kept {len(ni):,}")
# description
memb = pd.DataFrame({"author": authors[nodes], "comm": lab}); memb["old"] = memb.author.map(old_author).astype(bool); memb["threads"] = memb.author.map(nthreads)
D = pd.read_csv(REB / "seso_docs.csv.gz", usecols=["id", "author"]).merge(pd.read_csv(REB / "seso_doc_topics.csv.gz", usecols=["id", "topic"]), on="id")
tg = pd.read_csv(PRO / "topic_tree_topic_to_group_K14.csv").set_index("topic").group; D["g"] = D.topic.map(tg)
NAMES = {14: "Fats, PUFA, cholesterol", 7: "General seed-oil, nuts/seeds", 6: "Cooking oils, butter", 10: "Nutrition, meals, foods", 3: "Subreddit, science, politics, money", 9: "Shopping, dairy, sugar", 11: "Meat, animal fats",
         5: "Snacks, condiments, bread", 12: "Weight, keto, blood sugar", 4: "Tallow, frying", 2: "Doctors, pharma, vaccines", 8: "Chemicals, plastics, water", 13: "Drugs, mental health, allergy", 1: "Thanks, links"}
D = D.merge(memb[["author", "comm"]], on="author"); overall = D.g.value_counts(normalize=True); out = []
for c in range(min(12, len(sizes))):
    m = memb[memb.comm == c]; d = D[D.comm == c]; sh = d.g.value_counts(normalize=True); lift = (sh / overall).dropna(); lift = lift[sh >= 0.03].sort_values(ascending=False)
    out.append({"community": c, "authors": len(m), "old_guard_share": round(m.old.mean(), 2), "median_threads": float(m.threads.median()), "docs": len(d),
                "over_represented_topic_groups": "; ".join(f"{NAMES.get(int(g), g)} (x{lift[g]:.1f}, {100 * sh[g]:.0f}%)" for g in lift.index[:3])})
R = pd.DataFrame(out); R.to_csv(PRO / "cothread_communities.csv", index=False); pd.set_option("display.width", 300, "display.max_colwidth", 140); print(R.to_string(index=False))
memb.assign(author=memb.author.map(lambda a: hashlib.sha1(a.encode()).hexdigest()[:10])).to_csv(REB / "cothread_membership.csv", index=False)
# ingroup test: communities from half A of the threads, replies in half B
half = np.array([int(t, 36) % 2 for t in threads]); EA = E[half[E[:, 1]] == 0]; ai, aj, aw = weights(EA, N, len(threads)); ai, aj, aw = backbone(ai, aj, aw, N)
HA, ruA, moA = louvain_runs(ai, aj, aw, range(5)); nA, lA = labels(HA, ruA[int(np.argmax(moA))]); commA = dict(zip(authors[nA], lA))
print(f"\nhalf-A communities: {len(set(lA))} from {len(nA):,} authors, modularity {max(moA):.3f}")
tB = {t for t, h in zip(threads, half) if h == 1}; mates = P[P.thread.isin(tB) & P.a.isin(commA)].groupby("thread").a.apply(list).to_dict()
R2 = CC[CC.thread.isin(tB) & CC.pa.map(ok) & (CC.a != CC.pa)]; R2 = R2[R2.a.isin(commA) & R2.pa.isin(commA)].drop_duplicates(["a", "pa", "thread"])
obs, exp, thr, oldr = [], [], [], []
for r in R2.itertuples():
    ms = [x for x in mates.get(r.thread, []) if x != r.a]
    if not ms: continue
    obs.append(commA[r.a] == commA[r.pa]); exp.append(np.mean([commA[x] == commA[r.a] for x in ms])); thr.append(r.thread); oldr.append(bool(old_author.get(r.a, False)))
df = pd.DataFrame({"obs": obs, "exp": exp, "thread": thr, "old": oldr}); g = df.groupby("thread")[["obs", "exp"]].sum(); cnt = df.groupby("thread").size()
def est(sel=None):
    d = df if sel is None else df[sel]; return d.obs.mean(), d.exp.mean()
bs = []; tl = list(g.index)
for _ in range(300):
    pick = rng.choice(len(tl), len(tl)); gg = g.iloc[pick]; bs.append((gg.obs.sum() - gg.exp.sum()) / cnt.iloc[pick].sum())
print(f"replies tested (both authors in half-A communities, thread in half B): {len(df):,} in {len(tl):,} threads")
o, e = est(); print(f"same-community share of replies: observed {o:.1%}; expected from the same threads' participants {e:.1%}; excess {100 * (o - e):+.1f} points [{100 * np.percentile(bs, 2.5):+.1f}, {100 * np.percentile(bs, 97.5):+.1f}]")
for lab_, sel in (("repliers who are old guard", df.old), ("repliers who are newcomers", ~df.old)):
    o, e = est(sel); print(f"  {lab_}: observed {o:.1%}, expected {e:.1%} (n {int(sel.sum()):,})")
json.dump({"authors_input": int(N), "links_full": int(full), "links_kept": int(len(bi)), "modularity_mean": round(float(np.mean(mods)), 3), "ami_mean": round(float(np.mean(amis)), 2), "communities": int(len(sizes)), "null_modularity": [round(float(x), 3) for x in nm]}, open(PRO / "cothread_stats.json", "w"))
