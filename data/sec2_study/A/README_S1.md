# S1: flip-probability profiles

Inputs (sha256 prefix, first 1MiB; see study_common.COLUMNS for full paths), N=524288 rows (file-order prefix):
- snowflake: `$PROJECT/Datasets/twitter_snowflake_10M.csv` sha256[:12]=39d5a23b5082
- instagram: `$PROJECT/Datasets/Instagram/instagram_id_full.txt` sha256[:12]=f63a38e249a7
- uuidv7_hi: `$PROJECT/pulls/columns_524k/uuidv7_hi.txt` sha256[:12]=688a5b7bbdf4
- xmark: `$PROJECT/EncodingsPlayground/Datasets/XMark/csv/prepost_id_full.txt` sha256[:12]=6240b93c4cf5
- quadkey: `$PROJECT/pulls/columns_524k/quadkey_fileorder.txt` sha256[:12]=6e827d146bbc
- h3_r9: `$PROJECT/EncodingsPlayground/Datasets/OSM/csv/h3_r9_fileorder.txt` sha256[:12]=66b32f89d8ea
- h3_r15: `$PROJECT/EncodingsPlayground/Datasets/OSM/csv/h3_r15_fileorder.txt` sha256[:12]=31ec37054be3
- s2_l16: `$PROJECT/EncodingsPlayground/Datasets/OSM/csv/s2_l16_fileorder.txt` sha256[:12]=ec2ad67de9e1
- s2_l30: `$PROJECT/EncodingsPlayground/Datasets/OSM/csv/s2_l30_fileorder.txt` sha256[:12]=431a672465a3
- morton_2x16: `$PROJECT/EncodingsPlayground/Datasets/OSM/csv/morton_2x16_fileorder.txt` sha256[:12]=04c2fbf2ce49
- morton_2x32: `$PROJECT/EncodingsPlayground/Datasets/OSM/csv/morton_2x32_fileorder.txt` sha256[:12]=8bca54142424
- publicbi_drug_cost: `$PROJECT/EncodingsPlayground/Datasets/PublicBI/Medicare1/csv/TOTAL_DRUG_COST.txt` sha256[:12]=120c56bfca60
- publicbi_drug_cost_ge65: `$PROJECT/Datasets/PublicBI_controls_20260929_staged/Medicare1_TOTAL_DRUG_COST_GE65_cents_full.txt` sha256[:12]=1e2e56eabd61
- publicbi_bene_count: `$PROJECT/EncodingsPlayground/Datasets/PublicBI/Medicare1/csv/BENE_COUNT.txt` sha256[:12]=6733e55bf647
- publicbi_num_employees: `$PROJECT/EncodingsPlayground/Datasets/PublicBI/Corporations/csv/num_employees.txt` sha256[:12]=fda844955368
- publicbi_day_supply_bin: `$PROJECT/EncodingsPlayground/Datasets/PublicBI/Medicare1/csv/Avg_Day_Supply_Bene_bin.txt` sha256[:12]=6c49830527f4
- uuidv7_lo: `$PROJECT/pulls/columns_524k/uuidv7_lo.txt` sha256[:12]=5929ad6a5438
- publicbi_npi: `$PROJECT/EncodingsPlayground/Datasets/PublicBI/Medicare1/csv/NPI_full.txt` sha256[:12]=daf1c991fe67
- publicbi_id1: `$PROJECT/EncodingsPlayground/Datasets/PublicBI/Corporations/csv/Id1.txt` sha256[:12]=8a787fc92814
- tpch_orderkey: `$PROJECT/EncodingsPlayground/Datasets/TPCH/csv/orderkey.txt` sha256[:12]=91d4eef2fb7f
- inat_species_id: `$PROJECT/EncodingsPlayground/Datasets/iNaturalist_csv/species_id.txt` sha256[:12]=d89b03b5ca60
- ipv4_id: `$PROJECT/EncodingsPlayground/Datasets/IPv4/csv/ipv4_id.txt` sha256[:12]=4f6ff97e1e58

Method: for every column, load the leading 524288 rows in file order (int tokens -> uint64).
Per-bit flip probability p[b] = fraction of adjacent rows (i, i+1) where bit b differs
(`study_common.flip_profile`). Shuffled profile: same column, `numpy.random.default_rng(0).shuffle`
in place, same statistic. Gate decision: shipped admission test
(`paper-repo/eval_figures/c3_bitflip_admission/gates.py` `gradient_gate` + `plot_c3_profiles.py:20`
entropy_max=0.8), reimplemented in `study_common.gate_decision` (verified to match gates.py symbolically).

Outputs:
- csv/flip_profiles.csv: column,bit,p_file,p_shuffled,grad (64 rows/column)
- csv/flip_profiles_gate.csv: column,subtype,kind,n,gate_file,gate_shuffled,entropy_file,entropy_shuf,maxg_file,maxg_shuf
- fig/fig2_flip_profiles.pdf: one panel per sub-type (T1-T4, control), flip prob vs bit, file order, linear y in [0,1], no title

Runtime: 22.0 s
