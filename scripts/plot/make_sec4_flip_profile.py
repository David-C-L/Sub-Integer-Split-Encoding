#!/usr/bin/env python3
"""Sec. 4 snowflake_flip_profile.pdf: probability | |gradient| side by side, full column
(241.14 x 70 pt), Snowflake field shading. Bit axis has the MSB (bit 63) on the LEFT in both
panels, matching Fig. 3. Derived from paper_handover/figures_sec4_gradient_20261014/
make_gradient_options.py (B1 + fields). Data: data/bitflip_profiles/profiles_42col.npz,
key TwitterSnowflake_tweet_id, 1024 pairs. Floor = TopLevelPolicyConfig::minGradientMagnitude.
Run: python3 make_sec4_flip_profile.py   (writes snowflake_flip_profile.pdf to $SIS_FIG_OUT)"""
import os, sys
import matplotlib
import numpy as np
matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import artifact_paths as AP  # noqa: E402
import paperstyle
paperstyle.apply_rcparams()
plt.rcParams.update({"axes.grid": False})
store = np.load(f"{AP.DATA}/bitflip_profiles/profiles_42col.npz", allow_pickle=True)
profile = store["TwitterSnowflake_tweet_id"][list(store["pairs"]).index(1024)]
gradient = np.abs(np.diff(profile))
thr = gradient.mean() + 2 * gradient.std()
FLOOR = 0.005
edges = [i + 1 for i in np.where(gradient > thr)[0]]
assert edges == [12, 22]
PT = 1 / 72.0
LINE = paperstyle.SECTION2_COLUMN_COLORS["snowflake"]
SPIKE = paperstyle.ENTITIES["ACCEPT"]["color"]; BELOW = paperstyle.ENTITIES["REJECT"]["color"]
INK = "#333333"; FLOORC = "#CC3311"
FS = 8; MACH_FS = 7
FIELDS = [(-0.5, 11.5, "seq.", "#DDCC77"), (11.5, 21.5, "ID", "#88CCEE"), (21.5, 63.5, "timestamp", "#E2B6AE")]

def decorate(ax, ylabel, ymax, yt=(0, 0.5)):
    ax.set_xlim(63.5, -0.5); ax.set_ylim(0, ymax); ax.set_ylim(bottom=0)  # MSB left
    ax.set_xticks([63] + edges[::-1] + [0]); ax.set_yticks(list(yt))
    ax.set_yticklabels([("0" if t == 0 else f"{t:g}") for t in yt])
    ax.tick_params(length=2, pad=1.5)
    ax.set_xlabel("bit", labelpad=1); ax.set_ylabel(ylabel, labelpad=3)
    ax.spines[["top", "right"]].set_visible(False)
    for e in edges: ax.axvline(e - 0.5, color=LINE, linewidth=0.6, linestyle=":", zorder=1)

def shade(ax, labels=False):
    for x0, x1, t, c in FIELDS:
        ax.axvspan(x0, x1, facecolor=c, alpha=0.3, linewidth=0, zorder=0)
        if labels: ax.text((x0 + x1) / 2, 0.97, t, ha="center", va="top", fontsize=MACH_FS, color=INK, zorder=6)

def save(fig, ax_list, name, W, H, m=1):
    fig.set_size_inches(W * PT, H * PT)
    for _ in range(5):
        fig.canvas.draw(); r = fig.canvas.get_renderer()
        bbs = [a.get_tightbbox(r).transformed(fig.dpi_scale_trans.inverted()) for a in ax_list]
        x0 = min(b.x0 for b in bbs); x1 = max(b.x1 for b in bbs); y0 = min(b.y0 for b in bbs); y1 = max(b.y1 for b in bbs)
        w, h = W * PT, H * PT
        sx = (w - 2 * m * PT) / (x1 - x0); sy = (h - 2 * m * PT) / (y1 - y0)
        for a in ax_list:
            p = a.get_position()
            nx0 = (m * PT + (p.x0 * w - x0) * sx) / w; nx1 = (m * PT + (p.x1 * w - x0) * sx) / w
            ny0 = (m * PT + (p.y0 * h - y0) * sy) / h; ny1 = (m * PT + (p.y1 * h - y0) * sy) / h
            a.set_position([nx0, ny0, nx1 - nx0, ny1 - ny0])
    fig.savefig(f"{AP.OUT}/{name}.pdf"); plt.close(fig)

fig = plt.figure(figsize=(241.14 * PT, 70 * PT))
a1 = fig.add_axes([.08, .25, .39, .7]); a2 = fig.add_axes([.62, .25, .36, .7])
a1.plot(range(64), profile, color=LINE, linewidth=1.0, zorder=3)
decorate(a1, "flip p.", 1.0)
a2.bar(np.arange(63) + 0.5, gradient, width=0.7, zorder=3, color=[SPIKE if g > thr else BELOW for g in gradient])
a2.axhline(thr, color=INK, linewidth=0.6, linestyle=(0, (3, 2)), zorder=2)
a2.axhline(FLOOR, color=FLOORC, linewidth=0.8, linestyle="-.", zorder=4)
decorate(a2, "$\\Delta$ flip p.", 0.6)  # shortened from |Delta flip p.| to avoid colliding with the left panel
# labels anchored at the bit-63 edge (left side), clear of the spike bars at bits 22 and 12
a2.text(63.5, thr + 0.02, "mean+2$\\sigma$", ha="left", va="bottom", color=INK, fontsize=FS)
a2.text(63.5, FLOOR + 0.07, "floor", ha="left", va="bottom", color=FLOORC, fontsize=FS)
shade(a1, labels=True); shade(a2)
save(fig, [a1, a2], "snowflake_flip_profile", 241.14, 70)
print("ok")
