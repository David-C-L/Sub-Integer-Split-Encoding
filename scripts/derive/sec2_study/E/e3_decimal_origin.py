"""E3: decimal-origin test (ALP Sec. 2.5 style), study_20261001/E, 2026-10-02.

For d = 0..18: fraction of values with round(x * 10^d) / 10^d == x (vectorised numpy).
Report the minimal d reaching 99% round-trip. Also per-1024-vector stats for the chosen d
(fraction of the vector that round-trips, as a decimal_vector_stats analogue of ALP's
per-vector exponent/factor stability -- no ALP encoder, just the arithmetic check).

Outputs: csv/decimal_origin.csv (column, d, frac), csv/decimal_vector_stats.csv.
"""
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import float_common as F  # noqa: E402

OUT = F.E_DIR
VEC = 1024
D_MAX = 18


def round_trip_frac(x, d):
    scale = 10.0 ** d
    scaled = np.round(x * scale)
    back = scaled / scale
    return np.mean(back == x), scaled


def main():
    t0 = time.time()
    rows = []
    vec_rows = []
    chosen_d = {}
    for name in F.ORDERED_NAMES:
        x, _ = F.load_bits(name)
        n = len(x)
        d99 = None
        for d in range(D_MAX + 1):
            frac, _ = round_trip_frac(x, d)
            rows.append(dict(column=name, class_label=F.FLOATS[name]["class_label"],
                              d=d, frac=round(float(frac), 6)))
            if d99 is None and frac >= 0.99:
                d99 = d
        reached_99 = d99 is not None
        if d99 is None:
            d99 = D_MAX  # never reached 99% in range; use max tested, but flag as not reached
        chosen_d[name] = dict(d=d99, reached_99=reached_99)

        # per-1024-vector round-trip fraction at the chosen d
        nblk = n // VEC
        _, scaled_full = round_trip_frac(x, d99)
        back_full = scaled_full / (10.0 ** d99)
        ok = (back_full == x)
        for i in range(nblk):
            block_ok = ok[i * VEC:(i + 1) * VEC]
            vec_rows.append(dict(column=name, vector=i, d=d99, frac_ok=float(block_ok.mean())))

        print(f"{name}: d99={d99}", file=sys.stderr)

    pd.DataFrame(rows).to_csv(os.path.join(OUT, "csv", "decimal_origin.csv"), index=False)
    vdf = pd.DataFrame(vec_rows)
    vdf.to_csv(os.path.join(OUT, "csv", "decimal_vector_stats.csv"), index=False)

    # small summary printed for README purposes
    for name in F.ORDERED_NAMES:
        sub = vdf[vdf.column == name]
        print(f"{name}: chosen_d={chosen_d[name]} vector frac_ok median={sub.frac_ok.median():.3f} "
              f"min={sub.frac_ok.min():.3f}")

    dt = time.time() - t0
    print(f"wrote csv/decimal_origin.csv, csv/decimal_vector_stats.csv ({dt:.1f}s)")
    import json
    with open(os.path.join(OUT, "csv", "e3_chosen_d.json"), "w") as fh:
        json.dump(chosen_d, fh)


if __name__ == "__main__":
    main()
