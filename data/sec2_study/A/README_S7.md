# S7 + G4: stability across prefixes, sample sizes and blocks

Inputs (full local files, sha256 prefix of first 1MiB):
- snowflake: `$PROJECT/Datasets/twitter_snowflake_10M.csv` sha256[:12]=39d5a23b5082, n=10000000
- xmark: `$PROJECT/EncodingsPlayground/Datasets/XMark/csv/prepost_id_full.txt` sha256[:12]=6240b93c4cf5, n=32298988
- h3_r9: `$PROJECT/EncodingsPlayground/Datasets/OSM/csv/h3_r9_fileorder.txt` sha256[:12]=66b32f89d8ea, n=10000000
- publicbi_npi: `$PROJECT/EncodingsPlayground/Datasets/PublicBI/Medicare1/csv/NPI_full.txt` sha256[:12]=daf1c991fe67, n=17290144
- instagram: `$PROJECT/Datasets/Instagram/instagram_id_full.txt` sha256[:12]=f63a38e249a7, n=1536841

quadkey and uuidv7_hi full files are benchmark host-only and not available locally; skipped (matches plan D,
'full local files' row and 'Benchmark host unreachable' risk F.11).

Method: for each full column, (1) prefix sweep n=65536,131072,...,doubling up to the full file
length; (2) sample-size sweep n=128,512,2048,8192,32768,131072,524288,full, uniform random
subsample without replacement (seed 0), order preserved (sorted indices) so the flip statistic
stays meaningful; (3) per-64536-row-block pass over the whole file. For each (column, slice):
flip-profile gate decision (shipped admission test, study_common.gate_decision) and the
documented-field gain G_doc = C(x) - D_doc(x) bits/value (same statistic as S5).

Outputs:
- csv/stability_prefix.csv, csv/stability_sample.csv, csv/stability_block.csv (raw per-slice rows)
- csv/stability_summary.csv: column, n_full, full_gate, prefix_agreement, sample_agreement,
  block_agreement (fraction of slices whose gate decision matches the full-file gate),
  n_blocks, G_doc_block_mean/std
- fig/fig_stability.pdf: G_doc per 64K-row block vs block index, one line per column, linear y from 0

## Summary

| column | n_full | full_gate | prefix_agree | sample_agree | block_agree | n_blocks | G_doc mean (std) |
|---|---|---|---|---|---|---|---|
| snowflake | 10000000 | True | 1.00 | 0.50 | 1.00 | 152 | 2.676 (3.186) |
| xmark | 32298988 | True | 1.00 | 0.75 | 1.00 | 492 | 45.234 (2.093) |
| h3_r9 | 10000000 | True | 1.00 | 0.38 | 1.00 | 152 | 4.334 (0.805) |
| publicbi_npi | 17290144 | False | 1.00 | 1.00 | 1.00 | 263 | nan (nan) |
| instagram | 1536841 | False | 1.00 | 1.00 | 1.00 | 23 | 1.679 (0.016) |

Runtime: 437.6 s
