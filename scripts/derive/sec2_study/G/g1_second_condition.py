#!/usr/bin/env python3
"""G1: second membership condition (order-0 deficit on the Condition-1 range) + shuffle
diagnostic, applied to all 24 integer columns (study_20261001/G, 2026-10-02). See
G/README_G.md for the fixed criteria, written before this script ran. No SIS, no cost model,
no encoder. Reuses C/scripts/structure_common.py and C/csv/structure_measure.csv unchanged.
"""
import os
import sys

import numpy as np
import pandas as pd

C_SCRIPTS = "$PROJECT/paper-repo/study_20261001/C/scripts"
sys.path.insert(0, C_SCRIPTS)
import structure_common as C  # noqa: E402

G_DIR = os.path.dirname(os.path.dirname(__file__))
C_CSV = os.path.join(os.path.dirname(C_SCRIPTS), "csv")

ALL_NAMES = sorted(C.ALL_COLUMNS.keys())


def documented_label(name):
    cfg = C.ALL_COLUMNS[name]
    kind = cfg.get("kind", "control")
    if kind == "structured":
        return "structured", cfg.get("subtype", "?")
    if kind.startswith("near_miss"):
        return "near_miss", cfg.get("subtype", "?")
    return "control", cfg.get("subtype", "control")


def pick_range(struct_df, name):
    """TODO2's rule for Condition 1: lowest-cardinality range (data-chosen partition) with
    order1_reliable=True and order0_entropy_mm_bits > 0 (excludes constant sub-ranges)."""
    rows = struct_df[(struct_df.column == name) & (struct_df.partition_source == "data") &
                      (struct_df.order1_reliable == True) &  # noqa: E712
                      (struct_df.order0_entropy_mm_bits > 0)]
    if rows.empty:
        return None
    rows = rows.sort_values("width")
    return rows.iloc[0]


def best_deficit_range(struct_df, name):
    """Condition 2 scans the WHOLE per-range profile (data-chosen partition), not just the
    Condition-1 range: a trivial single bit caps the achievable deficit at 1 bit and is not
    where a measure's skew usually lives. Requires order0_reliable (distinct <= N/50, not
    degenerate) and distinct >= 4 (a single flip-prob bit has too little dynamic range to
    judge "uniform vs skewed" on). Returns the range with the largest RELATIVE deficit
    (1 - order0_mm/log2(distinct)) among those -- i.e. the strongest evidence, in either
    direction, that some range of this column's values departs from its own uniform
    expectation."""
    rows = struct_df[(struct_df.column == name) & (struct_df.partition_source == "data") &
                      (struct_df.order0_reliable == True) & (struct_df.distinct >= 4)]  # noqa: E712
    if rows.empty:
        return None
    rel_deficit = 1.0 - rows.order0_entropy_mm_bits / np.log2(rows.distinct)
    idx = rel_deficit.idxmax()
    r = rows.loc[idx].copy()
    r["relative_deficit"] = float(rel_deficit.loc[idx])
    return r


def shuffle_diagnostic(name, lo, hi, seed=0):
    """Recompute order-1 reduction on the SAME range after an independent row shuffle (fixed
    seed). Confirmatory only (see README): expected to vanish for every column with a real
    adjacency effect, member or control alike."""
    v = C.load(name)
    iv = v.astype(np.int64)
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(iv))
    shuf = iv[perm]
    f_shuf = C.field(shuf, int(lo), int(hi))
    if len(f_shuf) < 2:
        return None
    # Exact convention from C1 (c1_structure_measure.py range_row): H(X_t|X_{t-1}) =
    # H_joint(X_{t-1},X_t) - H(X_t) [full-array order-0 marginal, not the n-1 prefix].
    h0, h0_mm, k0, n0, rel0 = C.counts_entropy(f_shuf)
    hj, hj_mm, kj, nj, relj = C.joint_entropy(f_shuf[:-1], f_shuf[1:])
    cond = hj_mm - h0_mm
    reduction = 1.0 - (cond / h0_mm) if h0_mm > 0 else 0.0
    return dict(order0_shuffled=h0_mm, order1_cond_shuffled=cond, reduction_frac_shuffled=reduction,
                reliable_shuffled=bool(relj))


def main():
    struct_df = pd.read_csv(os.path.join(C_CSV, "structure_measure.csv"))
    rows = []
    for name in ALL_NAMES:
        label, subtype = documented_label(name)
        r = pick_range(struct_df, name)
        if r is None:
            rows.append(dict(column=name, documented_label=label, documented_subtype=subtype,
                              lo=None, hi=None, width=None, distinct=None,
                              order0_mm=None, order1_cond=None, reduction_frac=None,
                              uniform_expectation_bits=None, deficit_bits=None,
                              cond1_pass=False, cond2_pass=False, combined_member=False,
                              reduction_frac_shuffled=None, shuffle_vanishes=None,
                              note="no non-constant reliable data-chosen range found"))
            continue
        order0_mm = float(r.order0_entropy_mm_bits)
        order1_cond = float(r.order1_cond_entropy_bits)
        distinct = int(r.distinct)
        reduction = 1.0 - (order1_cond / order0_mm) if order0_mm > 0 else 0.0
        uniform_exp = float(np.log2(distinct)) if distinct > 1 else 0.0
        deficit = uniform_exp - order0_mm
        cond1 = reduction > 0.0

        dr = best_deficit_range(struct_df, name)
        if dr is None:
            cond2, rel_deficit, dr_lo, dr_hi, dr_width, dr_distinct = False, None, None, None, None, None
        else:
            rel_deficit = float(dr["relative_deficit"])
            cond2 = rel_deficit >= 0.2
            dr_lo, dr_hi, dr_width, dr_distinct = int(dr.lo), int(dr.hi), int(dr.width), int(dr.distinct)
        combined = cond1 and cond2

        sd = shuffle_diagnostic(name, int(r.lo), int(r.hi))
        red_shuf = sd["reduction_frac_shuffled"] if sd else None
        vanishes = (red_shuf is not None) and (red_shuf <= 0.01)

        rows.append(dict(column=name, documented_label=label, documented_subtype=subtype,
                          lo=int(r.lo), hi=int(r.hi), width=int(r.width), distinct=distinct,
                          order0_mm=round(order0_mm, 4), order1_cond=round(order1_cond, 4),
                          reduction_frac=round(reduction, 4),
                          uniform_expectation_bits=round(uniform_exp, 4),
                          deficit_bits=round(deficit, 4),
                          cond2_range_lo=dr_lo, cond2_range_hi=dr_hi, cond2_range_width=dr_width,
                          cond2_range_distinct=dr_distinct,
                          cond2_relative_deficit=(round(rel_deficit, 4) if rel_deficit is not None else None),
                          cond1_pass=cond1, cond2_pass=cond2, combined_member=combined,
                          reduction_frac_shuffled=(round(red_shuf, 4) if red_shuf is not None else None),
                          shuffle_vanishes=vanishes, note=""))
    df = pd.DataFrame(rows)
    out = os.path.join(G_DIR, "csv", "second_condition.csv")
    df.to_csv(out, index=False)
    print("wrote", out)

    # confusion: expected member = documented_label in {structured, near_miss}; expected
    # non-member = control.
    df["expected_member"] = df.documented_label.isin(["structured", "near_miss"])
    df["combined_member"] = df.combined_member.fillna(False)
    tp = int(((df.expected_member) & (df.combined_member)).sum())
    fn = int(((df.expected_member) & (~df.combined_member)).sum())
    fp = int(((~df.expected_member) & (df.combined_member)).sum())
    tn = int(((~df.expected_member) & (~df.combined_member)).sum())
    print(f"confusion (combined Cond1+Cond2): TP={tp} FN={fn} FP={fp} TN={tn}")
    print(df[["column", "documented_label", "reduction_frac", "cond2_relative_deficit", "cond1_pass",
               "cond2_pass", "combined_member", "reduction_frac_shuffled"]].to_string(index=False))


if __name__ == "__main__":
    main()
