"""Builds seedoils/label_stance.html: a local, offline page for hand-labelling the 177 blind stance items (no server, nothing uploaded).
Input: seedoils/data/processed/stance_sheet.csv (from dive_communities.py). The side and community stay in stance_key.csv, not in the page.
Run from final_project/:  ../.venv/bin/python seedoils/notebooks/make_stance_label_tool.py
The page keeps progress in the browser (localStorage) and exports stance_labels.csv (item_id, stance, focus, notes);
move that file to seedoils/data/processed/. The page holds Reddit text, so it is gitignored.

Codes (reworded 19 Nov: judge how the commenter TREATS the paper, which is visible without knowing the paper well):
S = uses it as evidence for their own point; D = attacks or discredits it (rats not humans, flawed methods, observational, funding, misread);
N = neutral mention or bare link, no position; U = cannot tell. Each item also shows the paper's conclusion (from its abstract), full abstract on demand.
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "label_stance.html"

ABSTRACTS = ROOT / "data" / "raw" / "sheet_abstracts.json"  # OpenAlex abstract_inverted_index, gaps filled from PubMed efetch (19 Nov)


def conclusion(abstract):
    """The abstract's conclusion: text after a CONCLUSION(S)/INTERPRETATION label if there is one, else its last two sentences."""
    if not abstract:
        return ""
    m = re.search(r"\b(CONCLUSIONS?|Conclusions?|INTERPRETATION|Interpretation|IMPLICATIONS)\b\s*[:.]?\s*(.+)", abstract, re.S)
    if m:
        return re.split(r"\b(TRIAL REGISTRATION|FUNDING|Funding|Trial registration|CLINICAL TRIAL)\b", m.group(2))[0].strip()
    sents = re.split(r"(?<=[.!?])\s+", abstract.strip())
    return " ".join(sents[-2:])


paper_of = {r["item_id"]: r["openalex_id"] for r in csv.DictReader(open(PROC / "stance_key.csv"))}  # only the paper id, not the side
abstracts = json.loads(ABSTRACTS.read_text()) if ABSTRACTS.exists() else {}
with open(PROC / "stance_sheet.csv", encoding="utf-8") as f:
    items = []
    for r in csv.DictReader(f):
        a = abstracts.get(paper_of[r["item_id"]], "")
        items.append({"id": int(r["item_id"]), "paper": r["paper_title"], "year": r["paper_year"], "win": r["citation_window"],
                      "found": r["window_anchor_found"] == "1", "text": r["comment_text"], "concl": conclusion(a), "abs": a})
payload = json.dumps(items, ensure_ascii=False).replace("</", "<\\/")

HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Label citation stance</title>
<style>
:root{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--line:#e1e0d9;--card:#ffffff;--on:#1f6fd0;--paper:#f3f1ea}
@media (prefers-color-scheme:dark){:root{--bg:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--line:#383835;--card:#232322;--on:#5598e7;--paper:#2b2a28}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
main{max-width:820px;margin:0 auto;padding:20px 16px 60px}
.top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;color:var(--ink2);font-size:14px}
.bar{height:6px;background:var(--line);border-radius:3px;margin:10px 0 18px}.bar i{display:block;height:100%;background:var(--on);border-radius:3px}
.paper{background:var(--paper);border-radius:10px;padding:12px 14px;font-size:15px;margin-bottom:12px}
.paper b{font-weight:600}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;white-space:pre-wrap;word-wrap:break-word;max-height:48vh;overflow:auto}
mark{background:#f6d77a;color:#1a1a19;border-radius:4px;padding:0 4px;font-weight:600}
details{margin-top:10px;font-size:15px;color:var(--ink2)}details .card{margin-top:8px;color:var(--ink);font-size:15px}
.warn{font-size:13px;color:#b5651d;margin:6px 0 0}
.btns{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:16px 0}
button{font:inherit;font-size:15px;padding:10px 8px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}
button.on{background:var(--on);border-color:var(--on);color:#fff}
button small{display:block;font-size:12px;opacity:.75}
input[type=text]{width:100%;font:inherit;font-size:15px;padding:8px 10px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--ink);margin-top:6px}
label{font-size:14px;color:var(--ink2);display:block;margin-top:10px}
.nav{display:flex;gap:8px;margin-top:16px;flex-wrap:wrap}.nav button{flex:1}
.help{font-size:13px;color:var(--ink2);margin-top:18px;line-height:1.5}
</style></head><body><main>
<div class="top"><span id="pos"></span><span id="done"></span></div>
<div class="bar"><i id="prog"></i></div>
<div class="paper">Cited paper: <b id="paper"></b> <span id="year"></span>
  <div id="concl" style="margin-top:6px"></div>
  <details id="absbox" style="margin-top:4px"><summary>Full abstract</summary><div id="abs" style="margin-top:6px"></div></details></div>
<div class="card" id="win"></div>
<p class="warn" id="warn"></p>
<details id="more"><summary>Show the full comment</summary><div class="card" id="text"></div></details>
<div class="btns">
  <button data-s="S">Uses as evidence<small>key S or 1</small></button>
  <button data-s="D">Attacks / discredits<small>key D or 2</small></button>
  <button data-s="N">Neutral<small>key N or 3</small></button>
  <button data-s="U">Can't tell<small>key U or 4</small></button>
</div>
<label>Focus (optional): which part of the paper the comment leans on<input type="text" id="focus"></label>
<label>Notes (optional)<input type="text" id="note"></label>
<div class="nav"><button id="prev">&larr; Previous</button><button id="next">Next &rarr;</button><button id="nextOpen">Next unlabelled</button><button id="export">Export CSV</button></div>
<p class="help">The box shows about 300 words around the highlighted link to the paper; open the full comment if you need more context.
Judge how the commenter TREATS this paper, not whether you or they are right about seed oils.
S = uses it as evidence: the paper backs their point ("this study shows...", "here is proof that...").
D = attacks or discredits it: argues against the paper ("that was in rats", "they used margarine", "only observational", "funded by...",
"it doesn't show what you claim"). N = neutral mention or bare link, no position. U = cannot tell.
The paper's conclusion is shown above the comment for the cases where you need it.
Keys: S/D/N/U or 1-4 to label and advance, arrow keys to move. Progress is saved in this browser. Export when done and move
stance_labels.csv to seedoils/data/processed/.</p>
</main>
<script>
const DATA = __DATA__;
const KEY = "stance_labels_v1";
let L = {}, F = {}, N = {}, i = 0;
try { const s = JSON.parse(localStorage.getItem(KEY) || "{}"); L = s.L || {}; F = s.F || {}; N = s.N || {}; i = s.i || 0; } catch (e) {}
function save() { try { localStorage.setItem(KEY, JSON.stringify({L: L, F: F, N: N, i: i})); } catch (e) {} }
const $ = id => document.getElementById(id);
function show() {
  const d = DATA[i];
  $("pos").textContent = "Item " + (i + 1) + " of " + DATA.length + " (id " + d.id + ")";
  const n = Object.keys(L).length; $("done").textContent = n + " labelled";
  $("prog").style.width = (100 * n / DATA.length) + "%";
  $("paper").textContent = d.paper; $("year").textContent = d.year ? "(" + d.year + ")" : "";
  $("concl").textContent = d.concl ? "Paper's conclusion: " + d.concl : "No abstract available.";
  $("abs").textContent = d.abs || ""; $("absbox").open = false; $("absbox").style.display = d.abs ? "" : "none";
  const w = $("win"); w.textContent = "";
  (d.win || "(text not available)").split("[[CITED STUDY LINK]]").forEach((part, k) => {
    if (k > 0) { const m = document.createElement("mark"); m.textContent = "cited study link"; w.appendChild(m); }
    w.appendChild(document.createTextNode(part));
  });
  $("warn").textContent = d.found ? "" : "The link to this paper was not found in the text (often a post whose link is the post itself); showing the start of the text.";
  $("text").textContent = d.text || "(text not available)"; $("more").open = false;
  $("focus").value = F[d.id] || ""; $("note").value = N[d.id] || "";
  document.querySelectorAll("[data-s]").forEach(b => b.classList.toggle("on", L[d.id] === b.dataset.s));
}
function setLabel(s) { L[DATA[i].id] = s; save(); if (i < DATA.length - 1) i++; save(); show(); }
document.querySelectorAll("[data-s]").forEach(b => b.onclick = () => setLabel(b.dataset.s));
$("focus").oninput = e => { F[DATA[i].id] = e.target.value; save(); };
$("note").oninput = e => { N[DATA[i].id] = e.target.value; save(); };
$("prev").onclick = () => { if (i > 0) i--; save(); show(); };
$("next").onclick = () => { if (i < DATA.length - 1) i++; save(); show(); };
$("nextOpen").onclick = () => { const j = DATA.findIndex(d => !L[d.id]); if (j >= 0) i = j; save(); show(); };
document.addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT") return;
  const k = e.key.toUpperCase(), map = {S: "S", D: "D", N: "N", U: "U", "1": "S", "2": "D", "3": "N", "4": "U"};
  if (map[k]) { e.preventDefault(); setLabel(map[k]); }
  else if (e.key === "ArrowLeft") $("prev").click(); else if (e.key === "ArrowRight") $("next").click();
});
$("export").onclick = () => {
  const q = s => '"' + String(s || "").replace(/"/g, '""') + '"';
  const rows = ["item_id,stance,focus,notes"].concat(DATA.map(d => [d.id, L[d.id] || "", q(F[d.id]), q(N[d.id])].join(",")));
  const blob = new Blob([rows.join("\n") + "\n"], {type: "text/csv;charset=utf-8"}); const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = "stance_labels.csv"; document.body.appendChild(a); a.click(); a.remove();
};
show();
</script></body></html>
"""
OUT.write_text(HTML.replace("__DATA__", payload), encoding="utf-8")
print(f"{len(items)} items -> {OUT}")
