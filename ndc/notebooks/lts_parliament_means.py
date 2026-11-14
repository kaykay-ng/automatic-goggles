"""How much goal-talk vs means-talk is there in parliaments (feasibility)? Run from final_project/:  ./.venv-nlp/bin/python ndc/notebooks/lts_parliament_means.py"""
import glob, re
from pathlib import Path
import numpy as np, pandas as pd

PM = Path("data/processed/parlamint"); PROC = Path("ndc/data/processed")
GOAL = re.compile(r"climate[- ]neutral\w*|carbon[- ]neutral\w*|net[- ]zero|zero net|long[- ]term (?:climate )?(?:strategy|goal|target)s?", re.I)
K = r"(?:reduc\w*|neutral\w*|zero|emissions?|carbon|greenhouse|decarboni\w*)"
G2050 = re.compile(rf"{K}[^.]{{0,80}}\b2050\b|\b2050\b[^.]{{0,80}}{K}", re.I)       # '2050' only next to emission/neutrality words (not population forecasts)
MEANS = {"energy": r"renewable\w*|\bwind\b|solar|photovoltaic|nuclear|hydropower|biomass|biogas|geothermal|energy transition|electrif\w*|energy efficiency|coal phase|phase[- ]out of coal|phase out coal|\bcoal\b",
         "transport": r"electric (?:vehicle|car)s?|\bEVs?\b|charging|public transport|railway|cycling|combustion engine|electromobility",
         "buildings": r"heat pumps?|insulation|renovation|retrofit\w*|district heating",
         "industry": r"hydrogen|carbon capture|\bCCS\b|\bCCUS\b|\bsteel\b|\bcement\b",
         "land_methane": r"livestock|methane|afforestation|reforestation|\bpeat\b",
         "instruments": r"carbon (?:price|pricing|tax)|emissions? trading|\bETS\b|carbon border",
         "removals": r"carbon removal|negative emissions|direct air capture|sequestration"}
MX = {k: re.compile(v, re.I) for k, v in MEANS.items()}


def goal_windows(text, w=300):
    spans = [m.span() for m in GOAL.finditer(text)]
    spans += [m.span() for m in G2050.finditer(text)]
    return [(max(0, a - w), min(len(text), b + w)) for a, b in spans]


rows, samples = [], []
for f in sorted(glob.glob(str(PM / "flagged_*.csv.gz"))):
    d = pd.read_csv(f, usecols=["country", "speech_id", "date", "role", "words", "n_climate", "text"])
    d = d[(d.words >= 50) & (d.role != "Chairperson") & (d.n_climate > 0)]
    cc = d.country.iloc[0]
    t = d.text.fillna("")
    wins = t.map(goal_windows); g = wins.map(len) > 0
    def near(text, ws, r):
        return any(r.search(text[a0:b0]) for a0, b0 in ws)
    cats = pd.DataFrame({k: [near(x, ws, r) if ws else False for x, ws in zip(t, wins)] for k, r in MX.items()}, index=d.index)   # same index as d (a mismatch gave ~0%)
    anym = cats.any(axis=1)
    r = dict(country=cc, climate_speeches=len(d), goal_speeches=int(g.sum()), goal_with_means=int((g & anym).sum()))
    r["means_share_of_goal"] = r["goal_with_means"] / max(r["goal_speeches"], 1)
    for k in MX:
        r[f"goal_has_{k}"] = float((cats[k] & g).sum() / max(g.sum(), 1))
    rows.append(r)
    gi = d[g & anym].sample(min(3, int((g & anym).sum())), random_state=1) if (g & anym).sum() else d.iloc[:0]
    gn = d[g & ~anym].sample(min(2, int((g & ~anym).sum())), random_state=1) if (g & ~anym).sum() else d.iloc[:0]
    for tag, S in [("GOAL+MEANS", gi), ("GOAL only", gn)]:
        for x in S.itertuples():
            ws = goal_windows(x.text); a0, b0 = ws[0]; samples.append((cc, tag, x.date[:4], x.text[a0:b0].replace("\n", " ")))
R = pd.DataFrame(rows).set_index("country")
L = pd.read_csv(PROC / "ndc_indicators_long.csv"); lts = L[L.document == "lts"]
iso3 = dict(AT="AUT", BA="BIH", BE="BEL", BG="BGR", CZ="CZE", DK="DNK", EE="EST", ES="ESP", FI="FIN", FR="FRA", GB="GBR", GR="GRC", HR="HRV", HU="HUN", IS="ISL", IT="ITA", LV="LVA", NL="NLD", NO="NOR", PL="POL", PT="PRT", RS="SRB", SE="SWE", SI="SVN", TR="TUR", UA="UKR")
cdr = lts[lts.indicator == "Reliance on Technological Carbon Removal"].groupby("iso").value.first().map(lambda v: "yes" if "Not Communicated" not in v else "no")
nz = L[L.indicator == "Net-zero Target Year"].groupby("iso").value.first()
R["lts_cdr"] = [cdr.get(iso3[c], "no LTS") for c in R.index]; R["net_zero_year"] = [nz.get(iso3[c], "") for c in R.index]
pd.set_option("display.width", 250)
print(R[["climate_speeches", "goal_speeches", "means_share_of_goal", "lts_cdr", "net_zero_year"]].round(2).sort_values("goal_speeches", ascending=False).to_string())
print("\nshare of GOAL speeches that mention each means category (all countries pooled; weighted by goal speeches):")
w = R.goal_speeches / R.goal_speeches.sum()
print({k: round(float((R[f"goal_has_{k}"] * w).sum()), 2) for k in MX})
print(f"\ntotal goal speeches {R.goal_speeches.sum()}, with means {R.goal_with_means.sum()} ({R.goal_with_means.sum()/R.goal_speeches.sum():.0%})")
R.to_csv(PROC / "lts_parliament_means_counts.csv")
import random
random.Random(4).shuffle(samples)
print("\nSAMPLES to eyeball (window around the goal statement; 10 goal+means, 8 goal-only):")
for tag, n in (("GOAL+MEANS", 10), ("GOAL only", 8)):
    for cc, tg, yr, txt in [x for x in samples if x[1] == tag][:n]:
        print(f"[{cc} {yr} {tg}] {txt[:560]}")
