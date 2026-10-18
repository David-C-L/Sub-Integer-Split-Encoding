#!/usr/bin/env bash
# Restore the experiment folders shipped as <folder>.tar.gz (listed in scripts/packed_data.txt) at their original
# paths. Idempotent: a folder that already exists is left alone. With --columns, also decompress
# datasets/columns_524k/<name>.txt.xz to <name>.txt (about 150 MB; only the dataset and Sec. 2 scripts need them).
set -euo pipefail
cd "$(dirname "$0")/.."
while read -r d; do
  [ -z "$d" ] && continue
  if [ -d "$d" ]; then continue; fi
  echo "unpack $d"
  tar -xzf "$d.tar.gz" -C "$(dirname "$d")"
done < scripts/packed_data.txt
if [ "${1:-}" = "--columns" ]; then
  for f in datasets/columns_524k/*.txt.xz; do
    [ -f "${f%.xz}" ] || { echo "unpack ${f%.xz}"; xz -dkc "$f" > "${f%.xz}"; }
  done
fi
