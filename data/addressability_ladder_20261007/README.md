# Addressability ladder and Arm B (2026-10-07)

Only one value set from this folder reaches the paper: the **priced** column of `tab:eval_composition`
(`ARM_B_OPENZL_AWARE_DP_20261007.csv`, arm `armB_openzl_priced`: split chosen by the planner with OpenZL size
estimates, sections stored Trivial and compressed with OpenZL). Every other column of that table comes from the
TopLevel run (`data/toplevel_sec7/ladder/`). `ADDRESSABILITY_LADDER_SIZES_20261007.csv` is read by
`scripts/plot/make_tables_toplevel.py` but none of its values is printed.

Sizes only, full length, uint64, shipped order, `nimble_ml_id_compression_benchmark --mlidc_iters=1`.

| file | what | build |
|---|---|---|
| `commands_arm_b.txt` | every Arm B invocation (`ref_*`, `refzl_*`, `armB_nimble_*`, `armB_select_*`) | `bin/` = rev-arm-b; `bin2/` = rev-arm-b-2 (npi, id1, uuidv7_lo); sha256 in `SHA256SUMS_arm_b` |
| `commands_ladder.txt` | every ladder invocation (arms 1+5, 2, 3, A) | `bin_rowframe/` = rev-toplevel + rev-arm-a |

Arm B flags: `--mlidc_encoders=SIS/trivial,SIS/realNested --mlidc_substream_compression=OpenZL --mlidc_sis_openzl_pricing=nimble`.
The `armB_openzl_priced_samples_*` rows come from a planner-sample sweep with `--mlidc_sis_planner_samples=<n>`
on the same build; they are not used in the paper.
