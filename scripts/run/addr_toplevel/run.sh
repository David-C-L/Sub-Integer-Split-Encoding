#!/bin/bash
# Top-level addressability rule, 524,288 rows (feat/addressable-top-level merged into evaluation; see COMMIT,
# bin/SHA256SUMS). Setting file suffix `toplevel` = --mlidc_sis_section_candidates=addressable (the top-level
# rule since this commit; the strict rule is now =addressable_strict).
# Stage 1: comp + encoding dumps, 15 columns, SIS/realNested and SIS/realNested+view.
# Stage 2: SIS/realNested+view timing, 3 interleaved repeats, flags and metrics as addr_20260930_0257 and
#   addr_retime_20260930_1056: bulk hot (5 iters; bulk also +view+ctor), point hot and point cold-payload
#   (256 probes, 5 iters), range B=64 hot (16 offsets, seed 1). Encode cache per column (key has |sc3).
#   Also re-timed under the new build (RERUN below): the default/unrestricted cells whose plan has a
#   viewless RLE run-values or Dictionary alphabet child (fixed by rev-addr-toplevel-feat-base), and instagram unrestricted
#   (its FOR sections were last timed on rev-addr-for-timing, before the FOR view fixes of section 6).
# Also in each repeat of stage 2 (the coordinator's additions): (a) the Delta-swap pinned plans for snowflake
#   and s2 (SIS/pinned+view at addr_20260930_0257's default realNested boundaries, Delta kept vs withdrawn,
#   as that run's pinned stage) and (b) SIS/hybrid+view (bulk also +ctor) under default / toplevel /
#   unrestricted for the 5 columns with FrequencyPartition sections. Their comp + dumps are in stage 1.
# Stage 3: summary.tsv (sizes, sections, non-addressable streams below sections), summary_read.tsv.
# Holds bench_timing.lock for the whole script. Resumable (skips outputs that exist). touch STOP to stop.
set -u
O=$(cd "$(dirname "$0")" && pwd); cd "$O"
R=$HOSTDATA/project; DS=$R/Datasets; BIN=$O/bin; PROG=$O/progress.log
log() { echo "[$(date '+%F %T %Z')] $*" | tee -a "$PROG"; }
exec 9>>$R/bench_timing.lock; log "waiting for lock"; flock 9; log "lock held"
(cd "$BIN" && sha256sum -c --quiet SHA256SUMS) || { log "checksum mismatch"; exit 1; }
mkdir -p comp access cache
COLS="snowflake|TwitterSnowflake/csv/tweet_id_full.txt
xmark_prepost_full|XMark/csv/prepost_id_full.txt
osm_h3_r9_fileorder|OSM/csv/h3_r9_fileorder.txt
osm_s2_l30_fileorder|OSM/csv/s2_l30_fileorder.txt
bing_quadkey|BingTiles/csv/quadkey_fileorder_full.txt
uuidv7_hi|UUIDv7/csv/uuidv7_hi_10M.txt
uuidv7_lo|UUIDv7/csv/uuidv7_lo_10M.txt
publicbi_npi|PublicBI/Medicare1/csv/NPI_full.txt
publicbi_id1|PublicBI/Corporations/csv/Id1.txt
instagram|Instagram/instagram_id_full.txt
publicbi_drug_cost|PublicBI_controls_20260929/Medicare1_TOTAL_DRUG_COST_cents_full.txt
publicbi_bene_count|PublicBI_controls_20260929/Medicare1_BENE_COUNT_full.txt
publicbi_num_employees|PublicBI_controls_20260929/Corporations_num_employees_full.txt
publicbi_day_supply_bin|PublicBI_controls_20260929/Medicare1_Avg_Day_Supply_Bene_bin_full.txt
publicbi_drug_cost_ge65|PublicBI_controls_20260929_float/Medicare1_TOTAL_DRUG_COST_GE65_cents_full.txt"
RERUN=" uuidv7_hi:default uuidv7_hi:unrestricted publicbi_day_supply_bin:default publicbi_day_supply_bin:unrestricted publicbi_drug_cost:default instagram:unrestricted "
PIN_snowflake="0-3;4-11;12-17;18-21;22-50;51-58;59-60;61-63"
PIN_osm_s2_l30_fileorder="0-0;1-35;36-43;44-59;60-63"
FPCOLS=" snowflake osm_s2_l30_fileorder xmark_prepost_full bing_quadkey publicbi_bene_count "
# extra_for <col>: the pinned and hybrid settings a column also runs.
extra_for() { local s=""; case "$1" in snowflake|osm_s2_l30_fileorder) s="pinned_keep pinned_nodelta";; esac
  case "$FPCOLS" in *" $1 "*) s="$s hybrid-default hybrid-toplevel hybrid-unrestricted";; esac; echo $s; }
# xflags <setting> <col>: arm and setting flags of a pinned or hybrid setting.
xflags() { local pin; eval pin=\${PIN_$2:-}; case $1 in
  pinned_keep) echo "--mlidc_sis_pinned_boundaries=$pin --mlidc_sis_pinned_label=realnested";;
  pinned_nodelta) echo "--mlidc_sis_pinned_boundaries=$pin --mlidc_sis_pinned_label=realnested_nodelta --mlidc_sis_withdraw_nested_encodings=Delta";;
  hybrid-*) echo "--mlidc_sis_section_candidates=$(flag ${1#hybrid-})";; esac; }
xarm() { case $1 in pinned_*) echo SIS/pinned+view;; *) echo SIS/hybrid+view;; esac; }
xbulk() { case $1 in pinned_*) echo SIS/pinned+view;; *) echo SIS/hybrid+view,SIS/hybrid+view+ctor;; esac; }
xcomp() { case $1 in pinned_*) echo SIS/pinned,SIS/pinned+view;; *) echo SIS/hybrid,SIS/hybrid+view;; esac; }
flag() { [ "$1" = toplevel ] && echo addressable || echo "$1"; }
settings_for() { local s="toplevel"; for x in default unrestricted; do case "$RERUN" in *" $1:$x "*) s="$s $x";; esac; done; echo $s; }
stopped() { [ -f "$O/STOP" ]; }
run() { local out=$1 t rc; shift; [ -f "$out" ] && return 0; stopped && return 0; t=$(date +%s)
  echo "$* --mlidc_output_csv=$out" >> commands.txt
  "$@" --mlidc_output_csv="$out.tmp" > "$out.log" 2>&1; rc=$?
  if [ $rc -eq 0 ] && [ -f "$out.tmp" ]; then mv "$out.tmp" "$out"; log "  ok $(( $(date +%s)-t ))s $(basename $out)"
  else rm -f "$out.tmp"; log "FAIL rc=$rc $(basename $out)"; echo "$(basename $out)" >> failed.txt; fi; }
common() { echo "--mlidc_file=$DS/$2 --mlidc_dataset_name=$1 --mlidc_datasets=$1 --mlidc_dtype=uint64 --mlidc_rows=524288 --mlidc_input_order=shipped"; }
log "=== START $(cat COMMIT)"
log "=== Stage 1: comp + dumps"
while IFS='|' read -r n f; do
  run comp/comp_${n}_toplevel.csv $BIN/nimble_ml_id_compression_benchmark $(common $n $f) --mlidc_iters=1 --mlidc_encoders=SIS/realNested,SIS/realNested+view --mlidc_sis_section_candidates=addressable --mlidc_dump_encoding
  for s in $(extra_for $n); do
    run comp/comp_${n}_${s}.csv $BIN/nimble_ml_id_compression_benchmark $(common $n $f) --mlidc_iters=1 --mlidc_encoders=$(xcomp $s) $(xflags $s $n) --mlidc_dump_encoding
  done
done <<< "$COLS"
log "=== Stage 2: timing"
for r in 1 2 3; do while IFS='|' read -r n f; do for s in $(settings_for $n); do
  X="$(common $n $f) --mlidc_sis_section_candidates=$(flag $s) --mlidc_encode_cache_dir=$O/cache/$n"
  V="--mlidc_encoders=SIS/realNested+view"
  run access/bulk_hot_${n}_${s}_r$r.csv $BIN/nimble_ml_id_decode_bulk_benchmark $X --mlidc_encoders=SIS/realNested+view,SIS/realNested+view+ctor --cache_state=hot --mlidc_iters=5
  run access/point_hot_${n}_${s}_r$r.csv $BIN/nimble_ml_id_decode_point_benchmark $X $V --cache_state=hot --mlidc_iters=5 --probes=256 --mlidc_block_codec_probes=256
  run access/point_cold_${n}_${s}_r$r.csv $BIN/nimble_ml_id_decode_point_benchmark $X $V --cache_state=cold-payload --mlidc_iters=5 --probes=256 --mlidc_block_codec_probes=256
  run access/range64_hot_${n}_${s}_r$r.csv $BIN/nimble_ml_id_decode_range_benchmark $X $V --cache_state=hot --mlidc_iters=5 --mlidc_block_codec_iters=3 --range_sizes=64 --range_offsets_by_size=16 --mlidc_seed=1
done
  for s in $(extra_for $n); do
    X="$(common $n $f) $(xflags $s $n) --mlidc_encode_cache_dir=$O/cache/$n"; V="--mlidc_encoders=$(xarm $s)"
    run access/bulk_hot_${n}_${s}_r$r.csv $BIN/nimble_ml_id_decode_bulk_benchmark $X --mlidc_encoders=$(xbulk $s) --cache_state=hot --mlidc_iters=5
    run access/point_hot_${n}_${s}_r$r.csv $BIN/nimble_ml_id_decode_point_benchmark $X $V --cache_state=hot --mlidc_iters=5 --probes=256 --mlidc_block_codec_probes=256
    run access/point_cold_${n}_${s}_r$r.csv $BIN/nimble_ml_id_decode_point_benchmark $X $V --cache_state=cold-payload --mlidc_iters=5 --probes=256 --mlidc_block_codec_probes=256
    run access/range64_hot_${n}_${s}_r$r.csv $BIN/nimble_ml_id_decode_range_benchmark $X $V --cache_state=hot --mlidc_iters=5 --mlidc_block_codec_iters=3 --range_sizes=64 --range_offsets_by_size=16 --mlidc_seed=1
  done
done <<< "$COLS"; log "repeat $r done"; done
log "=== Stage 3: summary"
python3 summarise.py "$O" > summary.tsv 2> summary.err && python3 summarise_read.py "$O" > summary_read.tsv 2>> summary.err && log "summaries written"
stopped && { log "=== STOPPED"; exit 0; }
log "=== DONE"; touch DONE
