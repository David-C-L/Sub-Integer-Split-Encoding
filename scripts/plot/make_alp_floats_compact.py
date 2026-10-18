#!/usr/bin/env python3
"""Two half-column subfigures (2026-10-17), palette tol_hc, from alp_floats_20261017_0115.

(a) fig_alp_floats_size:  bits/value, SIS (SIS/realNested) | ALP (CWI reference; smaller than Nimble ALP
    on all five columns) | OpenZL (qualifying arm with the fewest bits = openzl/auto). Linear y from 0.
(b) fig_alp_floats_range: time per range read of B=64 rows (us, median time_ns of the range driver,
    median of 3 per-repeat medians), SIS/realNested+view | Nimble ALP/view | OpenZL (fastest qualifying arm:
    openzl/auto always, blocks only when no larger than SIS). Log y.
No values are recomputed beyond the medians; ns -> us is the only change of unit.
"""
import os
import sys

import numpy as np
import pandas as pd

os.environ.setdefault("SIS_PALETTE", "tol_hc")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import artifact_paths as AP  # noqa: E402
import paperstyle  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import LogLocator, NullFormatter  # noqa: E402

PULL = os.path.join(AP.DATA, "alp_floats/runs")
REF = os.path.join(AP.DATA, "alp_floats/alp_ref_sizes.csv")
OUT = AP.OUT
COLS = [("F1_stocks_usa", "Stocks"), ("F5_city_temp", "Temp"), ("F6_air_pressure", "Press."),
        ("F8_poi_lat", "POI-lat"), ("F10_medicare_calc", "Calc.")]
OPENZL = ["openzl/auto", "openzl/block-1024", "openzl/block-65536"]
E = paperstyle.ENTITIES
SER = [("SIS", E["SIS_DEFAULT"]["color"]), ("ALP", E["ALP"]["color"]), ("OpenZL", E["OPENZL"]["color"])]


def med(df, arm, metric):
    s = df[(df.encoding == arm) & (df.skipped != 1)]
    return s.groupby("_repeat")[metric].median().median() if len(s) else np.nan


rows = []
ref = pd.read_csv(REF).set_index("column")["size"]
for c, lab in COLS:
    comp = pd.read_csv(os.path.join(PULL, f"comp_{c}_shipped.csv"))
    bits = comp[comp.skipped != 1].set_index("encoding")["bits_per_elem"]
    sis_bits = bits["SIS/realNested"]
    zl = [a for a in OPENZL if a == "openzl/auto" or bits.get(a, np.inf) <= sis_bits]
    rng = pd.concat([pd.read_csv(os.path.join(PULL, f"range_hot_{c}_shipped_r{r}.csv")).assign(_repeat=r)
                     for r in (1, 2, 3)])
    rng = rng[rng.B == 64]
    zl_t = {a: med(rng, a, "time_ns") for a in zl}
    zl_arm = min(zl_t, key=zl_t.get)
    zl_size_arm = min(zl, key=lambda a: bits[a])
    rows.append(dict(column=c, label=lab, size_SIS=sis_bits, size_ALP_CWI=ref[c], size_ALP_nimble=bits["ALP"],
                     size_OpenZL=bits[zl_size_arm], size_OpenZL_arm=zl_size_arm,
                     range64_us_SIS=med(rng, "SIS/realNested+view", "time_ns") / 1e3,
                     range64_us_ALPview=med(rng, "ALP/view", "time_ns") / 1e3,
                     range64_us_OpenZL=zl_t[zl_arm] / 1e3, range64_OpenZL_arm=zl_arm))
d = pd.DataFrame(rows)
assert (d.size_ALP_CWI <= d.size_ALP_nimble).all()
d.to_csv(os.path.join(OUT, "alp_floats_compact_values.csv"), index=False)
print(d.round(3).to_string())

paperstyle.apply_rcparams()
plt.rcParams.update({"font.family": "Liberation Sans", "axes.grid": False})
W, H = 118.0, 100.0
L, R, B, T = 27.0, 2.0, 24.0, 3.0  # identical axes box in both panels
x = np.arange(len(COLS))
w = 0.27


def panel(name, keys, ylabel, log):
    fig = plt.figure(figsize=(W / 72, H / 72))
    ax = fig.add_axes([L / W, B / H, (W - L - R) / W, (H - B - T) / H])
    for k, ((lab, col), key) in enumerate(zip(SER, keys)):
        ax.bar(x + (k - 1) * w, d[key], w, color=col, edgecolor="black", linewidth=0.3, label=lab, zorder=2)
    ax.set_xticks(x)
    ax.set_xticklabels(d.label, rotation=45, ha="right", rotation_mode="anchor")
    ax.tick_params(axis="x", length=0, pad=2)
    ax.tick_params(axis="y", length=2, pad=1)
    ax.set_xlim(-0.55, len(COLS) - 0.45)
    ax.set_ylabel(ylabel, labelpad=1)
    ax.yaxis.grid(True, color="#dddddd", lw=0.5, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if log:
        ax.set_yscale("log")
        ax.set_ylim(0.3, 2e4)
        ax.yaxis.set_major_locator(LogLocator(base=10, numticks=10))
        ax.yaxis.set_minor_formatter(NullFormatter())
        ax.set_yticks([1, 1e2, 1e4])
        ax.set_yticklabels(["1", "100", "10k"])
    else:
        ax.set_ylim(bottom=0, top=70)
        ax.set_yticks([0, 20, 40, 60])
        ax.legend(loc="upper left", ncol=1, handlelength=1.0, handletextpad=0.4, borderpad=0.2,
                  labelspacing=0.2, borderaxespad=0.2, frameon=True, facecolor="white", edgecolor="none",
                  framealpha=1.0)
    fig.savefig(os.path.join(OUT, name + ".pdf"))
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=300)
    plt.close(fig)


panel("fig_alp_floats_size", ["size_SIS", "size_ALP_CWI", "size_OpenZL"], "bits/value", False)
panel("fig_alp_floats_range", ["range64_us_SIS", "range64_us_ALPview", "range64_us_OpenZL"], "µs per range of 64", True)
print(f"each panel {W:.0f} x {H:.0f} pt")
