#!/usr/bin/env python3
"""HALF-WIDTH SNOWFLAKE VARIANT (2026-10-17, the author): only the Snowflake panel, ~118 pt wide (subfigure
next to fig_budget_sweep_half at the same height, SIS_HALF_H_PT). Same data, series, colours, labels and
annotations as the column figure; legend inside the panel (lower left, empty there). Original docstring follows.

fig_openzl_blocksize_tradeoff, the author 2026-09-30 compact pass: same design
as the 20260929b redesign (one trade-off panel: x = point-probe latency ns
log, y = size bits/value linear from 0; one line+marker series per (codec,
dataset), SIS plotted as a star) with whitespace removed between the legend
and the panels and inside the panels (tight x/y limits around the data,
y still from 0). Table-1 name only: "SIS" (SIS/realNested, the default
configuration; the star uses the SIS/realNested+view pinned-plan pull, same
build/host as v3, noted below).

Data (unchanged from 20260929b):
  codec curves: pulls/ablations_20260928_2223/a/
    comp_<dataset>.csv (bits_per_elem per zstd/block-K, openzl/block-K)
    point_<dataset>_r{1,2,3}.csv (ns_per_probe per block-K, median of 3 hot repeats)
  SIS star: pulls/plan_decode_20260928_2303/summary.csv
    row arm == "SIS/realNested+view", columns bits_per_value, point_ns_per_probe
"""
import os
import re

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # 2026-10-17: paperstyle copy with SIS_PALETTE
import paperstyle

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import artifact_paths as AP  # artifact-relative paths
IN_DIR = os.environ.get("SIS_ABL_DIR", f"{AP.TL}/abl_a")
PLAN_SUMMARY = os.environ.get("SIS_PLAN_SUMMARY", f"{AP.TL}/plan_decode/summary.csv")
OUT_DIR = AP.OUT

COL_W = 3.33
DATASETS = [("snowflake", paperstyle.short_label("snowflake"))]
CODECS = [("zstd", "Zstd"), ("openzl", "OpenZL")]
COLOR = {"zstd": paperstyle.ENTITIES["ZSTD"]["color"], "openzl": paperstyle.ENTITIES["OPENZL"]["color"]}
MARKER = {"zstd": "o", "openzl": "s"}
BLOCK_RE = re.compile(r"^(zstd|openzl)/block-(\d+)$")
FS = 8


def block_series(df, col):
    rows = []
    for _, r in df.iterrows():
        m = BLOCK_RE.match(r["encoding"])
        if m:
            rows.append((m.group(1), int(m.group(2)), r[col]))
    return rows


def k_label(k):
    if k >= 1024 and k % 1024 == 0:
        return f"{k // 1024}K"
    return str(k)


def load_dataset(ds_key):
    comp = pd.read_csv(os.path.join(IN_DIR, f"comp_{ds_key}.csv"))
    size = {(c, k): v for c, k, v in block_series(comp, "bits_per_elem")}
    reps = [pd.read_csv(os.path.join(IN_DIR, f"point_{ds_key}_r{r}.csv")) for r in (1, 2, 3)]
    merged = pd.concat(reps, ignore_index=True)
    merged = merged[merged["encoding"].str.match(BLOCK_RE)]
    merged["codec"] = merged["encoding"].str.extract(BLOCK_RE)[0]
    merged["K"] = merged["encoding"].str.extract(BLOCK_RE)[1].astype(int)
    med = merged.groupby(["codec", "K"])["ns_per_probe"].median().to_dict()
    out = {}
    for (c, k), v in size.items():
        if (c, k) in med:
            out[(c, k)] = (med[(c, k)], v)
    return out


plan = pd.read_csv(PLAN_SUMMARY)
sis_row = plan[plan["arm"] == "SIS/realNested+view"].set_index("dataset")
matplotlib.rcParams.update({"font.size": FS, "pdf.fonttype": 42, "ps.fonttype": 42})
W_IN = float(os.environ.get("SIS_HALF_W_PT", "118.0")) / 72.0
H_IN = float(os.environ.get("SIS_HALF_H_PT", "100.0")) / 72.0
MARGIN_IN = 1.0 / 72.0
fig, ax = plt.subplots(1, 1, figsize=(W_IN, H_IN))
ds_key, ds_label = DATASETS[0]
pts = load_dataset(ds_key)
xs_all, values = [], []
for codec_key, codec_label in CODECS:
    series = sorted((k, lat, bpv) for (c, k), (lat, bpv) in pts.items() if c == codec_key)
    xs = [p[1] for p in series]
    ys = [p[2] for p in series]
    xs_all.extend(xs)
    values += [(codec_label, k, lat, bpv) for k, lat, bpv in series]
    ax.plot(xs, ys, color=COLOR[codec_key], marker=MARKER[codec_key], markersize=3.6, linewidth=1.1, label=codec_label)
    for i, (k, lat, bpv) in enumerate(series):
        if i not in {0, len(series) - 1}:
            continue
        if i == len(series) - 1:   # as the column figure (Snowflake branch)
            dx, dy, ha, va = (4, 3, "right", "bottom") if codec_key == "zstd" else (-3, -3, "right", "top")
        else:
            dy = -3 if series[i + 1][2] > bpv else 3
            dx, ha, va = 3, "left", ("top" if dy < 0 else "bottom")
        ax.annotate(k_label(k), (lat, bpv), fontsize=FS, color=COLOR[codec_key], xytext=(dx, dy),
                    textcoords="offset points", ha=ha, va=va, annotation_clip=False)
srow = sis_row.loc[ds_key]
xs_all.append(srow["point_ns_per_probe"])
values.append(("SIS", "", srow["point_ns_per_probe"], srow["bits_per_value"]))
ax.scatter([srow["point_ns_per_probe"]], [srow["bits_per_value"]], marker="*", s=70,
           color=paperstyle.ENTITIES["SIS_DEFAULT"]["color"], zorder=5, label="SIS")
ax.set_xscale("log")
y_max = max([bpv for (_c, _k), (_lat, bpv) in pts.items()] + [srow["bits_per_value"]])
ax.text(0.03, 0.97, ds_label, transform=ax.transAxes, ha="left", va="top", fontsize=FS)
ax.tick_params(labelsize=FS, pad=1, length=2.5)
ax.tick_params(which="minor", length=1.5)
ax.grid(True, which="major", axis="both", alpha=0.25, linewidth=0.4)
ax.set_xlim(min(xs_all) / 1.3, max(xs_all) * 1.8)
ax.set_ylim(bottom=0, top=y_max * float(os.environ.get("SIS_FIG_YTOP_FACTOR", "1.30")))
ax.set_ylabel("Size (bits/value)", fontsize=FS, labelpad=1)
xl = fig.supxlabel("Point latency (ns, log scale)", fontsize=FS, y=MARGIN_IN / H_IN, va="bottom")  # centred on the figure: wider than the axes
ax.legend(loc="lower left", ncol=1, frameon=False, fontsize=FS, handlelength=1.6, handletextpad=0.4,
          labelspacing=0.2, borderaxespad=0.3, borderpad=0.1)
l, r, b, t = 0.2, 0.98, 0.2, 0.98
for _ in range(10):
    fig.subplots_adjust(left=l, right=r, bottom=b, top=t)
    fig.canvas.draw()
    bb = fig.get_tightbbox(fig.canvas.get_renderer())
    dl, dr = bb.x0 - MARGIN_IN, (W_IN - MARGIN_IN) - bb.x1
    db, dt = bb.y0 - MARGIN_IN, (H_IN - MARGIN_IN) - bb.y1
    l -= dl / W_IN; r += dr / W_IN; b -= db / H_IN; t += dt / H_IN
    if max(abs(dl), abs(dr), abs(db), abs(dt)) < 0.05 / 72:
        break
os.makedirs(OUT_DIR, exist_ok=True)
base = os.path.join(OUT_DIR, "fig_blocksize_snowflake_half")
fig.savefig(base + ".pdf")
fig.savefig(base + ".png", dpi=300)
pd.DataFrame(values, columns=["series", "block", "point_ns", "bits_per_value"]).to_csv(base + "_values.csv", index=False)
print(f"wrote {base}: {W_IN*72:.2f} x {H_IN*72:.2f} pt")
