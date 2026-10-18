#!/usr/bin/env python3
"""fig10 scoreboard at \\columnwidth (2026-10-06).

Mixed inputs, per EVAL_FIGURE_MAP_20261006.md (7.3 item 1):
  size axis            : pulls/stageE_rerun_20261003_1139/scoreboard_samebuild/fig10_openzl_scoreboard.csv
                         (same build, full length)
  every other axis     : paper-repo/eval_figures/latest_524k_rev-sweep-524k_20260924/fig10_openzl_scoreboard.csv
  (bulk, point, ranges, gathers, encode (CPU))   (524,288 rows, cache resident)
Rows are taken as they are (mode fixed_arm), merged row-wise by axis into
fig10_openzl_scoreboard_mixed.csv; no value is recomputed.

Colour map, clip, value formatting and contrast rule are copied from
paper_handover/figures_full2_20261003/scripts/make_fig10_scoreboard_full2.py. Layout is
transposed for one column: datasets are rows (Table 1 names), axes are columns with
rotated headers; the "x" suffix is dropped inside cells (the key carries it).
"""
import os
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plot"))
from compact_common import COL_PT, OUT, save

ROOT = os.environ.get("SIS_ARTIFACT_ROOT", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
SIZE_CSV = os.environ.get("SIS_FIG10_SIZE_CSV", f"{ROOT}/derived/toplevel_sec7/scoreboard_size_toplevel/fig10_openzl_scoreboard.csv")
SPEED_CSV = os.environ.get("SIS_FIG10_SPEED_CSV", f"{ROOT}/derived/toplevel_sec7/scoreboard_524k_toplevel/fig10_openzl_scoreboard.csv")
MODE = "fixed_arm"

ROWS = [("snowflake", "Snowflake", "Structured"), ("xmark_prepost_full", "XMark", "Structured"),
        ("osm_h3_r9_fileorder", "OSM h3_r9", "Structured"), ("osm_s2_l30_fileorder", "OSM s2_l30", "Structured"),
        ("bing_quadkey", "Bing quadkey", "Structured"), ("uuidv7_hi", "UUIDv7 high", "Structured"),
        ("publicbi_npi", "PublicBI NPI", "Unstructured"), ("publicbi_id1", "PublicBI Id1", "Unstructured"),
        ("uuidv7_lo", "UUIDv7 low", "Unstructured")]
AXES = [("size", "size", None), ("bulk", "bulk", "read"), ("point", "point", "read"),
        ("range B=64", "range B=64", "read"), ("range B=N", "range B=N", "read"),
        ("gather sel=0.01", "gather 1%", "read"), ("gather sel=0.33", "gather 33%", "read"),
        ("encode (CPU)", "encode", None)]

CLIP_LO, CLIP_HI = 0.1, 1000.0
LO, HI = np.log10(CLIP_LO), np.log10(CLIP_HI)
NEUTRAL = "#f0efec"
ORANGE = [(-1.0, "#b04418"), (-0.6, "#eb6834"), (-0.25, "#f5c3ab")]
BLUE = [(0.25, "#cde2fb"), (1.0, "#86b6ef"), (1.6, "#3987e5"), (2.2, "#256abf"), (3.0, "#0d366b")]
INK, INK_ON_DARK = "#1a1a19", "#ffffff"
FS = 8.0


def make_cmap():
    stops = sorted(ORANGE + [(0.0, NEUTRAL)] + BLUE)
    return LinearSegmentedColormap.from_list("sis_div", [((x - LO) / (HI - LO), c) for x, c in stops], N=512)


def fmt(v):  # as full2 script, without the trailing "x"
    if v >= 1000:
        k = v / 1000
        return f"{k:.1f}k" if k < 9.95 else f"{k:.0f}k"
    if v >= 100:
        return f"{float(f'{v:.2g}'):.0f}"
    if v >= 10:
        return f"{v:.0f}"
    if v >= 1:
        return f"{v:.1f}"
    return f"{v:.2f}"


def rel_lum(rgb):
    c = np.asarray(rgb[:3], dtype=float)
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted((rel_lum(a), rel_lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


a = pd.read_csv(SIZE_CSV)
b = pd.read_csv(SPEED_CSV)
a = a[(a["mode"] == MODE) & (a.axis == "size")]
b = b[(b["mode"] == MODE) & (b.axis != "size")]
mixed = pd.concat([a.assign(source="toplevel_full_length"), b.assign(source="toplevel_524k")],
                  ignore_index=True)
mixed.to_csv(os.path.join(OUT, "fig10_openzl_scoreboard_mixed.csv"), index=False)
grid = mixed.pivot(index="column", columns="axis", values="ratio").reindex(
    index=[r[0] for r in ROWS], columns=[x[0] for x in AXES])
vals = grid.to_numpy(dtype=float)
assert not np.isnan(vals).any(), grid
nr, nc = vals.shape

plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "Liberation Sans", "font.size": FS})
cmap = make_cmap()

# geometry (points)
W = COL_PT
GL = 11.0          # rotated row-group label column
NAMEW = 50.0       # dataset names
HEAD = 54.0        # rotated axis headers + "read" bracket
CBZ = 21.0         # colour key strip
ROWH = 11.0
PAD = 1.0
left = PAD + GL + NAMEW
cw = (W - left - PAD) / nc
H = PAD + HEAD + nr * ROWH + CBZ + PAD
fig = plt.figure(figsize=(W / 72, H / 72))
ax = fig.add_axes([left / W, (PAD + CBZ) / H, nc * cw / W, nr * ROWH / H])
z = np.clip(np.log10(vals), LO, HI)
ax.imshow(z, cmap=cmap, vmin=LO, vmax=HI, aspect="auto", interpolation="nearest",
          extent=(-0.5, nc - 0.5, nr - 0.5, -0.5))
for j in range(1, nc):
    ax.axvline(j - 0.5, color="white", lw=0.7)
for i in range(1, nr):
    ax.axhline(i - 0.5, color="white", lw=0.7)
min_c = 99.0
for i in range(nr):
    for j in range(nc):
        bg = cmap((z[i, j] - LO) / (HI - LO))
        c_ink, c_wh = contrast(bg, matplotlib.colors.to_rgb(INK)), contrast(bg, (1, 1, 1))
        min_c = min(min_c, max(c_ink, c_wh))
        ax.text(j, i, fmt(vals[i, j]), ha="center", va="center", fontsize=FS,
                color=INK if c_ink >= c_wh else INK_ON_DARK)
# dark rules: dataset groups (rows) and axis groups (size | read | encode)
groups = [r[2] for r in ROWS]
for i in range(1, nr):
    if groups[i] != groups[i - 1]:
        ax.axhline(i - 0.5, color=INK, lw=0.8)
agroups = [x[2] for x in AXES]
for j in range(1, nc):
    if agroups[j] != agroups[j - 1]:
        ax.axvline(j - 0.5, color=INK, lw=0.8)
ax.set_xlim(-0.5, nc - 0.5)
ax.set_ylim(nr - 0.5, -0.5)
ax.set_xticks(range(nc))
ax.set_xticklabels([x[1] for x in AXES], rotation=90, fontsize=FS)
ax.xaxis.tick_top()
ax.set_yticks(range(nr))
ax.set_yticklabels([r[1] for r in ROWS], fontsize=FS)
ax.tick_params(length=0, pad=1.5)
for s in ax.spines.values():
    s.set_visible(False)

# rotated row-group labels with a bracket
start = 0
for i in range(1, nr + 1):
    if i == nr or groups[i] != groups[start]:
        yt = (PAD + HEAD + start * ROWH + 1, PAD + HEAD + i * ROWH - 1)
        fig.add_artist(plt.Line2D([(PAD + GL) / W] * 2, [1 - yt[0] / H, 1 - yt[1] / H], color=INK, lw=0.6))
        # a label longer than its bracket hangs down into the empty gutter below the table
        if i == nr:
            fig.text((PAD + GL / 2 - 0.5) / W, 1 - yt[0] / H, groups[start], rotation=90,
                     ha="center", va="top", fontsize=FS)
        else:
            fig.text((PAD + GL / 2 - 0.5) / W, 1 - (yt[0] + yt[1]) / 2 / H, groups[start], rotation=90,
                     ha="center", va="center", fontsize=FS)
        start = i
# "read" bracket over the read axes (above the rotated headers)
r0 = agroups.index("read")
r1 = len(agroups) - 1 - agroups[::-1].index("read")
yb = (PAD + 9) / H
fig.add_artist(plt.Line2D([(left + r0 * cw + 1) / W, (left + (r1 + 1) * cw - 1) / W], [1 - yb] * 2,
                          color=INK, lw=0.6))
fig.text((left + (r0 + r1 + 1) / 2 * cw) / W, 1 - (PAD + 4.5) / H, "read", ha="center",
         va="center_baseline", fontsize=FS)
fig.text(PAD / W, 1 - (PAD + 4.5) / H, "Metric", ha="left", va="center_baseline", fontsize=FS,
         fontweight="bold")
fig.text(PAD / W, 1 - (PAD + HEAD - 5) / H, "Dataset", ha="left", va="center_baseline", fontsize=FS,
         fontweight="bold")

# colour key
cb_w = 90.0
cb_l = left + (nc * cw - cb_w) / 2
cax = fig.add_axes([cb_l / W, (PAD + 11) / H, cb_w / W, 4.5 / H])
cax.imshow(np.linspace(LO, HI, 512)[None, :], cmap=cmap, vmin=LO, vmax=HI, aspect="auto",
           extent=(LO, HI, 0, 1))
ticks = [0.1, 1, 10, 100, 1000]
cax.set_xticks(np.log10(ticks))
cax.set_xticklabels(["0.1×", "1×", "10×", "", "≥1000×"], fontsize=FS)
cax.set_yticks([])
cax.tick_params(axis="x", length=1.5, width=0.5, pad=1)
for s in cax.spines.values():
    s.set_linewidth(0.5)
cax.axvline(0, color=INK, lw=0.7)
cax.text(LO - 0.12, 0.5, "SIS worse", ha="right", va="center", fontsize=FS, transform=cax.transData)
cax.text(HI + 0.12, 0.5, "SIS better", ha="left", va="center", fontsize=FS, transform=cax.transData)
cax.set_xlim(LO, HI)

save(fig, "fig10_openzl_scoreboard")
print(f"cell {cw:.1f} x {ROWH} pt, min text contrast {min_c:.2f}:1")
for cname, aname in (("snowflake", "point"), ("xmark_prepost_full", "size"), ("uuidv7_hi", "size"),
                     ("publicbi_npi", "encode (CPU)")):
    print(f"check {cname:>20s} {aname:>14s}: {grid.loc[cname, aname]!r} -> '{fmt(grid.loc[cname, aname])}'")
