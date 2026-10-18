#!/bin/bash
# TopLevel rerun (--mlidc_sis_section_candidates=addressable on every config, baseline included) of decode_knob_20261010/scripts/sweep.sh.
# Budget sweep to 100% for the paper figure: Snowflake (headline), OSM S2 and OSM H3 (supporting), default planner.
set -u
. $(dirname $0)/common.sh
D=$O/sweep; mkdir -p $D
CFG=$D/configs.txt; : > $CFG
SC="--mlidc_sis_section_candidates=addressable"
REC="$SC --mlidc_sis_decode_read_path=1 --mlidc_sis_decode_cost_model=1 --mlidc_sis_section_read_nanos=-1 --mlidc_sis_decode_weight_sections_only --mlidc_sis_size_budget_strict --mlidc_sis_decode_mix=point:0.5,bulk:0.5"
echo "w0|$SC" >> $CFG
for b in 0 0.01 0.02 0.03 0.04 0.05 0.075 0.1 0.15 0.25 0.5 1; do bt=$(echo $b | tr . p)
  echo "B_b${bt}|$REC --mlidc_sis_size_budget=$b" >> $CFG
done
SW="$DS/TwitterSnowflake/csv/tweet_id_full.txt|snowflake|10000000
$DS/OSM/csv/s2_l30_fileorder.txt|osm_s2_l30_fileorder|10000000
$DS/OSM/csv/h3_r9_fileorder.txt|osm_h3_r9_fileorder|10000000"
ARMS=SIS/realNested; VARMS=SIS/realNested+view
cold() { tag=$1; f=$2; n=$3; rep=$4; shift 4
  [ -f $D/cold_${n}_${tag}_r${rep}.csv ] && return 0
  quiet; ( flock 9; run $D/cold_${n}_${tag}_r${rep}.csv $B/nimble_ml_id_decode_bulk_benchmark --mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n --mlidc_dtype=uint64 --mlidc_rows=$N --mlidc_input_order=shipped --cache_state=hot --mlidc_iters=5 --mlidc_seed=$rep --mlidc_encoders=SIS/realNested+view+ctor "$@" ) 9>>$LOCK; }
ext() { tag=$1; f=$2; n=$3; rep=$4; shift 4
  [ -f $D/enc_${n}_${tag}_r${rep}.csv ] && [ -f $D/plan_${n}_${tag}_r${rep}.csv ] && return 0
  quiet; ( flock 9
    C="--mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n --mlidc_dtype=uint64 --mlidc_rows=$N --mlidc_input_order=shipped --mlidc_seed=$rep"
    run $D/enc_${n}_${tag}_r${rep}.csv $B/nimble_ml_id_encode_benchmark $C --mlidc_iters=5 --mlidc_encoders=SIS/realNested "$@"
    run $D/plan_${n}_${tag}_r${rep}.csv $B/nimble_ml_id_compression_benchmark $C --mlidc_encoders=SIS/realNested --mlidc_sis_time_planner_reps=11 "$@" ) 9>>$LOCK; }
uptime > $D/load.txt; date -u +%s > $D/start_epoch
for rep in 1 2 3; do
  echo "$SW" | while IFS="|" read -r f n full; do
    while IFS="|" read -r tag flags; do
      echo "### rep$rep $n $tag $(date +%T) $(cut -d' ' -f1 /proc/loadavg)"
      [ $rep = 1 ] && comp $tag $f $n $N $ARMS $flags
      timed $tag $f $n $rep $VARMS $flags
      cold $tag $f $n $rep $flags
      ext $tag $f $n $rep $flags
    done < $CFG
  done
done
echo "TIMING_DONE $(date +%T)"
export -f comp run; export D B N
echo "$SW" | while IFS="|" read -r f n full; do
  while IFS="|" read -r tag flags; do echo "comp $tag $f $n $full $ARMS $flags"; done < $CFG
done > $D/full_jobs.txt
# full-length size jobs (untimed) also held under the lock, so they never overlap anyone's timing.
( flock 9; xargs -P 4 -I{} bash -c '{}' < $D/full_jobs.txt ) 9>>$LOCK
echo "SWEEP_DONE $(date +%T)"; date -u +%s > $D/end_epoch
