"""Do user niches emerge in 2024? (1) active people per month per niche (communities from the all-period backbone, commenter_topic_network.py); (2) the same method run separately on before-2024 and from-2024 comments and communities matched by topic profile;
(3) do niche members reply to each other more than chance. Same settings as Figure 7: >= 10 topic comments in the period, 50 topics, IDF cosine, disparity filter alpha 0.05, Louvain.
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/niche_emergence.py"""
from seedoil_common import is_bot, not_bot  # shared bot rule: AutoModerator + names ending in 'bot'
import gzip, glob, json
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
from networkx.algorithms.community import louvain_communities, modularity
P = Path("seedoils/data/processed"); CUT = pd.Timestamp("2024-01-01").timestamp(); K = 50; rng = np.random.default_rng(0)
raw = []
with gzip.open(glob.glob("seedoils/data/raw/*StopEatingSeedOils_comments.jsonl.gz")[0], "rt", encoding="utf-8") as f:
    for l in f:
        x = json.loads(l); raw.append((x["id"], x["author"], str(x.get("parent_id", "")), int(x["created_utc"])))
R = pd.DataFrame(raw, columns=["id", "a", "p", "t"]); who = dict(zip(R.id, R.a))
D = pd.read_csv(P / "seso_k50_doc_topics.csv.gz"); D = D[D.kind == "comment"]; D["a"] = D.id.map(who); D = D[D.a.notna() & (~D.a.isin(["[deleted]", "AutoModerator"]) & not_bot(D.a))]
tinfo = pd.read_csv(P / "seso_k50_topics_info.csv").set_index("topic"); W = lambda t: ", ".join(w.strip() for w in tinfo.loc[t, "top_words"].split(",")[:2])
# ---- all-period communities -> author map
nd = D.groupby("a").size(); U = np.array(sorted(nd[nd >= 10].index)); Nn = pd.read_csv(P / "commenter_topic_network_nodes.csv"); assert len(U) == len(Nn)
comm = dict(zip(U, Nn.community)); LAB = ['Condiments, snacks', 'Olive oil', 'Politics', 'Eggs, raw milk', 'Bread, butter', 'Organic, protein', 'Labels, ice cream', 'Sugar, carbs', 'Vaccines', 'LDL', 'Skin, sun', 'Infant formula', 'Coffee, plastics', 'Tallow, fries', 'MSG', 'Vitamins']
D["c"] = D.a.map(comm); D["m"] = pd.to_datetime(D.created_utc, unit="s").dt.to_period("M")
print("== 1. ACTIVE PEOPLE PER MONTH PER NICHE (communities from the all-period backbone; people with >= 10 comments overall)")
pre_m = pd.period_range("2022-01", "2023-12", freq="M"); post_m = pd.period_range("2024-01", "2026-10", freq="M")
act = D[D.c.notna()].groupby(["c", "m"]).a.nunique().unstack(fill_value=0)
rows = []
STATS = {}; MATCH = []; REPLY = {}
for c in act.index:
    a = act.loc[c].reindex(pre_m, fill_value=0).mean(); b = act.loc[c].reindex(post_m, fill_value=0).mean(); rows.append((c, a, b))
tot_a = sum(r[1] for r in rows); tot_b = sum(r[2] for r in rows)
for c, a, b in sorted(rows, key=lambda r: -(r[2] - r[1])):
    print(f"  {('C%d %s' % (c, LAB[int(c)])) if c >= 0 else 'No link (general core)':<30} active people per month {a:5.1f} -> {b:6.1f} (x{b / a if a else float('nan'):.1f})")
print(f"  total (sum of niches): {tot_a:.0f} -> {tot_b:.0f}")
SERIES = [{"c": int(c), "m": str(m), "p": int(v)} for c in act.index for m, v in act.loc[c].reindex(pd.period_range("2022-01", "2026-10", freq="M"), fill_value=0).items()]
GROWTH = [{"c": int(c), "label": (LAB[int(c)] if c >= 0 else "General core (no link)"), "before": round(float(a), 1), "after": round(float(b), 1)} for c, a, b in rows]
# ---- 2. period-specific clustering
def profile(Dp, users):
    ui = {u: i for i, u in enumerate(users)}; X = np.zeros((len(users), K)); np.add.at(X, (Dp.a.map(ui).values, Dp.topic.values), 1); df = (X > 0).sum(0); idf = np.log(len(users) / (1 + df)) + 1; Xw = X * idf; Xw /= np.linalg.norm(Xw, axis=1, keepdims=True); return X, Xw
def backbone(Xw, alpha=0.05):
    S = Xw @ Xw.T; np.fill_diagonal(S, 0); S[S < 1e-9] = 0; s = S.sum(1, keepdims=True); k = (S > 0).sum(1, keepdims=True); p = np.divide(S, s, out=np.zeros_like(S), where=s > 0); keep = ((1 - p) ** np.maximum(k - 1, 1) < alpha); keep = keep | keep.T; return S, np.triu(keep, 1)
def cluster(Dp, name):
    n_ = Dp.groupby("a").size(); users = np.array(sorted(n_[n_ >= 10].index)); Dp = Dp[Dp.a.isin(users)]; X, Xw = profile(Dp, users); S, Kp = backbone(Xw)
    G = nx.Graph(); G.add_nodes_from(range(len(users))); a, b = np.where(Kp); G.add_weighted_edges_from(zip(a.tolist(), b.tolist(), S[a, b].tolist()))
    H = G.subgraph(max(nx.connected_components(G), key=len)).copy(); best = None
    for sd in range(10):
        c = louvain_communities(H, weight="weight", seed=sd); m = modularity(H, c, weight="weight")
        if best is None or m > best[0]: best = (m, c)
    m, c = best; c = sorted(c, key=len, reverse=True); iso = sum(1 for v in G if G.degree(v) == 0)
    print(f"\n{name}: commenters {len(users):,} (comments {len(Dp):,}); links {int(Kp.sum()):,} of {len(users)*(len(users)-1)//2:,}; no link {iso} ({iso/len(users)*100:.0f}%); giant component {H.number_of_nodes()}; communities {len(c)} (>=50 people: {sum(len(x) >= 50 for x in c)}); modularity {m:.3f}")
    STATS[name] = {"commenters": int(len(users)), "comments": int(len(Dp)), "links": int(Kp.sum()), "no_link_pct": round(iso / len(users) * 100), "giant": int(H.number_of_nodes()), "communities": len(c), "comm50": int(sum(len(x) >= 50 for x in c)), "modularity": round(float(m), 3)}
    overall = X.sum(0) / X.sum(); prof = []
    for ci, comp in enumerate(c):
        idx = np.array(sorted(comp)); sh = X[idx].sum(0) / X[idx].sum(); prof.append((sh - overall, len(idx), sh, idx))
    return users, X, prof, overall, c
Dpre = D[D.created_utc < CUT]; Dpost = D[D.created_utc >= CUT]
u1, X1, pr1, ov1, c1 = cluster(Dpre, "BEFORE 2024"); u2, X2, pr2, ov2, c2 = cluster(Dpost, "FROM 2024")
print("\nFROM-2024 communities (>= 50 people) matched to before-2024 communities by topic profile (cosine of over-representation vectors; 1 = same niche)")
for ci, (v2, n2, sh2, idx2) in enumerate(pr2):
    if n2 < 50: continue
    top = np.argsort(-v2)[:3]; sims = [(np.dot(v2, v1) / (np.linalg.norm(v2) * np.linalg.norm(v1) + 1e-12), j) for j, (v1, n1, _, _) in enumerate(pr1)]; s, j = max(sims)
    t1 = np.argsort(-pr1[j][0])[:2]
    MATCH.append({"id": ci, "size": int(n2), "topics": [{"w": W(t), "s": round(float(sh2[t] * 100))} for t in top], "cos": round(float(s), 2), "pre_size": int(pr1[j][1])})
    print(f"  post C{ci:<2} {n2:>4} people | " + "; ".join(f"{W(t)} {sh2[t]*100:.0f}%" for t in top) + f" | best match before 2024: {pr1[j][1]} people, cosine {s:.2f} ({'; '.join(W(t) for t in t1)})")
print("\nBEFORE-2024 communities (>= 50 people) matched forward")
for j, (v1, n1, sh1, idx1) in enumerate(pr1):
    if n1 < 50: continue
    top = np.argsort(-v1)[:3]; sims = [(np.dot(v1, v2) / (np.linalg.norm(v2) * np.linalg.norm(v1) + 1e-12), k) for k, (v2, n2, _, _) in enumerate(pr2)]; s, k = max(sims)
    print(f"  pre C{j:<2} {n1:>4} people | " + "; ".join(f"{W(t)} {sh1[t]*100:.0f}%" for t in top) + f" | best match from 2024: {pr2[k][1]} people, cosine {s:.2f}")
# ---- 3. replies within niche (all-period communities)
print("\n== 3. DO NICHE MEMBERS REPLY TO EACH OTHER? share of replies (between two commenters in niches C0-C15, different people) inside the same niche")
R["pa"] = R.p.str.replace("t1_", "", regex=False).map(who); E = R[R.p.str.startswith("t1_") & R.pa.notna() & (R.pa != R.a)].copy(); E["ca"] = E.a.map(comm); E["cb"] = E.pa.map(comm); E = E[(E.ca >= 0) & (E.cb >= 0)]
nodes_c = pd.Series(comm); nodes_c = nodes_c[nodes_c >= 0]
for lab, Ep in (("before 2024", E[E.t < CUT]), ("from 2024", E[E.t >= CUT])):
    obs = (Ep.ca == Ep.cb).mean(); null = []
    for _ in range(200):
        perm = dict(zip(nodes_c.index, rng.permutation(nodes_c.values))); null.append((Ep.a.map(perm) == Ep.pa.map(perm)).mean())
    print(f"  {lab}: replies between niche members {len(Ep):,}; same niche {obs*100:.1f}% vs {np.mean(null)*100:.1f}% expected by chance (sd {np.std(null)*100:.2f}); ratio x{obs/np.mean(null):.2f}")
    REPLY[lab] = {"n": int(len(Ep)), "same": round(float(obs * 100), 1), "chance": round(float(np.mean(null) * 100), 1)}

(P / "artifact" / "niche_emergence.json").write_text(json.dumps({"series": SERIES, "growth": GROWTH, "match": MATCH, "stats": STATS, "reply": REPLY, "meta": [{"label": "niche_emergence.py", "value": Path(__file__).read_text()}]}))
print("exported niche_emergence.json")
