"""Full theme scheme for the rebuilt r/StopEatingSeedOils BERTopic (123 topics): EVERY topic in exactly one theme (26 Nov 2026, proposal for KK to confirm).
Rule: the original nine themes (themes_confirmed.json) are anchors and keep their topics; every other topic was placed by MEANING (top words) with the embedding similarity to the theme as a check, NOT by growth;
KK added 'Lifestyle'; the topics left over form 'Staple foods', 'Cooking and cooking fats' and 'General talk and meta' (generic seed-oil talk, the subreddit itself, thanks, spam, influencers). tiers: original | assigned | flagged (judgement call, or the topic is closer to another theme).
Outputs: seedoils/data/processed/themes_full.json, themes_full_by_topic.csv (topic, docs, words, theme, similarity to own and best other theme), themes_full_summary.csv (per theme: topics, docs, shares before / from 2024, ratio, emotion groups).
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/themes_full.py"""
import json
import numpy as np
import pandas as pd

R, P = "seedoils/data/processed_rebuild/", "seedoils/data/processed/"
ORIG = json.load(open(P + "themes_confirmed.json"))
ADD = {
 "Politics (RFK, Trump, left/right)": [93],
 "Distrust of industry, medicine and media": [99, 38, 67, 88, 100, 103],
 "Omega-6 / PUFA biochemistry": [4, 2, 112, 110, 20, 45, 108, 22, 35, 28, 80, 117, 49, 79, 119],
 "Keto, carbs, fasting": [58, 14, 92, 25, 43],
 "Other diets (vegan, carnivore, ancestral, Mediterranean)": [11, 12, 69, 107, 62, 102, 18, 115],
 "Shopping (stores, chips, avocado oil)": [95, 55, 113, 7, 61, 3, 32, 63, 64, 71, 106, 114, 91, 21, 42],
 "Ingredient labels and processed food": [121, 84, 54, 94, 120, 40, 24],
 "Lifestyle (smoking, skin and sun, mental health, allergies, pets, family)": [39, 10, 13, 105, 122, 87, 68, 101, 90, 70, 51, 66],
 "Staple foods (milk, grains, nuts, soy, chocolate, coffee)": [16, 29, 15, 48, 31, 111, 116, 53, 96, 65, 85, 44, 52],
 "Cooking and cooking fats (butter, tallow, frying)": [23, 41, 75, 76, 34, 36, 9],
 "General talk and meta (generic seed-oil, subreddit, thanks, influencers)": [0, 5, 78, 82, 83, 50, 104],
}
FLAGGED = {93, 99, 38, 67, 88, 100, 103, 49, 79, 119, 117, 28, 80, 25, 43, 102, 18, 115, 40, 24, 101, 90, 70, 51, 66, 68, 122, 78, 104, 50}  # judgement calls
theme = {}; tier = {}
for k, ids in ORIG.items():
    for i in ids: theme[int(i)] = k; tier[int(i)] = "original"
for k, ids in ADD.items():
    for i in ids:
        assert int(i) not in theme, f"topic {i} placed twice"; theme[int(i)] = k; tier[int(i)] = "flagged" if int(i) in FLAGGED else "assigned"
info = pd.read_csv(R + "seso_topics_info.csv").set_index("topic"); left = [t for t in info.index if t not in theme]; print("topics not yet placed:", left)
assert not left, "place every topic"
json.dump({k: sorted(t for t, v in theme.items() if v == k) for k in dict.fromkeys(list(ORIG) + list(ADD))}, open(P + "themes_full.json", "w"), indent=1)
# similarity check
V = np.load(R + "seso_vectors.npy").astype(np.float32); D = pd.read_csv(R + "seso_docs.csv.gz", usecols=["id", "created_utc"]).merge(pd.read_csv(R + "seso_doc_topics.csv.gz", usecols=["id", "topic"]), on="id")
cen = {t: V[(D.topic == t).values].mean(0) for t in info.index}; cen = {t: v / np.linalg.norm(v) for t, v in cen.items()}
def tcent(k, excl=None):
    ids = [t for t, v in theme.items() if v == k and t != excl]; w = np.array([info.n_docs[t] for t in ids], float); c = sum(wi * cen[t] for wi, t in zip(w, ids)); return c / np.linalg.norm(c)
names = list(dict.fromkeys(theme.values())); rows = []
for t in info.index:
    own = float(cen[t] @ tcent(theme[t], excl=t)) if sum(1 for v in theme.values() if v == theme[t]) > 1 else np.nan
    oth = {k: float(cen[t] @ tcent(k)) for k in names if k != theme[t]}; bo = max(oth, key=oth.get)
    rows.append({"topic": t, "docs": int(info.n_docs[t]), "words": ", ".join(info.top_words[t].split(", ")[:6]), "theme": theme[t], "tier": tier[t], "sim_own_theme": round(own, 2), "closest_other_theme": bo, "sim_other": round(oth[bo], 2), "closer_to_other": bool(oth[bo] > own)})
T = pd.DataFrame(rows); T.to_csv(P + "themes_full_by_topic.csv", index=False)
print("topics closer to another theme's centroid than to their own (leave-one-out):", int(T.closer_to_other.sum()), "of", len(T), "| of those, original-theme topics:", int(T[(T.tier == 'original') & T.closer_to_other].shape[0]))
# shares and emotion groups
D["theme"] = D.topic.map(theme); D["t"] = pd.to_datetime(D.created_utc, unit="s"); D["pre"] = D.t < "2024-01-01"
z = np.load(R + "goemo_seso.npz", allow_pickle=True); labs = list(pd.read_csv(P + "goemo_monthly.csv", nrows=1).columns[1:29]); Pm = z["p"].astype(float)
neg = "anger annoyance disappointment disapproval disgust embarrassment fear grief nervousness remorse sadness".split()
E = pd.DataFrame({"id": z["id"], "neg": (Pm[:, [labs.index(l) for l in neg]] >= 0.5).any(1), "flag": (Pm[:, [labs.index(l) for l in "anger annoyance disapproval disgust".split()]] >= 0.5).any(1)}); D = D.merge(E, on="id")
rng = np.random.default_rng(0); out = []
for k in names:
    s = D[D.theme == k]; a, b = s[s.pre], s[~s.pre]; sh0, sh1 = len(a) / D.pre.sum() * 100, len(b) / (~D.pre).sum() * 100
    b2 = s[s.t >= "2024-08-01"]; bs = [rng.choice(b2.neg.values, len(b2)).mean() - rng.choice(a.neg.values, len(a)).mean() for _ in range(300)] if len(a) > 50 and len(b2) > 50 else [np.nan]
    out.append({"theme": k, "topics": int((T.theme == k).sum()), "docs": len(s), "share_before": round(sh0, 2), "share_from2024": round(sh1, 2), "ratio": round(sh1 / sh0, 2), "negative_before": round(100 * a.neg.mean(), 1), "negative_from_aug24": round(100 * b2.neg.mean(), 1), "neg_change_lo": round(100 * np.nanpercentile(bs, 2.5), 1), "neg_change_hi": round(100 * np.nanpercentile(bs, 97.5), 1)})
S = pd.DataFrame(out); S.to_csv(P + "themes_full_summary.csv", index=False)
pd.set_option("display.width", 260, "display.max_colwidth", 60); S["theme"] = S.theme.str[:58]; print(S.to_string(index=False)); print(f"\ntotal docs {S.docs.sum():,}")
print("\nflagged or closer-to-other topics:"); print(T[(T.tier == "flagged") | T.closer_to_other][["topic", "docs", "words", "theme", "sim_own_theme", "closest_other_theme", "sim_other"]].assign(theme=lambda d: d.theme.str[:24], closest_other_theme=lambda d: d.closest_other_theme.str[:24]).to_string(index=False))
