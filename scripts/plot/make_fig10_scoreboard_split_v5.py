#!/usr/bin/env python3
"""V3 (2026-10-17): v2 with every cell and both keys drawn as vector pcolormesh quads (no raster image,
which PDF viewers smooth). Otherwise identical to v2.

V2 (2026-10-17, the author): the left panel (size, encode) gets its own diverging log scale, 0.25x-4x centred
at 1x (same palette stops, compressed onto that range), with its own key under it; the right panel and its
key keep 0.1x-1000x. Size, cell values and everything else as the split figure.

SPLIT VARIANT (2026-10-16) of the TopLevel fig10 script: same data/cmap/format, two panels
(size+encode | reads) side by side, one shared colour key. Original docstring follows.

fig10 scoreboard at \\columnwidth (2026-10-06).

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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # 2026-10-17: compact_common + paperstyle copy
from compact_common import COL_PT, PAD_PT
import paperstyle
import artifact_paths as AP  # artifact-relative paths
OUT = AP.OUT


def save(fig, name):
    fig.savefig(os.path.join(OUT, name + ".pdf"))
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=300)

SIZE_CSV = os.environ.get("SIS_FIG10_SIZE_CSV", os.path.join(AP.DERIVED, "fig10_openzl_scoreboard_mixed.csv"))  # TopLevel 2026-10-14 mixed CSV (size rows: full length; rest 524k)
SPEED_CSV = os.environ.get("SIS_FIG10_SPEED_CSV", SIZE_CSV)
MODE = "fixed_arm"

_GROUP = ["Structured"] * 6 + ["Unstructured"] * 3
ROWS = [(c, paperstyle.short_label(c), g) for c, g in zip(  # 2026-10-17: Sec. 7 short names
    ["snowflake", "xmark_prepost_full", "osm_h3_r9_fileorder", "osm_s2_l30_fileorder", "bing_quadkey", "uuidv7_hi",
     "publicbi_npi", "publicbi_id1", "uuidv7_lo"], _GROUP)]
AXES = [("size", "size", None), ("bulk", "bulk", "read"), ("point", "point", "read"),
        ("range B=64", "range (64)", "read"), ("range B=N", "range (N)", "read"),
        ("gather sel=0.01", "gather 1%", "read"), ("gather sel=0.33", "gather 33%", "read"),
        ("encode (CPU)", "encode", None)]

CLIP_LO, CLIP_HI = 0.1, 1000.0
LO, HI = np.log10(CLIP_LO), np.log10(CLIP_HI)
NEUTRAL, ORANGE, BLUE = paperstyle.scoreboard_stops()  # palette B: the original hard-coded stops
INK, INK_ON_DARK = "#1a1a19", "#ffffff"
FS = 8.0
FS_METRIC = 7.0  # v4: metric labels 1 pt smaller to lower the header


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
grid = mixed.pivot(index="column", columns="axis", values="ratio").reindex(
    index=[r[0] for r in ROWS], columns=[x[0] for x in AXES])
PANELS = [[AXES[0], AXES[7]], AXES[1:7]]  # (size, encode) | reads
vals = grid.to_numpy(dtype=float)
assert not np.isnan(vals).any(), grid
nr = vals.shape[0]

plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "Liberation Sans", "font.size": FS})
cmap = make_cmap()
# v2: left-panel scale. Palette stops (log10 units, -1..0 and 0..3) mapped linearly onto -L..0 and 0..L.
LO_L, HI_L = np.log10(0.25), np.log10(4.0)


BAND = np.log10(1 / float(os.environ.get("FIG10_PARITY", 0.85)))  # v5: |log ratio| <= BAND renders neutral (parity band)


def make_cmap_left():
    # v5: palette ramps start at the edge of the parity band instead of at 1x
    stops = ([(-BAND + x / 1.0 * (-LO_L - BAND), c) for x, c in ORANGE] + [(-BAND, NEUTRAL), (BAND, NEUTRAL)]
             + [(BAND + x / 3.0 * (HI_L - BAND), c) for x, c in BLUE])
    return LinearSegmentedColormap.from_list("sis_div_l", [((x - LO_L) / (HI_L - LO_L), c) for x, c in sorted(stops)], N=512)


cmap_l = make_cmap_left()
SCALES = [(cmap_l, LO_L, HI_L), (cmap, LO, HI)]

# geometry (points); same HEAD/ROWH/CBZ/NAMEW/GL as TopLevel so height is unchanged
W = COL_PT
GL, NAMEW, HEAD, CBZ, ROWH, PAD = 11.0, 50.0, float(os.environ.get("FIG10_HEAD", 48.0)), 21.0, 11.0, 1.0
GAP = 5.0
left = PAD + GL + NAMEW
ncs = [len(p) for p in PANELS]
cw = (W - left - PAD - GAP) / sum(ncs)
H = PAD + HEAD + nr * ROWH + CBZ + PAD
fig = plt.figure(figsize=(W / 72, H / 72))
groups = [r[2] for r in ROWS]
min_c = 99.0
x0s = [left, left + ncs[0] * cw + GAP]
for pi, panel in enumerate(PANELS):
    nc = len(panel)
    ax = fig.add_axes([x0s[pi] / W, (PAD + CBZ) / H, nc * cw / W, nr * ROWH / H])
    v = grid[[a[0] for a in panel]].to_numpy(dtype=float)
    cm, lo, hi = SCALES[pi]
    z = np.clip(np.log10(v), lo, hi)
    ax.pcolormesh(np.arange(nc + 1) - 0.5, np.arange(nr + 1) - 0.5, z, cmap=cm, vmin=lo, vmax=hi, shading="flat",
                  edgecolors="face", linewidth=0.25, rasterized=False)  # vector cells
    for j in range(1, nc):
        ax.axvline(j - 0.5, color="white", lw=0.7)
    for i in range(1, nr):
        ax.axhline(i - 0.5, color="white", lw=0.7)
    for i in range(nr):
        for j in range(nc):
            bg = cm((z[i, j] - lo) / (hi - lo))
            c_ink, c_wh = contrast(bg, matplotlib.colors.to_rgb(INK)), contrast(bg, (1, 1, 1))
            min_c = min(min_c, max(c_ink, c_wh))
            ax.text(j, i, fmt(v[i, j]), ha="center", va="center", fontsize=FS,
                    color=INK if c_ink >= c_wh else INK_ON_DARK)
    for i in range(1, nr):
        if groups[i] != groups[i - 1]:
            ax.axhline(i - 0.5, color=INK, lw=0.8)
    ax.set_xlim(-0.5, nc - 0.5)
    ax.set_ylim(nr - 0.5, -0.5)
    ax.set_xticks(range(nc))
    ax.set_xticklabels([a[1] for a in panel], rotation=90, fontsize=FS_METRIC)
    ax.xaxis.tick_top()
    ax.set_yticks(range(nr))
    ax.set_yticklabels([r[1] for r in ROWS] if pi == 0 else [], fontsize=FS)
    ax.tick_params(length=0, pad=1.5)
    for sp in ax.spines.values():
        sp.set_visible(False)
    if pi == 1:  # "read" bracket over the read panel (as TopLevel)
        yb = (PAD + 9) / H
        fig.add_artist(plt.Line2D([(x0s[1] + 1) / W, (x0s[1] + nc * cw - 1) / W], [1 - yb] * 2, color=INK, lw=0.6))
        fig.text((x0s[1] + nc * cw / 2) / W, 1 - (PAD + 4.5) / H, "read ratio", ha="center",
                 va="center_baseline", fontsize=FS)

# rotated row-group labels with a bracket (as TopLevel)
start = 0
for i in range(1, nr + 1):
    if i == nr or groups[i] != groups[start]:
        yt = (PAD + HEAD + start * ROWH + 1, PAD + HEAD + i * ROWH - 1)
        fig.add_artist(plt.Line2D([(PAD + GL) / W] * 2, [1 - yt[0] / H, 1 - yt[1] / H], color=INK, lw=0.6))
        if i == nr:
            fig.text((PAD + GL / 2 - 0.5) / W, 1 - yt[0] / H, groups[start], rotation=90,
                     ha="center", va="top", fontsize=FS)
        else:
            fig.text((PAD + GL / 2 - 0.5) / W, 1 - (yt[0] + yt[1]) / 2 / H, groups[start], rotation=90,
                     ha="center", va="center", fontsize=FS)
        start = i
fig.text(PAD / W, 1 - (PAD + 4.5) / H, "Metric", ha="left", va="center_baseline", fontsize=FS, fontweight="bold")
fig.text(PAD / W, 1 - (PAD + HEAD - 5) / H, "Dataset", ha="left", va="center_baseline", fontsize=FS, fontweight="bold")

# colour keys (v2): one under each panel, same row and bar height as the split figure's single key
def colour_key(x0, w, cm, lo, hi, ticks, labels):
    cax = fig.add_axes([x0 / W, (PAD + 11) / H, w / W, 4.5 / H])
    _e = np.linspace(lo, hi, 257)  # vector key: 256 flat strips
    cax.pcolormesh(_e, [0, 1], ((_e[:-1] + _e[1:]) / 2)[None, :], cmap=cm, vmin=lo, vmax=hi, shading="flat",
        edgecolors="face", linewidth=0.25, rasterized=False)
    cax.set_ylim(0, 1)
    cax.set_xticks(np.log10(ticks))
    cax.set_xticklabels(labels, fontsize=FS)
    cax.set_yticks([])
    cax.tick_params(axis="x", length=1.5, width=0.5, pad=1)
    for sp in cax.spines.values():
        sp.set_linewidth(0.5)
    cax.axvline(0, color=INK, lw=0.7)
    cax.set_xlim(lo, hi)
    return cax


KL0, KL1 = 53.0, x0s[0] + ncs[0] * cw - 2      # left key: under the left panel, extended into the free label column
KR0, KR1 = x0s[1] + 13, W - PAD - 40            # right key: under the read panel, room for "SIS better"
kl = colour_key(KL0, KL1 - KL0, cmap_l, LO_L, HI_L, [0.25, 1, 4], ["0.25×", "1×", "4×"])
kr = colour_key(KR0, KR1 - KR0, cmap, LO, HI, [0.1, 1, 10, 100, 1000], ["0.1×", "1×", "10×", "", "≥1000×"])
fig.text((PAD + GL + 1.5) / W, (PAD + 11 + 2.25) / H, "SIS worse", ha="left", va="center", fontsize=FS)
fig.text((KR1 + 2.5) / W, (PAD + 11 + 2.25) / H, "SIS better", ha="left", va="center", fontsize=FS)

save(fig, "fig10_openzl_scoreboard_split_v5")
fig.canvas.draw()
bb = fig.get_tightbbox(fig.canvas.get_renderer())
print(f"content bbox x {bb.x0*72:.1f}-{bb.x1*72:.1f} of {W:.2f}, y {bb.y0*72:.1f}-{bb.y1*72:.1f} of {H:.1f} pt")

print(f"cell {cw:.1f} x {ROWH} pt, size {W:.2f} x {H:.1f} pt, min text contrast {min_c:.2f}:1")
