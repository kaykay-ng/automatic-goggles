#!/bin/sh
# Build the 3-slide PDF with tectonic. Run from anywhere: ./paper/slides/compile_slides.sh   -> paper/slides/slides.pdf
cd "$(dirname "$0")" || exit 1
tectonic slides.tex 2>&1 | grep -i -E "^error|Writing|^!|warning: .*Overfull" | head; ls -la slides.pdf | awk '{print "wrote", $9, $5, "bytes"}'
