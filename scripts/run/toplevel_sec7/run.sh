#!/bin/bash
# toplevel_sec7: regenerate the Sec. 7 data with SIS in addressable TopLevel mode
# (--mlidc_sis_section_candidates=addressable = SectionCandidates::kAddressableTopLevel = 3), every arm,
# SIS and baselines, on ONE build: bin/ (see build/README in this dir and COMMIT).
# Harnesses mirrored, only the SIS mode changed (flag added to every command):
#   U1 sweep comp+compzl (w524_tl.sh phases 1,2; sweep_full.sh line 15)          -> sweep/comp_*, compzl_*
#   U2 composition ladder at full length (addr_ladder_20261007_1847 run1/run2):
#      arm1 SIS/realNested(+openzl/auto), arm3 +OpenZL substreams, pinned check, Arm A raw on the TopLevel split
#                                                                                -> ladder/
#   U3 cross-format Nimble row, sizes (cross_format_clean_20260929_1705/nimble_rep.sh, comp only) -> xf/
#   U4 planner gap plans + comp (plan_decode_20260928_2303/plan_decode.sh steps 1-2) -> plan_decode/
#   U5 comp checks of simdfor_view (fig6 baseline) and ablation (a) block sweep  -> simdfor_view/, abl_a/
#   T1 sweep timing: shipped hot r1-3 phases 34567, cold-payload gather/range r1, mergeirr_8 hot r1-2 (sweep_full.sh 17-19)
#   T2 admission, 42 columns (sweep_full.sh 42-45)                               -> admission/
#   T3 gather4 grid, 3 reps (sweep_full.sh 47-61)                                -> gather4/
#   T4 simdfor_view point + range64, 3 reps (addr_toplevel_20260930_1127/simdfor_view.sh) -> simdfor_view/
#   T5 planner gap timing, 3 reps (plan_decode.sh step 3)                         -> plan_decode/access/
#   T6 block sweep point + range, 3 reps (ablations_20260928_2223 run.sh stage a) -> abl_a/
# U* time nothing and run without the timing lock, before T*. T* hold both timing locks throughout.
# Resumable (finished CSVs skipped). touch STOP to stop before the next run.
set -u
O=$RESULTS/toplevel_sec7_20261014_1526; cd $O
R=$HOSTDATA/project; DS=$R/Datasets; B=$O/bin; PROG=$O/progress.log
SC="--mlidc_sis_section_candidates=addressable"
L1=$RESULTS/bench_timing.lock; L2=$R/bench_timing.lock
log() { echo "[$(date '+%F %T %Z')] $*" | tee -a "$PROG"; }
stopped() { [ -f $O/STOP ]; }
run() { local out=$1 t rc; shift; [ -f "$out" ] && return 0; stopped && return 0; t=$(date +%s)
  echo "$* --mlidc_output_csv=$out" >> $O/commands.txt
  "$@" --mlidc_output_csv="$out.tmp" > "${out%.csv}.log" 2>&1; rc=$?
  if [ $rc -eq 0 ] && [ -f "$out.tmp" ]; then mv "$out.tmp" "$out"; log "  ok $(( $(date +%s)-t ))s ${out#$O/}"
  else rm -f "$out.tmp"; log "FAIL rc=$rc ${out#$O/}"; echo "${out#$O/}" >> $O/failed.txt; fi; }
busy() { ps -eo stat=,comm= | awk '$1 !~ /^Z/ && ($2=="ninja" || $2=="cc1plus" || $2=="cc1") {f=1} END {exit !f}'; }
tload() { echo "[$(date +%T)] $1 load: $(cut -d' ' -f1-3 /proc/loadavg) build_running: $(busy && echo yes || echo no)" >> $O/timing_load.log; }
(cd $B && sha256sum -c --quiet SHA256SUMS) || { log "checksum mismatch"; exit 1; }
mkdir -p sweep ladder xf/nimble_raw plan_decode/plans plan_decode/comp plan_decode/access simdfor_view abl_a admission gather4 encode_cache
log "=== START $(cat COMMIT)"

# ---------------- U: untimed, no lock ----------------
log "=== U1 sweep comp (9 columns in parallel), U2 ladder, U4 oracle, in parallel"
export SWEEP_EXTRA_ARMS="SIS/hybrid_auto,SIS/hybrid_auto+view" SWEEP_EXTRA_ENCODE="SIS/hybrid_auto" SWEEP_EXTRA_COMP="RLE+nestedSIS,Dictionary+nestedSIS,MainlyConstant+nestedSIS,FPE/fpe_pertier+nestedSIS"
for col in snowflake xmark_prepost_full osm_h3_r9_fileorder osm_s2_l30_fileorder publicbi_npi publicbi_id1 bing_quadkey uuidv7_hi uuidv7_lo; do
  bash $O/w524_tl.sh "^$col\|" "1" "12" > $O/sweep/comp_$col.log 2>&1 &
done

# U2: composition ladder, full length (columns, files and rows as ADDRESSABILITY_LADDER_SIZES_20261007.md)
ladder_col() { local n=$1 f=$2 rows=$3 L tree hdr split rf X
  X="--mlidc_file=$DS/$f --mlidc_dataset_name=$n --mlidc_datasets=$n --mlidc_dtype=uint64 --mlidc_rows=$rows --mlidc_input_order=shipped --mlidc_iters=1 --mlidc_dump_encoding $SC"
  run $O/ladder/arm15_$n.csv $B/nimble_ml_id_compression_benchmark $X --mlidc_encoders=SIS/realNested,openzl/auto
  run $O/ladder/arm3_$n.csv $B/nimble_ml_id_compression_benchmark $X --mlidc_encoders=SIS/realNested --mlidc_substream_compression=OpenZL
  L=$O/ladder/arm15_$n.log; [ -f $O/ladder/arm15_$n.csv ] || return 0
  tree=$(awk '/--- SIS\/realNested encoding tree ---/{on=1;next} on&&/--- /{exit} on' $L)
  hdr=$(echo "$tree" | grep -m1 '^SubIntSplitEncoding')
  [ -z "$hdr" ] && { log "NOSIS $n"; return 0; }
  split=$(echo "$tree" | sed -n 's/^  \[\([0-9]*\)\.\.\([0-9]*\)\] .*/\1-\2/p' | paste -sd';')
  rf=""; case "$hdr" in *rowFrame=*) rf="--mlidc_sis_pinned_row_frame";; esac
  echo "$n	$split	${rf:-no_row_frame}	$hdr" > $O/ladder/split_$n.tsv
  run $O/ladder/pinned_default_$n.csv $B/nimble_ml_id_compression_benchmark $X --mlidc_encoders=SIS/pinned "--mlidc_sis_pinned_boundaries=$split" $rf --mlidc_sis_pinned_label=default_split
  run $O/ladder/armA_$n.csv $B/nimble_ml_id_compression_benchmark $X --mlidc_encoders=SIS/pinned "--mlidc_sis_pinned_boundaries=$split" $rf --mlidc_sis_pinned_label=default_split_trivial --mlidc_sis_allowed_encodings=Trivial --mlidc_substream_compression=OpenZL
}
while IFS='|' read -r n f rows; do ladder_col $n $f $rows & done <<'COLS'
snowflake|TwitterSnowflake/csv/tweet_id_full.txt|10000000
xmark_prepost_full|XMark/csv/prepost_id_full.txt|10000000
osm_h3_r9_fileorder|OSM/csv/h3_r9_fileorder.txt|10000000
osm_s2_l30_fileorder|OSM/csv/s2_l30_fileorder.txt|10000000
bing_quadkey|BingTiles/csv/quadkey_fileorder_full.txt|9869460
uuidv7_hi|UUIDv7/csv/uuidv7_hi_10M.txt|10000000
publicbi_npi|PublicBI/Medicare1/csv/NPI_full.txt|17290144
publicbi_id1|PublicBI/Corporations/csv/Id1.txt|739754
uuidv7_lo|UUIDv7/csv/uuidv7_lo_10M.txt|10000000
COLS

# U4: planner gap, step 1 (whole-column oracle, patched driver honours $SC)
P=$O/plan_decode; SNOW=$DS/TwitterSnowflake/csv/tweet_id.txt; H3=$DS/OSM/csv/h3_r9_fileorder.txt
PCOMMON="--mlidc_dtype=uint64 --mlidc_rows=524288 --mlidc_input_order=shipped $SC"
PCOLS="$SNOW|snowflake $H3|osm_h3_r9_fileorder"
for u in $PCOLS; do f=${u%%|*}; n=${u##*|}
  run $P/plans/oracle_$n.csv $B/nimble_ml_id_cost_model_oracle_benchmark --mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n $PCOMMON --sample_sizes=0 &
done
wait; log "U1/U2/U4-oracle done"

# U4 step 1b-2: plan table, bits/value
(cd $P && python3 - <<'PY'
import csv
for n in ['snowflake','osm_h3_r9_fileorder']:
    rows=list(csv.DictReader(open(f'plans/oracle_{n}.csv'))); N='524288'
    out=[]
    for r in rows:
        if r['plan_type']=='writer_reproduction': out.append((('writer'),r['plan_segment_count'],r['plan_boundaries'],r['writer_recompute_bytes']))
    for lab in ['oracle_dp','estimator_dp','oracle_dp_selection']:
        for r in rows:
            if r['plan_type']==lab+'_summary' and r['sample_size']==N: out.append((lab,r['plan_segment_count'],r['plan_boundaries'],r['full_column_bytes']))
    with open(f'plans/plans_{n}.tsv','w') as f:
        f.write('label\tsections\tboundaries\toracle_full_column_bytes\n')
        for o in out: f.write('\t'.join(o)+'\n')
PY
) || log "FAIL plans tsv"
PLANS="writer oracle_dp estimator_dp oracle_dp_selection"
bnd() { awk -F'\t' -v l=$2 '$1==l{print $3}' $P/plans/plans_$1.tsv; }
for u in $PCOLS; do f=${u%%|*}; n=${u##*|}
  run $P/comp/comp_${n}_base.csv $B/nimble_ml_id_compression_benchmark --mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n $PCOMMON --mlidc_iters=1 \
    --mlidc_encoders=SIS/realNested,SIS/realNested+view,SIS/hybrid,SIS/hybrid+view --mlidc_dump_encoding
  for l in $PLANS; do
    run $P/comp/comp_${n}_$l.csv $B/nimble_ml_id_compression_benchmark --mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n $PCOMMON --mlidc_iters=1 \
      --mlidc_encoders=SIS/pinned,SIS/pinned+view --mlidc_sis_pinned_boundaries="$(bnd $n $l)" --mlidc_sis_pinned_label=$l --mlidc_dump_encoding
  done
done

# U3: cross-format Nimble row, sizes (nimble_rep.sh rep 1 comp line)
SH=Trivial,Constant,Dictionary,RLE,PFOR,MainlyConstant,SparseBool,FixedBitWidth
declare -A XLIST=([auto]=$SH [auto_sis]=$SH,SubIntSplit)
for c in TwitterSnowflake/csv/tweet_id.txt:snowflake XMark/csv/prepost_id_full.txt:xmark_prepost_full OSM/csv/h3_r9_fileorder.txt:osm_h3_r9_fileorder OSM/csv/s2_l30_fileorder.txt:osm_s2_l30_fileorder BingTiles/csv/quadkey_fileorder.txt:bing_quadkey UUIDv7/csv/uuidv7_hi.txt:uuidv7_hi UUIDv7/csv/uuidv7_lo.txt:uuidv7_lo PublicBI/Medicare1/csv/NPI.txt:publicbi_npi PublicBI/Corporations/csv/Id1.txt:publicbi_id1; do
  f=$DS/${c%%:*}; n=${c##*:}
  for arm in auto auto_sis; do
    run $O/xf/nimble_raw/${arm}_${n}_r1_comp.csv $B/nimble_ml_id_compression_benchmark --mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n --mlidc_dtype=uint64 --mlidc_rows=524288 --mlidc_input_order=shipped --mlidc_output_manifest= --mlidc_encoders=Auto/view --mlidc_auto_encodings=${XLIST[$arm]} --mlidc_sis_allowed_encodings=$SH --mlidc_seed=1 $SC --mlidc_iters=1 --mlidc_dump_encoding
  done
done

# U5: size checks for the fig6 baseline and the block sweep
COLS9="snowflake|TwitterSnowflake/csv/tweet_id.txt
xmark_prepost_full|XMark/csv/prepost_id_full.txt
osm_h3_r9_fileorder|OSM/csv/h3_r9_fileorder.txt
osm_s2_l30_fileorder|OSM/csv/s2_l30_fileorder.txt
publicbi_npi|PublicBI/Medicare1/csv/NPI.txt
publicbi_id1|PublicBI/Corporations/csv/Id1.txt
bing_quadkey|BingTiles/csv/quadkey_fileorder.txt
uuidv7_hi|UUIDv7/csv/uuidv7_hi.txt
uuidv7_lo|UUIDv7/csv/uuidv7_lo.txt"
while IFS='|' read -r n f; do
  run $O/simdfor_view/comp_${n}_shipped.csv $B/nimble_ml_id_compression_benchmark --mlidc_file=$DS/$f --mlidc_dataset_name=$n --mlidc_datasets=$n --mlidc_dtype=uint64 --mlidc_rows=524288 --mlidc_input_order=shipped --mlidc_iters=1 --mlidc_encoders=SimdForBitpack/view $SC
done <<< "$COLS9"
BS=64,128,256,512,1024,2048,4096,8192,16384,32768,65536
AARMS=openzl/auto; for k in ${BS//,/ }; do AARMS=$AARMS,zstd/block-$k,openzl/block-$k; done
for u in $PCOLS; do f=${u%%|*}; n=${u##*|}
  run $O/abl_a/comp_$n.csv $B/nimble_ml_id_compression_benchmark --mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n $PCOMMON --mlidc_iters=1 --mlidc_block_sizes=$BS --mlidc_encoders=$AARMS
done
log "=== U done fails=$(cat $O/failed.txt 2>/dev/null | wc -l) sweep_comp_fails=$(cat $O/sweep/comp_*.log | grep -c FAIL)"
stopped && { log "=== STOPPED"; exit 0; }

# ---------------- T: timed, both locks held throughout ----------------
exec 8>>$L1; log "waiting for $L1"; flock 8; exec 9>>$L2; log "waiting for $L2"; flock 9
w=0; while busy && [ $w -lt 3600 ]; do sleep 30; w=$((w+30)); done
log "=== T locks held; waited ${w}s for builds; load $(cut -d' ' -f1-3 /proc/loadavg)"
log "=== T1 sweep timing"
bash $O/w524_tl.sh "shipped$" "1 2 3" "34567" "hot" >> $O/sweep/sweep_timing.log 2>&1
BPCS=hot bash $O/w524_tl.sh "shipped$" "1" "67" "cold-payload" >> $O/sweep/sweep_timing.log 2>&1
bash $O/w524_tl.sh "mergeirr_8$" "1 2" "34567" "hot" >> $O/sweep/sweep_timing.log 2>&1
log "T1 done fails=$(grep -c FAIL $O/sweep/sweep_timing.log)"

log "=== T2 admission"
while read n p dt rows; do
  [ -f $R/Datasets/$p ] || { log "FAIL missing $p"; continue; }
  run $O/admission/$n.csv $B/nimble_ml_id_admission_benchmark --mlidc_file=$R/Datasets/$p --mlidc_dataset_name=$n --mlidc_datasets=$n --mlidc_dtype=$dt --mlidc_rows=$rows --mlidc_input_order=shipped --mlidc_encoders=Trivial,FixedBitWidth,Dictionary,RLE,MainlyConstant,PFOR/view,SimdForBitpack/view,FPE/fpe_pertier,SIS/realNested,SIS/hybrid $SC
done < $O/admission/columns.txt

log "=== T3 gather4"
G4ARMS="SIS/realNested+view,SIS/hybrid+view,SIS/hybrid_auto+view,openzl/auto,openzl/block-1024,openzl/block-65536,FixedBitWidth/view"
for rep in 1 2 3; do while read n f dt; do
  run $O/gather4/gather_hot_${n}_shipped_r$rep.csv $B/nimble_ml_id_decode_gather_benchmark --mlidc_file=$R/Datasets/$f --mlidc_dataset_name=$n --mlidc_datasets=$n --mlidc_dtype=uint64 --mlidc_rows=524288 --mlidc_input_order=shipped --cache_state=hot --mlidc_iters=2 --mlidc_encoders=$G4ARMS --selectivity_values=0.001,0.01,0.05,0.10,0.33,0.66 --run_length_values=1,2,8,111,1024,12417,131072 --mlidc_encode_cache_dir=$O/encode_cache $SC
done <<'COLS'
snowflake TwitterSnowflake/csv/tweet_id.txt u
xmark_prepost_full XMark/csv/prepost_id_full.txt u
osm_h3_r9_fileorder OSM/csv/h3_r9_fileorder.txt u
osm_s2_l30_fileorder OSM/csv/s2_l30_fileorder.txt u
publicbi_npi PublicBI/Medicare1/csv/NPI.txt u
publicbi_id1 PublicBI/Corporations/csv/Id1.txt u
bing_quadkey BingTiles/csv/quadkey_fileorder.txt u
uuidv7_hi UUIDv7/csv/uuidv7_hi.txt u
uuidv7_lo UUIDv7/csv/uuidv7_lo.txt u
COLS
done

log "=== T4 simdfor_view"
for r in 1 2 3; do while IFS='|' read -r n f; do
  X="--mlidc_file=$DS/$f --mlidc_dataset_name=$n --mlidc_datasets=$n --mlidc_dtype=uint64 --mlidc_rows=524288 --mlidc_input_order=shipped --cache_state=hot --mlidc_iters=5 --mlidc_encoders=SimdForBitpack/view --mlidc_encode_cache_dir=$O/encode_cache/simdfor_$n $SC"
  run $O/simdfor_view/point_${n}_shipped_r$r.csv $B/nimble_ml_id_decode_point_benchmark $X --probes=256 --mlidc_block_codec_probes=256
  run $O/simdfor_view/range64_${n}_shipped_r$r.csv $B/nimble_ml_id_decode_range_benchmark $X --mlidc_block_codec_iters=3 --range_sizes=64 --range_offsets_by_size=16 --mlidc_seed=$r
done <<< "$COLS9"; done

log "=== T5 planner gap timing"
RS=1,8,64,512,4096,32768,131072,524288; RO=8,8,16,32,32,16,8,1
for rep in 1 2 3; do for u in $PCOLS; do f=${u%%|*}; n=${u##*|}
  for g in base $PLANS; do
    if [ $g = base ]; then A=(--mlidc_encoders=SIS/realNested,SIS/realNested+view,SIS/hybrid,SIS/hybrid+view)
    else A=(--mlidc_encoders=SIS/pinned,SIS/pinned+view "--mlidc_sis_pinned_boundaries=$(bnd $n $g)" --mlidc_sis_pinned_label=$g); fi
    C="--mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n $PCOMMON --cache_state=hot"
    tload bulk_${n}_${g}_r$rep; run $P/access/bulk_${n}_${g}_r$rep.csv $B/nimble_ml_id_decode_bulk_benchmark $C --mlidc_iters=5 "${A[@]}"
    tload point_${n}_${g}_r$rep; run $P/access/point_${n}_${g}_r$rep.csv $B/nimble_ml_id_decode_point_benchmark $C --mlidc_iters=5 --probes=256 --mlidc_block_codec_probes=256 "${A[@]}"
    tload range_${n}_${g}_r$rep; run $P/access/range_${n}_${g}_r$rep.csv $B/nimble_ml_id_decode_range_benchmark $C --mlidc_iters=5 --range_sizes=$RS --range_offsets_by_size=$RO --mlidc_seed=$rep "${A[@]}"
    tload gather_${n}_${g}_r$rep; run $P/access/gather_${n}_${g}_r$rep.csv $B/nimble_ml_id_decode_gather_benchmark $C --mlidc_iters=2 --selectivity_values=0.001,0.01,0.05,0.10,0.33,0.66,1.0 --run_length_values=1,111,12417,131072 "${A[@]}"
  done
done; done

log "=== T6 block sweep timing"
for rep in 1 2 3; do for u in $PCOLS; do f=${u%%|*}; n=${u##*|}
  tload abl_point_${n}_r$rep; run $O/abl_a/point_${n}_r$rep.csv $B/nimble_ml_id_decode_point_benchmark --mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n $PCOMMON \
    --mlidc_iters=3 --probes=4096 --mlidc_block_sizes=$BS --mlidc_encoders=${AARMS#openzl/auto,}
  tload abl_range_${n}_r$rep; run $O/abl_a/range_${n}_r$rep.csv $B/nimble_ml_id_decode_range_benchmark --mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n $PCOMMON \
    --mlidc_iters=3 --range_sizes=64,4096 --range_offsets=16 --mlidc_block_sizes=$BS --mlidc_encoders=${AARMS#openzl/auto,}
done; done
flock -u 9; flock -u 8; exec 9>&- 8>&-
log "=== T done, locks released; fails=$(cat $O/failed.txt 2>/dev/null | wc -l)"
stopped && { log "=== STOPPED"; exit 0; }
log "=== DONE"; touch $O/DONE
