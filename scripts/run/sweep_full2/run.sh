#!/bin/bash
# sweep_full2: resumed full-length SIS evaluation on evaluation rev-addr-toplevel (binaries in bin/, SHA256SUMS).
# Reuses sweep_full_20260929_0115 default comp (all arms); its baseline timing only until Stage E lands; see README.md, reuse/.
# Stages (headline first):
#   A  realNested x {default,addressable,unrestricted}: comp (non-default) + timing, 10 main columns
#   B  controls (5): realNested x 3 settings comp+timing, and baseline arms timing
#   C  hybrid x 3 settings: comp (non-default) + timing, 15 columns
#   D  + transforms (SIS/auto, SIS/hybrid_auto; default): timing, 15 columns
#   E  baseline arms timing, 10 main columns (the reuse spot-check failed: 5/16 cells outside 5%; see README)
#   F  compzl (OpenZL substreams) for realNested+hybrid, addressable+unrestricted, 15 columns
#   G  other SIS arms (key_derived, huffOn, huffOn/key_derived; default): timing, 15 columns
# Timing per group, as the old run.sh: 3 interleaved repeats of enc, bulk hot/cold, point hot/cold, gather hot,
# range hot (settings interleaved inside each repeat); then gather/range cold-payload once per setting.
# View open time and resident bytes come from the point/bulk CSVs (build_ns, resident_bytes); +view+ctor in bulk.
# Control: touch STOP to stop before the next run; rerun resumes (finished CSVs skipped). Writes DONE.
# Watchdog kills the running child group if MemAvailable < 8 GB, /data < 6 GB free or run dir > 10 GB.
set -u
O=$(cd "$(dirname "$0")" && pwd); cd $O
R=$HOSTDATA/project; DS=$R/Datasets; L=$R/bench_timing.lock
BIN=$O/bin; P=$O/progress.log; D=$O/full
. $O/sweep_config.sh
MAIN="snowflake|TwitterSnowflake/csv/tweet_id_full.txt|10000000
instagram|Instagram/instagram_id_full.txt|1536841
osm_h3_r9_fileorder|OSM/csv/h3_r9_fileorder.txt|10000000
osm_s2_l30_fileorder|OSM/csv/s2_l30_fileorder.txt|10000000
xmark_prepost_full|XMark/csv/prepost_id_full.txt|10000000
bing_quadkey|BingTiles/csv/quadkey_fileorder_full.txt|9869460
uuidv7_hi|UUIDv7/csv/uuidv7_hi_10M.txt|10000000
publicbi_npi|PublicBI/Medicare1/csv/NPI_full.txt|17290144
publicbi_id1|PublicBI/Corporations/csv/Id1.txt|739754
uuidv7_lo|UUIDv7/csv/uuidv7_lo_10M.txt|10000000"
CTRL="publicbi_drug_cost|PublicBI_controls_20260929/Medicare1_TOTAL_DRUG_COST_cents_full.txt|17290144
publicbi_bene_count|PublicBI_controls_20260929/Medicare1_BENE_COUNT_full.txt|17290144
publicbi_num_employees|PublicBI_controls_20260929/Corporations_num_employees_full.txt|739752
publicbi_day_supply_bin|PublicBI_controls_20260929/Medicare1_Avg_Day_Supply_Bene_bin_full.txt|17290144
publicbi_drug_cost_ge65|PublicBI_controls_20260929_float/Medicare1_TOTAL_DRUG_COST_GE65_cents_full.txt|10281398"
ALL="$MAIN
$CTRL"
GE65_SHA=0c405e34efea1f915de52c8724e19d13fd0f4d4d1bba87ff4378f943703dd7df
SETS3="default addressable unrestricted"   # addressable = top-level rule (rev-addr-toplevel)

# Arm groups: access arms | extra bulk arms | encode arms
g_access() { case $1 in
  rn) echo "SIS/realNested,SIS/realNested+view";;
  hy) echo "SIS/hybrid,SIS/hybrid+view";;
  tx) echo "SIS/auto,SIS/auto+view,SIS/hybrid_auto,SIS/hybrid_auto+view";;
  ot) echo "SIS/key_derived,SIS/key_derived+view,SIS/huffOn,SIS/huffOn+view,SIS/huffOn/key_derived,SIS/huffOn/key_derived+view";;
  base) echo "openzl/auto,FixedBitWidth,FixedBitWidth/view,FPE/fpe_noindex,FPE/fpe_pertier,FPE/fpe_elias,openzl/block-1024,openzl/block-65536";; esac; }
g_bulkx() { case $1 in rn) echo ",SIS/realNested+view+ctor";; hy) echo ",SIS/hybrid+view+ctor";; ot) echo ",SIS/key_derived+view+ctor";; *) echo "";; esac; }
g_enc() { case $1 in
  rn) echo "SIS/realNested";; hy) echo "SIS/hybrid";; tx) echo "SIS/auto,SIS/hybrid_auto";;
  ot) echo "SIS/key_derived,SIS/huffOn,SIS/huffOn/key_derived";;
  base) echo "openzl/auto,FixedBitWidth,FPE/fpe_noindex,FPE/fpe_pertier,FPE/fpe_elias,openzl/block-1024,openzl/block-65536";; esac; }

log() { echo "[$(date '+%F %T %Z')] $*" | tee -a $P; }
hostinfo() { echo "load=$(cut -d' ' -f1-3 /proc/loadavg) memavail_gb=$(awk '/MemAvailable/{printf "%d",$2/1048576}' /proc/meminfo) data_free_gb=$(df -BG --output=avail /data | tail -1 | tr -dc 0-9)"; }
stopped() { [ -f $O/STOP ]; }

watchdog() { while :; do sleep 20
  ma=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo); fr=$(df -BG --output=avail /data | tail -1 | tr -dc 0-9)
  used=$(du -s -BG $O 2>/dev/null | cut -f1 | tr -dc 0-9); bad=""
  [ "$ma" -lt 8 ] && bad="low memory ${ma}GB"; [ "$fr" -lt 6 ] && bad="low disk ${fr}GB free"
  [ "$used" -gt 10 ] && bad="output dir ${used}GB > 10GB budget"
  if [ -n "$bad" ]; then echo "watchdog: $bad" > $O/STOP; pg=$(cat $O/current.pgid 2>/dev/null)
    [ -n "$pg" ] && kill -TERM -- -$pg 2>/dev/null; log "WATCHDOG $bad; killed pgid ${pg:-none}"; fi
done; }

# Pre-run gate: wait up to 20 min for >= 20 GB available memory and >= 10 GB free on /data.
gate() { for i in $(seq 1 40); do
  ma=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo); fr=$(df -BG --output=avail /data | tail -1 | tr -dc 0-9)
  [ "$ma" -ge 20 ] && [ "$fr" -ge 10 ] && return 0; [ $i -eq 1 ] && log "  waiting: mem ${ma}GB disk ${fr}GB"; sleep 30; done
  log "  gate failed (mem ${ma}GB disk ${fr}GB)"; return 1; }

# run <out.csv> <cmd...>: skip if done; own process group; 4 h timeout; ok/FAIL line.
run() { local out=$1 t0 pid rc; shift; [ -f "$out" ] && return 0
  if stopped; then echo "SKIPPED $(basename $out)" >> $O/skipped.txt; return 0; fi
  gate || { echo "SKIPPED(gate) $(basename $out)" >> $O/skipped.txt; return 0; }
  t0=$(date +%s); echo "$* --mlidc_output_csv=$out" >> $O/commands.txt
  setsid timeout -s TERM 4h "$@" --mlidc_output_csv=$out.tmp --mlidc_output_manifest=$out.manifest.json > $out.log 2>&1 &
  pid=$!; echo $pid > $O/current.pgid; wait $pid; rc=$?; rm -f $O/current.pgid
  if [ $rc -eq 0 ] && [ -f $out.tmp ]; then mv $out.tmp $out; log "    ok $(( $(date +%s)-t0 ))s $(basename $out)  [$(hostinfo)]"
  else rm -f $out.tmp; log "    FAIL rc=$rc $(( $(date +%s)-t0 ))s $(basename $out)"; echo "$(basename $out)" >> $O/failed.txt; fi; }

common() { echo "--mlidc_file=$DS/$2 --mlidc_dataset_name=$1 --mlidc_datasets=$1 --mlidc_dtype=uint64 --mlidc_rows=$3 --mlidc_input_order=shipped"; }
scf() { [ "$1" = base ] && echo "" || echo "--mlidc_sis_section_candidates=$1"; }

# comp_grp <n> <f> <N> <grp> <setting> [zl]: compression (+ plan dump) for one group and setting.
comp_grp() { local n=$1 f=$2 N=$3 g=$4 s=$5 zl=${6:-}
  if [ -z "$zl" ]; then run $D/comp_${n}_${g}-${s}.csv $BIN/nimble_ml_id_compression_benchmark $(common $n $f $N) --mlidc_iters=1 --mlidc_encoders="$(g_access $g)" $(scf $s) --mlidc_dump_encoding
  else run $D/compzl_${n}_${g}-${s}.csv $BIN/nimble_ml_id_compression_benchmark $(common $n $f $N) --mlidc_iters=1 --mlidc_encoders="$(g_access $g)" $(scf $s) --mlidc_substream_compression=OpenZL; fi; }

# timing_grp <n> <f> <N> <grp> <settings...>: as the old timing_col, settings interleaved within each repeat.
timing_grp() { local n=$1 f=$2 N=$3 g=$4; shift 4; local sets="$*" C=$O/cache_$n CM rep s T X A
  mkdir -p $C; CM=$(common $n $f $N); local RS="1,8,64,512,4096,32768,131072,$N" EC="--mlidc_encode_cache_dir=$C"
  A=$(g_access $g)
  for rep in 1 2 3; do for s in $sets; do T=${g}-${s}; X=$(scf $s)
    run $D/enc_${n}_${T}_r$rep.csv $BIN/nimble_ml_id_encode_benchmark $CM $X --mlidc_iters=1 --mlidc_encoders="$(g_enc $g)"
    for drv in bulk point; do PX=""; EA=$A; [ $drv = point ] && PX="--probes=256 --mlidc_block_codec_probes=256"; [ $drv = bulk ] && EA="$A$(g_bulkx $g)"
      for cs in hot cold-payload; do c=$(echo $cs | tr - _)
        run $D/${drv}_${c}_${n}_${T}_r$rep.csv $BIN/nimble_ml_id_decode_${drv}_benchmark $CM $X --cache_state=$cs --mlidc_iters=5 --mlidc_encoders="$EA" $PX $EC; done; done
    run $D/gather_hot_${n}_${T}_r$rep.csv $BIN/nimble_ml_id_decode_gather_benchmark $CM $X --cache_state=hot --mlidc_iters=2 --mlidc_encoders="$A" --selectivity_values=$GATHER_SELECTIVITY --run_length_values=$GATHER_RUN_LENGTHS $EC
    run $D/range_hot_${n}_${T}_r$rep.csv $BIN/nimble_ml_id_decode_range_benchmark $CM $X --cache_state=hot --mlidc_iters=5 --mlidc_block_codec_iters=3 --mlidc_encoders="$A" --range_sizes=$RS --range_offsets_by_size=$RANGE_OFFSETS_BY_SIZE --mlidc_seed=$rep
  done; done
  for s in $sets; do T=${g}-${s}; X=$(scf $s)
    run $D/gather_cold_payload_${n}_${T}_r1.csv $BIN/nimble_ml_id_decode_gather_benchmark $CM $X --cache_state=cold-payload --mlidc_iters=2 --mlidc_encoders="$A" --selectivity_values=$GATHER_SELECTIVITY --run_length_values=$GATHER_RUN_LENGTHS $EC
    run $D/range_cold_payload_${n}_${T}_r1.csv $BIN/nimble_ml_id_decode_range_benchmark $CM $X --cache_state=cold-payload --mlidc_iters=5 --mlidc_block_codec_iters=3 --mlidc_encoders="$A" --range_sizes=$RS --range_offsets_by_size=$RANGE_OFFSETS_BY_SIZE --mlidc_seed=1
  done
  log "    cache $n: $(du -sh $C | cut -f1), removed"; rm -rf $C; }

stage() { log "=== $1 START [$(hostinfo)]"; }

rm -f $O/current.pgid
exec 9>$L; log "waiting for timing lock $L"; flock 9; log "timing lock held"
(cd $BIN && sha256sum -c --quiet SHA256SUMS) || { log "bin checksum mismatch"; exit 1; }
got=$(sha256sum $DS/PublicBI_controls_20260929_float/Medicare1_TOTAL_DRUG_COST_GE65_cents_full.txt | cut -c1-64)
[ "$got" = "$GE65_SHA" ] || { log "float control sha256 mismatch ($got); dropping publicbi_drug_cost_ge65"; CTRL=$(echo "$CTRL" | grep -v ge65); ALL="$MAIN
$CTRL"; }
watchdog & WD=$!; trap 'kill $WD 2>/dev/null; pg=$(cat $O/current.pgid 2>/dev/null); [ -n "$pg" ] && kill -TERM -- -$pg 2>/dev/null' EXIT
trap 'log "SIGTERM received"; echo "SIGTERM" > $O/STOP; exit 143' TERM
mkdir -p $D
log "commit $(cat $O/COMMIT)"

stage "Stage A realNested x 3 settings, 10 main columns"
while IFS='|' read -r n f N; do log "  A $n N=$N START"
  for s in addressable unrestricted; do comp_grp $n $f $N rn $s; done
  timing_grp $n $f $N rn $SETS3; log "  A $n END"; done <<< "$MAIN"

stage "Stage B controls: realNested x 3 settings + baselines"
while IFS='|' read -r n f N; do log "  B $n N=$N START"
  for s in addressable unrestricted; do comp_grp $n $f $N rn $s; done
  timing_grp $n $f $N rn $SETS3; timing_grp $n $f $N base base; log "  B $n END"; done <<< "$CTRL"

stage "Stage C hybrid (re-priced) x 3 settings, 15 columns"
while IFS='|' read -r n f N; do log "  C $n START"
  for s in addressable unrestricted; do comp_grp $n $f $N hy $s; done
  timing_grp $n $f $N hy $SETS3; log "  C $n END"; done <<< "$ALL"

stage "Stage D + transforms (SIS/auto, SIS/hybrid_auto; default), 15 columns"
while IFS='|' read -r n f N; do log "  D $n START"; timing_grp $n $f $N tx default; log "  D $n END"; done <<< "$ALL"

stage "Stage E baselines, 10 main columns"
while IFS='|' read -r n f N; do log "  E $n START"; timing_grp $n $f $N base base; log "  E $n END"; done <<< "$MAIN"

stage "Stage F compzl, realNested+hybrid, addressable+unrestricted, 15 columns"
while IFS='|' read -r n f N; do for g in rn hy; do for s in addressable unrestricted; do comp_grp $n $f $N $g $s zl; done; done; done <<< "$ALL"

stage "Stage G other SIS arms (key_derived, huffOn, huffOn/key_derived; default), 15 columns"
while IFS='|' read -r n f N; do log "  G $n START"; timing_grp $n $f $N ot default; log "  G $n END"; done <<< "$ALL"

nf=$(cat $O/failed.txt 2>/dev/null | wc -l); ns=$(cat $O/skipped.txt 2>/dev/null | wc -l)
if stopped; then { echo "stopped: $(cat $O/STOP)"; echo "skipped runs: $ns"; cat $O/skipped.txt 2>/dev/null; } > $O/STOPPED; log "STOPPED ($(cat $O/STOP)); skipped=$ns fails=$nf"
else log "DONE csv=$(find $D -name '*.csv' | wc -l) fails=$nf skipped=$ns"; fi
echo "fails=$nf skipped=$ns $(date)" > $O/DONE
