# Paper (PNAS format, due Friday 27 Nov 2026, 23:59, six pages including figures and references)

Files
- `meta.tex`: title, abstract, significance statement, keywords, author contributions (one place for both versions).
- `body.tex`: Introduction, Results, Discussion, Methods. Write the paper here.
- `references.bib`: starting references for the methods used; check every entry before submitting.
- `figures/`: put the three figures here as PDF.
- `main.tex`: the PNAS version for Overleaf (needs the PNAS class from the Overleaf template; untested here).
- `preview.tex`: a plain two-column version that compiles on this computer so you can check text and rough length.
- `compile.sh`: builds `build/preview.pdf` with Tectonic (installed with `brew install tectonic`).
- `REPORT_PLAN.md`: requirements, what to put where, and the numbers.

Compile here: `./paper/compile.sh` from the repo root (first run downloads LaTeX support files). The preview is not the PNAS layout; its page count is only a rough guide.

Overleaf: the PNAS template is not available from this computer. `main.tex` follows PNAS's research-report example (`Research_report.tex`, template type pnasresearcharticle). In Overleaf open the PNAS template, keep its class files, add `meta.tex`, `body.tex`, `references.bib` and `figures/`, and replace its `main.tex` with this one.
The course requires the PNAS template in LaTeX; check the exact name and the six-page limit on the course site.
