#!/usr/bin/env python3
"""C2: data-based justification for PublicBI measure-column + Instagram membership
(proposals/18 section H task 2, 2026-10-02).

Builds value_stats.csv (magnitude/scale/concentration/run stats for the 5 PublicBI measure
columns + instagram, contrasted with the hashed/random controls and two more "no documented
layout" controls) and one small figure: the order-1 conditional-entropy reduction on each
column's lowest-cardinality RELIABLE bit range from C1's structure_measure.csv (the one
reliable, defensible run/drift signal -- see C/README_C1.md caveats on why wide/high-cardinality
ranges are not usable here). No cost model, no encoder, no SIS.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import structure_common as C  # noqa: E402

OUT_CSV = os.path.join(os.path.dirname(os.path.dirname(__file__)), "csv")
OUT_FIG = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fig")

TARGETS = ["publicbi_drug_cost", "publicbi_drug_cost_ge65", "publicbi_bene_count",
           "publicbi_num_employees", "publicbi_day_supply_bin", "instagram"]
CONTRASTS = ["hashed_splitmix64", "random_uint64", "uuidv7_lo", "publicbi_npi"]

NOTES = {
    "publicbi_drug_cost": "dollars*100 (cents); Medicare Part D total drug cost per claim group",
    "publicbi_drug_cost_ge65": "cents, same measure restricted to age>=65 beneficiaries",
    "publicbi_bene_count": "beneficiary count per claim group, small positive integer, heavily right-skewed",
    "publicbi_num_employees": "employee count per company record, small positive integer, heavily right-skewed",
    "publicbi_day_supply_bin": "pre-binned average day-supply, a handful of discrete bin codes",
    "instagram": "composite id: sequence + shard + timestamp fields (documented layout)",
    "hashed_splitmix64": "splitmix64 hash stream, no documented structure (synthetic control)",
    "random_uint64": "numpy uniform random uint64, no documented structure (synthetic control)",
    "uuidv7_lo": "UUIDv7 low 64 bits (random part by spec), no documented bit-field layout",
    "publicbi_npi": "US National Provider Identifier, government-assigned, no documented bit-field layout",
}


def value_stats(name):
    cfg = C.ALL_COLUMNS[name]
    v = C.load(name)
    n = len(v)
    iv = v.astype(np.int64)
    distinct_vals, counts = np.unique(iv, return_counts=True)
    distinct = len(distinct_vals)
    order = np.argsort(-counts)
    top20_frac = counts[order][:20].sum() / n
    eq_prev = (iv[1:] == iv[:-1])
    frac_eq_prev = float(eq_prev.mean()) if n > 1 else 0.0
    mean_run_length = 1.0 / (1.0 - frac_eq_prev) if frac_eq_prev < 1.0 else float(n)
    p = C.A.flip_profile(v)
    active = p[p > 0]
    return dict(
        column=name, kind=cfg["kind"], n=n, distinct=distinct,
        distinct_ratio=round(distinct / n, 6),
        min=int(iv.min()), max=int(iv.max()), value_range=int(iv.max()) - int(iv.min()),
        bit_width_of_range=max(1, int(int(iv.max()) - int(iv.min())).bit_length()),
        top20_values_frac=round(float(top20_frac), 4),
        frac_eq_prev_row=round(frac_eq_prev, 4),
        mean_run_length=round(mean_run_length, 3),
        bitflip_prob_min=round(float(p.min()), 4), bitflip_prob_max=round(float(p.max()), 4),
        n_bits_never_flip=int((p == 0).sum()), n_bits_always_flip_near_half=int((np.abs(p - 0.5) < 0.02).sum()),
        active_bits_entropy_mean=round(float(C.A.h_bin(active).mean()) if active.size else 0.0, 4),
        notes=NOTES.get(name, ""),
    )


def lowest_card_reliable_range(struct_df, name):
    """From C1's per-range table (data partition), the narrowest range whose order0 estimate
    is reliable and whose order1_cond_entropy is also reliable -- the only ranges where a
    run/drift reduction claim is defensible at N=524,288 (see C1 caveats)."""
    rows = struct_df[(struct_df.column == name) & (struct_df.partition_source == "data") &
                      (struct_df.order1_reliable == True)]  # noqa: E712
    if rows.empty:
        return None
    rows = rows.sort_values("width")
    r = rows.iloc[0]
    reduction = 1.0 - (r.order1_cond_entropy_bits / r.order0_entropy_mm_bits) if r.order0_entropy_mm_bits > 0 else 0.0
    return dict(column=name, lo=int(r.lo), hi=int(r.hi), width=int(r.width),
                order0=float(r.order0_entropy_mm_bits), order1_cond=float(r.order1_cond_entropy_bits),
                reduction_frac=float(reduction))


def main():
    rows = [value_stats(n) for n in TARGETS + CONTRASTS]
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT_CSV, "value_stats.csv"), index=False)
    print("wrote", os.path.join(OUT_CSV, "value_stats.csv"))

    struct_df = pd.read_csv(os.path.join(OUT_CSV, "structure_measure.csv"))
    fig_rows = []
    for n in TARGETS + CONTRASTS:
        r = lowest_card_reliable_range(struct_df, n)
        if r is not None:
            fig_rows.append(r)
    fig_df = pd.DataFrame(fig_rows)
    fig_df.to_csv(os.path.join(OUT_CSV, "order1_reduction_reliable_ranges.csv"), index=False)
    print("wrote", os.path.join(OUT_CSV, "order1_reduction_reliable_ranges.csv"))

    # --- figure: order-1 conditional-entropy reduction, lowest-cardinality reliable range ---
    fig_df = fig_df.sort_values("reduction_frac")
    is_target = fig_df.column.isin(TARGETS)
    colors = np.where(is_target, "#3A6EA5", "#B0B0B0")  # categorical: measure/instagram vs control, fixed order
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    ypos = np.arange(len(fig_df))
    ax.barh(ypos, fig_df.reduction_frac * 100, color=colors, height=0.6)
    ax.set_yticks(ypos)
    ax.set_yticklabels(fig_df.column, fontsize=8)
    ax.set_xlabel("order-1 cond. entropy reduction (%)\nlowest-card. reliable range", fontsize=8)
    ax.set_xlim(left=0)
    ax.tick_params(axis="x", labelsize=8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#888888")
    from matplotlib.patches import Patch
    handles = [Patch(color="#3A6EA5", label="measure col. / instagram"),
               Patch(color="#B0B0B0", label="control (no documented layout)")]
    ax.legend(handles=handles, loc="lower right", fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_FIG, "fig_order1_reduction.pdf"))
    print("wrote", os.path.join(OUT_FIG, "fig_order1_reduction.pdf"))


if __name__ == "__main__":
    main()
