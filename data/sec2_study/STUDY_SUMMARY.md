# Section 2 data-class study -- findings index (2026-10-02)

Scope: Sec. 2 characterises the DATA (ALP Sec. 2 / PIDS style). No SIS result belongs here.
**SIS/compression results live separately in `eval_from_study_runs.md` and `eval_from_study_runs/`
-- do not merge the two.** Batches `A/` and `B/` are the earlier (2026-10-01) local work; `C/`
(2026-10-02) is the re-do that removes the cost-model-based DP gain `G` and replaces it with an
encoder-agnostic entropy measure, per the author's correction (`proposals/18_reframe_plan.md`
section H). Old `A/`/`B/` outputs are kept as-is; nothing in them was edited.

## Findings, each with its evidence file

1. **22+2 local columns profiled by adjacent-row bit-flip probability.** `A/csv/flip_profiles.csv`,
   `A/README_S1.md`. Controls mostly show a flat ~0.5 profile; structured/near-miss columns show
   field-shaped profiles.
2. **Instagram's scraped-order flip profile looks unstructured (~0.5) but its values are not.**
   `A/csv/order_sensitivity.csv`, `A/README_S5.md` (qualitative: sorting by the documented leading
   field drops active-entropy from 0.822 to 0.694) and `C/README_C2.md` / `C/csv/order1_reduction_reliable_ranges.csv`
   (quantitative: order-1 conditional entropy on a 5-bit reliable range drops 82% vs. the
   previous row's value; every control shows 0% on its own reliable range). **Still open:**
   neither analysis fully separates "order artifact" from "value structure" below the leading
   field; treat the 82% figure as the current best quantitative evidence, not a settled bound.
3. **Gate decision (old DP/cost-model admission test) is stable across row prefixes/blocks, less
   so across tiny random samples.** `A/csv/stability_*.csv`, `A/README_S7.md`. 100% stable on
   64K-row blocks and prefixes for all 5 full-file columns tested; 0.38-1.00 agreement on random
   subsamples of 128-2048 rows. **This result still references the old shipped admission gate
   (gradient+entropy_max=0.8), which is itself a cost/threshold artifact, not a pure data
   measure -- read it as a robustness check on an existing test, not as part of the new C1/C2
   data characterisation.**
4. **The old gate, as a classifier against documented labels, has precision 0.60 / recall 0.82.**
   `A/csv/g1_classifier_labels.csv`, `A/csv/g1_threshold_sweep.csv`, `A/README_G1.md`. False
   positives are exactly the 5 PublicBI measure columns + tpch_orderkey; false negatives are
   instagram (order artifact, see finding 2) and quadkey. **Superseded in spirit by C1/C2**: the
   new entropy-based measure doesn't use this gate at all, but this number documents why the old
   gate alone could not be the membership test.
5. **Per-field additive order-0 entropy is not a lower bound on achievable size.** `B/README.md`
   (S4 section), e.g. xmark's additive per-field entropy (40.8 bpv) sits *above* every measured
   baseline (best 2.41 bpv) because of the strong post-pre correlation (r=0.95,
   `B/csv/field_stats.csv`). This motivated the switch (in C1) to also reporting mutual
   information between adjacent ranges rather than only additive per-range entropy.
6. **New encoder-agnostic structure measure (C1): per-range order-0/order-1/delta entropy +
   inter-range MI, documented and data-chosen partitions, 24 columns.**
   `C/csv/structure_measure.csv`, `C/csv/structure_summary.csv`, `C/README_C1.md`. **Central,
   load-bearing caveat**: at N=524,288, any near-unique whole value or wide high-cardinality
   range gives a degenerate order-1 conditional entropy (~0, regardless of real structure) by
   construction -- flagged `*_reliable=False` throughout, and must not be read as "no
   structure". The summary-level `gain_bits` (whole-value vs. sum-of-ranges) mixes two different
   estimators across its two sides and is **not reliable** either (both synthetic controls show
   more negative `gain_bits` than most structured columns) -- reported for completeness only,
   not as a headline result.
7. **The one reliable, headline structure signal: order-1 conditional-entropy reduction on each
   column's lowest-cardinality reliable bit range.** `C/csv/order1_reduction_reliable_ranges.csv`,
   `C/fig/fig_order1_reduction.pdf`, `C/README_C2.md`. All 4 controls (`hashed_splitmix64`,
   `random_uint64`, `uuidv7_lo`, `publicbi_npi`) show **exactly 0%** reduction; all 6 targets
   (5 PublicBI measure columns + instagram) show a **positive, reliable** reduction, 1.6%-82%.
   This is the cleanest, most defensible reliable result in the whole study and is the
   recommended citation for "the class is defined by compressible/dependent bit-range structure,
   not documented fields" in Sec. 2.
8. **Value-statistics justification for the 5 PublicBI measure columns + instagram.**
   `C/csv/value_stats.csv`, `C/README_C2.md`: cents-scale/narrow-magnitude ranges (30/29-bit
   value ranges, 34-35/64 never-flip bits) for the two drug-cost columns; small sets of
   low-order distinct values with heavy top-20 concentration (40-94% of rows) for
   bene_count/num_employees/day_supply_bin, contrasted with `publicbi_npi` (similar or lower
   cardinality, 0.4% top-20 concentration, no such behaviour) as the matched negative control;
   66.5%/17.2% immediate-row repeats (runs) for num_employees/day_supply_bin vs. <=0.3% for every
   control.
9. **`gain_vs_nimble.csv` (B) is dropped, not regenerated.** `C/README_C3.md`: its Python-side
   numbers are cost-model artifacts (not encoder-agnostic, independent of the Nimble-side
   question), and a true non-SIS Nimble default is only available locally for 7 of its 15
   columns (`B/csv/blank_cells_measured.csv`) -- the other 8 would need new benchmark host measurement,
   which is evaluation-side work, not data characterisation.
10. **PIDS-style generic-compressor split measure (D): a real compressor rarely rewards the
    documented or data-chosen split, and almost never rewards it on controls.** `D/csv/split_measure.csv`,
    `D/table_split_measure.tex`, `D/fig/fig_split_gain.pdf`, `D/fig/fig_split_gain_compressors.pdf`,
    `D/README.md`. Four generic, off-the-shelf byte-stream compressors (xz/LZMA preset 6, zstd
    level 19, LZ4 frame default, Snappy -- the latter two added for completeness, confirmed
    dominated by zstd on WHOLE for 24/24 columns as expected) compress each of the 24 columns
    whole vs. split under the documented layout (SPLIT_DOC) and under C1's data-chosen
    flip-gradient partition (SPLIT_DATA, same partitions, byte-for-byte). Under xz: structured
    SPLIT_DOC mean +4.1% (range -1.6%..+24.1%, 13 columns with a layout), structured SPLIT_DATA
    mean -3.9% (-30.6%..+27.0%), control SPLIT_DATA mean -12.2% (-57.9%..-0.0%, all 8 controls
    <=0%, as expected). Only 4 columns (xmark, uuidv7_hi, snowflake, s2_l16) show a clear,
    compressor-independent positive split gain (best SPLIT > 0 under xz, zstd, LZ4 and Snappy;
    corrected 2026-10-03: instagram is -2.4%/-1.7% under LZ4/Snappy, s2_l16 is +7.9/+4.8/+5.4/+15.1); for most structured/near-miss columns a generic
    compressor's whole-stream match-finder already captures the redundancy the split would
    expose, so the split's main visible effect is per-stream header/dictionary-reset overhead
    (worst on BIT_PLANE, up to 64 streams). **One surprise**: under zstd (not xz), one control,
    `tpch_orderkey` (a monotonic sequential id with no documented layout), shows a *positive*
    SPLIT_DATA/BYTE_PLANE gain (+44.7%/+67.0%) because xz's LZMA already compresses its raw
    monotone sequence far better as one stream (1.29 vs. 3.77 bits/value on WHOLE) than zstd
    does at level 19 -- a compressor-capability artifact, not a reclassification of
    `tpch_orderkey`; every other control stays <=0% under every compressor. This is a
    complementary, independent-measure cross-check on finding 7/C2's entropy-based result, not
    a replacement for it: the two measures agree on direction for the controls (never positive,
    `tpch_orderkey`/zstd aside) and on the strongest structured columns (xmark, uuidv7_hi,
    instagram, snowflake) but disagree on magnitude and on several mid-table structured columns
    (e.g. morton_2x16, quadkey show large *negative* generic-compressor split gain despite
    documented structure) -- expected, since a real LZ77+entropy-coder's match-finder and an
    order-0/1 entropy estimator are measuring different things.

11. **Generic row-addressable fixed-width layouts (F): bit-range knowledge helps, but only a
    fraction of what a non-addressable generic compressor captures.** `F/csv/addressable_layouts.csv`,
    `F/table_addressable_layouts.tex`, `F/fig/fig_addressable_vs_xz.pdf`, `F/README.md`. Four
    textbook O(1)-row-access layouts (fixed bit width, FOR global, FOR per-1024-row block,
    dictionary+fixed-width code -- no SIS, no planner, no cost model, no Nimble encoder),
    computed per bit range (SPLIT_DOC/SPLIT_DATA, same partitions as C1/D) vs. per whole value
    (WHOLE_best), on the same 24 columns/524,288 rows. SPLIT_DATA over best-WHOLE-addressable:
    structured +17.6% mean (-0.1%..+58.2%, best on xmark), near_miss -2.6%, control -3.8% (all
    <=0%, as expected); SPLIT_DOC (documented partition) weaker, +7.6% structured mean, because
    some documented field boundaries don't align with where FOR/DICT actually save bits. Against
    this, `xz_WHOLE` (reused unchanged from D) is smaller than best-WHOLE-addressable by +52.0%
    mean on structured columns, +30.7% near_miss, and **+21.4% even on controls** (vs. <=0% for
    any addressable SPLIT on controls) -- xz's LZ77 match-finder exploits incidental
    regularities (e.g. `tpch_orderkey`'s monotone run, +87.7%) that no fixed-width per-row slot
    can represent, addressable or not. **Headline trade-off**: knowing the bit ranges measurably
    helps a row-addressable layout, but recovers only part of the redundancy a heavyweight,
    non-addressable compressor already captures "for free" at the cost of giving up O(1) random
    access -- consistent in direction with finding 10 (D), with a bigger addressable-vs-xz gap
    than D's SPLIT-vs-WHOLE gap since D's generic compressors were already in the non-addressable
    regime on both sides of their comparison.

12. **Floats (IEEE-754 doubles), full run, 10 real columns + C0 control (updated 2026-10-02, v2).**
    `E/README_E.md`, `E/csv/membership_float_v2.csv`, `E/csv/structure_measure_float_v2.csv`,
    `E/csv/split_measure_float_v2.csv`, `E/csv/table2_float_candidate_rows_v2.csv`. Per plan 20
    section 2 (E1-E6; E7 skipped). All 11 of the plan's float columns plus the control are now
    present (`Datasets/Floats/txt/`, sha256-checked against `MANIFEST.txt`): F1 Stocks-USA, F2
    Food-prices, F3 Gov/10, F4 Medicare1 TOTAL_DRUG_COST (decimal-origin); F5 City-Temp, F6
    Air-Pressure, F7 Dew-Point-Temp (sensor, a class added this run); F8 POI-lat, F9 NYC/29, F10
    Medicare1 computed ratio (high-precision); C0 synthetic uniform control. The pre-existing
    4-column (F2/F4/F10/C0) outputs are kept unsuffixed for provenance; `_v2` suffixes are the
    full run. `E/scripts/float_common.py`'s `FLOATS` registry and `CLASS_ORDER` were extended
    accordingly (unchanged logic in E1-E6 otherwise).

    Fixed membership criteria (order-1 reduction on a reliable range, file vs shuffled, that the
    shuffled copy loses; generic-compressor split gain under a front-bits or data-chosen
    partition for both xz and zstd) give: **2 full members** -- F7 Dew-Point-Temp (sensor, split
    gain xz +2.72%/zstd +23.45%) and F10 (high-precision, local, split gain xz +0.1%/zstd
    +5.36%); **7 weak-members** -- F1, F2, F3, F4 (decimal-origin), F5, F6 (sensor), F9
    (high-precision), each with real, reliable order-1 structure in the IEEE exponent range
    (14.4% to 99.8% reduction where the range is reliable; F6/F9 have only 1 distinct exponent,
    so the exponent range is not evaluable there, but a data-chosen partition still shows
    order-1 structure) but no positive generic-compressor split gain under any bit partition;
    **1 non-member** -- F8 POI-lat (high-precision, ALP's own flagged hard case: near-0%
    repeated values, up to 20 decimals of precision, near-random mantissa even at the bit
    level -- fails both criteria outright); and C0 (control) remains **non-member in substance**
    (exactly 0% order-1 reduction on every reliable range, file vs shuffled identical) despite
    the same spurious `data_chosen_partition` noise-cutting false positive on its split-gain
    test already flagged for the integer controls (finding 9's open-issues note), which is why
    its mechanical label is still "weak-member".

    The plan's hypothesis -- floats are members through front bits only, with decimal origin
    showing up mainly in a decimal-integer transform rather than any bit partition -- now holds
    more clearly at 10 columns than it did at 4: every non-control column shows real order-1
    exponent-range structure (criterion i), confirming the front-bits mechanism is general, but
    only 2 columns (Dew-Point-Temp, 16 distinct exponents; the Medicare1 ratio, 15) convert
    that into an exploitable generic-compressor split (criterion ii). (Corrected 2026-10-03:
    these are not the narrowest exponent fields; `float_fields_v2.csv` has F1 at 8, F5 at 12,
    F6/F9 at 1 and F8 at 16 distinct exponents, so exponent width does not predict criterion ii.)
    Decimal origin (F1-F4) is uniformly weak-member: real exponent-range signal, no exploitable
    split, consistent with the plan's prediction that decimal structure is not a contiguous bit
    range. POI-lat's clean non-member result confirms the plan's and ALP's own characterisation
    of that dataset as the class's hard case. **This is now the plan's full battery (10 float
    columns + control); the class-level framing can be treated as settled for this corpus, not
    provisional.**

## Still unreliable / open (do not cite as settled)

- Instagram order-artifact vs. value-structure separation (finding 2) -- quantified but not
  fully disentangled.
- `D_opt`/DP-partition numbers in `B/csv/membership.csv` and anything downstream of them
  (`table2_candidate.tex`, `gain_vs_nimble.csv`) -- cost-model-based, excluded from Sec. 2 by
  the author's correction; kept in `B/` as historical record only, not for citation in the new
  framing.
- `B`'s S4 "missed opportunity" figure and `A`'s FP-cost analysis -- these apply real codecs
  (Zstd/OpenZL/BtrBlocks/FastLanes/SIS) to make a *compression* argument and belong to the
  evaluation framing (`eval_from_study_runs.md`), not Sec. 2's data characterisation, even though
  they predate the author's 2026-10-02 correction and were written for the old framing.
- `A`'s stability/gate-classifier results (findings 3-4) reference the shipped admission gate,
  which is a threshold/cost-model artifact in its own right; useful context for why the study
  moved away from it, not evidence for the new measure.
- The data-chosen partition rule in C1 (gradient threshold, k=2.0) occasionally cuts noise on
  the unstructured controls (4-5 spurious ranges each) -- stated and visible in the CSV, not
  hidden, but not a validated general change-point method.

13. **OpenZL as a second heavyweight reference in F (2026-10-02).**     OpenZL added as a fourth, non-addressable size reference alongside xz_WHOLE in
    `fig/fig_addressable_vs_xz_v2.pdf` and `table_addressable_layouts_openzl_row.tex`
    (data: `csv/openzl_reference.csv`; method: B's `min(openzl/auto, block-1024, block-65536)`,
    same build/flags; 17/24 columns reused from B's benchmark host pulls with sha256-verified
    byte-identical inputs, 7 newly measured on benchmark host in this session).
    
    OpenZL beats xz on the T1 composite-key columns with strong field-local structure
    (xmark, uuidv7_hi, instagram, snowflake) and on most controls/near-miss columns.
    OpenZL loses to xz, by small margins, on the OSM geospatial digit-structured
    columns (quadkey, h3_r9, h3_r15, morton_2x16, s2_l16) and the low-cardinality
    PublicBI measure columns (npi, bene_count, num_employees, day_supply_bin).
    Neither compressor's edge over the other is large on the columns where OpenZL
    loses; xz's edge over OpenZL is at most ~1.2 bits/value in this set, versus
    both compressors' much larger, consistent edge over any addressable layout.
    Group gains over best whole-column addressable: structured OpenZL +54.9% (xz +52.0%), near-miss +28.9% (xz +30.7%), control +23.7% (xz +21.4%). OpenZL smaller than xz on 15/24 columns.

14. **Richer addressable layouts and the row-order share (F v3, 2026-10-05).**
    Two textbook row-addressable layouts added (RLE_RANK with end-position rank directory, PFOR per 1024-row block), no SIS; the four earlier layouts regress byte-identical (142 rows, 0 mismatches; `F/csv/addressable_layouts_v3.csv`).
    Mean gain over the four-layout WHOLE_best on the 9 structured columns: SPLIT_DATA four layouts +19.0%, SPLIT_DATA6 +25.6%, whole-value six layouts +0.3%, xz +50.5%, OpenZL +54.3%. Near-miss (7): SPLIT_DATA6 +26.8%, xz +38.7%. Control (8): SPLIT_DATA6 +6.5%, xz +21.4%.
    RLE_RANK supplies most of the 6.6 added points on structured (SPLIT_DATA +RLE_RANK 24.4, +PFOR 21.4); it wins 7 structured ranges (constant or near constant in file order) and no structured whole column.
    Row shuffle (`F/csv/shuffle_gap_v3.csv`): xz mean gain on structured falls 50.5% -> 16.1% (68% of its advantage is row order); SPLIT_DATA6 falls 25.6% -> 11.6%; the six-over-four margin falls 6.6 -> 2.9 points. OpenZL on the shuffle not run (no local binary); benchmark host command in `F/README.md`.
