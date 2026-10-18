#!/usr/bin/env python3
"""Write the 524,288-row prefix of each column as xz-compressed text (one value per line), as the Sec. 2 study and the
524,288-row timing runs read them (first whitespace/comma token of each line, file order).

Usage: make_columns_524k.py <raw_dir> <out_dir> [column ...]
<raw_dir> holds the per-column text files produced by the derivation scripts listed in datasets/README.md,
under the relative paths in SOURCES below. Only the columns whose licence allows redistribution are shipped in
datasets/columns_524k/; the others must be rebuilt from their sources with the same script.
"""
import lzma
import os
import sys

N = 524288
SOURCES = {  # column key -> path under <raw_dir>
    # shipped (redistributable)
    "snowflake": "TwitterSnowflake/twitter_snowflake_10M.csv",
    "uuidv7_hi": "UUIDv7/uuidv7_hi.txt",
    "uuidv7_lo": "UUIDv7/uuidv7_lo.txt",
    "xmark": "XMark/csv/prepost_id_full.txt",
    "quadkey": "BingTiles/quadkey_fileorder.txt",
    "h3_r9": "OSM/csv/h3_r9_fileorder.txt",
    "h3_r15": "OSM/csv/h3_r15_fileorder.txt",
    "s2_l16": "OSM/csv/s2_l16_fileorder.txt",
    "s2_l30": "OSM/csv/s2_l30_fileorder.txt",
    "morton_2x16": "OSM/csv/morton_2x16_fileorder.txt",
    "morton_2x32": "OSM/csv/morton_2x32_fileorder.txt",
    "publicbi_npi": "PublicBI/Medicare1/csv/NPI_full.txt",
    "inat_species_id": "iNaturalist_csv/species_id.txt",
    "ipv4_id": "IPv4/csv/ipv4_id.txt",
    "F1_stocks_usa": "Floats/txt/F1_stocks_usa.txt",
    "F2_food_prices": "Floats/txt/F2_food_prices.txt",
    # not shipped (licence unknown or not stated, or trivially regenerated); rebuild locally
    "instagram": "Instagram/instagram_id_full.txt",
    "publicbi_id1": "PublicBI/Corporations/csv/Id1.txt",
    "publicbi_bene_count": "PublicBI/Medicare1/csv/BENE_COUNT.txt",
    "publicbi_num_employees": "PublicBI/Corporations/csv/num_employees.txt",
    "publicbi_day_supply_bin": "PublicBI/Medicare1/csv/Avg_Day_Supply_Bene_bin.txt",
    "tpch_orderkey": "TPCH/csv/orderkey.txt",
}
SHIPPED = list(SOURCES)[:16]


def main():
    raw, out = sys.argv[1], sys.argv[2]
    cols = sys.argv[3:] or SHIPPED
    os.makedirs(out, exist_ok=True)
    for c in cols:
        src = os.path.join(raw, SOURCES[c])
        vals = []
        with open(src) as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                vals.append(s.split()[0].split(",")[0])
                if len(vals) == N:
                    break
        with lzma.open(os.path.join(out, f"{c}.txt.xz"), "wb", preset=9 | lzma.PRESET_EXTREME) as g:
            g.write(("\n".join(vals) + "\n").encode())
        print(f"{c}: {len(vals)} rows")


if __name__ == "__main__":
    main()
