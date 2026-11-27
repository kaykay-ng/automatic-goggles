"""Second labeller for the GoEmotions GROUP hand check (27 Nov). Rebuilds Kaykay's label page (emotion_label_sample.py) with the SAME 130 comments
in the SAME order, taken from the ids in her committed answers (data/processed/emotion_label_answers.csv), with text from the local corpus
(data/processed/seso_docs.csv.gz). Same instructions and boxes: tick all of negative / positive / ambiguous, or 'neutral or none'. Blind: no
model output, no period, no first labeller's answers. The download is named emotion_label_answers_<initials>.csv (default HC) so the first
labeller's file is not overwritten; move it to seedoils/data/processed/.
Writes (Reddit text: local only, gitignored) seedoils/label_emotions_second.html.
Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/emotion_label_page_second.py [initials]"""
import html
import sys

import pandas as pd

INI = sys.argv[1] if len(sys.argv) > 1 else "HC"
ids = pd.read_csv("seedoils/data/processed/emotion_label_answers.csv", usecols=["id"]).id.astype(str).tolist()
T = pd.read_csv("seedoils/data/processed/seso_docs.csv.gz", usecols=["id", "text"], keep_default_na=False); T["id"] = T.id.astype(str); T = T.set_index("id").text
missing = [i for i in ids if i not in T.index]
assert not missing, f"{len(missing)} comments not in the local corpus: {missing[:5]}"
cards = "".join(f'<div class="c" data-id="{i}"><p><b>{k + 1}.</b> {html.escape(T[i][:900])}{"..." if len(T[i]) > 900 else ""}</p>'
                f'<label><input type="checkbox" class="e" value="neg"> negative emotion</label> <label><input type="checkbox" class="e" value="pos"> positive emotion</label> '
                f'<label><input type="checkbox" class="e" value="amb"> ambiguous (curious, confused, surprised, realization)</label> <label><input type="checkbox" class="n" value="neu"> neutral or none</label> '
                f'<input class="note" placeholder="note (optional)"></div>' for k, i in enumerate(ids))
page = f"""<!doctype html><meta charset="utf-8"><title>Emotion groups: hand check</title><style>body{{font:15px system-ui;max-width:800px;margin:20px auto;padding:0 16px}}.c{{border:1px solid #ccc;border-radius:6px;padding:10px 14px;margin:12px 0}}p{{margin:6px 0 10px}}label{{margin-right:12px;display:inline-block}}.note{{width:95%;margin-top:6px}}button{{padding:8px 14px}}details{{margin:10px 0}}#prog{{position:sticky;top:0;background:#fff;padding:6px 0;border-bottom:1px solid #ddd}}</style>
<h2>Which emotions does the comment express?</h2><div id="prog"></div><p>{len(ids)} comments, shuffled. Tick <b>all</b> that apply: a comment can express more than one. Tick &quot;neutral or none&quot; if no clear emotion is expressed (it clears the other boxes). Judge the comment's own wording, not the topic. Your answers are kept in this browser while you work; press Download at the end.</p>
<details><summary>What the groups mean (GoEmotions)</summary><p><b>Negative:</b> anger, annoyance, disappointment, disapproval, disgust, embarrassment, fear, grief, nervousness, remorse, sadness.<br><b>Positive:</b> admiration, amusement, approval, caring, desire, excitement, gratitude, joy, love, optimism, pride, relief.<br><b>Ambiguous:</b> confusion, curiosity, realization, surprise.</p></details>{cards}
<button onclick="dl()">Download answers (CSV)</button><script>
const KEY='emo_second_{INI}';let st={{}};try{{st=JSON.parse(localStorage.getItem(KEY)||'{{}}')}}catch(e){{}}
function save(){{try{{localStorage.setItem(KEY,JSON.stringify(st))}}catch(e){{}}prog()}}
function prog(){{let n=[...document.querySelectorAll('.c')].filter(c=>[...c.querySelectorAll('input[type=checkbox]')].some(x=>x.checked)).length;document.getElementById('prog').textContent=n+' of {len(ids)} answered'}}
document.querySelectorAll('.c').forEach(c=>{{const id=c.dataset.id,s=st[id]||{{}};c.querySelectorAll('input[type=checkbox]').forEach(x=>{{x.checked=!!s[x.value]}});c.querySelector('.note').value=s.note||'';
 c.querySelector('.n').addEventListener('change',e=>{{if(e.target.checked)c.querySelectorAll('.e').forEach(x=>x.checked=false)}});
 c.querySelectorAll('.e').forEach(x=>x.addEventListener('change',e=>{{if(e.target.checked)c.querySelector('.n').checked=false}}));
 c.addEventListener('change',()=>{{let o={{}};c.querySelectorAll('input[type=checkbox]').forEach(x=>o[x.value]=x.checked);o.note=c.querySelector('.note').value;st[id]=o;save()}});
 c.querySelector('.note').addEventListener('input',()=>{{(st[id]=st[id]||{{}}).note=c.querySelector('.note').value;save()}})}});prog();
function dl(){{let o=['id,neg,pos,amb,neutral,note,labeller'];document.querySelectorAll('.c').forEach(c=>{{let v=k=>c.querySelector('input[value='+k+']').checked?1:0;let note=c.querySelector('.note').value.replace(/[,\\n"]/g,' ');o.push([c.dataset.id,v('neg'),v('pos'),v('amb'),v('neu'),note,'{INI}'].join(','))}});let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([o.join('\\n')],{{type:'text/csv'}}));a.download='emotion_label_answers_{INI}.csv';a.click()}}</script>"""
open("seedoils/label_emotions_second.html", "w", encoding="utf-8").write(page)
print(f"wrote seedoils/label_emotions_second.html: {len(ids)} comments, same order as the first labeller; download -> emotion_label_answers_{INI}.csv")
