# Size budget on eight columns (2026-10-10)

Backs the Sec. 7 sentences "the encoded size stays within the budget at every step and on all eight columns we
measure" and "at a 5% budget, SIS reads XMark and Id1 slower than the default SIS"
(`python3 scripts/derive/budget_8col.py`).

- Build: rev-decode-knob, the same binary as `data/decode_knob_toplevel/` (the Snowflake budget figure), but this
  run predates the TopLevel configuration: it does **not** pass `--mlidc_sis_section_candidates=addressable`, so
  section encodings are unrestricted (Delta allowed), as in the earlier kDefault runs.
- Columns: Snowflake, OSM H3, OSM S2, Bing, XMark, UUIDv7-hi, NPI, Id1. Sizes at full length and on the 524,288-row
  prefix; point, range-64 and bulk reads on the prefix (view path, hot), 3 repeats, median.
- Configurations (`configs.txt`): `w0` = no knob; `M_P1B1_b<budget>` = strict budget on encoded bytes, mix
  point 0.5 / bulk 0.5 (the setting of the budget figure), budgets 2%, 5%, 10%; other tags are alternative mixes.
- Files: `eval3_measurements.csv` (one row per column, configuration and planner, built by `scripts/parse.py` from
  the raw per-run CSVs, which are not included), `summary_eval3.txt` (`scripts/summ3.py`), `commands.txt.gz`
  (every invocation), `scripts/eval3.sh` + `scripts/common.sh` (driver), `load.txt`.
