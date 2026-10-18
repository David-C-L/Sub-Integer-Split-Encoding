"""Follow-up 1: gate-decision agreement at the planner's actual sampler config.

Shipped sampler (velox-fork-for-nimble, evaluation branch head,
velox/dwio/nimble/encodings/subintsplit/Sampler.h, read-only):
  SamplerConfig{ maxSamples = 2048, blockSize = 128 }  (defaultSamplerConfig())
  sampleIntoU64WithRows, blockSize>0 branch: numBlocks = max(1, target/blockSize) = 16,
  blockStride = max(1, n/numBlocks) = n/16, then for each of 16 blocks takes rows
  [b*blockStride, b*blockStride+128) -- i.e. 16 CONTIGUOUS 128-row blocks spread evenly
  across the file by a fixed stride. This is deterministic, not random, for a fixed n:
  there is exactly one planner sample per column. To report an agreement RATE (the
  coordinator's ask: ">=50 random 2,048-row samples drawn the way the planner samples"),
  we reproduce the same block-stratified scheme (16 x 128-row contiguous blocks, stride
  n/16) but jitter the phase: each of the 50 draws (seed 0..49) picks a uniform random
  start offset in [0, blockStride-128) before laying down the 16-block grid, i.e. "the
  planner's sample, as if the file had been rotated by a random amount." This is NOT what
  the shipped sampler itself does (it is phase-fixed at offset 0); it is our way of turning
  the planner's deterministic scheme into a distribution for a stability check. Documented
  explicitly so it is not mistaken for shipped randomness.
"""
import csv
import time

import numpy as np

import study_common as sc

OUT = "$PROJECT/paper-repo/study_20261001/A"
N_PREFIX = 524288
N_DRAWS = 50
MAX_SAMPLES = 2048
BLOCK_SIZE = 128
NUM_BLOCKS = MAX_SAMPLES // BLOCK_SIZE  # 16
t0 = time.time()


def planner_sample(values, rng):
    n = len(values)
    block_stride = max(1, n // NUM_BLOCKS)
    max_offset = max(1, block_stride - BLOCK_SIZE)
    offset = int(rng.integers(0, max_offset)) if max_offset > 1 else 0
    idx = []
    for b in range(NUM_BLOCKS):
        start = offset + b * block_stride
        end = min(start + BLOCK_SIZE, n)
        if start >= n:
            break
        idx.extend(range(start, end))
    idx = np.array(idx[:MAX_SAMPLES], dtype=np.int64)
    return values[idx]


def gate_of(values):
    p = sc.flip_profile(values)
    ok, f = sc.gate_decision(p)
    return ok


rows = []

# (a) full S7 columns, at full length
FULL_COLS = ["snowflake", "xmark", "h3_r9", "publicbi_npi", "instagram"]
for name in FULL_COLS:
    cfg = sc.COLUMNS[name]
    import pandas as pd
    v = pd.read_csv(cfg["path"], header=None, dtype="uint64", usecols=[0]).iloc[:, 0].to_numpy()
    full_gate = gate_of(v)
    agree = 0
    for seed in range(N_DRAWS):
        rng = np.random.default_rng(seed)
        s = planner_sample(v, rng)
        if gate_of(s) == full_gate:
            agree += 1
    rows.append(dict(column=name, scope="S7_full", n_full=len(v), full_gate=int(full_gate),
                      n_draws=N_DRAWS, agreement=agree / N_DRAWS))

# (b) every G1-labelled column, at the 524,288-row prefix (or full if shorter)
for name in sorted(sc.COLUMNS.keys()):
    v = sc.load(name, n=N_PREFIX)
    full_gate = gate_of(v)
    agree = 0
    for seed in range(N_DRAWS):
        rng = np.random.default_rng(seed)
        s = planner_sample(v, rng)
        if gate_of(s) == full_gate:
            agree += 1
    rows.append(dict(column=name, scope="G1_524k", n_full=len(v), full_gate=int(full_gate),
                      n_draws=N_DRAWS, agreement=agree / N_DRAWS))

with open(f"{OUT}/csv/g4b_planner_sampler_agreement.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["column", "scope", "n_full", "full_gate", "n_draws", "agreement"])
    w.writeheader()
    w.writerows(rows)

dt = time.time() - t0
with open(f"{OUT}/README_G4b.md", "w") as fh:
    fh.write(f"""# Follow-up 1: gate-decision agreement at the planner's sampler config

Shipped sampler: `velox-fork-for-nimble` evaluation branch head,
`velox/dwio/nimble/encodings/subintsplit/Sampler.h`, `defaultSamplerConfig()` =
`{{maxSamples: 2048, blockSize: 128}}`. `sampleIntoU64WithRows` with `blockSize>0` lays down
`numBlocks = max(1, target/blockSize) = 16` CONTIGUOUS 128-row blocks at fixed stride
`n/16` across the file (block-stratified, deterministic, not uniform-random rows) -- confirmed
by reading the source (read-only, no edits). For a fixed column length this gives exactly one
planner sample, so "agreement across >=50 random samples" is reported here by jittering the
16-block grid's phase (random start offset in [0, n/16 - 128), seed 0..49 via
`numpy.random.default_rng(seed)`) and re-running the shipped flip-profile gate on each draw,
comparing to the full-column gate decision. This jitter is our construction, not shipped
randomness (documented in g4b_planner_sampler.py).

Inputs: S7's 5 full local files (full length) + all 22 study_common.COLUMNS at the 524,288-row
prefix (G1's labelled set). {N_DRAWS} draws per column.

Output: csv/g4b_planner_sampler_agreement.csv (column, scope, n_full, full_gate, n_draws, agreement).

Runtime: {dt:.1f} s
""")
print("done", dt)
for r in rows:
    print(r["column"], r["scope"], r["agreement"])
