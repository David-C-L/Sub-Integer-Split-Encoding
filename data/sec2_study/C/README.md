# Section 2 data-class study -- batch C (local, 2026-10-02)

Redo of parts of the Sec. 2 data-class study per the author's correction
(`paper_handover/proposals/18_reframe_plan.md` section H): characterise the DATA
(ALP Sec. 2 / PIDS style), do not apply SIS or any cost model. `A/` and `B/` (2026-10-01) are
kept unchanged; this batch adds new, separately-versioned outputs only. Local only (no benchmark host).
Nothing in `paper-repo/paper/` (the paper repo) was read or
edited.

Interpreter: `EncodingsPlayground/Datasets/.venv/bin/python` (numpy 2.4.2, pandas 3.0.1,
matplotlib 3.11.1). Rows: leading 524,288-row prefix of each column file, file order (same
convention as A/B).

Per-task READMEs (method, caveats, results):
- `README_C1.md` -- task 1: encoder-agnostic structure measure (replaces the DP-based gain `G`).
- `README_C2.md` -- task 2: data-based membership justification for the 5 PublicBI measure
  columns + instagram.
- `README_C3.md` -- task 3: decision to drop (not regenerate) `B/csv/gain_vs_nimble.csv`.

Top-level `../STUDY_SUMMARY.md` (task 4) indexes every finding from A/B/C against its evidence
file, separately from `../eval_from_study_runs.md` (SIS results, out of scope for Sec. 2).

## Scripts

- `scripts/structure_common.py` -- shared helpers: column registry (reuses
  `A/scripts/study_common.py`'s registry + two freshly-materialised controls), Miller-Madow
  entropy/joint-entropy/delta-entropy estimators, the flip-profile-gradient data-chosen
  partition rule. No cost model, no encoder.
- `scripts/c1_structure_measure.py` -> `csv/structure_measure.csv`, `csv/structure_summary.csv`.
- `scripts/c2_membership_justification.py` -> `csv/value_stats.csv`,
  `csv/order1_reduction_reliable_ranges.csv`, `fig/fig_order1_reduction.pdf`.
- (no script for C3: a decision note, not a regenerated table -- see `README_C3.md`.)

## Data

`data/hashed_splitmix64.txt`, `data/random_uint64.txt` -- regenerated locally by
`A/scripts/gen_unstructured_controls.py` (unchanged script; same splitmix64 stream / numpy
`default_rng(20261002)` seed `A` used, N=524,288). `A` never wrote these to disk (consumed
in-memory for `A/README_FP_COST.md`); this batch materialises them so C1/C2 can load them like
every other column.

## Known limitations (see README_C1.md/README_C2.md for detail)

- Order-1 conditional entropy and inter-range mutual information are only meaningful where
  flagged `reliable` (distinct, or distinct-pair, count <= N/50); every near-unique whole value
  or wide high-cardinality range is flagged unreliable by construction, not because it lacks
  structure.
- The whole-value-vs-sum-of-ranges `gain_bits` in `structure_summary.csv` mixes two different
  entropy estimators (order-0 vs. delta) depending on which is reliable per side, so it is not a
  strict bound; it is reported for completeness, and the headline result (README_C2.md) uses the
  single-estimator, reliable order-1-reduction comparison instead.
