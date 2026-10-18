# Top-level addressability rule, 524,288 rows (addr_toplevel_20260930_1127)

Commit: evaluation `rev-addr-toplevel`, the merge of `feat/addressable-top-level` (`rev-addr-toplevel-feat-base` RLE run values and a
Dictionary alphabet without a view are decoded once instead of failing the parent view; `rev-addr-toplevel-feat`
SectionCandidates::kAddressableTopLevel) into `rev-addr-strict`. Binaries: `bin/` (SHA256SUMS), built on benchmark host in
wt-evaluation with `ninja -j10` targets only (`addr_build/build.sh`, `addr_build/merged_rev-addr-toplevel.log`).

Checks before the run (`chain.sh`):
- `check_default_ident.log`: default payloads byte-identical to `sweep_full_20260929_0115/bin/` on the 9 columns.
- `check_strict_ident.log`: `--mlidc_sis_section_candidates=addressable_strict` payloads identical to
  `addr_20260930_0257` `addressable` (the strict rule as it ran there) on the 9 columns, 4 arms.

Flag values: `addressable` is the top-level rule since this commit (file suffix `toplevel`);
`addressable_strict` is the old `addressable`.

Launch: `setsid nohup bash chain.sh > chain.log 2>&1 &` (the run itself: `bash run.sh > run.log 2>&1`).
Holds `bench_timing.lock` per step. Resumable (skips outputs that exist); `touch STOP` stops before the next run.
Stages and scope: see the header of `run.sh`. Summaries: `summary.tsv` (0257's summarise.py: bits/value,
sections, non-addressable streams below sections), `summary_read.tsv` (retime summarise.py, generalised to
the pinned and hybrid settings).

Added stages: hybrid+view on the 5 FP columns and the snowflake/s2 pinned Delta swap (in run.sh); simdfor_view.sh -> simdfor_view/ (SimdForBitpack/view point + range64, 9 columns, w524.sh inputs and flags, for fig6).
