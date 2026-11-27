"""Kardos-style reading check of the outlier threshold at TOPIC level (27 Nov 2026): does a document tagged with a topic really belong to it, and at what probability does that stop being true?
Bands (side/probability HIDDEN from the reader, comments shuffled): BASE = documents HDBSCAN itself put in a topic (not outliers); outliers moved to their most probable topic at highest probability in [0.10, 1], [0.05, 0.10), [0.02, 0.05), [0.01, 0.02). N_PER = 30 documents per band, drawn at random over all 123 topics (seed 1). The reader sees the comment and the topic label (top six class-based TF-IDF words; words from one repeated document are skipped) and answers fits / partly / no.
Writes (Reddit text: local only, do not commit or paste): seedoils/data/processed_rebuild_prob/topic_fit_reading.html (label page; 'Download answers' saves topic_fit_reading_answers.csv), topic_fit_reading_key.csv (id, band, topic, maxp) and topic_fit_population.json (documents per band, for population weighting).
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/topic_fit_reading_sample.py"""
import html, json
import numpy as np, pandas as pd
R = "seedoils/data/processed_rebuild_prob/"; N_PER = 30
z = np.load(R + "seso_probs.npz", allow_pickle=True); pr = z["p"].astype(np.float32); T = pd.read_csv(R + "seso_doc_topics.csv.gz"); T["maxp"] = pr.max(1); T["arg"] = pr.argmax(1)
D = pd.read_csv(R + "seso_docs.csv.gz", usecols=["id", "text"], keep_default_na=False); T = T.merge(D, on="id")
info = pd.read_csv(R + "seso_topics_info.csv").set_index("topic"); SKIP = {47: {"rape"}, 103: {"et al", "et", "al"}, 108: {"capita"}}
lab = lambda t: ", ".join([w for w in info.top_words[t].split(", ") if w not in SKIP.get(t, ())][:6])
base = T[T.topic_before_outlier_fix >= 0].assign(band="BASE (HDBSCAN topic)", tp=lambda d: d.topic_before_outlier_fix); out = T[T.topic_before_outlier_fix == -1].assign(tp=lambda d: d.arg)
bands = [("BASE (HDBSCAN topic)", base)] + [(f"outlier p in [{lo}, {hi})", out[(out.maxp >= lo) & (out.maxp < hi)].assign(band=f"outlier p in [{lo}, {hi})")) for lo, hi in ((0.10, 1.01), (0.05, 0.10), (0.02, 0.05), (0.01, 0.02))]
pop = {}; rows = []
for name, d in bands:
    pop[name] = len(d); print(f"{name:<28} documents {len(d):>7,}")
    for _, r in d.sample(min(N_PER, len(d)), random_state=1).iterrows(): rows.append({"id": r.id, "band": name, "topic": int(r.tp), "maxp": round(float(r.maxp), 3), "text": r.text})
json.dump(pop, open(R + "topic_fit_population.json", "w"))
S = pd.DataFrame(rows).sample(frac=1, random_state=2).reset_index(drop=True); S[["id", "band", "topic", "maxp"]].to_csv(R + "topic_fit_reading_key.csv", index=False)
cards = "".join(f'<div class="c" data-id="{r.id}"><div class="t"><b>{i + 1}.</b> Topic: <b>{html.escape(lab(r.topic))}</b></div><p>{html.escape(r.text[:800])}{"..." if len(r.text) > 800 else ""}</p>'
                f'<label><input type="radio" name="q{i}" value="fits"> fits the topic</label> <label><input type="radio" name="q{i}" value="partly"> partly</label> <label><input type="radio" name="q{i}" value="no"> does not fit</label></div>' for i, r in S.iterrows())
page = f"""<!doctype html><meta charset="utf-8"><title>Topic fit reading</title><style>body{{font:15px system-ui;max-width:760px;margin:20px auto;padding:0 16px}}.c{{border:1px solid #ccc;border-radius:6px;padding:10px 14px;margin:12px 0}}.t{{color:#444;margin-bottom:6px}}p{{margin:6px 0 10px}}label{{margin-right:14px}}button{{padding:8px 14px}}</style>
<h2>Does the comment belong to the topic named above it?</h2><p>{len(S)} comments, shuffled. The topic is shown by its six highest-scoring words. Judge only whether the comment is about what these words describe (fits / partly / does not fit). Your answers stay in this browser until you press Download.</p>{cards}
<button onclick="dl()">Download answers (CSV)</button><script>function dl(){{let o=['id,answer'];document.querySelectorAll('.c').forEach((c,i)=>{{let r=c.querySelector('input:checked');o.push(c.dataset.id+','+(r?r.value:''))}});let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([o.join('\\n')],{{type:'text/csv'}}));a.download='topic_fit_reading_answers.csv';a.click()}}</script>"""
open(R + "topic_fit_reading.html", "w", encoding="utf-8").write(page); print(f"{len(S)} comments written")
