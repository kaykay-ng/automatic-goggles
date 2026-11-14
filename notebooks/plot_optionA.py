"""Scatter plots of the three pre-declared Option A tests (one dot per country). Run from final_project/."""
import pandas as pd, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
D = pd.read_csv("data/processed/country_text_and_food_system.csv", index_col=0)
col = {"North": "#2a6f97", "West": "#d1495b", "South": "#edae49", "East": "#66a182"}
panels = [("shift_pct", "climate_in_agri", "P1: hidden emissions in imports -> climate talk in farming debates",
           "trade-adjusted footprint vs production-based (%)\n(+ = imports emissions, - = exports them)", "share of agriculture speeches that mention climate", 100),
          ("net_animal_exports_pc", "attention_agri", "P2: net meat/dairy exports -> attention to agriculture",
           "net meat + dairy + egg exports (kg per person)", "agriculture speeches per 10,000", 1),
          ("food_selfsuff", "attention_food", "P3: food self-sufficiency -> attention to food",
           "self-sufficiency (log2 production/supply; 0 = balanced)", "food speeches per 10,000", 1)]
fig, axs = plt.subplots(1, 3, figsize=(17, 5.2))
for ax, (x, y, title, xl, yl, mult) in zip(axs, panels):
    yy = D[y] * mult
    for r, c in col.items():
        m = D.region == r
        ax.scatter(D.loc[m, x], yy[m], s=38, color=c, label=r)
    for iso in D.index:
        ax.annotate(iso, (D.loc[iso, x], yy[iso]), fontsize=7, xytext=(3, 3), textcoords="offset points")
    ax.set_title(f"{title}\nSpearman rho = {spearmanr(D[x], yy)[0]:+.2f}", fontsize=9)
    ax.set_xlabel(xl, fontsize=8); ax.set_ylabel(yl, fontsize=8)
axs[0].legend(title="region", fontsize=7)
fig.tight_layout(); fig.savefig("figures/optionA_primary_tests.png", dpi=140)
print("saved")
