#!/bin/sh
# Build the PNAS paper WITH network_draft.tex pasted in, from a temporary copy (body.tex is not changed).
# Output: paper/build_pnas/main_with_network_draft.pdf. Run from anywhere:  ./paper/compile_draft.sh
cd "$(dirname "$0")" || exit 1
T=$(mktemp -d) && cp -R main.tex meta.tex body.tex references.bib network_draft.tex figures pnas_template "$T"/ && python3 tools/insert_draft.py . "$T" || exit 1
(cd "$T" && TEXINPUTS=".:./pnas_template//:" BSTINPUTS=".:./pnas_template//:" latexmk -f -pdf -interaction=nonstopmode -outdir=build main.tex > build.log 2>&1)
mkdir -p build_pnas && cp "$T/build/main.pdf" build_pnas/main_with_network_draft.pdf && echo "wrote paper/build_pnas/main_with_network_draft.pdf ($(grep -o '([0-9]* pages' "$T/build/main.log" | tr -d '('))"
grep -n "^!" "$T/build/main.log" | grep -v "fig1_themes\|fig2_checks" | head -5
rm -rf "$T"
