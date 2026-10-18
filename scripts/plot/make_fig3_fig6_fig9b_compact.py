#!/usr/bin/env python3
"""Compact re-render (2026-10-06) of fig3_composition, fig6_point_access and
fig9b_gather_shapes_{a,b,c,d,legend}.

Data loading/selection is copied unchanged from
paper-repo/eval_figures/paper_panels_20260930_review/scripts/make_fig3_fig6_fig9b_panels.py;
only layout changed. Two pulls, as in the paper files they replace:
  fig3 sizes   : SIS_FIG_COMP_PULL  (full length, sweep_full2 merged_shipped; the FULL2 render)
  fig6 / fig9b : SIS_FIG_PULL (+ SIS_FIG_BASELINE_PULL) and SIS_FIG_GATHER_PULL (524K; the PB render)

Outputs (all exactly \\columnwidth or subfigure width wide, cropped to ~1 pt):
  fig3_6_stacked.pdf            fig3 over fig6 in one PDF, shared x tick labels
  fig3_composition_top.pdf      fig3 without x tick labels (top of a LaTeX stack)
  fig6_point_access_bottom.pdf  fig6 with x tick labels (bottom of a LaTeX stack)
  fig3_composition.pdf, fig6_point_access.pdf   standalone fallbacks with tick labels
  fig9b_gather_shapes_{a,b,c,d}.pdf, fig9b_gather_shapes_legend.pdf
"""
import os
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paperstyle
from compact_common import COL_PT, TEXT_PT, fit, save, OUT

import artifact_paths as AP  # artifact-relative paths
P = AP.TL  # 2026-10-17: defaults = TopLevel run (README of figures_sec7_toplevel_20261014_1526)
DATA_DIR = os.environ.get("SIS_FIG_PULL", f"{AP.TL_DERIVED}/pull_524k_toplevel")
COMP_DIR = os.environ.get("SIS_FIG_COMP_PULL", f"{AP.TL_DERIVED}/merged_shipped_toplevel")
BASELINE_POINT_DIR = os.environ.get("SIS_FIG_BASELINE_PULL", f"{P}/simdfor_view")
GATHER_SHAPE_DIR = os.environ.get("SIS_FIG_GATHER_PULL", f"{P}/gather4")

STRUCTURED = ["snowflake", "xmark_prepost_full", "osm_h3_r9_fileorder", "osm_s2_l30_fileorder", "bing_quadkey", "uuidv7_hi"]
UNSTRUCTURED = ["publicbi_npi", "publicbi_id1", "uuidv7_lo"]
ALL_COLUMNS = STRUCTURED + UNSTRUCTURED
GROUP_OF = {c: "structured" for c in STRUCTURED}
GROUP_OF.update({c: "unstructured" for c in UNSTRUCTURED})
SHORT = {c: paperstyle.short_label(c) for c in ALL_COLUMNS}  # 2026-10-17: Sec. 7 short names

SIS_AUTO = "SIS/realNested"
SIS_AUTO_VIEW = "SIS/realNested+view"
OPENZL = "openzl/auto"
SIS_HYBRID = "SIS/hybrid"
SIS_HYBRID_VIEW = "SIS/hybrid+view"
OPENZL_BLOCK_SMALL = "openzl/block-1024"
BASELINE_BASES = ["FixedBitWidth", "Dictionary", "RLE", "PFOR", "SimdForBitpack",
                  "FPE/fpe_elias", "FPE/fpe_noindex", "FPE/fpe_pertier", "FPE/fpe_tagtag"]
C_SIS = paperstyle.ENTITIES["SIS_DEFAULT"]["color"]
C_SIS2 = paperstyle.ENTITIES["SIS_AUTO"]["color"]
C_SIS_HYBRID = paperstyle.ENTITIES["SIS_HYBRID"]["color"]
C_OPENZL = paperstyle.ENTITIES["OPENZL"]["color"]
C_OPENZL_BLOCK = paperstyle.ENTITIES["OPENZL_BLOCK"]["color"]
C_BASELINE = paperstyle.ENTITIES["FBW"]["color"]
# Table 1 configuration names
L_SIS, L_RP = "SIS (default)", "re-priced"

paperstyle.apply_rcparams()
plt.rcParams.update({"axes.grid": False, "axes.linewidth": 0.6})
LEG = dict(frameon=False, fontsize=8, columnspacing=0.8, handletextpad=0.3, handlelength=1.2,
           labelspacing=0.2, borderaxespad=0.15, borderpad=0.1)


def group_separator(ax):
    ax.axvline(len(STRUCTURED) - 0.5, color="black", linewidth=0.8, linestyle=(0, (3, 2)))


def read_repeats(driver, column, order, data_dir=None):
    frames = []
    for r in (1, 2, 3):
        path = os.path.join(data_dir or DATA_DIR, f"{driver}_{column}_{order}_r{r}.csv")
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path)
        df["_repeat"] = r
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else None


def best_baseline_row(df, encoding_col="encoding", metric_col="bits_per_elem", view=False):
    candidates = df[df[encoding_col].apply(lambda e: any(e == b or e == b + "/view" for b in BASELINE_BASES))]
    if candidates.empty:
        return None
    candidates = candidates.copy()
    candidates["_base"] = candidates[encoding_col].str.replace("/view", "", regex=False)
    best_base = candidates.loc[candidates.groupby("_base")[metric_col].transform("min") == candidates[metric_col]]
    best_base = best_base.sort_values(metric_col).iloc[0]
    base_name = best_base["_base"]
    if view:
        viewed = candidates[candidates[encoding_col] == base_name + "/view"]
        if not viewed.empty:
            return viewed.iloc[0]
    return best_base


def load_comp(prefix, d):
    rows = []
    for column in ALL_COLUMNS:
        path = os.path.join(d, f"{prefix}_{column}_shipped.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            df["_column"] = column
            rows.append(df)
    return pd.concat(rows, ignore_index=True)


def bits_of(cdf, enc):
    rows = cdf[cdf.encoding == enc]["bits_per_elem"]
    return rows.iloc[0] if not rows.empty else np.nan


x = np.arange(len(ALL_COLUMNS))

# ---------------------------------------------------------------- fig3 data (full length)
comp3 = load_comp("comp", COMP_DIR)
zl3 = load_comp("compzl", COMP_DIR)
c3 = [comp3[comp3._column == c] for c in ALL_COLUMNS]
z3 = [zl3[zl3._column == c] for c in ALL_COLUMNS]
fig3_series = [
    (L_SIS, [bits_of(d, SIS_AUTO) for d in c3], C_SIS, None),
    (L_SIS + " + OpenZL", [bits_of(d, SIS_AUTO) for d in z3], C_SIS2, "//"),
    (L_RP, [bits_of(d, SIS_HYBRID) for d in c3], C_SIS_HYBRID, "\\\\"),
    (L_RP + " + OpenZL", [bits_of(d, SIS_HYBRID) for d in z3], C_SIS_HYBRID, "xx"),
    ("OpenZL", [bits_of(d, OPENZL) for d in c3], C_OPENZL, ".."),
]
fig3_series = [s for s in fig3_series if not all(np.isnan(v) for v in s[1])]
pd.DataFrame({s[0]: s[1] for s in fig3_series}, index=ALL_COLUMNS).to_csv(os.path.join(OUT, "fig3_composition_values.csv"))

# ---------------------------------------------------------------- fig6 data (524K)
comp6 = load_comp("comp", DATA_DIR)
point_rows = []
for column in ALL_COLUMNS:
    pdf = read_repeats("point", column, "shipped")
    if pdf is None:
        continue
    bpdf = read_repeats("point", column, "shipped", data_dir=BASELINE_POINT_DIR)
    if bpdf is not None:
        pdf = pd.concat([pdf, bpdf], ignore_index=True)
    cdf = comp6[comp6._column == column]
    for label, enc in [(L_SIS, SIS_AUTO_VIEW), (L_RP, SIS_HYBRID_VIEW), ("OpenZL", OPENZL),
                       ("OpenZL-1K", OPENZL_BLOCK_SMALL)]:
        sub = pdf[pdf.encoding == enc]
        if sub.empty:
            continue
        med = sub.groupby("_repeat")["ns_per_probe"].first()
        point_rows.append(dict(column=column, label=label, med=med.median(), lo=med.min(), hi=med.max()))
    best = best_baseline_row(cdf, view=True)
    if best is not None:
        sub = pdf[pdf.encoding == best["encoding"]]
        if not sub.empty:
            med = sub.groupby("_repeat")["ns_per_probe"].first()
            point_rows.append(dict(column=column, label="best baseline", med=med.median(),
                                   lo=med.min(), hi=med.max(), encoding=best["encoding"]))
pointdf = pd.DataFrame(point_rows)
pointdf.to_csv(os.path.join(OUT, "fig6_point_access_values.csv"), index=False)
POINT_STYLE = {L_SIS: (paperstyle.sis_marker("o"), C_SIS), L_RP: ("D", C_SIS_HYBRID), "best baseline": ("^", C_BASELINE),
               "OpenZL": ("s", C_OPENZL), "OpenZL-1K": ("v", C_OPENZL_BLOCK)}

CLIP = 42
AX_H = 58 / 72.0          # axes height of each bar/point panel (inches)
LEFT_IN = 0.40            # common left edge so LaTeX-stacked panels align
# 2026-10-17: the short names are longer than the old tick labels; panels with x tick labels give the extra
# label height back from the axes so every PDF keeps the TopLevel page size (fig6 112.07 pt, fig9b 114.70 pt).
TICK_GROW_PT = 4.84
GATHER_TICK_GROW_PT = 6.84


def draw_fig3(ax, ticks):
    width = 0.8 / len(fig3_series)
    clipped = {}
    for k, (label, values, color, hatch) in enumerate(fig3_series):
        xs = x + (k - (len(fig3_series) - 1) / 2) * width
        plotted = [min(v, CLIP) if not np.isnan(v) else 0 for v in values]
        bars = ax.bar(xs, plotted, width, label=label, color=color, edgecolor="black",
                      linewidth=0.4, hatch=hatch)
        for i, (v, bar) in enumerate(zip(values, bars)):
            if not np.isnan(v) and v > CLIP:
                bar.set_hatch((hatch or "") + "xx")
                clipped.setdefault(i, []).append(v)
    for i, vals in clipped.items():
        lo_v, hi_v = min(vals), max(vals)
        txt = f"all≈{lo_v:.0f}" if round(lo_v) == round(hi_v) else f"{lo_v:.0f}–{hi_v:.0f}"
        ax.text(x[i], CLIP + 0.8, txt, ha="center", va="bottom", fontsize=8, color="#222222")
    ax.set_ylim(0, CLIP + 7)
    ax.set_yticks([0, 20, 40])
    ax.axhline(CLIP, color="#999999", linewidth=0.5, linestyle=(0, (1, 1)))
    ax.set_ylabel("Bits/value", labelpad=2)
    common_x(ax, ticks)
    h, l = ax.get_legend_handles_labels()
    idx = [0, 2, 1, 3, 4]  # column-major fill: [SIS, re-priced] [+ OpenZL, + OpenZL] [OpenZL]
    top_legend(ax, [h[i] for i in idx], [l[i] for i in idx])


def top_legend(ax, h, l):
    """Legend right above the axes, centred on the figure (not the axes) so it cannot
    run past the left page edge."""
    tr = mtransforms.blended_transform_factory(ax.figure.transFigure, ax.transAxes)
    ax.legend(h, l, loc="lower center", bbox_to_anchor=(0.5, 1.0), bbox_transform=tr, ncol=3, **LEG)


def draw_fig6(ax, ticks):
    for i in range(0, len(ALL_COLUMNS), 2):
        ax.axvspan(i - 0.5, i + 0.5, color="#f4f4f4", zorder=0, linewidth=0)
    order = [l for l in [L_SIS, L_RP, "best baseline", "OpenZL", "OpenZL-1K"] if (pointdf.label == l).any()]
    for k, lbl in enumerate(order):
        sub = pointdf[pointdf.label == lbl]
        xs = [ALL_COLUMNS.index(c) + (k - (len(order) - 1) / 2) * 0.15 for c in sub.column]
        ax.errorbar(xs, sub.med, yerr=[sub.med - sub.lo, sub.hi - sub.med], fmt=POINT_STYLE[lbl][0],
                    color=POINT_STYLE[lbl][1], markersize=paperstyle.sis_ms(4.0) if lbl == L_SIS else 4.0, capsize=2,
                    linewidth=0.9, label=lbl, zorder=4 if lbl == L_SIS else 3)
    ax.set_yscale("log")
    lo, hi = pointdf.lo.min(), pointdf.hi.max()
    ax.set_ylim(lo / 1.8, hi * 2.2)   # log axis: trim empty headroom (no zero baseline on log)
    ax.set_yticks([1e2, 1e4, 1e6])
    ax.minorticks_off()
    ax.set_ylabel("Latency (ns)", labelpad=2)
    ax.grid(True, which="major", axis="y", alpha=0.3, zorder=0)
    common_x(ax, ticks)
    top_legend(ax, *ax.get_legend_handles_labels())


def common_x(ax, ticks):
    ax.set_xlim(-0.6, len(ALL_COLUMNS) - 0.4)
    ax.set_xticks(range(len(ALL_COLUMNS)))
    if ticks:
        ax.set_xticklabels([SHORT[c] for c in ALL_COLUMNS], rotation=45, ha="right",
                           rotation_mode="anchor")
    else:
        ax.set_xticklabels([])
    ax.tick_params(axis="x", length=2, pad=2)
    ax.tick_params(axis="y", length=2, pad=1.5)
    group_separator(ax)


def single(drawer, ticks, name):
    fig = plt.figure(figsize=(COL_PT / 72, 2.0))
    ax = fig.add_axes([LEFT_IN / (COL_PT / 72), 0.3, 0.8, (AX_H - (TICK_GROW_PT / 72 if ticks else 0)) / 2.0])
    drawer(ax, ticks)
    fit(fig, COL_PT, left_in=LEFT_IN)
    save(fig, name)


single(draw_fig3, False, "fig3_composition_top")
single(draw_fig6, True, "fig6_point_access_bottom")
single(draw_fig3, True, "fig3_composition")
single(draw_fig6, True, "fig6_point_access")

# stacked: fig6 axes at the bottom, its legend between the panels, fig3 on top
fig = plt.figure(figsize=(COL_PT / 72, 4.0))
W = COL_PT / 72
axb = fig.add_axes([LEFT_IN / W, 0.15, 0.8, (AX_H - TICK_GROW_PT / 72) / 4.0])
draw_fig6(axb, True)
fig.canvas.draw()
leg_h = axb.get_legend().get_window_extent().height / fig.dpi
top_y0 = axb.get_position().y1 * 4.0 + leg_h + 6 / 72
axt = fig.add_axes([LEFT_IN / W, top_y0 / 4.0, 0.8, AX_H / 4.0])
draw_fig3(axt, False)
fit(fig, COL_PT, left_in=LEFT_IN)
save(fig, "fig3_6_stacked")

# ---------------------------------------------------------------- fig9b (524K)
SIS_HYBRID_AUTO_VIEW = "SIS/hybrid_auto+view"
GATHER_SHAPES = [("short runs, sparse picks", 0.01, [2, 8]), ("long runs, sparse picks", 0.01, [1024]),
                 ("short runs, dense picks", 0.33, [2, 8]), ("long runs, dense picks", 0.33, [1024, 12417])]
SHAPE_SERIES = [(SIS_AUTO_VIEW, C_SIS, paperstyle.sis_marker("o"), L_SIS), (SIS_HYBRID_VIEW, C_SIS_HYBRID, "D", L_RP),
                (SIS_HYBRID_AUTO_VIEW, C_SIS2, "^", "re-priced + transforms"),
                (OPENZL, C_OPENZL, "s", "OpenZL"), (OPENZL_BLOCK_SMALL, C_OPENZL_BLOCK, "v", "OpenZL-1K"),
                ("FixedBitWidth/view", C_BASELINE, "x", "FixedBitWidth")]
shape_frames = {}
for column in ALL_COLUMNS:
    frames = []
    for r in (1, 2, 3):
        path = os.path.join(GATHER_SHAPE_DIR, f"gather_hot_{column}_shipped_r{r}.csv")
        if os.path.exists(path):
            d = pd.read_csv(path)
            d["_repeat"] = r
            frames.append(d)
    if frames:
        shape_frames[column] = pd.concat(frames, ignore_index=True)

PANEL_W = {"a": 0.245 * TEXT_PT, "b": 0.23 * TEXT_PT, "c": 0.23 * TEXT_PT, "d": 0.23 * TEXT_PT}
PANEL_AX_H = (75 - GATHER_TICK_GROW_PT) / 72.0
shape_rows, handles = [], None
for panel, (shape, selectivity, run_lengths) in enumerate(GATHER_SHAPES):
    letter = "abcd"[panel]
    fig = plt.figure(figsize=(PANEL_W[letter] / 72, 2.0))
    ax = fig.add_axes([0.3, 0.4, 0.6, PANEL_AX_H / 2.0])
    lo_all, hi_all = [], []
    for k, (enc, color, marker, label) in enumerate(SHAPE_SERIES):
        xs, med, lo, hi = [], [], [], []
        for column in ALL_COLUMNS:
            gdf = shape_frames.get(column)
            if gdf is None:
                continue
            sub = gdf[(gdf.encoding == enc) & (gdf.selectivity == selectivity)
                      & (gdf.run_length.isin(run_lengths)) & (gdf.range_count >= 2)]
            if sub.empty:
                continue
            per_cell = sub.groupby(["run_length", "_repeat"])["gather_Meps"].first()
            cells = per_cell.groupby("run_length").median()
            xs.append(ALL_COLUMNS.index(column) + (k - (len(SHAPE_SERIES) - 1) / 2) * 0.16)
            med.append(cells.median())
            lo.append(per_cell.groupby("run_length").min().min())
            hi.append(per_cell.groupby("run_length").max().max())
            shape_rows.append(dict(shape=shape, selectivity=selectivity,
                                   run_lengths="|".join(str(r) for r in run_lengths), column=column,
                                   encoding=enc, median_Meps=cells.median(), min_Meps=per_cell.min(),
                                   max_Meps=per_cell.max(), ranges=int(sub["range_count"].median())))
        if not xs:
            continue
        lo_all += lo
        hi_all += hi
        ax.errorbar(xs, med, yerr=[np.array(med) - np.array(lo), np.array(hi) - np.array(med)], fmt=marker,
                    color=color, markersize=paperstyle.sis_ms(3.2) if enc == SIS_AUTO_VIEW else 3.2, capsize=1.5,
                    linewidth=0.8, markeredgewidth=0.8, label=label, zorder=4 if enc == SIS_AUTO_VIEW else 2)
    ax.set_yscale("log")
    ax.set_ylim(min(lo_all) / 1.35, max(hi_all) * 1.35)   # trim empty log headroom
    ax.grid(True, which="major", axis="y", alpha=0.3, linewidth=0.4)
    ax.set_xticks(range(len(ALL_COLUMNS)))
    ax.set_xticklabels([SHORT[c] for c in ALL_COLUMNS], rotation=90, ha="center")
    ax.tick_params(axis="y", pad=1, length=2)
    ax.tick_params(axis="x", pad=1.5, length=2)
    ax.set_xlim(-0.5, len(ALL_COLUMNS) - 0.5)
    group_separator(ax)
    if panel == 0:
        ax.set_ylabel("Gather (Meps)", labelpad=1)
        handles = ax.get_legend_handles_labels()
    fit(fig, PANEL_W[letter])
    save(fig, f"fig9b_gather_shapes_{letter}")

# legend strip at full \textwidth (one row; Table 1 names are too long for 0.7\textwidth at 8 pt)
fig = plt.figure(figsize=(TEXT_PT / 72, 0.3))
fig.legend(*handles, loc="center", ncol=6, frameon=False, fontsize=8, columnspacing=1.2,
           handletextpad=0.3, handlelength=1.3, borderaxespad=0.0, borderpad=0.0, markerscale=0.85)
fig.canvas.draw()
bb = fig.get_tightbbox(fig.canvas.get_renderer())
fig.set_size_inches(TEXT_PT / 72, bb.height + 2 / 72)
save(fig, "fig9b_gather_shapes_legend")
pd.DataFrame(shape_rows).to_csv(os.path.join(OUT, "fig9b_gather_shapes.csv"), index=False)
print("Done.")
