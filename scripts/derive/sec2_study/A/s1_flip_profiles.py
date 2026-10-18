"""S1: per-bit flip-probability profiles for every local column, file order + shuffled (seed 0).
Outputs: csv/flip_profiles.csv, fig/fig2_flip_profiles.pdf (one panel per sub-type).
"""
import csv
import os
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import study_common as sc

OUT = "$PROJECT/paper-repo/study_20261001/A"
N = 524288
t0 = time.time()

rows = []
gate_rows = []
profiles = {}
for name, cfg in sc.COLUMNS.items():
    v = sc.load(name, n=N)
    p_file = sc.flip_profile(v)
    rng = np.random.default_rng(0)
    vs = v.copy()
    rng.shuffle(vs)
    p_shuf = sc.flip_profile(vs)
    grad = np.zeros(64)
    grad[1:] = np.abs(np.diff(p_file))
    ok_file, f_file = sc.gate_decision(p_file)
    ok_shuf, f_shuf = sc.gate_decision(p_shuf)
    profiles[name] = (p_file, p_shuf)
    gate_rows.append(dict(column=name, subtype=cfg["subtype"], kind=cfg["kind"], n=len(v),
                           gate_file=int(ok_file), gate_shuffled=int(ok_shuf),
                           entropy_file=f_file["active_entropy"], entropy_shuf=f_shuf["active_entropy"],
                           maxg_file=f_file["maxg"], maxg_shuf=f_shuf["maxg"]))
    for b in range(64):
        rows.append(dict(column=name, bit=b, p_file=p_file[b], p_shuffled=p_shuf[b], grad=grad[b]))

with open(f"{OUT}/csv/flip_profiles.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["column", "bit", "p_file", "p_shuffled", "grad"])
    w.writeheader()
    w.writerows(rows)

with open(f"{OUT}/csv/flip_profiles_gate.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["column", "subtype", "kind", "n", "gate_file", "gate_shuffled",
                                        "entropy_file", "entropy_shuf", "maxg_file", "maxg_shuf"])
    w.writeheader()
    w.writerows(gate_rows)

# ---- figure: one panel per sub-type, flip prob (file order) vs bit index, linear y from 0 ----
subtypes = ["T1", "T2", "T3", "T4", "control"]
palette = ["#1b6fa8", "#c2572a", "#3c8a5b", "#8a5fbf", "#b0392f", "#4d4d4d", "#9a7d0a", "#2e7d7d",
           "#6b6bb8", "#a85c9e", "#5c8a3c"]

fig, axes = plt.subplots(len(subtypes), 1, figsize=(6.5, 2.0 * len(subtypes)), sharex=True)
for ax, st in zip(axes, subtypes):
    names = [n for n, c in sc.COLUMNS.items() if c["subtype"] == st]
    for i, name in enumerate(names):
        p_file, _ = profiles[name]
        ax.plot(range(64), p_file, label=name, color=palette[i % len(palette)], linewidth=1.2)
    ax.set_ylim(bottom=0, top=1.0)
    ax.set_xlim(0, 63)
    ax.set_ylabel(f"{st}\nflip prob.", fontsize=8)
    ax.tick_params(labelsize=8)
    ax.legend(fontsize=6, ncol=3, loc="upper left", frameon=False)
axes[-1].set_xlabel("bit (0=LSB)", fontsize=8)
fig.tight_layout()
fig.savefig(f"{OUT}/fig/fig2_flip_profiles.pdf")
plt.close(fig)

dt = time.time() - t0
with open(f"{OUT}/README_S1.md", "w") as fh:
    fh.write(f"""# S1: flip-probability profiles

Inputs (sha256 prefix, first 1MiB; see study_common.COLUMNS for full paths), N={N} rows (file-order prefix):
""")
    for name, cfg in sc.COLUMNS.items():
        try:
            sha = sc.sha256_prefix(cfg["path"])
        except Exception as e:
            sha = f"ERROR {e}"
        fh.write(f"- {name}: `{cfg['path']}` sha256[:12]={sha}\n")
    fh.write(f"""
Method: for every column, load the leading {N} rows in file order (int tokens -> uint64).
Per-bit flip probability p[b] = fraction of adjacent rows (i, i+1) where bit b differs
(`study_common.flip_profile`). Shuffled profile: same column, `numpy.random.default_rng(0).shuffle`
in place, same statistic. Gate decision: shipped admission test
(`paper-repo/eval_figures/c3_bitflip_admission/gates.py` `gradient_gate` + `plot_c3_profiles.py:20`
entropy_max=0.8), reimplemented in `study_common.gate_decision` (verified to match gates.py symbolically).

Outputs:
- csv/flip_profiles.csv: column,bit,p_file,p_shuffled,grad (64 rows/column)
- csv/flip_profiles_gate.csv: column,subtype,kind,n,gate_file,gate_shuffled,entropy_file,entropy_shuf,maxg_file,maxg_shuf
- fig/fig2_flip_profiles.pdf: one panel per sub-type (T1-T4, control), flip prob vs bit, file order, linear y in [0,1], no title

Runtime: {dt:.1f} s
""")
print("done", dt)
