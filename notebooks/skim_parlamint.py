"""Skim: is there enough climate / food content in ParlaMint (2015-2022) to build a text analysis on?

Run from final_project/:  ../.venv/bin/python notebooks/skim_parlamint.py
Reads data/processed/parlamint/index_*.csv.gz. Keyword matches are a first skim, not a validated filter.
"""
import glob
import pandas as pd

pd.set_option("display.width", 220)
I = pd.concat([pd.read_csv(f) for f in sorted(glob.glob("data/processed/parlamint/index_*.csv.gz"))])
I = I.reset_index(drop=True)
I["year"] = I["date"].str[:4].astype(int)
I["climate"] = I.n_climate > 0
I["food"] = I.n_food > 0
I["both"] = I.climate & I.food
I["livestock"] = I.n_livestock > 0
I["topic_agri"] = I.topic == "Agriculture"
I["topic_env"] = I.topic.isin(["Environment", "Energy"])
I["substantive"] = I.words >= 50           # drop one-line procedural speeches
print(f"{len(I):,} speeches, {I.words.sum()/1e6:.0f}M words, {I.country.nunique()} countries, 2015-2022\n")

g = I.groupby("country")
T = pd.DataFrame({
    "speeches_k": g.size() / 1000,
    "years": g.year.nunique(),
    "climate": g.climate.sum(), "food": g.food.sum(), "both": g.both.sum(),
    "climate_pct": 100 * g.climate.mean(), "food_pct": 100 * g.food.mean(), "both_pct": 100 * g.both.mean(),
    "livestock": g.livestock.sum(),
    "topicAgri": g.topic_agri.sum(), "topicEnv/En": g.topic_env.sum(),
}).round({"speeches_k": 0, "climate_pct": 2, "food_pct": 2, "both_pct": 3})
print(T.sort_values("both").to_string())
print("\nTOTAL: climate", int(I.climate.sum()), "| food", int(I.food.sum()), "| both", int(I.both.sum()),
      "| livestock", int(I.livestock.sum()), "| topic=Agriculture", int(I.topic_agri.sum()))

print("\nclimate-keyword speeches per year (all countries):", I.groupby("year").climate.sum().to_dict())
print("food-keyword speeches per year:", I.groupby("year").food.sum().to_dict())
print("both per year:", I.groupby("year").both.sum().to_dict())

print("\nHow many countries clear a threshold (substantive speeches only, words>=50)?")
S = I[I.substantive]
for thr in (30, 100, 300, 1000):
    c = S[S.both].groupby("country").size()
    f = S[S.food].groupby("country").size()
    print(f"  >= {thr:4d} climate+food speeches: {(c >= thr).sum():2d} countries | >= {thr:4d} food speeches: {(f >= thr).sum():2d} countries")
print("\nAgreement between topic label and keywords (food keyword vs topic=Agriculture):")
print(pd.crosstab(I.topic_agri, I.food, margins=True).to_string())
print("\nTop topic labels among food-keyword speeches:", S[S.food].topic.value_counts(normalize=True).head(6).round(2).to_dict())
