#!/bin/bash
# Stream ParlaMint-XX-en.ana.tgz (CLARIN.SI, hdl 11356/2006, CC BY 4.0) and keep ONLY the plain-text
# part (speeches + metadata TSVs). Transfers ~56 GB, stores ~5-6 GB. Resumable: finished countries are skipped.
# Run from final_project/:  bash notebooks/fetch_parlamint_en_txt.sh
set -u
OUT=data/raw/parlamint_en_txt
BASE=https://www.clarin.si/repository/xmlui/bitstream/handle/11356/2006
mkdir -p "$OUT"
for c in AT BA BE BG CZ DK EE ES FI FR GB GR HR HU IS IT LV NL NO PL PT RS SE SI TR UA; do
  if [ -f "$OUT/.done_$c" ]; then echo "$(date +%T) skip $c"; continue; fi
  if [ "$c" = LV ] && [ -d data/raw/parlamint_pilot/en/ParlaMint-LV-en.txt ]; then
    cp -R data/raw/parlamint_pilot/en/ParlaMint-LV-en.txt "$OUT/" && touch "$OUT/.done_LV" && echo "$(date +%T) LV copied from pilot"; continue
  fi
  ok=0
  for try in 1 2 3; do
    echo "$(date +%T) $c try $try"
    rm -rf "$OUT/ParlaMint-$c-en.txt"
    if curl -sSL -f --retry 3 --connect-timeout 30 --speed-limit 200000 --speed-time 90 "$BASE/ParlaMint-$c-en.ana.tgz" | tar -xzf - -C "$OUT" --include '*-en.txt*' \
       && [ -d "$OUT/ParlaMint-$c-en.txt" ]; then ok=1; break; fi
  done
  if [ $ok = 1 ]; then touch "$OUT/.done_$c"; echo "$(date +%T) $c done $(du -sh "$OUT/ParlaMint-$c-en.txt" | cut -f1)"; else echo "$(date +%T) $c FAILED"; fi
done
echo "$(date +%T) ALL FINISHED"
