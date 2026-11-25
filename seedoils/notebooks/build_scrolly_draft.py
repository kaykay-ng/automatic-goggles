"""Builds the scroll-story (scrollyteller) draft of the 'Seed Oil Debate' artifact from the dashboard page seedoils/artifact/index.html.

Run from final_project/:  ../.venv/bin/python seedoils/notebooks/build_scrolly_draft.py
  -> seedoils/artifact/draft_scrolly.html (the page) and <scratchpad>/store/draft_index.json ({"text": page}, for the artifact store document drafts/<id>/files/index.html)
The draft reads the dashboard's own datasets by id. It reuses the dashboard's chart code: each drawing becomes a plain render function R[name](el); one sticky stage
re-renders the chart of the chapter in view (IntersectionObserver with root: document), and each chapter also holds its own chart for printing.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp")
src = (ROOT / "artifact" / "index.html").read_text(encoding="utf-8")
css_dash = src[src.index("<style>") + 7:src.index("</style>")]
js = src[src.index("<script>") + 8:src.rindex("</script>")]

# 1. drawings -> plain render functions R[name](el), except 'fact' (it stays a drawing)
out, mode = [], False
for line in js.split("\n"):
    m = re.match(r"^  dash\.draw\('([\w-]+)', \(el\) => \{$", line)
    if m and m.group(1) != "fact":
        out.append(f"  R['{m.group(1)}'] = (el) => {{")
        mode = True
        continue
    if mode and line == "  });":
        out.append("  };")
        mode = False
        continue
    out.append(line)
js = "\n".join(out)
js = re.sub(r"\n  listen\('[^']+', '[^']+', \[[^\]]*\]\);", "", js)
js = js.replace("  const state = {", "  const R = {};\n  const state = { step: 0, printing: false, maxH: null, maxRows: null,")
js = js.replace("narrow = W < 560, H = Math.round(narrow ? Math.max(420, W * 1.15) : Math.max(340, Math.min(700, W * 0.8)));",
                "narrow = W < 560, H = Math.min(state.maxH || 9999, Math.round(narrow ? Math.max(420, W * 1.15) : Math.max(340, Math.min(700, W * 0.8))));")
js = js.replace(".sort((a, b) => b[key] - a[key]).slice(0, 10);", ".sort((a, b) => b[key] - a[key]).slice(0, state.maxRows || 10);")
js = js.replace("const W = Math.max(280, el.clientWidth), H = Math.round(Math.min(560, W * 0.95)), pad = 24;",
                "const W = Math.max(280, el.clientWidth), H = Math.min(state.maxH || 9999, Math.round(Math.min(560, W * 0.95))), pad = 24;")
js = js.replace("    rows.sort((x, y) => (y.b - y.a) - (x.b - x.a));\n    dumbbell(el, P, T, rows, { rowH: 22,",
                "    rows.sort((x, y) => (y.b - y.a) - (x.b - x.a));\n    if (state.maxRows) rows = rows.slice(0, state.maxRows / 2).concat(rows.slice(-state.maxRows / 2));\n    dumbbell(el, P, T, rows, { rowH: 22,")
js = js.replace("const rows = g[0].filter((r) => r.group === 'riser'", "let rows = g[0].filter((r) => r.group === 'riser'")
assert "let rows = g[0].filter((r) => r.group" in js
assert js.count("state.maxRows") >= 4 and js.count("state.maxH || 9999") >= 2, "chart patches did not apply"

STAGE = """
  // ------------------------------------------------------------------ the stage: one chart that changes with the chapter
  const CH = [
    { r: 'papermap', t: 'Figure 1. A map of the cited research', o: { mapColor: 'community' } },
    { r: 'papermap', t: 'Figure 1. The same map, by who cites each paper', o: { mapColor: 'side' } },
    { r: 'casefiles', t: 'Figure 2. The case files: the most-cited foundations (PageRank)' },
    { r: 'nullplot', t: 'Figure 2. Observed structure against random networks' },
    { r: 'science', t: 'Figure 3a. What the cited papers conclude, by kind of evidence' },
    { r: 'online', t: 'Figure 3b. What each community says: are seed oils harmful?' },
    { r: 'matching', t: 'Figure 3c. What kind of evidence each position cites' },
    { r: 'topics', t: 'Figure 4. Topics in r/StopEatingSeedOils: share of discussion', o: { topicSub: 'r/StopEatingSeedOils', topicMetric: 'share' } },
    { r: 'topics', t: 'Figure 4. The same themes: how well comments are received', o: { topicSub: 'r/StopEatingSeedOils', topicMetric: 'vote' } },
    { r: 'emotion', t: 'Figure 5. Hostile comments, before and from 2024', o: { emo: 'hostile_pct' } },
    { r: 'cocnet', t: 'Figure 6. Where seed-oil commenters also post' },
    { r: 'cocshare', t: 'Figure 6. Biggest risers and fallers', o: { maxRows: 16 } },
    { r: 'cocshare', t: 'Figure 6. Biggest risers and fallers', o: { maxRows: 16 } }
  ];

  // ------------------------------------------------------------------ case files: top papers by PageRank, joined by red string
  R.casefiles = (el) => {
    const g = guard(el, ['bridges', 'paper_nodes', 'paper_edges', 'paper_communities']); if (!g) return;
    const [br, nodes, edges, comms] = g;
    const key = (t) => (t || '').toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 30);
    const byTitle = new Map(nodes.map((n) => [key(n.title), n]));
    const top = br.filter((r) => r.top_pagerank).sort((a, b) => b.pagerank - a.pagerank).slice(0, 4)
      .map((r, k) => ({ r, k, n: byTitle.get(key(r.title)) }));
    const adj = new Map(); edges.forEach((e) => { (adj.get(e.s) || adj.set(e.s, []).get(e.s)).push(e.t); (adj.get(e.t) || adj.set(e.t, []).get(e.t)).push(e.s); });
    function hops(a, b) {
      if (a == null || b == null) return null;
      const d = new Map([[a, 0]]), q = [a];
      while (q.length) { const u = q.shift(); if (u === b) return d.get(u); (adj.get(u) || []).forEach((v) => { if (!d.has(v)) { d.set(v, d.get(u) + 1); q.push(v); } }); }
      return null;
    }
    const cname = new Map(comms.map((c) => [c.c, c.name]));
    const side = { SESO: 'CITED IN r/STOP ONLY', both: 'CITED IN BOTH', SciNut: 'CITED IN r/SCI ONLY' };
    el.replaceChildren();
    const wrap = document.createElement('div'); wrap.className = 'cf-wrap';
    const grid = document.createElement('div'); grid.className = 'cf-grid';
    top.forEach((t) => {
      const f = document.createElement('div'); f.className = 'cf-file'; f.style.setProperty('--tilt', ((t.k % 2 ? 1 : -1) * (0.6 + 0.3 * t.k)) + 'deg');
      const tab = document.createElement('div'); tab.className = 'cf-tab'; tab.textContent = t.n ? (cname.get(t.n.c) || 'community ' + t.n.c) : 'unplaced';
      const pin = document.createElement('i'); pin.className = 'cf-pin'; tab.appendChild(pin);
      const st = document.createElement('div'); st.className = 'cf-stamp'; st.textContent = side[t.r.side] || '';
      const sheet = document.createElement('div'); sheet.className = 'cf-sheet';
      const h = document.createElement('b'); h.textContent = t.r.title;
      const y = document.createElement('small'); y.textContent = (t.r.year || '') + '';
      const pr = document.createElement('div'); pr.className = 'cf-pr'; pr.textContent = 'PageRank ' + t.r.pagerank.toFixed(4);
      const u = document.createElement('small'); u.textContent = t.r.users_seso + ' in r/StopEatingSeedOils, ' + t.r.users_scinut + ' in r/ScientificNutrition';
      sheet.append(h, y, pr, u);
      const no = document.createElement('div'); no.className = 'cf-no'; no.textContent = 'PR-' + String(t.k + 1).padStart(3, '0');
      f.append(tab, st, sheet, no); grid.appendChild(f); t.el = f; t.pin = pin;
    });
    wrap.appendChild(grid);
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('class', 'cf-string'); svg.setAttribute('aria-hidden', 'true');
    wrap.appendChild(svg); el.appendChild(wrap);
    const note = document.createElement('p'); note.className = 'cf-note';
    note.textContent = 'Solid string: the two papers are directly linked. Dashed: not directly linked, with the number of steps through other papers. The cited-by counts are people on Reddit and play no part in the rank.';
    el.appendChild(note);
    requestAnimationFrame(() => {
      const wr = wrap.getBoundingClientRect(); svg.setAttribute('width', wr.width); svg.setAttribute('height', wr.height);
      const pos = top.map((t) => { const b = t.pin.getBoundingClientRect(); return [b.left - wr.left + b.width / 2, b.top - wr.top + b.height / 2]; });
      for (let i = 0; i + 1 < top.length; i++) {
        const [x1, y1] = pos[i], [x2, y2] = pos[i + 1];
        const hp = hops(top[i].n && top[i].n.i, top[i + 1].n && top[i + 1].n.i);
        const sag = Math.max(26, Math.abs(x2 - x1) * 0.18 + Math.abs(y2 - y1) * 0.5);
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', 'M' + x1 + ',' + y1 + ' Q' + (x1 + x2) / 2 + ',' + (Math.max(y1, y2) + sag) + ' ' + x2 + ',' + y2);
        path.setAttribute('class', 'cf-thread' + (hp === 1 ? '' : ' cf-dash')); svg.appendChild(path);
        const lab = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        lab.setAttribute('x', (x1 + x2) / 2); lab.setAttribute('y', (y1 + y2) / 2 + sag / 2 + 14); lab.setAttribute('text-anchor', 'middle'); lab.setAttribute('class', 'cf-lab');
        lab.textContent = hp === 1 ? 'directly linked' : hp == null ? 'no path found' : hp + ' steps apart'; svg.appendChild(lab);
      }
      top.forEach((t, i) => { const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle'); c.setAttribute('cx', pos[i][0]); c.setAttribute('cy', pos[i][1]); c.setAttribute('r', 5); c.setAttribute('class', 'cf-knot'); svg.appendChild(c); });
    });
  };
  function paint(el, n) {
    const ch = CH[n];
    el.replaceChildren();
    Object.assign(state, { maxH: null, maxRows: null }, ch.o || {});
    if (!state.printing) { const h = el.clientHeight; state.maxH = h > 260 ? h - 70 : null; }
    R[ch.r](el);
    if (ch.r === 'bridges') { const lg = document.createElement('div'); lg.className = 'sod-legend'; el.prepend(lg); R.sidelegend(lg); }
    const t = document.createElement('h3'); t.textContent = ch.t; el.prepend(t);
  }
  dash.draw('stage', (el) => paint(el, state.step));
  dash.draw('printfig', (el) => { el.replaceChildren(); if (state.printing) paint(el, Number(el.dataset.step)); });
  window.addEventListener('beforeprint', () => { state.printing = true; dash.draw('printfig'); });
  window.addEventListener('afterprint', () => { state.printing = false; dash.draw('printfig'); dash.draw('stage'); });
  const steps = Array.from(document.querySelectorAll('.st-step'));
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (!e.isIntersecting) return;
      const i = Number(e.target.dataset.i);
      if (i === state.step) return;
      state.step = i;
      steps.forEach((s, k) => s.classList.toggle('is-on', k === i));
      dash.draw('stage');
    });
  }, { root: document, rootMargin: '-42% 0px -42% 0px', threshold: 0 });
  steps.forEach((s) => io.observe(s));
})();
"""
js = js.rstrip()
assert js.endswith("})();")
js = js[:-len("})();")] + STAGE


def F(key):
    return f'<b data-draw="fact" data-source="facts" data-field="value" data-where="key={key}">—</b>'


SRC = "paper_nodes paper_edges paper_communities community_links bridges null_summary null_runs science online matching topic_themes emotion cocomment_nodes cocomment_edges cocomment_share"
CHAPTERS = [
    ("One body of research", f"We kept the {F('n_papers_net')} papers that at least two people cited in these subreddits, and joined two papers when one cites the other. Papers that mostly cite each other form communities. Four carry the seed-oil argument: omega-6 and linoleic acid, old rodent studies, saturated fat, and LDL cholesterol."),
    ("Both camps cite the same papers", "Colour each paper by who cites it. The papers cited only in r/StopEatingSeedOils sit inside the nutrition literature, not beside it, and the papers both camps cite are the ones that join the communities."),
    ("The papers everything leads back to", "PageRank scores a paper higher when many well-cited papers lead to it. These four folders are the top-scoring papers, and the red string joins them in rank order: solid where the two are directly linked in the citation network, dashed where the shortest path runs through other papers. The stamp says who cites the paper on Reddit. A foundation of the literature is not always one Reddit argues about."),
    ("Not an accident of the data", f"The citation network has modularity {F('mod_sch')}. Random networks with the same links per paper reach {F('mod_sch_null')}. Papers that one side cites far more than the other sort into separate communities: side assortativity is {F('assort_sch')}, against 0 for random."),
    ("What the research says", f"Among human trials and meta-analyses, {F('trial_benefit')} conclude benefit and {F('trial_harm')} harm. Among animal and cell studies, {F('animal_harm')} conclude harm. We labelled the conclusion of each paper from its abstract. These are the papers Reddit cites, not all research."),
    ("What each community says", f"Among comments that take a position, r/StopEatingSeedOils was {F('seso_harm_pre')} harmful before 2024 and {F('seso_harm_from')} from 2024. r/ScientificNutrition went from {F('scinut_harm_pre')} harmful to {F('scinut_harm_from')}."),
    ("What each side cites", f"Comments that call seed oils harmful rest on animal or cell studies {F('harm_cites_animal')} of the time. Comments that call them not harmful cite human trials {F('notharm_cites_trials')} of the time."),
    ("The conversation changed in 2024", f"A topic model of {F('n_docs_seso')} comments and posts in r/StopEatingSeedOils shows what the argument became. Politics, led by RFK Jr., grew {F('politics_ratio')} in share from 2024, while omega-6 biochemistry fell to {F('biochem_ratio')} of its earlier share."),
    ("What gets rewarded", "The same themes scored by how well their comments are received in their own threads (0.5 is typical). Vaccines and studies and evidence are the two lowest from 2024."),
    ("The tone", f"Hostile comments (anger, annoyance, disapproval, disgust) rose in r/StopEatingSeedOils from {F('host_seso_pre')} to {F('host_seso_from')}, and stayed near {F('host_scinut_from')} in r/ScientificNutrition. The sharpest rise is in arguments about studies and evidence: {F('host_evid_pre')} to {F('host_evid_from')}. The classifier is provisional."),
    ("A new crowd", f"{F('seso_new')} of r/StopEatingSeedOils commenters from 2024 had not commented there before, and so had {F('scinut_new')} of r/ScientificNutrition. Its share of commenters who also post in r/carnivore fell from {F('seso_carn_pre')} to {F('seso_carn_from')}. <span class=\"sod-note\">Preliminary: {F('cocomment_fetched')} of {F('cocomment_total')} selected commenters fetched so far.</span>"),
    ("Where they went", "For the heaviest seed-oil commenters, the chart shows the subreddits where the share who are also active grew most and shrank most from 2024. This figure will be rebuilt when the commenter fetch is complete."),
    ("What to be careful about", "The labels of paper conclusions and comment positions were made blind by Claude subagents and have not been checked by a human. The papers are the ones Reddit cites. Several samples are small, the emotion classifier is provisional, and the last figure is preliminary."),
]
steps_html = ""
for i, (h, p) in enumerate(CHAPTERS):
    on = " is-on" if i == 0 else ""
    steps_html += f"""    <section class="st-step{on}" data-i="{i}">
      <h2>{h}</h2>
      <p>{p}</p>
      <div class="sod-chart st-printfig" data-draw="printfig" data-step="{i}" data-source="{SRC}"></div>
    </section>
"""

CSS_EXTRA = """
/* Scroll story: chapters scroll beside (wide) or under (narrow) one sticky chart that changes with them. */
.st { container-type: inline-size; max-width: 1080px; margin: 0 auto; font-family: var(--font-anthropic-sans); color: var(--color-fg); }
.st h1 { font-family: var(--font-anthropic-serif); font-weight: 400; font-size: clamp(30px, 6cqi, 48px); line-height: 1.08; margin: 6px 0 14px; text-wrap: balance; }
.st h2 { font-family: var(--font-anthropic-serif); font-weight: 400; font-size: clamp(22px, 3.6cqi, 30px); line-height: 1.15; margin: 0 0 10px; text-wrap: balance; }
.st h3 { font-size: 14px; font-weight: 500; margin: 0 0 6px; }
.st p { line-height: 1.6; margin: 0 0 12px; }
.st-hero { padding: 8px 0 24px; max-width: 64ch; }
.st-grid { display: block; }
.st-stagewrap { position: sticky; top: 0; z-index: 3; background: var(--color-bg); border-bottom: 1px solid var(--color-border-line); padding: 8px 0 10px; }
.st-stage { height: 50vh; overflow: auto; position: relative; container-type: inline-size; }
.st-steps { padding-bottom: 30vh; }
.st-step { min-height: 62vh; padding: 28px 0 0; opacity: .38; }
.st-step.is-on { opacity: 1; }
.st-step p { max-width: 52ch; }
.st-printfig { display: none; container-type: inline-size; }
.sod-note { color: var(--color-fg-muted); font-size: 13px; }
@media (prefers-reduced-motion: no-preference) { .st-step { transition: opacity var(--cds-dur-slow, .3s) var(--cds-ease-out, ease); } }
@container (min-width: 800px) {
  .st-grid { display: grid; grid-template-columns: 5fr 7fr; gap: 0 36px; align-items: start; }
  .st-steps { grid-column: 1; grid-row: 1; padding-bottom: 20vh; }
  .st-stagewrap { grid-column: 2; grid-row: 1; top: 12px; border: 0; padding: 0; }
  .st-stage { height: min(80vh, 720px); border: 1px solid var(--color-border-line); border-radius: var(--cds-radius, 8px); padding: 14px 16px; background: var(--color-bg); }
  .st-step { min-height: 78vh; padding-top: 34vh; }
  .st-step:first-child { padding-top: 12vh; }
}
@media print {
  .st-stagewrap { display: none; }
  .st-grid, .st-steps { display: block; }
  .st-step { opacity: 1; min-height: 0; padding: 0; break-before: page; }
  .st-step:first-child { break-before: auto; }
  .st-printfig { display: block; margin-top: 12px; }
  .sod-ctl { display: none; }
}
.cf-wrap { position: relative; padding: 6px 2px 40px; }
.cf-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; align-items: start; }
@container (max-width: 520px) { .cf-grid { grid-template-columns: repeat(2, 1fr); gap: 36px 10px; } }
.cf-file { position: relative; background: #c8a05a; border-radius: 3px 8px 6px 6px; padding: 26px 8px 22px; transform: rotate(var(--tilt)); box-shadow: 0 6px 12px rgba(0,0,0,.28); color: #1b1710; font-family: var(--font-anthropic-sans); }
.cf-tab { position: absolute; top: -16px; left: 8px; background: #bd9450; border-radius: 4px 4px 0 0; padding: 3px 18px 3px 8px; font: 700 9px/1.2 ui-monospace, Menlo, monospace; letter-spacing: .06em; text-transform: uppercase; max-width: 82%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cf-pin { position: absolute; right: 4px; top: 3px; width: 9px; height: 9px; border-radius: 50%; background: #c0392b; box-shadow: inset -1px -1px 2px rgba(0,0,0,.4); }
.cf-stamp { position: absolute; bottom: 5px; right: 8px; border: 1.5px solid #b23a2e; color: #b23a2e; font: 700 8px/1.2 ui-monospace, Menlo, monospace; padding: 1px 4px; transform: rotate(-4deg); opacity: .85; letter-spacing: .05em; }
.cf-sheet { background: #efe6d2; border-radius: 2px; padding: 8px 8px 7px; margin-top: 8px; min-height: 120px; }
.cf-sheet b { display: block; font-size: 11.5px; line-height: 1.3; font-weight: 600; display: -webkit-box; -webkit-line-clamp: 5; -webkit-box-orient: vertical; overflow: hidden; }
.cf-sheet small { display: block; font-size: 10px; line-height: 1.35; color: #4b4333; margin-top: 4px; }
.cf-pr { margin-top: 6px; font: 700 11px/1.2 ui-monospace, Menlo, monospace; border-top: 1px solid #c9bda2; padding-top: 5px; }
.cf-no { position: absolute; left: 10px; bottom: 5px; background: #efe6d2; font: 9px/1 ui-monospace, Menlo, monospace; padding: 2px 5px; }
.cf-string { position: absolute; inset: 0; pointer-events: none; overflow: visible; }
.cf-thread { fill: none; stroke: #c0392b; stroke-width: 2; stroke-linecap: round; }
.cf-dash { stroke-dasharray: 5 5; }
.cf-knot { fill: #c0392b; stroke: #7d1f15; stroke-width: 1; }
.cf-lab { fill: var(--color-fg); font-size: 11px; }
.cf-note { font-size: 12px; color: var(--color-fg-muted, var(--color-fg)); margin: 4px 0 0; line-height: 1.45; }
"""
html = f"""<meta name="dash-one-writer">
<style>
{css_dash.replace('.sod {', '.sod-unused {')}{CSS_EXTRA}</style>
<div class="st">
  <header class="st-hero">
    <p class="sod-kicker">Reddit and the research it cites, 2018 to 2026</p>
    <h1>Same papers, different evidence, new crowd</h1>
    <p class="sod-lede">The claim that seed oils are harmful moved from a nutrition argument to a political one. We followed it through three subreddits and the {F('n_papers_net')} papers people cite there. Both camps cite the same research, the harm case leans on animal studies, and from 2024 it was argued by mostly new people. Scroll to follow the argument.</p>
  </header>
  <div class="st-grid">
    <div class="st-stagewrap"><div class="st-stage sod-chart" data-draw="stage" data-source="{SRC}"></div></div>
    <div class="st-steps">
{steps_html}    </div>
  </div>
  <p class="sod-foot">Data: Reddit via Arctic Shift, OpenAlex, PubMed. Every figure's data and the script that made it are in Sources.</p>
</div>
<script>
{js}</script>
"""
(ROOT / "artifact" / "draft_scrolly.html").write_text(html, encoding="utf-8")
(STORE / "draft_index.json").write_text(json.dumps({"text": html}), encoding="utf-8")
print(f"{len(html) // 1024} KB; {html.count('data-draw=\"fact\"')} fact marks; {js.count(chr(82) + '[' + chr(39))} render functions; {len(CHAPTERS)} chapters")
