"""F1: generic row-addressable fixed-width layouts, with/without bit-range knowledge
(study_20261001/F, 2026-10-02).

Companion to C1/C2 (entropy) and D (generic byte-stream compressors). Neither of those two
measures a ROW-ADDRESSABLE layout: C1/C2's entropy numbers are not realised by any decoder that
gives O(1) random access to row i, and D's xz/zstd/lz4/snappy streams are LZ77-style sequential
formats with no random-row access either (you must decompress from the start of a stream to
reach row i). This batch asks the complementary question: how much does a plain, textbook,
ROW-ADDRESSABLE fixed-width layout gain from knowing the documented or data-chosen bit-range
partition, and how does its best achievable size compare to a generic (non-addressable) heavy
compressor's whole-column size (xz, reused from `D/csv/split_measure.csv`)?

No SIS, no planner, no cost model, no Nimble encoder anywhere in this script: four textbook
addressable layouts, implemented directly in numpy, nothing else.

Columns, partitions, seeds: identical to C/D -- `C/scripts/structure_common.py`'s `ALL_COLUMNS`
registry (A's 22 columns + the 2 regenerated unstructured controls), same leading 524,288-row
prefix, same `field()` and `data_chosen_partition(k=2.0)` (imported unchanged, so SPLIT_DATA's
ranges are byte-for-byte the same cuts C1/D use). SPLIT_DOC uses the same documented layouts.

## The four addressable layouts (bits/value is always total_bits / n, n = 524288)

Every layout below gives O(1) access to row i: the decoder needs only i, a handful of
column-level header scalars (width, min, dictionary), and -- for the per-block FOR and for any
SPLIT_* layout -- one array lookup (block index = i // 1024; per-value: which range's narrow
field word to read, fixed at layout-compile-time, not stored per row). No value is reordered;
row i's data lives in a fixed-size slot indexed by i, as in a real columnar page.

- **WHOLE_FBW**: fixed bit width for the whole value: `W = max(1, bit_length(max(vals)))` bits
  per row, plus one column-level header (`WIDTH_HDR_BITS=8`, amortised) to record W.
- **WHOLE_FOR (global)**: subtract the column min, then fixed width for the residual:
  `Wd = max(1, bit_length(max(vals)-min(vals)))` bits per row, plus two column-level headers:
  the min (stored at W bits -- safe since min <= max < 2^W) and the residual width
  (`WIDTH_HDR_BITS=8`).
  *header: WIDTH_HDR_BITS + W, once per column.*
- **WHOLE_FOR (per-1024-row block)**: same idea, independently per contiguous block of 1024
  rows (last block may be shorter): each block stores its own min (W bits) and width
  (`WIDTH_HDR_BITS=8`), then `width_block` bits per row in that block.
  *header: n_blocks * (WIDTH_HDR_BITS + W).*
- **WHOLE_DICT**: only when distinct count `k <= n/2` (`DICT_MAX_DISTINCT_FRAC=0.5`). Fixed-width
  code per row, `Wc = max(1, bit_length(k-1))` bits, plus the dictionary itself (`k` entries at
  W bits each -- same safe bound as FOR's min) and a small column-level count header
  (`DICT_COUNT_HDR_BITS=32`).
  *header: DICT_COUNT_HDR_BITS + k*W, once per column.*

`WHOLE_best` = min bits/value across the 4 (DICT excluded when inapplicable) -- this is the
denominator for every SPLIT gain below, and the thing a schema designer would actually pick
without bit-range knowledge.

## SPLIT_DOC / SPLIT_DATA (bit-range knowledge)

For each bit range `(lo, hi)` in the documented layout (SPLIT_DOC, 13/24 columns) or the
data-chosen flip-gradient partition (SPLIT_DATA, `data_chosen_partition(k=2.0)`, all 24
columns, same cuts as C1/D): extract `field(vals, lo, hi)` (values confined to
`[0, 2**(hi-lo))` by construction, so every header above is already tight for sub-ranges too),
independently choose the best of the same 4 layouts *for that range alone*, and sum. One
additional small header per range -- `RANGE_TAG_BITS=2` bits, amortised over n -- records
*which* of the 4 layouts this range uses (the range boundaries themselves are compiled into the
layout/schema, not stored per row or per column; only the layout-choice tag is data-dependent
enough to count). `SPLIT_best_bits = sum_over_ranges(min_layout_bits) + n_ranges * RANGE_TAG_BITS`.

Gain reported as `gain_pct = (WHOLE_best_bpv - SPLIT_bpv) / WHOLE_best_bpv * 100` (positive =
knowing the bit ranges helps even in a fully addressable layout).

## Generic-compressor reference (xz, non-addressable)

`xz_whole_bpv` is reused unchanged from `D/csv/split_measure.csv` (`compressor==xz,
variant==WHOLE_best`) -- NOT recomputed here. It is NOT addressable (xz/LZMA is a sequential
LZ77 stream; reaching row i requires decompressing from the start), included only as the
generic-compressor trade-off reference point requested for the figure/table.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

F_DIR = os.path.dirname(os.path.dirname(__file__))  # .../F
STUDY_DIR = os.path.dirname(F_DIR)  # .../study_20261001
C_SCRIPTS = os.path.join(STUDY_DIR, "C", "scripts")
D_CSV = os.path.join(STUDY_DIR, "D", "csv", "split_measure.csv")
sys.path.insert(0, C_SCRIPTS)
import structure_common as S  # noqa: E402
A = S.A

N = S.N  # 524288
BLOCK = 1024
WIDTH_HDR_BITS = 8          # column- or range-level header: records a fixed bit width (0..64)
DICT_COUNT_HDR_BITS = 32    # column- or range-level header: records a dictionary entry count
RANGE_TAG_BITS = 2          # per-range header: which of the 4 layouts this range uses (SPLIT only)
DICT_MAX_DISTINCT_FRAC = 0.5  # WHOLE_DICT / per-range DICT only applies if distinct <= n/2


def bit_width(vals):
    mx = int(vals.max()) if len(vals) else 0
    return max(1, int(mx).bit_length())


def layout_fbw(vals):
    n = len(vals)
    w = bit_width(vals)
    total_bits = w * n + WIDTH_HDR_BITS
    return total_bits, dict(method="FBW", width=w)


def layout_for_global(vals):
    n = len(vals)
    w_full = bit_width(vals)  # bound for storing min safely
    mn = int(vals.min())
    d = vals.astype(np.uint64) - np.uint64(mn)
    wd = max(1, int(d.max()).bit_length()) if n else 1
    total_bits = wd * n + WIDTH_HDR_BITS + w_full
    return total_bits, dict(method="FOR_global", width=wd, min_hdr_bits=w_full)


def layout_for_block(vals, block=BLOCK):
    n = len(vals)
    if n == 0:
        return WIDTH_HDR_BITS, dict(method="FOR_block", n_blocks=0)
    w_full = bit_width(vals)
    total_bits = 0
    n_blocks = 0
    for start in range(0, n, block):
        chunk = vals[start:start + block]
        mn = int(chunk.min())
        d = chunk.astype(np.uint64) - np.uint64(mn)
        wd = max(1, int(d.max()).bit_length())
        total_bits += wd * len(chunk) + WIDTH_HDR_BITS + w_full
        n_blocks += 1
    return total_bits, dict(method="FOR_block", n_blocks=n_blocks)


def layout_dict(vals):
    n = len(vals)
    distinct = np.unique(vals)
    k = len(distinct)
    if n == 0 or k > DICT_MAX_DISTINCT_FRAC * n:
        return None, dict(method="DICT", applicable=False, k=k)
    w_full = bit_width(vals)
    wc = max(1, (k - 1).bit_length()) if k > 1 else 1
    total_bits = wc * n + DICT_COUNT_HDR_BITS + k * w_full
    return total_bits, dict(method="DICT", applicable=True, k=k, code_width=wc)


def best_addressable(vals):
    """Return (best_bits, best_method_name, {method: bits_or_None})."""
    n = len(vals)
    if n == 0:
        return WIDTH_HDR_BITS, "FBW", {}
    candidates = {}
    b, _ = layout_fbw(vals)
    candidates["FBW"] = b
    b, _ = layout_for_global(vals)
    candidates["FOR_global"] = b
    b, _ = layout_for_block(vals)
    candidates["FOR_block"] = b
    b, info = layout_dict(vals)
    candidates["DICT"] = b if info.get("applicable") else None
    valid = {m: v for m, v in candidates.items() if v is not None}
    best_m = min(valid, key=valid.get)
    return valid[best_m], best_m, candidates


def split_cost(vals, ranges):
    """Sum best_addressable bits over each (lo, hi) range, + per-range method tag header."""
    total_bits = 0
    per_range = []
    for (lo, hi) in ranges:
        fv = A.field(vals, lo, hi)
        b, m, _ = best_addressable(fv)
        total_bits += b + RANGE_TAG_BITS
        per_range.append(dict(lo=lo, hi=hi, width=hi - lo, method=m, bits=b))
    return total_bits, per_range


def main():
    xz_whole = pd.read_csv(D_CSV)
    xz_whole = xz_whole[(xz_whole.compressor == "xz") & (xz_whole.variant == "WHOLE_best")]
    xz_whole_bpv = dict(zip(xz_whole.column, xz_whole.bits_per_value))

    rows = []
    range_rows = []
    names = sorted(S.ALL_COLUMNS.keys())
    for name in names:
        cfg = S.ALL_COLUMNS[name]
        vals = S.load(name, n=N)
        n = len(vals)
        kind = cfg.get("kind")
        subtype = cfg.get("subtype")
        layout = cfg.get("layout")

        # WHOLE layouts
        whole_bits = {}
        for method, fn in [("FBW", layout_fbw), ("FOR_global", layout_for_global),
                            ("FOR_block", layout_for_block)]:
            b, _ = fn(vals)
            whole_bits[method] = b
        b, info = layout_dict(vals)
        whole_bits["DICT"] = b if info.get("applicable") else None

        valid_whole = {m: v for m, v in whole_bits.items() if v is not None}
        best_whole_method = min(valid_whole, key=valid_whole.get)
        best_whole_bits = valid_whole[best_whole_method]
        best_whole_bpv = best_whole_bits / n

        for method, b in whole_bits.items():
            rows.append(dict(
                column=name, kind=kind, subtype=subtype, layout_class="WHOLE", method=method,
                n_rows=n, total_bits=b, bits_per_value=(b / n) if b is not None else None,
                applicable=b is not None,
                gain_pct_vs_best_whole=0.0 if method == best_whole_method else
                ((best_whole_bpv - b / n) / best_whole_bpv * 100.0 if b is not None else None),
                n_ranges=1,
            ))
        rows.append(dict(
            column=name, kind=kind, subtype=subtype, layout_class="WHOLE", method="WHOLE_best",
            n_rows=n, total_bits=best_whole_bits, bits_per_value=best_whole_bits / n,
            applicable=True, gain_pct_vs_best_whole=0.0, n_ranges=1,
        ))

        # SPLIT layouts
        doc_ranges = [(lo, hi) for (_, lo, hi) in layout] if layout else None
        p_flip = A.flip_profile(vals)
        data_ranges = S.data_chosen_partition(p_flip, k=2.0)

        for variant, ranges in [("SPLIT_DOC", doc_ranges), ("SPLIT_DATA", data_ranges)]:
            if ranges is None:
                continue
            total_bits, per_range = split_cost(vals, ranges)
            bpv = total_bits / n
            gain = (best_whole_bpv - bpv) / best_whole_bpv * 100.0 if best_whole_bpv > 0 else 0.0
            rows.append(dict(
                column=name, kind=kind, subtype=subtype, layout_class="SPLIT", method=variant,
                n_rows=n, total_bits=total_bits, bits_per_value=bpv, applicable=True,
                gain_pct_vs_best_whole=gain, n_ranges=len(ranges),
            ))
            for pr in per_range:
                range_rows.append(dict(column=name, variant=variant, **pr))

        xz_bpv = xz_whole_bpv.get(name)
        rows.append(dict(
            column=name, kind=kind, subtype=subtype, layout_class="GENERIC", method="xz_WHOLE",
            n_rows=n, total_bits=(xz_bpv * n) if xz_bpv is not None else None,
            bits_per_value=xz_bpv, applicable=xz_bpv is not None,
            gain_pct_vs_best_whole=(
                (best_whole_bpv - xz_bpv) / best_whole_bpv * 100.0 if xz_bpv is not None and best_whole_bpv > 0
                else None
            ),
            n_ranges=None,
        ))

        print(f"done: {name} (best_whole={best_whole_method} {best_whole_bpv:.2f} bpv, "
              f"doc_ranges={len(doc_ranges) if doc_ranges else 0}, data_ranges={len(data_ranges)})",
              file=sys.stderr)

    df = pd.DataFrame(rows)
    out_csv = os.path.join(F_DIR, "csv", "addressable_layouts.csv")
    df.to_csv(out_csv, index=False)
    print(f"wrote {out_csv} ({len(df)} rows)")

    rdf = pd.DataFrame(range_rows)
    out_ranges = os.path.join(F_DIR, "csv", "addressable_ranges.csv")
    rdf.to_csv(out_ranges, index=False)
    print(f"wrote {out_ranges} ({len(rdf)} rows)")


if __name__ == "__main__":
    main()
