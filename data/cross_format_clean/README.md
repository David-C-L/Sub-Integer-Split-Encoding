# Clean cross-format rerun (prepared 2026-09-29 17:05 local time, not launched)

**Update 2026-09-29 (evening): FastLanes is now pinned to rev-fls-sis (branch `cost-model-fix`), not rev-fls-sis-pre.**
rev-fls-sis = rev-fls-sis-pre + one commit: a multi-section SIS plan is kept only if its estimate beats the measured size of the one
full-width section (section selector's codec, run on the sampled vectors, dictionary from the whole rowgroup). This
removes the npi bias below. The commit is not on GitHub: it is the local branch `cost-model-fix` of the benchmark host checkout
`cross_format/FastLanes` (fetched from a git bundle). `run.sh` checks it exists, then runs a copy of
`cross_format_shared.sh` (`cross_format_shared_fls_fix.sh`, written at start) whose only change is
`FLS_COMMIT=rev-fls-sis-pre` -> `rev-fls-sis`; `prep_ok` and `builds.txt` use the new pin. BtrBlocks stays at rev-btr-sis.
Size check at 524,288 rows (same harness flags, one run on benchmark host, `cost_model_fix/bpv_v3_vs_rev-fls-sis.txt`): npi auto_sis
16.97 -> 15.33 bits/value; the other 17 column/arm cells are byte-identical to v3; all 18 validated.

Reruns the cross-format SIS comparison (figure `paper-repo/eval_figures/cross_format_v3_shared/`) cleanly:
pinned BtrBlocks/FastLanes commits built from clean checkouts, current Nimble binaries, host-load gating, 3 interleaved repeats.

## Launch
```
setsid nohup bash $RESULTS/cross_format_clean_20260929_1705/run.sh \
  >> $RESULTS/cross_format_clean_20260929_1705/run.log 2>&1 < /dev/null &
```
- `run.sh` takes `$HOSTDATA/project/bench_timing.lock` (fd 9) before anything else, so it can be
  launched now: it sleeps until `sweep_full_20260929_0115` releases the lock at the end of its Stage 5.
  flock is not FIFO: any other job queued on the same lock may run first.
- Resumable: rerun the same command. Finished CSVs are skipped, the prep step is skipped once the pinned builds are stamped.
- `touch STOP` stops before the next run. Outputs: `xf/{btrblocks,fastlanes,nimble}_run{1,2,3}.csv` (same format as
  `cross_format/shared_20260928/`), `progress.log`, `loads.log`, `builds.txt`, `commands.txt`, `logs/`, `DONE`.

## What it runs
1. Prep (once): `cross_format_shared.sh` with `XF_RUNS=0 XF_SKIP_NIMBLE=1 XF_HAVE_TIMING_LOCK=1` and
   `XF_TAG=../cross_format_clean_20260929_1705/xf`. It checks out btrblocks rev-btr-sis and FastLanes rev-fls-sis
   (branch cost-model-fix, via the harness copy above; was rev-fls-sis-pre), applies only the local gcc 11 patch to FastLanes, builds `subintsplit_bench` and
   `bench_subintsplit` at -j10 (needs >= 24 GB available), regenerates `cross_format/data_524288`. No benchmark runs.
2. Three repeats; each repeat runs every format once, rotated (btr fls nimble / fls nimble btr / nimble btr fls):
   - BtrBlocks: `cross_format_shared.sh` `XF_STAGES=btr XF_RUNS=<rep>` (arms AUTO_BASELINE64 = auto, AUTO_WITH_SIS64 = auto_sis, `--shared-codecs`).
   - FastLanes: `XF_STAGES=fls XF_RUNS=<rep>` (wizard_without_sis = auto, wizard_with_sis = auto_sis, `FLS_SUBINTSPLIT_SHARED_CODECS=1`).
   - Nimble: `nimble_rep.sh <rep>`, the commands of `xf_nimble_shared.sh` (Auto/view, `--mlidc_auto_encodings` shared set
     with/without SubIntSplit, `--mlidc_sis_allowed_encodings` shared set) with the evaluation binaries in `bin/`.
3. Before each run: memory/disk gate (>= 20 GB available, >= 10 GB free on /data, up to 20 min), then the load gate:
   if the 1-minute load is > 4 it polls every 60 s for up to 30 min; still loaded, the run is deferred to a retry pass
   after all repeats; still loaded then, it is skipped (`skipped.txt`) and a later rerun of `run.sh` picks it up.
   Host load/memory/disk are logged at the start and end of every run (`progress.log`, `loads.log`).
4. Each run: own process group, `timeout 4h`; a watchdog kills it on < 8 GB available memory or < 6 GB free disk.
5. `DONE` is written when all 9 CSVs exist (it records the count of unvalidated rows).

## Scope: 9 columns, 524,288 rows (not full length)
The cross-format harness cannot take the main sweep's full lengths (`sweep_full_20260929_0115/sweep_config.sh`:
10M for snowflake/xmark/h3/s2/uuidv7, 9,869,460 bing, 17,290,144 npi, 739,754 id1, 1,536,841 instagram) or the extra
columns (instagram, the 5 PublicBI controls) without code changes, which were not made. So this run keeps the
original 9 columns at the leading 524,288 rows in file order, matching `cross_format_v3_shared`. Changes needed:
1. `cross_format_shared.sh`: `ROWS=524288` and `COLS` are literals; the BtrBlocks converter's `ORDER` list and the
   FastLanes converter's `ROWS = 524288` (bits/value divisor) and `DATASETS` list are hard-coded in its inline Python.
2. `make_xf_datasets.py`: `COLUMNS` is hard-coded to the 524K-era source files (`tweet_id.txt`, `uuidv7_hi.txt`,
   `NPI.txt`, `quadkey_fileorder.txt`), not the `_full`/`_10M` files in `sweep_config.sh`; it takes one global `--rows`
   and exits when a column is shorter (id1 739,754, instagram 1,536,841, num_employees 739,752), so it needs per-column N.
3. `xf_nimble_shared.sh` (and `nimble_rep.sh` here): `--mlidc_rows=524288` and the column list are literals.
4. Unmeasured at full length: FastLanes' `bench_subintsplit` loads `generated.csv` text into memory and its SIS
   selector took 17.6 s to encode npi at 524K rows (single run); 17.3M rows is ~33x that per arm per repeat. Memory
   and runtime at 10-17M rows are unknown and need one narrow trial before a full-length cross-format sweep.

## Nimble binaries: evaluation branch rev-kdefault (chosen), not the pre-TuningConfig build
- v3 used `wt-encode-speed` at rev-encode-speed-1 plus the uncommitted Auto/view arm (`shared_20260928/nimble_manifest.txt`).
  That binary no longer exists: `wt-encode-speed` was rebuilt at rev-encode-speed-2 on 2026-09-28 15:45 local time. Exact
  reproduction of v3's Nimble numbers is impossible either way.
- Currency: the evaluation binaries are the ones every other paper figure is now measured with (main sweep,
  `sweep_full_20260929_0115/bin/`, sha256 in `bin/SHA256SUMS`, verified on copy). They carry the TuningConfig driver
  conversion (an upstream change), and their defaults are byte-identical to pr/8 on 9 columns x 59 arms (PROJECT_STATE.md section 5).
  Using them keeps the cross-format Nimble numbers consistent with the paper's Nimble-only numbers.
- Comparability: the Auto/view arm, `--mlidc_auto_encodings`, `--mlidc_sis_allowed_encodings` and the CSV headers
  are unchanged (checked: flag strings in the binaries, headers of the sweep's CSVs). Nimble bits/value may move
  slightly vs v3 (v3 README caveat 3). Compare `xf/nimble_run1.csv` with `cross_format/shared_20260928/nimble_run1.csv`
  and report any change beyond 0.1 bits/value in the figure README.

## Pinned builds (verified read-only on 2026-09-29, before launch)
- The benchmark host checkouts under `.../project/cross_format/` are still at the pre-pin commits (btrblocks rev-btr-pre,
  FastLanes rev-fls-pre) with the old patches applied as uncommitted changes, and have no `.xf_shared_stamp`; the
  pinned commits were never fetched there. Every file the pinned commits change (rev-btr-pre..rev-btr-sis, rev-fls-pre..rev-fls-sis-pre)
  is blob-identical in those working trees, and the binaries (btrblocks 2026-09-28 12:43, FastLanes 12:55) are newer
  than every source file. So v3 measured the pinned code, but not from a clean checkout.
- The prep step makes it clean: `ensure_repo` fetches cross-format-alignment, discards the (identical) working-tree
  changes, detaches at the pin and rebuilds. The old patches stay in `cross_format/patches/`. `builds.txt` records the result.
- Do not run `cross_format.sh` concurrently: it applies a different patch set to the same checkouts.

## ETA
- Update 2026-09-29 ~17:10 local time: the author paused the main sweep's timing stage (it exits and releases the lock), and another
  agent is building/benchmarking cost-model changes on benchmark host. Do NOT launch yet. Launch only once that work is finished and
  it has been decided whether the sweep resumes first. The resumed sweep and this run both queue on `bench_timing.lock`, and
  flock is not FIFO, so launch this after the sweep is relaunched if the sweep should go first.
- If the sweep resumes where it stopped (Stage 3 uuidv7_hi/npi onward), its remainder was estimated at 19-31 h.
- This run once it holds the lock: prep ~20-30 min (both builds from a fresh checkout at -j10, datasets), BtrBlocks
  ~5 min x 3, FastLanes ~20 min x 3 (v3 took 19-21 min per run under load), Nimble ~1 min x 3. About 1.5-2 h without
  load deferrals. Its prep build needs >= 24 GB available and waits up to 20 min for it; builds by other agents that
  do not hold the timing lock can still overlap it.

## Known issue (fixed by the rev-fls-sis pin)
FastLanes npi auto_sis 16.97 bits/value at rev-fls-sis-pre (vs 15.33 under the old FFOR-only split model): see
`paper_handover/state/CROSS_FORMAT_CLEAN_20260929_1705.md` (local). With rev-fls-sis it is 15.33 again (size check above);
the other columns are unchanged.
