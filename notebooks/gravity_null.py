"""Geography-aware null model + region-controlled attribute test.

Run from final_project/:  ../.venv/bin/python notebooks/gravity_null.py

1. Gravity null. Pair (i->j) gets probability proportional to out_i * in_j * dist_ij^-beta * exp(gamma * both_in_EU).
   beta, gamma are FITTED per layer by maximum likelihood (multinomial) to the observed tonnage, so the null reproduces
   distance decay and the EU effect. We then draw random networks, apply the same backbone + Louvain, and ask whether
   observed modularity still exceeds the null. Distances: great-circle between capitals (hard-coded, a proxy).
   EU = current EU27 members among the 26 (GB left in 2020, treated as non-EU; NO/IS are EEA, not EU: noted limitation).
2. Region-controlled attribute test. UN-geoscheme-style regions (Northern/Western/Southern/Eastern; TR put in Southern).
   Does the trade-community partition explain attribute variance beyond region? Test: permute community labels only
   WITHIN regions and recompute eta^2.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
from scipy.optimize import minimize
sys.path.insert(0, str(Path(__file__).parent))
from build_trade_networks import load, edge_table, GROUPS
from null_and_attributes import graph_from, louvain_Q, attributes, eta2

PROC = Path("data/processed")
RNG = np.random.default_rng(7)
N_NULL, UNITS = 200, 100_000

CAP = {"AT": (48.21, 16.37), "BA": (43.86, 18.41), "BE": (50.85, 4.35), "BG": (42.70, 23.32), "CZ": (50.08, 14.44),
       "DK": (55.68, 12.57), "EE": (59.44, 24.75), "ES": (40.42, -3.70), "FI": (60.17, 24.94), "FR": (48.86, 2.35),
       "GB": (51.51, -0.13), "GR": (37.98, 23.73), "HR": (45.81, 15.98), "HU": (47.50, 19.04), "IS": (64.15, -21.94),
       "IT": (41.90, 12.50), "LV": (56.95, 24.11), "NL": (52.37, 4.90), "NO": (59.91, 10.75), "PL": (52.23, 21.01),
       "PT": (38.72, -9.14), "RS": (44.79, 20.45), "SE": (59.33, 18.07), "SI": (46.06, 14.51), "TR": (39.93, 32.86),
       "UA": (50.45, 30.52)}
EU = {"AT", "BE", "BG", "CZ", "DK", "EE", "ES", "FI", "FR", "GR", "HR", "HU", "IT", "LV", "NL", "PL", "PT", "SE", "SI"}
REGION = {**{c: "North" for c in "DK EE FI IS LV NO SE GB".split()},
          **{c: "West" for c in "AT BE FR NL".split()},
          **{c: "South" for c in "BA ES GR HR IT PT RS SI TR".split()},
          **{c: "East" for c in "BG CZ HU PL UA".split()}}
NODES = sorted(CAP)


def haversine(a, b):
    la1, lo1, la2, lo2 = map(np.radians, (*a, *b))
    h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(h))


D = np.array([[haversine(CAP[i], CAP[j]) if i != j else 1.0 for j in NODES] for i in NODES])
SAME_EU = np.array([[1.0 if (i in EU and j in EU) else 0.0 for j in NODES] for i in NODES])
OFF = ~np.eye(len(NODES), dtype=bool)


def weights_matrix(G):
    W = np.zeros((len(NODES), len(NODES)))
    ix = {n: k for k, n in enumerate(NODES)}
    for u, v, w in G.edges(data="weight"):
        W[ix[u], ix[v]] = w
    return W


def prob(W, beta, gamma):
    so, si = W.sum(1), W.sum(0)
    P = np.outer(so, si) * D ** (-beta) * np.exp(gamma * SAME_EU) * OFF
    return P / P.sum()


def fit(W):
    def nll(p):
        P = prob(W, *p)
        return -(W[OFF] * np.log(P[OFF] + 1e-300)).sum() / W.sum()
    r = minimize(nll, x0=[1.0, 0.0], method="Nelder-Mead")
    return r.x, r.fun


def draw(W, beta, gamma):
    P = prob(W, beta, gamma)
    C = RNG.multinomial(UNITS, P.ravel()).reshape(P.shape)
    H = nx.DiGraph(); H.add_nodes_from(NODES)
    for i, j in zip(*np.nonzero(C)):
        H.add_edge(NODES[i], NODES[j], weight=float(C[i, j]))
    return H


if __name__ == "__main__":
    t = load()
    rows, comm = [], {}
    print("== GRAVITY NULL (fitted distance decay beta and EU effect gamma; 200 draws/layer)")
    for g in [None] + list(GROUPS):
        name = g or "all_food"
        G = graph_from(edge_table(t, g)); W = weights_matrix(G)
        (beta, gamma), _ = fit(W)
        q_obs, comms, _ = louvain_Q(G, 42)
        nulls = np.array([louvain_Q(draw(W, beta, gamma), s)[0] for s in range(N_NULL)])
        p = (1 + (nulls >= q_obs).sum()) / (1 + N_NULL)
        rows.append(dict(layer=name, beta=beta, gamma=gamma, Q_obs=q_obs, Q_null_mean=nulls.mean(),
                         Q_null_sd=nulls.std(), p=p))
        comm[name] = {n: i for i, c in enumerate(comms) for n in c}
        print(f"{name:16s} beta={beta:4.2f} gamma={gamma:5.2f} | Q_obs={q_obs:.2f}  null={nulls.mean():.2f}±{nulls.std():.2f}"
              f"  p={p:.3f}")
    pd.DataFrame(rows).to_csv(PROC / "networks/gravity_null_modularity.csv", index=False)

    A = attributes().loc[NODES]
    reg = np.array([REGION[n] for n in NODES])
    print("\n== eta^2 of attribute: REGION alone vs TRADE COMMUNITY; p = community labels permuted within regions")
    out = []
    for name, lab in comm.items():
        L = np.array([lab[n] for n in NODES])
        for col in A.columns:
            x = A[col].values
            obs = eta2(x, L)
            perm = []
            for _ in range(5000):
                Lp = L.copy()
                for r in np.unique(reg):
                    idx = np.where(reg == r)[0]; Lp[idx] = RNG.permutation(L[idx])
                perm.append(eta2(x, Lp))
            out.append(dict(layer=name, attribute=col, eta2_comm=obs, eta2_region=eta2(x, reg),
                            p_within_region=(1 + (np.array(perm) >= obs).sum()) / 5001))
    R = pd.DataFrame(out); R.to_csv(PROC / "networks/community_attribute_tests_region_controlled.csv", index=False)
    print("eta2 by region alone:", R.drop_duplicates("attribute").set_index("attribute").eta2_region.round(2).to_dict())
    print("\ncommunity eta^2 (p within region):")
    piv = R.assign(s=R.eta2_comm.round(2).astype(str) + np.where(R.p_within_region < 0.05, "*", "")).pivot(
        index="layer", columns="attribute", values="s")
    print(piv.to_string())
    print(f"\n{(R.p_within_region < 0.05).sum()} of {len(R)} tests p<0.05 within regions (expect ~{0.05*len(R):.1f} by chance)")
    print(R[R.p_within_region < 0.05].round(3).to_string(index=False))
