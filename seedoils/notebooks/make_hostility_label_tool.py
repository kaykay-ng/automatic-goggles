"""Builds seedoils/label_hostility_sampleA.html (the 21 Nov sample; seedoils/label_hostility.html is now the teammate's page for the rerun sample, do not overwrite): a local, offline page for hand-labelling the 150 blind hostility items (no server, nothing uploaded).
Input: seedoils/data/processed/hostility_sample_to_label.csv (text only; the model's score band stays in hostility_sample_key.csv, so the labeller cannot see it).
Run from final_project/:  python3 seedoils/notebooks/make_hostility_label_tool.py
Keys: 1 hostile toward a person or group, 2 disagreement or complaint only, 3 neither, 4 cannot tell, left/right arrows move, N focuses the notes box.
Progress is kept in the browser (localStorage, per coder name). 'Download labels' saves hostility_labels_<coder>.csv (item, label, notes); move it to seedoils/data/processed/.
The page holds Reddit text, so it is gitignored. Then run notebooks/hostility_agreement.py."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows = [{"item": int(r["item"]), "text": r["text"]} for r in csv.DictReader(open(ROOT / "data" / "processed" / "hostility_sample_to_label.csv", encoding="utf-8"))]
data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
html = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Label hostility</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--fg:#1b1f24;--mut:#5a6470;--line:#dde1e7;--acc:#c4521a;--ok:#2a7a4b}
@media (prefers-color-scheme:dark){:root{--bg:#14171b;--card:#1b1f25;--fg:#e8ebef;--mut:#99a3af;--line:#2d333b;--acc:#f08a4b;--ok:#5cc98b}}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,sans-serif;padding:20px 16px 60px}.wrap{max-width:760px;margin:0 auto;display:flex;flex-direction:column;gap:14px}
h1{font-size:22px;margin:0}.sub{color:var(--mut);font-size:14px}.bar{height:8px;background:var(--line);border-radius:4px;overflow:hidden}.bar i{display:block;height:100%;background:var(--ok);width:0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:18px}.meta{color:var(--mut);font-size:13px;margin-bottom:8px}.text{white-space:pre-wrap;font-size:17px;line-height:1.6}
.btns{display:grid;grid-template-columns:1fr;gap:8px}button{font:inherit;text-align:left;padding:12px 14px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg);cursor:pointer}
button b{display:inline-block;min-width:22px;color:var(--acc)}button.sel{border-color:var(--acc);box-shadow:inset 0 0 0 2px var(--acc)}button:focus-visible,input:focus-visible,textarea:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.nav{display:flex;gap:8px;flex-wrap:wrap}.nav button{text-align:center;padding:9px 14px}textarea,input{font:inherit;width:100%;box-sizing:border-box;padding:8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg)}
details{color:var(--mut);font-size:14px}details p{margin:6px 0}
</style></head><body><div class="wrap">
<h1>Label hostility</h1>
<div class="sub">150 comments in random order. Read the whole comment and pick the one label that fits best. The model's score is not shown.</div>
<details open><summary>What the labels mean</summary>
<p><b>1 Hostile toward a person or group</b>: insults, name-calling, mockery, contempt or personal attacks aimed at a person or a group of people (including public figures, doctors, other commenters, "the left", "vegans").</p>
<p><b>2 Disagreement or complaint only</b>: criticises or disapproves of an idea, claim, product, company or institution without attacking people.</p>
<p><b>3 Neither</b>: neutral, a question, agreement, humour, information, thanks.</p>
<p><b>4 Cannot tell</b>: too short, missing context, or you cannot decide.</p></details>
<div><label class="sub" for="coder">Your name or initials (used in the file name)</label><input id="coder" placeholder="e.g. kk" autocomplete="off"></div>
<div class="bar"><i id="bar"></i></div><div class="sub" id="prog"></div>
<div class="card"><div class="meta" id="meta"></div><div class="text" id="text"></div></div>
<div class="btns" id="btns"></div>
<div><label class="sub" for="notes">Notes (optional, press N)</label><textarea id="notes" rows="2"></textarea></div>
<div class="nav"><button id="prev">&larr; Back</button><button id="next">Next &rarr;</button><button id="jump">Next unlabelled</button><button id="dl">Download labels (CSV)</button></div>
<div class="sub">Everything stays in this browser tab on this computer. Download the CSV when you finish (or any time), then move it to seedoils/data/processed/.</div>
</div><script>
const ITEMS=__DATA__;const CH=[["hostile","Hostile toward a person or group"],["complaint","Disagreement or complaint only"],["neither","Neither"],["unsure","Cannot tell"]];
let i=0,coder="",L={};const $=id=>document.getElementById(id);const key=()=>"hostility_labels_"+(coder||"anon");
function load(){try{L=JSON.parse(localStorage.getItem(key())||"{}")}catch(e){L={}}}function save(){try{localStorage.setItem(key(),JSON.stringify(L))}catch(e){}}
function draw(){const it=ITEMS[i],l=L[it.item]||{};$("meta").textContent="Item "+(i+1)+" of "+ITEMS.length;$("text").textContent=it.text;$("notes").value=l.notes||"";
 const b=$("btns");b.replaceChildren();CH.forEach(([k,t],n)=>{const x=document.createElement("button");x.className=l.label===k?"sel":"";x.innerHTML="<b>"+(n+1)+"</b> "+t;x.onclick=()=>set(k);b.appendChild(x)});
 const done=ITEMS.filter(z=>L[z.item]&&L[z.item].label).length;$("bar").style.width=(done/ITEMS.length*100)+"%";$("prog").textContent=done+" of "+ITEMS.length+" labelled"}
function set(k){const it=ITEMS[i];L[it.item]=Object.assign(L[it.item]||{},{label:k});save();if(i<ITEMS.length-1)i++;draw()}
$("notes").addEventListener("input",e=>{const it=ITEMS[i];L[it.item]=Object.assign(L[it.item]||{},{notes:e.target.value});save()});
$("coder").addEventListener("change",e=>{coder=e.target.value.trim().replace(/[^A-Za-z0-9_-]/g,"");try{localStorage.setItem("hostility_coder",coder)}catch(_){}load();draw()});
$("prev").onclick=()=>{if(i>0){i--;draw()}};$("next").onclick=()=>{if(i<ITEMS.length-1){i++;draw()}};
$("jump").onclick=()=>{const n=ITEMS.findIndex((z,j)=>j>i&&!(L[z.item]&&L[z.item].label));const m=n>=0?n:ITEMS.findIndex(z=>!(L[z.item]&&L[z.item].label));if(m>=0){i=m;draw()}};
$("dl").onclick=()=>{const q=s=>'"'+String(s==null?"":s).replace(/"/g,'""')+'"';const rows=["item,label,notes"].concat(ITEMS.map(z=>{const l=L[z.item]||{};return [z.item,q(l.label||""),q(l.notes||"")].join(",")}));
 const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([rows.join("\\n")+"\\n"],{type:"text/csv"}));a.download="hostility_labels_"+(coder||"anon")+".csv";a.click()};
document.addEventListener("keydown",e=>{if(e.target.tagName==="TEXTAREA"||e.target.tagName==="INPUT")return;if(e.key>="1"&&e.key<="4")set(CH[+e.key-1][0]);else if(e.key==="ArrowLeft")$("prev").onclick();else if(e.key==="ArrowRight")$("next").onclick();else if(e.key==="n"||e.key==="N"){e.preventDefault();$("notes").focus()}});
try{coder=localStorage.getItem("hostility_coder")||""}catch(_){}$("coder").value=coder;load();const first=ITEMS.findIndex(z=>!(L[z.item]&&L[z.item].label));i=first>=0?first:0;draw();
</script></body></html>"""
(ROOT / "label_hostility_sampleA.html").write_text(html.replace("__DATA__", data), encoding="utf-8")
print("wrote", ROOT / "label_hostility_sampleA.html", len(rows), "items")
