#!/usr/bin/env python3
"""Table 1 (tab:class_study_grouped) and the Sec. 2 numbers quoted around it, from the study CSVs.

The paper's table body was assembled by hand from these CSVs; this script recomputes every cell with the rules
written in the table's header comment and prints the Sec. 2 prose numbers. The paper table has no Predictability
column; the predictable-bit-range counts (G/csv/second_condition.csv, reduction_frac > 0) are printed to stdout only.
  Members:     D/csv/split_measure.csv, best of SPLIT_DOC/SPLIT_DATA gains >= 0.1% under both xz and zstd.
  Per-range:   F/csv/addressable_layouts.csv, method SPLIT_DATA, gain_pct_vs_best_whole.
  xz:          same file, method xz_WHOLE.
  OpenZL:      F/csv/openzl_reference.csv openzl_full_bpv against WHOLE_best bits_per_value.
Output: <out>/table_class_study_grouped_body.tex (rows only) and stdout.
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import artifact_paths as AP  # noqa: E402

S = os.path.join(AP.DATA, "sec2_study")
GROUPS = [
    ("T1 time IDs", ["snowflake", "instagram"]),
    ("T2 UUIDv7 high", ["uuidv7_hi"]),
    ("T3 spatial cells", ["h3_r9", "h3_r15", "s2_l16", "s2_l30", "quadkey"]),
    ("T4 composite key", ["xmark"]),
    ("Near-misses", ["publicbi_drug_cost", "publicbi_drug_cost_ge65", "publicbi_bene_count",
                     "publicbi_num_employees", "publicbi_day_supply_bin", "morton_2x16", "morton_2x32"]),
    ("Controls", ["hashed_splitmix64", "random_uint64", "uuidv7_lo", "publicbi_id1", "tpch_orderkey",
                  "inat_species_id", "publicbi_npi", "ipv4_id"]),
]
TYPED = [c for _, cs in GROUPS[:4] for c in cs]

g = pd.read_csv(os.path.join(S, "G/csv/second_condition.csv")).set_index("column")
d = pd.read_csv(os.path.join(S, "D/csv/split_measure.csv"))
f = pd.read_csv(os.path.join(S, "F/csv/addressable_layouts.csv"))
oz = pd.read_csv(os.path.join(S, "F/csv/openzl_reference.csv")).set_index("column")["openzl_full_bpv"]


def member(c):
    ok = []
    for comp in ("xz", "zstd"):
        x = d[(d.column == c) & (d.compressor == comp) & d.variant.isin(["SPLIT_DOC", "SPLIT_DATA"])]
        ok.append(len(x) > 0 and x.gain_pct_vs_best_whole.max() >= 0.1)
    return all(ok)


def fval(c, method, col="gain_pct_vs_best_whole"):
    x = f[(f.column == c) & (f.method == method)][col]
    return float(x.iloc[0]) if len(x) else float("nan")


def ozl(c):
    return 100.0 * (1.0 - oz[c] / fval(c, "WHOLE_best", "bits_per_value")) if c in oz.index else float("nan")


def num(v):
    s = f"{v:.1f}"
    if s == "-0.0":
        s = "0.0"
    return f"${s}$" if s.startswith("-") else s


def rng(vals):
    v = [x for x in vals if x == x]
    lo, hi = min(v), max(v)
    return num(lo) if f"{lo:.1f}" == f"{hi:.1f}" else f"{num(lo)}--{num(hi)}"


rows = []
for name, cols in GROUPS:
    mem = sum(member(c) for c in cols)
    rows.append(f"    {name} & {len(cols)} & {mem} & {rng([fval(c, 'SPLIT_DATA') for c in cols])} & "
                f"{rng([fval(c, 'xz_WHOLE') for c in cols])} & {rng([ozl(c) for c in cols])} \\\\")
    if name == "T4 composite key":
        mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
        # The paper keeps this row commented out; it is printed to stdout below, not written to the body.
        mean_row = (f"    % \\textit{{T1--T4 mean}} & {len(TYPED)} & {sum(member(c) for c in TYPED)} & "
                    f"{num(mean([fval(c, 'SPLIT_DATA') for c in TYPED]))} & "
                    f"{num(mean([fval(c, 'xz_WHOLE') for c in TYPED]))} & {num(mean([ozl(c) for c in TYPED]))} \\\\")
        rows.append("    \\midrule")
out = os.path.join(AP.OUT, "table_class_study_grouped_body.tex")
open(out, "w").write("\n".join(rows) + "\n")
print("\n".join(rows))
print("(commented out in the paper)\n" + mean_row)

# Sec. 2 prose numbers
allc = [c for _, cs in GROUPS for c in cs]
rf = g.reindex(allc).reduction_frac
pos = rf[rf > 0]
print(f"\npredictable: {len(pos)} of {int(rf.notna().sum())}, {100 * pos.min():.1f}%..{100 * pos.max():.1f}%"
      f" (max excluding xmark {100 * pos.drop('xmark').max():.1f}%; C/csv/order1_reduction_reliable_ranges.csv max"
      f" {100 * pd.read_csv(os.path.join(S, 'C/csv/order1_reduction_reliable_ranges.csv')).reduction_frac.max():.1f}%)")
xzg = {c: max(d[(d.column == c) & (d.compressor == 'xz') & d.variant.isin(['SPLIT_DOC', 'SPLIT_DATA'])]
              .gain_pct_vs_best_whole.max(), -1e9) for c in allc}
mem = [c for c in TYPED if member(c)]
print("members (typed):", len(mem), "xz split gain range %.1f%%..%.1f%%" % (min(xzg[c] for c in mem), max(xzg[c] for c in mem)))
nm = GROUPS[4][1]
morton = d[d.column.str.startswith("morton") & (d.compressor == "xz") & (d.variant == "SPLIT_DATA")]
print("near-miss members:", sum(member(c) for c in nm), "; Morton xz SPLIT_DATA gain:",
      dict(zip(morton.column, morton.gain_pct_vs_best_whole.round(1))))
mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
print("per-range saving typed %.1f%%, near-miss %.1f%%, controls %.1f%%" % (
    mean([fval(c, 'SPLIT_DATA') for c in TYPED]), mean([fval(c, 'SPLIT_DATA') for c in nm]),
    mean([fval(c, 'SPLIT_DATA') for c in GROUPS[5][1] if fval(c, 'SPLIT_DATA') == fval(c, 'SPLIT_DATA')])))
print("documented layout (SPLIT_DOC) typed %.1f%%" % mean([fval(c, 'SPLIT_DOC') for c in TYPED if fval(c, 'SPLIT_DOC') == fval(c, 'SPLIT_DOC')]))

fl = pd.read_csv(os.path.join(S, "E/csv/membership_float_v2.csv"))
fl = fl[~fl.column.str.contains("control|random", case=False)]
print(f"floats: predictable {int(fl.criterion_i.sum())}/{len(fl)}, separation gain {int(fl.criterion_ii.sum())}")
