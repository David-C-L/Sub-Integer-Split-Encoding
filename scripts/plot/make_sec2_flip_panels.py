"""Single-panel flip-probability PDFs for the Sec. 2 subfigure (decision 10: LaTeX subfigures
from single-panel PDFs). Source: ../../csv/flip_profiles.csv (p_file, file order). No titles."""
import csv, collections, os, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import artifact_paths as AP  # noqa: E402
import paperstyle
paperstyle.apply_rcparams()
rows = list(csv.DictReader(open(f"{AP.DATA}/sec2_study/A/csv/flip_profiles.csv")))
prof = collections.defaultdict(dict)
for r in rows: prof[r["column"]][int(r["bit"])] = float(r["p_file"])
edges = {"snowflake": [12, 22], "instagram": [10, 23], "uuidv7_hi": [12, 16], "xmark": [28, 56],
         "quadkey": [30], "h3_r9": [45, 52, 56], "s2_l16": [61]}
label = {c: paperstyle.section2_dataset_label(c) for c in
         ["snowflake", "instagram", "uuidv7_hi", "h3_r9", "s2_l16", "quadkey", "xmark",
          "publicbi_num_employees", "publicbi_drug_cost", "uuidv7_lo", "publicbi_npi"]}
panels = {"T1": ["snowflake", "instagram"], "T2": ["uuidv7_hi"], "T3": ["h3_r9", "s2_l16", "quadkey"],
          "T4": ["xmark"], "nearmiss": ["publicbi_num_employees", "publicbi_drug_cost"],
          "control": ["uuidv7_lo", "publicbi_npi"]}
# Dedicated Section 2 dataset-identity triple (Tol muted/vibrant, chosen to not
# collide with any ENTITIES hex in paperstyle.py); these 3 slots are reused
# positionally across panels, as in the original ad hoc palette.
colors = [paperstyle.SECTION2_COLUMN_COLORS["snowflake"], paperstyle.SECTION2_COLUMN_COLORS["instagram"],
          paperstyle.SECTION2_COLUMN_COLORS["uuidv7_hi"]]
# Rendered at the exact LaTeX placed size (subfigure width 0.48\columnwidth
# of acmart sigconf's \columnwidth=241.14pt=3.33in -> 1.60in wide, ~1.05in
# tall; coordinator fix 2026-10-02) so 8pt text in the PDF stays 8pt once
# \includegraphics[width=\linewidth] scales it -- rendering wider and relying
# on LaTeX to shrink it silently drops the font below the 8pt floor.
# With the MSB on the left the legend goes upper-left (high bits are near 0 in T1/T3/nearmiss);
# control has a 0.5 plateau across the whole axis, so its y top is raised to fit the legend above it.
YTOP = {}  # common y top below
LEGLOC = {"T3": "upper right"}  # T3 field lines cross the upper-left; bits 0-25 are free above 0.5
for name, cols in panels.items():
    fig, ax = plt.subplots(figsize=(1.60, 0.92))
    for i, c in enumerate(cols):
        p = [prof[c][b] for b in range(64)]
        ax.plot(range(64), p, color=colors[i], linewidth=1.0, label=label[c])
        for e in edges.get(c, []):
            ax.axvline(e, color=colors[i], linewidth=0.5, linestyle=":", alpha=0.8)
    ax.set_ylim(bottom=0, top=1.4); ax.set_xlim(63, 0)  # MSB (bit 63) on the left
    ax.set_xticks([0, 32, 63]); ax.set_yticks([0, 0.5])
    ax.tick_params(labelsize=7, length=2, pad=1.5)
    ax.set_ylabel("flip p.", fontsize=8, labelpad=1.5)
    ax.set_xlabel("bit", fontsize=8, labelpad=1.5)
    ax.grid(axis="y", color="#dddddd", linewidth=0.4); ax.spines[["top", "right"]].set_visible(False)
    # At most 2-3 short entries, placed above the axes so it never covers data.
    # ncol is chosen from the total label character budget, not just the
    # count, so a long label (e.g. "Employee count") doesn't push a sibling
    # entry past the figure's 1.6in placed width (coordinator fix
    # 2026-10-02: ncol=2 clipped "Drug cost" to "Drug" when paired with the
    # long "Employee count" label; ncol=3 clipped "Quadkey").
    labels_here = [label[c] for c in cols]
    max_len = max(len(s) for s in labels_here)
    total_chars = sum(len(s) for s in labels_here)
    if len(cols) == 1:
        legend_ncol = 1
    elif max_len <= 8 and total_chars <= 16:
        legend_ncol = len(cols)
    elif max_len <= 8:
        legend_ncol = 2
    else:
        legend_ncol = 1
    # Flip probabilities never exceed 0.5, so the band above it is empty on
    # every panel and holds the legend (coordinator 2026-10-03: legends above
    # the axes took ~40% of the panel height).
    ax.legend(fontsize=7, frameon=False, loc=LEGLOC.get(name, "upper left"), ncol=1,
              handlelength=0.9, handletextpad=0.25, borderaxespad=0.1,
              labelspacing=0.1)
    top = 0.97
    fig.subplots_adjust(left=0.22, right=0.95, top=top, bottom=0.30)
    fig.savefig(f"{AP.OUT}/flip_{name}.pdf"); plt.close(fig)
print("ok")
