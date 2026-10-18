#!/usr/bin/env python3
"""Cross-format absolute bits per value, variants A (3 panels) and B (6 SFV columns), 2026-10-17.
Without SIS = light grey, with SIS = tol_hc SIS blue, separate adjacent bars.

Same numbers as make_tables_toplevel.py (tab:eval_crossformat), before dividing:
  Nimble: TopLevel $RUN/xf/nimble_raw/auto_{c}_r1_comp.csv (Auto/view) = without, auto_sis_... = with.
  BtrBlocks/FastLanes: data/cross_format_clean/xf/{fmt}_run{1,2,3}.csv, median of bits_per_value over the
  three runs per (dataset, arm); arm auto = without SIS, auto_sis = with SIS. 524,288 rows.
Env: SIS_ARTIFACT_ROOT (artifact root holding data/), SIS_FIG_OUT.
"""
import csv, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mc
from matplotlib.patches import Patch
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DEF_ROOT = os.path.dirname(os.path.dirname(HERE))  # artifact root
try:
    import artifact_paths as AP
    ROOT, OUT = AP.ROOT, os.environ.get("SIS_FIG_OUT", AP.OUT)
except ImportError:
    ROOT, OUT = os.environ.get("SIS_ARTIFACT_ROOT", DEF_ROOT), os.environ.get("SIS_FIG_OUT", HERE)
RUN = os.environ.get("SIS_TL_RUN", os.path.join(ROOT, "data", "toplevel_sec7"))
XO = os.path.join(ROOT, "data", "cross_format_clean", "xf")

import paperstyle
paperstyle.apply_rcparams()
plt.rcParams["axes.grid"] = False

COLS = ["snowflake", "xmark_prepost_full", "osm_h3_r9_fileorder", "osm_s2_l30_fileorder", "bing_quadkey",
        "uuidv7_hi", "publicbi_npi", "publicbi_id1", "uuidv7_lo"]

def bits(path, enc):
    for r in csv.DictReader(open(path)):
        if r["encoding"] == enc:
            assert r["validated"] == "1", (path, enc)
            return float(r["bits_per_elem"])
    raise KeyError((path, enc))

val = {"Nimble": {c: (bits(f"{RUN}/xf/nimble_raw/auto_{c}_r1_comp.csv", "Auto/view"),
                      bits(f"{RUN}/xf/nimble_raw/auto_sis_{c}_r1_comp.csv", "Auto/view")) for c in COLS}}
for name, f in (("BtrBlocks", "btrblocks"), ("FastLanes", "fastlanes")):
    d = pd.concat([pd.read_csv(f"{XO}/{f}_run{r}.csv") for r in (1, 2, 3)]).groupby(
        ["dataset", "arm"]).bits_per_value.median()
    val[name] = {c: (d[(c, "auto")], d[(c, "auto_sis")]) for c in COLS}  # (without, with)

# sanity: reproduce the ratio CSV when available
rc = os.path.join(ROOT, "out", "tab_eval_crossformat_toplevel.csv")
if os.path.exists(rc):
    r = pd.read_csv(rc, index_col=0)
    for f in val:
        for c in COLS:
            assert abs(val[f][c][1] / val[f][c][0] - r.loc[f, c]) < 1e-9, (f, c)


GREY, BLUE = "#BBBBBB", paperstyle.ENTITIES["SIS_DEFAULT"]["color"]
FMTS = ["Nimble", "BtrBlocks", "FastLanes"]
LAB = [paperstyle.short_label(c) for c in COLS]
ymax = max(v for f in val for c in COLS for v in val[f][c])
EC = dict(edgecolor="black", linewidth=0.3)

def legend(fig, W, y=1.0):
    h = [Patch(facecolor=GREY, **EC), Patch(facecolor=BLUE, **EC)]
    fig.legend(h, ["without SIS", "with SIS"], loc="upper center", ncol=2, bbox_to_anchor=(0.55, y),
               handlelength=1.0, handletextpad=0.3, columnspacing=1.0, borderpad=0, borderaxespad=0, fontsize=7)

# ---- A: three panels, shared y ----
W, H = 241.14, 90.0
fig = plt.figure(figsize=(W / 72, H / 72))
L, R, G = 25.0, 1.0, 3.0
pw = (W - L - R - 2 * G) / 3
axs = []
for p, f in enumerate(FMTS):
    ax = fig.add_axes([(L + p * (pw + G)) / W, 40 / H, pw / W, 38 / H], sharey=axs[0] if axs else None)
    axs.append(ax)
    bw, gap = 0.4, 0.5
    xs, x = [], 0.0
    for i in range(9):
        if i == 6: x += gap
        xs.append(x); x += 1.0
    ax.bar([a - bw / 2 for a in xs], [val[f][c][0] for c in COLS], bw, color=GREY, **EC)
    ax.bar([a + bw / 2 for a in xs], [val[f][c][1] for c in COLS], bw, color=BLUE, **EC)
    ax.axvline((xs[5] + xs[6]) / 2, color="#999999", lw=0.4)
    ax.set_xlim(xs[0] - 0.6, xs[-1] + 0.6)
    ax.set_xticks(xs)
    ax.set_xticklabels(LAB, fontsize=7, rotation=90)
    ax.tick_params(length=1.5, pad=1)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    ax.text(0.5, 1.0, f, transform=ax.transAxes, ha="center", va="bottom", fontsize=7)
    if p: plt.setp(ax.get_yticklabels(), visible=False)
axs[0].set_ylim(0, 65)
axs[0].set_yticks([0, 20, 40, 60])
axs[0].set_ylabel("Bits per value", labelpad=1.5)
legend(fig, W, 1.0)
fig.savefig(os.path.join(OUT, "fig_crossformat_bpv_A.pdf"))
fig.savefig(os.path.join(OUT, "fig_crossformat_bpv_A.png"), dpi=300)

# ---- B: six SFV columns, three format pairs each ----
W, H = 241.14, 78.0
fig = plt.figure(figsize=(W / 72, H / 72))
ax = fig.add_axes([25 / W, 21 / H, (W - 25 - 4) / W, 47 / H])
bw, pg, cg = 0.5, 0.12, 0.8   # bar width, gap within format group (between pairs), gap between columns
step = 2 * bw + 0.25
ticks, letters = [], []
x = 0.0
for i, c in enumerate(COLS[:6]):
    x0 = x
    for j, f in enumerate(FMTS):
        a, b = val[f][c]
        ax.bar(x, a, bw, color=GREY, align="edge", **EC)
        ax.bar(x + bw, b, bw, color=BLUE, align="edge", **EC)
        letters.append((x + bw, f[0]))
        x += step
    ticks.append((x0 + x - 0.25) / 2)
    x += cg
ax.set_ylim(bottom=0, top=65)
ax.set_yticks([0, 20, 40, 60])
ax.set_ylabel("Bits per value", labelpad=1.5)
ax.set_xlim(-0.3, x - cg + 0.1)
ax.set_xticks([lx for lx, _ in letters])
ax.set_xticklabels([t for _, t in letters], fontsize=7)
ax.tick_params(length=0, pad=1)
for k, t in enumerate(ticks):
    ax.text(t, -12, LAB[k], transform=ax.transData, ha="center", va="top", fontsize=7, clip_on=False)
for sp in ("top", "right"): ax.spines[sp].set_visible(False)
legend(fig, W, 1.0)
fig.savefig(os.path.join(OUT, "fig_crossformat_bpv_B.pdf"))
fig.savefig(os.path.join(OUT, "fig_crossformat_bpv_B.png"), dpi=300)
