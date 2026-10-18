"""E4: generic-compressor split measure for floats (study_20261001/E, 2026-10-02).

Reuses D/scripts/d1_split_measure.py's compressors (xz preset 6, zstd -19, lz4, snappy) and
byte-packing helpers unchanged. For each float column, compresses WHOLE (raw IEEE uint64
stream) vs per-range byte streams under three bit-partitions of the IEEE word:
  (a) IEEE sign/exp/mantissa: [63,64) [52,63) [0,52)
  (b) front-bits split at b = E2's leading_bits_stable_min: [64-b,64) [0,64-b) (degenerates to
      WHOLE when b==0, e.g. the control)
  (c) data-chosen from E1 (data_chosen_partition on the file-order flip profile)
Also (d) a decimal control: round(x * 10^d) for E3's chosen d, as int64 bytes, compared in
bits/value against (a)-(c) and against WHOLE.

No SIS/Nimble/cost model: same generic byte-stream compressors as D1, never told the data's
structure beyond the partition boundaries given to them.

Output: csv/split_measure_float.csv (column, partition, compressor, bytes, bpv, gain_pct vs WHOLE).
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import float_common as F  # noqa: E402

D1_SCRIPTS = os.path.join(F.STUDY_DIR, "D", "scripts")
sys.path.insert(0, D1_SCRIPTS)
import d1_split_measure as D1  # noqa: E402  (xz_size, zstd_size, lz4_size, snappy_size, etc.)

OUT = F.E_DIR
COMPRESSORS = D1.COMPRESSORS  # {"xz":..., "zstd":..., "lz4":..., "snappy":...}


def split_ranges_bits(ranges, n_bits=64):
    """Validate/clean a list of (lo,hi) half-open ranges covering [0, n_bits)."""
    ranges = sorted(set([(lo, hi) for (lo, hi) in ranges if hi > lo]))
    return ranges


def main():
    t0 = time.time()
    with open(os.path.join(OUT, "csv", "e1_data_chosen_partitions.json")) as fh:
        data_partitions = json.load(fh)
    with open(os.path.join(OUT, "csv", "e3_chosen_d.json")) as fh:
        chosen_d = json.load(fh)
    fields = pd.read_csv(os.path.join(OUT, "csv", "float_fields.csv")).set_index("column")

    rows = []
    for name in F.ORDERED_NAMES:
        x, v = F.load_bits(name)
        n = len(v)
        b_front = int(fields.loc[name, "leading_bits_stable_min"])

        ieee_ranges = split_ranges_bits([(63, 64), (52, 63), (0, 52)])
        if b_front > 0 and b_front < 64:
            front_ranges = split_ranges_bits([(64 - b_front, 64), (0, 64 - b_front)])
        else:
            front_ranges = split_ranges_bits([(0, 64)])  # degenerate: no usable front split
        data_ranges = split_ranges_bits([tuple(r) for r in data_partitions[name]])

        whole_stream = D1.pack_le_stream(v, 8)
        ieee_streams = D1.range_streams(v, ieee_ranges)
        front_streams = D1.range_streams(v, front_ranges)
        data_streams = D1.range_streams(v, data_ranges)

        d_info = chosen_d[name]
        d = d_info["d"] if isinstance(d_info, dict) else d_info
        reached_99 = d_info.get("reached_99", True) if isinstance(d_info, dict) else True
        scaled = x * (10.0 ** d)
        overflow = (not reached_99) and (np.abs(scaled).max() >= 2.0 ** 62)
        if overflow:
            # control / non-decimal-origin column: d never reached 99% round-trip, and the
            # fallback d=D_MAX overflows int64 here. The decimal-integer control is not
            # meaningful for this column (it has no decimal origin) -- record as NaN, not a
            # garbage overflow value.
            dec_stream_narrow = None
            dec_w = None
        else:
            dec_int = np.round(scaled).astype(np.int64)
            dec_stream = D1.pack_le_stream(dec_int.astype(np.uint64), 8)
            dec_w = D1.narrow_width_bytes(dec_int.astype(np.uint64))
            dec_stream_narrow = D1.pack_le_stream(dec_int.astype(np.uint64), dec_w) if dec_w < 8 else dec_stream

        for cname, comp_fn in COMPRESSORS.items():
            whole_sz = comp_fn(whole_stream)
            whole_bpv = whole_sz * 8.0 / n

            def rec(variant, total_sz, n_streams, ranges_desc):
                bpv = total_sz * 8.0 / n
                gain_pct = (whole_bpv - bpv) / whole_bpv * 100.0 if whole_bpv > 0 else 0.0
                rows.append(dict(
                    column=name, class_label=F.FLOATS[name]["class_label"], compressor=cname,
                    variant=variant, n_rows=n, n_streams=n_streams, compressed_bytes=total_sz,
                    bits_per_value=bpv, gain_pct_vs_whole=gain_pct, ranges=ranges_desc,
                ))

            rec("WHOLE", whole_sz, 1, "[0,64)")
            rec("SPLIT_IEEE_a", D1.sum_compressed(ieee_streams, comp_fn), len(ieee_streams),
                json.dumps(ieee_ranges))
            rec("SPLIT_FRONT_b", D1.sum_compressed(front_streams, comp_fn), len(front_streams),
                json.dumps(front_ranges) + f" (b={b_front})")
            rec("SPLIT_DATA_c", D1.sum_compressed(data_streams, comp_fn), len(data_streams),
                json.dumps(data_ranges))
            if dec_stream_narrow is None:
                rows.append(dict(
                    column=name, class_label=F.FLOATS[name]["class_label"], compressor=cname,
                    variant="DECIMAL_INT_d", n_rows=n, n_streams=1, compressed_bytes=np.nan,
                    bits_per_value=np.nan, gain_pct_vs_whole=np.nan,
                    ranges=f"not meaningful: d={d} never reached 99% round-trip (control/non-decimal)",
                ))
            else:
                dec_sz = comp_fn(dec_stream_narrow)
                rec("DECIMAL_INT_d", dec_sz, 1, f"round(x*10^{d}) as {dec_w}B int")

        print(f"done: {name} (b_front={b_front}, d={d}, reached_99={reached_99})", file=sys.stderr)

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "csv", "split_measure_float.csv"), index=False)
    dt = time.time() - t0
    print(f"wrote csv/split_measure_float.csv ({len(df)} rows, {dt:.1f}s)")


if __name__ == "__main__":
    main()
