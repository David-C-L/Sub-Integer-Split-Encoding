#!/bin/bash
# Attribution check: default + re-priced with --mlidc_sis_row_frame=false (row-frame fit skipped), 524,288 and ~2M rows.
set -u
O=$(cd "$(dirname "$0")" && pwd); cd $O
DS=$HOSTDATA/project/Datasets; B=$O/bin; P=$O/progress.log; L=$O/timing_load.log
mkdir -p $O/out_rowframe_off
(cd $B && sha256sum -c --quiet SHA256SUMS) || { echo "checksum mismatch" >> $P; exit 1; }
exec 8>>$RESULTS/host_timing.lock; flock 8
run() { local out=$1; shift; echo "$* --mlidc_output_csv=$out" >> $O/commands.txt
  echo "$(date +%T) start $(basename $out) load $(cut -d' ' -f1-3 /proc/loadavg)" >> $L
  "$@" --mlidc_output_csv=$out > ${out%.csv}.log 2>&1 && echo "ok rf_off $(basename $out)" >> $P || echo "FAIL $? $(basename $out)" >> $P
  echo "$(date +%T) end   $(basename $out) load $(cut -d' ' -f1-3 /proc/loadavg)" >> $L; }
for c in "snowflake|TwitterSnowflake/csv/tweet_id.txt|131072" "snowflake|TwitterSnowflake/csv/tweet_id.txt|524288" "snowflake|TwitterSnowflake/csv/tweet_id.txt|2000000" \
         "osm_h3_r9_fileorder|OSM/csv/h3_r9_fileorder.txt|131072" "osm_h3_r9_fileorder|OSM/csv/h3_r9_fileorder.txt|524288" "osm_h3_r9_fileorder|OSM/csv/h3_r9_fileorder.txt|2097152"; do
  IFS='|' read -r n f rows <<< "$c"
  run $O/out_rowframe_off/comp_${n}_${rows}.csv $B/nimble_ml_id_compression_benchmark --mlidc_file=$DS/$f --mlidc_dataset_name=$n --mlidc_datasets=$n \
    --mlidc_dtype=uint64 --mlidc_rows=$rows --mlidc_input_order=shipped --mlidc_sis_section_candidates=addressable --mlidc_iters=1 \
    --mlidc_encoders=SIS/realNested,SIS/hybrid --mlidc_sis_plan_time_reps=11 --mlidc_sis_row_frame=false; done
flock -u 8; echo "DONE rf_off $(date)" >> $P
