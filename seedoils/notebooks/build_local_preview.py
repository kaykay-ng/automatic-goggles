"""Build a standalone local preview of the dashboard page.

seedoils/artifact/index.html is the source of a claude.ai Dashboard artifact: the host supplies
`dash.data` / `dash.draw` (datasets from the artifact store), d3 and the theme tokens. Opened directly
in a browser none of those exist, so every chart and fact mark stays empty.

This script wraps index.html with stand-ins for all three and inlines the datasets it names
(seedoils/data/processed/artifact/<id>.json, built by artifact_data.py / intro_data.py), so the
result opens from disk with no server:

    ../.venv/bin/python seedoils/notebooks/build_local_preview.py
    open seedoils/artifact/preview_local.html

index.html itself is not changed. Rerun after editing the page or rebuilding the datasets.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "artifact" / "index.html"
DATA = ROOT / "data" / "processed" / "artifact"
OUT = ROOT / "artifact" / "preview_local.html"

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Seed Oil Debate (local preview)</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<style>
/* Stand-ins for the claude.ai host theme tokens the page uses. */
:root {
  --font-anthropic-sans: Inter, system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-anthropic-serif: "Source Serif 4", Georgia, serif;
  --color-bg: #faf9f5; --color-fg: #1f1e1b; --color-fg-muted: #6b6a64;
  --color-panel: #f0eee6; --color-border-line: #dedcd3;
  --cds-chart-grid: #e6e4dc; --cds-radius: 8px;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --color-bg: #1f1e1b; --color-fg: #f0eee6; --color-fg-muted: #a3a29b;
    --color-panel: #2a2926; --color-border-line: #3d3c38; --cds-chart-grid: #34332f;
  }
}
:root[data-theme="dark"] {
  --color-bg: #1f1e1b; --color-fg: #f0eee6; --color-fg-muted: #a3a29b;
  --color-panel: #2a2926; --color-border-line: #3d3c38; --cds-chart-grid: #34332f;
}
html, body { margin: 0; background: var(--color-bg); color: var(--color-fg); }
body { padding: 24px 16px 64px; }
.dash-select { font: inherit; font-size: 13px; padding: 3px 6px; border-radius: 6px;
  border: 1px solid var(--color-border-line); background: var(--color-panel); color: var(--color-fg); }
.dash-skeleton { background: var(--color-panel); border-radius: 8px; min-height: 120px; }
.local-note { max-width: 980px; margin: 0 auto 16px; font: 12px/1.5 var(--font-anthropic-sans);
  color: var(--color-fg-muted); border-bottom: 1px solid var(--color-border-line); padding-bottom: 8px; }
</style>
<script>
/* Minimal stand-in for the host's `dash` runtime: data(id) -> {status, data: rows};
   draw(name, fn) registers and runs fn on every [data-draw=name]; draw(name) redraws. */
window.__DATA__ = __DATA_JSON__;
window.dash = (function () {
  const fns = {};
  function run(name) {
    document.querySelectorAll('[data-draw="' + name + '"]').forEach((el) => {
      try { fns[name](el); } catch (e) { console.error('draw ' + name, e); el.textContent = 'Error in ' + name + ': ' + e.message; }
    });
  }
  let t;
  const redrawAll = () => { clearTimeout(t); t = setTimeout(() => Object.keys(fns).forEach(run), 150); };
  addEventListener('resize', redrawAll);
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', redrawAll);
  return {
    data(id) {
      const d = window.__DATA__[id];
      return d ? { status: 'ok', data: d.rows, meta: d.meta } : { status: 'error', error: 'no dataset ' + id };
    },
    draw(name, fn) { if (fn) fns[name] = fn; if (fns[name]) run(name); }
  };
})();
</script>
</head>
<body>
<p class="local-note">Local preview built by seedoils/notebooks/build_local_preview.py. Theme, fonts and the data runtime are stand-ins for the claude.ai host, so details can differ from the published dashboard.</p>
"""

TAIL = "\n</body>\n</html>\n"


def main():
    page = PAGE.read_text(encoding="utf-8")
    ids = set()
    for m in re.finditer(r'data-source="([^"]+)"', page):
        ids.update(m.group(1).split())
    ids.update(re.findall(r"dash\.data\('([a-z_0-9]+)'\)", page))
    for g in re.findall(r"guard\(el, \[([^\]]+)\]", page):
        ids.update(re.findall(r"'([a-z_0-9]+)'", g))
    data, missing = {}, []
    for i in sorted(ids):
        f = DATA / f"{i}.json"
        if f.exists():
            data[i] = json.loads(f.read_text(encoding="utf-8"))
        else:
            missing.append(i)
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    OUT.write_text(HEAD.replace("__DATA_JSON__", blob) + page + TAIL, encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB), {len(data)} datasets")
    if missing:
        print("MISSING datasets (those figures will say 'Failed to load'):", ", ".join(missing))


if __name__ == "__main__":
    main()
