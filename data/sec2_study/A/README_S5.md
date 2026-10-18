# S5 + G2: order sensitivity (T1 columns)

Inputs: same T1 files as S1 (study_common.COLUMNS), N=524288 rows.
Method: for each T1 column (snowflake, instagram, uuidv7_hi, xmark, quadkey), compute the flip
profile, shipped gate decision, and the membership statistic G_doc = C(x) - D_doc(x) in bits/value
(C(x) = best closed-form whole-value cost across Constant/FOR/Dict/RLE/DeltaFOR; D_doc = sum of
best per-field costs over the documented layout; study_common.best_whole_cost /
documented_field_cost) in three row orders: file (as stored), sorted (numpy.sort, ascending),
shuffled (numpy.random.default_rng(0).shuffle). For instagram, a fourth order sorts by the
documented leading timestamp field (bits 23-63) only (ties broken stably by file order), to test
whether this recovers the structure hidden by interleaved scraping order.

Outputs: csv/order_sensitivity.csv (column, order, n, gate, entropy, maxg, boundaries,
C_whole_bits, whole_best, D_doc_bits, G_doc_bits).

## Key result: instagram scraped order

- file order:          gate=False, active_entropy=0.822 (>0.8 cutoff), G_doc=1.950 bits/value
- sorted by ts field:  gate=True, active_entropy=0.694, G_doc=1.950 bits/value

Interpretation: sorting by the leading timestamp field recovers the admission (flips drop, gate flips True).
This shows the ~0.5 flip-probability profile in scraped order comes from row interleaving across
users/shards (the shard/seq fields still perturb adjacent rows even after a ts sort), not from an
absence of structure in the values themselves: G_doc stays positive in file order already
(the documented fields are still a cheaper encoding of the *values*; what moves is the row-pair
flip statistic, which is order-dependent by construction).

Runtime: 13.3 s
