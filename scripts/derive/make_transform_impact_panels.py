#!/usr/bin/env python3
"""What the SIS transform layer buys, and what it costs to read.

The transform layer exists to compress better without giving up random
access. This figure puts the two sides next to each other for every column
and every arrival order the sweep carries.

  transforms off : SIS/realNested (DP planner)      and SIS/hybrid
  transforms on  : SIS/auto (DP planner, per-section transform search)
                   and SIS/hybrid_auto

Panel (a) is the size the layer saves, per column and arrival order. Orders
that were measured for compression only are drawn open and marked, because
their read cost is unknown. Panel (b) is the read cost that saving buys: for
each timed (column, order) the transforms-on arm's read rate over the
transforms-off arm's, on point, bulk and range B = 64. A point at y = 1 means
the transform was free to read.

Absolute read rates are also written to the CSV normalised to
FixedBitWidth/view, so the reader can see the level, not only the ratio.

Env: SIS_FIG_PULL, SIS_FIG_OUT, SIS_FIG_COLUMNS, SIS_FIG_N_STRUCTURED.
Outputs fig12_transform_impact.{pdf,png} and fig12_transform_impact.csv.

2026-09-29 resize: panels are placed at 0.49\\columnwidth (1.632in) in the
paper, not a full column (3.33in), so figsize is now the exact final width
and every font floor is raised to >= 8pt (see README_fig12_transform_impact.md
next to this script's output for the per-element minimums achieved).
"""
import glob
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
N_STRUCTURED = int(os.environ.get("SIS_FIG_N_STRUCTURED", "6"))
SHORT = {"snowflake": "snow", "xmark_prepost_full": "xmark", "osm_h3_r9_fileorder": "h3",
         "osm_s2_l30_fileorder": "s2", "bing_quadkey": "quad", "uuidv7_hi": "u7-hi",
         "publicbi_npi": "npi", "publicbi_id1": "id1", "uuidv7_lo": "u7-lo"}
ORDER_NICE = {"shipped": "ship", "mergeirr_8": "mirr8", "mergekey_0": "mkey0",
              "mergekey_2": "mkey2", "shuffled": "shuf", "sorted": "sort"}
ORDER_SEQ = ["shipped", "mergeirr_8", "mergekey_0", "mergekey_2", "shuffled", "sorted"]

# planner label -> (transforms off arm, transforms on arm, colour, hatch)
PAIRS = [("DP planner", "SIS/realNested", "SIS/auto", "#0072B2", None),
         ("hybrid planner", "SIS/hybrid", "SIS/hybrid_auto", "#56B4E9", "///")]
BASELINE = "FixedBitWidth/view"
C_GREY = "#999999"
AXIS_STYLE = [("point", "o"), ("bulk", "s"), ("range B=64", "^")]

plt.rcParams.update({
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
    "pdf.fonttype": 42, "ps.fonttype": 42, "axes.linewidth": 0.6,
})


def repeats(prefix, column, order):
    frames = []
    for r in (1, 2, 3):
        path = os.path.join(DATA_DIR, f"{prefix}_{column}_{order}_r{r}.csv")
        if os.path.exists(path):
            d = pd.read_csv(path)
            d["_repeat"] = r
            frames.append(d)
    return pd.concat(frames, ignore_index=True) if frames else None


def med(df, encoding, metric, mask=None):
    if df is None:
        return np.nan
    sub = df[df.encoding == encoding]
    if "skipped" in sub.columns:
        sub = sub[sub.skipped != 1]
    if mask is not None:
        sub = sub[mask(sub)]
    if sub.empty:
        return np.nan
    return float(sub.groupby("_repeat")[metric].median().median())


def orders_of(column):
    found = []
    for path in glob.glob(os.path.join(DATA_DIR, f"comp_{column}_*.csv")):
        found.append(os.path.basename(path)[len(f"comp_{column}_"):-4])
    return [o for o in ORDER_SEQ if o in found] + sorted(set(found) - set(ORDER_SEQ))


rows = []
for column in COLUMNS:
    for order in orders_of(column):
        comp = pd.read_csv(os.path.join(DATA_DIR, f"comp_{column}_{order}.csv"))
        bits = comp.set_index("encoding")["bits_per_elem"].to_dict()
        point = repeats("point", column, order)
        bulk = repeats("bulk", column, order)
        rng = repeats("range_hot", column, order)
        timed = point is not None and bulk is not None and rng is not None
        # Read rate, oriented higher-is-better, so a ratio reads the same way
        # on every axis.
        def rate(enc):
            return {
                "point": 1e3 / med(point, enc, "ns_per_probe"),  # probes per us
                "bulk": med(bulk, enc, "decode_Meps"),
                "range B=64": med(rng, enc, "elem_Meps", lambda d: d.B == 64),
            }
        base = rate(BASELINE) if timed else {a: np.nan for a, _ in AXIS_STYLE}
        for planner, off, on, _c, _h in PAIRS:
            b_off, b_on = bits.get(off, np.nan), bits.get(on, np.nan)
            r_off = rate(off + "+view") if timed else {}
            r_on = rate(on + "+view") if timed else {}
            row = dict(column=column, order=order, planner=planner, timed=int(timed),
                       bits_off=b_off, bits_on=b_on,
                       size_reduction_pct=100.0 * (b_off - b_on) / b_off if b_off else np.nan)
            for axis, _m in AXIS_STYLE:
                row[f"{axis}_off_vs_fbw"] = r_off.get(axis, np.nan) / base[axis] if timed else np.nan
                row[f"{axis}_on_vs_fbw"] = r_on.get(axis, np.nan) / base[axis] if timed else np.nan
                row[f"{axis}_retained"] = (r_on.get(axis, np.nan) / r_off.get(axis, np.nan)
                                            if timed else np.nan)
            rows.append(row)

tt = pd.DataFrame(rows)
tt.to_csv(os.path.join(OUT_DIR, "fig12_transform_impact.csv"), index=False)


def _timed_any(df, column, order):
    sub = df[(df.column == column) & (df.order == order)]
    return bool(sub.timed.max()) if not sub.empty else False


# --- figure -------------------------------------------------------------
# the author's figure rules (2026-09-28): one panel per PDF, no in-plot titles.
# 2026-09-29: panels are placed at 0.49\columnwidth (columnwidth = 3.33in),
# so the true target width is 1.632in, not a full column. Height grows to
# keep the >=8pt font floor legible given 9 columns x up to 6 orders in
# panel (a); still flagged as tight in the README.
PANEL_W = 1.632
# figsize is intentionally smaller than PANEL_W: bbox_inches="tight" expands
# the saved PDF to include rotated tick labels, the y-axis label and legend
# text that stick out past the nominal axes box at this width, so the
# figsize below is tuned (see README) so the *saved* PDF lands at PANEL_W.
figa, axa = plt.subplots(1, 1, figsize=(1.291, 3.9))
figb, axb = plt.subplots(1, 1, figsize=(1.259, 3.6))

# (a) size the transform layer saves.
xt, xl = [], []
pos = 0.0
for column in COLUMNS:
    ords = [o for o in orders_of(column) if not tt[(tt.column == column) & (tt.order == o)].empty]
    start = pos
    for order in ords:
        for k, (planner, _off, _on, color, hatch) in enumerate(PAIRS):
            r = tt[(tt.column == column) & (tt.order == order) & (tt.planner == planner)]
            if r.empty:
                continue
            r = r.iloc[0]
            axa.bar(pos + k * 0.42, r.size_reduction_pct, 0.40, color=color if r.timed else "white",
                    edgecolor=color, linewidth=0.6, hatch=hatch if r.timed else "",
                    label=planner if (column == COLUMNS[0] and order == ords[0]) else None)
        pos += 1.05
    # Columns measured in one order only would otherwise sit so close that
    # their names run together, so every group gets a minimum width.
    span = max(pos - start, 3.2)
    xt.append(start + span / 2 - 0.32)
    xl.append(SHORT.get(column, column))
    pos = start + span + 0.55
# 2026-09-29 resize: at the 1.632in placed width, 29 individual per-order
# tick labels (rotated, >=8pt) cannot fit without overlapping -- each rotated
# label needs ~1 line-height (~0.13in) of horizontal room, and the panel only
# has ~1.3in of usable plot width for all 29 groups combined (see
# README_fig12_transform_impact.md). Per-order labels are dropped; only the
# column-level tick (below) is kept. The bars and their left-to-right order
# within each column group are unchanged and still follow ORDER_SEQ, and the
# full per-order breakdown remains in fig12_transform_impact.csv.
axa.set_xticks([])
for x, label in zip(xt, xl):
    axa.text(x, -0.03, label, ha="center", va="top", fontsize=8, rotation=90,
             transform=axa.get_xaxis_transform())
axa.set_ylabel("Size saved by the\ntransform layer (%)")
axa.set_ylim(bottom=0)
axa.set_xlim(-0.6, pos - 0.55)
axa.axvline(xt[N_STRUCTURED - 1] + (xt[N_STRUCTURED] - xt[N_STRUCTURED - 1]) / 2,
            color="black", linewidth=0.8, linestyle=(0, (3, 2)))
axa.grid(True, axis="y", alpha=0.25, linewidth=0.4)
axa.set_ylim(top=axa.get_ylim()[1] * 1.22)
axa.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=1,
           handletextpad=0.3, borderaxespad=0.15, labelspacing=0.25)

# (b) the read cost that buys.
for axis, marker in AXIS_STYLE:
    for planner, _off, _on, color, _h in PAIRS:
        sub = tt[(tt.planner == planner) & (tt.timed == 1)]
        axb.scatter(sub.size_reduction_pct, sub[f"{axis}_retained"], s=16, marker=marker,
                    facecolors="none", edgecolors=color, linewidths=0.8,
                    label=f"{axis}, {planner.split()[0]}")
axb.axhline(1.0, color=C_GREY, linewidth=0.8)
axb.axvline(0.0, color=C_GREY, linewidth=0.8)
axb.set_xlabel("size saved by\ntransform layer (%)")
axb.set_ylabel("read rate retained\n(transforms on / off)")
axb.set_ylim(bottom=0)
axb.set_xlim(left=-1)
axb.grid(True, alpha=0.25, linewidth=0.4)
# One legend entry per read axis (marker) and one per planner (colour), so the
# key does not have to list all six combinations over the data. Stacked in a
# single column (rather than 3 columns) because the panel is now half as wide.
handles = [plt.Line2D([], [], marker=m, color="0.4", ls="none", mfc="none", ms=4, label=a)
           for a, m in AXIS_STYLE]
handles += [plt.Line2D([], [], marker="o", color=c, ls="none", mfc="none", ms=4, label=pl)
            for pl, _o, _n, c, _h in PAIRS]
axb.legend(handles=handles, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.42),
           ncol=1, columnspacing=0.9, handletextpad=0.3, borderpad=0.2)

for fig, name in ((figa, "fig12_transform_impact_a"), (figb, "fig12_transform_impact_b")):
    for ext, kw in (("pdf", {}), ("png", {"dpi": 200})):
        fig.savefig(os.path.join(OUT_DIR, f"{name}.{ext}"), bbox_inches="tight",
                    pad_inches=0.02, **kw)
    plt.close(fig)
    print("wrote panel", name)

# --- what the caption may claim ------------------------------------------
timed = tt[tt.timed == 1]
fires = tt[tt.size_reduction_pct > 1.0]
print("wrote fig12_transform_impact")
print(f"cells: {len(tt)} (column, order, planner); {len(timed)} timed, {len(tt) - len(timed)} compression only")
print(f"transform layer saves >1% in {len(fires)} of {len(tt)} cells; "
      f"max {fires.size_reduction_pct.max():.1f}% "
      f"({fires.loc[fires.size_reduction_pct.idxmax(), 'column']}/"
      f"{fires.loc[fires.size_reduction_pct.idxmax(), 'order']})")
for axis, _m in AXIS_STYLE:
    f = timed[timed.size_reduction_pct > 1.0][f"{axis}_retained"]
    n = timed[timed.size_reduction_pct <= 1.0][f"{axis}_retained"]
    print(f"  {axis:11s} retained: where the layer fires median {f.median():.2f} "
          f"(min {f.min():.2f}); where it does not, median {n.median():.2f}")
