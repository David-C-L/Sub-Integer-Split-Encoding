#!/usr/bin/env python3
"""SIS against the best OpenZL configuration, axis by axis.

Only OpenZL configurations that compress at least as well as the compared SIS
arm count (openzl/auto always counts), so a small-block configuration cannot
win a speed axis by giving up compression.

For each column (shipped order) and axis, the cell is the best SIS view arm's
metric over the best OpenZL arm's metric (whole-payload or blocked), oriented
so that > 1 means SIS is better. Axes: size (bits/element), bulk decode,
point probe, range read at B = 64 and B = N, gather at selectivity 0.01 and
0.33 (run length 1), and encode (CPU time where the pull records it).
Medians over repeats. Reads the same pull as make_figures.py.
"""
import os

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA_DIR = os.environ.get("SIS_FIG_PULL", "derived/toplevel_sec7/pull_524k_toplevel")
OUT_DIR = os.environ.get("SIS_FIG_OUT", os.path.dirname(os.path.abspath(__file__)))
COLUMNS = (os.environ["SIS_FIG_COLUMNS"].split(",") if os.environ.get("SIS_FIG_COLUMNS") else
           ["snowflake", "xmark_prepost_full", "osm_h3_r9_fileorder", "osm_s2_l30_fileorder",
            "bing_quadkey", "uuidv7_hi", "publicbi_npi", "publicbi_id1", "uuidv7_lo"])
NICE = {"bing_quadkey": "bing quadkey", "uuidv7_hi": "UUIDv7 high", "uuidv7_lo": "UUIDv7 low", "snowflake": "snowflake", "xmark_prepost_full": "xmark prepost", "osm_h3_r9_fileorder": "osm h3 r9",
        "osm_s2_l30_fileorder": "osm s2 l30", "publicbi_npi": "BI npi", "publicbi_id1": "BI id1"}
N_STRUCTURED = int(os.environ.get("SIS_FIG_N_STRUCTURED", "6"))
SIS_VIEW = ["SIS/realNested+view", "SIS/hybrid+view"]
SIS_CURSOR = ["SIS/realNested", "SIS/hybrid"]
# One configuration held fixed on every axis and every column, so the paper can
# quote numbers a deployment would actually see rather than a per-axis best.
# SIS/realNested read through a view is the pick: scored against the best SIS
# arm per column (make_sis_arms.py) it is above 0.93 on all six read and size
# axes, 0.88 on encode, and the highest overall at 0.96 geomean;
# SIS/hybrid_auto compresses best (1.00) but falls to 0.35 on range B = 64 and
# 0.65 overall.
FIXED_ARM = os.environ.get("SIS_FIG_FIXED_ARM", "SIS/realNested")
FIXED_VIEW = [FIXED_ARM + "+view"]
FIXED_CURSOR = [FIXED_ARM]
OPENZL = ["openzl/auto", "openzl/block-1024", "openzl/block-65536"]


def repeats(prefix, column):
    frames = []
    for r in (1, 2, 3):
        path = os.path.join(DATA_DIR, f"{prefix}_{column}_shipped_r{r}.csv")
        if os.path.exists(path):
            d = pd.read_csv(path)
            d["_repeat"] = r
            frames.append(d)
    return pd.concat(frames, ignore_index=True) if frames else None


def best(df, arms, metric, higher_better, mask=None):
    """Best arm's median-over-repeats value of `metric`, and the arm name."""
    if df is None:
        return np.nan, None
    sub = df[df.encoding.isin(arms)]
    if "skipped" in sub.columns:
        sub = sub[sub.skipped != 1]
    if mask is not None:
        sub = sub[mask(sub)]
    if sub.empty:
        return np.nan, None
    per_rep = sub.groupby(["encoding", "_repeat"])[metric].median().reset_index()
    med = per_rep.groupby("encoding")[metric].median()
    arm = med.idxmax() if higher_better else med.idxmin()
    return med[arm], arm


rows = []
for column in COLUMNS:
    comp_path = os.path.join(DATA_DIR, f"comp_{column}_shipped.csv")
    if not os.path.exists(comp_path):
        continue
    comp = pd.read_csv(comp_path)
    comp["_repeat"] = 1
    enc = repeats("enc", column)
    enc_metric = "encode_cpu_Meps" if enc is not None and "encode_cpu_Meps" in enc.columns else "encode_Meps"
    bulk, point, rng, gat = (repeats(k, column) for k in ("bulk", "point", "range_hot", "gather_hot"))
    n_rows = int(comp["N"].iloc[0]) if "N" in comp.columns else None
    axes = [
        ("size", comp, "bits_per_elem", False, None, SIS_CURSOR),
        ("bulk", bulk, "decode_Meps", True, None, SIS_VIEW),
        ("point", point, "ns_per_probe", False, None, SIS_VIEW),
        ("range B=64", rng, "elem_Meps", True, lambda d: d.B == 64, SIS_VIEW),
        ("range B=N", rng, "elem_Meps", True, lambda d: d.B == d.N, SIS_VIEW),
        ("gather sel=0.01", gat, "gather_Meps", True, lambda d: (d.selectivity == 0.01) & (d.run_length == 1), SIS_VIEW),
        ("gather sel=0.33", gat, "gather_Meps", True, lambda d: (d.selectivity == 0.33) & (d.run_length == 1), SIS_VIEW),
        ("encode" + (" (CPU)" if enc_metric == "encode_cpu_Meps" else ""), enc, enc_metric, True, None, SIS_CURSOR),
    ]
    bits = comp.set_index("encoding")["bits_per_elem"].to_dict()
    for name, df, metric, higher, mask, sis_arms in axes:
        fixed = FIXED_CURSOR if sis_arms is SIS_CURSOR else FIXED_VIEW
        for mode, arms in (("best_per_axis", sis_arms), ("fixed_arm", fixed)):
            s_val, s_arm = best(df, arms, metric, higher, mask)
            # A blocked OpenZL configuration counts only where it compresses at
            # least as well as the SIS arm it is compared with: small blocks buy
            # decode speed by giving up the compression OpenZL is chosen for.
            # openzl/auto is the reference configuration and always counts.
            sis_bits = bits.get(s_arm.replace("+view", ""), np.nan) if s_arm else np.nan
            eligible = [a for a in OPENZL
                        if a == "openzl/auto" or bits.get(a, np.inf) <= sis_bits]
            z_val, z_arm = best(df, eligible, metric, higher, mask)
            ratio = (s_val / z_val if higher else z_val / s_val) if s_val and z_val else np.nan
            rows.append(dict(column=column, axis=name, mode=mode, ratio=ratio, sis_arm=s_arm,
                             sis=s_val, openzl_arm=z_arm, openzl=z_val))

board = pd.DataFrame(rows)
board.to_csv(os.path.join(OUT_DIR, "fig10_openzl_scoreboard.csv"), index=False)
axis_order = list(dict.fromkeys(board.axis))

PANELS = [("best_per_axis", "(a) best SIS arm per axis"),
          ("fixed_arm", f"(b) one fixed configuration: {FIXED_ARM.split('/')[1]} (+view on read axes)")]
grids = {m: board[board["mode"] == m].pivot(index="column", columns="axis", values="ratio")
                                      .reindex(index=COLUMNS, columns=axis_order)
         for m, _t in PANELS}

fig, axs = plt.subplots(1, 2, figsize=(7.0, 2.7), sharey=True,
                        gridspec_kw={"wspace": 0.06})
for ax, (mode, title) in zip(axs, PANELS):
    grid = grids[mode]
    im = ax.imshow(np.log10(grid.to_numpy(dtype=float)), aspect="auto", cmap="RdBu",
                   vmin=-2, vmax=2)
    ax.set_xticks(range(len(axis_order)))
    ax.set_xticklabels(axis_order, rotation=35, ha="right", fontsize=6)
    for i in range(len(COLUMNS)):
        for j in range(len(axis_order)):
            v = grid.iloc[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.0f}x" if v >= 10 else f"{v:.2g}x", ha="center", va="center",
                        fontsize=5, color="white" if abs(np.log10(v)) > 1.2 else "black")
    ax.axhline(N_STRUCTURED - 0.5, color="black", linewidth=1.2)
    ax.set_title(title, fontsize=7, pad=3)
axs[0].set_yticks(range(len(COLUMNS)))
axs[0].set_yticklabels([NICE[c] for c in COLUMNS], fontsize=6.5)
cbar = fig.colorbar(im, ax=axs, shrink=0.9, pad=0.015)
cbar.set_label("SIS over best OpenZL arm\n(log10; > 0 means SIS is better)", fontsize=6.5)
cbar.ax.tick_params(labelsize=6)
for ext, kw in (("pdf", {}), ("png", {"dpi": 200})):
    fig.savefig(os.path.join(OUT_DIR, f"fig10_openzl_scoreboard.{ext}"), bbox_inches="tight", **kw)
for mode, title in PANELS:
    print(f"--- {title} ---")
    print(grids[mode].round(2).to_string())
lost = (grids["fixed_arm"] / grids["best_per_axis"]).min()
print("\nfixed arm vs best-per-axis, worst column on each axis:")
print(lost.round(3).to_string())
