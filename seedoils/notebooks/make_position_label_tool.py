"""Fresh, hand-labelled sample for Figure 3b ('what each community says: are seed oils harmful?'), decision 25 Nov: the AI-labelled sample and
its labels are not on this machine, so a new random sample is labelled by people and REPLACES the AI labels in the figure.
Sample (seed 31): comments (not posts) of >= 15 words that mention a seed-oil term (same SEED regex as build_comment_sample.py), bots and
[deleted] left out, 40 per subreddit x period (before / from 1 Jan 2024) = 160, shuffled; no subreddit, date or author shown.
Text: quotes ('>' lines) marked [quote], links replaced by [link], capped at 400 words.
Codebook = position_codebook_v2.md in one key per comment:
  H harmful       says or clearly implies seed oils / LA / omega-6 / PUFA harm health (incl. avoiding them as unhealthy, calling them toxic or inflammatory)
  N not harmful   says or implies they are safe or healthy, or that the evidence of harm is weak or wrong (incl. rebutting a harm claim)
  M mixed         harmful in some circumstances, fine in others (refined / heated / in excess bad, cold-pressed or moderate fine; some oils bad, others fine)
  Q no position   on the claim but no verdict: a genuine question, a request for sources, neutral explanation, 'the evidence is unclear'
  X off the claim the term appears only in passing, or the comment is about something else (politics, shopping, taste, saturated fat or sugar alone)
Rules: judge the commenter's own words (quotes count only if adopted); health harm only (taste, cost, ethics are not harm); insults alone do not decide;
do not infer a position from the community or topic.
Outputs: seedoils/label_positions.html (gitignored: Reddit text) and data/processed/position_sample_key.csv (item -> comment id, side, period;
gitignored). Labels export position_labels_<initials>.csv -> data/processed/; position_eval.py builds the figure data.
Run from the repo root:  ./.venv-nlp/bin/python seedoils/notebooks/make_position_label_tool.py"""
import csv
import gzip
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from seedoil_common import is_bot  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]; RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"; OUT = ROOT / "label_positions.html"
SUBS = ["StopEatingSeedOils", "ScientificNutrition"]; SPLIT = 1704067200; PER_CELL, MIN_WORDS, MAX_WORDS = 40, 15, 400
SEED = re.compile(r"\b(seed ?oils?|vegetable oils?|veg oils?|canola|rapeseed|soybean oil|soy oil|sunflower oil|safflower|corn oil|"
                  r"cottonseed|linoleic|omega[- ]?6|n-6|pufas?|polyunsaturated)\b", re.I)
URL = re.compile(r"https?://\S+")


def clean(t):
    t = URL.sub("[link]", t or "")
    t = "\n".join(("[quote] " + l.lstrip("> ").strip()) if l.lstrip().startswith(">") else l for l in t.splitlines())
    w = t.split(" ")
    return " ".join(w[:MAX_WORDS]) + (" ..." if len(w) > MAX_WORDS else "")


rng = random.Random(31); picks = []
for s in SUBS:
    pools = {"pre2024": [], "from2024": []}
    with gzip.open(RAW / f"{s}_comments.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            x = json.loads(line); a = x.get("author") or ""; b = x.get("body") or ""
            if a == "[deleted]" or is_bot(a) or b.strip() in ("", "[removed]", "[deleted]") or len(b.split()) < MIN_WORDS or not SEED.search(b):
                continue
            pools["from2024" if int(x["created_utc"]) >= SPLIT else "pre2024"].append((x["id"], b))
    for per, pool in pools.items():
        pool.sort()
        for cid, b in rng.sample(pool, PER_CELL):
            picks.append((s, per, cid, b))
        print(f"{s} {per}: {len(pool):,} eligible, drew {PER_CELL}")
random.Random(32).shuffle(picks)
with open(PROC / "position_sample_key.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["item", "side", "period", "comment_id"])
    for i, (s, per, cid, _) in enumerate(picks, 1):
        w.writerow([i, s, per, cid])
items = [{"item": i, "text": clean(b)} for i, (_, _, _, b) in enumerate(picks, 1)]
DATA = json.dumps(items, ensure_ascii=True).replace("</", "<\\/")
PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Position Labels</title>
<style>
:root { --bg:#f6f7f5; --card:#fff; --fg:#1c2120; --muted:#5d6763; --line:#dbe0dd; --on:#2b6cb0; --focus:#2b6cb0; --sans:Inter, system-ui, -apple-system, "Segoe UI", sans-serif; }
@media (prefers-color-scheme: dark) { :root { --bg:#151918; --card:#1d2220; --fg:#e8ece9; --muted:#9aa49f; --line:#2e3532; --on:#6ea8e6; --focus:#6ea8e6; color-scheme: dark; } }
body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.55 var(--sans); }
main { max-width:860px; margin:0 auto; padding:20px 16px 60px; display:grid; gap:14px; }
h1 { font-size:22px; margin:0; } .muted { color:var(--muted); font-size:13px; }
.bar { display:flex; flex-wrap:wrap; gap:8px 14px; align-items:center; }
.prog { flex:1 1 200px; height:6px; background:var(--line); border-radius:3px; overflow:hidden; } .prog i { display:block; height:100%; background:var(--focus); width:0; }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:16px; }
.text { white-space:pre-wrap; font-size:16px; line-height:1.6; max-height:50vh; overflow:auto; }
.keys { display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:8px; }
button.lab { text-align:left; border:2px solid var(--line); background:var(--card); color:var(--fg); border-radius:8px; padding:9px 12px; cursor:pointer; font:inherit; }
button.lab small { display:block; color:var(--muted); font-size:12.5px; } button.lab.on { border-color:var(--on); font-weight:600; }
button:focus-visible, input:focus-visible, textarea:focus-visible { outline:2px solid var(--focus); outline-offset:2px; }
.nav button, .tools button { border:1px solid var(--line); background:var(--card); color:var(--fg); border-radius:6px; padding:6px 12px; cursor:pointer; font:inherit; }
textarea { width:100%; box-sizing:border-box; min-height:40px; border:1px solid var(--line); border-radius:6px; background:var(--card); color:var(--fg); padding:6px 8px; font:inherit; }
input#who { width:90px; border:1px solid var(--line); border-radius:6px; padding:5px 8px; background:var(--card); color:var(--fg); font:inherit; }
details { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:10px 14px; } summary { cursor:pointer; font-weight:600; } details ul { margin:8px 0 0; padding-left:20px; }
#csv { font-family:ui-monospace, Menlo, monospace; font-size:12px; min-height:120px; }
</style></head><body><main>
<h1>Position labels</h1>
<p class="muted">160 comments that mention seed oils (or canola, linoleic acid, omega-6, PUFA&hellip;), from both subreddits, without subreddit or date. What does the commenter say about whether seed oils harm health? Keys <b>H N M Q X</b> (or 1&ndash;5); &larr; &rarr; to move. Progress is saved in this browser under your initials.</p>
<div class="bar"><label for="who">Your initials (then press Enter)</label><input id="who" maxlength="6" placeholder="e.g. HC"><span id="count" class="muted"></span><div class="prog"><i id="pg"></i></div></div>
<details open><summary>Codebook</summary><ul>
<li><b>H harmful</b>: says or clearly implies seed oils / linoleic acid / omega-6 / PUFA harm health, including avoiding them because they are unhealthy, advising others to, calling them toxic or inflammatory.</li>
<li><b>N not harmful</b>: says or implies they are safe or healthy, or that the evidence of harm is weak or wrong, including rebutting a harm claim.</li>
<li><b>M mixed</b>: harmful in some circumstances, fine in others (refined, heated or in excess bad; cold-pressed or moderate fine; some oils bad, others fine).</li>
<li><b>Q no position</b>: about the harm question but no verdict: a genuine question, a request for sources, a neutral explanation, &ldquo;the evidence is unclear&rdquo;.</li>
<li><b>X off the claim</b>: the term appears only in passing, or the comment is about something else (politics, shopping, taste, saturated fat or sugar alone).</li>
<li>Judge the commenter&rsquo;s own words; <code>[quote]</code> text counts only if they adopt it. Health harm only: taste, cost or ethics are not harm. Insults alone do not decide. Do not guess from the topic.</li></ul></details>
<div class="card"><div class="muted" id="pos"></div><div class="text" id="text"></div></div>
<div class="keys">
<button class="lab" data-l="H"><b>H</b> Harmful<small>seed oils harm health</small></button>
<button class="lab" data-l="N"><b>N</b> Not harmful<small>safe, healthy, harm claim wrong</small></button>
<button class="lab" data-l="M"><b>M</b> Mixed<small>depends on kind or amount</small></button>
<button class="lab" data-l="Q"><b>Q</b> No position<small>question, neutral, unsure</small></button>
<button class="lab" data-l="X"><b>X</b> Off the claim<small>about something else</small></button></div>
<label for="note" class="muted">Note (optional)</label><textarea id="note"></textarea>
<div class="bar nav"><button id="prev">&larr; Previous</button><button id="next">Next &rarr;</button><button id="skip">Next unlabelled</button></div>
<div class="bar tools"><button id="save">Save labels as CSV</button><button id="show">Show CSV to copy</button><span id="msg" class="muted"></span></div>
<textarea id="csv" hidden readonly></textarea>
</main>
<script>
const ITEMS = __DATA__;
let i = 0, who = "", L = {};
const $ = (id) => document.getElementById(id);
const key = () => "position_labels_" + (who || "anon");
function load() { try { L = JSON.parse(localStorage.getItem(key()) || "{}"); } catch (e) { L = {}; } }
function store() { try { localStorage.setItem(key(), JSON.stringify(L)); } catch (e) { $("msg").textContent = "Could not save in this browser: export the CSV before closing."; } }
function render() {
  const it = ITEMS[i], cur = L[it.item] || {};
  $("pos").textContent = "Comment " + (i + 1) + " of " + ITEMS.length; $("text").textContent = it.text; $("text").scrollTop = 0; $("note").value = cur.notes || "";
  document.querySelectorAll(".lab").forEach((b) => b.classList.toggle("on", b.dataset.l === cur.label));
  const n = ITEMS.filter((x) => L[x.item] && L[x.item].label).length; $("count").textContent = n + " / " + ITEMS.length + " labelled"; $("pg").style.width = (100 * n / ITEMS.length) + "%";
}
function setLabel(l) { const it = ITEMS[i]; L[it.item] = Object.assign({}, L[it.item], { label: l, notes: $("note").value }); store(); render(); setTimeout(() => go(1), 120); }
function go(d) { const it = ITEMS[i]; if (L[it.item]) { L[it.item].notes = $("note").value; store(); } i = Math.max(0, Math.min(ITEMS.length - 1, i + d)); render(); }
function csv() { const q = (s) => '"' + String(s || "").replace(/"/g, '""') + '"'; return "item,label,notes,labeller\\n" + ITEMS.map((x) => [x.item, (L[x.item] || {}).label || "", q((L[x.item] || {}).notes), who].join(",")).join("\\n") + "\\n"; }
document.querySelectorAll(".lab").forEach((b) => b.addEventListener("click", () => setLabel(b.dataset.l)));
$("prev").onclick = () => go(-1); $("next").onclick = () => go(1);
$("skip").onclick = () => { const j = ITEMS.findIndex((x, k) => k > i && !(L[x.item] && L[x.item].label)); const k2 = j >= 0 ? j : ITEMS.findIndex((x) => !(L[x.item] && L[x.item].label)); if (k2 >= 0) { i = k2; render(); } };
$("note").addEventListener("change", () => { const it = ITEMS[i]; L[it.item] = Object.assign({}, L[it.item], { notes: $("note").value }); store(); });
$("who").addEventListener("keydown", (ev) => { if (ev.key === "Enter") ev.target.blur(); });
$("who").addEventListener("change", () => { who = $("who").value.trim().toUpperCase(); try { localStorage.setItem("position_labeller", who); } catch (e) {} load(); render(); });
$("save").onclick = () => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([csv()], { type: "text/csv" })); a.download = "position_labels_" + (who || "anon") + ".csv"; document.body.appendChild(a); a.click(); a.remove(); $("msg").textContent = "Saved to your Downloads folder. Move it to seedoils/data/processed/."; };
$("show").onclick = () => { $("csv").hidden = !$("csv").hidden; $("csv").value = csv(); };
document.addEventListener("keydown", (ev) => {
  if (ev.target.tagName === "TEXTAREA" || ev.target.tagName === "INPUT") return;
  const m = { h: "H", n: "N", m: "M", q: "Q", x: "X", 1: "H", 2: "N", 3: "M", 4: "Q", 5: "X" }[ev.key.toLowerCase()];
  if (m) { setLabel(m); ev.preventDefault(); } else if (ev.key === "ArrowRight") go(1); else if (ev.key === "ArrowLeft") go(-1);
});
try { who = localStorage.getItem("position_labeller") || ""; } catch (e) {} $("who").value = who; load(); render();
</script></body></html>"""
OUT.write_text(PAGE.replace("__DATA__", DATA), encoding="utf-8")
print(f"wrote {OUT} ({len(items)} comments) and data/processed/position_sample_key.csv")
