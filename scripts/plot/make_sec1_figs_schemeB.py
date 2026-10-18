#!/usr/bin/env python3
"""Figure 1 (Section 1) redesign, 2026-10-01.

Produces all four Section-1 panels used/available in the paper:
  fig0_frontier        (frontier scatter, with SIS)
  fig0_frontier_nosis   (frontier scatter, without SIS)
  fig0_ladder          (cost-vs-range-size ladder, with SIS)
  fig0_ladder_nosis     (cost-vs-range-size ladder, without SIS)

Built from two prior scripts, kept read-only:
  eval_figures/fig1_20260930/scripts/make_fig1_frontier.py       (variant C
    point set + provenance-fixed durable data defaults)
  eval_figures/paper_panels_20260928/scripts/make_motivation_figure_panels.py
    (the only generator that also makes the ladder + nosis variants)

Per the author's 2026-10-01 review of the prior renders:
  1. Heavyweight set is variant C's: OpenZL (whole column) + Zstd/1K +
     OpenZL/1K + OpenZL/64K + Zstd/64 (the one block-sweep point). The
     ladder gets the same identity set added as a Zstd/64 curve alongside
     its existing OpenZL whole-column / OpenZL block=1024 curves.
  2. Ratio axis (frontier) no longer starts at 0 or at a hardcoded 1.0: the
     limit is derived from the smallest plotted ratio (Dictionary, ~0.73
     against the durable pull) minus a small margin, with small headroom on
     top. This is a deliberate, documented exception to the project's
     ax.set_ylim(bottom=0) convention -- see the comment at set_ylim below.
  3. Exactly four points are annotated per frontier plot (plus SIS as a
     fifth, star-marked one, in the SIS variants): most-compressing
     heavyweight, fastest heavyweight, most-compressing lightweight,
     fastest lightweight. No other per-point labels.
  4. x-axis label: "64-element range-read throughput (elements/µs)" on
     the frontier if it fits at the rendered width (it does, checked against
     the render -- see README); the ladder's x-axis is a different quantity
     (range size, not throughput) and is labelled accordingly.
  5. The dashed frontier boundary line is dropped (the shaded region alone,
     plus the four labels, carries the same information without an extra
     line); legend kept compact (group identity only, SIS added in the SIS
     variants).

Data: durable pulls only, pinned by env var, never a temp default:
  SIS_FIG_PULL      -> pulls/pull_524k_rev-sweep-524k_20260924
  SIS_FIG_BLOCK_DIR -> pulls/motivation_524k_v2
Run (from this dir's parent):
  BASE=$PROJECT/
  SIS_FIG_PULL=$BASE/pulls/pull_524k_rev-sweep-524k_20260924 \\
  SIS_FIG_BLOCK_DIR=$BASE/pulls/motivation_524k_v2 \\
  SIS_FIG_OUT=$BASE/paper-repo/eval_figures/fig1_20261001 \\
  python3 make_fig1_all.py
"""

import os
import re
import subprocess

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paperstyle as ps
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# Round 4 (the author, 2026-10-01): tight-cropped PDFs (minimal outlining
# whitespace) that must still land at *exactly* the tex's
# \includegraphics{width=0.9\columnwidth} = 215.784pt. bbox_inches="tight"
# crops a figure to its actual ink extent, which is smaller than the fixed
# canvas the previous rounds rendered at (that canvas had generous margins
# specifically so nothing could clip); so the figure is rendered at a
# *larger* figsize than 2.997in, then cropped, and the figsize is scaled
# iteratively until the cropped PDF's width lands on the target.
TARGET_WIDTH_PT = 217.03
WIDTH_TOL_PT = 0.1


def pdf_width_pt(path):
    out = subprocess.run(["pdfinfo", path], capture_output=True, text=True, check=True).stdout
    m = re.search(r"Page size:\s*([\d.]+) x ([\d.]+)", out)
    return float(m.group(1))


def render_tight(build_fn, base_figsize, out_name, max_iter=8):
    """Calls build_fn(figsize) -> fig repeatedly, each time at a rescaled
    figsize, until the bbox_inches="tight" crop of the saved PDF lands
    within WIDTH_TOL_PT of TARGET_WIDTH_PT. build_fn reruns the *entire*
    plotting routine at each trial figsize (not a post-hoc resize of a
    finished figure), so the collision-avoidance label placement -- which
    reads the actual rendered axes geometry via get_window_extent -- is
    always computed correctly for whatever figsize is being tried, not
    stale from a previous size."""
    w, h = base_figsize
    scale = 1.0
    tmp_path = os.path.join(OUT_DIR, f"_tmp_{out_name}.pdf")
    cur_w = None
    for _ in range(max_iter):
        fig = build_fn((w * scale, h * scale))
        fig.savefig(tmp_path, bbox_inches="tight", pad_inches=0.0)
        plt.close(fig)
        cur_w = pdf_width_pt(tmp_path)
        if abs(cur_w - TARGET_WIDTH_PT) <= WIDTH_TOL_PT:
            break
        scale *= TARGET_WIDTH_PT / cur_w
    fig = build_fn((w * scale, h * scale))
    pdf_path = os.path.join(OUT_DIR, f"{out_name}.pdf")
    png_path = os.path.join(OUT_DIR, f"{out_name}.png")
    fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.0)
    fig.savefig(png_path, bbox_inches="tight", pad_inches=0.0, dpi=150)
    plt.close(fig)
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    final_w = pdf_width_pt(pdf_path)
    print(f"  [{out_name}] tight-crop width = {final_w:.3f}pt "
          f"(target {TARGET_WIDTH_PT}pt), figsize scale = {scale:.4f}")
    return final_w

DATA_DIR = os.environ["SIS_FIG_PULL"]
BLOCK_DIR = os.environ["SIS_FIG_BLOCK_DIR"]
OUT_DIR = os.environ["SIS_FIG_OUT"]

COLUMN = "snowflake"
ORDER = "shipped"
B_PANEL_A = 64

C_SIS = ps.ENTITIES["SIS_DEFAULT"]["color"]
C_OPENZL = ps.ENTITIES["OPENZL"]["color"]
C_BASELINE = ps.ENTITIES["FPE"]["color"]  # lightweight family (blue-grey)
C_GAP = ps.ENTITIES["GAP"]["color"]
SPEED_SCALE = 1000.0

ps.apply_rcparams()
plt.rcParams.update({
    "axes.grid": False,
    "font.size": 9,
    "axes.titlesize": 9,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8.0,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "axes.linewidth": 0.6,
})

WHITEBOX = {
    "FixedBitWidth": ["FixedBitWidth", "FixedBitWidth/view"],
    "PFOR": ["PFOR/view"],
    "SIMD-FOR": ["SimdForBitpack/view"],
    "Dictionary": ["Dictionary", "Dictionary/view"],
    "RLE": ["RLE", "RLE/view"],
}
RAW_ARM = "Trivial"
HEAVYWEIGHT = {"OpenZL": "openzl/auto"}
# Variant C's set (the author, 2026-09-29): the base pull's own block arms plus
# exactly one point from the separate block-sweep run, Zstd/64 -- the
# fastest block arm, closest to SIS on the log-x axis. Zstd/256 and
# OpenZL/256 are deliberately not included (variant B's full sweep).
BLOCKED = {
    "Zstd/64": "zstd/block-64",
    "Zstd/1K": "zstd/block-1024",
    "OpenZL/1K": "openzl/block-1024",
    "OpenZL/64K": "openzl/block-65536",
}
SHORT_NAME = {
    "OpenZL": "OpenZL",
    "Zstd/64": ps.ENTITIES["ZSTD_BLOCK"]["label"],
    "Zstd/1K": "Zstd-1K",
    "OpenZL/1K": ps.ENTITIES["OPENZL_BLOCK"]["label"],
    "OpenZL/64K": "OpenZL-64K",
    "FixedBitWidth": ps.ENTITIES["FBW"]["label"],
    "PFOR": "PFOR",
    "SIMD-FOR": "SIMD-FOR",
    "Dictionary": "Dictionary",
    "RLE": "RLE",
}
SIS_ARM = "SIS/realNested+view"


def read_skip():
    frames = []
    for r in (1, 2, 3):
        path = os.path.join(DATA_DIR, f"fig0_skip_{COLUMN}_{ORDER}_r{r}.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            df["_repeat"] = r
            frames.append(df)
    for r in (1, 2, 3):
        block = os.path.join(BLOCK_DIR, f"n524288_range_hot_{COLUMN}_{ORDER}_r{r}.csv")
        if os.path.exists(block):
            df = pd.read_csv(block)
            df["_repeat"] = r
            frames.append(df)
    if not frames:
        raise SystemExit("no fig0_skip CSVs found for " + COLUMN)
    out = pd.concat(frames, ignore_index=True)
    return out[out.get("skipped", 0) != 1]


def read_comp():
    path = os.path.join(DATA_DIR, f"fig0_comp_{COLUMN}_{ORDER}.csv")
    frames = [pd.read_csv(path)]
    block = os.path.join(BLOCK_DIR, f"n524288_comp_{COLUMN}_{ORDER}.csv")
    if os.path.exists(block):
        frames.append(pd.read_csv(block))
    out = pd.concat(frames, ignore_index=True)
    return out[out.get("skipped", 0) != 1]


def read_bulk():
    frames = []
    for r in (1, 2, 3):
        path = os.path.join(DATA_DIR, f"bulk_{COLUMN}_{ORDER}_r{r}.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            df["_repeat"] = r
            frames.append(df)
    return pd.concat(frames, ignore_index=True)


skip = read_skip()
comp = read_comp()
bulk = read_bulk()
N_ROWS = int(bulk["N"].iloc[0])


def per_elem_stats(arm, b):
    """Returns (median, min, max, q25, q75) ns/element across every sampled
    row range at this B (all three repeats' offsets pooled together). The
    frontier plot's error bars use [1], [2] (min, max); the ladder's shaded
    band uses [3], [4] (IQR) -- see the 2026-10-01 round-3 note at
    make_ladder_figure for why IQR, not min-max, is used there."""
    sub = skip[(skip.encoding == arm) & (skip.B == b)]
    if sub.empty:
        return None
    v = sub["time_ns"].to_numpy(dtype=float) / b
    return (float(np.median(v)), float(v.min()), float(v.max()),
            float(np.percentile(v, 25)), float(np.percentile(v, 75)))


def bits(arm):
    sub = comp[comp.encoding == arm]
    if sub.empty:
        return None
    return float(sub["bits_per_elem"].iloc[0])


# --- Frontier points --------------------------------------------------------
points = []
for label, arms in WHITEBOX.items():
    best = None
    for arm in arms:
        st = per_elem_stats(arm, B_PANEL_A)
        if st is None:
            continue
        if best is None or st[0] < best[1][0]:
            best = (arm, st)
    if best is None:
        continue
    arm, st = best
    sizes = [b for b in (bits(a) for a in arms) if b is not None]
    points.append(dict(label=label, kind="whitebox", arm=arm,
                       ns=st[0], lo=st[1], hi=st[2], bpe=min(sizes)))

for label, arm in HEAVYWEIGHT.items():
    st = per_elem_stats(arm, B_PANEL_A)
    points.append(dict(label=label, kind="heavy", arm=arm,
                       ns=st[0], lo=st[1], hi=st[2], bpe=bits(arm)))

for label, arm in BLOCKED.items():
    st = per_elem_stats(arm, B_PANEL_A)
    if st is None:
        continue
    points.append(dict(label=label, kind="blocked", arm=arm,
                       ns=st[0], lo=st[1], hi=st[2], bpe=bits(arm)))

st = per_elem_stats(SIS_ARM, B_PANEL_A)
sis_point = dict(label="SIS (this paper)", kind="sis", arm=SIS_ARM,
                 ns=st[0], lo=st[1], hi=st[2], bpe=bits(SIS_ARM))
raw_bpe = bits(RAW_ARM)

pts = pd.DataFrame(points)
pts["ratio"] = raw_bpe / pts["bpe"]
pts["speed"] = SPEED_SCALE / pts["ns"]
pts["speed_lo"] = SPEED_SCALE / pts["hi"]
pts["speed_hi"] = SPEED_SCALE / pts["lo"]
# the author, 2026-10-05: drop points that expand rather than compress (ratio
# below 1x; 0.99 keeps FixedBitWidth and RLE, whose headers put them a hair
# under 1.0). They only add whitespace below the gap and say nothing about
# the trade-off the frontier shows.
_dropped = pts[pts["ratio"] < 0.99]
for _, _row in _dropped.iterrows():
    print(f"  dropped from frontier (ratio < 1): {_row.label} ratio={_row.ratio:.4f}")
pts = pts[pts["ratio"] >= 0.99].reset_index(drop=True)

sis_point["ratio"] = raw_bpe / sis_point["bpe"]
sis_point["speed"] = SPEED_SCALE / sis_point["ns"]
sis_point["speed_lo"] = SPEED_SCALE / sis_point["hi"]
sis_point["speed_hi"] = SPEED_SCALE / sis_point["lo"]

BS = sorted(skip["B"].unique())


def decade_floor(x):
    return 10.0 ** np.floor(np.log10(x))


def decade_ceil(x):
    return 10.0 ** np.ceil(np.log10(x))


def log_bounds(values, margin_decades_lo=1, margin_decades_hi=0):
    lo = decade_floor(min(values)) / (10.0 ** margin_decades_lo)
    hi = decade_ceil(max(values)) * (10.0 ** margin_decades_hi)
    return lo, hi


def ratio_bounds(values, headroom=1.08):
    """Lower limit just below the smallest plotted ratio (rounded down to the
    nearest 0.1 so the floor itself reads as a clean tick), upper limit with
    small headroom above the largest. Deliberate exception to the project's
    ax.set_ylim(bottom=0): these axes measure a compression ratio, where
    space below the smallest plotted point (not zero) is the only dead
    space, and a reader comparing points cares about the differences between
    ~0.7-1.8x, not the gap down to 0."""
    lo = np.floor(min(values) * 10.0) / 10.0
    # keep a sliver below the lowest point rather than clipping it to the frame
    if lo >= min(values):
        lo -= 0.1
    hi = max(values) * headroom
    return float(lo), float(hi)


def place_labels(ax, renderer, items, marker_boxes_extra=()):
    """items: list of (text, (x, y), fontsize, color, weight[, prefer]).
    `prefer`, if given, is a list of (dx, dy) offsets (in points) tried
    before the generic candidate list -- used to pin a label to a
    particular side of its marker (e.g. so two nearby labels' leader lines
    don't cross) while still falling back to the generic search if every
    preferred offset collides. Places each by trying candidates
    nearest-first, keeping the first whose box clears every already-placed
    label, every marker, and the axes frame. Ported from
    paper_panels_20260928/scripts/make_motivation_figure_panels.py but
    called only for the small, curated label set each plot now uses."""
    axes_box = ax.get_window_extent(renderer)
    placed = list(marker_boxes_extra)

    def overlaps(box, others):
        return any(not (box[2] < o[0] or box[0] > o[2] or box[3] < o[1] or box[1] > o[3])
                   for o in others)

    CANDIDATES = [(10, 0), (-10, 0), (0, 11), (0, -11), (11, 8), (-11, 8), (11, -11), (-11, -11),
                  (16, 0), (-16, 0), (20, 20), (-20, 20), (20, -20), (-20, -20), (0, 30), (0, -30),
                  (32, 12), (-32, 12), (32, -12), (-32, -12), (0, 44)]

    for item in items:
        text, xy, fontsize, color, weight = item[:5]
        prefer = item[5] if len(item) > 5 else []
        candidates = list(prefer) + [c for c in CANDIDATES if c not in prefer]
        for dx, dy in candidates:
            ha = "center" if dx == 0 else ("left" if dx > 0 else "right")
            va = "center" if dy == 0 else ("bottom" if dy > 0 else "top")
            far = abs(dx) + abs(dy) >= 20
            ann = ax.annotate(text, xy, fontsize=fontsize, xytext=(dx, dy), textcoords="offset points",
                              ha=ha, va=va, color=color, zorder=6, fontweight=weight,
                              arrowprops=(dict(arrowstyle="-", color="0.55", linewidth=0.5, alpha=0.8,
                                               shrinkA=0, shrinkB=1) if far else None))
            ann.update_positions(renderer)
            bb = matplotlib.text.Text.get_window_extent(ann, renderer)
            box = (bb.x0 - 1, bb.y0 - 1, bb.x1 + 1, bb.y1 + 1)
            inside = (box[0] >= axes_box.x0 and box[2] <= axes_box.x1 and
                      box[1] >= axes_box.y0 and box[3] <= axes_box.y1)
            if inside and not overlaps(box, placed):
                placed.append(box)
                break
            ann.remove()
        else:
            ax.annotate(text, xy, fontsize=fontsize, xytext=(0, 11), textcoords="offset points",
                        ha="center", va="bottom", color=color, zorder=6, fontweight=weight)


def pick_four(pts):
    """Returns the four points to annotate: most-compressing heavyweight,
    fastest heavyweight, most-compressing lightweight, fastest lightweight
    (each only if that kind is present)."""
    heavy = pts[pts.kind.isin(["heavy", "blocked"])]
    light = pts[pts.kind == "whitebox"]
    out = []
    if not heavy.empty:
        out.append(("most-compressing heavy", heavy.loc[heavy["ratio"].idxmax()]))
        out.append(("fastest heavy", heavy.loc[heavy["speed"].idxmax()]))
    if not light.empty:
        out.append(("most-compressing light", light.loc[light["ratio"].idxmax()]))
        out.append(("fastest light", light.loc[light["speed"].idxmax()]))
    # de-duplicate (possible if one point is both fastest and most-compressing
    # within its kind)
    seen, uniq = set(), []
    for role, row in out:
        if row["label"] not in seen:
            seen.add(row["label"])
            uniq.append((role, row))
    return uniq


FRONTIER_XLABEL = f"{B_PANEL_A}-element range-read throughput (elements/µs)"
FRONTIER_XLABEL_SHORT = f"{B_PANEL_A}-element range-read throughput"


def make_frontier_figure(include_sis, figsize, ax=None, legend=True, errbars=True, speed_mult=1.0, anchor_step=0.12):
    _g = globals()
    pts = _g["pts"].copy()
    for _c in ("speed", "speed_lo", "speed_hi"):
        pts[_c] = pts[_c] * speed_mult
    sis_point = dict(_g["sis_point"])
    for _c in ("speed", "speed_lo", "speed_hi"):
        sis_point[_c] = sis_point[_c] * speed_mult
    if ax is None:
        fig, axa = plt.subplots(figsize=figsize)
    else:
        axa = ax
        fig = axa.figure

    panel_speed = pts["speed"].tolist()
    panel_ratio = pts["ratio"].tolist()
    if include_sis:
        panel_speed = panel_speed + [sis_point["speed"]]
        panel_ratio = panel_ratio + [sis_point["ratio"]]
    x_lo, x_hi = log_bounds(panel_speed)
    y_lo, y_hi = ratio_bounds(panel_ratio)

    best_white_ratio = pts[pts.kind == "whitebox"]["ratio"].max()
    heavy_family = pts[pts.kind.isin(["heavy", "blocked"])].sort_values("speed", ascending=False)
    running_max, keep = -np.inf, []
    for _, row in heavy_family.iterrows():
        if row["ratio"] > running_max:
            keep.append(row)
            running_max = row["ratio"]
    heavy_frontier = pd.DataFrame(keep).sort_values("speed")
    heavy_log_speed = np.log10(heavy_frontier["speed"].to_numpy())
    heavy_ratio = heavy_frontier["ratio"].to_numpy()
    curve_x = np.logspace(np.log10(x_lo), np.log10(x_hi), 200)
    curve_y = np.interp(np.log10(curve_x), heavy_log_speed, heavy_ratio,
                        left=heavy_ratio[0], right=heavy_ratio[-1])
    boundary_ratio = np.maximum(curve_y, best_white_ratio)
    # Shaded gap region kept; the dashed boundary line itself is dropped
    # (the author, 2026-10-01) -- the four point labels now carry the same
    # information the line used to stand in for, and removing it declutters
    # the plot.
    axa.fill_between(curve_x, boundary_ratio, y_hi, color=C_GAP, alpha=0.6,
                     edgecolor="none", zorder=0)

    for _, row in pts.iterrows():
        if row.kind == "whitebox":
            color, marker, ms = C_BASELINE, "^", 4.5
        else:
            color, marker, ms = C_OPENZL, "s", 5.5
        axa.errorbar(row.speed, row.ratio,
                     xerr=([[row.speed - row.speed_lo], [row.speed_hi - row.speed]] if errbars else None),
                     fmt=marker, color=color, markersize=ms, capsize=1.6,
                     linewidth=0.7, zorder=4)

    if include_sis:
        axa.errorbar(sis_point["speed"], sis_point["ratio"],
                     xerr=([[sis_point["speed"] - sis_point["speed_lo"]],
                            [sis_point["speed_hi"] - sis_point["speed"]]] if errbars else None),
                     fmt="*", color=C_SIS, markersize=11, capsize=1.6, linewidth=0.7,
                     zorder=5)

    axa.set_xscale("log")
    axa.set_xlim(x_lo, x_hi)
    axa.set_ylim(y_lo, y_hi)
    axa.yaxis.set_major_locator(mticker.MultipleLocator(0.5))
    axa.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}×"))
    axa.grid(True, which="major", axis="both", alpha=0.25, linewidth=0.5)
    axa.set_axisbelow(True)
    axa.set_ylabel("Compression ratio", labelpad=1.5)

    # Final layout margins fixed *before* any pixel-space collision
    # detection below: label placement and the error-bar obstacle boxes
    # read back screen coordinates via transData, which only match what
    # actually gets saved once the axes' final position in the figure is
    # set. Calling subplots_adjust after placement (as the first version of
    # this script did) leaves every placement decision computed against a
    # stale, pre-adjustment layout -- harmless when the adjustment is small,
    # but it silently misplaced "FixedBitWidth" on top of the Zstd/1K
    # marker once the top margin changed to make room for the legend
    # (the author, 2026-10-01 review).
    if ax is None:
        fig.subplots_adjust(left=0.195, right=0.96, bottom=0.26, top=0.88)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    # x-axis label: full wording if it fits inside the axes width at this
    # render size, else the shorter form (units given in the caption).
    axa.set_xlabel(FRONTIER_XLABEL, labelpad=1.0)
    fig.canvas.draw()
    axes_box = axa.get_window_extent(renderer)
    label_box = axa.xaxis.label.get_window_extent(renderer)
    if label_box.width > axes_box.width:
        axa.set_xlabel(FRONTIER_XLABEL_SHORT, labelpad=1.0)
        fig.canvas.draw()

    marker_boxes = []
    for sx, sy, sxlo, sxhi in list(zip(pts["speed"], pts["ratio"], pts["speed_lo"], pts["speed_hi"])) + (
            [(sis_point["speed"], sis_point["ratio"], sis_point["speed_lo"], sis_point["speed_hi"])]
            if include_sis else []):
        px, py = axa.transData.transform((sx, sy))
        marker_boxes.append((px - 7, py - 7, px + 7, py + 7))
        # Also block out each point's horizontal error-bar span (a thin
        # strip at marker height) as an obstacle -- otherwise a label can
        # land clear of every *marker* box but still be drawn straight
        # through a wide error-bar whisker, which the first render did.
        pxlo, _ = axa.transData.transform((sxlo, sy))
        pxhi, _ = axa.transData.transform((sxhi, sy))
        if errbars:
            marker_boxes.append((pxlo - 1, py - 3, pxhi + 1, py + 3))

    # Preferred first-try offsets for the two lightweight labels: pinned to
    # opposite sides of their markers (most-compressing light above-left,
    # fastest light below-right) so their leader lines point away from each
    # other instead of crossing near the bottom-right cluster (the author,
    # 2026-10-01 review of the first render).
    # SIMD-FOR (x~179) and FixedBitWidth (x~508) are only ~0.45 decades
    # apart -- on this 7-decade log-x axis that is about 10pt of screen
    # space, roughly one marker width, so any small offset for one sits
    # almost on top of the other regardless of direction; separating them
    # needs a vertical split instead. Below the cluster is not clear space
    # at this panel height: Dictionary sits at the bottom of the y-range
    # and, on a log-x axis, is close enough to this cluster in screen space
    # that any down-left offset collides with it. The only genuinely open
    # area is above the cluster, into the shaded region, so both labels go
    # up-left -- SIMD-FOR further up, FixedBitWidth a shorter distance up,
    # so they stack rather than collide, each with its own leader line back
    # to its marker.
    PREFER = {
        "most-compressing light": [(-10, 26), (-14, 22), (-6, 30)],
        # FixedBitWidth's text is wide (13 characters); on this log-x axis
        # that one text box spans roughly two decades, so *any* height near
        # the lightweight cluster (where Zstd/64, Zstd/1K, Dictionary, and
        # -- in the SIS variant -- the SIS star itself all sit at varying x)
        # ends up overlapping something. The only height with a clear
        # two-decade-wide band on both axis variants is near the very top
        # of the panel, above the SIS star and OpenZL/64K: nothing else is
        # plotted up there to the right of x~1.
        "fastest light": [(-4, 64), (-8, 60), (-2, 68)],
    }
    # the author, 2026-10-05: put the Zstd-64 and both lightweight labels in the
    # empty bottom-left (worse than the heavyweights on both axes), so the
    # gap stays clear and draws the eye. Anchors are data coordinates of
    # each label's right edge; leader lines run back to the markers.
    ANCHOR = {
        "fastest heavy": (0.12 * speed_mult, 1.10),
        "most-compressing light": (0.12 * speed_mult, 1.10 + anchor_step),
        "fastest light": (0.12 * speed_mult, 1.10 + 2 * anchor_step),
    }
    def to_offset(anchor, xy):
        ax_px = axa.transData.transform(anchor)
        pt_px = axa.transData.transform(xy)
        k = 72.0 / axa.figure.dpi
        return [((ax_px[0] - pt_px[0]) * k, (ax_px[1] - pt_px[1]) * k)]
    items = []
    if include_sis:
        items.append(("SIS", (sis_point["speed"], sis_point["ratio"]), 8.0, C_SIS, "bold"))
    for role, row in pick_four(pts):
        color = C_OPENZL if row.kind in ("heavy", "blocked") else "black"
        prefer = (to_offset(ANCHOR[role], (row.speed, row.ratio)) if role in ANCHOR
                  else PREFER.get(role, []))
        items.append((SHORT_NAME[row.label], (row.speed, row.ratio), 8.0, color, "normal",
                      prefer))
    place_labels(axa, renderer, items, marker_boxes_extra=marker_boxes)

    legend_handles = [
        Line2D([], [], color=C_BASELINE, marker="^", linestyle="none", markersize=4.5,
               label="lightweight encodings"),
        Line2D([], [], color=C_OPENZL, marker="s", linestyle="none", markersize=5,
               label="heavyweight codecs"),
        # The shaded region itself, named (the author, round 4, 2026-10-01): a
        # short label ("gap") rather than the full "unreached by
        # heavyweight codecs" description, which does not fit this panel's
        # one-row legend at a readable size -- the full description stays
        # in the caption/body text, same as it already is in the intro
        # prose this figure illustrates.
        Patch(facecolor=C_GAP, alpha=0.6, edgecolor="none", label=ps.ENTITIES["GAP"]["label"]),
    ]
    if include_sis:
        legend_handles.append(
            Line2D([], [], color=C_SIS, marker="*", linestyle="none", markersize=9, label="SIS"))
    # Legend placed above the axes, outside the data area entirely, rather
    # than inside the lower-left corner: at this point density the in-plot
    # legend box collided with the Zstd/64 label (the author, 2026-10-01
    # review). The nosis variant's 3 entries (lightweight / heavyweight /
    # gap) fit one row; the SIS variant's 4th entry pushed a one-row
    # legend's fixed (point-size) text width past the target page width --
    # confirmed by the tight-crop iteration never converging (its width
    # floor was the legend, which does not shrink when figsize does, not
    # the axes) -- so the SIS variant wraps to 2 rows x 2 cols instead
    # (round 4, the author, 2026-10-01).
    ncol = 2
    axa._sec1_handles = legend_handles
    if legend:
      axa.legend(handles=legend_handles, loc="lower center", bbox_to_anchor=(0.40, 1.0),
               frameon=False, ncol=ncol, handletextpad=0.2, columnspacing=0.5,
               borderaxespad=0.1, labelspacing=0.15, fontsize=8.0, markerscale=0.85)

    print(f"  [frontier include_sis={include_sis}] y_lo={y_lo:.2f} y_hi={y_hi:.2f} "
          f"xlabel='{axa.get_xlabel()}'")
    return fig


def make_ladder_figure(include_sis, figsize, ax=None, legend=True, throughput=False):
    if ax is None:
        fig, axb = plt.subplots(figsize=figsize)
    else:
        axb = ax
        fig = axb.figure
    axb._sec1_at64 = []

    series = [
        ("OpenZL", HEAVYWEIGHT["OpenZL"], C_OPENZL, "s", "-", False),
    ]
    if include_sis:
        series.append(("SIS", SIS_ARM, C_SIS, "*", "-", False))
    series.append(("FixedBitWidth", "FixedBitWidth/view", C_BASELINE, "^", "--", False))
    # Variant C's heavyweight identity, extended to the ladder (the author,
    # 2026-10-01): the whole-column OpenZL curve and a Zstd/64-block curve
    # -- the same block arm labelled on the frontier -- so both plots carry
    # the same set. OpenZL/1K-row-blocks (round 3's with/without choice) is
    # dropped here: round 4 (the author, 2026-10-01) picked the "noozl1k"
    # variant as the final one -- see fig1_20261001b/ for the dropped
    # alternative with that curve still in, kept for reference only.
    series.append((ps.ENTITIES["ZSTD_BLOCK"]["label"], "zstd/block-64", C_OPENZL, "v", "-.", True))

    panel_ys = []
    first_ns, last_ns = {}, {}
    legend_handles = []
    for label, arm, color, marker, ls, hollow in series:
        xs, ys, los, his = [], [], [], []
        for b in BS:
            st = per_elem_stats(arm, b)
            if st is None:
                continue
            xs.append(b)
            ys.append(st[0])
            # Shaded band = interquartile range (25th-75th pct) across every
            # sampled row range at this B, not min-max. Round 3 (the author,
            # 2026-10-01): the Zstd/64 band was "enormous" -- diagnosed
            # against the raw motivation_524k_v2 CSVs (see README sec. 11):
            # at B=64, min-max for zstd/block-64 spans ~2 to ~166 ns/elem
            # (a ~67x range) *within a single repeat*, i.e. it is not
            # repeat-to-repeat measurement noise (reruns would not shrink
            # it) -- it is real, offset-dependent spread, because B=64
            # exactly matches zstd/block-64's own block size: whichever
            # 64-row block a given offset lands in, that block's own
            # content determines how cheap Zstd's decode is, and content
            # varies block to block. Min-max shows every outlier block;
            # IQR shows the typical range and is applied identically to
            # every series so the bands stay comparable.
            los.append(st[3])
            his.append(st[4])
        extended_via_bulk = False
        if not xs or xs[-1] != N_ROWS:
            bsub = bulk[bulk.encoding == arm]
            if not bsub.empty:
                per_rep = bsub.groupby("_repeat")["time_ns"].first() / N_ROWS
                xs.append(N_ROWS)
                ys.append(float(per_rep.median()))
                # Only 3 repeats at the bulk (whole-column) endpoint, not 16
                # offsets -- min/max over 3 samples is the only option here,
                # it is not the same "band" as the IQR used elsewhere, and
                # (being one draw of a single, whole-column read) it is not
                # a block-offset effect like the one described above.
                los.append(float(per_rep.min()))
                his.append(float(per_rep.max()))
                extended_via_bulk = True
        if not xs:
            continue
        if throughput:
            ys = [1e9 / y for y in ys]
            los, his = [1e9 / h for h in his], [1e9 / l for l in los]
        first_ns[label] = ys[0]
        if 64 in xs:
            axb._sec1_at64.append((color, marker, ys[xs.index(64)], hollow, arm))
        last_ns[label] = ys[-1]
        panel_ys.extend(los)
        panel_ys.extend(his)
        ms = 4 if marker != "*" else 7
        face = "none" if hollow else color
        if extended_via_bulk:
            axb.plot(xs[:-1], ys[:-1], color=color, marker=marker, linestyle=ls,
                     markersize=ms, linewidth=0.9, markerfacecolor=face)
            axb.plot(xs[-2:], ys[-2:], color=color, linestyle=(0, (2, 1.5)), linewidth=0.9)
            axb.plot(xs[-1:], ys[-1:], color=color, marker=marker, linestyle="none",
                     markersize=ms, markerfacecolor="white",
                     markeredgecolor=color, markeredgewidth=0.9)
        else:
            axb.plot(xs, ys, color=color, marker=marker, linestyle=ls,
                     markersize=ms, linewidth=0.9, markerfacecolor=face)
        axb.fill_between(xs, los, his, color=color, alpha=0.15, linewidth=0)
        legend_handles.append(Line2D([0], [0], color=color, marker=marker, linestyle=ls,
                                     markersize=ms, markerfacecolor=("none" if hollow else color),
                                     label=label))

    # Tight log bounds: a 1-decade low margin wastes most of a 2.15in-tall
    # panel on dead space below the data; a fraction of a decade is enough
    # that the bottom curve/fill never touches the frame. The SIS variant
    # widens both margins (round 5, the author, 2026-10-01) to make room for the
    # OpenZL/SIS ratio brackets at B=1 and B=N -- drawn just inside the
    # frame, to the side of the B=1/B=N marker columns rather than through
    # them, so they need a clear sliver on each side that the nosis variant
    # (no brackets) doesn't.
    margin_lo, margin_hi = (0.34, 0.30) if include_sis else (0.08, 0.03)
    x_lo_b, x_hi_b = log_bounds([min(BS), N_ROWS], margin_decades_lo=margin_lo, margin_decades_hi=margin_hi)
    y_lo_b, y_hi_b = log_bounds(panel_ys, margin_decades_lo=0.1, margin_decades_hi=0.35)

    axb.set_xscale("log")
    axb.set_yscale("log")
    axb.set_xlim(x_lo_b, x_hi_b)
    axb.set_ylim(y_lo_b, y_hi_b)
    # Different quantity from the frontier's x-axis (range size, not a
    # throughput), so it keeps its own, accurate label rather than the
    # frontier's wording. "B" dropped (the author, round 3, 2026-10-01): it is
    # defined in the frontier's own B=64 label but never used again in this
    # axis's own text.
    axb.set_xlabel("Range size (elements, log scale)", labelpad=1.0)
    axb.set_ylabel("ns / element (log scale)", labelpad=1.5)
    axb.yaxis.set_major_locator(mticker.LogLocator(base=10, numticks=6))
    axb.grid(True, which="major", axis="both", alpha=0.25, linewidth=0.5)
    axb.set_axisbelow(True)

    # Five series converge toward the right (B -> N) where every curve
    # approaches its own whole-column bulk cost, so there is no point along
    # any curve that stays clear of its neighbours for a floating direct
    # label; a compact legend (not a per-point label) is what stays legible
    # here, same as the group legend on the frontier.
    axb._sec1_handles = legend_handles
    if legend:
      axb.legend(handles=legend_handles, loc="upper right", frameon=False, ncol=1,
               handletextpad=0.3, columnspacing=0.7, borderaxespad=0.2,
               labelspacing=0.18, fontsize=8.0)

    # The OpenZL/SIS ratio call-outs ("11,198x at B=1", "3.3x at the whole
    # column") were in-plot annotations in the first render; both landed on
    # top of other curves/points in every spot tried (the author, 2026-10-01,
    # round 2: "either move both into clear space ... or drop them and put
    # the numbers in the caption"). Dropped then; round 5 asked for them
    # back as brackets. Round 5's first attempt used *rotated* labels
    # sitting right against each bracket -- the left one's rotated text
    # bled left into the y-tick-label column, and the right bracket itself
    # (drawn in the widened right margin, outside the B=N marker column)
    # landed outside the frame. Round 6 (the author, 2026-10-01) fixes both:
    # horizontal labels only, each placed in open data space well away
    # from its bracket rather than flush against it, with a thin leader
    # line back to the bracket; both brackets moved fully inside the axes.
    if include_sis and "OpenZL" in first_ns and "SIS" in first_ns:
        z1 = first_ns["OpenZL"] / first_ns["SIS"]
        zN = last_ns["OpenZL"] / last_ns["SIS"]
        if throughput:
            z1, zN = 1.0 / z1, 1.0 / zN
        print(f"  [ladder include_sis={include_sis}] OpenZL/SIS ratio: {z1:,.0f}x at B=1, "
              f"{zN:.1f}x at the whole column (B={N_ROWS})")

        bracket_kw = dict(arrowstyle="<->", color="0.25", linewidth=0.8,
                          shrinkA=0, shrinkB=0)
        leader_kw = dict(arrowstyle="-", color="0.45", linewidth=0.5, shrinkA=1, shrinkB=1)

        # --- Left bracket (B=1): kept at the same inside-the-margin x as
        # before (a thin arrow there, with no text attached, doesn't reach
        # the tick labels) -- only the label moves, to x~2.2 (inside
        # 1.5-3), y=1e4, the empty band between the OpenZL curve (still
        # ~3e6 at that x) and the Zstd/SIS/FixedBitWidth cluster (~50-600
        # there). A short leader ties the two together since they no
        # longer touch.
        x_b1 = x_lo_b * (10.0 ** (margin_lo * 0.5))
        axb.annotate("", xy=(x_b1, first_ns["SIS"]), xytext=(x_b1, first_ns["OpenZL"]),
                     arrowprops=bracket_kw)
        mid_b1 = (first_ns["SIS"] * first_ns["OpenZL"]) ** 0.5
        x_label1, y_label1 = 2.2, (1.0e4 if throughput else 1.0e4)
        axb.annotate(f"{z1:,.0f}$\\times$", xy=(x_b1, mid_b1), xytext=(x_label1, y_label1),
                     fontsize=8.0, color="0.15", ha="left", va="center",
                     arrowprops=leader_kw)

        # --- Right bracket (B=N): moved from the right margin (outside
        # the frame) to x=262144, the geometric midpoint between the last
        # two B columns (131072, 524288) -- confirmed clear there: OpenZL
        # and Zstd nearly cross around that x (~29, ~27), both well above
        # the bracket's true endpoint values (OpenZL 15.2, SIS 4.6), so
        # the bracket itself sits in the gap below both lines, above
        # FixedBitWidth. Label placed just left of the bracket, same gap
        # (between the Zstd/OpenZL pair above and SIS below), with a short
        # leader since it sits a few points clear of the arrow rather than
        # flush against it.
        x_bN = (131072.0 * N_ROWS) ** 0.5
        axb.annotate("", xy=(x_bN, last_ns["SIS"]), xytext=(x_bN, last_ns["OpenZL"]),
                     arrowprops=bracket_kw)
        mid_bN = (last_ns["SIS"] * last_ns["OpenZL"]) ** 0.5
        if throughput:
            axb.annotate(f"{zN:.1f}$\\times$", xy=(x_bN, mid_bN), xytext=(1.2e5, 1.5e5),
                         fontsize=8.0, color="0.15", ha="center", va="center",
                         arrowprops=leader_kw)
        else:
            axb.annotate(f"{zN:.1f}$\\times$", xy=(x_bN, mid_bN), xytext=(-16, 0),
                         textcoords="offset points", fontsize=8.0, color="0.15",
                         ha="right", va="center", arrowprops=leader_kw)

    if ax is None:
        fig.subplots_adjust(left=0.185, right=0.97, bottom=0.165, top=0.97)
    print(f"  [ladder include_sis={include_sis}] y_lo={y_lo_b:.3g} y_hi={y_hi_b:.3g}")
    return fig


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    # Final set (the author, round 4, 2026-10-01): 4 PDFs, each tight-cropped to
    # minimal whitespace but rescaled so the crop still lands at exactly
    # TARGET_WIDTH_PT (= 0.9\columnwidth). Ladder uses the "noozl1k" variant
    # (round 3's with/without choice, resolved).
    render_tight(lambda fs: make_frontier_figure(include_sis=True, figsize=fs),
                 (2.997, 1.90), "fig0_frontier")
    render_tight(lambda fs: make_frontier_figure(include_sis=False, figsize=fs),
                 (2.997, 1.90), "fig0_frontier_nosis")
    render_tight(lambda fs: make_ladder_figure(include_sis=True, figsize=fs),
                 (2.997, 1.55), "fig0_ladder")
    render_tight(lambda fs: make_ladder_figure(include_sis=False, figsize=fs),
                 (2.997, 1.55), "fig0_ladder_nosis")

    print(f"\nPoints plotted (B={B_PANEL_A}, {COLUMN}/{ORDER}, N={N_ROWS}):")
    for _, row in pts.iterrows():
        print(f"  {row.label:<12s} ratio={row.ratio:.4f}  speed={row.speed:10.3f} elem/us")
    print(f"  {'SIS':<12s} ratio={sis_point['ratio']:.4f}  speed={sis_point['speed']:10.3f} elem/us")
