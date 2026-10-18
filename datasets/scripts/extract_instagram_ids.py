#!/usr/bin/env python3
"""RECONSTRUCTED from the dataset's README (the original extraction script was not kept).
Reads ig_all.csv from the Kaggle archive ig_all.csv.zip with a CSV reader (content fields contain newlines)
and writes the `_id` field (Instagram media ID) unchanged, one per line, in file order.
Usage: extract_instagram_ids.py ig_all.csv.zip instagram_id_full.txt
"""
import csv
import io
import sys
import zipfile

csv.field_size_limit(sys.maxsize)
src, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(src) as z:
    member = next(n for n in z.namelist() if n.endswith("ig_all.csv"))
    with z.open(member) as raw, open(out, "w") as o:
        r = csv.reader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
        i = next(r).index("_id")
        n = 0
        for row in r:
            o.write(row[i] + "\n"); n += 1
print(out, n)
