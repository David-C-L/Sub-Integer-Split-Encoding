# Follow-up 1: gate-decision agreement at the planner's sampler config

Shipped sampler: `velox-fork-for-nimble` evaluation branch head,
`velox/dwio/nimble/encodings/subintsplit/Sampler.h`, `defaultSamplerConfig()` =
`{maxSamples: 2048, blockSize: 128}`. `sampleIntoU64WithRows` with `blockSize>0` lays down
`numBlocks = max(1, target/blockSize) = 16` CONTIGUOUS 128-row blocks at fixed stride
`n/16` across the file (block-stratified, deterministic, not uniform-random rows) -- confirmed
by reading the source (read-only, no edits). For a fixed column length this gives exactly one
planner sample, so "agreement across >=50 random samples" is reported here by jittering the
16-block grid's phase (random start offset in [0, n/16 - 128), seed 0..49 via
`numpy.random.default_rng(seed)`) and re-running the shipped flip-profile gate on each draw,
comparing to the full-column gate decision. This jitter is our construction, not shipped
randomness (documented in g4b_planner_sampler.py).

Inputs: S7's 5 full local files (full length) + all 22 study_common.COLUMNS at the 524,288-row
prefix (G1's labelled set). 50 draws per column.

Output: csv/g4b_planner_sampler_agreement.csv (column, scope, n_full, full_gate, n_draws, agreement).

Runtime: 77.2 s
