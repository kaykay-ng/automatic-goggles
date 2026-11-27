#!/bin/sh
# Build the real PNAS layout (main.tex) with tectonic, no latexmk needed. Copies the files to a temporary folder together with the PNAS class files, builds there, and copies the PDF to paper/build_pnas/main_tectonic.pdf.
# Run from anywhere:  ./paper/compile_pnas_tectonic.sh     (needs: brew install tectonic; figures that are missing in paper/figures stop the build)
cd "$(dirname "$0")" || exit 1
T=$(mktemp -d) && mkdir -p "$T/figures" && cp main.tex meta.tex body.tex references.bib "$T"/ && cp figures/*.pdf "$T/figures/" 2>/dev/null
cp pnas_template/pnas-new.cls pnas_template/pnasresearcharticle.sty pnas_template/pnas-new.bst pnas_template/jabbrv.sty pnas_template/jabbrv-ltwa-all.ldf pnas_template/jabbrv-ltwa-en.ldf pnas_template/PNAS_Logo.pdf "$T"/
(cd "$T" && tectonic main.tex) 2>&1 | grep -i -E "^error|Writing|^!"
mkdir -p build_pnas && cp "$T/main.pdf" build_pnas/main_tectonic.pdf && echo "wrote paper/build_pnas/main_tectonic.pdf"
