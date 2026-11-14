"""Split the lumped keyword flag into three separate topics (agriculture, food, climate) from the saved flagged text.

Run from final_project/:  ../.venv/bin/python notebooks/split_topics.py
Reads data/processed/parlamint/flagged_XX.csv.gz (speeches that matched the first, lumped lists), re-matches with three
separate lists, writes topic_flags_XX.csv.gz (speech_id + counts). LIMITATION: speeches that matched none of the first
lists are not in the flagged files, so words added to the lists now (e.g. 'hunger', 'nutrition') are only found within
speeches that already matched 'food', 'farm', 'climate' etc. Expanding vocabulary needs a full re-parse of the raw text.
"""
import glob, re
import pandas as pd

AGRI = re.compile(r"\bagricultur\w*|\bfarm(?:s|er|ers|ing)?\b|\bcrops?\b|\bharvests?\b|\bfertili[sz]\w*|\blivestock\b|\bcattle\b|\bcommon agricultural policy\b|\bfisher\w*", re.I)
FOOD = re.compile(r"\bfood\b|\bfoods\b|\bnutrition\w*|\bhunger\b|\bdiets?\b|\bgrocer\w*|\bsupermarkets?\b|\bfood security\b", re.I)
CLIM = re.compile(r"\bclimate\b|\bgreenhouse\b|\bglobal warming\b|\bcarbon\b|\bemissions?\b|\bdecarboni[sz]|\bnet[- ]zero\b|\bfossil fuels?\b", re.I)
MEAT = re.compile(r"\bmeat\b|\bdairy\b|\bbeef\b|\bpork\b|\bpoultry\b|\bmilk\b|\bsheep\b|\bpigs?\b|\bcows?\b", re.I)

rows = []
for f in sorted(glob.glob("data/processed/parlamint/flagged_*.csv.gz")):
    d = pd.read_csv(f, usecols=["country", "speech_id", "date", "words", "topic", "text"])
    t = d.text.fillna("")
    out = pd.DataFrame({"country": d.country, "speech_id": d.speech_id, "date": d.date, "words": d.words, "topic": d.topic,
                        "n_agri": t.str.count(AGRI), "n_food": t.str.count(FOOD),
                        "n_climate": t.str.count(CLIM), "n_meat": t.str.count(MEAT)})
    out.drop(columns=["country"]).to_csv(f.replace("flagged_", "topic_flags_"), index=False)
    rows.append(out)
A = pd.concat(rows, ignore_index=True)
for c in ("agri", "food", "climate"):
    A[c] = A[f"n_{c}"] > 0
A["sub"] = A.words >= 50
pd.set_option("display.width", 200)
print("speeches by topic keyword (all lengths | substantive >=50 words):")
for c in ("agri", "food", "climate"):
    print(f"  {c:8s} {A[c].sum():7d} | {(A[c] & A['sub']).sum():7d}")
print("overlaps (substantive): agri&food", int((A.agri & A.food & A['sub']).sum()), "| agri&climate", int((A.agri & A.climate & A['sub']).sum()),
      "| food&climate", int((A.food & A.climate & A['sub']).sum()), "| all three", int((A.agri & A.food & A.climate & A['sub']).sum()))
print("only-one-topic (substantive): agri only", int((A.agri & ~A.food & ~A.climate & A['sub']).sum()),
      "| food only", int((~A.agri & A.food & ~A.climate & A['sub']).sum()), "| climate only", int((~A.agri & ~A.food & A.climate & A['sub']).sum()))
S = A[A["sub"]]
T = S.groupby("country").agg(agri=("agri", "sum"), food=("food", "sum"), climate=("climate", "sum"),
                             agri_climate=("agri", lambda s: int((s & S.loc[s.index, "climate"]).sum())),
                             food_climate=("food", lambda s: int((s & S.loc[s.index, "climate"]).sum())))
print("\nper country, substantive speeches:\n", T.sort_values("food").to_string())
for c in ("agri", "food", "climate"):
    v = T[c] if c in T else None
    print(f"countries with >=300 {c} speeches: {(T[c] >= 300).sum()}, >=1000: {(T[c] >= 1000).sum()}")
print("countries with >=300 agri&climate:", (T.agri_climate >= 300).sum(), "| food&climate:", (T.food_climate >= 300).sum())
