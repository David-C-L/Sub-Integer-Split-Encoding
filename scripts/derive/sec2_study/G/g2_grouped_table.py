#!/usr/bin/env python3
"""G2: grouped Table 1 variant (task 2, 2026-10-02). Joins the per-column numbers already
hand-joined in the draft's per-column Table 1 (F/csv/addressable_layouts.csv SPLIT_DATA
gain_pct_vs_best_whole; D/csv/split_measure.csv xz WHOLE_best bits_per_value;
C/csv/order1_reduction_reliable_ranges.csv reduction_frac) into one row per group, with
min-max ranges, plus the combined Condition-1+2 member count from
G/csv/second_condition.csv. No new measurement; this is a presentation re-aggregation only.
"""
import csv
import os

G_DIR = os.path.dirname(os.path.dirname(__file__))

GROUPS = {
    "T1 (time-ordered IDs)": ["snowflake", "instagram"],
    "T2 (UUID halves)": ["uuidv7_hi"],
    "T3 (spatial cells)": ["h3_r9", "h3_r15", "s2_l16", "s2_l30", "quadkey"],
    "T4 (packed composite)": ["xmark"],
    "Near-misses": ["publicbi_drug_cost", "publicbi_drug_cost_ge65", "publicbi_bene_count",
                     "publicbi_num_employees", "publicbi_day_supply_bin", "morton_2x16", "morton_2x32"],
    "Controls": ["hashed_splitmix64", "random_uint64", "uuidv7_lo", "publicbi_id1",
                 "tpch_orderkey", "inat_species_id", "publicbi_npi", "ipv4_id"],
}

# Per-column numbers as already hand-joined in the draft's per-column Table 1 (section (b) of
# 21_section2_draft.md): (order1_reduction_pct or None, split_gain_pct, xz_bits_per_value)
PERCOL = {
    "snowflake": (None, 16.3, 38.5), "instagram": (82.0, 1.9, 55.8),
    "uuidv7_hi": (None, 15.7, 11.9),
    "h3_r9": (None, 25.7, 4.9), "h3_r15": (None, 6.6, 22.9), "s2_l16": (None, 46.8, 7.8),
    "s2_l30": (None, 0.0, 36.9), "quadkey": (None, -0.1, 18.4),
    "xmark": (None, 58.2, 10.1),
    "publicbi_drug_cost": (2.9, -0.0, 21.8), "publicbi_drug_cost_ge65": (1.8, 0.1, 20.9),
    "publicbi_bene_count": (1.6, -1.8, 7.0), "publicbi_num_employees": (3.0, -6.0, 2.1),
    "publicbi_day_supply_bin": (25.6, -5.1, 4.3),
    "morton_2x16": (None, 15.4, 4.3), "morton_2x32": (None, 7.6, 37.4),
    "hashed_splitmix64": (0.0, -0.0, 64.0), "random_uint64": (0.0, -0.0, 64.0),
    "uuidv7_lo": (0.0, -1.6, 64.0), "publicbi_id1": (None, -10.2, 20.0),
    "tpch_orderkey": (None, -1.6, 1.3), "inat_species_id": (None, -5.8, 10.6),
    "publicbi_npi": (0.0, -8.0, 12.9), "ipv4_id": (None, -3.1, 27.7),
}


def member_counts():
    with open(os.path.join(G_DIR, "csv", "second_condition.csv")) as f:
        rows = {r["column"]: r for r in csv.DictReader(f)}
    out = {}
    for g, cols in GROUPS.items():
        n = len(cols)
        m = sum(1 for c in cols if rows[c]["combined_member"] == "True")
        out[g] = (m, n)
    return out


def rng(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "--"
    lo, hi = min(vals), max(vals)
    if lo == hi:
        return f"{lo:+.1f}" if lo != 0 else "0.0"
    return f"{lo:+.1f}..{hi:+.1f}"


def main():
    mc = member_counts()
    lines = []
    for g, cols in GROUPS.items():
        red = rng([PERCOL[c][0] for c in cols])
        split = rng([PERCOL[c][1] for c in cols])
        xz = rng([PERCOL[c][2] for c in cols])
        m, n = mc[g]
        lines.append((g, len(cols), f"{m}/{n}", red, split, xz))

    out = os.path.join(G_DIR, "table1_grouped.tex")
    with open(out, "w") as f:
        f.write("% Grouped Table 1 (task 2, G2). Member: combined Cond.1 (order-1 reduction>0 on\n"
                "% the data-chosen reliable range) AND Cond.2 (order-0 relative deficit>=20%% on the\n"
                "% most-skewed reliable range, width>=2, distinct>=4) -- G/csv/second_condition.csv.\n"
                "% Ranges: Order-1 red./Split gain/xz bpv from the draft's per-column Table 1 cells\n"
                "% (same provenance), re-aggregated per group, min..max over the columns with a value.\n")
        f.write("\\begin{table}[t]\n  \\footnotesize\n  \\setlength{\\tabcolsep}{4pt}\n")
        f.write("  \\caption{The study corpus grouped by sub-type (24 integer columns, 524{,}288 rows "
                "each). Member: count passing both membership conditions "
                "(\\autoref{subsection:definition}) over the group size. Ranges are min..max over "
                "the columns in the group with a measured value.}\n")
        f.write("  \\label{tab:class_study_grouped}\n")
        f.write("  \\begin{tabular}{lcccc}\n    \\toprule\n")
        f.write("    Group & Member & \\shortstack{Order-1\\\\red.\\,\\%} & \\shortstack{Split\\\\gain\\,\\%} & \\shortstack{xz\\\\bits/val} \\\\\n    \\midrule\n")
        for g, n, m, red, split, xz in lines:
            f.write(f"    {g} & {m} & {red} & {split} & {xz} \\\\\n")
        f.write("    \\bottomrule\n  \\end{tabular}\n\\end{table}\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
