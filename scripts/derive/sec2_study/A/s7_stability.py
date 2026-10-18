"""S7 + G4: stability of the membership decision and gain G across row prefixes,
sample sizes and per-block (64K-row blocks), on full local files.

Full local files (plan D / provenance doc): snowflake (10M), xmark (32.3M), h3_r9 (10M),
publicbi_npi (17.29M, control), instagram (1.54M, local full). quadkey/uuidv7 full files are
benchmark host-only (not available locally) and are skipped here, matching the plan.
"""
import csv
import time

import numpy as np
import pandas as pd

import study_common as sc

OUT = "$PROJECT/paper-repo/study_20261001/A"
BLOCK = 65536
t0 = time.time()

FULL_COLS = ["snowflake", "xmark", "h3_r9", "publicbi_npi", "instagram"]


def load_full_fast(name):
    cfg = sc.COLUMNS[name]
    df = pd.read_csv(cfg["path"], header=None, dtype="uint64", usecols=[0])
    return df.iloc[:, 0].to_numpy()


def membership_row(name, v, tag):
    p = sc.flip_profile(v)
    ok, f = sc.gate_decision(p)
    whole, which, _ = sc.best_whole_cost(v)
    layout = sc.COLUMNS[name]["layout"]
    if layout is not None:
        doc_cost, _ = sc.documented_field_cost(v, layout)
        g_doc = whole - doc_cost
    else:
        doc_cost, g_doc = float("nan"), float("nan")
    return dict(column=name, tag=tag, n=len(v), gate=int(ok), entropy=f["active_entropy"],
                G_doc_bits=g_doc)


prefix_rows, sample_rows, block_rows = [], [], []
full_cache = {}

for name in FULL_COLS:
    v_full = load_full_fast(name)
    full_cache[name] = v_full
    N = len(v_full)

    # (1) prefix sweep: 65536 .. full, doubling
    sizes = []
    s = BLOCK
    while s < N:
        sizes.append(s)
        s *= 2
    sizes.append(N)
    for s in sizes:
        prefix_rows.append(dict(membership_row(name, v_full[:s], f"prefix_{s}"), prefix_n=s))

    # (2) sample-size sweep: 128 .. full, random subsample (seed 0), preserving relative order
    rng = np.random.default_rng(0)
    ssizes = [128, 512, 2048, 8192, 32768, 131072, 524288]
    ssizes = [s for s in ssizes if s <= N] + [N]
    for s in sorted(set(ssizes)):
        if s == N:
            idx = np.arange(N)
        else:
            idx = np.sort(rng.choice(N, size=s, replace=False))
        sample_rows.append(dict(membership_row(name, v_full[idx], f"sample_{s}"), sample_n=s))

    # (3) per-block: 64K-row blocks over the whole file
    nblocks = N // BLOCK
    boundary_sets = []
    for bi in range(nblocks):
        blk = v_full[bi * BLOCK:(bi + 1) * BLOCK]
        r = membership_row(name, blk, f"block_{bi}")
        r["block_index"] = bi
        block_rows.append(r)
        layout = sc.COLUMNS[name]["layout"]

with open(f"{OUT}/csv/stability_prefix.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["column", "tag", "n", "gate", "entropy", "G_doc_bits", "prefix_n"])
    w.writeheader()
    w.writerows(prefix_rows)

with open(f"{OUT}/csv/stability_sample.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["column", "tag", "n", "gate", "entropy", "G_doc_bits", "sample_n"])
    w.writeheader()
    w.writerows(sample_rows)

with open(f"{OUT}/csv/stability_block.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["column", "tag", "n", "gate", "entropy", "G_doc_bits", "block_index"])
    w.writeheader()
    w.writerows(block_rows)

# ---- summary table: agreement rate of gate decision vs full-file gate, and G_doc stats per block ----
summary = []
for name in FULL_COLS:
    full_gate = [r for r in prefix_rows if r["column"] == name and r["prefix_n"] == len(full_cache[name])][0]["gate"]
    pref = [r for r in prefix_rows if r["column"] == name]
    samp = [r for r in sample_rows if r["column"] == name]
    blk = [r for r in block_rows if r["column"] == name]
    pref_agree = np.mean([r["gate"] == full_gate for r in pref])
    samp_agree = np.mean([r["gate"] == full_gate for r in samp])
    blk_agree = np.mean([r["gate"] == full_gate for r in blk])
    g_blk = np.array([r["G_doc_bits"] for r in blk])
    summary.append(dict(column=name, n_full=len(full_cache[name]), full_gate=full_gate,
                         prefix_agreement=pref_agree, sample_agreement=samp_agree,
                         block_agreement=blk_agree, n_blocks=len(blk),
                         G_doc_block_mean=float(np.nanmean(g_blk)) if len(g_blk) else float("nan"),
                         G_doc_block_std=float(np.nanstd(g_blk)) if len(g_blk) else float("nan")))

with open(f"{OUT}/csv/stability_summary.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(summary[0].keys()))
    w.writeheader()
    w.writerows(summary)

# ---- small figure: G_doc per block vs block index, one line per column, linear y from 0 ----
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(6.5, 3.2))
palette = ["#1b6fa8", "#c2572a", "#3c8a5b", "#8a5fbf", "#b0392f"]
for i, name in enumerate(FULL_COLS):
    blk = [r for r in block_rows if r["column"] == name]
    g = [r["G_doc_bits"] for r in blk]
    ax.plot(range(len(g)), g, label=name, color=palette[i % len(palette)], linewidth=1.0)
ax.set_ylim(bottom=0)
ax.set_xlabel("block index (64K rows/block)", fontsize=8)
ax.set_ylabel("G_doc (bits/value)", fontsize=8)
ax.tick_params(labelsize=8)
ax.legend(fontsize=7, ncol=3, loc="upper right", frameon=False)
fig.tight_layout()
fig.savefig(f"{OUT}/fig/fig_stability.pdf")
plt.close(fig)

dt = time.time() - t0
with open(f"{OUT}/README_S7.md", "w") as fh:
    fh.write("# S7 + G4: stability across prefixes, sample sizes and blocks\n\n")
    fh.write("Inputs (full local files, sha256 prefix of first 1MiB):\n")
    for name in FULL_COLS:
        sha = sc.sha256_prefix(sc.COLUMNS[name]["path"])
        fh.write(f"- {name}: `{sc.COLUMNS[name]['path']}` sha256[:12]={sha}, n={len(full_cache[name])}\n")
    fh.write("""
quadkey and uuidv7_hi full files are benchmark host-only and not available locally; skipped (matches plan D,
'full local files' row and 'Benchmark host unreachable' risk F.11).

Method: for each full column, (1) prefix sweep n=65536,131072,...,doubling up to the full file
length; (2) sample-size sweep n=128,512,2048,8192,32768,131072,524288,full, uniform random
subsample without replacement (seed 0), order preserved (sorted indices) so the flip statistic
stays meaningful; (3) per-64536-row-block pass over the whole file. For each (column, slice):
flip-profile gate decision (shipped admission test, study_common.gate_decision) and the
documented-field gain G_doc = C(x) - D_doc(x) bits/value (same statistic as S5).

Outputs:
- csv/stability_prefix.csv, csv/stability_sample.csv, csv/stability_block.csv (raw per-slice rows)
- csv/stability_summary.csv: column, n_full, full_gate, prefix_agreement, sample_agreement,
  block_agreement (fraction of slices whose gate decision matches the full-file gate),
  n_blocks, G_doc_block_mean/std
- fig/fig_stability.pdf: G_doc per 64K-row block vs block index, one line per column, linear y from 0

""")
    fh.write("## Summary\n\n")
    fh.write("| column | n_full | full_gate | prefix_agree | sample_agree | block_agree | n_blocks | G_doc mean (std) |\n")
    fh.write("|---|---|---|---|---|---|---|---|\n")
    for s in summary:
        fh.write(f"| {s['column']} | {s['n_full']} | {bool(s['full_gate'])} | {s['prefix_agreement']:.2f} | "
                  f"{s['sample_agreement']:.2f} | {s['block_agreement']:.2f} | {s['n_blocks']} | "
                  f"{s['G_doc_block_mean']:.3f} ({s['G_doc_block_std']:.3f}) |\n")
    fh.write(f"\nRuntime: {dt:.1f} s\n")
print("done", dt)
