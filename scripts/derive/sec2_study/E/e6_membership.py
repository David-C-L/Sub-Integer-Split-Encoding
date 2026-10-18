"""E6: membership verdict for the 4 float columns (study_20261001/E, 2026-10-02).

Joins E1-E5 outputs and applies the FIXED criteria (written into README_E.md before this
script was run, verbatim from plan 20 section 2's E6 row):

  (i)  at least one reliable range (order1_reliable=True, from E5/C1's range_row) with a
       positive order-1 conditional-entropy reduction (file order lower than shuffled, i.e.
       the shuffled copy loses the structure this test measures) -- C2's test, reused unchanged.
  (ii) E4 split gain > 0 under partition (b) [front-bits] or (c) [data-chosen] for BOTH of the
       two primary generic compressors (xz preset 6, zstd -19 -- the two D1 treats as the main
       measure; lz4/snappy are D1's fast completeness arms and are reported in the CSV for
       context but are not part of this fixed criterion).

Verdict per column: member (i AND ii), weak-member (exactly one of i, ii), non-member (neither).

Output: csv/membership_float.csv (column, class_label, criterion_i, criterion_i_evidence,
criterion_ii, criterion_ii_evidence, verdict, structure_ranges).
"""
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import float_common as F  # noqa: E402

OUT = F.E_DIR
MAIN_COMPRESSORS = ["xz", "zstd"]


def criterion_i(struct_df, name):
    """Returns (bool, evidence_str, list_of_ranges) using E5's structure_measure_float.csv."""
    sub = struct_df[struct_df.column == name]
    file_rows = sub[sub.order == "file"].set_index(["partition", "lo", "hi"])
    shuf_rows = sub[sub.order == "shuffled"].set_index(["partition", "lo", "hi"])
    hits = []
    for key in file_rows.index:
        if key not in shuf_rows.index:
            continue
        fr = file_rows.loc[key]
        sr = shuf_rows.loc[key]
        if not bool(fr["order1_reliable"]):
            continue
        h_file = fr["order1_cond_entropy_bits"]
        h_shuf = sr["order1_cond_entropy_bits"]
        if h_shuf > 1e-9:
            reduction = (h_shuf - h_file) / h_shuf
        else:
            reduction = 0.0
        if reduction > 0.0 and h_file < h_shuf - 1e-9:
            hits.append((key, round(float(reduction) * 100, 2)))
    ok = len(hits) > 0
    evidence = "; ".join(f"{p}:[{lo},{hi}) reduction={r}%" for (p, lo, hi), r in hits) if hits else "none"
    ranges = [f"{p}:[{lo},{hi})" for (p, lo, hi), _ in hits]
    return ok, evidence, ranges


def criterion_ii(split_df, name):
    """Returns (bool, evidence_str) using E4's split_measure_float.csv, variants (b)/(c),
    both xz and zstd > 0."""
    sub = split_df[(split_df.column == name) & (split_df.compressor.isin(MAIN_COMPRESSORS))]
    hits = []
    for variant in ("SPLIT_FRONT_b", "SPLIT_DATA_c"):
        vsub = sub[sub.variant == variant]
        gains = {row.compressor: row.gain_pct_vs_whole for _, row in vsub.iterrows()}
        if all(gains.get(c, -1.0) > 0.0 for c in MAIN_COMPRESSORS):
            hits.append((variant, {c: round(float(gains[c]), 2) for c in MAIN_COMPRESSORS}))
    ok = len(hits) > 0
    evidence = "; ".join(f"{v}: {g}" for v, g in hits) if hits else "none (no partition gave positive gain under both xz and zstd)"
    return ok, evidence


def main():
    t0 = time.time()
    struct_df = pd.read_csv(os.path.join(OUT, "csv", "structure_measure_float.csv"))
    split_df = pd.read_csv(os.path.join(OUT, "csv", "split_measure_float.csv"))

    rows = []
    for name in F.ORDERED_NAMES:
        ok_i, ev_i, ranges_i = criterion_i(struct_df, name)
        ok_ii, ev_ii = criterion_ii(split_df, name)
        if ok_i and ok_ii:
            verdict = "member"
        elif ok_i or ok_ii:
            verdict = "weak-member"
        else:
            verdict = "non-member"
        rows.append(dict(
            column=name, class_label=F.FLOATS[name]["class_label"],
            criterion_i=ok_i, criterion_i_evidence=ev_i,
            criterion_ii=ok_ii, criterion_ii_evidence=ev_ii,
            verdict=verdict, structure_ranges=";".join(ranges_i) if ranges_i else "",
        ))
        print(f"{name}: verdict={verdict} (i={ok_i}, ii={ok_ii})", file=sys.stderr)

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "csv", "membership_float.csv"), index=False)
    dt = time.time() - t0
    print(f"wrote csv/membership_float.csv ({dt:.1f}s)")


if __name__ == "__main__":
    main()
