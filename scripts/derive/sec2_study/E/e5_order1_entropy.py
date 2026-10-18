"""E5: order-0/order-1 entropy per range of each E4 partition (study_20261001/E, 2026-10-02).

Reuses C1's range_row logic (order-0, delta, order-1 conditional entropy, *_reliable flag)
unchanged, applied to the IEEE partition (a), front-bits partition (b) and data-chosen
partition (c) from E4, for each float column, file order vs shuffled (seed 0) -- the same
file-vs-shuffled comparison C2 uses as its headline test (order-1 reduction a shuffled copy
loses).

Output: csv/structure_measure_float.csv.
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import float_common as F  # noqa: E402

C_SCRIPTS = os.path.join(F.STUDY_DIR, "C", "scripts")
sys.path.insert(0, C_SCRIPTS)
import c1_structure_measure as C1  # noqa: E402  (range_row)

OUT = F.E_DIR


def ranges_for(name, b_front, data_partition):
    ieee = [(63, 64), (52, 63), (0, 52)]
    if 0 < b_front < 64:
        front = [(64 - b_front, 64), (0, 64 - b_front)]
    else:
        front = [(0, 64)]
    data = [tuple(r) for r in data_partition]
    return dict(SPLIT_IEEE_a=ieee, SPLIT_FRONT_b=front, SPLIT_DATA_c=data)


def process(name, v, order, b_front, data_partition):
    """order: 'file' or 'shuffled'. Returns list of row dicts (one per range per partition)."""
    out = []
    parts = ranges_for(name, b_front, data_partition)
    for pname, ranges in parts.items():
        for i, (lo, hi) in enumerate(ranges):
            next_v = F.A.field(v, *ranges[i + 1]) if i + 1 < len(ranges) else None
            row, proxy, rel = C1.range_row(name, f"{pname}:{order}", lo, hi, v, next_v=next_v)
            row["order"] = order
            row["partition"] = pname
            out.append(row)
    return out


def main():
    t0 = time.time()
    with open(os.path.join(OUT, "csv", "e1_data_chosen_partitions.json")) as fh:
        data_partitions = json.load(fh)
    fields = pd.read_csv(os.path.join(OUT, "csv", "float_fields.csv")).set_index("column")

    all_rows = []
    for name in F.ORDERED_NAMES:
        _, v = F.load_bits(name)
        b_front = int(fields.loc[name, "leading_bits_stable_min"])
        data_partition = data_partitions[name]

        rows_file = process(name, v, "file", b_front, data_partition)
        rng = np.random.default_rng(0)
        vs = v.copy()
        rng.shuffle(vs)
        rows_shuf = process(name, vs, "shuffled", b_front, data_partition)

        all_rows.extend(rows_file)
        all_rows.extend(rows_shuf)
        print(f"done: {name}", file=sys.stderr)

    df = pd.DataFrame(all_rows)
    df.insert(0, "class_label", df["column"].map(lambda n: F.FLOATS[n]["class_label"]))
    df.to_csv(os.path.join(OUT, "csv", "structure_measure_float.csv"), index=False)
    dt = time.time() - t0
    print(f"wrote csv/structure_measure_float.csv ({len(df)} rows, {dt:.1f}s)")


if __name__ == "__main__":
    main()
