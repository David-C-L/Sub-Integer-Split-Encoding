#!/usr/bin/env python3
# V4 (2026-10-17): group labels shortened to fit their 3-row groups (7.5 pt, two short lines) and inside the page; nothing else changed vs v3.
# V3 (2026-10-17): the two NPI rows removed (NPI is not an SFV column); only COLS and the output name changed vs v2.
"""V2 (2026-10-17): colour keys drawn as vector pcolormesh strips (no raster image). Otherwise identical.

Fig. 12, SIS (default) only (2026-10-17, the author): copy of make_fig12_clarity.py with the re-priced
columns, planner sub-headers and planner/dataset role labels removed and a compact header (title row,
one colour-key row, Point/Bulk/Range row). Same CSV, cells, number format, norms and palette.
Original docstring follows.

Fig. 12 (transform impact heatmap), clarity re-render 2026-10-14.

Derived from paper_handover/figures_sec7_transforms_20261008/scripts/make_fig12_side_labels.py.
Same CSV, same rows, same cell values and number formatting, same norms
(size saved: linear 0-40 %; read rate kept: log2, centred on 100 %, 5 %-200 %).

Changed (layout and colour only):
  * "Metrics" heading removed; the corner holds only "planner" / "dataset" role labels;
  * each colour key sits directly under its own heading, spanning its own columns
    ("Size saved (%)" over the size column pair, "Read rate kept (%)" over the three
    read-rate pairs), instead of an untitled block in the table corner;
  * group headers (Point / Bulk / Range) horizontal; planner names rotated, one per cell column;
  * the two orderings separated by a 6 pt gap and a light rule, plus the side labels;
  * colours from palette B (paperstyle): size saved = Tol muted teal/green ramp; read
    rate kept = diverging wine/rose (lost) - light grey (100 %) - indigo (gained).
Rendered at \\columnwidth (241.14 pt); everything placed in points; 1 pt margin.
"""
import os
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize, TwoSlopeNorm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # 2026-10-17: paperstyle copy
import paperstyle  # noqa: E402
import artifact_paths as AP  # artifact-relative paths

SRC = os.environ.get("SIS_FIG12_CSV", os.path.join(AP.TL_DERIVED, "fig12_panels_toplevel/fig12_transform_impact.csv"))
OUT = AP.OUT
COLS = ["snowflake", "xmark_prepost_full", "osm_h3_r9_fileorder"]  # v3: NPI rows removed (not an SFV column)
PS_KEY = {"xmark_prepost_full": "xmark", "osm_h3_r9_fileorder": "osm_h3_r9"}
NAMES = {c: paperstyle.short_label(c) for c in COLS}  # 2026-10-17: Sec. 7 short names
BLOCKS = [("shipped", "Stored\norder"), ("mergeirr_8", "8-writer\norder")]
PLANNER = "DP planner"  # SIS (default)
GROUPS = [("size_reduction_pct", None), ("point_retained", "Point"),
          ("bulk_retained", "Bulk"), ("range B=64_retained", "Range")]

E = paperstyle.ENTITIES
INK, MUTED, RULE = "#1A1A1A", "#555555", "#9A9A9A"
paperstyle.apply_rcparams()
plt.rcParams.update({"axes.grid": False, "font.size": 8})

d = pd.read_csv(SRC)
t = d[(d.timed == 1) & d.column.isin(COLS)]

seq = LinearSegmentedColormap.from_list("seq", ["#F4F4F1", E["ALP_RD"]["color"], E["ALP"]["color"],
                                                E["ALP_REF"]["color"]])
div = LinearSegmentedColormap.from_list("div", paperstyle.fig12_div_colors())
nseq = Normalize(0, 40)
ndiv = TwoSlopeNorm(vmin=np.log2(0.05), vcenter=0.0, vmax=np.log2(2.0))

# ---- geometry in points (y measured from the top) ----
W, PAD = 241.14, 1.0
ROW = 8.8
LBL = 64.0                # left edge of the first cell column (order labels + bracket + dataset names)
GAPG = 5.0                # gap between metric groups
BLOCK_GAP = 6.0
Y_TITLE = PAD + 3.0       # centre line of "Size saved (%)", "Read rate kept (%)"
Y_KEY = PAD + 8.5         # top of the colour key bars (clear of the title descenders)
KEY_H = 4.0
Y_GROUP = PAD + 26.5      # Point / Bulk / Range
HEAD = 30.5               # header height
ncell = len(GROUPS)
cw = (W - PAD - LBL - GAPG * (ncell - 1)) / ncell
nrows = {o: len(t[t.order == o].column.unique()) for o, _ in BLOCKS}
H = PAD + HEAD + ROW * sum(nrows.values()) + BLOCK_GAP + PAD
fig = plt.figure(figsize=(W / 72, H / 72))
fx = lambda x: x / W           # noqa: E731
fy = lambda y: 1 - y / H       # noqa: E731
T = dict(fontsize=8, transform=fig.transFigure)
xcell = [LBL + j * (cw + GAPG) for j in range(ncell)]


def line(x0, y0, x1, y1, color=RULE, lw=0.5):
    fig.add_artist(plt.Line2D([fx(x0), fx(x1)], [fy(y0), fy(y1)], color=color, lw=lw,
                              transform=fig.transFigure))


rows_out = []
y = PAD + HEAD
for bi, (order, bname) in enumerate(BLOCKS):
    y0 = y
    for c in COLS:
        sub = t[(t.column == c) & (t.order == order)]
        if sub.empty:
            continue
        fig.text(fx(LBL - 3), fy(y + ROW / 2), NAMES[c], ha="right", va="center_baseline", **T)
        for g, (col, _) in enumerate(GROUPS):
            v = float(sub[sub.planner == PLANNER][col].iloc[0])
            if g == 0:
                fc = seq(nseq(v))
                s = "0" if v < 0.05 else ("<1" if v < 1 else f"{v:.0f}")
                dark = nseq(v) > 0.55
            else:
                lv = np.log2(max(v, 1e-3))
                fc = div(ndiv(lv))
                s = f"{100 * v:.0f}"
                dark = lv < np.log2(0.3) or lv > np.log2(1.6)
            rows_out.append(dict(order=order, column=c, metric=col, text=s))
            fig.patches.append(plt.Rectangle((fx(xcell[g] + 0.5), fy(y + ROW - 0.4)), fx(cw - 1.0),
                                             (ROW - 0.8) / H, transform=fig.transFigure, facecolor=fc,
                                             edgecolor="none"))
            fig.text(fx(xcell[g] + cw / 2), fy(y + ROW / 2), s, ha="center", va="center_baseline",
                     color="white" if dark else INK, fontsize=7.5, transform=fig.transFigure)
        y += ROW
    fig.text(fx(PAD + 8.5), fy((y0 + y) / 2), bname, rotation=90, ha="center", va="center",
             style="italic", linespacing=1.0, multialignment="center", **{**T, "fontsize": 6.5})
    line(PAD + 18.5, y0 + 1, PAD + 18.5, y - 1, color="#7A7A7A", lw=0.6)
    if bi == 0:
        line(PAD, y + BLOCK_GAP / 2, W - PAD, y + BLOCK_GAP / 2, color="#BDBDBD", lw=0.5)
        y += BLOCK_GAP

for g in range(1, ncell):
    xs = xcell[g] - GAPG / 2
    line(xs, Y_GROUP - 4, xs, H - PAD)

# ---- header: titles, one colour-key row, group labels ----
size_l, size_r = xcell[0], xcell[0] + cw
read_l, read_r = xcell[1], xcell[-1] + cw
fig.text(fx(size_r), fy(Y_TITLE), "Size saved (%)", ha="right", va="center_baseline", **T)
fig.text(fx((read_l + read_r) / 2), fy(Y_TITLE), "Read rate kept (%)", ha="center", va="center_baseline", **T)


def key(x0, x1, cmap, ticks, labels):
    k = fig.add_axes([fx(x0), fy(Y_KEY + KEY_H), fx(x1 - x0), KEY_H / H])
    _e = np.linspace(0, 1, 257)  # vector key: 256 flat strips
    k.pcolormesh(_e, [0, 1], ((_e[:-1] + _e[1:]) / 2)[None, :], cmap=cmap, vmin=0, vmax=1, shading="flat",
        edgecolors="face", linewidth=0.25, rasterized=False)
    k.set_ylim(0, 1)
    k.set_xlim(0, 1)
    k.set_xticks(ticks)
    k.set_xticklabels(labels)
    k.set_yticks([])
    k.tick_params(labelsize=7, length=1.5, width=0.5, pad=0.8, colors=INK)
    for sp in k.spines.values():
        sp.set_linewidth(0.4)


key(size_l + 4, size_r - 4, seq, [0, 0.5, 1], ["0", "20", "40"])
rk = [5, 20, 100, 200]
key(read_l + 6, read_r - 8, div, [float(ndiv(np.log2(v / 100))) for v in rk], [str(v) for v in rk])
for g, (_, lab) in enumerate(GROUPS[1:], start=1):
    fig.text(fx(xcell[g] + cw / 2), fy(Y_GROUP), lab, ha="center", va="center_baseline", **T)

name = "fig12_transform_impact_heatmap_default_only_v5"
for ext, kw in (("pdf", {}), ("png", {"dpi": 400})):
    fig.savefig(os.path.join(OUT, f"{name}.{ext}"), **kw)
pd.DataFrame(rows_out).to_csv(os.path.join(OUT, f"{name}_cells.csv"), index=False)
fig.canvas.draw()
bb = fig.get_tightbbox(fig.canvas.get_renderer())
print(f"wrote {name}: {W:.2f} x {H:.2f} pt, cell width {cw:.1f} pt, content bbox x {bb.x0*72:.1f}-{bb.x1*72:.1f}, y {bb.y0*72:.1f}-{bb.y1*72:.1f} pt")
