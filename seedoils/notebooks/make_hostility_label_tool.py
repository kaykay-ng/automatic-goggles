"""Builds seedoils/label_hostility.html: a local, offline page for hand-labelling the 150 blind hostility items (nothing is uploaded).
Input: seedoils/data/processed/hostility_sample_to_label.csv (from hostility_robustness.py; 30 comments per GoEmotions score band, shuffled).
The score band stays in hostility_sample_key.csv and is NOT in the page: label blind.
The page keeps progress in the browser per labeller (localStorage) and exports hostility_labels_<initials>.csv (item, label, notes);
move that file to seedoils/data/processed/ and run hostility_eval.py. The page holds Reddit text, so it is gitignored.

Codebook (one label per comment):
  H  Hostile toward a person or group: insults, name-calling, mockery, contempt, sarcasm aimed at someone, calling people shills/idiots,
     dehumanising, wishing harm. The target is another commenter, a named person, or a group of people (vegans, doctors, 'seed-oil apologists').
  C  Critical but civil: disagrees, complains, or criticises ideas, studies, products, companies or institutions, even strongly
     ('this study is junk', 'the FDA is corrupt', 'canola is poison'), without attacking people.
  N  Neither: neutral, informational, a question, agreement, thanks, positive.
  U  Can't tell: needs missing context, sarcasm you cannot read, not English.
Rules: swearing alone is not H ('this shit works'); criticising an institution is C unless it shows contempt for the people in it ('doctors are
idiots' = H); if any part of the comment is hostile toward a person or group, the whole comment is H; label the commenter's own words, not a quote.
Run from the repo root:  python3 seedoils/notebooks/make_hostility_label_tool.py   then open seedoils/label_hostility.html in a browser."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "data" / "processed" / "hostility_sample_to_label.csv", ROOT / "label_hostility.html"
items = [{"item": int(r["item"]), "text": r["text"]} for r in csv.DictReader(open(SRC, encoding="utf-8"))]
items.sort(key=lambda x: x["item"])
DATA = json.dumps(items, ensure_ascii=True).replace("</", "<\\/")

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hostility Labels</title>
<style>
:root { --bg:#f6f7f5; --card:#fff; --fg:#1c2120; --muted:#5d6763; --line:#dbe0dd; --H:#b42318; --C:#b7791f; --N:#2f6f4f; --U:#6b6f7a; --focus:#2b6cb0;
  --sans:Inter, system-ui, -apple-system, "Segoe UI", sans-serif; }
@media (prefers-color-scheme: dark) { :root { --bg:#151918; --card:#1d2220; --fg:#e8ece9; --muted:#9aa49f; --line:#2e3532; --H:#f0796d; --C:#e2b04a; --N:#6cc191; --U:#a3a7b2; --focus:#6ea8e6; color-scheme: dark; } }
body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.55 var(--sans); }
main { max-width:860px; margin:0 auto; padding:20px max(16px, env(safe-area-inset-left)) 60px; display:grid; gap:16px; }
h1 { font-size:22px; margin:0; } .muted { color:var(--muted); font-size:13px; }
.bar { display:flex; flex-wrap:wrap; gap:8px 14px; align-items:center; }
.prog { flex:1 1 200px; height:6px; background:var(--line); border-radius:3px; overflow:hidden; } .prog i { display:block; height:100%; background:var(--focus); width:0; }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:18px; }
.text { white-space:pre-wrap; font-size:16px; line-height:1.6; max-height:50vh; overflow:auto; }
.keys { display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:8px; }
button.lab { text-align:left; border:2px solid var(--line); background:var(--card); color:var(--fg); border-radius:8px; padding:10px 12px; cursor:pointer; font:inherit; }
button.lab b { display:inline-block; min-width:22px; } button.lab small { display:block; color:var(--muted); font-size:12.5px; }
button.lab.on[data-l="H"] { border-color:var(--H); } button.lab.on[data-l="C"] { border-color:var(--C); } button.lab.on[data-l="N"] { border-color:var(--N); } button.lab.on[data-l="U"] { border-color:var(--U); }
button.lab.on { box-shadow:0 0 0 2px var(--line) inset; font-weight:600; }
button, input, textarea { font:inherit; } button:focus-visible, input:focus-visible, textarea:focus-visible { outline:2px solid var(--focus); outline-offset:2px; }
.nav button, .tools button { border:1px solid var(--line); background:var(--card); color:var(--fg); border-radius:6px; padding:6px 12px; cursor:pointer; }
textarea { width:100%; box-sizing:border-box; min-height:44px; border:1px solid var(--line); border-radius:6px; background:var(--card); color:var(--fg); padding:6px 8px; }
input#who { width:90px; border:1px solid var(--line); border-radius:6px; padding:5px 8px; background:var(--card); color:var(--fg); }
details { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:10px 14px; } summary { cursor:pointer; font-weight:600; }
details ul { margin:8px 0 0; padding-left:20px; } #csv { width:100%; min-height:120px; font-family:ui-monospace, Menlo, monospace; font-size:12px; }
</style></head><body><main>
<h1>Hostility labels</h1>
<p class="muted">150 comments from r/StopEatingSeedOils, shown without the model&rsquo;s score. Pick one label per comment. Keys: <b>H</b>, <b>C</b>, <b>N</b>, <b>U</b> (or 1&ndash;4); &larr; &rarr; to move. Progress is saved in this browser under your initials.</p>
<div class="bar"><label for="who">Your initials (then press Enter)</label><input id="who" maxlength="6" placeholder="e.g. HC"><span id="count" class="muted"></span><div class="prog"><i id="pg"></i></div></div>
<details open><summary>Codebook</summary><ul>
<li><b>H &mdash; Hostile toward a person or group.</b> Insults, name-calling, mockery, contempt, sarcasm aimed at someone, calling people shills or idiots, dehumanising, wishing harm. The target is another commenter, a named person, or a group of people (vegans, doctors, &ldquo;seed-oil apologists&rdquo;).</li>
<li><b>C &mdash; Critical but civil.</b> Disagrees, complains, or criticises ideas, studies, products, companies or institutions, even strongly (&ldquo;this study is junk&rdquo;, &ldquo;the FDA is corrupt&rdquo;, &ldquo;canola is poison&rdquo;), without attacking people.</li>
<li><b>N &mdash; Neither.</b> Neutral, informational, a question, agreement, thanks, positive.</li>
<li><b>U &mdash; Can&rsquo;t tell.</b> Needs missing context, sarcasm you can&rsquo;t read, not English.</li>
<li>Swearing alone is not H (&ldquo;this shit works&rdquo;). Criticising an institution is C unless it shows contempt for the people in it (&ldquo;doctors are idiots&rdquo; = H). If any part is hostile toward a person or group, the comment is H. Label the commenter&rsquo;s own words, not something they quote.</li></ul></details>
<div class="card"><div class="muted" id="pos"></div><div class="text" id="text"></div></div>
<div class="keys">
<button class="lab" data-l="H"><b>H</b> Hostile to a person or group<small>insult, mockery, contempt</small></button>
<button class="lab" data-l="C"><b>C</b> Critical but civil<small>disagrees or criticises ideas, products, institutions</small></button>
<button class="lab" data-l="N"><b>N</b> Neither<small>neutral, informational, question, positive</small></button>
<button class="lab" data-l="U"><b>U</b> Can&rsquo;t tell<small>missing context, unreadable sarcasm</small></button></div>
<label for="note" class="muted">Note (optional)</label><textarea id="note"></textarea>
<div class="bar nav"><button id="prev">&larr; Previous</button><button id="next">Next &rarr;</button><button id="skip">Next unlabelled</button></div>
<div class="bar tools"><button id="save">Save labels as CSV</button><button id="show">Show CSV to copy</button><span id="msg" class="muted"></span></div>
<textarea id="csv" hidden readonly></textarea>
</main>
<script>
const ITEMS = __DATA__;
let i = 0, who = "", L = {};
const $ = (id) => document.getElementById(id);
const key = () => "hostility_labels_" + (who || "anon");
function load() { try { L = JSON.parse(localStorage.getItem(key()) || "{}"); } catch (e) { L = {}; } }
function store() { try { localStorage.setItem(key(), JSON.stringify(L)); } catch (e) { $("msg").textContent = "Could not save in this browser: export the CSV before closing."; } }
function render() {
  const it = ITEMS[i], cur = L[it.item] || {};
  $("pos").textContent = "Comment " + (i + 1) + " of " + ITEMS.length + " (item " + it.item + ")";
  $("text").textContent = it.text; $("note").value = cur.notes || "";
  document.querySelectorAll(".lab").forEach((b) => b.classList.toggle("on", b.dataset.l === cur.label));
  const done = ITEMS.filter((x) => L[x.item] && L[x.item].label).length;
  $("count").textContent = done + " / " + ITEMS.length + " labelled"; $("pg").style.width = (100 * done / ITEMS.length) + "%";
}
function setLabel(l) { const it = ITEMS[i]; L[it.item] = Object.assign({}, L[it.item], { label: l, notes: $("note").value }); store(); render(); setTimeout(() => go(1), 120); }
function go(d) { const it = ITEMS[i]; if (L[it.item]) { L[it.item].notes = $("note").value; store(); } i = Math.max(0, Math.min(ITEMS.length - 1, i + d)); render(); }
function csv() { const q = (s) => '"' + String(s || "").replace(/"/g, '""') + '"'; return "item,label,notes,labeller\\n" + ITEMS.map((x) => [x.item, (L[x.item] || {}).label || "", q((L[x.item] || {}).notes), who].join(",")).join("\\n") + "\\n"; }
document.querySelectorAll(".lab").forEach((b) => b.addEventListener("click", () => setLabel(b.dataset.l)));
$("prev").onclick = () => go(-1); $("next").onclick = () => go(1);
$("skip").onclick = () => { const j = ITEMS.findIndex((x, k) => k > i && !(L[x.item] && L[x.item].label)); const k2 = j >= 0 ? j : ITEMS.findIndex((x) => !(L[x.item] && L[x.item].label)); if (k2 >= 0) { i = k2; render(); } };
$("note").addEventListener("change", () => { const it = ITEMS[i]; L[it.item] = Object.assign({}, L[it.item], { notes: $("note").value }); store(); });
$("who").addEventListener("keydown", (ev) => { if (ev.key === "Enter") ev.target.blur(); });  // Enter confirms the initials and frees the label keys
$("who").addEventListener("change", () => { who = $("who").value.trim().toUpperCase(); try { localStorage.setItem("hostility_labeller", who); } catch (e) {} load(); render(); });
$("save").onclick = () => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([csv()], { type: "text/csv" })); a.download = "hostility_labels_" + (who || "anon") + ".csv"; document.body.appendChild(a); a.click(); a.remove(); $("msg").textContent = "Saved to your Downloads folder. Move it to seedoils/data/processed/."; };
$("show").onclick = () => { $("csv").hidden = !$("csv").hidden; $("csv").value = csv(); };
document.addEventListener("keydown", (ev) => {
  if (ev.target.tagName === "TEXTAREA" || ev.target.tagName === "INPUT") return;
  const m = { h: "H", c: "C", n: "N", u: "U", 1: "H", 2: "C", 3: "N", 4: "U" }[ev.key.toLowerCase()];
  if (m) { setLabel(m); ev.preventDefault(); } else if (ev.key === "ArrowRight") go(1); else if (ev.key === "ArrowLeft") go(-1);
});
try { who = localStorage.getItem("hostility_labeller") || ""; } catch (e) {} $("who").value = who; load(); render();
</script></body></html>"""
OUT.write_text(PAGE.replace("__DATA__", DATA), encoding="utf-8")
print(f"wrote {OUT} ({len(items)} items). Open it in a browser; it works offline.")
