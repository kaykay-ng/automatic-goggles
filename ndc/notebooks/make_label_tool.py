"""Builds ndc/label_passages.html: a local, offline page for hand-labelling the cutoff sheet (no server, nothing uploaded).
Run from final_project/:  ./.venv-nlp/bin/python ndc/notebooks/make_label_tool.py
Reads ndc/data/processed/cutoff_labelling_sheet.csv (passages only, NO scores). The page exports cutoff_labelling_sheet_labelled.csv (columns id,country,text,label,note).
"""
import json
from pathlib import Path
import pandas as pd

S = pd.read_csv(Path("ndc/data/processed/cutoff_labelling_sheet.csv"))
data = [dict(id=int(r.id), country=str(r.country), text=str(r.text)) for r in S.itertuples()]
payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Label climate passages</title>
<style>
:root{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--line:#e1e0d9;--card:#ffffff;--yes:#1f6fd0;--no:#c8501f;--unsure:#6b6a66}
@media (prefers-color-scheme:dark){:root{--bg:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--line:#383835;--card:#232322;--yes:#5598e7;--no:#e8845a;--unsure:#a5a49d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
main{max-width:760px;margin:0 auto;padding:20px 16px 60px}
h1{font-size:19px;margin:0 0 4px}
.rubric{color:var(--ink2);font-size:15px;border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin:10px 0 16px;background:var(--card)}
.rubric b{color:var(--ink)}
.bar{height:6px;background:var(--line);border-radius:3px;overflow:hidden;margin:6px 0 4px}.bar>i{display:block;height:100%;background:var(--yes);width:0}
.meta{display:flex;justify-content:space-between;color:var(--ink2);font-size:14px}
.card{border:1px solid var(--line);border-radius:12px;background:var(--card);padding:18px 20px;margin:12px 0;font-size:18px;min-height:150px;white-space:pre-wrap}
.btns{display:flex;gap:10px;flex-wrap:wrap}
button{font:inherit;font-weight:600;border:2px solid var(--line);background:var(--card);color:var(--ink);border-radius:10px;padding:10px 18px;cursor:pointer;flex:1;min-width:130px}
button kbd{font-weight:400;color:var(--ink2);margin-left:6px;font-size:13px}
button.yes{border-color:var(--yes)}button.no{border-color:var(--no)}button.unsure{border-color:var(--unsure)}
button.sel.yes{background:var(--yes);color:#fff}button.sel.no{background:var(--no);color:#fff}button.sel.unsure{background:var(--unsure);color:#fff}
button.sel kbd{color:inherit}
button.small{flex:0 0 auto;min-width:0;font-weight:400;padding:7px 14px;white-space:nowrap}
.row{display:flex;gap:10px;align-items:center;margin:14px 0;flex-wrap:wrap}
input[type=text]{flex:1;font:inherit;font-size:15px;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);min-width:150px}
.summary{color:var(--ink2);font-size:15px}
.hint{color:var(--ink2);font-size:14px;margin-top:18px}
</style></head><body><main>
<h1>Label climate passages</h1>
<div class="rubric"><b>1 = climate</b>: the passage is about climate change, greenhouse-gas emissions or climate policy.<br>
<b>0 = not</b>: it is not (e.g. "business climate", "political climate", "carbon" in another sense).<br>
<b>? = unsure</b>: you cannot tell from the passage (counted as 0).</div>
<div class="meta"><span id="pos"></span><span id="done"></span></div><div class="bar"><i id="fill"></i></div>
<div class="card" id="text"></div>
<div class="btns">
<button class="yes" id="b1">1 &nbsp;Climate<kbd>key 1</kbd></button>
<button class="no" id="b0">0 &nbsp;Not climate<kbd>key 0</kbd></button>
<button class="unsure" id="bq">? &nbsp;Unsure<kbd>key ?</kbd></button></div>
<div class="row"><input type="text" id="note" placeholder="Optional note about this passage"><button class="small" id="prev">&larr; Back</button><button class="small" id="next">Skip &rarr;</button></div>
<div class="row"><button class="small" id="dl">Download CSV</button><span class="summary" id="sum"></span></div>
<div class="hint">Keys: 1, 0, ? (or u) to label and move on &middot; left/right arrows to move without labelling. Your answers are saved in this browser as you go, so you can close the page and come back.
When you are done, click Download CSV and move the file into <code>final_project/ndc/data/processed/</code> (name it <code>cutoff_labelling_sheet_labelled.csv</code>).</div>
</main>
<script>
const DATA = __DATA__;
const KEY = "cutoff_labels_v1";
let L = {}, N = {}, i = 0;
try { const s = JSON.parse(localStorage.getItem(KEY) || "{}"); L = s.L || {}; N = s.N || {}; i = s.i || 0; } catch (e) {}
function save() { try { localStorage.setItem(KEY, JSON.stringify({L: L, N: N, i: i})); } catch (e) {} }
const $ = id => document.getElementById(id);
function render() {
  const d = DATA[i]; $("text").textContent = d.text; $("pos").textContent = "Passage " + (i + 1) + " of " + DATA.length + "  (" + d.country + ")";
  const n = Object.keys(L).length; $("done").textContent = n + " labelled"; $("fill").style.width = (100 * n / DATA.length) + "%";
  for (const [b, v] of [["b1", "1"], ["b0", "0"], ["bq", "?"]]) $(b).classList.toggle("sel", L[d.id] === v);
  $("note").value = N[d.id] || "";
  const c = {"1": 0, "0": 0, "?": 0}; Object.values(L).forEach(v => c[v]++);
  $("sum").textContent = "climate " + c["1"] + " · not " + c["0"] + " · unsure " + c["?"] + " · left " + (DATA.length - n);
}
function setLabel(v) { const d = DATA[i]; N[d.id] = $("note").value; L[d.id] = v; if (i < DATA.length - 1) i++; save(); render(); }
function go(k) { const d = DATA[i]; N[d.id] = $("note").value; i = Math.max(0, Math.min(DATA.length - 1, i + k)); save(); render(); }
$("b1").onclick = () => setLabel("1"); $("b0").onclick = () => setLabel("0"); $("bq").onclick = () => setLabel("?");
$("prev").onclick = () => go(-1); $("next").onclick = () => go(1);
document.addEventListener("keydown", e => {
  if (e.target.id === "note") return;
  if (e.key === "1") setLabel("1"); else if (e.key === "0") setLabel("0"); else if (e.key === "?" || e.key === "u" || e.key === "/") setLabel("?");
  else if (e.key === "ArrowLeft") go(-1); else if (e.key === "ArrowRight") go(1);
});
function q(s) { return '"' + String(s).replace(/"/g, '""') + '"'; }
$("dl").onclick = () => {
  const d = DATA[i]; N[d.id] = $("note").value; save();
  const left = DATA.length - Object.keys(L).length;
  if (left > 0 && !confirm(left + " passages are still unlabelled. Download anyway?")) return;
  const rows = ["id,country,text,label,note"].concat(DATA.map(x => [x.id, x.country, q(x.text), L[x.id] === undefined ? "" : L[x.id], q(N[x.id] || "")].join(",")));
  const blob = new Blob([rows.join("\n") + "\n"], {type: "text/csv;charset=utf-8"}); const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = "cutoff_labelling_sheet_labelled.csv"; document.body.appendChild(a); a.click(); a.remove();
};
render();
</script></body></html>"""
out = Path("ndc/label_passages.html"); out.write_text(HTML.replace("__DATA__", payload), encoding="utf-8")
print("wrote", out, f"({out.stat().st_size // 1024} KB, {len(data)} passages)")
