#!/usr/bin/env python3
"""RECONSTRUCTED (the original export script was not kept). Writes the first N values of one parquet column as
text, one value per line, in row order. Verified to reproduce the text files used in the paper byte for byte:
  TPC-H orderkey : lineitem_orderkey_int32.parquet (generate_orderkey_id.py)      -> TPCH/csv/orderkey.txt
  IPv4           : dbip_ipv4_shuffled.parquet (extract_ip_cols.py), --unsigned32  -> IPv4/csv/ipv4_id.txt
  iNaturalist    : iNaturalist_species_ids.parquet (read_bgif_data.py)            -> iNaturalist_csv/species_id.txt
Usage: export_parquet_prefix.py IN.parquet OUT.txt [--column NAME] [--rows 1000000] [--unsigned32]
"""
import argparse

import pyarrow.parquet as pq

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("out")
ap.add_argument("--column", default=None, help="default: the only/first column")
ap.add_argument("--rows", type=int, default=1_000_000)
ap.add_argument("--unsigned32", action="store_true", help="print int32 values as uint32")
a = ap.parse_args()
t = pq.read_table(a.src, columns=[a.column] if a.column else None)
col = t.column(0).slice(0, a.rows).to_pylist()
with open(a.out, "w") as f:
    for v in col:
        f.write(f"{(v & 0xFFFFFFFF) if a.unsigned32 else v}\n")
print(a.out, len(col))
