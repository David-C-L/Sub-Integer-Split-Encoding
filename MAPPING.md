# Mapping: paper item -> data -> script -> command

All commands run from the artifact root after `scripts/unpack_data.sh` and `scripts/derive_all.sh`, and write to
`out/` (override with `SIS_FIG_OUT`). `scripts/regenerate_all.sh` runs all of them and then
`scripts/check_against_paper.sh`, which compares each output with the paper copy in `figures/` (PDFs: `pdftotext`
text and page size, plus a 100 dpi raster comparison; TeX: `diff` ignoring comment lines; Table 2
whitespace-normalised; Table 1 body rows).

Status: **reproduced** = text and numbers identical to the paper copy; **pixel-identical** where the raster also
matches. TL = the TopLevel Sec. 7 run (`data/toplevel_sec7/`), SIS restricted to addressable section encodings
(`--mlidc_sis_section_candidates=addressable`). Palette: Sec. 1, 2 and 4 figures are rendered with
`SIS_PALETTE=B`; Fig. 3 and Sec. 7 with the default `tol_hc`.

## Figures and tables placed in the paper

| # | paper item (`figures/` file) | data | intermediate | command | status |
|---|---|---|---|---|---|
| 1 | Fig. 1 `fig:skip_gap_motivation` (`section_1/fig0_zoom_nosis.pdf`) | `data/sec1_motivation/` (Snowflake, baselines only) | none | `SIS_PALETTE=B python3 scripts/plot/make_sec1_zoom_v4_figure.py` -> `fig0_v4.pdf` | reproduced, pixel-identical |
| 2 | Table 1 `tab:class_study_grouped` (`section_2/table_class_study_grouped.tex`) | `data/sec2_study/{D,F}/csv/` | none | `python3 scripts/plot/make_table1_class_study.py` -> `table_class_study_grouped_body.tex` | reproduced: body rows identical (columns $n$, Members, per-range, xz, OpenZL; no Predictability column); the paper's header, caption and the commented-out T1-T4 mean row are hand-written (the script prints the mean row to stdout) |
| 3 | Fig. 2 `fig:flip_profiles` (`section_2/flip_{T1,T3,nearmiss,control}.pdf`) | `data/sec2_study/A/csv/flip_profiles.csv` | none | `SIS_PALETTE=B python3 scripts/plot/make_sec2_flip_panels.py` | reproduced, pixel-identical under `requirements.txt` (matplotlib 3.6.3) |
| 4 | Fig. 3 `fig:sis_encode` (`section_3/sis_encode_pipeline.pdf`) | `data/sec3_pipeline/snowflake_first16.txt`, `data/addr_toplevel_snowflake/comp_snowflake_toplevel.csv.log` (SIS tree) | `derived/sec3_plan_breakdown_8sec_addr.csv` (read by hand off the log) | `python3 scripts/plot/make_sis_encode_pipeline_v5.py` -> `sis_encode_pipeline_v5.pdf` | reproduced, pixel-identical |
| 5 | Fig. 4 `fig:bit_flip` (`section_4/snowflake_flip_profile.pdf`) | `data/bitflip_profiles/profiles_42col.npz` (key `TwitterSnowflake_tweet_id`, 1,024 pairs) | none | `SIS_PALETTE=B python3 scripts/plot/make_sec4_flip_profile.py` | reproduced, pixel-identical |
| 6 | Table 2 `tab:eval_setup` (`section_7/tab_eval_setup.tex`) | `data/table2_column_stats/column_stats.csv` | none | `python3 scripts/plot/make_tab_eval_setup.py` -> `tab_eval_setup.tex` | reproduced (all cells, whitespace-normalised; Calc. distinct 0.99 = 521,478 / 524,288) |
| 7 | Fig. `fig:eval_scoreboard` (`section_7/fig10_openzl_scoreboard.pdf`) | TL `sweep/` (524K reads, encode), `data/sweep_full2/` + TL `ladder/` (full-length sizes) | `derived/toplevel_sec7/{pull_524k_toplevel,merged_shipped_toplevel,scoreboard_*}`, `derived/fig10_openzl_scoreboard_mixed.csv` | `python3 scripts/plot/make_fig10_scoreboard_split_v5.py` | reproduced, pixel-identical |
| 8 | Fig. `fig:eval_gather` (`section_7/fig9b_gather_shapes_{a,b,c,d,legend}.pdf`) | TL `gather4/` | none | `python3 scripts/plot/make_fig3_fig6_fig9b_compact.py` | reproduced, pixel-identical (5 files) |
| 9 | Fig. `fig:eval_blocksize` (`section_7/fig_blocksize_snowflake_half.pdf`) | TL `abl_a/`, TL `plan_decode/summary.csv` (SIS point) | none | `python3 scripts/plot/make_blocksize_half.py` | reproduced, pixel-identical |
| 10 | Fig. `fig:eval_budget` (`section_7/fig_budget_sweep_half.pdf`) | `data/decode_knob_toplevel/sweep_measurements.csv` | `derived/budget_sweep_values.csv` | `python3 scripts/plot/make_budget_half_v2.py` -> `fig_budget_sweep_half_v2.pdf` | reproduced, pixel-identical |
| 11 | Fig. `fig:eval_floats` (`section_7/fig_alp_floats_{size,range}.pdf`) | `data/alp_floats/` | none | `python3 scripts/plot/make_alp_floats_compact.py` | reproduced, pixel-identical |
| 12 | Table `tab:eval_composition` (`section_7/tab_eval_composition.tex`) | TL `ladder/` (SIS = `arm15`, enc. = `arm3`, raw = `armA`, OpenZL = `arm15` `openzl/auto`); priced = `data/addressability_ladder_20261007/ARM_B_OPENZL_AWARE_DP_20261007.csv` (`armB_openzl_priced`) | none | `python3 scripts/plot/make_tables_toplevel.py` -> `tab_eval_composition_full.tex` | reproduced (identical tex; TopLevel, no Seq. column; the unrestricted arm of `data/seq_toplevel/` is only in `tab_eval_composition_toplevel.csv`) |
| 13 | Fig. `fig:eval_crossformat` (`section_7/fig_crossformat_bpv_B.pdf`) | TL `xf/nimble_raw/` (Nimble), `data/cross_format_clean/xf/` (BtrBlocks, FastLanes; median of 3 runs) | none | `python3 scripts/plot/make_fig_crossformat_bpv_AB.py` -> `fig_crossformat_bpv_B.pdf` | reproduced, pixel-identical |
| 14 | Table `tab:eval_planner_gap` (`section_7/tab_eval_planner_gap_body.tex`) | TL `plan_decode/summary.csv` (bits, sections, point reads), `data/plan_time/summary.csv` (planning time); rows default = `SIS/realNested`, re-priced = `SIS/hybrid`, encoded = `SIS/oracle_dp_selection` | none | as row 12 -> `tab_eval_planner_gap_toplevel.tex` | reproduced (identical tex); the 10M-row variant (`data/planner_gap_10m/`) is not in the paper |
| 15 | Table `tab:eval_admission` (`section_7/table7_admission_confusion.tex`) | TL `admission/` (42 columns), `data/bitflip_profiles/profiles.npz` | none | as row 12 (+ `scripts/plot/admission/gates.py`) | reproduced (identical tex, header Precision / Recall) |
| 16 | Fig. `fig:eval_transform_impact` (`section_7/fig12_transform_impact_heatmap.pdf`) | TL `sweep/` (shipped and `mergeirr_8` orders) | `derived/toplevel_sec7/fig12_panels_toplevel/fig12_transform_impact.csv` | `python3 scripts/plot/make_fig12_default_only_v5.py` | reproduced, pixel-identical |

Not placed in the final paper (commented out in the tex), but kept in `figures/` and checked:
`section_4/snowflake_flip_{probability,gradient}.pdf` (`make_sec4_bitflip.py`) and `section_7/fig6_point_access.pdf`
(`make_fig3_fig6_fig9b_compact.py`); all three reproduce pixel-identically.

## Intermediates (`derived/`), rebuilt byte-identically by `scripts/derive_all.sh`

| intermediate | command (inside `derive_all.sh`) |
|---|---|
| `toplevel_sec7/pull_524k_toplevel` | `python3 scripts/derive/normalise_pull.py data/toplevel_sec7/sweep <out>` |
| `toplevel_sec7/merged_shipped_toplevel` | `SIS_DERIVE_OUT=<out> python3 scripts/derive/build_merged_shipped_toplevel.py` |
| `toplevel_sec7/scoreboard_size_toplevel` | `SIS_FIG_PULL=derived/toplevel_sec7/merged_shipped_toplevel SIS_FIG_OUT=<out> python3 scripts/derive/make_scoreboard.py` (CSV and stdout kept) |
| `toplevel_sec7/scoreboard_524k_toplevel` | `SIS_FIG_PULL=derived/toplevel_sec7/pull_524k_toplevel SIS_FIG_OUT=<out> python3 scripts/derive/make_scoreboard.py` |
| `toplevel_sec7/fig12_panels_toplevel` | `SIS_FIG_PULL=derived/toplevel_sec7/pull_524k_toplevel SIS_FIG_OUT=<out> python3 scripts/derive/make_transform_impact_panels.py` |
| `fig10_openzl_scoreboard_mixed.csv` | `SIS_FIG_OUT=<out> python3 scripts/derive/make_fig10_scoreboard_col.py` (size rows from the full-length scoreboard, the rest from the 524K one) |
| `budget_sweep_values.csv` | `python3 scripts/derive/sweeptab.py data/decode_knob_toplevel/sweep_measurements.csv <out>.csv` |
| `sec3_plan_breakdown_8sec_addr.csv` | not rebuilt: read by hand from `data/addr_toplevel_snowflake/comp_snowflake_toplevel.csv.log` |
| TL `plan_decode/summary.csv` (in `data/`) | `python3 scripts/derive/summarise_plan_decode.py <copy of data/toplevel_sec7/plan_decode>` |

Checked: `SIS_DERIVE_ROOT=<scratch> scripts/derive_all.sh` reproduces every file of the previously shipped
`derived/` byte for byte (`diff -r`).

## Numbers quoted in the prose

| section, claim | value in paper | source -> command | status |
|---|---|---|---|
| 2: corpus | 24 integer columns (9 typed, 7 near-misses, 8 controls) | `make_table1_class_study.py` (`GROUPS`) | reproduced |
| 2: members | six of nine typed columns; separation gain under xz 1.5% (S2 l30) to 27.0% (XMark) | D `split_measure.csv` -> `make_table1_class_study.py` | reproduced |
| 2: no near-miss or control is a member | 0, 0 | same | reproduced |
| 2: per-bit-range saving typed / near-miss / controls | 19.0% / 1.4% / nothing | F `addressable_layouts.csv` -> same | reproduced (controls mean -3.8%, no saving) |
| 2: documented layout saving | 9.3% | F (`SPLIT_DOC`) -> same | reproduced |
| 2: xz / OpenZL saving on typed columns | 50.5% / 54.3% | F, F `openzl_reference.csv` -> same | reproduced |
| 2: with RLE and patched FOR | 19.0% -> 25.6% | F `addressable_layouts_v3.csv` -> `python3 scripts/derive/sec2_study/F/f5_v3_summary.py` | reproduced |
| 2: row shuffle | xz 50.5% -> 16.1%; per-range 25.6% -> 11.6% | F `shuffle_gap_v3.csv` -> same | reproduced |
| 3: Fig. 3 split | 8 sections, 39.35 of 64 bits | `derived/sec3_plan_breakdown_8sec_addr.csv` | reproduced |
| 7: setup | nine columns (six SFV, three controls); five float columns | Table 2 data | reproduced |
| 7: OpenZL smaller on every SFV column except UUIDv7-hi | size ratios 0.84-0.91 (Snowflake, H3, S2, Bing), 0.34 (XMark), 1.13 (UUIDv7-hi) | `derived/fig10_openzl_scoreboard_mixed.csv` (axis `size`) | reproduced |
| 7: gap widest on NPI and XMark | about 3x | same (0.32, 0.34) | reproduced |
| 7: NPI distinct values | 4% | `data/table2_column_stats/column_stats.csv` (640,119 / 17,290,144 = 3.7%) | reproduced |
| 7: read lead smallest on Snowflake and Bing (1,024-row blocks qualify), largest on UUIDv7 (whole column) | | same (axes `point`, `range B=64`; `openzl_arm`) | reproduced (point 44.9x and 109x; UUIDv7 27,123x and 32,495x) |
| 7: encode slower | seven of nine columns | same (axis `encode (CPU)`, ratio < 1 on 7 columns) | reproduced |
| 7: at selectivity 0.33 OpenZL faster on Snowflake and Bing (short runs) | | same (`gather sel=0.33`: 0.79, 0.80) and TL `gather4/` | reproduced |
| 7: budget within limit at every step and on all eight columns | | `python3 scripts/derive/budget_8col.py` (`data/decode_knob_8col/`, older configuration) and `data/decode_knob_toplevel/` | reproduced (max +3.8% full length / +4.1% prefix at 5%, +5.3% at 10%) |
| 7: at a 5% budget XMark and Id1 read slower than default SIS | | same | partly: XMark open + first bulk 0.75x; Id1 point 0.999x (within noise); OSM H3 open + first bulk 0.95x also slower |
| 7: cold cache changes the OpenZL/SIS point ratio by at most a third | | `python3 scripts/derive/cold_point_ratio.py derived/toplevel_sec7/pull_524k_toplevel` | reproduced (max 33.3%, Bing) |
| 7: SIS smaller than ALP on all float columns, most on POI-lat | | `out/alp_floats_compact_values.csv` (`make_alp_floats_compact.py`) | reproduced (POI-lat 39.2 vs 55.5 bits) |
| 7: OpenZL on SIS sections smaller than on whole values on every SFV column; priced gains further on Snowflake and Bing; misses on NPI | | `out/tab_eval_composition_toplevel.csv` | reproduced |
| 7: OpenZL-priced planning slower | 51x | TL `extra_planner_time/summary.txt` (579.9 / 11.33 ms) | reproduced |
| 7: SIS reduces size on every SFV column in all three formats | | `out/tab_eval_crossformat_toplevel.csv` | reproduced |
| 7: re-pricing triples planning time; encoded over 40 s | | `data/plan_time/table_cells.csv` (3.26x, 3.51x; 41.2 s, 45.9 s) | reproduced |
| 7: Snowflake re-priced and encoded read points slower; H3 within 6% | | TL `plan_decode/summary.csv` (1,376 and 1,594 vs 1,033 ns; H3 684 and 642 vs 682 ns) | reproduced |
| 7: planner cost per column | 7-15 ms | `data/plan_time/table_cells.csv` (default: H3 7.3 ms, Snowflake 15.1 ms) | reproduced |
| 7: admission columns | 42, SIS wins on 38 | `python3 scripts/derive/admission_numbers.py data/toplevel_sec7/admission` | reproduced |
| 7: one false positive (UUIDv7-lo), one false negative (Public BI funding) | | same | reproduced |
| 7: size estimate wrong on four columns | 4 | same | reproduced |
| 7: 1,024 pairs: same answers as the full profile; cost | 0.007-0.097% of an encode | same | reproduced |
| 8: share of OpenZL's compression ratio | 84% to 113% on five of six structured columns | `derived/fig10_openzl_scoreboard_mixed.csv` (axis `size`) | reproduced (0.842 to 1.130; XMark 0.338) |

## Known differences between paper text and data

Statements in `sample-sigconf.tex` (final version) that the shipped data does not reproduce as written:

| section | paper text | reproduced value |
|---|---|---|
| 8 (Conclusion) | "reading selective row ranges 40x to 30,000x faster" than OpenZL | range reads of 64 rows: 17.7x (Snowflake) to 15,338x (UUIDv7-lo); point reads: 44.9x to 32,495x (`derived/fig10_openzl_scoreboard_mixed.csv`) |
| 8 (Conclusion) | SIS "improves decode throughput over OpenZL on every access pattern we measure" | OpenZL is faster on dense gathers (selectivity 0.33) on Snowflake (SIS/OpenZL 0.79x) and Bing (0.80x), as Sec. 7 itself states |
| 8 (Conclusion) | "The splits SIS finds also improve OpenZL's own compression ratio by up to 28%" | 28% holds for UUIDv7-hi (8.48 / 6.60 bits); on XMark OpenZL on the raw sections is 2.5x smaller than on whole values (1.50 / 0.60 bits) (`tab:eval_composition`) |
| 7 (cross-format) | "On the controls each format's selection leaves SIS unused" | FastLanes selects SIS on NPI (0.80 of the size without SIS); Nimble and BtrBlocks leave all three controls at 1.00 (two decimals) (`out/tab_eval_crossformat_toplevel.csv`) |
| 7 (budget) | "at a 5% budget, SIS reads XMark and Id1 slower than the default SIS" | XMark open + first bulk 0.75x; Id1 0.999x point, within noise; OSM H3 open + first bulk 0.95x (`scripts/derive/budget_8col.py`) |
