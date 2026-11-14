"""Paper figures at PNAS widths (single column 8.7 cm = 3.42 in, double 17.8 cm = 7.0 in), read from saved CSVs only (no re-analysis).
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python ndc/notebooks/paper_figures.py
Writes ndc/figures/paper/fig1..fig4 as PDF (for LaTeX) and PNG (for slides).
Colours: fixed-order categorical palette (blue, orange, aqua, yellow, magenta, green, violet, red); text in ink colours, not series colours.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

PROC = Path("ndc/data/processed"); OUT = Path("ndc/figures/paper"); OUT.mkdir(parents=True, exist_ok=True)
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
plt.rcParams.update({"font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6.5,
                     "font.family": "sans-serif", "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlelocation": "left",
                     "pdf.fonttype": 42, "savefig.dpi": 300})


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight"); fig.savefig(OUT / f"{name}.png", bbox_inches="tight", dpi=300); plt.close(fig)
    print("saved", OUT / name)


def grid(ax, axis="x"):
    ax.grid(axis=axis, color=GRID, lw=0.5); ax.set_axisbelow(True)


# ---------------- Fig 1: language network, coloured by community and by region ----------------
sys.path.insert(0, str(Path(__file__).parent))
import ndc_common as D
G = nx.Graph(); G.add_nodes_from(range(D.n))
for i in range(D.n):
    for j in [j for j in np.argsort(-D.L[i]) if j != i][:5]: G.add_edge(i, j, weight=max(float(D.L[i, j]), 0.01))
LC = pd.read_csv(PROC / "ndc_language_communities.csv").set_index("iso").loc[D.nodes]
pos = nx.spring_layout(G, weight="weight", seed=4, k=0.5, iterations=300)
REG_SHORT = {"Europe & Central Asia": "Europe & C. Asia", "Sub-Saharan Africa": "Sub-Saharan Africa", "Latin America & Caribbean": "Latin Am. & Caribbean",
             "East Asia & Pacific": "East Asia & Pacific", "Middle East, North Africa, Afghanistan & Pakistan": "Mid. East, N. Africa, Afg. & Pak.",
             "South Asia": "South Asia", "North America": "North America"}
reg = [REG_SHORT.get(r.strip(), r.strip()) for r in LC.region]
regs = sorted(set(reg), key=lambda r: -reg.count(r)); rcol = {r: CAT[k] for k, r in enumerate(regs)}
comms = sorted(set(LC.language_community))
ccol, used = {}, set()
for c in sorted(comms, key=lambda c: -(LC.language_community == c).sum()):
    maj = pd.Series([r for r, l in zip(reg, LC.language_community) if l == c]).value_counts().index[0]
    col = rcol[maj] if rcol[maj] not in used else ([x for x in CAT if x not in used and x not in rcol.values()] + [x for x in CAT if x not in used])[0]
    ccol[c] = col; used.add(col)
fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.3))
deg = dict(G.degree()); big = sorted(range(D.n), key=lambda i: -deg[i])[:22]
for ax, cols, title, handles in [
        (axs[0], [ccol[c] for c in LC.language_community], "A  Language communities (Louvain)",
         [Line2D([], [], marker="o", ls="", color=ccol[c], ms=4, label=f"community {c + 1} (n={int((LC.language_community == c).sum())})") for c in comms]),
        (axs[1], [rcol[r] for r in reg], "B  World Bank region",
         [Line2D([], [], marker="o", ls="", color=rcol[r], ms=4, label=f"{r} (n={reg.count(r)})") for r in regs])]:
    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.15, width=0.4, edge_color=MUTED)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=cols, node_size=[8 + 2.5 * deg[i] for i in range(D.n)], edgecolors="white", linewidths=0.4)
    nx.draw_networkx_labels(G, pos, labels={i: D.nodes[i] for i in big}, ax=ax, font_size=4.5, font_color=INK)
    ax.set_title(title); ax.axis("off")
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=2, frameon=False, fontsize=5.5, handletextpad=0.2, columnspacing=0.8)
fig.text(0.5, -0.17, "Each of 154 countries (EU as one) linked to its 5 most similar first NDCs. Agreement of communities with region: ARI = 0.40 (p = 0.0002);"
         " with emission-profile clusters: ARI = 0.04. Community colours follow each community's main region.", ha="center", fontsize=6, color=INK2)
save(fig, "fig1_language_network")

# ---------------- Fig 2: say vs do (2015 NDC progress, 2020 pledge outcome) ----------------
P = pd.read_csv(PROC / "ndc_pledge_progress.csv"); P = P[P.E_base >= 1].copy()
P["change23"] = 100 * (P.E_2023 / P.E_base - 1); P["target"] = -P.reduction
P = P.sort_values("change23"); XMAX = 45
Q = pd.read_csv(PROC / "ndc_pledge2020_outcomes.csv").sort_values("change_2020")
fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.6), gridspec_kw={"width_ratios": [1.15, 1]})
for ax, df, actual, target, ok, title, okl, nol in [
        (axs[0], P, "change23", "target", "on_track", "A  First NDC (2015): emissions in 2023 vs pledge", "on track for 2030 target", "not on track"),
        (axs[1], Q, "change_2020", None, "met_2020", "B  2020 pledges (Copenhagen/Cancún): outcome", "met in 2020", "missed")]:
    y = np.arange(len(df)); tg = df[target] if target else -df.pledge_pct
    good = df[ok].astype(bool).values
    for k in range(len(df)):
        ax.plot([tg.iloc[k], df[actual].iloc[k]], [y[k], y[k]], color=GRID, lw=1.5, zorder=1, solid_capstyle="round")
    ax.scatter(tg, y, marker="|", s=60, color=INK, lw=1.3, zorder=2, label="pledged change")
    ax.scatter(df[actual][good], y[good], s=22, color=CAT[0], edgecolors="white", linewidths=0.5, zorder=3, label=okl)
    ax.scatter(df[actual][~good], y[~good], s=22, color=CAT[1], edgecolors="white", linewidths=0.5, zorder=3, label=nol)
    if actual == "change_2020":
        ax.scatter(df.change_2019, y, s=10, facecolors="none", edgecolors=MUTED, lw=0.7, zorder=2, label="2019 (pre-COVID)")
    if actual == "change23":
        ax.set_xlim(-90, XMAX)
        for k in np.where(df[actual].values > XMAX)[0]:
            ax.scatter([XMAX - 2], [y[k]], marker=">", s=22, color=CAT[1], zorder=4)
            ax.text(XMAX - 6, y[k] + 0.45, f"{df[actual].iloc[k]:+.0f}% (data mismatch, see text)", ha="right", fontsize=5.5, color=INK2)
    ax.axvline(0, color=AXIS, lw=0.8); ax.set_yticks(y); ax.set_yticklabels(df.iso, fontsize=6)
    ax.set_xlabel("change in emissions vs base year (%)"); ax.set_title(title); grid(ax)
    ax.legend(loc="lower right" if actual == "change23" else "upper left", frameon=False, fontsize=5.8)
fig.tight_layout()
save(fig, "fig2_say_vs_do")

# ---------------- Fig 3: strategy vs parliament theme gaps ----------------
S = pd.read_csv(PROC / "lts_vs_parliament_profiles_with_translated.csv").set_index("cc"); S = S[S.n_goal >= 30]
cats = ["energy", "transport", "buildings", "industry", "agriculture", "land_forest", "waste", "instruments", "removals"]
NICE = {"land_forest": "land & forests", "instruments": "policy instruments", "removals": "carbon removals"}
gap = pd.Series({k: np.nanmean(np.log2((S[f"lts_{k}"] + 1e-3) / (S[f"par_goal_{k}"] + 1e-3))) for k in cats}).sort_values()
fig, ax = plt.subplots(figsize=(3.42, 2.6))
cols = [CAT[0] if v > 0 else CAT[1] for v in gap.values]
ax.barh([NICE.get(k, k) for k in gap.index], gap.values, color=cols, height=0.6)
for k, v in enumerate(gap.values):
    ax.text(v + (0.06 if v > 0 else -0.06), k, f"{2 ** v:.1f}×" if v > 0 else f"1/{2 ** -v:.1f}", va="center", ha="left" if v > 0 else "right", fontsize=5.8, color=INK2)
ax.axvline(0, color=AXIS, lw=0.8); grid(ax)
ax.set_xlabel("log2(share in strategy / share in parliament)")
ax.set_title(f"Strategies stress land and removals;\nparliaments stress energy (n = {len(S)})")
ax.set_xlim(gap.min() - 0.7, gap.max() + 0.7)
fig.tight_layout(); save(fig, "fig3_strategy_vs_parliament")

# ---------------- Fig 4: hedged wording and emission growth; ideas spreading ----------------
F = pd.read_csv(PROC / "round4_firmness_v2.csv", index_col=0); F = F[(F.e15 >= 1) & F[["t1519", "t0515"]].notna().all(axis=1)]
INC = ["Low income", "Lower middle income", "Upper middle income", "High income"]
fig, axs = plt.subplots(1, 2, figsize=(7.0, 2.8), gridspec_kw={"width_ratios": [1.1, 1]})
ax = axs[0]
for k, g in enumerate(INC):
    s = F[F.income == g]; jit = np.random.default_rng(k).uniform(-0.04, 0.04, len(s))
    ax.scatter(s.firmness_v2 + jit, s.t1519.clip(-8, 12), s=14, color=CAT[k], edgecolors="white", linewidths=0.4, label=f"{g} (n={len(s)})", alpha=0.9)
ax.axhline(0, color=AXIS, lw=0.8); grid(ax, "both"); ax.set_ylim(-8.5, 15.5)
ax.set_xlabel("← more hedged      wording of first NDC      firmer →"); ax.set_ylabel("emission trend 2015–19 (%/yr, clipped)")
ax.set_title("A  Hedged pledges went with faster growth"); ax.legend(frameon=False, fontsize=5.5, loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=2)
ax.text(0.02, 0.97, "partial ρ = −0.16 (controls: income, 2005–15 trend), p = 0.03", transform=ax.transAxes, fontsize=5.8, color=INK2, va="top")
ax = axs[1]
DF = pd.read_csv(PROC / "ndc_idea_diffusion.csv").set_index("idea")
SHOW = {"Article 6 / carbon markets": "Article 6 / carbon markets", "methane": "methane", "1.5 degrees": "1.5 °C", "electric vehicles": "electric vehicles",
        "net zero / neutrality": "net zero", "circular economy": "circular economy", "loss and damage": "loss and damage", "just transition": "just transition"}
ideas = [(lab, DF.loc[k, ["first_ndc", "revised_first_ndc", "third_ndc"]].round().astype(int).tolist()) for k, lab in SHOW.items()]
NC = int(DF.n_countries.iloc[0])
x = [0, 1, 2]
for k, (nm, v) in enumerate(ideas):
    ax.plot(x, v, color=CAT[k], lw=1.6, marker="o", ms=3.5, markeredgecolor="white", markeredgewidth=0.4)
    ax.text(2.06, v[-1], nm, va="center", fontsize=5.8, color=INK)
ax.set_xticks(x); ax.set_xticklabels(["first NDC", "revised first", "third NDC"]); ax.set_xlim(-0.1, 2.9)
ax.set_ylabel(f"% of {NC} countries mentioning"); grid(ax, "y")
ax.set_title("B  Ideas spreading between pledge rounds")
# de-overlap labels on the right edge
txts = sorted([t for t in ax.texts], key=lambda t: t.get_position()[1]); last = -99
for t in txts:
    yv = max(t.get_position()[1], last + 4.2); t.set_y(yv); last = yv
fig.tight_layout(); save(fig, "fig4_hedging_and_diffusion")
