# C3: `gain_vs_nimble.csv` -- decision: drop, not regenerate (2026-10-02)

Task: regenerate `B/csv/gain_vs_nimble.csv` against the TRUE Nimble default (not SIS
realNested), or drop it if it isn't encoder-agnostic and doesn't serve the study -- say which.

**Decision: drop.** No regenerated `gain_vs_nimble.csv` is produced in `C/`. `B/csv/gain_vs_nimble.csv`
itself is left untouched (old outputs kept, per batch convention).

## Why

1. **It isn't encoder-agnostic even before the Nimble-default question.** Its own `python_C_whole_bpv`
   and `python_fbw_bpv` columns are `B/scripts/study_common.py`'s 5-class closed-form cost model
   (`FixedBitWidth`/Dictionary/RLE/Delta+FOR argmin), not a property of the data. That is exactly
   the kind of number the author's correction (proposals/18 section H) replaces with the C1 entropy
   measure. Regenerating the Nimble-side column would still leave a cost-model number on the
   other side of every comparison -- it would not become an encoder-agnostic result by fixing
   only the Nimble label.
2. **A true non-SIS Nimble default is only available locally for 7 of the file's 15 columns.**
   `B/csv/blank_cells_measured.csv` (this batch's predecessor) has `nimble_best_nonsis_arm`/`_bpv`
   for `snowflake`, `instagram`, `publicbi_drug_cost`, `publicbi_drug_cost_ge65`,
   `publicbi_bene_count`, `publicbi_num_employees`, `publicbi_day_supply_bin` -- 7 of the 15 rows
   in `gain_vs_nimble.csv`. The other 8 (`xmark_prepost_full`, `osm_h3_r9_fileorder`,
   `osm_s2_l30_fileorder`, `bing_quadkey`, `uuidv7_hi`, `uuidv7_lo`, `publicbi_npi`,
   `publicbi_id1`) have no non-SIS-default measurement in any local pull:
   `addr_table_toplevel.tsv`'s `bpv_default` column covers all 15, but per `B/README.md` v3 point
   3, that column **is** SIS/realNested-under-default-candidates, i.e. the exact number the task
   says to replace -- it cannot stand in for the 8 missing rows. A full 15-row regeneration would
   need new benchmark host measurements, which are evaluation-side (SIS-adjacent build/benchmark work), not
   a local data-characterisation task.
3. **It doesn't add anything the study needs that isn't already covered, encoder-agnostically,
   by C1/C2.** The role `gain_vs_nimble.csv` played (sanity-check that a closed-form proxy tracks
   a real encoder's ranking) is superseded here by C1's entropy-based whole-value-vs-ranges
   measure, which needs no encoder at all. Where an existing codec's number is still useful to
   show "what it misses" (the author's correction explicitly allows this), the right source is
   `B/csv/blank_cells_measured.csv` (non-SIS Nimble, Zstd, OpenZL, BtrBlocks, FastLanes for the 6
   measure/instagram columns + 2 controls) -- already encoder-agnostic-compatible in the sense
   that it reports codecs' sizes as external facts, not as this study's own metric. No new file
   is needed to carry that; `C2/README_C2.md` does not re-quote it only because C2's claims are
   already fully supported by the entropy/value-statistics evidence without it.

## What this means for Sec. 2

Sec. 2 should not cite `gain_vs_nimble.csv` (v1/v2/v3 alike) at all going forward -- it was a
closed-form-cost-model cross-check, which the section no longer uses. Any "existing codecs show
what they miss" sentence in Sec. 2 should cite `B/csv/blank_cells_measured.csv` or
`A/csv/unstructured_controls.csv` directly (both already report real codec sizes, not a Python
re-implementation), not `gain_vs_nimble.csv`.
