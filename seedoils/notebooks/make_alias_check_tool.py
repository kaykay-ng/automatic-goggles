"""Builds seedoils/check_aliases.html: a local, offline page for checking every alias in entity_aliases.csv by reading (nothing is uploaded).
For each alias (switched-off '#' rows included, marked 'off'): how many documents it matches in each subreddit, and up to 6 random matches in
context (3 per subreddit), the alias highlighted. One decision per alias:
  K keep    the alias means the canonical name in (nearly) all matches
  D drop    it often means something else (switch it off with #)
  ? unsure
Exports alias_decisions_<initials>.csv (canonical, alias, decision, note) -> move to seedoils/data/processed/; then entity_aliases.csv is updated
to match (K -> on, D -> off) and the counting scripts are rerun. The page holds Reddit text, so it is gitignored.
Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/make_alias_check_tool.py"""
import csv
import json
import random
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from seedoil_common import ALIAS_FILE, basic_clean  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "check_aliases.html"; rng = random.Random(0)
rows = []
for line in open(ALIAS_FILE, encoding="utf-8"):
    s = line.strip(); off = s.startswith("#")
    body = s.lstrip("#").strip()
    if not body or body.startswith("canonical") or "," not in body:
        continue
    parts = next(csv.reader([body])); canon, alias = parts[0].strip(), parts[1].strip(); note = parts[2].strip() if len(parts) > 2 else ""
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", canon) or not alias or " " in canon:
        continue  # a commented-out explanation line, not an alias row
    rows.append({"canonical": canon, "alias": alias, "clean": basic_clean(alias), "off": off, "note": note})
texts = {}
for pfx in ("seso", "scinut"):
    texts[pfx] = [basic_clean(t) for t in pd.read_csv(ROOT / "data" / "processed" / f"{pfx}_docs.csv.gz", usecols=["text"], keep_default_na=False).text.astype(str)]
for r in rows:
    rx = re.compile(r"(?<![\w-])" + re.escape(r["clean"]) + r"(?![\w-])"); r["n"] = {}; r["ex"] = []
    for pfx, T in texts.items():
        hits = [t for t in T if rx.search(t)]; r["n"][pfx] = len(hits)
        for t in rng.sample(hits, min(3, len(hits))):
            m = rx.search(t); r["ex"].append([pfx, t[max(0, m.start() - 70):m.start()], t[m.start():m.end()], t[m.end():m.end() + 70]])
    print(f"{r['canonical']:<30} {r['alias']!r:<32} SESO {r['n']['seso']:>6,}  SciNut {r['n']['scinut']:>6,}{'  (off)' if r['off'] else ''}")
DATA = json.dumps([{k: r[k] for k in ("canonical", "alias", "off", "note", "n", "ex")} for r in rows], ensure_ascii=True).replace("</", "<\\/")
PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alias Check</title>
<style>
:root { --bg:#f6f7f5; --card:#fff; --fg:#1c2120; --muted:#5d6763; --line:#dbe0dd; --hl:#fde68a; --K:#2f6f4f; --D:#b42318; --Q:#6b6f7a; --focus:#2b6cb0;
  --sans:Inter, system-ui, -apple-system, "Segoe UI", sans-serif; }
@media (prefers-color-scheme: dark) { :root { --bg:#151918; --card:#1d2220; --fg:#e8ece9; --muted:#9aa49f; --line:#2e3532; --hl:#6b5a12; --K:#6cc191; --D:#f0796d; --Q:#a3a7b2; --focus:#6ea8e6; color-scheme: dark; } }
body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.55 var(--sans); }
main { max-width:900px; margin:0 auto; padding:20px 16px 60px; display:grid; gap:14px; }
h1 { font-size:22px; margin:0; } .muted { color:var(--muted); font-size:13px; }
.bar { display:flex; flex-wrap:wrap; gap:8px 14px; align-items:center; }
.prog { flex:1 1 200px; height:6px; background:var(--line); border-radius:3px; overflow:hidden; } .prog i { display:block; height:100%; background:var(--focus); width:0; }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:16px; display:grid; gap:10px; }
.head { display:flex; flex-wrap:wrap; gap:6px 14px; align-items:baseline; } .head b { font-size:19px; } code { font-size:14px; }
.tag { font-size:12px; border:1px solid var(--line); border-radius:4px; padding:0 6px; color:var(--muted); }
ul.ex { margin:0; padding-left:18px; display:grid; gap:6px; } ul.ex li { font-size:14.5px; } mark { background:var(--hl); color:inherit; border-radius:3px; padding:0 2px; }
.keys { display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:8px; }
button.lab { text-align:left; border:2px solid var(--line); background:var(--card); color:var(--fg); border-radius:8px; padding:9px 12px; cursor:pointer; font:inherit; }
button.lab small { display:block; color:var(--muted); font-size:12.5px; }
button.lab.on[data-l="K"] { border-color:var(--K); } button.lab.on[data-l="D"] { border-color:var(--D); } button.lab.on[data-l="?"] { border-color:var(--Q); } button.lab.on { font-weight:600; }
button:focus-visible, input:focus-visible, textarea:focus-visible { outline:2px solid var(--focus); outline-offset:2px; }
.nav button, .tools button { border:1px solid var(--line); background:var(--card); color:var(--fg); border-radius:6px; padding:6px 12px; cursor:pointer; font:inherit; }
textarea { width:100%; box-sizing:border-box; min-height:40px; border:1px solid var(--line); border-radius:6px; background:var(--card); color:var(--fg); padding:6px 8px; font:inherit; }
input#who { width:90px; border:1px solid var(--line); border-radius:6px; padding:5px 8px; background:var(--card); color:var(--fg); font:inherit; }
#csv { font-family:ui-monospace, Menlo, monospace; font-size:12px; min-height:120px; }
</style></head><body><main>
<h1>Alias check</h1>
<p class="muted">Each alias in <code>entity_aliases.csv</code> becomes one merged token where words are counted. For each, read the random matches (text lowercased, punctuation removed) and decide. Keys <b>K</b> keep, <b>D</b> drop, <b>?</b> unsure (or 1&ndash;3); &larr; &rarr; to move. Aliases marked <span class="tag">off</span> are currently switched off: K would switch them on.</p>
<div class="bar"><label for="who">Your initials (then press Enter)</label><input id="who" maxlength="6" placeholder="e.g. HC"><span id="count" class="muted"></span><div class="prog"><i id="pg"></i></div></div>
<div class="card"><div class="head"><b id="alias"></b><span>&rarr; <code id="canon"></code></span><span class="tag" id="off" hidden>off</span><span class="muted" id="n"></span></div><div class="muted" id="note"></div><ul class="ex" id="ex"></ul><div class="muted" id="pos"></div></div>
<div class="keys">
<button class="lab" data-l="K"><b>K</b> Keep<small>means this name in (nearly) all matches</small></button>
<button class="lab" data-l="D"><b>D</b> Drop<small>often means something else</small></button>
<button class="lab" data-l="?"><b>?</b> Unsure<small>leave as it is, discuss</small></button></div>
<label for="note2" class="muted">Note (optional)</label><textarea id="note2"></textarea>
<div class="bar nav"><button id="prev">&larr; Previous</button><button id="next">Next &rarr;</button></div>
<div class="bar tools"><button id="save">Save decisions as CSV</button><button id="show">Show CSV to copy</button><span id="msg" class="muted"></span></div>
<textarea id="csv" hidden readonly></textarea>
</main>
<script>
const ITEMS = __DATA__;
let i = 0, who = "", L = {};
const $ = (id) => document.getElementById(id), K_ = (it) => it.canonical + "|" + it.alias;
const key = () => "alias_decisions_" + (who || "anon");
function load() { try { L = JSON.parse(localStorage.getItem(key()) || "{}"); } catch (e) { L = {}; } }
function store() { try { localStorage.setItem(key(), JSON.stringify(L)); } catch (e) { $("msg").textContent = "Could not save in this browser: export the CSV before closing."; } }
function render() {
  const it = ITEMS[i], cur = L[K_(it)] || {};
  $("alias").textContent = it.alias; $("canon").textContent = it.canonical; $("off").hidden = !it.off;
  $("n").textContent = "matches: r/StopEatingSeedOils " + it.n.seso.toLocaleString() + " documents, r/ScientificNutrition " + it.n.scinut.toLocaleString();
  $("note").textContent = it.note ? "Note in the file: " + it.note : "";
  const ul = $("ex"); ul.textContent = "";
  if (!it.ex.length) { const li = document.createElement("li"); li.textContent = "(no matches)"; ul.appendChild(li); }
  it.ex.forEach(([p, a, m, b]) => { const li = document.createElement("li"); const s = document.createElement("span"); s.className = "muted"; s.textContent = (p === "seso" ? "SESO" : "SciNut") + ": "; li.appendChild(s);
    li.appendChild(document.createTextNode("…" + a)); const mk = document.createElement("mark"); mk.textContent = m; li.appendChild(mk); li.appendChild(document.createTextNode(b + "…")); ul.appendChild(li); });
  $("pos").textContent = "Alias " + (i + 1) + " of " + ITEMS.length; $("note2").value = cur.notes || "";
  document.querySelectorAll(".lab").forEach((b) => b.classList.toggle("on", b.dataset.l === cur.label));
  const done = ITEMS.filter((x) => L[K_(x)] && L[K_(x)].label).length;
  $("count").textContent = done + " / " + ITEMS.length + " decided"; $("pg").style.width = (100 * done / ITEMS.length) + "%";
}
function setLabel(l) { const it = ITEMS[i]; L[K_(it)] = Object.assign({}, L[K_(it)], { label: l, notes: $("note2").value }); store(); render(); setTimeout(() => go(1), 120); }
function go(d) { const it = ITEMS[i]; if (L[K_(it)]) { L[K_(it)].notes = $("note2").value; store(); } i = Math.max(0, Math.min(ITEMS.length - 1, i + d)); render(); }
function csv() { const q = (s) => '"' + String(s || "").replace(/"/g, '""') + '"'; return "canonical,alias,was_off,decision,note,labeller\\n" + ITEMS.map((x) => [x.canonical, q(x.alias), x.off ? 1 : 0, (L[K_(x)] || {}).label || "", q((L[K_(x)] || {}).notes), who].join(",")).join("\\n") + "\\n"; }
document.querySelectorAll(".lab").forEach((b) => b.addEventListener("click", () => setLabel(b.dataset.l)));
$("prev").onclick = () => go(-1); $("next").onclick = () => go(1);
$("note2").addEventListener("change", () => { const it = ITEMS[i]; L[K_(it)] = Object.assign({}, L[K_(it)], { notes: $("note2").value }); store(); });
$("who").addEventListener("keydown", (ev) => { if (ev.key === "Enter") ev.target.blur(); });
$("who").addEventListener("change", () => { who = $("who").value.trim().toUpperCase(); try { localStorage.setItem("alias_labeller", who); } catch (e) {} load(); render(); });
$("save").onclick = () => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([csv()], { type: "text/csv" })); a.download = "alias_decisions_" + (who || "anon") + ".csv"; document.body.appendChild(a); a.click(); a.remove(); $("msg").textContent = "Saved to your Downloads folder. Move it to seedoils/data/processed/."; };
$("show").onclick = () => { $("csv").hidden = !$("csv").hidden; $("csv").value = csv(); };
document.addEventListener("keydown", (ev) => {
  if (ev.target.tagName === "TEXTAREA" || ev.target.tagName === "INPUT") return;
  const m = { k: "K", d: "D", "?": "?", 1: "K", 2: "D", 3: "?" }[ev.key.toLowerCase()];
  if (m) { setLabel(m); ev.preventDefault(); } else if (ev.key === "ArrowRight") go(1); else if (ev.key === "ArrowLeft") go(-1);
});
try { who = localStorage.getItem("alias_labeller") || ""; } catch (e) {} $("who").value = who; load(); render();
</script></body></html>"""
OUT.write_text(PAGE.replace("__DATA__", DATA), encoding="utf-8")
print(f"wrote {OUT} ({len(rows)} aliases). Open it in a browser; it works offline.")
