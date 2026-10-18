# sweep_full2_20260930_1213: resumed full-length SIS evaluation (approved by the author 2026-09-30)

Commit: evaluation `rev-addr-toplevel` (merges feat/addressable-top-level; see COMMIT). Binaries in bin/ are copied from
addr_toplevel_20260930_1127/bin (same SHA256, bin/SHA256SUMS); built with -Wa,-mbranches-within-32B-boundaries, zstd bundled.
Predecessor: sweep_full_20260929_0115 (binaries rev-kdefault; stopped with STOP after Stage 4 comp).

## Columns (full length, as the old sweep_config.sh)
Main 10: snowflake 10M, instagram 1,536,841, osm_h3_r9 10M, osm_s2_l30 10M, xmark_prepost_full 10M (capped, as the old run),
bing_quadkey 9,869,460, uuidv7_hi 10M, publicbi_npi 17,290,144, publicbi_id1 739,754, uuidv7_lo 10M.
Controls 5: publicbi_drug_cost, publicbi_bene_count, publicbi_day_supply_bin (17,290,144 each), publicbi_num_employees 739,752,
publicbi_drug_cost_ge65 10,281,398 (Datasets/PublicBI_controls_20260929_float/, sha256 checked at start).

## Reuse decisions (evidence in checks/)
1. Default compression, all 33 arms (SIS and baselines): REUSED from the old full/comp_*, compzl_* (reuse/comp/).
   Evidence: checks/comp_{instagram,snowflake}.csv at full length with the old arm list: 33/33 payload_bytes identical on each
   (cmp.py). Earlier: default identity on 9 columns at 524,288 (addr_build/check_rev-addr-toplevel).
2. Baseline timing (openzl/auto, openzl/block-*, FixedBitWidth(+view), FPE x3): code check PASSES, timing spot-check FAILS, so
   baselines are RERUN (Stage E main columns, Stage B controls). Old CSVs are linked in reuse/baseline_timing/ as provisional only.
   - git diff rev-kdefault..rev-addr-toplevel: no change to FixedBitWidth/FrequencyPartition/OpenZL encodings or the FBW view; harness changes
     are flag plumbing (section candidates, cost model v2, cache key suffix only when non-default), a no-op virtual
     EncodingView::willRead, the FP view registration, and rowAddressed plumbing in the selection policy (a no-op under default).
   - instagram full N, hot, 3 reps each, median new/old: bulk 0.885-1.078 (openzl/auto 0.94, fbw 1.01, fbw_view 1.08,
     fpe_noindex 1.02, fpe_pertier 1.00, fpe_elias 0.92, block-1024 0.94, block-65536 0.89); point 0.91-1.07 (fbw 1.07,
     fbw_view 1.05, fpe_elias 0.91, others within 5%). 5 of 16 cells outside 5%, in both directions; the within-run rep
     spread is 1.00-1.14x (spread.py), so this is most likely noise, but the agreed criterion fails.
3. Every SIS arm is re-timed on rev-addr-toplevel (new FP/MainlyConstant views, full-scan switch, top-level rule).
   Compression is rerun only for non-default section candidates (default is byte-identical, point 1).
   Not rerun: the old Stage 2 (instagram at 524,288) and Stage 5 (chunked); old n524k/ SIS timings are stale.

## Stages (run.sh; addressable = top-level rule; arms per group in run.sh g_access/g_enc)
A realNested + realNested+view (+view+ctor in bulk) x default/addressable/unrestricted, 10 main columns: comp (non-default, with
  --mlidc_dump_encoding) and timing. ETA ~5.5 h.
B Controls: realNested x 3 settings (comp + timing) + baseline arms timing. ~5.5 h.
C hybrid (re-priced) x 3 settings, 15 columns. ~7.5 h.
D + transforms (SIS/auto(+view), SIS/hybrid_auto(+view)), default, 15 columns. ~4.5 h.
E Baseline arms timing, 10 main columns. ~6.5 h.
F compzl for realNested/hybrid x addressable/unrestricted, 15 columns. ~1 h.
G Other SIS arms (key_derived, huffOn, huffOn/key_derived, +view), default, 15 columns. ~7 h.
Total ~38 h (+/- 30%), estimated by scaling the old per-column durations by arm count. Re-estimate after snowflake in Stage A.
Timing per group as the old run.sh: 3 interleaved repeats (settings interleaved within a repeat) of enc, bulk hot/cold,
point hot/cold (256 probes), gather hot, range hot; gather/range cold-payload once per setting. View open (build_ns) and
resident_bytes are in the bulk/point CSVs.

## Layout
full/<phase>_<column>_<group>-<setting>_r<rep>.csv; group rn|hy|tx|ot|base; base rows have setting "base".
comp: full/comp_<column>_<group>-<setting>.csv (+ .log with the plan dump), compzl_*.
reuse/MANIFEST.tsv: the reused old CSVs and which arms to use from them. checks/: the reuse evidence.

## Safety
Holds bench_timing.lock throughout; memory/disk watchdog (< 8 GB available, /data < 6 GB free, run dir > 10 GB); pre-run gate
(>= 20 GB memory, >= 10 GB /data); 4 h per-run timeout; touch STOP to stop; rerun resumes; DONE at the end.
Output estimate ~1-1.5 GB (old run dir 512 MB with 22 arms) + per-column encode cache (< 1 GB, deleted after each group);
/data had 26 GB free at launch.

2026-09-30 (the author): stages E (baseline rerun) and G (other SIS arms) dropped; old baseline timings reused (code unchanged, difference within repeat noise). Switch via STOP at Stage E start, then run_noEG.sh resumes (runs F only).
