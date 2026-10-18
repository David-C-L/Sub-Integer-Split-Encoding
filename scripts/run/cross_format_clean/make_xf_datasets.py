#!/usr/bin/env python3
"""Cross-format inputs: the leading ROWS values of each column, file order.

Writes, per column,
  OUT/txt/<name>.txt            one value per line (BtrBlocks --dataset NAME=PATH)
  OUT/fls/<name>/generated.csv  + schema.json + README.MD (FastLanes), written
                                with FastLanes' own scripts/make_cross_format_datasets.write_dataset
  OUT/fls/manifest.csv          for FLS_SUBINTSPLIT_MANIFEST

Both harnesses read signed int64. A value >= 2^63 (only uuidv7_lo, all of it)
is written as its two's-complement int64, i.e. the same 64-bit pattern, so
bit-range sections see identical bits; since every uuidv7_lo value has the top
bit set, signed order equals unsigned order and min/max-based codecs see the
same spread. All columns are INT64 in FastLanes (its script types npi/id1 as
INT32; INT64 here keeps the element width equal to Nimble's uint64 and
BtrBlocks' 64-bit arm).
"""
import argparse, os, sys

COLUMNS = [  # nimble name, source relative to Datasets/
    ("snowflake", "TwitterSnowflake/csv/tweet_id.txt"),
    ("xmark_prepost_full", "XMark/csv/prepost_id_full.txt"),
    ("osm_h3_r9_fileorder", "OSM/csv/h3_r9_fileorder.txt"),
    ("osm_s2_l30_fileorder", "OSM/csv/s2_l30_fileorder.txt"),
    ("bing_quadkey", "BingTiles/csv/quadkey_fileorder.txt"),
    ("uuidv7_hi", "UUIDv7/csv/uuidv7_hi.txt"),
    ("uuidv7_lo", "UUIDv7/csv/uuidv7_lo.txt"),
    ("publicbi_npi", "PublicBI/Medicare1/csv/NPI.txt"),
    ("publicbi_id1", "PublicBI/Corporations/csv/Id1.txt"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", required=True)
    ap.add_argument("--fastlanes", required=True, help="FastLanes checkout")
    ap.add_argument("--out", required=True)
    ap.add_argument("--rows", type=int, default=524288)
    a = ap.parse_args()
    sys.path.insert(0, os.path.join(a.fastlanes, "scripts"))
    import make_cross_format_datasets as fls  # reuse the repo's writer
    os.makedirs(os.path.join(a.out, "txt"), exist_ok=True)
    manifest = ["name,dir,type"]
    for name, rel in COLUMNS:
        vals = []
        with open(os.path.join(a.datasets, rel)) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                v = int(line)
                if not 0 <= v < 2**64:
                    sys.exit(f"{name}: {v} is not uint64")
                vals.append(v - 2**64 if v >= 2**63 else v)
                if len(vals) == a.rows:
                    break
        if len(vals) != a.rows:
            sys.exit(f"{name}: only {len(vals)} rows")
        with open(os.path.join(a.out, "txt", name + ".txt"), "w") as f:
            f.write("\n".join(map(str, vals)) + "\n")
        fdir = os.path.join(a.out, "fls", name)
        fls.write_dataset(os.path.join(a.out, "fls"), name, vals, "INT64",
                          f"{name} from Datasets/{rel}", "file")
        manifest.append(f"{name},{fdir},INT64")
        wrapped = sum(v < 0 for v in vals)
        print(f"{name:22s} rows={len(vals)} wrapped_to_signed={wrapped}")
    with open(os.path.join(a.out, "fls", "manifest.csv"), "w") as f:
        f.write("\n".join(manifest) + "\n")


if __name__ == "__main__":
    main()
