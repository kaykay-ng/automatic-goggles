"""Builds seedoils/check_papers.html: a local, offline page for checking the AI paper labels (paper_labels_*.csv) by hand, BLIND to them.
Sample (seed 21): 64 papers the AI marked relevant (yes/partly) + 16 it marked not relevant, all with an abstract, shuffled. Shown: title, year,
abstract (exactly the text the AI labelled from, papers_to_label.jsonl). Three choices per paper (codebook rebuilt 25 Nov from the label fields):
  RELEVANCE  Y yes: the paper is about the health effects of seed oils, linoleic acid (LA), omega-6 or polyunsaturated fat (PUFA)
             P partly: PUFA / LA is one of several things studied, or only a secondary outcome
             N no: not about these (e.g. only saturated fat vs carbohydrate, only omega-3 fish oil, LDL drugs)
  DIRECTION  (only if Y or P) what the paper concludes about eating MORE seed oil / LA / omega-6 / PUFA (or replacing saturated fat with it):
             H harm, B benefit, E no effect, M mixed (harm on some outcomes, benefit on others), U unclear from the abstract
  EVIDENCE   T human trial or meta-analysis of trials; O human observational (cohort, case-control, meta of those); R review or statement
             without new data; A animal or cell study; X other (e.g. methods, cross-sectional biomarker study)
Exports paper_checks_<initials>.csv -> seedoils/data/processed/; then paper_eval.py compares with the AI labels.
Key (item -> openalex id) in data/processed/paper_check_key.csv. The page holds abstracts, so it is gitignored.
Run from the repo root:  python3 seedoils/notebooks/make_paper_check_tool.py"""
import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; PROC = ROOT / "data" / "processed"; OUT = ROOT / "check_papers.html"
P = {json.loads(l)["openalex_id"]: json.loads(l) for l in open(PROC / "papers_to_label.jsonl", encoding="utf-8")}
L = {}
for fn in ("paper_labels_omega6.csv", "paper_labels_satfat_rodent.csv", "paper_labels_ldl.csv"):
    for r in csv.DictReader(open(PROC / fn, encoding="utf-8")):
        L[r["openalex_id"]] = r
has_abs = lambda k: bool((P.get(k, {}).get("abstract") or "").strip())  # noqa: E731
rel = sorted(k for k, r in L.items() if r["relevance"] in ("yes", "partly") and has_abs(k))
nrel = sorted(k for k, r in L.items() if r["relevance"] == "no" and has_abs(k))
rng = random.Random(21); pick = rng.sample(rel, 64) + rng.sample(nrel, 16); rng.shuffle(pick)
with open(PROC / "paper_check_key.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["item", "openalex_id"]); [w.writerow([i + 1, k]) for i, k in enumerate(pick)]
items = [{"item": i + 1, "title": P[k]["title"], "year": P[k].get("year", ""), "abstract": P[k]["abstract"]} for i, k in enumerate(pick)]
DATA = json.dumps(items, ensure_ascii=True).replace("</", "<\\/")
PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Paper Check</title>
<style>
:root { --bg:#f6f7f5; --card:#fff; --fg:#1c2120; --muted:#5d6763; --line:#dbe0dd; --on:#2b6cb0; --focus:#2b6cb0; --sans:Inter, system-ui, -apple-system, "Segoe UI", sans-serif; }
@media (prefers-color-scheme: dark) { :root { --bg:#151918; --card:#1d2220; --fg:#e8ece9; --muted:#9aa49f; --line:#2e3532; --on:#6ea8e6; --focus:#6ea8e6; color-scheme: dark; } }
body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.55 var(--sans); }
main { max-width:900px; margin:0 auto; padding:20px 16px 60px; display:grid; gap:14px; }
h1 { font-size:22px; margin:0; } .muted { color:var(--muted); font-size:13px; }
.bar { display:flex; flex-wrap:wrap; gap:8px 14px; align-items:center; }
.prog { flex:1 1 200px; height:6px; background:var(--line); border-radius:3px; overflow:hidden; } .prog i { display:block; height:100%; background:var(--focus); width:0; }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:16px; display:grid; gap:8px; }
.card h2 { font-size:17px; margin:0; line-height:1.35; } .abs { white-space:pre-wrap; font-size:15px; line-height:1.6; max-height:46vh; overflow:auto; }
.q { display:grid; gap:6px; } .q b { font-size:14px; } .opts { display:flex; flex-wrap:wrap; gap:6px; }
.opts button { border:2px solid var(--line); background:var(--card); color:var(--fg); border-radius:7px; padding:6px 10px; cursor:pointer; font:inherit; font-size:14px; }
.opts button.on { border-color:var(--on); font-weight:600; } .opts button:disabled { opacity:.35; cursor:default; }
button:focus-visible, input:focus-visible, textarea:focus-visible { outline:2px solid var(--focus); outline-offset:2px; }
.nav button, .tools button { border:1px solid var(--line); background:var(--card); color:var(--fg); border-radius:6px; padding:6px 12px; cursor:pointer; font:inherit; }
textarea { width:100%; box-sizing:border-box; min-height:40px; border:1px solid var(--line); border-radius:6px; background:var(--card); color:var(--fg); padding:6px 8px; font:inherit; }
input#who { width:90px; border:1px solid var(--line); border-radius:6px; padding:5px 8px; background:var(--card); color:var(--fg); font:inherit; }
details { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:10px 14px; } summary { cursor:pointer; font-weight:600; } details ul { margin:8px 0 0; padding-left:20px; }
#csv { font-family:ui-monospace, Menlo, monospace; font-size:12px; min-height:120px; }
</style></head><body><main>
<h1>Paper check</h1>
<p class="muted">80 cited papers, shown without the AI&rsquo;s labels. For each: is it about seed oils / linoleic acid / omega-6 / PUFA, what does it conclude, and what kind of evidence is it. Judge from the abstract only. Keys: relevance <b>Y P N</b>; conclusion <b>H B E M U</b>; evidence <b>T O R A X</b>; &larr; &rarr; to move. A paper is done when all needed choices are made.</p>
<div class="bar"><label for="who">Your initials (then press Enter)</label><input id="who" maxlength="6" placeholder="e.g. HC"><span id="count" class="muted"></span><div class="prog"><i id="pg"></i></div></div>
<details><summary>Codebook</summary><ul>
<li><b>Relevance.</b> Y: about the health effects of seed oils, linoleic acid, omega-6 or polyunsaturated fat. P: PUFA/LA is one of several things studied, or a secondary outcome. N: not about these (only saturated fat vs carbs, only omega-3 fish oil, LDL drugs, &hellip;).</li>
<li><b>Conclusion</b> (only if Y or P), about eating <i>more</i> seed oil / LA / omega-6 / PUFA, or replacing saturated fat with it: H harm, B benefit, E no effect, M mixed (harm on some outcomes, benefit on others), U unclear from the abstract.</li>
<li><b>Evidence.</b> T human trial or meta-analysis of trials; O human observational (cohort, case-control, meta-analysis of those); R review or statement without new data; A animal or cell study; X other.</li></ul></details>
<div class="card"><div class="muted" id="pos"></div><h2 id="title"></h2><div class="muted" id="year"></div><div class="abs" id="abs"></div></div>
<div class="q"><b>Relevant?</b><div class="opts" data-f="rel"><button data-v="Y">Y yes</button><button data-v="P">P partly</button><button data-v="N">N no</button></div></div>
<div class="q"><b>Conclusion about more seed oil / LA / PUFA</b><div class="opts" data-f="dir"><button data-v="H">H harm</button><button data-v="B">B benefit</button><button data-v="E">E no effect</button><button data-v="M">M mixed</button><button data-v="U">U unclear</button></div></div>
<div class="q"><b>Kind of evidence</b><div class="opts" data-f="ev"><button data-v="T">T trial / meta of trials</button><button data-v="O">O observational</button><button data-v="R">R review / statement</button><button data-v="A">A animal / cell</button><button data-v="X">X other</button></div></div>
<label for="note" class="muted">Note (optional)</label><textarea id="note"></textarea>
<div class="bar nav"><button id="prev">&larr; Previous</button><button id="next">Next &rarr;</button><button id="skip">Next unfinished</button></div>
<div class="bar tools"><button id="save">Save as CSV</button><button id="show">Show CSV to copy</button><span id="msg" class="muted"></span></div>
<textarea id="csv" hidden readonly></textarea>
</main>
<script>
const ITEMS = __DATA__;
let i = 0, who = "", L = {};
const $ = (id) => document.getElementById(id);
const key = () => "paper_checks_" + (who || "anon");
function load() { try { L = JSON.parse(localStorage.getItem(key()) || "{}"); } catch (e) { L = {}; } }
function store() { try { localStorage.setItem(key(), JSON.stringify(L)); } catch (e) { $("msg").textContent = "Could not save in this browser: export the CSV before closing."; } }
const done = (c) => c && c.rel && c.ev && (c.rel === "N" || c.dir);
function render() {
  const it = ITEMS[i], cur = L[it.item] || {};
  $("pos").textContent = "Paper " + (i + 1) + " of " + ITEMS.length; $("title").textContent = it.title; $("year").textContent = it.year; $("abs").textContent = it.abstract; $("abs").scrollTop = 0;
  document.querySelectorAll(".opts").forEach((o) => { const f = o.dataset.f; o.querySelectorAll("button").forEach((b) => { b.classList.toggle("on", cur[f] === b.dataset.v); b.disabled = f === "dir" && cur.rel === "N"; }); });
  $("note").value = cur.notes || "";
  const n = ITEMS.filter((x) => done(L[x.item])).length; $("count").textContent = n + " / " + ITEMS.length + " done"; $("pg").style.width = (100 * n / ITEMS.length) + "%";
}
function set(f, v) { const it = ITEMS[i]; const c = Object.assign({}, L[it.item], { [f]: v, notes: $("note").value }); if (f === "rel" && v === "N") c.dir = ""; L[it.item] = c; store(); render(); if (done(c)) setTimeout(() => go(1), 150); }
function go(d) { const it = ITEMS[i]; if (L[it.item]) { L[it.item].notes = $("note").value; store(); } i = Math.max(0, Math.min(ITEMS.length - 1, i + d)); render(); }
function csv() { const q = (s) => '"' + String(s || "").replace(/"/g, '""') + '"'; return "item,relevance,direction,evidence,notes,labeller\\n" + ITEMS.map((x) => { const c = L[x.item] || {}; return [x.item, c.rel || "", c.dir || "", c.ev || "", q(c.notes), who].join(","); }).join("\\n") + "\\n"; }
document.querySelectorAll(".opts").forEach((o) => o.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => set(o.dataset.f, b.dataset.v))));
$("prev").onclick = () => go(-1); $("next").onclick = () => go(1);
$("skip").onclick = () => { const j = ITEMS.findIndex((x, k) => k > i && !done(L[x.item])); const k2 = j >= 0 ? j : ITEMS.findIndex((x) => !done(L[x.item])); if (k2 >= 0) { i = k2; render(); } };
$("note").addEventListener("change", () => { const it = ITEMS[i]; L[it.item] = Object.assign({}, L[it.item], { notes: $("note").value }); store(); });
$("who").addEventListener("keydown", (ev) => { if (ev.key === "Enter") ev.target.blur(); });
$("who").addEventListener("change", () => { who = $("who").value.trim().toUpperCase(); try { localStorage.setItem("paper_labeller", who); } catch (e) {} load(); render(); });
$("save").onclick = () => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([csv()], { type: "text/csv" })); a.download = "paper_checks_" + (who || "anon") + ".csv"; document.body.appendChild(a); a.click(); a.remove(); $("msg").textContent = "Saved to your Downloads folder. Move it to seedoils/data/processed/."; };
$("show").onclick = () => { $("csv").hidden = !$("csv").hidden; $("csv").value = csv(); };
document.addEventListener("keydown", (ev) => {
  if (ev.target.tagName === "TEXTAREA" || ev.target.tagName === "INPUT") return;
  const k = ev.key.toUpperCase(), M = { Y: ["rel", "Y"], P: ["rel", "P"], N: ["rel", "N"], H: ["dir", "H"], B: ["dir", "B"], E: ["dir", "E"], M: ["dir", "M"], U: ["dir", "U"], T: ["ev", "T"], O: ["ev", "O"], R: ["ev", "R"], A: ["ev", "A"], X: ["ev", "X"] }[k];
  if (M) { if (M[0] === "dir" && (L[ITEMS[i].item] || {}).rel === "N") return; set(M[0], M[1]); ev.preventDefault(); } else if (ev.key === "ArrowRight") go(1); else if (ev.key === "ArrowLeft") go(-1);
});
try { who = localStorage.getItem("paper_labeller") || ""; } catch (e) {} $("who").value = who; load(); render();
</script></body></html>"""
OUT.write_text(PAGE.replace("__DATA__", DATA), encoding="utf-8")
print(f"wrote {OUT} ({len(items)} papers: 64 AI-relevant + 16 AI-not-relevant, shuffled) and data/processed/paper_check_key.csv")
