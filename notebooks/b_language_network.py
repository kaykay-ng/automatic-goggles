"""Angle B: language-similarity network vs trade network.

Run from final_project/ with the NLP environment:
  ./.venv-nlp/bin/python notebooks/b_language_network.py validate     # reliability, neighbours, source-language check (BEFORE tests)
  ./.venv-nlp/bin/python notebooks/b_language_network.py test         # pre-declared MRQAP + partition comparison
Design pre-declared in PLAN.md ('ANGLE B chosen').
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
import networkx as nx
from gravity_null import NODES, D as DIST, SAME_EU, REGION
from build_trade_networks import load, edge_table

PROC = Path("data/processed")
RNG = np.random.default_rng(314)
FAMILY = {**{c: "Germanic" for c in "AT DK GB IS NL NO SE".split()}, **{c: "Romance" for c in "ES FR IT PT".split()},
          **{c: "Slavic" for c in "BA BG CZ HR PL RS SI UA".split()}, **{c: "Uralic" for c in "EE FI HU".split()},
          "LV": "Baltic", "GR": "Greek", "TR": "Turkic", "BE": "Mixed"}
IU = np.triu_indices(len(NODES), 1)


def country_vectors(V, countries, subset=None):
    sel = np.ones(len(countries), bool) if subset is None else subset
    C = np.vstack([V[(countries == c) & sel].mean(axis=0) for c in NODES])
    C = C - C.mean(axis=0)                       # remove the shared 'parliament' component
    return C / np.linalg.norm(C, axis=1, keepdims=True)


def sim_matrix(C):
    return C @ C.T


def mantel(a, b):
    return np.corrcoef(a[IU], b[IU])[0, 1]


def load_data():
    pool = pd.read_csv(PROC / "b_pool.csv.gz", usecols=["country", "speech_id", "date", "text"])
    V = np.load(PROC / "b_speech_vectors.npy")
    return pool, V, pool.country.values


def validate():
    pool, V, cc = load_data()
    S = sim_matrix(country_vectors(V, cc))
    print("== (1) split-half reliability of the 26x26 similarity matrix (100 random splits of each country's speeches)")
    rs = []
    for _ in range(100):
        half = RNG.random(len(cc)) < 0.5
        rs.append(mantel(sim_matrix(country_vectors(V, cc, half)), sim_matrix(country_vectors(V, cc, ~half))))
    print(f"   Pearson r between halves: mean {np.mean(rs):.2f}, range {min(rs):.2f}-{max(rs):.2f}  (1 = perfectly repeatable)")
    print("\n== (2) nearest language neighbours (cosine), pre-chosen countries GR, NO, PL, plus GB and BA (outlier checks)")
    for c in ["GR", "NO", "PL", "GB", "BA"]:
        i = NODES.index(c); order = np.argsort(-S[i]); order = [j for j in order if j != i][:5]
        print(f"   {c}: " + ", ".join(f"{NODES[j]} {S[i, j]:.2f}" for j in order), f"| mean sim to all others {np.delete(S[i], i).mean():.2f}")
    print("\n== (3) is similarity organised by SOURCE-LANGUAGE FAMILY (translation artefact) rather than content?")
    fam = np.array([FAMILY[n] for n in NODES]); reg = np.array([REGION[n] for n in NODES])
    same_f = (fam[:, None] == fam[None, :]) & (fam[:, None] != "Mixed")
    same_r = reg[:, None] == reg[None, :]
    for nm, M in [("same family", same_f), ("same region", same_r)]:
        w, b = S[IU][M[IU]].mean(), S[IU][~M[IU]].mean()
        perm = []
        for _ in range(5000):
            p = RNG.permutation(len(NODES)); Mp = M[p][:, p]
            perm.append(S[IU][Mp[IU]].mean() - S[IU][~Mp[IU]].mean())
        print(f"   {nm:12s}: mean sim within {w:+.3f} vs between {b:+.3f}, gap {w-b:+.3f}, permutation p={(1+sum(np.array(perm)>=(w-b)))/5001:.4f}")
    print("   per-family mean similarity within family:", {f: round(float(S[np.ix_(fam == f, fam == f)][np.triu_indices((fam == f).sum(), 1)].mean()), 2)
                                                         for f in np.unique(fam) if (fam == f).sum() > 1})
    print("\n== (4) bootstrap over speeches: stability of the similarity of selected pairs")
    pairs = [("SE", "NO"), ("DK", "NL"), ("GR", "IT"), ("PL", "UA"), ("GB", "FR")]
    boots = {p: [] for p in pairs}
    for _ in range(200):
        idx = RNG.integers(0, len(cc), len(cc))
        Sb = sim_matrix(country_vectors(V[idx], cc[idx]))
        for a, b in pairs:
            boots[(a, b)].append(Sb[NODES.index(a), NODES.index(b)])
    for (a, b), v in boots.items():
        print(f"   {a}-{b}: {S[NODES.index(a), NODES.index(b)]:+.2f}  95% CI [{np.percentile(v, 2.5):+.2f}, {np.percentile(v, 97.5):+.2f}]")
    np.save(PROC / "b_language_similarity.npy", S)
    pd.DataFrame(S, index=NODES, columns=NODES).to_csv(PROC / "b_language_similarity.csv")


def dyad_matrices():
    t = load()
    e = edge_table(t, None)
    W = pd.DataFrame(0.0, index=NODES, columns=NODES)
    for r in e.itertuples():
        W.loc[r.exporter, r.importer] = r.w
    T = (W + W.T).values
    return np.log1p(T)


def design(logT):
    reg = np.array([REGION[n] for n in NODES]); fam = np.array([FAMILY[n] for n in NODES])
    cols = {"log_trade": logT, "log_distance": np.log(DIST), "both_EU": SAME_EU,
            "same_region": (reg[:, None] == reg[None, :]).astype(float),
            "same_lang_family": ((fam[:, None] == fam[None, :]) & (fam[:, None] != "Mixed")).astype(float)}
    X = np.column_stack([v[IU] for v in cols.values()])
    return list(cols), X


def dsp_mrqap(S, names, X, n_perm=5000):
    """OLS of dyadic similarity on predictors; p-values by Dekker's double semi-partialling (permute node labels of Y)."""
    y = S[IU]
    Xs = (X - X.mean(0)) / X.std(0); ys = (y - y.mean()) / y.std()
    A = np.column_stack([np.ones(len(ys)), Xs])
    beta = np.linalg.lstsq(A, ys, rcond=None)[0][1:]
    r2 = 1 - ((ys - A @ np.r_[np.mean(ys), beta] * 0 - (A @ np.linalg.lstsq(A, ys, rcond=None)[0])) ** 2).sum() / (ys ** 2).sum()
    out = []
    perms = [RNG.permutation(len(NODES)) for _ in range(n_perm)]
    Ys = [((S[p][:, p])[IU] - y.mean()) / y.std() for p in perms]
    for k, nm in enumerate(names):
        others = np.column_stack([np.ones(len(ys))] + [Xs[:, j] for j in range(Xs.shape[1]) if j != k])
        xr = Xs[:, k] - others @ np.linalg.lstsq(others, Xs[:, k], rcond=None)[0]
        b_perm = np.array([(xr @ yp) / (xr @ xr) for yp in Ys])
        b_obs = (xr @ ys) / (xr @ xr)
        out.append((nm, beta[k], b_obs, (1 + (np.abs(b_perm) >= abs(b_obs)).sum()) / (n_perm + 1)))
    return out, r2


def test():
    S = np.load(PROC / "b_language_similarity.npy")
    logT = dyad_matrices()
    names, X = design(logT)
    out, r2 = dsp_mrqap(S, names, X)
    print("== PRIMARY (pre-declared): language similarity ~ log trade + controls; standardised coefficients, DSP-MRQAP p (5,000 permutations)")
    print(f"   {len(IU[0])} dyads, R^2 = {r2:.3f}")
    for nm, b, bo, p in out:
        print(f"   {nm:18s} beta={b:+.3f}  p={p:.4f}" + ("   <-- primary, predicted POSITIVE" if nm == "log_trade" else ""))
    print("   raw Spearman of language similarity with log trade (no controls):",
          round(float(pd.Series(S[IU]).corr(pd.Series(logT[IU]), method='spearman')), 3))

    print("\n== SECONDARY (exploratory, Holm over 9 layers): same model, trade measured per commodity layer")
    t = load(); rows = []
    for g in ["cereals", "fruit_veg", "pulses_spices", "oilseeds_oils", "sugar_sweets", "meat", "dairy_eggs", "beverages", "feed_byproducts"]:
        e = edge_table(t, g); W = pd.DataFrame(0.0, index=NODES, columns=NODES)
        for r in e.itertuples():
            W.loc[r.exporter, r.importer] = r.w
        lt = np.log1p((W + W.T).values)
        nm, X2 = design(lt)
        o, _ = dsp_mrqap(S, nm, X2, n_perm=2000)
        rows.append((g, o[0][1], o[0][3]))
    ps = np.array([r[2] for r in rows]); order = np.argsort(ps); adj = np.empty(len(ps)); run = 0
    for rank, i in enumerate(order):
        run = max(run, (len(ps) - rank) * ps[i]); adj[i] = min(run, 1)
    for (g, b, p), a in zip(rows, adj):
        print(f"   {g:16s} beta={b:+.3f}  p={p:.4f}  Holm p={a:.3f}")

    print("\n== PARTITIONS of the 26 countries: language clusters vs trade communities vs region vs source-language family")
    Dm = squareform(1 - S, checks=False); L = linkage(Dm, "ward")
    best = None
    for k in range(2, 7):
        lab = fcluster(L, k, "maxclust")
        sil = silhouette_from_sim(S, lab)
        print(f"   k={k}: silhouette {sil:.2f}")
        if best is None or sil > best[0]:
            best = (sil, k, lab)
    sil, k, lab = best
    print(f"   chosen k={k} (silhouette {sil:.2f}):", {c: [n for n, l in zip(NODES, lab) if l == c] for c in sorted(set(lab))})
    G = nx.read_graphml(PROC / "networks/trade_all_food.graphml")
    tc = np.array([int(G.nodes[n]["community"]) for n in NODES])
    parts = {"trade communities (all food)": tc, "region": np.array([REGION[n] for n in NODES]),
             "source-language family": np.array([FAMILY[n] for n in NODES]), "EU member": np.array([n in EU_SET for n in NODES])}
    for nm, p in parts.items():
        a = ari(lab, p); perm = [ari(lab, RNG.permutation(p)) for _ in range(5000)]
        print(f"   language clusters vs {nm:30s} ARI={a:+.2f} permutation p={(1+sum(np.array(perm)>=a))/5001:.4f}")
    reg = parts["region"]
    for nm, p in [("trade communities", tc)]:
        M = p[:, None] == p[None, :]
        obs = S[IU][M[IU]].mean() - S[IU][~M[IU]].mean()
        perm = []
        for _ in range(5000):
            q = p.copy()
            for r in np.unique(reg):
                i = np.where(reg == r)[0]; q[i] = RNG.permutation(q[i])
            Mq = q[:, None] == q[None, :]
            perm.append(S[IU][Mq[IU]].mean() - S[IU][~Mq[IU]].mean())
        print(f"   within-minus-between language similarity for {nm}: {obs:+.3f}; permuting labels WITHIN regions p={(1+sum(np.array(perm)>=obs))/5001:.4f}")


EU_SET = {"AT", "BE", "BG", "CZ", "DK", "EE", "ES", "FI", "FR", "GR", "HR", "HU", "IT", "LV", "NL", "PL", "PT", "SE", "SI"}


def silhouette_from_sim(S, lab):
    Dm = 1 - S; np.fill_diagonal(Dm, 0); s = []
    for i in range(len(lab)):
        same = (lab == lab[i]) & (np.arange(len(lab)) != i)
        if same.sum() == 0:
            s.append(0); continue
        a = Dm[i, same].mean(); b = min(Dm[i, lab == c].mean() for c in np.unique(lab) if c != lab[i])
        s.append((b - a) / max(a, b))
    return float(np.mean(s))


def ari(x, y):
    ct = pd.crosstab(pd.Series(x), pd.Series(y)).values
    c2 = lambda a: a * (a - 1) / 2
    sij, sa, sb = c2(ct).sum(), c2(ct.sum(1)).sum(), c2(ct.sum(0)).sum()
    exp = sa * sb / c2(ct.sum())
    return (sij - exp) / ((sa + sb) / 2 - exp)


if __name__ == "__main__":
    {"validate": validate, "test": test}[sys.argv[1]]()
