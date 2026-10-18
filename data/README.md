# Measurement data

Raw benchmark CSVs and logs, one folder per experiment. Folders listed in `scripts/packed_data.txt` are shipped
as `<folder>.tar.gz` next to where they belong; `scripts/unpack_data.sh` restores them (`regenerate_all.sh` calls
it first). Which code state produced each folder: `code/README.md`, "Code states behind the data".

| dir | what | rows | build |
|---|---|---|---|
| `toplevel_sec7/` | Sec. 7 main run, SIS in addressable TopLevel mode, every arm on one build: sizes (`sweep/comp*`, `ladder/`, `xf/`), 524K reads (`sweep/`), gathers (`gather4/`), point baselines (`simdfor_view/`), block-size ablation (`abl_a/`), planner gap (`plan_decode/`), admission (`admission/`), OpenZL-priced planning time (`extra_planner_time/`); `commands.txt` lists every invocation | 524,288 (reads), full length (sizes) | `COMMIT`, `bin/SHA256SUMS` |
| `sweep_full2/` | full-length sizes of the baselines, merged with the TopLevel SIS rows into `derived/toplevel_sec7/merged_shipped_toplevel` | full length | `COMMIT` |
| `decode_knob_toplevel/` | size-budget sweep on Snowflake (Fig. `fig:eval_budget`) | 524,288 | `COMMIT` |
| `decode_knob_8col/` | size budget on eight columns, older configuration without the addressable restriction (`README.md`) | 524,288 + full length | `COMMIT` |
| `cross_format_clean/` | SIS ported to BtrBlocks and FastLanes, each format's selection with and without SIS, 3 runs (`README.md`, `builds.txt`, `commands.txt`; harness in `scripts/run/cross_format_clean/`) | 524,288 | `builds.txt` |
| `alp_floats/` | SIS vs ALP vs OpenZL on five float columns | 524,288 | `COMMIT` |
| `addressability_ladder_20261007/` | supplies only the priced column of `tab:eval_composition` (`README.md`, `commands_*.txt`) | full length | `README.md` |
| `seq_toplevel/` | unrestricted section encodings (+Delta/Huffman) on the TopLevel binary; kept in the CSV of the composition table, not printed in the paper | full length | same binary as `toplevel_sec7/` (`bin/SHA256SUMS`); host dir `seq_toplevel_20261017_2057` on the benchmark host |
| `plan_time/` | planning time of the three `tab:eval_planner_gap` planners (default `SIS/realNested`, re-priced `SIS/hybrid`, encoded `SIS/oracle_dp_selection`), TopLevel mode: encode entry to chosen split via a plan observer (21 timed encodes after 2 warm-ups) and the encoded planner alone (11 runs, whole column, plus a 2,048-row sample); row-count check at 131,072 and about 2M rows and with `--mlidc_sis_row_frame=false`; `scripts/derive/summarise_plan_time.py` writes `raw_plan_time.csv` and `summary.csv` and checks sizes and plans against `toplevel_sec7/plan_decode` (all equal) | 524,288 (+131,072, 2,000,000 / 2,097,152) | `rev-head` + `plan_time.patch` (timers only), `bin/SHA256SUMS` |
| `planner_gap_10m/` | `tab:eval_planner_gap` at 10M rows (not in the paper): sizes, sections and hot point reads on the TopLevel binary, planning time with the `plan_time/` timers; `scripts/derive/summarise_planner_gap_10m.py` writes `summary.csv`, `SIS_PG_ROWS=10000000 python3 scripts/plot/make_tables_toplevel.py` writes `out/tab_eval_planner_gap_10m.tex` | 10,000,000 | `toplevel_sec7/bin` + `plan_time/bin` |
| `addr_toplevel_snowflake/` | the Snowflake SIS tree drawn in Fig. 3 | 524,288 | `COMMIT` |
| `sec1_motivation/` | Snowflake baselines for Fig. 1 | 524,288 | baselines only |
| `sec2_study/` | Sec. 2 data-class study: flip profiles (A), structure and order-1 entropy (C), separation gain (D), floats (E), per-bit-range layouts (F), membership (G) | 524,288 | Python |
| `sec3_pipeline/` | the Snowflake IDs drawn in Fig. 3 (`commands.txt`) | 16 | Python |
| `table2_column_stats/` | exact row and distinct counts of the Table 2 columns (`datasets/compute_column_stats.py`, run read-only on the full-length files) | full length / 524,288 | Python |
| `bitflip_profiles/` | cached flip profiles used by Fig. 4 and the admission table (`commands.txt`) | 524,288 | Python |

`plan_time/`, `planner_gap_10m/` and `seq_toplevel/` keep their run scripts (`run*.sh`, `pg_*.sh`, `pt_build.sh`)
and `commands.txt` inside the data folder; the other experiments' drivers are in `scripts/run/<experiment>/`.

Placeholders in run scripts and logs: `$RESULTS` (result directory on the benchmark host), `$HOSTDATA` (its data
volume), `$PROJECT` (the project checkout; `$HOSTDATA/project` is the same checkout, holding `Datasets/`), `<ssh-key>`, `<fork-url>` (the private development forks of BtrBlocks
and FastLanes, whose shipped state is `code/btrblocks` and `code/fastlanes`), `benchmark-host`. Revision labels
(`rev-*`) replace the hashes of private commits; `code/README.md` lists them.

## Anonymisation
Personal names, user names, host names, home and data paths, e-mail addresses, repository URLs, pull-request
numbers and private commit hashes were removed from every text file, including the packed folders. Comments that
recorded who made a decision say "the author". Code and patches keep the C++ namespaces of the public Velox project
(`facebook::velox`, `facebook::nimble`).
