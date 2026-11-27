"""Reading validation of the outlier threshold (0.05) for three themes (politics, distrust, omega-6): are the documents just above the threshold (reassigned) as good a fit as those just below (left unassigned)?
Population: HDBSCAN outliers whose highest-probability topic belongs to the theme; ABOVE = highest probability in [0.05, 0.08), BELOW = in [0.03, 0.05). N_PER documents per theme and side, drawn at random (seed 1), shuffled, side and probability HIDDEN from the reader.
Writes (Reddit text: local only, do not commit or paste) seedoils/data/processed_rebuild_prob/threshold_reading.html (label page; 'Download answers' saves a CSV) and threshold_reading_key.csv (id, theme, side, maxp).
Run from final_project/:  ./.venv-nlp/bin/python seedoils/notebooks/threshold_reading_sample.py"""
import html, json
import numpy as np, pandas as pd
R, P = "seedoils/data/processed_rebuild_prob/", "seedoils/data/processed/"; N_PER = 15; rng = np.random.default_rng(1)
z = np.load(R + "seso_probs.npz", allow_pickle=True); pr = z["p"].astype(np.float32); T = pd.read_csv(R + "seso_doc_topics.csv.gz"); T["maxp"] = pr.max(1); T["arg"] = pr.argmax(1)
D = pd.read_csv(R + "seso_docs.csv.gz", usecols=["id", "text"], keep_default_na=False); T = T.merge(D, on="id")
th = json.load(open(P + "themes_full.json")); m = {int(i): k for k, v in th.items() for i in v}; T["argtheme"] = T.arg.map(m)
out = T[T.topic_before_outlier_fix == -1]; pick = {"Politics (RFK, Trump, left/right)": "Politics", "Distrust of industry, medicine and media": "Distrust of industry, medicine and media", "Omega-6 / PUFA biochemistry": "Omega-6 / PUFA biochemistry"}
rows = []
for k, label in pick.items():
    s = out[out.argtheme == k]
    for side, lo, hi in (("above", 0.05, 0.08), ("below", 0.03, 0.05)):
        c = s[(s.maxp >= lo) & (s.maxp < hi)]; print(f"{label[:30]:<32}{side:<6} available {len(c):,}")
        for _, r in c.sample(min(N_PER, len(c)), random_state=1).iterrows(): rows.append({"id": r.id, "theme": label, "side": side, "maxp": round(float(r.maxp), 3), "text": r.text})
S = pd.DataFrame(rows).sample(frac=1, random_state=2).reset_index(drop=True); S[["id", "theme", "side", "maxp"]].to_csv(R + "threshold_reading_key.csv", index=False)
cards = "".join(f'<div class="c" data-id="{r.id}"><div class="t"><b>{i + 1}.</b> Theme: <b>{html.escape(r.theme)}</b></div><p>{html.escape(r.text[:800])}{"..." if len(r.text) > 800 else ""}</p>'
                f'<label><input type="radio" name="q{i}" value="fits"> fits the theme</label> <label><input type="radio" name="q{i}" value="partly"> partly</label> <label><input type="radio" name="q{i}" value="no"> does not fit</label></div>' for i, r in S.iterrows())
page = f"""<!doctype html><meta charset="utf-8"><title>Threshold reading</title><style>body{{font:15px system-ui;max-width:760px;margin:20px auto;padding:0 16px}}.c{{border:1px solid #ccc;border-radius:6px;padding:10px 14px;margin:12px 0}}.t{{color:#444;margin-bottom:6px}}p{{margin:6px 0 10px}}label{{margin-right:14px}}button{{padding:8px 14px}}</style>
<h2>Does the comment fit the theme named above it?</h2><p>{len(S)} comments, shuffled. Judge only whether the comment is about the named theme (fits / partly / does not fit). Your answers stay in this browser until you press Download.</p>{cards}
<button onclick="dl()">Download answers (CSV)</button><script>function dl(){{let o=['id,answer'];document.querySelectorAll('.c').forEach((c,i)=>{{let r=c.querySelector('input:checked');o.push(c.dataset.id+','+(r?r.value:''))}});let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([o.join('\\n')],{{type:'text/csv'}}));a.download='threshold_reading_answers.csv';a.click()}}</script>"""
open(R + "threshold_reading.html", "w", encoding="utf-8").write(page); print(f"{len(S)} comments written")
