# C1: encoder-agnostic structure measure (2026-10-02)

Per the author's correction (`proposals/18_reframe_plan.md` section H): replaces the DP/cost-model
gain `G` from `study_20261001/B/csv/membership.csv` with a measure that only ever looks at the
data (empirical entropies, flip profiles, order). No encoder, no cost model, no SIS anywhere in
this script.

Script: `scripts/c1_structure_measure.py` (+ shared helpers `scripts/structure_common.py`).
Interpreter: `EncodingsPlayground/Datasets/.venv/bin/python` (numpy 2.4.2, pandas 3.0.1).
Rows: leading 524,288-row prefix (or full file if shorter) of each column, file order, same
convention as `A/` and `B/`. 24 columns: the 22 in `A/scripts/study_common.py`'s registry (T1-T4
structured/near-miss + 6 original controls) plus `hashed_splitmix64`/`random_uint64`, freshly
regenerated here (`C/data/*.txt`) by `A/scripts/gen_unstructured_controls.py` unchanged (same
splitmix64/numpy-seed-20261002 generator A used; A never wrote these to disk, consuming them
in-memory for `A/README_FP_COST.md`).

## Method

**Partitions.** Two bit-range partitions of each 64-bit value, each a set of contiguous
half-open ranges covering `[0,64)`:
- **(a) documented**, from the registry's `layout` list, where one exists (12/24 columns; the
  other 12 have no documented layout and are skipped for this partition).
- **(b) data-chosen**, from the adjacent-row bit-flip profile alone (`p[b]`, `b=0..63`, same
  profile `A/scripts/study_common.py:flip_profile` already uses for the admission gate): compute
  the gradient `g[b] = |p[b]-p[b-1]|`, threshold `thr = mean(g[1:]) + 2*std(g[1:])` (`k=2.0`, the
  same multiplier the shipped admission gate uses for its own boundary count feature -- reused
  here only as a threshold constant, not as a gate/cost decision), cut at every `b` with
  `g[b] > thr`. This never touches cardinality, run length, or any encoder cost; it is a function
  of the flip profile only.

**Entropies.** For every range (and for the whole 64-bit value as a one-range baseline):
- order-0 empirical Shannon entropy of the range's integer values, with the Miller-Madow bias
  correction `H_mm = H_naive + (K-1)/(2N ln2)` (K = distinct values observed, N = 524,288).
- a **delta-entropy** fallback: order-0 entropy (+ Miller-Madow) of the first difference of
  consecutive values (plain integer subtraction, no modular wraparound).
- **reliability rule** (B's convention, `study_20261001/B/README.md`, S4/G5 section: "distinct
  count <= N/50, i.e. average multiplicity >= 50"): a range's order-0 estimate is `reliable` iff
  its distinct-value count <= 10,485.76. The **entropy proxy** used in `gain_bits` is the order-0
  estimate if reliable, else the delta estimate (flagged `entropy_proxy_source`); even the delta
  estimate is flagged unreliable if its own distinct-delta count exceeds the same threshold.
- **order-1 conditional entropy** `H(X_t|X_{t-1}) = H_joint(X_{t-1},X_t) - H(X_{t-1})` (both terms
  Miller-Madow corrected), reliability = joint-pair distinct count <= N/50.
- **mutual information** between each range and the next range in the partition (same row,
  `MI = H(R_i)+H(R_{i+1})-H_joint(R_i,R_{i+1})`), same reliability rule on the joint pair count.

Outputs: `csv/structure_measure.csv` (one row per range: both partitions + the whole-value
baseline, every quantity above) and `csv/structure_summary.csv` (one row per column per
partition: `gain_bits = whole_value_entropy_proxy - sum(range_entropy_proxy)`).

## Central caveat: what's actually reliable at N=524,288

Every structured/near-miss column's **whole value** and every **wide, high-cardinality** range
(e.g. any timestamp-like field) has distinct count within 1-2 of N -- by construction, for
*any* sequence of near-unique values (structured or pure noise), order-0 entropy plug-in gives
H~log2(N) and the order-1 joint over near-unique pairs gives H_joint~log2(N) too, so the naive
`order1_cond_entropy ~ 0` **regardless of real structure**. This is not a finding; it is a known
degeneracy of plug-in entropy at small N relative to a huge support, and it is why every one of
these cells is flagged `order1_reliable=False` / `mi_reliable=False` in the CSV. **Do not read
"order1_cond_entropy≈0 for structured and control high-cardinality ranges" as "no difference" --
it is uninformative there by construction.** The delta-entropy estimator does resolve the
whole-value / wide-range *order-0* picture somewhat (e.g. snowflake's whole-value delta-entropy
19.72 bits is well below its order-0 proxy sum of 28.14 bits across the documented partition --
but this comparison mixes two different estimators across the two sides and is flagged
`gain_bits` **approximate, not a bound**: entropy is strictly subadditive only when the *same*
estimator is used on both sides of the partition; mixing order-0 and delta-of-whole-value breaks
that property, visible in that even the two unstructured controls (hashed_splitmix64,
random_uint64) show large *negative* `gain_bits` (-23.7, -20.7) under the data-chosen partition,
more negative than most structured columns -- so `gain_bits` is reported for completeness
(`csv/structure_summary.csv`) but is **not** the headline comparison; see C2 for the reliable one.

## What is reliable, and what it shows

Restricting to ranges flagged `order0_reliable=True` AND `order1_reliable=True` (distinct count,
and distinct-pair count, both <= N/50 -- genuinely low-cardinality fields/sub-fields):

- **Controls never show order-1 reduction.** Every reliable range of `hashed_splitmix64`,
  `random_uint64`, `uuidv7_lo`, `publicbi_npi` has `order1_cond_entropy_bits == order0_entropy_mm_bits`
  to within rounding (e.g. `random_uint64[0,3)`: 3.000 -> 3.000; `hashed_splitmix64[61,64)`: 3.000
  -> 3.000), i.e. zero measurable adjacent-row dependency, and entropy at or near the field's
  maximum possible (`width` bits) -- exactly the signature of an unstructured/random sub-field.
- **Structured/near-miss columns show a measurable, reliable reduction** on at least one
  low-cardinality range: xmark's 1-bit `level` field at bit 56, order0 0.997 -> order1_cond 0.656
  (34% reduction); `publicbi_day_supply_bin`'s bits [0,4) 3.890->3.675 and bit [4,5) 0.996->0.741;
  snowflake's `seq`/`worker` fields are reliable in order-0 but their order-1/MI cells are *not*
  reliable (too many distinct pairs) -- suggestive only, not claimed as a finding here (see C2's
  table for the full per-target numbers, which uses this same reliable-range rule).
- **Mutual information between adjacent ranges** is informative only where the joint-pair count
  is also <= N/50; most structured columns' field-pairs fail this (too many combinations even
  when each field alone is low-cardinality), so MI is reported in `structure_measure.csv` for
  completeness but not used as a headline claim here; `xmark[56,57)-[57,64)` is one of the few
  `mi_reliable=True` cells (MI=0.0497 bits, weak).

Table (columns x measures) is `csv/structure_measure.csv` (per-range) +
`csv/structure_summary.csv` (per-column roll-up); read with the reliability flags, not in
isolation -- an unflagged cell is a number, not a claim.

## Known limitations

- The data-chosen partition rule (`k=2.0` gradient threshold) is a simple, stated, reproducible
  rule, not a validated general change-point detector; it occasionally cuts noise (both synthetic
  controls get 4-5 "ranges" from flip-profile sampling variance at 64 bins), which is itself
  reported (not hidden) and is part of why `gain_bits` is not the headline number.
- `gain_bits` mixes order-0 and delta estimators across the two sides of the equality and should
  not be read as a bound (see caveat above); C2's order-1-reduction figure is the defensible
  headline result from this batch.
- No second-order (lag-2+) structure, no cross-column structure, and no float/IEEE-754 bit
  decomposition are measured in this batch.
