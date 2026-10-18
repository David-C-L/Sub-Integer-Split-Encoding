"""Shared helpers for the 2026-10-06 compact Sec. 7 re-render.

fit(fig, w_pt): moves/resizes every axes (absolute inches) so that the tight
bounding box of all artists is exactly w_pt wide with a PAD_PT margin on every
side, and shrinks the figure height to the content. The saved PDF page is then
the placed width, so 8 pt text prints at 8 pt, and is already cropped to ~1 pt.
Only layout is touched; no data passes through here.
"""
import os

import matplotlib.pyplot as plt

COL_PT = 241.14      # sigconf \columnwidth
TEXT_PT = 506.295    # sigconf \textwidth
PAD_PT = 1.0
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import artifact_paths as AP  # noqa: E402
OUT = AP.OUT


def fit(fig, w_pt, pad_pt=PAD_PT, left_in=None, iters=6):
    """left_in: if given, fix the left edge of every axes at this many inches
    (used to align panels that LaTeX stacks vertically); the right edge is fitted."""
    W, pad = w_pt / 72.0, pad_pt / 72.0
    for _ in range(iters):
        fig.canvas.draw()
        bb = fig.get_tightbbox(fig.canvas.get_renderer())
        fw, fh = fig.get_size_inches()
        boxes = [(a, a.get_position()) for a in fig.axes]
        x0s = [p.x0 * fw for _, p in boxes]
        if left_in is None:
            dx = pad - bb.x0                                # shift everything right/left
            grow = (W - pad) - (bb.x1 + dx)                 # widen axes by this
        else:
            dx = left_in - min(x0s)
            grow = (W - pad) - (bb.x1 + dx)
        dy = pad - bb.y0
        newh = bb.height + 2 * pad
        for a, p in boxes:
            x0 = p.x0 * fw + dx
            w = p.width * fw
            # axes that span the same column grow together; scale x positions
            x0n = x0 if left_in is None else x0
            fx = (x0n - (min(x0s) + dx)) / max(1e-9, (max(p2.x1 * fw for _, p2 in boxes) - min(x0s)))
            span = max(p2.x1 * fw for _, p2 in boxes) - min(x0s)
            x0n = min(x0s) + dx + fx * (span + grow)
            wn = w * (span + grow) / span
            y0 = p.y0 * fh + dy
            a.set_position([x0n / W, y0 / newh, wn / W, p.height * fh / newh])
        fig.set_size_inches(W, newh)
    fig.canvas.draw()
    return fig.get_size_inches() * 72


def save(fig, name, out=OUT):
    for ext, kw in (("pdf", {}), ("png", {"dpi": 300})):
        fig.savefig(os.path.join(out, f"{name}.{ext}"), **kw)
    w, h = fig.get_size_inches() * 72
    plt.close(fig)
    print(f"wrote {name}: {w:.2f} x {h:.2f} pt")
