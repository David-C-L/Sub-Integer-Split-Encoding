# E: floats in the Sec. 2 data-class study (study_20261001/E, 2026-10-02)

Scope: data-only characterisation of IEEE-754 double columns, following
`paper_handover/proposals/20_floats_alp_plan.md` section 2 (E1-E6; E7 skipped, optional
per the plan). No SIS, no Nimble, no cost model, no builds -- same framing as `C/` and `D/`.
Never edits `A/`, `B/`, `C/`, `D/`. Interpreter:
`EncodingsPlayground/Datasets/.venv/bin/python`.

**Reduced run**: the plan specifies 10 float columns + 1 control (F1-F10, C0). Disk space and
login-walled sources (Kaggle, NEON post-2026-06-30) meant only 4 of 11 were obtained this run:
F2 (Food-prices), F4 (Medicare1 TOTAL_DRUG_COST, local), F10 (Medicare1 computed ratio, local),
C0 (synthetic uniform control). See `Datasets/Floats/README.md` for the acquisition note and
`Datasets/Floats/MANIFEST.txt` for file-level provenance. This covers all three plan classes
(decimal-origin, high-precision, control) but is not the full battery; F1, F3, F5-F9 are absent.

## Columns

| name | class | source | n |
|---|---|---|---|
| F2_food_prices | decimal-origin | WFP food prices, `mp_price` | 524,288 |
| F4_medicare_total_drug_cost | decimal-origin | local Medicare1 TOTAL_DRUG_COST | 524,288 |
| F10_medicare_calc_9030826185528129 | high-precision | local Medicare1 computed ratio | 524,288 |
| C0_uniform_control | control | synthetic uniform double, no decimal structure | 524,288 |

IEEE 754 double layout used throughout (bit 0 = LSB): sign `[63,64)`, exponent `[52,63)`,
mantissa `[0,52)`.

## Fixed membership criteria (written before computing E6, verbatim from plan 20 section 2's
## E6 row, plus one explicit implementation choice needed to make "both compressors" concrete)

> (i) at least one reliable range with order-1 reduction > 0 that the shuffled copy loses
> (C2's test); (ii) E4 split gain > 0 under partition (b) or (c) for both compressors.

Implementation choices, fixed before running `e6_membership.py`:
- "reliable range" = `order1_reliable=True` in the per-range output (C1's `range_row`,
  reused unchanged via `e5_order1_entropy.py`), i.e. the joint-entropy estimate is not
  degenerate at N=524,288 (distinct count of the range small enough, same test C1/C2 use).
- "order-1 reduction > 0 that the shuffled copy loses" = file-order `order1_cond_entropy_bits`
  strictly less than the shuffled-order value on the same range, both `order1_reliable=True`.
- "both compressors" in (ii) = xz (preset 6) and zstd (-19), the two D1 treats as its primary
  measure (`D/scripts/d1_split_measure.py`'s docstring: LZ4/Snappy are the later-added "fast
  completeness" arms). Both must show `gain_pct_vs_whole > 0` under the same partition variant
  (SPLIT_FRONT_b or SPLIT_DATA_c) for (ii) to hold. LZ4/Snappy gains are still recorded in
  `csv/split_measure_float.csv` for context but are not part of the fixed test.
- Verdict: **member** if (i) AND (ii); **weak-member** if exactly one of (i), (ii);
  **non-member** if neither.

## Scripts and outputs

- `scripts/float_common.py`: `FLOATS` registry, IEEE layout, `load_floats`/`load_bits`.
  Imports `flip_profile`/`field`/`h_bin` from `A/scripts/study_common.py` and
  `counts_entropy`/`delta_entropy`/`data_chosen_partition` from
  `C/scripts/structure_common.py`, unchanged.
- `e1_flip_profiles.py` -> `csv/flip_profiles_float.csv`, `fig/fig_flip_float.pdf` (heatmap,
  rows grouped by class; IEEE boundaries at bit 52/63 marked). Also dumps
  `csv/e1_data_chosen_partitions.json` (data-chosen partition per column, k=2.0, reused by
  E4/E5).
- `e2_fields.py` -> `csv/float_fields.csv`, `fig/fig_float_exp_tz.pdf`. Exponent
  histogram/distinct/entropy; mantissa trailing-zero distribution; effective mantissa width
  (52 - median trailing zeros); leading-bits stability (number of top bits constant within
  each 1024-value vector), reported as both the median and the min over vectors
  (`leading_bits_stable_min`, used as `b` for E4/E5's front-bits partition -- the min is the
  number of bits guaranteed constant in *every* vector, the safe global split point).
- `e3_decimal_origin.py` -> `csv/decimal_origin.csv` (column,d,frac for d=0..18),
  `csv/decimal_vector_stats.csv` (per-1024-vector round-trip fraction at the chosen d),
  `csv/e3_chosen_d.json`. Minimal d reaching 99% round-trip; if never reached in d=0..18
  (true only for C0), flagged `reached_99=False` and the decimal-integer control (E4(d)) is
  marked not-meaningful for that column rather than computed on an overflowing cast.
- `e4_split_measure.py` -> `csv/split_measure_float.csv`. Reuses
  `D/scripts/d1_split_measure.py`'s compressors/byte-packing unchanged. WHOLE vs (a) IEEE
  sign/exp/mantissa, (b) front-bits at `b=leading_bits_stable_min` (degenerates to no-split
  when b=0, e.g. C0), (c) data-chosen from E1, and (d) `round(x*10^d)` as an int64 byte stream
  for E3's chosen d.
- `e5_order1_entropy.py` -> `csv/structure_measure_float.csv`. Reuses C1's `range_row`
  (order-0/delta/order-1 entropy, `*_reliable`) per range of partitions (a)/(b)/(c), file vs
  shuffled (seed 0).
- `e6_membership.py` -> `csv/membership_float.csv`. Applies the criteria above.
- `csv/table2_float_candidate_rows.csv`: one row per column, for the Sec. 2 Table 2 float row
  group (columns: exponent distinct/entropy, effective mantissa width, leading-bits-stable
  min, decimal d99, order-1-reduction-present, split-gain-pass, membership verdict).

## Results per column

| column | class | exp entropy (bits, MM) | eff. mantissa width | front-bits-stable (min) | decimal d99 | criterion (i) | criterion (ii) | verdict |
|---|---|---|---|---|---|---|---|---|
| F2_food_prices | decimal-origin | 3.65 | 9.0 | 1 | 4 (100% r.t.) | True (IEEE exp range, 79% reduction) | False | **weak-member** |
| F4_medicare_total_drug_cost | decimal-origin | 3.10 | 51.0 | 7 | 2 (100% r.t.) | True (IEEE exp range, 14% reduction) | False | **weak-member** |
| F10_medicare_calc_9030826185528129 | high-precision | 2.59 | 52.0 | 1 | 15 (87-100% r.t. per vector) | True (IEEE exp range, 38% reduction) | True (SPLIT_DATA_c, xz +0.1%, zstd +5.4%) | **member** |
| C0_uniform_control | control | 2.07 | 50.0 | 0 | 18, `reached_99=False` (not decimal-origin) | **False** (0% reduction on every reliable range, file vs shuffled identical) | True* (SPLIT_DATA_c, xz +3.3%, zstd +5.4%) | **weak-member*** |

\* **C0's criterion (ii) pass is a known artifact, not real structure.** Its data-chosen
partition (`data_chosen_partition`, k=2.0) cut 4 spurious ranges
(`[(0,1),(1,55),(55,63),(63,64)]`) on pure noise -- the same failure mode `STUDY_SUMMARY.md`
already documents for the integer controls ("the data-chosen partition rule in C1 ... cuts
noise on the unstructured controls (4-5 spurious ranges each)"). Criterion (i), the direct
order-1 file-vs-shuffled test, is unambiguous: C0 shows **exactly 0%** reduction on every
reliable range (sign bit 1.0 vs 1.0, exponent range 2.0704 vs 2.0704, identical to 4 decimal
places). Read C0 as a **non-member in substance**; its "weak-member" label is a mechanical
side-effect of a known partition-noise issue, not evidence of structure. If (ii) is read as
"all 4 compressors" instead of the 2 primary ones, C0 still passes (lz4 +0.8%, snappy +3.0%
also positive) -- the artifact is in the partition, not the compressor choice.

Per-column detail:

- **F2 (decimal-origin, 4-digit round-trip)**: exponent field (28 distinct values) carries a
  strong, reliable order-1 signal (79% conditional-entropy reduction, file vs shuffled) --
  front-bits structure is real and order-dependent. But it does **not** show up as positive
  split gain under the front-bits or data-chosen byte-partition for both xz and zstd (all
  negative or ~0) -- the per-value exponent variation is wide enough (std. dev., ALP's own
  flagged case) that a generic byte-stream compressor on the packed front-bits range doesn't
  beat compressing the whole word. E4(d), the decimal-integer control, is also negative for
  xz (-14.9%) though positive for zstd (+-2.2%) and strongly positive for lz4/snappy (+7-8%) --
  mixed, not the clean decimal win the plan predicted for this column.
- **F4 (decimal-origin, 2-digit round-trip, local)**: same pattern as F2 but weaker on
  criterion (i) (14% reduction) and also failing (ii). E4(d) is the column's clearest result:
  the decimal-integer control gives the largest, most consistent gain of any partition for
  any column here (+8.5% xz, +12.3% zstd, +24.7% lz4, +26.0% snappy) -- exactly the plan's
  prediction that decimal structure shows up in (d), not in (a)/(b)/(c).
- **F10 (high-precision, computed ratio, local)**: the only full **member**. Its exponent
  field is narrow (15 distinct values) and gives the strongest order-1 reduction (38%); its
  data-chosen partition (effectively a fine-grained split of the sign+exponent region, since
  `leading_bits_stable_min=1` means almost nothing is bit-exact across every 1024-vector) is
  the only partition in this run to pass criterion (ii) outright (positive for both primary
  compressors, and for lz4/snappy too). Decimal round-trip only reaches 99% at d=15 and is
  unstable per-vector (86.7%-100%), so E4(d) is a weak, inconsistent signal here (xz +7.2%,
  zstd +2.1%, lz4/snappy ~0) -- consistent with "high-precision, not decimal-origin".
- **C0 (control)**: non-member in substance (see above); zero order-1 structure on every
  reliable range, file vs shuffled.

## Does the hypothesis hold?

**Partially, and with a flip in which class is the cleaner front-bits case.** The plan's
hypothesis was: floats are members through front bits only; decimal origin, if detected at
all, should show up mainly in E4(d), not in E4(a)/(b)/(c).

- The **E4(d) >> E4(a)/(b)/(c) for decimal structure** half holds clearly for F4 (its best
  result by far is the decimal-integer control) and partially for F2 (mixed across
  compressors, but its best decimal signal is still (d), not a bit partition).
- The **"front bits only, cleanly" half is weaker than predicted for the two decimal-origin
  columns**: F2 and F4 both show a real, reliable order-1 signal in the IEEE exponent range
  (criterion i), confirming the front bits *carry* structure, but neither one converts that
  into a positive generic-compressor split gain (criterion ii) -- on this reduced 4-column
  sample, the front-bits structure in decimal-origin floats is visible to the order-1 entropy
  test but not (yet) exploitable by a naive byte-range compressor split, landing them at
  **weak-member** rather than the plan's predicted clean front-bits membership.
- The high-precision column (F10), which the plan expected to be a weak member or near-miss,
  is instead the one column that is a **full member** by both criteria -- its narrow exponent
  field and near-maximal-entropy mantissa still produce an exploitable front/data-chosen split.
- The control (C0) correctly separates out under the direct, non-partition-dependent test
  (criterion i), as predicted, though the partition-dependent test (ii) has a known false
  positive from the same data-chosen-partition noise issue already flagged for the integer
  study.

**Caveat on generality**: this is 3 non-control columns (2 decimal-origin, 1 high-precision),
not the plan's 10. The flip in which class looks "cleanest" could easily reverse with F1/F3
(wider exponent variance, the ALP cases where Zstd already beats ALP) or F5-F9 (sensor data,
narrower exponent range, long runs) in the sample. Treat this section's verdicts as
column-specific results, not yet a validated statement about "decimal-origin floats" or
"high-precision floats" as classes.

## Runtime

E1: ~5s. E2: ~3s. E3: ~1s. E4: ~95s (4 compressors x 4 partitions x 4 columns, xz/zstd-19
dominate). E5: ~50s. E6: <1s. Total well under the plan's time estimate, all local, no benchmark host.
