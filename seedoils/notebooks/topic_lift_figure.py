"""Paper figure (one column, 8.7 cm): co-writing lift before vs from 2024 for key topic pairs, from topic_network_lift_periods.json
(topic_network_lift_periods.py). Open circle = before 2024, filled = from 2024, bars = 95% bootstrap intervals, dotted line = chance (1); dashed lines = lift of all links of the network in each period (light: before 2024, dark: from 2024).
Text by LaTeX in Latin Modern, as the other figures. Output: paper/figures/topic_lift_periods.pdf and seedoils/figures/topic_lift_periods.png.
Run from the repo root:  PATH=/Library/TeX/texbin:$PATH ./.venv-nlp/bin/python seedoils/notebooks/topic_lift_figure.py"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams.update({"text.usetex": __import__("shutil").which("latex") is not None, "font.family": "serif", "font.serif": ["cmr10", "DejaVu Serif"], "axes.formatter.use_mathtext": True, "font.size": 7.5, "axes.spines.top": False, "axes.spines.right": False,
                     "text.latex.preamble": r"\usepackage[T1]{fontenc}\usepackage{lmodern}"})
L = json.loads(Path("seedoils/data/processed/topic_network_lift_periods.json").read_text())
A, B = L["periods"]["before 2024"]["sets"], L["periods"]["from 2024"]["sets"]
ROWS = [("Politics - Politics", "Politics -- politics"), ("Politics - Vaccines and COVID", "Politics -- vaccines"),
        ("Politics - Distrust of industry, medicine and media", "Politics -- distrust"), ("Politics - Studies and evidence", "Politics -- studies and evidence"),
        ("Politics - food, diet and shopping themes", "Politics -- food, diet and shopping"),
        ("Omega-6 / PUFA - Omega-6 / PUFA", "Omega-6 -- omega-6"), ("Omega-6 / PUFA - Keto, carbs, fasting", "Omega-6 -- keto"),
        ("Saturated-fat topic (4) - all other topics", "Saturated-fat topic -- all topics")]
NL = len(json.loads(Path("seedoils/data/processed/topic_cooccurrence_network.json").read_text())["edges_all"])  # all links: drawn as dashed reference lines, not a row (27 Nov)
BLUE, GREY = "#2a78d6", "#52514e"
fig, ax = plt.subplots(figsize=(3.42, 2.5), constrained_layout=True)
for i, (k, lab) in enumerate(ROWS):
    y = len(ROWS) - 1 - i; c = BLUE if k.startswith("Politics") else GREY
    for d, off, filled in ((A[k], 0.17, False), (B[k], -0.17, True)):
        ax.plot(d["ci95"], [y + off] * 2, color=c, lw=0.9, alpha=0.55 if not filled else 1)
        ax.scatter([d["lift"]], [y + off], s=16, facecolor=c if filled else "white", edgecolor=c, linewidths=0.9, zorder=3)
ax.axvline(1, color="0.55", ls=":", lw=0.8)
ALL = "the all-years links"
ax.axvline(A[ALL]["lift"], color=GREY, ls=(0, (4, 2)), lw=0.8, alpha=0.45, zorder=0); ax.axvline(B[ALL]["lift"], color=GREY, ls=(0, (4, 2)), lw=0.8, zorder=0)
ax.set_yticks(range(len(ROWS))); ax.set_yticklabels([lab for _, lab in ROWS][::-1]); ax.set_xlim(0.45, 1.95)
ax.set_xlabel(r"Lift (1 = chance)")
ax.scatter([], [], s=16, facecolor="white", edgecolor=GREY, label="before 2024"); ax.scatter([], [], s=16, color=GREY, label="from 2024")
ax.plot([], [], color=GREY, ls=(0, (4, 2)), lw=0.8, alpha=0.45, label=f"all {NL} links, before 2024"); ax.plot([], [], color=GREY, ls=(0, (4, 2)), lw=0.8, label=f"all {NL} links, from 2024")
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=6.5, handletextpad=0.2, columnspacing=1.2)
fig.savefig("paper/figures/topic_lift_periods.pdf", bbox_inches="tight", pad_inches=0.02); fig.savefig("seedoils/figures/topic_lift_periods.png", dpi=300, bbox_inches="tight", pad_inches=0.02)
print("wrote paper/figures/topic_lift_periods.pdf")
