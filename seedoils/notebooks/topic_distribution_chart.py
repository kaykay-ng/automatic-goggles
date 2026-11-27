"""Distribution of documents over topics, in the style of the common topic-model tutorial chart: (left) number of documents by DOMINANT topic (the topic BERTopic assigned, every outlier moved to its nearest topic, so all 149,815 documents count); (right) number of documents by TOPIC WEIGHTAGE (the summed HDBSCAN soft membership of all documents in each topic, rescaled so the total is 149,815; soft memberships are closeness to a topic's cluster, not a mixture of topics).
Two versions: the 10 largest of the 123 topics (labelled with their top 3 words) and the 14 themes (themes_full_v3.json). Output: seedoils/figures/topic_distribution_topics.png and topic_distribution_themes.png (exploratory).
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/topic_distribution_chart.py"""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

Rp, P = "seedoils/data/processed_rebuild_prob/", "seedoils/data/processed/"
z = np.load(Rp + "seso_probs.npz", allow_pickle=True); pr = z["p"].astype(np.float64); T = pd.read_csv(Rp + "seso_doc_topics.csv.gz"); assert (T.id.values == z["id"]).all(); N = len(T)
info = pd.read_csv(Rp + "seso_topics_info.csv").set_index("topic"); topics = sorted(info.index)
dom = T.topic.value_counts().reindex(topics, fill_value=0).values.astype(float); w = pr.sum(0); w = w / w.sum() * N
th = json.load(open(P + "themes_full_v3.json")); short = lambda s: s.split(" (")[0].replace("Distrust of industry, medicine and media", "Distrust of industry & media").replace("Ingredient labels and processed food", "Ingredient labels").replace("Omega-6 / PUFA biochemistry", "Omega-6 / PUFA").replace("General talk and meta", "General talk, meta")
def draw(labels, d, wt, fname, rot, title):
    fig, ax = plt.subplots(1, 2, figsize=(13.5 if rot == 0 else 11.5, 4.6), sharey=True, constrained_layout=True); x = np.arange(len(labels))
    ax[0].bar(x, d, color="#b02020", width=0.5); ax[1].bar(x, wt, color="#4682b4", width=0.5)
    for a, t in zip(ax, ("Number of Documents by Dominant Topic", "Number of Documents by Topic Weightage")):
        a.set_title(t, fontsize=10); a.set_xticks(x); a.set_xticklabels(labels, rotation=rot, ha="right" if rot else "center", fontsize=7 if rot == 0 else 8); a.set_ylim(0, max(d.max(), wt.max()) * 1.08)
    ax[0].set_ylabel("Number of Documents"); fig.suptitle(title, fontsize=9, color="0.35"); fig.savefig(fname, dpi=170)
order = np.argsort(-dom)[:10]; lab = ["Topic %d\n" % topics[i] + ",\n".join(info.top_words[topics[i]].split(", ")[:2]) for i in order]
draw(lab, dom[order], w[order], "seedoils/figures/topic_distribution_topics.png", 0, f"The 10 largest of the 123 topics (all {N:,} documents; weightage rescaled to the same total)")
names = list(th); dd = np.array([sum(dom[topics.index(t)] for t in th[k]) for k in names]); ww = np.array([sum(w[topics.index(t)] for t in th[k]) for k in names]); o = np.argsort(-dd)
draw([short(names[i]) for i in o], dd[o], ww[o], "seedoils/figures/topic_distribution_themes.png", 40, f"The 14 themes (all {N:,} documents; weightage rescaled to the same total)")
print("largest topics: dominant vs weightage"); [print(f"  topic {topics[i]:>3}: {dom[i]:>8,.0f} vs {w[i]:>8,.0f}  {info.top_words[topics[i]][:50]}") for i in order]
print("themes:"); [print(f"  {short(names[i]):<30}{dd[i]:>9,.0f} vs {ww[i]:>9,.0f}") for i in o]
