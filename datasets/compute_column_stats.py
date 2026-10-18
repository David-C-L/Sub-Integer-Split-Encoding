#!/usr/bin/env python3
"""Row counts and exact distinct ratios behind Table 2 (tab:eval_setup).

Usage: compute_column_stats.py <datasets_root> <out.csv>

For each column, reads the text file (one value per line, file order) and reports
  rows_in_file   lines in the file;
  rows_used      rows the paper reports for that column: the full-length row count of the Sec. 7 size runs for
                 integer columns (XMark is run on its first 10,000,000 rows), and the 524,288-row study file for
                 floats (POI-lat: its full 424,205 rows);
  distinct_used  exact number of distinct values among those rows (integers parsed as Python int, so values
                 above INT64_MAX are kept; doubles compared by their 64-bit pattern);
  distinct_ratio distinct_used / rows_used.
Exact (Python set), no sampling. Paths are relative to <datasets_root>, laid out as in datasets/README.md.
"""
import csv
import os
import struct
import sys
import time

COLUMNS = [  # name, path under <datasets_root>, kind, rows_used (None = whole file)
    ("snowflake", "TwitterSnowflake/csv/tweet_id_full.txt", "int", 10_000_000),
    ("xmark_prepost_full", "XMark/csv/prepost_id_full.txt", "int", 10_000_000),
    ("osm_h3_r9_fileorder", "OSM/csv/h3_r9_fileorder.txt", "int", 10_000_000),
    ("osm_s2_l30_fileorder", "OSM/csv/s2_l30_fileorder.txt", "int", 10_000_000),
    ("bing_quadkey", "BingTiles/csv/quadkey_fileorder_full.txt", "int", 9_869_460),
    ("uuidv7_hi", "UUIDv7/csv/uuidv7_hi_10M.txt", "int", 10_000_000),
    ("publicbi_npi", "PublicBI/Medicare1/csv/NPI_full.txt", "int", 17_290_144),
    ("publicbi_id1", "PublicBI/Corporations/csv/Id1.txt", "int", 739_754),
    ("uuidv7_lo", "UUIDv7/csv/uuidv7_lo_10M.txt", "int", 10_000_000),
    ("F1_stocks_usa", "Floats/txt/F1_stocks_usa.txt", "double", None),
    ("F5_city_temp", "Floats/txt/F5_city_temp.txt", "double", None),
    ("F6_air_pressure", "Floats/txt/F6_air_pressure.txt", "double", None),
    ("F8_poi_lat", "Floats/txt/F8_poi_lat.txt", "double", None),
    ("F10_medicare_calc", "Floats/txt/F10_medicare_calc_9030826185528129.txt", "double", None),
]


def key(tok, kind):
    if kind == "int":
        return int(tok)
    return struct.unpack("<Q", struct.pack("<d", float(tok)))[0]


def main():
    root, out = sys.argv[1], sys.argv[2]
    names = set(sys.argv[3:])
    rows = []
    for name, rel, kind, used in COLUMNS:
        if names and name not in names:
            continue
        t0 = time.time()
        seen, n_file, n_used = set(), 0, 0
        path = f"{root}/{rel}"
        if not os.path.exists(path) and "/txt/" in rel:  # some copies keep the float files directly in Floats/
            path = f"{root}/{rel.replace('/txt/', '/')}"
        with open(path) as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                n_file += 1
                if used is None or n_used < used:
                    seen.add(key(s.split()[0].split(",")[0], kind))
                    n_used += 1
        if used is not None and n_used != used:
            raise SystemExit(f"{name}: file has {n_used} rows, expected {used}")
        rows.append(dict(column=name, kind=kind, rows_in_file=n_file, rows_used=n_used,
                         distinct_used=len(seen), distinct_ratio=len(seen) / n_used))
        print(f"{name}: {n_used:,} rows used of {n_file:,}, {len(seen):,} distinct "
              f"({len(seen) / n_used:.4f}) in {time.time() - t0:.0f}s", flush=True)
        del seen
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
