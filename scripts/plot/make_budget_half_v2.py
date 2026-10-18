#!/usr/bin/env python3
"""V2 (2026-10-17, the author): plots only the measured budgets 0, 2, 5, 10, 15 and 25 % (a subset of the rows,
no interpolation, values unchanged) so the budget, sections and size +% rows are all horizontal.

HALF-WIDTH VARIANT (2026-10-17, the author) of make_budget_sweep.py's paper figure (budget_sweep_snowflake_to25):
Snowflake, budgets 0-25 %, y cut at 6x, ~118 pt wide at the same height as fig_blocksize_snowflake_half
(SIS_HALF_H_PT), so the two sit side by side as subfigures. Same data, series, colours, markers, dashed 1x line,
linear y from 0, sections row on top and size row below. Changed for the width only: budget and size labels
are rotated 90 degrees (unrotated they overlap at ~8 pt per budget), the legend is one column inside the
upper left (empty there: values <= 1.7x up to 4 %)."""
import csv, os, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paperstyle
paperstyle.apply_rcparams()
import artifact_paths as AP  # artifact-relative paths
OUT = AP.OUT
DATA = os.path.join(AP.DERIVED, "budget_sweep_values.csv")
_E = paperstyle.ENTITIES
SERIES = [("point", "point", _E["SIS_DEFAULT"]["color"], "o"), ("range64", "range (64 rows)", _E["SIS_HYBRID"]["color"], "s"),
          ("bulk", "bulk", _E["SIS_BEST"]["color"], "^")]
W_PT = float(os.environ.get("SIS_HALF_W_PT", "118.0"))
H_PT = float(os.environ.get("SIS_HALF_H_PT", "100.0"))
YMAX, MAX_BUDGET = 6.0, 25
KEEP = {0.0, 2.0, 5.0, 10.0, 15.0, 25.0}

rows = [r for r in csv.DictReader(open(DATA)) if r["dataset"] == "snowflake" and float(r["budget_pct"]) <= MAX_BUDGET
        and float(r["budget_pct"]) in KEEP]
assert len(rows) == len(KEEP)
xs = list(range(len(rows)))
fig = plt.figure(figsize=(W_PT / 72, H_PT / 72))
left, right, bottom, top = 38.0, 3.0, 21.5, 10.0  # points
ax = fig.add_axes([left / W_PT, bottom / H_PT, (W_PT - left - right) / W_PT, (H_PT - bottom - top) / H_PT])
for key, label, color, marker in SERIES:
    ys = [float(r[key]) for r in rows]
    assert max(ys) <= YMAX
    ax.plot(xs, ys, "-", color=color, lw=1.0, zorder=3)
    ax.plot(xs, ys, ls="none", color=color, marker=marker, ms=3.2, clip_on=False, zorder=4)
    ax.plot([], [], "-", color=color, marker=marker, ms=3.2, lw=1.0, label=label)
ax.axhline(1.0, color="#555555", lw=0.6, ls=(0, (4, 3)), zorder=1)
ax.set_ylim(bottom=0, top=YMAX)
ax.set_xlim(-0.5, len(rows) - 0.5)
ax.set_xticks(xs)
ax.set_xticklabels([f"{float(r['budget_pct']):g}" for r in rows])
ax.tick_params(axis="both", length=2, pad=1.5, width=0.5)
ax.set_ylabel("read rate", labelpad=1.0)
ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=3, integer=True))
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: "0" if v == 0 else f"{v:g}×"))
ax.grid(axis="x", visible=False)
ax.spines[["top", "right"]].set_visible(False)


def size_label(v):
    return f"{v:.0f}" if abs(v) >= 9.95 else ("0" if abs(v) < 0.05 else f"{v:.1f}")


SIZE_Y = -11.5  # points below the axes: top of the rotated size labels
for i, r in enumerate(rows):
    ax.annotate(size_label(float(r["size_prefix_pct"])), (i, 0), xycoords=("data", "axes fraction"), xytext=(0, SIZE_Y),
                textcoords="offset points", ha="center", va="top", fontsize=7, color="#555555")
    ax.annotate(r["read_sections"], (i, 1), xycoords=("data", "axes fraction"), xytext=(0, 1.5),
                textcoords="offset points", ha="center", va="bottom", fontsize=7, color="#555555")
for txt, y, va, col in [("sections", 1.5, "bottom", "#555555"), ("budget %", -3.5, "top", "#333333"),
                        ("size +%", SIZE_Y - 1, "top", "#555555")]:
    ax.annotate(txt, (0, 1 if va == "bottom" else 0), xycoords="axes fraction", xytext=(-3, y),
                textcoords="offset points", ha="right", va=va, fontsize=7, color=col)
ax.legend(loc="upper left", bbox_to_anchor=(0.0, 1.0), ncol=1, handlelength=1.3, handletextpad=0.35,
          labelspacing=0.15, borderaxespad=0.1, borderpad=0.1)
base = os.path.join(OUT, "fig_budget_sweep_half_v2")
fig.savefig(base + ".pdf")
fig.savefig(base + ".png", dpi=300)
fig.canvas.draw()
bb = fig.get_tightbbox(fig.canvas.get_renderer())
print(f"wrote {base}: {W_PT:.2f} x {H_PT:.2f} pt; content x {bb.x0*72:.1f}-{bb.x1*72:.1f}, y {bb.y0*72:.1f}-{bb.y1*72:.1f}")
