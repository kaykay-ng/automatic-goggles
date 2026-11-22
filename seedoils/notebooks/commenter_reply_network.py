"""Reply network among the 2,618 commenters of the ~130-topic backbone (communities from commenter_topic_network_130.py). Who replies to whom, by community?
Edge: a comment by person A that replies to a comment by person B (parent_id 't1_...'), both in the network, A != B. Counted from ALL their comments (any length), not only the topic-model ones.
Test: replies happen inside threads, and people in the same thread are often in the same community, so a naive 'they reply within their own community' is partly just 'they share a thread'. Expected counts therefore
condition on the thread: for each reply by A in thread T, the partner is imagined to be drawn at random from the OTHER network members who commented in T (weights = number of their comments there).
Output: observed vs expected share of replies that stay inside the community, and a community x community lift matrix (observed / expected replies). Aggregates only.
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python seedoils/notebooks/commenter_reply_network.py"""
import glob
import gzip
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

P = Path("seedoils/data/processed"); K = 12
rows = []
with gzip.open(glob.glob("seedoils/data/raw/*StopEatingSeedOils_comments.jsonl.gz")[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); rows.append((x["id"], x["author"], x["link_id"], x["parent_id"], int(x["created_utc"])))
R = pd.DataFrame(rows, columns=["id", "a", "thread", "parent", "t"])
D = pd.read_csv(P / "seso_doc_topics.csv.gz", usecols=["id", "kind"]); D = D[D.kind == "comment"]; author = dict(zip(R.id, R.a))
D["a"] = D.id.map(author); D = D[D.a.notna() & ~D.a.isin(["[deleted]", "AutoModerator"])]
nd = D.groupby("a").size(); U = np.array(sorted(nd[nd >= 10].index)); N = pd.read_csv(P / "commenter_topic_network_130_nodes.csv"); assert len(U) == len(N)
comm = dict(zip(U, N.community)); old = dict(zip(U, N.old))
R = R[R.a.isin(comm)]; print(f"commenters {len(U):,}; their comments {len(R):,}")
# thread composition: comments per (thread, community) and per (thread, person)
per_tp = R.groupby(["thread", "a"]).size()
tc = defaultdict(lambda: np.zeros(K)); tp = defaultdict(dict)
for (t, a), n in per_tp.items(): tc[t][comm[a]] += n; tp[t][a] = n
pid = R.set_index("id")
rep = R[R.parent.str.startswith("t1_")].copy(); rep["pid"] = rep.parent.str[3:]
allc = pd.DataFrame(rows, columns=["id", "a", "thread", "parent", "t"]).set_index("id")
rep["b"] = rep.pid.map(allc.a); rep = rep[rep.b.isin(comm) & (rep.a != rep.b)]
print(f"replies between network members: {len(rep):,} (from {rep.a.nunique():,} repliers to {rep.b.nunique():,} people)")
O = np.zeros((K, K)); E = np.zeros((K, K))
for r in rep.itertuples():
    ca, cb = comm[r.a], comm[r.b]; O[ca, cb] += 1
    v = tc[r.thread].copy(); v[ca] -= tp[r.thread].get(r.a, 0)  # other members' comments in this thread, by community, replier removed
    if v.sum() > 0: E[ca] += v / v.sum()
ok = E.sum(1) > 0
obs_in = np.trace(O) / O.sum(); exp_in = np.trace(E) / E.sum()
print(f"\nshare of replies that stay inside the replier's community: observed {obs_in:.3f}, expected from who is in the same thread {exp_in:.3f}  (ratio {obs_in / exp_in:.2f})")
names = ['Shopping, food', 'Politics, vaccines', 'Omega-6 science', 'Evidence, the sub', 'Keto, LDL', 'Olive oil', 'Vegan, soy', 'Weight, fasting', 'Mayo, sugar', 'Pork, canola', 'Sun, skin', 'Formula, kids']
print("\nper community: replies sent | share kept inside: observed vs expected | ratio")
for c in range(K):
    print(f"  {names[c]:<18}{int(O[c].sum()):>6} | {O[c, c] / O[c].sum():.3f} vs {E[c, c] / E[c].sum():.3f} | x{(O[c, c] / O[c].sum()) / (E[c, c] / E[c].sum()):.2f}")
L = np.divide(O, E, out=np.full_like(O, np.nan), where=E > 0)
print("\nlift (observed / expected replies) for pairs with >= 150 observed replies, off-diagonal, highest and lowest:")
pairs = [(L[i, j], i, j, int(O[i, j])) for i in range(K) for j in range(K) if i != j and O[i, j] >= 150]
for l, i, j, n in sorted(pairs, reverse=True)[:8]: print(f"  {names[i]} -> {names[j]}: x{l:.2f} ({n} replies)")
print("  ...")
for l, i, j, n in sorted(pairs)[:6]: print(f"  {names[i]} -> {names[j]}: x{l:.2f} ({n} replies)")
# politics community row
print("\nwhere the Politics, vaccines community's replies go (observed share vs expected share):")
for j in np.argsort(-O[1])[:6]: print(f"  -> {names[j]:<18} {O[1, j] / O[1].sum():.3f} vs {E[1, j] / E[1].sum():.3f}")
# newcomers replying to long-time
cohort = {(True, True): 0, (True, False): 0, (False, True): 0, (False, False): 0}
for r in rep.itertuples(): cohort[(bool(old[r.a]), bool(old[r.b]))] += 1
tot = sum(cohort.values()); print(f"\nreplies by cohort (replier -> replied-to), % of all: long->long {cohort[(True, True)] / tot * 100:.0f}, long->new {cohort[(True, False)] / tot * 100:.0f}, new->long {cohort[(False, True)] / tot * 100:.0f}, new->new {cohort[(False, False)] / tot * 100:.0f}")
pd.DataFrame(O.astype(int)).to_csv(P / "reply_matrix_130.csv", index=False)
