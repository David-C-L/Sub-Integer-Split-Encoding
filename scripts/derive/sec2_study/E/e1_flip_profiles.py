"""E1: per-bit adjacent-row flip-profile for the 4 float columns (study_20261001/E, 2026-10-02).

File order + shuffled (seed 0), gradient. Marks IEEE boundaries at bit 52 (mantissa/exponent)
and bit 63 (exponent/sign), and the data-chosen partition edges (data_chosen_partition, k=2.0,
same call as C1). No SIS/Nimble/cost model: this is the same flip_profile statistic A/C already
use, applied to the raw IEEE uint64 bits.

Outputs: csv/flip_profiles_float.csv (column,bit,p_file,p_shuffled,grad),
fig/fig_flip_float.pdf (heatmap, rows grouped by class).
"""
import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import float_common as F  # noqa: E402

OUT = F.E_DIR

t0 = time.time()
rows = []
partitions = {}
heat_file = []
heat_shuf = []

for name in F.ORDERED_NAMES:
    _, v = F.load_bits(name)
    p_file = F.A.flip_profile(v)
    rng = np.random.default_rng(0)
    vs = v.copy()
    rng.shuffle(vs)
    p_shuf = F.A.flip_profile(vs)
    grad = np.zeros(64)
    grad[1:] = np.abs(np.diff(p_file))
    partition = F.C.data_chosen_partition(p_file, k=2.0)
    partitions[name] = partition
    heat_file.append(p_file)
    heat_shuf.append(p_shuf)
    for b in range(64):
        rows.append(dict(column=name, bit=b, p_file=p_file[b], p_shuffled=p_shuf[b], grad=grad[b]))
    print(f"{name}: data_chosen_partition={partition}", file=sys.stderr)

df = pd.DataFrame(rows)
df.to_csv(os.path.join(OUT, "csv", "flip_profiles_float.csv"), index=False)

# ---- figure: heatmap, rows = columns grouped by class, cols = bit 0..63 (file order) ----
heat = np.array(heat_file)  # (n_columns, 64)
fig, ax = plt.subplots(figsize=(7.0, 0.55 * len(F.ORDERED_NAMES) + 1.2))
im = ax.imshow(heat, aspect="auto", cmap="viridis", vmin=0, vmax=1,
               extent=[-0.5, 63.5, len(F.ORDERED_NAMES) - 0.5, -0.5])
ax.set_yticks(range(len(F.ORDERED_NAMES)))
ax.set_yticklabels([f"{n}\n({F.FLOATS[n]['class_label']})" for n in F.ORDERED_NAMES], fontsize=7)
ax.set_xlabel("bit (0=LSB)", fontsize=8)
ax.tick_params(labelsize=8)
# IEEE boundaries
for b in (52, 63):
    ax.axvline(b - 0.5, color="white", linewidth=1.0, linestyle="--")
ax.text(52 - 0.5, -0.9, "mant|exp", fontsize=6, color="black", ha="center")
ax.text(63 - 0.5, -0.9, "exp|sign", fontsize=6, color="black", ha="center")
cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
cbar.set_label("p(flip), file order", fontsize=7)
cbar.ax.tick_params(labelsize=7)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig", "fig_flip_float.pdf"))
plt.close(fig)

dt = time.time() - t0
print(f"wrote csv/flip_profiles_float.csv, fig/fig_flip_float.pdf ({dt:.1f}s)")

# stash partitions for downstream scripts (E4) as a tiny json
import json  # noqa: E402
with open(os.path.join(OUT, "csv", "e1_data_chosen_partitions.json"), "w") as fh:
    json.dump({n: p for n, p in partitions.items()}, fh)
