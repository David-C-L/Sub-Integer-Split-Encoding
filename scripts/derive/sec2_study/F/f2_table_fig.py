"""F2: table + figure candidates from F/csv/addressable_layouts.csv (study_20261001/F, 2026-10-02).

No SIS, no cost model, no encoder: purely tabulating/plotting f1's addressable-layout bits/value
and the reused xz WHOLE reference.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

F_DIR = os.path.dirname(os.path.dirname(__file__))
OUT_CSV = os.path.join(F_DIR, "csv")
OUT_FIG = os.path.join(F_DIR, "fig")
sys.path.insert(0, os.path.normpath(os.path.join(F_DIR, "..", "..", "..", "pulls")))
import paperstyle
paperstyle.apply_rcparams()

df = pd.read_csv(os.path.join(OUT_CSV, "addressable_layouts.csv"))


def group_of(kind):
    if kind == "control":
        return "control"
    if isinstance(kind, str) and kind.startswith("near_miss"):
        return "near_miss"
    return "structured"


kindmap = df.drop_duplicates("column").set_index("column")["kind"]
groupmap = kindmap.map(group_of)

# ---------------- group-level summary table (LaTeX booktabs) ----------------

lines = []
lines.append(r"\begin{tabular}{llrrrr}")
lines.append(r"\toprule")
lines.append(r"layout & group & mean\% & min\% & max\% & n \\")
lines.append(r"\midrule")
for vi, variant in enumerate(["SPLIT_DOC", "SPLIT_DATA", "xz_WHOLE"]):
    sub = df[df.method == variant].copy()
    sub["group"] = sub.column.map(groupmap)
    g = sub.groupby("group").gain_pct_vs_best_whole.agg(["mean", "min", "max", "count"])
    for grp in ["structured", "near_miss", "control"]:
        if grp not in g.index:
            continue
        row = g.loc[grp]
        lines.append(
            f"{variant.replace('_', '\\_')} & {grp.replace('_', '\\_')} & "
            f"{row['mean']:.1f} & {row['min']:.1f} & {row['max']:.1f} & {int(row['count'])} \\\\"
        )
    lines.append(r"\bottomrule" if vi == 2 else r"\midrule")
lines.append(r"\end{tabular}")
tex_path = os.path.join(F_DIR, "table_addressable_layouts.tex")
with open(tex_path, "w") as f:
    f.write("\n".join(lines) + "\n")
print("wrote", tex_path)

# ---------------- figure: per-column bits/value, WHOLE_best vs SPLIT_DATA vs xz_WHOLE ----------------

piv = df.pivot_table(index="column", columns="method", values="bits_per_value").reset_index()
piv["group"] = piv.column.map(groupmap)
piv = piv.sort_values(["group", "WHOLE_best"], ascending=[True, False])
order = pd.concat([
    piv[piv.group == "structured"].sort_values("WHOLE_best", ascending=False),
    piv[piv.group == "near_miss"].sort_values("WHOLE_best", ascending=False),
    piv[piv.group == "control"].sort_values("WHOLE_best", ascending=False),
]).reset_index(drop=True)

ypos = np.arange(len(order))
bar_h = 0.26

# categorical colors, sourced from paperstyle.SECTION2_ADDRESSABLE_COLORS
# (scheme B, Tol muted/vibrant, decision 2026-10-02; shared with f3_openzl_fig.py
# so both Section 2 addressable-layout figures agree on colour and wording).
COLOR_WHOLE = paperstyle.SECTION2_ADDRESSABLE_COLORS["WHOLE"]["color"]
COLOR_SPLIT = paperstyle.SECTION2_ADDRESSABLE_COLORS["SPLIT_DATA"]["color"]
COLOR_XZ = paperstyle.SECTION2_ADDRESSABLE_COLORS["XZ"]["color"]
LABEL_WHOLE = paperstyle.SECTION2_ADDRESSABLE_COLORS["WHOLE"]["label"]
LABEL_SPLIT = paperstyle.SECTION2_ADDRESSABLE_COLORS["SPLIT_DATA"]["label"]
LABEL_XZ = paperstyle.SECTION2_ADDRESSABLE_COLORS["XZ"]["label"]

# Rendered at the exact LaTeX placed width (\columnwidth = 3.33in, acmart
# sigconf; coordinator fix 2026-10-02 -- a wider PDF gets shrunk by LaTeX's
# \includegraphics scaling and the 8pt text floor silently breaks).
fig, ax = plt.subplots(figsize=(3.33, 5.2))
ax.barh(ypos + bar_h, order.WHOLE_best, height=bar_h, color=COLOR_WHOLE, label=LABEL_WHOLE)
ax.barh(ypos, order.SPLIT_DATA, height=bar_h, color=COLOR_SPLIT, label=LABEL_SPLIT)
ax.barh(ypos - bar_h, order.xz_WHOLE, height=bar_h, color=COLOR_XZ, label=LABEL_XZ)

ax.set_yticks(ypos)
ax.set_yticklabels([paperstyle.section2_dataset_label(c) for c in order.column], fontsize=7)
ax.set_xlabel("bits / value", fontsize=8)
ax.tick_params(axis="x", labelsize=8)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
for spine in ("left", "bottom"):
    ax.spines[spine].set_color("#888888")
xmin, xmax = ax.get_xlim()
ax.set_xlim(0, xmax)  # linear x-axis, always starts at 0
# Legend above the axes, single column (3 short entries) so it stays within
# the 3.33in placed width at 8pt without clipping or overlapping any bar
# (coordinator fix 2026-10-02; matches f3_openzl_fig.py's approach).
ax.legend(fontsize=8, frameon=False, loc="lower left", bbox_to_anchor=(0.0, 1.01),
          ncol=1, handlelength=1.1, handletextpad=0.35, borderaxespad=0.1,
          labelspacing=0.25)
fig.subplots_adjust(left=0.33, right=0.97, top=0.80, bottom=0.08)
fig_path = os.path.join(OUT_FIG, "fig_addressable_vs_xz.pdf")
fig.savefig(fig_path)
print("wrote", fig_path)
