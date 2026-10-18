#!/usr/bin/env bash
# Downloads the TSPLIB instances used in the notebook and unpacks them here.
set -euo pipefail
cd "$(dirname "$0")"
BASE=https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp
for f in att48.tsp berlin52.tsp brazil58.tsp gr48.tsp burma14.tsp gr17.tsp eil51.tsp \
         att48.opt.tour berlin52.opt.tour eil51.opt.tour gr48.opt.tour brazil58.opt.tour; do
    if [ ! -f "$f" ]; then
        if curl -fsSL "$BASE/$f.gz" -o "$f.gz"; then
            gunzip -f "$f.gz"
            echo "ok   $f"
        else
            rm -f "$f.gz"
            echo "skip $f (not published)"
        fi
    fi
done
