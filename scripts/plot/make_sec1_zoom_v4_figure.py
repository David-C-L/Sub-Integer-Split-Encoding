"""Sec. 1 zoom figure v4 (the author, 2026-10-16): v3 with legend "Zstd" and a
compacted layout (shorter panels, tight log/ratio ranges, fewer ticks, smaller
gaps). v3 notes follow.

v3 v3 = v2 plus: the frontier
line restored (boundary of the original gap shading, same points), and the
label set reduced to the original figure's (OpenZL, Zstd-64, FixedBitWidth;
SIMD-FOR dropped). v2 notes follow.

v2: original layout of
make_sec1_zoom_figure.py (ladder on top, frontier below, zoom connectors),
with only these changes:
  1. no gray gap shading, no "gap" legend entry;
  2. the zoom is one vertical line at range length 64 (not a band), with the
     connectors running from that line down to the frontier's top corners;
  3. frontier: every point kept, each labelled next to its point (no leader
     lines); SIMD-FOR is the only unlabelled point;
  4. axis labels carry the old subcaptions; subcaptions removed;
  5. one legend for the whole figure; Zstd gets its own palette-B colour.
No SIS. Data unchanged (make_sec1_figs_schemeB data, same pull).
"""
import os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import artifact_paths as AP  # noqa: E402
OUT = AP.OUT
os.makedirs(OUT, exist_ok=True)
os.environ["SIS_FIG_OUT"] = OUT
os.environ.setdefault("SIS_FIG_PULL", f"{AP.DATA}/sec1_motivation/pull_524k")
os.environ.setdefault("SIS_FIG_BLOCK_DIR", f"{AP.DATA}/sec1_motivation/motivation_524k_v2")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_sec1_figs_schemeB as m
import paperstyle as ps
import numpy as np
import pandas as pd
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
from matplotlib.patches import ConnectionPatch
plt = m.plt

plt.rcParams.update({k: 8.0 for k in ("font.size", "axes.titlesize", "axes.labelsize",
                                       "xtick.labelsize", "ytick.labelsize", "legend.fontsize")})

TARGET = 217.03          # 0.9 \columnwidth, same as the original
SLICE = m.B_PANEL_A      # 64
GREY = "0.55"
FAM = {  # palette B (paperstyle.ENTITIES)
    "openzl": dict(color=ps.ENTITIES["OPENZL"]["color"], marker="s", ms=4.0),
    "zstd":   dict(color=ps.ENTITIES["ZSTD"]["color"], marker="v", ms=4.5),
    "light":  dict(color=m.C_BASELINE, marker="^", ms=4.5),
}
# ladder series: (legend label, family, arm, linestyle) -- as in the original
LADDER = [("OpenZL", "openzl", "openzl/auto", "-"),
          ("Zstd", "zstd", "zstd/block-64", "-."),
          ("FixedBitWidth", "light", "FixedBitWidth/view", "--")]
# frontier labels: offset (pt), ha, va. SIMD-FOR deliberately unlabelled.
LABELS = {  # original figure's label set minus SIMD-FOR
    "OpenZL":        ((0, -4.0), "center", "top"),
    "Zstd/64":       ((-4.0, -2.0), "right", "center"),
    "FixedBitWidth": ((3.0, -6.0), "right", "top"),
}
Y_FLOOR = 0.76
FR_XLABELS = ["Throughput at Range Length 64 (elements/s)",
              "Throughput, Range Length 64 (elements/s)",
              "Throughput (elements/s)"]


def family(row):
    if row.kind == "whitebox":
        return "light"
    return "zstd" if row.arm.startswith("zstd") else "openzl"


def ladder(ax):
    ys_all, at64, handles = [], [], []
    for label, fam, arm, ls in LADDER:
        f = FAM[fam]
        xs, ys, lo, hi = [], [], [], []
        for b in m.BS:
            st = m.per_elem_stats(arm, b)
            if st is None:
                continue
            xs.append(b); ys.append(1e9 / st[0]); lo.append(1e9 / st[4]); hi.append(1e9 / st[3])
        assert xs[-1] == m.N_ROWS, arm
        at64.append((arm, f, ys[xs.index(SLICE)]))
        ys_all += lo + hi
        ax.fill_between(xs, lo, hi, color=f["color"], alpha=0.15, linewidth=0)
        ax.plot(xs, ys, color=f["color"], marker=f["marker"], markersize=f["ms"],
                linestyle=ls, linewidth=0.9, zorder=3)
        handles.append(Line2D([], [], color=f["color"], marker=f["marker"], markersize=f["ms"],
                              linestyle=ls, linewidth=0.9, label=label))
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(*m.log_bounds([min(m.BS), m.N_ROWS], 0.08, 0.03))
    ax.set_ylim(min(ys_all) / 10 ** 0.25, max(ys_all) * 10 ** 0.25)   # tight to the data
    ax.yaxis.set_major_locator(mticker.FixedLocator([1e3, 1e6, 1e9]))
    ax.yaxis.set_minor_locator(mticker.NullLocator())
    ax.axvline(SLICE, color=GREY, linewidth=0.7, zorder=0.6)
    for arm, f, y in at64:   # ring markers at the slice, as in the original
        ax.plot([SLICE], [y], marker=f["marker"], markersize=7, markerfacecolor="none",
                markeredgecolor="0.15", markeredgewidth=0.6, linestyle="none", zorder=6)
    return at64, handles


def frontier(ax):
    p = m.pts.copy()
    for c in ("speed",):
        p[c] = p[c] * 1e6                  # elements/us -> elements/s
    for _, r in p.iterrows():
        f = FAM[family(r)]
        ax.plot(r.speed, r.ratio, linestyle="none", color=f["color"], marker=f["marker"],
                markersize=f["ms"] + 1.0, zorder=4)
    # frontier line: the lower edge of the original gap shading, computed exactly
    # as make_frontier_figure does (heavyweight Pareto points, floored at the
    # best lightweight ratio, flat beyond the end points).
    x_lo, x_hi = m.log_bounds(p["speed"].tolist())
    best_white = p[p.kind == "whitebox"]["ratio"].max()
    heavy = p[p.kind.isin(["heavy", "blocked"])].sort_values("speed", ascending=False)
    run, keep = -np.inf, []
    for _, r in heavy.iterrows():
        if r["ratio"] > run:
            keep.append(r); run = r["ratio"]
    hf = pd.DataFrame(keep).sort_values("speed")
    cx = np.logspace(np.log10(x_lo), np.log10(x_hi), 200)
    cy = np.interp(np.log10(cx), np.log10(hf["speed"].to_numpy()), hf["ratio"].to_numpy(),
                   left=hf["ratio"].iloc[0], right=hf["ratio"].iloc[-1])
    ax.plot(cx, np.maximum(cy, best_white), color=GREY, linewidth=0.8,
            linestyle=(0, (4, 2)), zorder=1)
    print("  frontier line through:", ", ".join(hf["label"]), f"| floor {best_white:.3f}")
    texts = []
    for _, r in p.iterrows():
        if r.label not in LABELS:
            continue
        off, ha, va = LABELS[r.label]
        texts.append(ax.annotate(m.SHORT_NAME[r.label], xy=(r.speed, r.ratio), xytext=off,
                                 textcoords="offset points", ha=ha, va=va,
                                 color=FAM[family(r)]["color"], zorder=5))
    ax.set_xscale("log")
    ax.set_xlim(*m.log_bounds(p["speed"].tolist()))
    # documented ratio exception, as before; floor 0.05 lower than ratio_bounds
    # (0.90 -> 0.85) so the FixedBitWidth label fits under its point
    y_lo, y_hi = m.ratio_bounds(p["ratio"].tolist())
    ax.set_ylim(Y_FLOOR, max(p["ratio"]) * 1.045)   # tight around points and labels
    ax.yaxis.set_major_locator(mticker.MultipleLocator(0.5))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}×"))
    return {r.arm: r.speed for r in p.itertuples()}, texts, p


def check_overlaps(fig, ax, texts, p):
    fig.canvas.draw()
    rd = fig.canvas.get_renderer()
    boxes = [t.get_window_extent(rd) for t in texts]
    names = [t.get_text() for t in texts]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if boxes[i].overlaps(boxes[j]):
                print(f"  WARN label overlap: {names[i]} / {names[j]}")
    axb = ax.get_window_extent(rd)
    for b, n in zip(boxes, names):
        if b.x0 < axb.x0 or b.x1 > axb.x1 or b.y0 < axb.y0 or b.y1 > axb.y1:
            print(f"  WARN label outside axes: {n}")
        for r in p.itertuples():
            px, py = ax.transData.transform((r.speed, r.ratio))
            if b.x0 + 1 < px < b.x1 - 1 and b.y0 + 1 < py < b.y1 - 1:
                print(f"  WARN label {n} covers point {r.label}")


def build(W):
    H_leg, H_lad, H_gap, H_fr, bot = 0.15, 1.05, 0.36, 0.90, 0.34
    Ht = H_leg + H_lad + H_gap + H_fr + bot
    fig = plt.figure(figsize=(W, Ht))
    L, R = 0.60 / W, 0.99
    ax_fr = fig.add_axes([L, bot / Ht, R - L, H_fr / Ht])
    ax_lad = fig.add_axes([L, (bot + H_fr + H_gap) / Ht, R - L, H_lad / Ht])
    at64, handles = ladder(ax_lad)
    ref, texts, p = frontier(ax_fr)
    for arm, _, y in at64:
        assert abs(y / ref[arm] - 1) < 1e-9, (arm, y, ref[arm])
    for ax in (ax_lad, ax_fr):
        ax.grid(True, which="major", alpha=0.25, linewidth=0.5)
        ax.set_axisbelow(True)
    ax_lad.set_ylabel("Throughput (elements/s)", labelpad=1.5)
    ax_lad.set_xlabel("Range Length (elements)", labelpad=1.0)
    ax_fr.set_ylabel("Compression Ratio", labelpad=1.5)
    fig.canvas.draw()
    rd = fig.canvas.get_renderer()
    # full label may overhang the short axis a little (checked: clears the frontier label)
    if ax_lad.yaxis.label.get_window_extent(rd).height > 1.10 * ax_lad.get_window_extent(rd).height:
        ax_lad.set_ylabel("Throughput (elems/s)", labelpad=1.5)
    for xl in FR_XLABELS:
        ax_fr.set_xlabel(xl, labelpad=1.0)
        fig.canvas.draw()
        if ax_fr.xaxis.label.get_window_extent(rd).width <= ax_fr.get_window_extent(rd).width:
            break

    # zoom: connectors from the 64 line (ladder bottom) to the frontier's top corners
    tr = ax_lad.get_xaxis_transform()
    for xb in (0.0, 1.0):
        fig.add_artist(ConnectionPatch(xyA=(SLICE, 0.0), coordsA=tr, xyB=(xb, 1.0),
                                       coordsB=ax_fr.transAxes, color=GREY, linewidth=0.6,
                                       zorder=0.2))
    ax_lad.xaxis.label.set_bbox(dict(facecolor="white", edgecolor="none", pad=0.6))
    ax_lad.xaxis.label.set_zorder(5)
    for t in ax_lad.get_xticklabels():
        t.set_bbox(dict(facecolor="white", edgecolor="none", pad=0.3))

    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5 * (L + R), 1 - H_leg / Ht),
               ncol=3, frameon=False, handlelength=2.0, handletextpad=0.3, columnspacing=0.9,
               borderaxespad=0.0, borderpad=0.0)
    check_overlaps(fig, ax_fr, texts, p)
    return fig


def size_pt(path):
    o = subprocess.run(["pdfinfo", path], capture_output=True, text=True, check=True).stdout
    mm = re.search(r"Page size:\s*([\d.]+) x ([\d.]+)", o)
    return float(mm.group(1)), float(mm.group(2))


def render(name="fig0_v4"):
    W = TARGET / 72.0
    tmp = os.path.join(OUT, f"_tmp_{name}.pdf")
    for _ in range(8):
        fig = build(W)
        fig.savefig(tmp, bbox_inches="tight", pad_inches=0.0)
        plt.close(fig)
        w, _ = size_pt(tmp)
        if abs(w - TARGET) <= 0.1:
            break
        W += (TARGET - w) / 72.0
    os.remove(tmp)
    fig = build(W)
    print("  ladder ylabel:", fig.axes[1].get_ylabel(), "| frontier xlabel:", fig.axes[0].get_xlabel())
    fig.savefig(os.path.join(OUT, name + ".pdf"), bbox_inches="tight", pad_inches=0.0)
    fig.savefig(os.path.join(OUT, name + ".png"), bbox_inches="tight", pad_inches=0.0, dpi=200)
    plt.close(fig)
    print(name, size_pt(os.path.join(OUT, name + ".pdf")), "canvas W", round(W, 3))


render()
