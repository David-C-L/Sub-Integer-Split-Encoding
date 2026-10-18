#!/bin/bash
# tab:eval_planner_gap at 10,000,000 rows (Snowflake tweet_id_full, H3 h3_r9_fileorder), TopLevel addressable.
# Sizes/sections/point reads: toplevel_sec7_20261014_1526 bin (b186c969...), plan_decode flags with --mlidc_rows=10000000.
# Encoded plan + planning times: plan_time_20261017_2134 bin (timers). Encoded runs in background meanwhile (2 cores).
set -u
O=$(cd "$(dirname "$0")" && pwd); cd $O; mkdir -p out
DS=$HOSTDATA/project/Datasets; TB=$RESULTS/toplevel_sec7_20261014_1526/bin; PB=$RESULTS/plan_time_20261017_2134/bin; P=$O/progress.log; L=$O/timing_load.log
(cd $TB && grep -E "compression|point" SHA256SUMS | sha256sum -c --quiet) || { echo "tb checksum mismatch" >> $P; exit 1; }
(cd $PB && sha256sum -c --quiet SHA256SUMS) || { echo "pb checksum mismatch" >> $P; exit 1; }
exec 8>>$RESULTS/host_timing.lock; echo "[$(date +%T)] waiting for lock" >> $P; flock 8
run() { local out=$1; shift; echo "$* --mlidc_output_csv=$out" >> $O/commands.txt
  echo "$(date +%T) start $(basename $out) load $(cut -d' ' -f1-3 /proc/loadavg)" >> $L
  "$@" --mlidc_output_csv=$out > ${out%.csv}.log 2>&1 && echo "ok $(basename $out)" >> $P || echo "FAIL $? $(basename $out)" >> $P
  echo "$(date +%T) end   $(basename $out) load $(cut -d' ' -f1-3 /proc/loadavg)" >> $L; }
common() { echo --mlidc_file=$DS/$2 --mlidc_dataset_name=$1 --mlidc_datasets=$1 --mlidc_dtype=uint64 --mlidc_rows=10000000 --mlidc_input_order=shipped --mlidc_sis_section_candidates=addressable; }
COLS="snowflake|TwitterSnowflake/csv/tweet_id_full.txt osm_h3_r9_fileorder|OSM/csv/h3_r9_fileorder.txt"
for c in $COLS; do n=${c%%|*}; f=${c#*|}
  run $O/out/oracle_${n}.csv $PB/nimble_ml_id_cost_model_oracle_benchmark $(common $n $f) --sample_sizes=0 --plan_time_reps=1 --plan_time_only &
done
for c in $COLS; do n=${c%%|*}; f=${c#*|}
  run $O/out/comp_${n}_base.csv $TB/nimble_ml_id_compression_benchmark $(common $n $f) --mlidc_iters=1 --mlidc_encoders=SIS/realNested,SIS/realNested+view,SIS/hybrid,SIS/hybrid+view --mlidc_dump_encoding
  run $O/out/plantime_${n}.csv $PB/nimble_ml_id_compression_benchmark $(common $n $f) --mlidc_iters=1 --mlidc_encoders=SIS/realNested,SIS/hybrid --mlidc_sis_plan_time_reps=5
  for r in 1 2 3; do
    run $O/out/point_${n}_base_r$r.csv $TB/nimble_ml_id_decode_point_benchmark $(common $n $f) --cache_state=hot --mlidc_iters=5 --probes=256 --mlidc_block_codec_probes=256 --mlidc_encoders=SIS/realNested,SIS/realNested+view,SIS/hybrid,SIS/hybrid+view
  done
done
echo "base done $(date +%T)" >> $P
wait; flock -u 8; echo "DONE $(date)" >> $P; touch $O/DONE
