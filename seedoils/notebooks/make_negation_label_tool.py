"""Builds seedoils/label_negation.html: a local, offline page for checking the negation marking (seedoil_common.mark_negation) by reading.
Input: seedoils/data/processed/negation_check.csv (from  python seedoils/notebooks/seedoil_common.py negation : 150 random r/StopEatingSeedOils
documents that contain a negator; the stretch around the first negator and the words marked no_<word>).
The page shows the stretch with the negator and the marked words highlighted. One judgement per item:
  Y  correct: every marked word is negated in meaning, and no clearly negated content word in the stretch is left unmarked
     (also Y when nothing is marked and nothing should be).
  P  partly: some marked words are not negated (scope runs too far, past a clause boundary) or a negated word right after the negator is missed.
  W  wrong: the word does not negate here ('not only', 'no doubt', a rhetorical 'isn't it'), or the marking reverses the meaning.
  U  can't tell.
Exports negation_labels_<initials>.csv (item, label, notes) -> move to seedoils/data/processed/. Reddit text: the page is gitignored.
Run from the repo root:  python3 seedoils/notebooks/make_negation_label_tool.py"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# optional argument: a version tag, e.g. v2 -> reads negation_check_v2.csv, writes label_negation_v2.html, exports negation_labels_v2_<initials>.csv
TAG = sys.argv[1] if len(sys.argv) > 1 else ""; SFX = f"_{TAG}" if TAG else ""
SRC, OUT = ROOT / "data" / "processed" / f"negation_check{SFX}.csv", ROOT / f"label_negation{SFX}.html"
items = [{"item": int(r["item"]), "stretch": r["stretch"], "negator": r["negator"], "marked": r["marked"]} for r in csv.DictReader(open(SRC, encoding="utf-8"))]
DATA = json.dumps(items, ensure_ascii=True).replace("</", "<\\/")
PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Negation Check</title>
<style>
:root { --bg:#f6f7f5; --card:#fff; --fg:#1c2120; --muted:#5d6763; --line:#dbe0dd; --neg:#2b6cb0; --mark:#fde68a; --Y:#2f6f4f; --P:#b7791f; --W:#b42318; --U:#6b6f7a; --focus:#2b6cb0;
  --sans:Inter, system-ui, -apple-system, "Segoe UI", sans-serif; }
@media (prefers-color-scheme: dark) { :root { --bg:#151918; --card:#1d2220; --fg:#e8ece9; --muted:#9aa49f; --line:#2e3532; --neg:#6ea8e6; --mark:#6b5a12; --Y:#6cc191; --P:#e2b04a; --W:#f0796d; --U:#a3a7b2; --focus:#6ea8e6; color-scheme: dark; } }
body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.55 var(--sans); }
main { max-width:860px; margin:0 auto; padding:20px 16px 60px; display:grid; gap:16px; }
h1 { font-size:22px; margin:0; } .muted { color:var(--muted); font-size:13px; }
.bar { display:flex; flex-wrap:wrap; gap:8px 14px; align-items:center; }
.prog { flex:1 1 200px; height:6px; background:var(--line); border-radius:3px; overflow:hidden; } .prog i { display:block; height:100%; background:var(--focus); width:0; }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:18px; display:grid; gap:10px; }
.text { font-size:18px; line-height:1.9; } .text .n { color:var(--neg); font-weight:700; text-decoration:underline; } .text .m { background:var(--mark); border-radius:3px; padding:0 2px; }
.marked { font-family:ui-monospace, Menlo, monospace; font-size:14px; }
.keys { display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:8px; }
button.lab { text-align:left; border:2px solid var(--line); background:var(--card); color:var(--fg); border-radius:8px; padding:10px 12px; cursor:pointer; font:inherit; }
button.lab small { display:block; color:var(--muted); font-size:12.5px; }
button.lab.on[data-l="Y"] { border-color:var(--Y); } button.lab.on[data-l="P"] { border-color:var(--P); } button.lab.on[data-l="W"] { border-color:var(--W); } button.lab.on[data-l="U"] { border-color:var(--U); }
button.lab.on { font-weight:600; }
button:focus-visible, input:focus-visible, textarea:focus-visible { outline:2px solid var(--focus); outline-offset:2px; }
.nav button, .tools button { border:1px solid var(--line); background:var(--card); color:var(--fg); border-radius:6px; padding:6px 12px; cursor:pointer; font:inherit; }
textarea { width:100%; box-sizing:border-box; min-height:44px; border:1px solid var(--line); border-radius:6px; background:var(--card); color:var(--fg); padding:6px 8px; font:inherit; }
input#who { width:90px; border:1px solid var(--line); border-radius:6px; padding:5px 8px; background:var(--card); color:var(--fg); font:inherit; }
details { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:10px 14px; } summary { cursor:pointer; font-weight:600; } details ul { margin:8px 0 0; padding-left:20px; }
#csv { font-family:ui-monospace, Menlo, monospace; font-size:12px; min-height:120px; }
</style></head><body><main>
<h1>Negation check</h1>
<p class="muted">150 stretches from r/StopEatingSeedOils around the first negation word (<span style="color:var(--neg);font-weight:700;text-decoration:underline">underlined</span>). Words the code marks as negated are <span style="background:var(--mark);padding:0 2px">highlighted</span>; in counting they become <code>no_word</code>. Text is lowercased, apostrophes removed (don't &rarr; dont). Keys <b>Y</b>, <b>P</b>, <b>W</b>, <b>U</b> (or 1&ndash;4); &larr; &rarr; to move.</p>
<div class="bar"><label for="who">Your initials (then press Enter)</label><input id="who" maxlength="6" placeholder="e.g. HC"><span id="count" class="muted"></span><div class="prog"><i id="pg"></i></div></div>
<details open><summary>What to judge</summary><ul>
<li><b>Y &mdash; correct.</b> Every highlighted word is negated in meaning, and no clearly negated content word right after the negator is left out. Also Y when nothing is highlighted and nothing should be.</li>
<li><b>P &mdash; partly.</b> Some highlighted words are not negated (the scope runs past the end of the negated phrase), or a negated word is missed.</li>
<li><b>W &mdash; wrong.</b> The word does not negate here (&ldquo;not only&rdquo;, &ldquo;no doubt&rdquo;, a rhetorical &ldquo;isn&rsquo;t it&rdquo;), or the marking turns the meaning around.</li>
<li><b>U &mdash; can&rsquo;t tell.</b></li>
<li>Judge only the first (underlined) negation word; words highlighted after a later negation word belong to that one. Small function words (the, a, is) are never marked; that is on purpose.</li></ul></details>
<div class="card"><div class="muted" id="pos"></div><div class="text" id="text"></div><div class="muted">Marked: <span class="marked" id="marked"></span></div></div>
<div class="keys">
<button class="lab" data-l="Y"><b>Y</b> Correct<small>all highlighted words negated, none missed</small></button>
<button class="lab" data-l="P"><b>P</b> Partly<small>too far, or a word missed</small></button>
<button class="lab" data-l="W"><b>W</b> Wrong<small>not a negation here, or meaning reversed</small></button>
<button class="lab" data-l="U"><b>U</b> Can&rsquo;t tell<small></small></button></div>
<label for="note" class="muted">Note (optional)</label><textarea id="note"></textarea>
<div class="bar nav"><button id="prev">&larr; Previous</button><button id="next">Next &rarr;</button><button id="skip">Next unjudged</button></div>
<div class="bar tools"><button id="save">Save labels as CSV</button><button id="show">Show CSV to copy</button><span id="msg" class="muted"></span></div>
<textarea id="csv" hidden readonly></textarea>
</main>
<script>
const ITEMS = __DATA__;
let i = 0, who = "", L = {};
const $ = (id) => document.getElementById(id);
const key = () => "negation_labels_" + (who || "anon");
function load() { try { L = JSON.parse(localStorage.getItem(key()) || "{}"); } catch (e) { L = {}; } }
function store() { try { localStorage.setItem(key(), JSON.stringify(L)); } catch (e) { $("msg").textContent = "Could not save in this browser: export the CSV before closing."; } }
function render() {
  const it = ITEMS[i], cur = L[it.item] || {}, marks = (it.marked || "").split(" ").filter(Boolean).map((w) => w.slice(3));
  $("pos").textContent = "Item " + (i + 1) + " of " + ITEMS.length;
  const box = $("text"); box.textContent = ""; let seen = false, after = false;
  it.stretch.split(" ").forEach((w) => {
    const s = document.createElement("span"); s.textContent = w + " ";
    if (!seen && w === it.negator) { s.className = "n"; seen = true; after = true; }
    else if (after && marks.length && w === marks[0]) { s.className = "m"; marks.shift(); }
    box.appendChild(s);
  });
  $("marked").textContent = it.marked || "(nothing marked)"; $("note").value = cur.notes || "";
  document.querySelectorAll(".lab").forEach((b) => b.classList.toggle("on", b.dataset.l === cur.label));
  const done = ITEMS.filter((x) => L[x.item] && L[x.item].label).length;
  $("count").textContent = done + " / " + ITEMS.length + " judged"; $("pg").style.width = (100 * done / ITEMS.length) + "%";
}
function setLabel(l) { const it = ITEMS[i]; L[it.item] = Object.assign({}, L[it.item], { label: l, notes: $("note").value }); store(); render(); setTimeout(() => go(1), 120); }
function go(d) { const it = ITEMS[i]; if (L[it.item]) { L[it.item].notes = $("note").value; store(); } i = Math.max(0, Math.min(ITEMS.length - 1, i + d)); render(); }
function csv() { const q = (s) => '"' + String(s || "").replace(/"/g, '""') + '"'; return "item,label,notes,labeller\\n" + ITEMS.map((x) => [x.item, (L[x.item] || {}).label || "", q((L[x.item] || {}).notes), who].join(",")).join("\\n") + "\\n"; }
document.querySelectorAll(".lab").forEach((b) => b.addEventListener("click", () => setLabel(b.dataset.l)));
$("prev").onclick = () => go(-1); $("next").onclick = () => go(1);
$("skip").onclick = () => { const j = ITEMS.findIndex((x, k) => k > i && !(L[x.item] && L[x.item].label)); const k2 = j >= 0 ? j : ITEMS.findIndex((x) => !(L[x.item] && L[x.item].label)); if (k2 >= 0) { i = k2; render(); } };
$("note").addEventListener("change", () => { const it = ITEMS[i]; L[it.item] = Object.assign({}, L[it.item], { notes: $("note").value }); store(); });
$("who").addEventListener("keydown", (ev) => { if (ev.key === "Enter") ev.target.blur(); });
$("who").addEventListener("change", () => { who = $("who").value.trim().toUpperCase(); try { localStorage.setItem("negation_labeller", who); } catch (e) {} load(); render(); });
$("save").onclick = () => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([csv()], { type: "text/csv" })); a.download = "negation_labels_" + (who || "anon") + ".csv"; document.body.appendChild(a); a.click(); a.remove(); $("msg").textContent = "Saved to your Downloads folder. Move it to seedoils/data/processed/."; };
$("show").onclick = () => { $("csv").hidden = !$("csv").hidden; $("csv").value = csv(); };
document.addEventListener("keydown", (ev) => {
  if (ev.target.tagName === "TEXTAREA" || ev.target.tagName === "INPUT") return;
  const m = { y: "Y", p: "P", w: "W", u: "U", 1: "Y", 2: "P", 3: "W", 4: "U" }[ev.key.toLowerCase()];
  if (m) { setLabel(m); ev.preventDefault(); } else if (ev.key === "ArrowRight") go(1); else if (ev.key === "ArrowLeft") go(-1);
});
try { who = localStorage.getItem("negation_labeller") || ""; } catch (e) {} $("who").value = who; load(); render();
</script></body></html>"""
PAGE = PAGE.replace('"negation_labels_"', '"negation_labels' + SFX + '_"').replace("<h1>Negation check</h1>", f"<h1>Negation check{' (' + TAG + ')' if TAG else ''}</h1>")
PAGE = PAGE.replace("150 stretches", f"{len(items)} stretches")
OUT.write_text(PAGE.replace("__DATA__", DATA), encoding="utf-8")
print(f"wrote {OUT} ({len(items)} items). Open it in a browser; it works offline.")
