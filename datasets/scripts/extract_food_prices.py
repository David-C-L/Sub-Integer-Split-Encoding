#!/usr/bin/env python3
"""RECONSTRUCTED from the float README (no script was kept). WFP Food Prices (HDX, CC BY-IGO):
csv.DictReader over wfpvam_foodprices.csv, float(row["mp_price"]) for the first 524,288 non-empty values in file
order, written "%.17g" per line. Usage: extract_food_prices.py wfpvam_foodprices.csv F2_food_prices.txt"""
import csv
import sys

src, out, n = sys.argv[1], sys.argv[2], 524288
k = 0
with open(src, newline="", encoding="utf-8") as f, open(out, "w") as o:
    for row in csv.DictReader(f):
        v = (row.get("mp_price") or "").strip()
        if not v:
            continue
        o.write("%.17g\n" % float(v)); k += 1
        if k == n:
            break
print(out, k)
