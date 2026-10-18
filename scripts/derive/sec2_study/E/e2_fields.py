"""E2: exponent/mantissa field statistics for the 4 float columns (study_20261001/E, 2026-10-02).

Per column: exponent histogram, distinct exponent count, exponent entropy (order-0, via
C.counts_entropy); mantissa trailing-zero-count distribution; effective mantissa width =
52 - median trailing zeros; leading-bits stability = number of top bits constant within each
1024-value vector (ALP_rd's front-bits quantity), reported as the median over vectors and the
value used downstream (min over vectors, i.e. the number of bits guaranteed constant in every
vector) as `leading_bits_stable_min`.

Outputs: csv/float_fields.csv, fig/fig_float_exp_tz.pdf.
"""
import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import float_common as F  # noqa: E402

OUT = F.E_DIR
VEC = 1024


def leading_bits_stable(v_u64, vec=VEC):
    """Number of top bits (from bit 63 down) constant within each `vec`-sized block.
    Returns array of per-vector counts."""
    n = len(v_u64)
    nblk = n // vec
    counts = []
    for i in range(nblk):
        block = v_u64[i * vec:(i + 1) * vec]
        first = block[0]
        diffmask = np.uint64(0)
        for x in block[1:]:
            diffmask |= (x ^ first)
        # count leading zero bits of diffmask (from bit 63 downward) = stable top bits
        if diffmask == 0:
            counts.append(64)
            continue
        hi = 63
        while hi >= 0 and ((diffmask >> np.uint64(hi)) & np.uint64(1)) == 0:
            hi -= 1
        counts.append(63 - hi)
    return np.array(counts, dtype=np.int64)


def main():
    t0 = time.time()
    rows = []
    exp_hists = {}
    tz_hists = {}
    for name in F.ORDERED_NAMES:
        x, v = F.load_bits(name)
        n = len(v)
        exp = F.A.field(v, 52, 63).astype(np.int64)
        mant = F.A.field(v, 0, 52).astype(np.uint64)

        h, h_mm, k, nn, reliable = F.C.counts_entropy(exp)
        exp_hists[name] = exp

        # trailing zero count of mantissa (0..52, 52 = mantissa is exactly 0)
        tz = np.zeros(n, dtype=np.int64)
        nonzero = mant != 0
        if nonzero.any():
            # bit_length of lowest set bit via (mant & -mant) trick is awkward in uint64;
            # use direct loop over 52 bits (cheap: 52*524288 bit ops, vectorised per bit)
            tz_nz = np.zeros(nonzero.sum(), dtype=np.int64)
            mz = mant[nonzero].copy()
            done = np.zeros(len(mz), dtype=bool)
            for b in range(52):
                has_bit = ((mz >> np.uint64(b)) & np.uint64(1)) == 1
                newly = has_bit & (~done)
                tz_nz[newly] = b
                done |= has_bit
            tz[nonzero] = tz_nz
        tz[~nonzero] = 52  # mantissa all-zero -> treat as 52 trailing zeros
        tz_hists[name] = tz
        median_tz = float(np.median(tz))
        eff_mant_width = 52.0 - median_tz

        lbs = leading_bits_stable(v, vec=VEC)
        lbs_median = float(np.median(lbs))
        lbs_min = int(lbs.min())

        rows.append(dict(
            column=name, class_label=F.FLOATS[name]["class_label"], n=n,
            exp_distinct=k, exp_entropy_bits=round(h, 4), exp_entropy_mm_bits=round(h_mm, 4),
            exp_min=int(exp.min()), exp_max=int(exp.max()),
            mant_tz_median=median_tz, mant_tz_mean=float(np.mean(tz)),
            effective_mantissa_width=eff_mant_width,
            leading_bits_stable_median=lbs_median, leading_bits_stable_min=lbs_min,
            n_vectors_1024=n // VEC,
        ))
        print(f"{name}: exp_distinct={k} eff_mant_width={eff_mant_width:.1f} "
              f"leading_bits_stable(median/min)={lbs_median:.1f}/{lbs_min}", file=sys.stderr)

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "csv", "float_fields.csv"), index=False)

    # ---- figure: 2-panel, exponent histogram (top) + mantissa trailing-zero histogram (bottom) ----
    palette = ["#1b6fa8", "#c2572a", "#3c8a5b", "#8a5fbf"]
    fig, axes = plt.subplots(2, 1, figsize=(7.0, 5.0))
    for i, name in enumerate(F.ORDERED_NAMES):
        exp = exp_hists[name]
        vals, counts = np.unique(exp, return_counts=True)
        axes[0].plot(vals, counts / counts.sum(), label=name, color=palette[i % len(palette)],
                     linewidth=1.2, marker="o", markersize=2)
    axes[0].set_ylim(bottom=0)
    axes[0].set_xlabel("exponent field value (biased)", fontsize=8)
    axes[0].set_ylabel("fraction of rows", fontsize=8)
    axes[0].legend(fontsize=6, loc="upper right", frameon=False)
    axes[0].tick_params(labelsize=8)

    for i, name in enumerate(F.ORDERED_NAMES):
        tz = tz_hists[name]
        vals, counts = np.unique(tz, return_counts=True)
        axes[1].plot(vals, counts / counts.sum(), label=name, color=palette[i % len(palette)],
                     linewidth=1.2, marker="o", markersize=2)
    axes[1].set_ylim(bottom=0)
    axes[1].set_xlabel("mantissa trailing-zero count", fontsize=8)
    axes[1].set_ylabel("fraction of rows", fontsize=8)
    axes[1].legend(fontsize=6, loc="upper left", frameon=False)
    axes[1].tick_params(labelsize=8)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig", "fig_float_exp_tz.pdf"))
    plt.close(fig)

    dt = time.time() - t0
    print(f"wrote csv/float_fields.csv, fig/fig_float_exp_tz.pdf ({dt:.1f}s)")


if __name__ == "__main__":
    main()
