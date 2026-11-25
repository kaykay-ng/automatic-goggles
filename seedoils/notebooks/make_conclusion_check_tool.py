"""Builds seedoils/check_conclusions.html: a local, offline page for a NON-EXPERT check of the AI's paper conclusions (decision 25 Nov: the full
paper check asked for domain judgement; this one only asks what the abstract's own conclusion says). BLIND to the AI labels.
Sample (seed 22): 40 papers the AI marked relevant (yes/partly), with an abstract. Shown: title, year, the conclusion sentences highlighted
(conclusion_extract.py: structured CONCLUSION section, else a cue such as 'In conclusion' / 'These results suggest', else the last two sentences),
and the full abstract one click away (the same text the AI labelled from, papers_to_label.jsonl).
One choice: what does the paper conclude about eating MORE seed oil / linoleic acid / omega-6 / PUFA (or replacing saturated fat with it)?
  H harm   B benefit   E no effect   M mixed (harm on some outcomes, benefit on others)   U unclear / not about this
Exports conclusion_checks_<initials>.csv -> seedoils/data/processed/; conclusion_eval.py compares with the AI. Key: conclusion_check_key.csv.
The page holds abstracts, so it is gitignored. Run from the repo root:  python3 seedoils/notebooks/make_conclusion_check_tool.py"""
import csv
import html
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from conclusion_extract import conclusion  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]; PROC = ROOT / "data" / "processed"; OUT = ROOT / "check_conclusions.html"
P = {json.loads(l)["openalex_id"]: json.loads(l) for l in open(PROC / "papers_to_label.jsonl", encoding="utf-8")}
L = {}
for fn in ("paper_labels_omega6.csv", "paper_labels_satfat_rodent.csv", "paper_labels_ldl.csv"):
    for r in csv.DictReader(open(PROC / fn, encoding="utf-8")):
        L[r["openalex_id"]] = r
rel = sorted(k for k, r in L.items() if r["relevance"] in ("yes", "partly") and (P.get(k, {}).get("abstract") or "").strip())
pick = random.Random(22).sample(rel, 40)
with open(PROC / "conclusion_check_key.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["item", "openalex_id", "conclusion_rule"])
    items = []
    for i, k in enumerate(pick):
        ab = html.unescape(P[k]["abstract"]); con, rule = conclusion(ab); w.writerow([i + 1, k, rule])
        items.append({"item": i + 1, "title": html.unescape(P[k]["title"]), "year": P[k].get("year", ""), "con": con, "abs": ab})
DATA = json.dumps(items, ensure_ascii=True).replace("</", "<\\/")
PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Conclusion Check</title>
<style>
:root { --bg:#f6f7f5; --card:#fff; --fg:#1c2120; --muted:#5d6763; --line:#dbe0dd; --hl:#fff4c2; --on:#2b6cb0; --focus:#2b6cb0; --sans:Inter, system-ui, -apple-system, "Segoe UI", sans-serif; }
@media (prefers-color-scheme: dark) { :root { --bg:#151918; --card:#1d2220; --fg:#e8ece9; --muted:#9aa49f; --line:#2e3532; --hl:#3d3512; --on:#6ea8e6; --focus:#6ea8e6; color-scheme: dark; } }
body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.55 var(--sans); }
main { max-width:860px; margin:0 auto; padding:20px 16px 60px; display:grid; gap:14px; }
h1 { font-size:22px; margin:0; } .muted { color:var(--muted); font-size:13px; }
.bar { display:flex; flex-wrap:wrap; gap:8px 14px; align-items:center; }
.prog { flex:1 1 200px; height:6px; background:var(--line); border-radius:3px; overflow:hidden; } .prog i { display:block; height:100%; background:var(--focus); width:0; }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:16px; display:grid; gap:10px; }
.card h2 { font-size:17px; margin:0; line-height:1.35; }
.con { background:var(--hl); border-radius:6px; padding:10px 12px; font-size:16.5px; line-height:1.6; }
details.full summary { cursor:pointer; color:var(--muted); font-size:13px; } details.full div { white-space:pre-wrap; font-size:14px; line-height:1.55; margin-top:6px; max-height:40vh; overflow:auto; }
.keys { display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:8px; }
button.lab { text-align:left; border:2px solid var(--line); background:var(--card); color:var(--fg); border-radius:8px; padding:9px 12px; cursor:pointer; font:inherit; }
button.lab small { display:block; color:var(--muted); font-size:12.5px; } button.lab.on { border-color:var(--on); font-weight:600; }
button:focus-visible, input:focus-visible, textarea:focus-visible { outline:2px solid var(--focus); outline-offset:2px; }
.nav button, .tools button { border:1px solid var(--line); background:var(--card); color:var(--fg); border-radius:6px; padding:6px 12px; cursor:pointer; font:inherit; }
textarea { width:100%; box-sizing:border-box; min-height:40px; border:1px solid var(--line); border-radius:6px; background:var(--card); color:var(--fg); padding:6px 8px; font:inherit; }
input#who { width:90px; border:1px solid var(--line); border-radius:6px; padding:5px 8px; background:var(--card); color:var(--fg); font:inherit; }
#csv { font-family:ui-monospace, Menlo, monospace; font-size:12px; min-height:120px; }
</style></head><body><main>
<h1>Conclusion check</h1>
<p class="muted">40 papers that Reddit users cite. Read the highlighted conclusion (open the full abstract if it is not clear) and say what the paper itself concludes about eating <b>more</b> seed oil, linoleic acid, omega-6 or polyunsaturated fat, or about replacing saturated fat with it. You are not judging whether the paper is right, only what it says. Keys <b>H B E M U</b> (or 1&ndash;5); &larr; &rarr; to move.</p>
<div class="bar"><label for="who">Your initials (then press Enter)</label><input id="who" maxlength="6" placeholder="e.g. HC"><span id="count" class="muted"></span><div class="prog"><i id="pg"></i></div></div>
<div class="card"><div class="muted" id="pos"></div><h2 id="title"></h2><div class="con" id="con"></div><details class="full"><summary>Show the full abstract</summary><div id="abs"></div></details></div>
<div class="keys">
<button class="lab" data-l="H"><b>H</b> Harm<small>more of it is bad for health</small></button>
<button class="lab" data-l="B"><b>B</b> Benefit<small>more of it is good, or better than saturated fat</small></button>
<button class="lab" data-l="E"><b>E</b> No effect<small>no difference found</small></button>
<button class="lab" data-l="M"><b>M</b> Mixed<small>bad on some outcomes, good on others</small></button>
<button class="lab" data-l="U"><b>U</b> Unclear<small>can&rsquo;t tell, or not about this</small></button></div>
<label for="note" class="muted">Note (optional)</label><textarea id="note"></textarea>
<div class="bar nav"><button id="prev">&larr; Previous</button><button id="next">Next &rarr;</button></div>
<div class="bar tools"><button id="save">Save as CSV</button><button id="show">Show CSV to copy</button><span id="msg" class="muted"></span></div>
<textarea id="csv" hidden readonly></textarea>
</main>
<script>
const ITEMS = __DATA__;
let i = 0, who = "", L = {};
const $ = (id) => document.getElementById(id);
const key = () => "conclusion_checks_" + (who || "anon");
function load() { try { L = JSON.parse(localStorage.getItem(key()) || "{}"); } catch (e) { L = {}; } }
function store() { try { localStorage.setItem(key(), JSON.stringify(L)); } catch (e) { $("msg").textContent = "Could not save in this browser: export the CSV before closing."; } }
function render() {
  const it = ITEMS[i], cur = L[it.item] || {};
  $("pos").textContent = "Paper " + (i + 1) + " of " + ITEMS.length + (it.year ? " (" + it.year + ")" : ""); $("title").textContent = it.title; $("con").textContent = it.con; $("abs").textContent = it.abs;
  document.querySelector("details.full").open = false; $("note").value = cur.notes || "";
  document.querySelectorAll(".lab").forEach((b) => b.classList.toggle("on", b.dataset.l === cur.label));
  const n = ITEMS.filter((x) => L[x.item] && L[x.item].label).length; $("count").textContent = n + " / " + ITEMS.length + " done"; $("pg").style.width = (100 * n / ITEMS.length) + "%";
}
function setLabel(l) { const it = ITEMS[i]; L[it.item] = Object.assign({}, L[it.item], { label: l, notes: $("note").value }); store(); render(); setTimeout(() => go(1), 150); }
function go(d) { const it = ITEMS[i]; if (L[it.item]) { L[it.item].notes = $("note").value; store(); } i = Math.max(0, Math.min(ITEMS.length - 1, i + d)); render(); }
function csv() { const q = (s) => '"' + String(s || "").replace(/"/g, '""') + '"'; return "item,label,notes,labeller\\n" + ITEMS.map((x) => [x.item, (L[x.item] || {}).label || "", q((L[x.item] || {}).notes), who].join(",")).join("\\n") + "\\n"; }
document.querySelectorAll(".lab").forEach((b) => b.addEventListener("click", () => setLabel(b.dataset.l)));
$("prev").onclick = () => go(-1); $("next").onclick = () => go(1);
$("note").addEventListener("change", () => { const it = ITEMS[i]; L[it.item] = Object.assign({}, L[it.item], { notes: $("note").value }); store(); });
$("who").addEventListener("keydown", (ev) => { if (ev.key === "Enter") ev.target.blur(); });
$("who").addEventListener("change", () => { who = $("who").value.trim().toUpperCase(); try { localStorage.setItem("conclusion_labeller", who); } catch (e) {} load(); render(); });
$("save").onclick = () => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([csv()], { type: "text/csv" })); a.download = "conclusion_checks_" + (who || "anon") + ".csv"; document.body.appendChild(a); a.click(); a.remove(); $("msg").textContent = "Saved to your Downloads folder. Move it to seedoils/data/processed/."; };
$("show").onclick = () => { $("csv").hidden = !$("csv").hidden; $("csv").value = csv(); };
document.addEventListener("keydown", (ev) => {
  if (ev.target.tagName === "TEXTAREA" || ev.target.tagName === "INPUT") return;
  const m = { h: "H", b: "B", e: "E", m: "M", u: "U", 1: "H", 2: "B", 3: "E", 4: "M", 5: "U" }[ev.key.toLowerCase()];
  if (m) { setLabel(m); ev.preventDefault(); } else if (ev.key === "ArrowRight") go(1); else if (ev.key === "ArrowLeft") go(-1);
});
try { who = localStorage.getItem("conclusion_labeller") || ""; } catch (e) {} $("who").value = who; load(); render();
</script></body></html>"""
OUT.write_text(PAGE.replace("__DATA__", DATA), encoding="utf-8")
print(f"wrote {OUT} ({len(items)} papers) and data/processed/conclusion_check_key.csv")
