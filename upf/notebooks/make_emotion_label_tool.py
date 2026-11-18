"""C4 of the emotion pilot (upf/PLAN.md): builds upf/label_emotions.html, a local offline page for hand-labelling 100 reviews (no server, nothing uploaded).
Draw: 20 reviews per star level (1-5) from the same 20,000 pilot reviews, shown in random order, WITHOUT stars and WITHOUT any model or lexicon score (blind).
Run from final_project/ with the NLP env:  ./.venv-nlp/bin/python upf/notebooks/make_emotion_label_tool.py
The page exports emotion_labels.csv (columns id, text, one 0/1 column per emotion, none, note); move it to upf/data/processed/soj/.
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import emotion_pilot as EP

GOSET = len(sys.argv) > 1 and sys.argv[1] == "go"                 # 'go' = the fresh GoEmotions label set (upf/PLAN.md 'GOEMOTIONS PILOT')
S = EP.sample(); S["id"] = np.arange(len(S))                     # id = row in soj/emotion_pilot.csv.gz
pil = pd.read_csv(EP.H.CACHE / "emotion_pilot.csv.gz", usecols=["stars"]); assert (pil.stars.values == S.stars.values).all()
if GOSET: S = S[~S.id.isin(pd.read_csv(EP.H.CACHE / "emotion_label_ids.csv").id)]   # exclude the 100 C4 reviews
D = pd.concat([S[S.stars == s].sample(20, random_state=21 if GOSET else 11) for s in (1, 2, 3, 4, 5)]).sample(frac=1, random_state=22 if GOSET else 12)
D[["id", "stars"]].to_csv(EP.H.CACHE / ("go_label_ids.csv" if GOSET else "emotion_label_ids.csv"), index=False)  # key kept apart from the page
data = [dict(id=int(r.id), text=str(r.text)[:2500]) for r in D.itertuples()]
payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
EMO_GO = [("admiration", "1", "praise for the product, 'excellent', 'best I've had'"), ("approval", "2", "okay / acceptable, agrees it does the job, 'good value'"),
          ("gratitude", "3", "thanks, grateful, 'glad I found this'"), ("joy", "4", "happy, delighted, pleased (the writer's feeling)"),
          ("love", "5", "affection, 'I love these', 'my kids adore it'"), ("excitement", "6", "eager, thrilled, can't wait"),
          ("disappointment", "7", "let down, expected better, 'not as described'"), ("annoyance", "8", "irritated, mildly bothered, 'annoying'"),
          ("anger", "9", "strong anger, outraged, furious"), ("disgust", "0", "revolted, gross, 'tastes awful', 'moldy'"),
          ("sadness", "-", "sad, unhappy, sorrowful"), ("surprise", "=", "unexpected, astonished (good or bad)")]
EMO = [("joy", "1", "happy, pleased, delighted, satisfied"), ("love", "2", "affection, adoring it, 'I love these'"),
       ("optimism", "3", "hopeful, expects good things, 'will buy again'"), ("trust", "4", "confidence in the product or seller, reliable, recommends"),
       ("anticipation", "5", "looking forward to something, eager"), ("surprise", "6", "unexpected, astonished (good or bad)"),
       ("anger", "7", "annoyed, irritated, outraged"), ("disgust", "8", "revolted, gross, 'tastes awful', repelled"),
       ("sadness", "9", "disappointed, let down, unhappy"), ("fear", "0", "worried, afraid, anxious (e.g. about safety, allergies)"),
       ("pessimism", "-", "expects bad things, 'won't buy again', gives up")]

HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Label review emotions</title>
<style>
:root{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--line:#e1e0d9;--card:#ffffff;--on:#1f6fd0;--none:#6b6a66}
@media (prefers-color-scheme:dark){:root{--bg:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--line:#383835;--card:#232322;--on:#5598e7;--none:#a5a49d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
main{max-width:820px;margin:0 auto;padding:20px 16px 60px}
h1{font-size:19px;margin:0 0 4px}
.rubric{color:var(--ink2);font-size:14.5px;border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin:10px 0 16px;background:var(--card)}
.rubric b{color:var(--ink)}
.bar{height:6px;background:var(--line);border-radius:3px;overflow:hidden;margin:6px 0 4px}.bar>i{display:block;height:100%;background:var(--on);width:0}
.meta{display:flex;justify-content:space-between;color:var(--ink2);font-size:14px}
.card{border:1px solid var(--line);border-radius:12px;background:var(--card);padding:18px 20px;margin:12px 0;font-size:18px;min-height:130px;white-space:pre-wrap;overflow-wrap:anywhere}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px}
button{font:inherit;font-size:15.5px;border:2px solid var(--line);background:var(--card);color:var(--ink);border-radius:10px;padding:8px 12px;cursor:pointer;text-align:left}
button kbd{float:right;font-size:12.5px;color:var(--ink2);font-family:inherit}
button[aria-pressed=true]{background:var(--on);border-color:var(--on);color:#fff}button[aria-pressed=true] kbd{color:#fff}
button.none[aria-pressed=true]{background:var(--none);border-color:var(--none)}
button.small{padding:7px 14px;white-space:nowrap;text-align:center}
button.primary{border-color:var(--on);font-weight:600}
.row{display:flex;gap:10px;align-items:center;margin:14px 0;flex-wrap:wrap}
input[type=text]{flex:1;font:inherit;font-size:15px;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);min-width:150px}
.summary{color:var(--ink2);font-size:14px}
.hint{color:var(--ink2);font-size:14px;margin-top:18px}
</style></head><body><main>
<h1>Label review emotions</h1>
<div class="rubric">Tick <b>every emotion the reviewer expresses</b> (several are fine). Judge the writer's feeling from the text alone, not what you think of the product.
If the review is purely factual, tick <b>None</b>. Stars are hidden on purpose.<br>__RUBRIC__</div>
<div class="meta"><span id="pos"></span><span id="done"></span></div><div class="bar"><i id="fill"></i></div>
<div class="card" id="text"></div>
<div class="grid" id="grid"></div>
<div class="row"><button class="small primary" id="next">Save &amp; next &rarr; <kbd>Enter</kbd></button><button class="small" id="prev">&larr; Back</button>
<input type="text" id="note" placeholder="Optional note (sarcasm, mixed, not English...)"></div>
<div class="row"><button class="small" id="dl">Download CSV</button><span class="summary" id="sum"></span></div>
<div class="hint">Keys: the key shown on each emotion toggles it, n toggles None, Enter saves and moves on, left/right arrows move. Answers are saved in this browser as you go, so you can close the page and come back.
A review counts as labelled once you press Save &amp; next with at least one box ticked. When you are done, click Download CSV and move <code>emotion_labels.csv</code> into <code>final_project/upf/data/processed/soj/</code>.</div>
</main>
<script>
const DATA = __DATA__, EMO = __EMO__;
const KEY = "review_emotion_labels_v1";
let L = {}, N = {}, i = 0, cur = new Set();
try { const s = JSON.parse(localStorage.getItem(KEY) || "{}"); L = s.L || {}; N = s.N || {}; i = s.i || 0; } catch (e) {}
function save() { try { localStorage.setItem(KEY, JSON.stringify({L: L, N: N, i: i})); } catch (e) {} }
const $ = id => document.getElementById(id), grid = $("grid");
for (const [e, k] of EMO) { const b = document.createElement("button"); b.id = "e_" + e; b.innerHTML = e + "<kbd>" + k + "</kbd>"; b.onclick = () => toggle(e); grid.appendChild(b); }
{ const b = document.createElement("button"); b.id = "e_none"; b.className = "none"; b.innerHTML = "None (factual)<kbd>n</kbd>"; b.onclick = () => toggle("none"); grid.appendChild(b); }
function toggle(e) {
  if (e === "none") { cur = cur.has("none") ? new Set() : new Set(["none"]); } else { cur.delete("none"); cur.has(e) ? cur.delete(e) : cur.add(e); }
  paint();
}
function paint() { for (const [e] of EMO.concat([["none"]])) $("e_" + e).setAttribute("aria-pressed", cur.has(e)); }
function render() {
  const d = DATA[i]; $("text").textContent = d.text; $("pos").textContent = "Review " + (i + 1) + " of " + DATA.length;
  const n = Object.keys(L).length; $("done").textContent = n + " labelled"; $("fill").style.width = (100 * n / DATA.length) + "%";
  cur = new Set(L[d.id] || []); paint(); $("note").value = N[d.id] || "";
  $("sum").textContent = (DATA.length - n) + " left";
}
function keep() { const d = DATA[i]; N[d.id] = $("note").value; if (cur.size) L[d.id] = [...cur]; }
function next() { if (!cur.size) { alert("Tick at least one emotion, or None."); return; } keep(); if (i < DATA.length - 1) i++; save(); render(); }
function go(k) { keep(); i = Math.max(0, Math.min(DATA.length - 1, i + k)); save(); render(); }
$("next").onclick = next; $("prev").onclick = () => go(-1);
document.addEventListener("keydown", e => {
  if (e.target.id === "note") { if (e.key === "Enter") next(); return; }
  const hit = EMO.find(x => x[1] === e.key);
  if (hit) toggle(hit[0]); else if (e.key === "n") toggle("none"); else if (e.key === "Enter") { e.preventDefault(); next(); }
  else if (e.key === "ArrowLeft") go(-1); else if (e.key === "ArrowRight") go(1);
});
function q(s) { return '"' + String(s).replace(/"/g, '""') + '"'; }
$("dl").onclick = () => {
  keep(); save(); const left = DATA.length - Object.keys(L).length;
  if (left > 0 && !confirm(left + " reviews are still unlabelled. Download anyway?")) return;
  const cols = EMO.map(x => x[0]).concat(["none"]);
  const rows = [["id", "text"].concat(cols, ["note"]).join(",")].concat(DATA.map(x => [x.id, q(x.text)].concat(cols.map(c => L[x.id] ? +L[x.id].includes(c) : ""), [q(N[x.id] || "")]).join(",")));
  const blob = new Blob([rows.join("\n") + "\n"], {type: "text/csv;charset=utf-8"}); const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = "emotion_labels.csv"; document.body.appendChild(a); a.click(); a.remove();
};
render();
</script></body></html>"""
if GOSET:
    EMO = EMO_GO
    HTML = HTML.replace("emotion_labels.csv", "go_labels.csv").replace("review_emotion_labels_v1", "go_labels_v1").replace("<h1>Label review emotions</h1>", "<h1>Label review emotions (set 2)</h1>")
rub = "<br>".join(f"<b>{e}</b> ({k}): {d}" for e, k, d in EMO)
out = Path("upf/label_emotions_set2.html" if GOSET else "upf/label_emotions.html")
out.write_text(HTML.replace("__DATA__", payload).replace("__EMO__", json.dumps([[e, k] for e, k, _ in EMO])).replace("__RUBRIC__", rub), encoding="utf-8")
print("wrote", out, f"({out.stat().st_size // 1024} KB, {len(data)} reviews; star mix", D.stars.value_counts().sort_index().to_dict(), ")")
