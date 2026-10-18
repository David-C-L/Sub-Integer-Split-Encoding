#!/usr/bin/env python3
"""Bing Maps tile quadkeys, in file order, from the High Resolution Settlement Layer
crowd labels (facebookresearch/HighResolutionSettlementLayer, data/labels.csv.gz; one row
per labelled zoom-15 tile). A quadkey of L base-4 digits q is stored as (1 << 2L) | int(q, 4),
so the level is recoverable from the leading one bit.
Usage: gen_bing_quadkey.py LABELS_CSV_GZ OUT_TXT [N]   (N omitted = every row)"""
import csv, gzip, sys
src, out = sys.argv[1], sys.argv[2]; limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
n = 0
with gzip.open(src, "rt") as f, open(out, "w") as o:
    r = csv.reader(f); next(r)
    for row in r:
        qk = row[1]; o.write(f"{(1 << (2 * len(qk))) | int(qk, 4)}\n"); n += 1
        if limit is not None and n == limit: break
print("rows", n)
