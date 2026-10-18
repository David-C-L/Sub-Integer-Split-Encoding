# G: second membership condition + grouped Table 1 (study_20261001/G, 2026-10-02)

Scope: closes draft `21_section2_draft.md` TODO 3 (sequential controls `tpch_orderkey`
66.3%, `publicbi_id1` 51.0% pass the order-1 test alone) and builds the grouped Table 1 variant
(task 2). No SIS. Never edits `C/`, `D/`, `E/`, or the paper repo. Reuses `C/scripts/structure_common.py`
and `C/csv/structure_measure.csv` unchanged.

## Condition 2, fixed BEFORE computing

Condition 1 (already shipped, draft section (b) "Operational definition and its test") admits a
column on adjacency alone: a positive order-1 conditional-entropy reduction on the lowest-cardinality
reliable bit range. This is necessary but not sufficient -- a monotonic counter's low bits toggle
in lock-step with the previous row (large order-1 reduction) even though the counter carries no
per-field value structure at all.

**Condition 2 (value structure): on the SAME range used for Condition 1, the range's own order-0
distribution must be measurably non-uniform.** Concretely: `deficit_bits = log2(distinct) -
order0_entropy_mm_bits` on that range; the column passes Condition 2 if `deficit_bits >= 1.0` (the
range's values are at least 1 bit away from the maximum-entropy distribution over its own observed
support). This is a property of the multiset of values in the range, invariant to row order --
unlike Condition 1, shuffling the rows cannot change it.

Rationale for picking the order-0-deficit form over the shuffle form: a shuffle test on order-1
reduction ("recompute reduction on a row-shuffled copy, require it to vanish") does not separate
members from the sequential-counter false positives, because BOTH lose their order-1 reduction
under a random shuffle -- shuffling destroys any row-to-row adjacency effect, real or artifactual.
(This is visible directly in `E/README_E.md`'s own criterion (i), which requires genuine float
members to LOSE their order-1 reduction when shuffled.) The discriminating fact is instead in the
range's marginal distribution: a counter's low bits are, by construction, close to uniformly
distributed over their own support (incrementing a counter visits all residues roughly equally
often), while a genuine field (a worker id, a shard id, a measure bin) is usually concentrated on
a subset of its domain. We therefore run the shuffle test too, but only as a **confirmatory
diagnostic** (it should show the order-1 reduction vanishing for every column with real adjacency
dependence, member or control alike -- a sanity check that the Condition-1 signal is a genuine
row-to-row effect, not noise) -- never as the discriminator.

**Combined membership**: Condition 1 AND Condition 2 (both on the same data-chosen range: lowest-
cardinality range with `order1_reliable=True` and `order0_entropy_mm_bits > 0`, i.e. TODO 2's
already-used selection rule, applied uniformly to all 24 columns -- not only the 10 covered by
`C/csv/order1_reduction_reliable_ranges.csv`).

## Floats

Reuses `E/README_E.md`'s criteria unchanged (criterion i = file-vs-shuffled order-1 reduction on a
reliable range; criterion ii = generic-compressor split gain under both xz and zstd). Condition 2
(order-0 deficit) is additionally reported on the same exponent range E already used, for
cross-checking only -- the float verdict itself stays E's (member/weak-member/non-member), not
reclassified here.

## Outputs

- `scripts/g1_second_condition.py` -> `csv/second_condition.csv` (one row per column: range,
  distinct, order0 bits, uniform expectation, deficit, Condition-1/2/combined pass, shuffle
  diagnostic, documented label, combined vs. documented confusion).
- `scripts/g2_grouped_table.py` -> `table1_grouped.tex`, `table1_percolumn_appendix.tex` (task 2).

(Results and the confusion matrix are appended below the fixed criteria, after computation --
nothing above this line was altered after running the scripts.)

## Results

Condition 2 is evaluated over the WHOLE per-range profile of the data-chosen partition (not
just Condition 1's lowest-cardinality range: a single bit caps the achievable deficit at 1 bit
and is rarely where a measure's skew actually lives). It picks the range with the largest
relative deficit `1 - order0_mm/log2(distinct)` among ranges with `order0_reliable=True` and
`distinct>=4`, and passes at `relative_deficit >= 0.2` (20%). Full numbers:
`csv/second_condition.csv`.

**Confusion against the documented labels (combined Condition 1 AND Condition 2): TP=6, FN=10,
FP=0, TN=8.** Zero false positives -- every one of the 8 documented controls is excluded,
including both named sequential controls:

- `tpch_orderkey`: Condition 1 passes (18.9% reduction on bit [0,1)) but Condition 2 fails (no
  reliable range with `distinct>=4` reaches 20% relative deficit) -- **now excluded**.
- `publicbi_id1`: Condition 1 passes (4.8% on bit [18,19)) but Condition 2 fails likewise --
  **now excluded**.
- `inat_species_id`: same pattern (24.0% / fails Condition 2) -- also excluded, not previously
  flagged as a problem but confirms the fix generalises.

The 10 false negatives are the 9 documented-layout (T1-T3) structured columns minus `instagram`
and `xmark` (both now pass), plus `publicbi_day_supply_bin`. Five of those nine (`uuidv7_hi`,
`h3_r9`, `h3_r15`, `quadkey`, plus `snowflake`/`s2_l16`/`s2_l30` which have no Condition-1 range
at all) fail Condition 2, not Condition 1 -- their documented fields exist and show adjacency
dependence, but the data-chosen partition's most-skewed reliable range doesn't clear the 20%
threshold at N=524,288. Read these as "Condition 2, as specified, is conservative on this
sample size" rather than as evidence the columns lack structure (their layouts are documented,
unlike the controls). `publicbi_day_supply_bin` is the one near-miss that flips: it passes
Condition 1 (25.6%) but fails Condition 2 because the automatic data-chosen partition does not
isolate a sufficiently skewed range for it -- the same partition-noise issue `STUDY_SUMMARY.md`
already flags for the integer controls. Its membership by `value_stats.csv` (94% top-20
concentration) is untouched by this; it is a test artifact, not a reversal.

**Morton (`morton_2x16`, `morton_2x32`): both fail Condition 2 (relative deficit ~0 on every
qualifying range)**, consistent with the by-construction argument (interleaved coordinates, no
contiguous cut sees anything but the shared prefix) and with D's xz SPLIT_DOC result
(+0.0%). This resolves the draft's open choice 4: Morton is confirmed non-member, not merely
argued, and the earlier contradiction (F's positive data-chosen split gain) is no longer in
tension with the membership label -- a column can gain from a per-byte split under a generic
compressor without its values showing bit-range structure by this test.

**Floats**: the order-0 deficit does not discriminate (the synthetic uniform control `C0` shows
50% relative deficit on its own exponent range too -- an artifact of any bounded-magnitude
double, not evidence of structure). `E/README_E.md`'s file-vs-shuffled criterion is the right
test for floats and is kept unchanged: F10 full member, F2/F4 weak-member, C0 non-member in
substance.

## Table 1, grouped variant (task 2)

`table1_grouped.tex` (7 rows: T1-T4, near-misses, controls, floats) replaces the per-column
table as the in-body default; `table1_percolumn_appendix.tex` (24 rows, Member column updated
per the results above) becomes the optional appendix block.

**Column-space estimate**: the per-column table is 24 data rows + header/rule, `footnotesize`,
estimated at ~0.5 column in the draft's own page estimate. The grouped table is 7 data rows +
header/rule + one footnote line, roughly 0.15 column. **Estimated saving: ~0.35 column (~70%
reduction)** in the main body; the per-column table still costs ~0.5 column but moves to an
appendix, which is typically outside the page-limit-relevant body count.
