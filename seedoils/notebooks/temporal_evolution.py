"""Temporal evolution of the commenter network, r/StopEatingSeedOils vs r/ScientificNutrition (rerun data, seedoils/data/raw_haoyu).
Design follows Task 4 of Theo-Daniel/Web-Science-Reddit-Network-Analysis (weekly activity with a 4-week moving average; largest connected component per time slice), with two fixes:
 - the notebook's 'new post authors' counts distinct authors of the posts that were commented on, not new people; here NEW = a commenter's first comment ever in that subreddit (within the data, which starts Oct 2018: the first months are all 'new').
 - the notebook's 'posts per user' divides the cumulative total by one week's users; here items per active commenter are computed within the same period.
Network per time slice: directed, commenter -> author of the post or comment being replied to (direct parent), a reply link counts once however often it repeats; bots (seedoil_common.is_bot), '[deleted]' authors and self-replies removed (the notebook removes deleted authors and self-replies; bots are removed as in the rerun).
Panels: A weekly active commenters (4-week moving average); B share of active commenters that are new, per month (months with >= 30 active commenters); C largest weakly connected component as a share of nodes, per quarter (slices with >= 50 nodes; the incomplete last quarter is left out).
Writes paper/figures/temporal_evolution.pdf, seedoils/figures/temporal_evolution.png, seedoils/data/processed/temporal_evolution_summary.txt (aggregates only).
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/temporal_evolution.py"""
import gzip
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

from seedoil_common import is_bot

SUBS = {"StopEatingSeedOils": "#b5482a", "ScientificNutrition": "#2a6f97"}
EVENTS = ["2024-01-01", "2024-08-01"]
MIN_NODES = 50
lines, series = [], {}


def load(sub):
    P = {}
    with gzip.open(f"seedoils/data/raw_haoyu/{sub}_posts.jsonl.gz", "rt", encoding="utf-8") as f:
        for l in f:
            x = json.loads(l); P["t3_" + x["id"]] = x.get("author") or ""
    rows = []
    with gzip.open(f"seedoils/data/raw_haoyu/{sub}_comments.jsonl.gz", "rt", encoding="utf-8") as f:
        for l in f:
            x = json.loads(l); rows.append((x["id"], x.get("author") or "", x["parent_id"], int(x["created_utc"])))
    C = pd.DataFrame(rows, columns=["id", "a", "parent", "t"])
    cauth = dict(zip("t1_" + C.id, C.a))
    C["pa"] = C.parent.map(lambda p: cauth.get(p) if p.startswith("t1_") else P.get(p))
    C["dt"] = pd.to_datetime(C.t, unit="s")
    return C


def ok(a):
    return isinstance(a, str) and a not in ("", "[deleted]") and not is_bot(a)


for sub in SUBS:
    C = load(sub)
    C = C[C.a.map(ok)].copy()          # commenters: real, non-bot accounts
    first = C.groupby("a").dt.min().rename("first")
    C = C.join(first, on="a")
    C["month"] = C.dt.dt.to_period("M"); C["new"] = C["first"].dt.to_period("M") == C.month
    wk = C.set_index("dt").groupby(pd.Grouper(freq="W")).a.nunique()
    wk_ma = wk.rolling(4, min_periods=1).mean()
    m = C.groupby("month").agg(active=("a", "nunique")); m["new"] = C[C.new].groupby("month").a.nunique(); m = m.fillna(0)
    m["new_share"] = m.new / m.active; m.index = m.index.to_timestamp()
    E = C[C.pa.map(ok) & (C.a != C.pa)].copy(); E["q"] = E.dt.dt.to_period("Q")
    q = []
    for per, g in E.groupby("q"):
        G = nx.from_pandas_edgelist(g.drop_duplicates(["a", "pa"]), "a", "pa", create_using=nx.DiGraph())
        if G.number_of_nodes() >= MIN_NODES and per.end_time <= pd.Timestamp("2026-11-22"):  # last quarter is incomplete (data end 22 Nov 2026)
            q.append((per.start_time, len(max(nx.weakly_connected_components(G), key=len)) / G.number_of_nodes(), G.number_of_nodes(), G.number_of_edges()))
    Q = pd.DataFrame(q, columns=["start", "lcc", "nodes", "edges"])
    series[sub] = (wk, wk_ma, m, Q)
    lines.append(f"r/{sub}: {len(C):,} comments by {C.a.nunique():,} commenters (bots, [deleted] removed); {len(E):,} reply links with a known non-self author")
    for y in (2022, 2023, 2024, 2025):
        s = m[(m.index >= f"{y}-01-01") & (m.index < f"{y + 1}-01-01")]
        lines.append(f"  {y}: median monthly active commenters {s.active.median():.0f}, median share new {s.new_share.median():.0%}")
    lines.append("  quarterly LCC share (nodes): " + "; ".join(f"{r.start.year}Q{(r.start.month - 1) // 3 + 1} {r.lcc:.0%} ({r.nodes})" for r in Q.itertuples() if r.start.year >= 2022))

plt.rcParams.update({"font.size": 7, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})
fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.4), constrained_layout=True)
for sub, c in SUBS.items():
    wk, ma, m, Q = series[sub]
    ax[0].plot(ma.index, ma.values, color=c, lw=1.3, label=f"r/{sub}")
    mm = m[m.active >= 30]; ax[1].plot(mm.index, mm.new_share.values, color=c, lw=1.3)  # months with < 30 active commenters are too noisy
    ax[2].plot(Q.start, Q.lcc.values, color=c, lw=1.3, marker="o", ms=2.5)
ax[0].set_ylabel("Active commenters per week\n(4-week moving average)"); ax[1].set_ylabel("Share of active commenters\nwho are new (per month)"); ax[2].set_ylabel("Largest connected component\n(share of nodes, per quarter)")
ax[1].yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0)); ax[2].yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
for a, lab in zip(ax, "ABC"):
    a.set_xlim(pd.Timestamp("2019-01-01"), pd.Timestamp("2026-12-01"))
    a.xaxis.set_major_locator(mdates.YearLocator(2)); a.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    for d in EVENTS: a.axvline(pd.Timestamp(d), color="0.45", ls=":", lw=0.8)
    a.text(-0.02, 1.06, lab, transform=a.transAxes, fontweight="bold", fontsize=8)
ax[0].legend(frameon=False, loc="upper left", fontsize=6.5)
fig.savefig("paper/figures/temporal_evolution.pdf"); fig.savefig("seedoils/figures/temporal_evolution.png", dpi=200)
open("seedoils/data/processed/temporal_evolution_summary.txt", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
