#!/bin/sh
# Compile the plain preview of the paper on this computer (needs tectonic: brew install tectonic). Output: paper/build/preview.pdf
# The PNAS version (main.tex) is compiled on Overleaf, where the PNAS template provides pnas-new.cls.
cd "$(dirname "$0")" && mkdir -p build && tectonic --outdir build preview.tex
