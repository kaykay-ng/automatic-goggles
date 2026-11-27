#!/bin/sh
# Build the real PNAS layout WITH the teammate's network_draft.tex pasted into a COPY of body.tex (body.tex itself is not changed), using tectonic (no latexmk needed).
# Output: paper/build_pnas/main_with_network_tectonic.pdf. Run from anywhere:  ./paper/compile_with_network_tectonic.sh
cd "$(dirname "$0")" || exit 1
T=$(mktemp -d) && mkdir -p "$T/figures" && cp main.tex meta.tex body.tex network_draft.tex references.bib "$T"/ && cp figures/*.pdf "$T/figures/" 2>/dev/null
cp pnas_template/pnas-new.cls pnas_template/pnasresearcharticle.sty pnas_template/pnas-new.bst pnas_template/jabbrv.sty pnas_template/jabbrv-ltwa-all.ldf pnas_template/jabbrv-ltwa-en.ldf pnas_template/PNAS_Logo.pdf "$T"/
python3 tools/insert_draft.py . "$T" || exit 1
(cd "$T" && tectonic main.tex) 2>&1 | grep -i -E "^error|Writing|^!|Unable"
mkdir -p build_pnas && cp "$T/main.pdf" build_pnas/main_with_network_tectonic.pdf && echo "wrote paper/build_pnas/main_with_network_tectonic.pdf"
