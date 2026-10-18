#!/usr/bin/env python3
"""Sec. 4 bit-flip figure (fig:sis_encode_layout), compact re-render 2026-10-06.

Two single-panel PDFs placed side by side as LaTeX subfigures, each at
0.49\\columnwidth (acmart sigconf \\columnwidth = 241.14 pt), rendered at that
exact width so 8 pt text prints at 8 pt. Styled to pair with the Sec. 2 flip
panels (study_20261001/A/fig/panels_20261002/make_panels.py): bit 0 on the
left, Snowflake identity colour, dotted field edges, lowercase "bit" /
"flip p." labels, y from 0.

Data (unchanged, read-only, same selection as
paper-repo/eval_figures/section4_bitflip_20260930b/scripts/make_bitflip_figures.py):
  paper-repo/eval_figures/c3_bitflip_admission/profiles_42col.npz
  column TwitterSnowflake_tweet_id, 1024 sampled adjacent pairs.
Gradient = |diff(profile)|; gate threshold = mean + 2 sigma of the gradient.

Run: python3 make_sec4_bitflip.py   (writes next to this script)
"""
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import artifact_paths as AP  # noqa: E402
import paperstyle  # noqa: E402

paperstyle.apply_rcparams()
plt.rcParams.update({"axes.grid": False})

PROFILES = os.path.join(AP.DATA, "bitflip_profiles", "profiles_42col.npz")
COLUMN = "TwitterSnowflake_tweet_id"
SAMPLE_PAIRS = 1024
GRADIENT_SIGMAS = 2.0

PT = 1 / 72.0
WIDTH = 0.49 * 241.14 * PT        # placed width of each subfigure, inches
HEIGHT = 80 * PT                  # target placed height, inches
MARGIN = 1 * PT                   # ink-to-edge margin

LINE = paperstyle.SECTION2_COLUMN_COLORS["snowflake"]   # Sec. 2 Snowflake colour
SPIKE = paperstyle.ENTITIES["ACCEPT"]["color"]           # gradient bars above threshold
BELOW = paperstyle.ENTITIES["REJECT"]["color"]           # gradient bars below threshold
INK = "#333333"
FIELDS = [("seq", 0, 11, 0.60), ("machine", 12, 21, 0.80), ("timestamp", 22, 62, 0.60)]

store = np.load(PROFILES, allow_pickle=True)
profile = store[COLUMN][list(store["pairs"]).index(SAMPLE_PAIRS)]
gradient = np.abs(np.diff(profile))
threshold = gradient.mean() + GRADIENT_SIGMAS * gradient.std()
edges = [i + 1 for i in np.where(gradient > threshold)[0]]
assert edges == [12, 22], edges
print(f"threshold {threshold:.3f}; spikes at bits {edges}")


def base_axes(ylabel, ymax):
    fig = plt.figure(figsize=(WIDTH, HEIGHT))
    ax = fig.add_axes([0.2, 0.2, 0.75, 0.75])
    ax.set_xlim(-0.5, 63.5)
    ax.set_xticks([0] + edges + [63])
    ax.set_ylim(0, ymax)
    ax.set_yticks([0, 0.5])
    ax.set_yticklabels(["0", "0.5"])
    ax.tick_params(length=2, pad=1.5)
    ax.set_xlabel("bit", labelpad=1)
    ax.set_ylabel(ylabel, labelpad=4)
    ax.grid(axis="y", color="#dddddd", linewidth=0.4)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    for e in edges:
        ax.axvline(e - 0.5, color=LINE, linewidth=0.6, linestyle=":", zorder=1)
    return fig, ax


def fit_and_save(fig, ax, name):
    # Move the axes so the ink sits MARGIN from every edge of the fixed
    # WIDTH x HEIGHT canvas (no bbox_inches crop, so the page size is exact).
    for _ in range(4):
        fig.canvas.draw()
        r = fig.canvas.get_renderer()
        bb = ax.get_tightbbox(r).transformed(fig.dpi_scale_trans.inverted())
        pos = ax.get_position()
        x0 = pos.x0 * WIDTH + (MARGIN - bb.x0)
        x1 = pos.x1 * WIDTH - (bb.x1 - (WIDTH - MARGIN))
        y0 = pos.y0 * HEIGHT + (MARGIN - bb.y0)
        y1 = pos.y1 * HEIGHT - (bb.y1 - (HEIGHT - MARGIN))
        ax.set_position([x0 / WIDTH, y0 / HEIGHT, (x1 - x0) / WIDTH, (y1 - y0) / HEIGHT])
    fig.savefig(os.path.join(AP.OUT, f"{name}.pdf"))
    fig.savefig(os.path.join(AP.OUT, f"{name}.png"), dpi=300)
    plt.close(fig)
    print("wrote", name)


# (a) flip probability, field names in the empty band above p = 0.52.
fig, ax = base_axes("flip p.", 1.0)
ax.plot(range(64), profile, color=LINE, linewidth=1.0, zorder=3)
for name, lo, hi, y in FIELDS:
    # Extent bracket of the field just under its name.
    ax.annotate("", xy=(lo - 0.4, y - 0.02), xytext=(hi + 0.4, y - 0.02),
                arrowprops=dict(arrowstyle="|-|,widthA=0.15,widthB=0.15",
                                color=INK, linewidth=0.5, shrinkA=0, shrinkB=0))
    ax.text((lo + hi) / 2, y, name, ha="center", va="bottom", color=INK, fontsize=8)
fit_and_save(fig, ax, "snowflake_flip_probability")

# (b) |gradient| with the gate threshold.
fig, ax = base_axes("|$\\Delta$ flip p.|", 0.6)
between = np.arange(63) + 0.5
ax.bar(between, gradient, width=0.7, zorder=3,
       color=[SPIKE if g > threshold else BELOW for g in gradient])
ax.axhline(threshold, color=INK, linewidth=0.6, linestyle=(0, (3, 2)), zorder=2)
ax.text(63.5, threshold + 0.02, f"mean + {GRADIENT_SIGMAS:.0f}$\\sigma$",
        ha="right", va="bottom", color=INK, fontsize=8)
fit_and_save(fig, ax, "snowflake_flip_gradient")
