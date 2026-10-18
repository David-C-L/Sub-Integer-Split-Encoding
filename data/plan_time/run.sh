#!/bin/bash
# Planning time of the three tab:eval_planner_gap planners (default = SIS/realNested, re-priced = SIS/hybrid,
# encoded = SIS/oracle_dp_selection), TopLevel addressable mode, 524,288 rows, single-threaded, serial, under the
# shared timing lock. Binary: bin/ (rev-head + plan_time.patch), sha256 checked first.
set -u
O=$(cd "$(dirname "$0")" && pwd); cd $O
DS=$HOSTDATA/project/Datasets; B=$O/bin; P=$O/progress.log; L=$O/timing_load.log
mkdir -p $O/out
(cd $B && sha256sum -c --quiet SHA256SUMS) || { echo "checksum mismatch" >> $P; exit 1; }
exec 8>>$RESULTS/host_timing.lock; echo "[$(date +%T)] waiting for lock" >> $P; flock 8
run() { local out=$1; shift; echo "$* --mlidc_output_csv=$out" >> $O/commands.txt
  echo "$(date +%T) start $(basename $out) load $(cut -d' ' -f1-3 /proc/loadavg)" >> $L
  "$@" --mlidc_output_csv=$out > ${out%.csv}.log 2>&1 && echo "ok $(basename $out)" >> $P || echo "FAIL $? $(basename $out)" >> $P
  echo "$(date +%T) end   $(basename $out) load $(cut -d' ' -f1-3 /proc/loadavg)" >> $L; }
common() { echo --mlidc_file=$DS/$2 --mlidc_dataset_name=$1 --mlidc_datasets=$1 --mlidc_dtype=uint64 --mlidc_rows=$3 --mlidc_input_order=shipped --mlidc_sis_section_candidates=addressable; }
COLS="snowflake|TwitterSnowflake/csv/tweet_id.txt osm_h3_r9_fileorder|OSM/csv/h3_r9_fileorder.txt"
# 1. default + re-priced at 524,288: 21 timed encodes each (after 2 warm-ups), then the normal arm rows (sizes).
for c in $COLS; do n=${c%%|*}; f=${c#*|}
  run $O/out/comp_${n}_524288.csv $B/nimble_ml_id_compression_benchmark $(common $n $f 524288) --mlidc_iters=1 \
    --mlidc_encoders=SIS/realNested,SIS/hybrid --mlidc_sis_plan_time_reps=21; done
# 2. encoded: whole column (as tab:eval_planner_gap's plan was chosen, --sample_sizes=0) and a 2,048-row sample.
for c in $COLS; do n=${c%%|*}; f=${c#*|}
  run $O/out/oracle_${n}_524288.csv $B/nimble_ml_id_cost_model_oracle_benchmark $(common $n $f 524288) \
    --sample_sizes=2048,0 --plan_time_reps=11 --plan_time_only; done
# 3. row-count scaling check for default + re-priced (11 timed encodes).
for c in "snowflake|TwitterSnowflake/csv/tweet_id.txt|131072" "snowflake|TwitterSnowflake/csv/tweet_id.txt|2000000" \
         "osm_h3_r9_fileorder|OSM/csv/h3_r9_fileorder.txt|131072" "osm_h3_r9_fileorder|OSM/csv/h3_r9_fileorder.txt|2097152"; do
  IFS='|' read -r n f rows <<< "$c"
  run $O/out/comp_${n}_${rows}.csv $B/nimble_ml_id_compression_benchmark $(common $n $f $rows) --mlidc_iters=1 \
    --mlidc_encoders=SIS/realNested,SIS/hybrid --mlidc_sis_plan_time_reps=11; done
flock -u 8; echo "DONE $(date)" >> $P; touch $O/DONE
