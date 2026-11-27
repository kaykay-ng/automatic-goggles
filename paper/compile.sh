#!/bin/sh
# Compile the paper on this computer (needs a LaTeX install with latexmk, e.g. MacTeX).
#   ./paper/compile.sh          -> paper/build_pnas/main.pdf  the real PNAS layout (class files from the Overleaf template, in paper/pnas_template/)
#   ./paper/compile.sh preview  -> paper/build/preview.pdf    plain two-column preview (no PNAS class needed)
# Missing figure files do not stop the build (-f); they show as empty boxes.
cd "$(dirname "$0")" || exit 1
if [ "$1" = "preview" ]; then
  mkdir -p build && latexmk -f -pdf -interaction=nonstopmode -outdir=build preview.tex
else
  mkdir -p build_pnas && TEXINPUTS=".:./pnas_template//:" BSTINPUTS=".:./pnas_template//:" latexmk -f -pdf -interaction=nonstopmode -outdir=build_pnas main.tex
fi
