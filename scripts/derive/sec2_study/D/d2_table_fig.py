"""D2: compact table + figure candidates from D/csv/split_measure.csv (study_20261001/D, 2026-10-02).

No SIS, no cost model, no encoder: purely tabulating/plotting the generic-compressor (xz/zstd)
measurements produced by d1_split_measure.py.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

D_DIR = os.path.dirname(os.path.dirname(__file__))
OUT_CSV = os.path.join(D_DIR, "csv")
OUT_FIG = os.path.join(D_DIR, "fig")

df = pd.read_csv(os.path.join(OUT_CSV, "split_measure.csv"))
df["group"] = df.kind.apply(lambda k: "control" if k == "control" else "structured")

# ---------------- compact LaTeX table: group-level summary, both compressors ----------------

def group_stats(sub, variant):
    v = sub[sub.variant == variant]
    g = v.groupby("group").gain_pct_vs_best_whole.agg(["mean", "min", "max", "count"])
    return g

lines = []
lines.append(r"\begin{tabular}{llrrrr}")
lines.append(r"\toprule")
lines.append(r"compressor & variant & group & mean\% & min\% & max\% \\")
lines.append(r"\midrule")
COMPS = ["xz", "zstd", "lz4", "snappy"]
for ci, comp in enumerate(COMPS):
    sub = df[df.compressor == comp]
    for variant in ["SPLIT_DOC", "SPLIT_DATA"]:
        g = group_stats(sub, variant)
        for grp in ["structured", "control"]:
            if grp not in g.index:
                continue
            row = g.loc[grp]
            lines.append(
                f"{comp} & {variant.replace('_', '\\_')} & {grp} & "
                f"{row['mean']:.1f} & {row['min']:.1f} & {row['max']:.1f} \\\\"
            )
    lines.append(r"\bottomrule" if ci == len(COMPS) - 1 else r"\midrule")
lines.append(r"\end{tabular}")
tex_path = os.path.join(OUT_CSV, "..", "table_split_measure.tex")
tex_path = os.path.normpath(tex_path)
with open(tex_path, "w") as f:
    f.write("\n".join(lines) + "\n")
print("wrote", tex_path)

# ---------------- figure: per-column gain of SPLIT_DATA (and SPLIT_DOC) over WHOLE, xz ----------------

sub = df[df.compressor == "xz"]
piv = sub.pivot_table(index=["column", "group"], columns="variant",
                       values="gain_pct_vs_best_whole").reset_index()
piv = piv.sort_values(["group", "SPLIT_DATA"], ascending=[True, True])
# order: controls first (bottom), then structured, each sorted by SPLIT_DATA gain ascending
order = pd.concat([piv[piv.group == "control"].sort_values("SPLIT_DATA"),
                    piv[piv.group == "structured"].sort_values("SPLIT_DATA")])
order = order.reset_index(drop=True)

ypos = np.arange(len(order))
colors = np.where(order.group == "structured", "#3A6EA5", "#B0B0B0")

fig, ax = plt.subplots(figsize=(3.4, 5.4))
bar_h = 0.38
ax.barh(ypos + bar_h / 2, order.SPLIT_DATA, height=bar_h, color=colors, label="SPLIT_DATA")
has_doc = order.SPLIT_DOC.notna()
ax.barh((ypos - bar_h / 2)[has_doc], order.SPLIT_DOC[has_doc], height=bar_h,
        color=colors[has_doc], hatch="///", edgecolor="white", linewidth=0.4, label="SPLIT_DOC")

ax.axvline(0, color="#888888", linewidth=0.8, zorder=0)
ax.set_yticks(ypos)
ax.set_yticklabels(order.column, fontsize=8)
ax.set_xlabel("gain over best WHOLE, xz preset 6 (%)", fontsize=8)
ax.tick_params(axis="x", labelsize=8)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
for spine in ("left", "bottom"):
    ax.spines[spine].set_color("#888888")
xmin, xmax = ax.get_xlim()
ax.set_xlim(min(xmin, 0), max(xmax, 0))  # linear x-axis always includes 0

from matplotlib.patches import Patch
handles = [
    Patch(facecolor="#3A6EA5", label="structured/near-miss"),
    Patch(facecolor="#B0B0B0", label="control"),
    Patch(facecolor="white", edgecolor="black", hatch="///", label="SPLIT\\_DOC (solid=SPLIT\\_DATA)"),
]
ax.legend(handles=handles, loc="lower right", fontsize=7, frameon=False)
fig.tight_layout()
fig_path = os.path.join(OUT_FIG, "fig_split_gain.pdf")
fig.savefig(fig_path)
print("wrote", fig_path)

# ---------------- supplementary: compact panel, group-mean SPLIT_DATA/SPLIT_DOC gain, all 4 compressors ----------------

fig2, ax2 = plt.subplots(figsize=(3.4, 2.6))
x = np.arange(len(COMPS))
w = 0.18
# structured SPLIT_DOC, structured SPLIT_DATA, control SPLIT_DATA (no control SPLIT_DOC: no documented layout)
doc_struct, data_struct, data_ctrl = [], [], []
for comp in COMPS:
    sub = df[df.compressor == comp]
    gdoc = group_stats(sub, "SPLIT_DOC")
    gdata = group_stats(sub, "SPLIT_DATA")
    doc_struct.append(gdoc.loc["structured", "mean"] if "structured" in gdoc.index else np.nan)
    data_struct.append(gdata.loc["structured", "mean"] if "structured" in gdata.index else np.nan)
    data_ctrl.append(gdata.loc["control", "mean"] if "control" in gdata.index else np.nan)

ax2.bar(x - w, doc_struct, width=w, color="#3A6EA5", hatch="///", edgecolor="white",
        linewidth=0.4, label="structured, SPLIT_DOC")
ax2.bar(x, data_struct, width=w, color="#3A6EA5", label="structured, SPLIT_DATA")
ax2.bar(x + w, data_ctrl, width=w, color="#B0B0B0", label="control, SPLIT_DATA")
ax2.axhline(0, color="#888888", linewidth=0.8, zorder=0)
ax2.set_xticks(x)
ax2.set_xticklabels(COMPS, fontsize=8)
ax2.set_ylabel("mean gain over best WHOLE (%)", fontsize=8)
ax2.tick_params(axis="y", labelsize=8)
for spine in ("top", "right"):
    ax2.spines[spine].set_visible(False)
for spine in ("left", "bottom"):
    ax2.spines[spine].set_color("#888888")
ymin, ymax = ax2.get_ylim()
ax2.set_ylim(min(ymin, 0), max(ymax, 0))  # linear y-axis always includes 0
ax2.legend(fontsize=7, frameon=False, loc="upper left")
fig2.tight_layout()
fig2_path = os.path.join(OUT_FIG, "fig_split_gain_compressors.pdf")
fig2.savefig(fig2_path)
print("wrote", fig2_path)
