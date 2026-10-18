"""F3: add OpenZL as a fourth bar vs the existing WHOLE_best / SPLIT_DATA / xz_WHOLE comparison
(study_20261001/F, 2026-10-02). Reuses F/csv/addressable_layouts.csv (f1) and the new
F/csv/openzl_reference.csv (B-reused where input sha256 matches D's, else a new benchmark host run with
B's exact method -- see F/README.md). Writes fig/fig_addressable_vs_xz_v2.pdf (keeps the
original fig/fig_addressable_vs_xz.pdf) and appends an OpenZL row to the headline table.
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
oz = pd.read_csv(os.path.join(OUT_CSV, "openzl_reference.csv")).set_index("column")["openzl_full_bpv"]


def group_of(kind):
    if kind == "control":
        return "control"
    if isinstance(kind, str) and kind.startswith("near_miss"):
        return "near_miss"
    return "structured"


kindmap = df.drop_duplicates("column").set_index("column")["kind"]
groupmap = kindmap.map(group_of)

piv = df.pivot_table(index="column", columns="method", values="bits_per_value").reset_index()
piv["group"] = piv.column.map(groupmap)
piv["openzl"] = piv.column.map(oz)
piv = pd.concat([
    piv[piv.group == "structured"].sort_values("WHOLE_best", ascending=False),
    piv[piv.group == "near_miss"].sort_values("WHOLE_best", ascending=False),
    piv[piv.group == "control"].sort_values("WHOLE_best", ascending=False),
]).reset_index(drop=True)

ypos = np.arange(len(piv))
bar_h = 0.2

# Colours/labels from paperstyle.SECTION2_ADDRESSABLE_COLORS (scheme B, Tol
# muted/vibrant, decision 2026-10-02; shared with f2_table_fig.py so both
# Section 2 addressable-layout figures agree). OpenZL uses the same entity
# colour as every other figure in the paper (paperstyle.ENTITIES["OPENZL"]).
COLOR_WHOLE = paperstyle.SECTION2_ADDRESSABLE_COLORS["WHOLE"]["color"]
COLOR_SPLIT = paperstyle.SECTION2_ADDRESSABLE_COLORS["SPLIT_DATA"]["color"]
COLOR_XZ = paperstyle.SECTION2_ADDRESSABLE_COLORS["XZ"]["color"]
COLOR_OZ = paperstyle.color_for("OPENZL")
LABEL_WHOLE = paperstyle.SECTION2_ADDRESSABLE_COLORS["WHOLE"]["label"]
LABEL_SPLIT = paperstyle.SECTION2_ADDRESSABLE_COLORS["SPLIT_DATA"]["label"]
LABEL_XZ = paperstyle.SECTION2_ADDRESSABLE_COLORS["XZ"]["label"]
LABEL_OZ = "OpenZL"

# Rendered at the exact LaTeX placed width (\includegraphics[width=\columnwidth],
# acmart sigconf \columnwidth = 241.14pt = 3.33in; coordinator fix 2026-10-02:
# an earlier 5.2in-wide render would be shrunk by LaTeX to 3.33in and drop the
# 8pt text below the floor). Height capped at 4.3in per the coordinator's
# page-budget note. The axes position is set explicitly via subplots_adjust
# instead of tight_layout's rect, so the bars get the full remaining width
# regardless of how long the y-tick label text runs.
fig, ax = plt.subplots(figsize=(3.33, 3.75))
ax.barh(ypos + 1.5 * bar_h, piv.WHOLE_best, height=bar_h, color=COLOR_WHOLE, label=LABEL_WHOLE)
ax.barh(ypos + 0.5 * bar_h, piv.SPLIT_DATA, height=bar_h, color=COLOR_SPLIT, label=LABEL_SPLIT)
ax.barh(ypos - 0.5 * bar_h, piv.xz_WHOLE, height=bar_h, color=COLOR_XZ, label=LABEL_XZ)
ax.barh(ypos - 1.5 * bar_h, piv.openzl, height=bar_h, color=COLOR_OZ, label=LABEL_OZ)

ax.set_yticks(ypos)
ax.set_yticklabels([paperstyle.section2_dataset_label(c) for c in piv.column], fontsize=7)
ax.set_ylim(-0.6, len(piv) - 0.4)
ax.set_xlabel("bits / value", fontsize=8)
ax.tick_params(axis="x", labelsize=8)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
for spine in ("left", "bottom"):
    ax.spines[spine].set_color("#888888")
xmin, xmax = ax.get_xlim()
ax.set_xlim(0, xmax)  # linear x-axis, always starts at 0
# Legend placed above the axes (outside the plotting area), 2 columns
# spanning the figure width, so it never overlaps any bar.
fig.legend(*ax.get_legend_handles_labels(), fontsize=8, frameon=False,
           loc="upper center", bbox_to_anchor=(0.5, 0.995), ncol=2,
           handlelength=1.1, handletextpad=0.35, columnspacing=1.0,
           borderaxespad=0.1, labelspacing=0.25)
fig.subplots_adjust(left=0.33, right=0.97, top=0.885, bottom=0.105)
fig_path = os.path.join(OUT_FIG, "fig_addressable_vs_xz_v2.pdf")
fig.savefig(fig_path)
print("wrote", fig_path)

# ---------------- OpenZL headline row, by group ----------------
# gain of OpenZL over the best whole-column addressable layout (WHOLE_best), same sign
# convention as the existing table (positive = OpenZL smaller/better).
piv["gain_pct_openzl_vs_whole_best"] = (piv.WHOLE_best - piv.openzl) / piv.WHOLE_best * 100
g = piv.groupby("group").gain_pct_openzl_vs_whole_best.agg(["mean", "min", "max", "count"])

lines = [r"\begin{tabular}{llrrrr}", r"\toprule",
         r"layout & group & mean\% & min\% & max\% & n \\", r"\midrule"]
for grp in ["structured", "near_miss", "control"]:
    if grp not in g.index:
        continue
    row = g.loc[grp]
    lines.append(
        f"OpenZL\\_WHOLE & {grp.replace('_', '\\_')} & "
        f"{row['mean']:.1f} & {row['min']:.1f} & {row['max']:.1f} & {int(row['count'])} \\\\"
    )
lines.append(r"\bottomrule")
lines.append(r"\end{tabular}")
row_path = os.path.join(F_DIR, "table_addressable_layouts_openzl_row.tex")
with open(row_path, "w") as f:
    f.write("\n".join(lines) + "\n")
print("wrote", row_path)

for grp in ["structured", "near_miss", "control"]:
    if grp in g.index:
        row = g.loc[grp]
        print(f"{grp}: mean={row['mean']:.1f}% min={row['min']:.1f}% max={row['max']:.1f}% n={int(row['count'])}")

# where OpenZL beats or loses to xz specifically
piv["openzl_minus_xz_bpv"] = piv.openzl - piv.xz_WHOLE
beats = piv[piv.openzl_minus_xz_bpv < 0].sort_values("openzl_minus_xz_bpv")
loses = piv[piv.openzl_minus_xz_bpv > 0].sort_values("openzl_minus_xz_bpv", ascending=False)
print("\nOpenZL beats xz (smaller bpv) on:")
for _, r in beats.iterrows():
    print(f"  {r.column}: openzl={r.openzl:.2f} xz={r.xz_WHOLE:.2f}")
print("\nOpenZL loses to xz (larger bpv) on:")
for _, r in loses.iterrows():
    print(f"  {r.column}: openzl={r.openzl:.2f} xz={r.xz_WHOLE:.2f}")
