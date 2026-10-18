#!/bin/bash
# Blended pricing: strict size budgets x pattern mixes, both planners, head with the MainlyConstant view fix.
set -u
export BIN=$RESULTS/decode_knob_20261010/bin_i
. $(dirname $0)/common.sh
D=$O/eval3; mkdir -p $D
CFG=$D/configs.txt; : > $CFG
echo "w0|" >> $CFG
CAL="--mlidc_sis_decode_read_path=1 --mlidc_sis_decode_cost_model=1 --mlidc_sis_section_read_nanos=-1 --mlidc_sis_decode_weight_sections_only --mlidc_sis_size_budget_strict"
for b in 0.02 0.05 0.1; do bt=$(echo $b | tr . p)
  echo "M_P_b${bt}|$CAL --mlidc_sis_size_budget=$b --mlidc_sis_decode_mix=point:1" >> $CFG
  echo "M_P3B1_b${bt}|$CAL --mlidc_sis_size_budget=$b --mlidc_sis_decode_mix=point:0.75,bulk:0.25" >> $CFG
  echo "M_P1B1_b${bt}|$CAL --mlidc_sis_size_budget=$b --mlidc_sis_decode_mix=point:0.5,bulk:0.5" >> $CFG
  echo "M_P1B3_b${bt}|$CAL --mlidc_sis_size_budget=$b --mlidc_sis_decode_mix=point:0.25,bulk:0.75" >> $CFG
  echo "M_B_b${bt}|$CAL --mlidc_sis_size_budget=$b --mlidc_sis_decode_mix=bulk:1" >> $CFG
done
for b in 0.05 0.1; do bt=$(echo $b | tr . p)
  echo "G_P_b${bt}|$CAL --mlidc_sis_size_budget=$b --mlidc_sis_decode_mix=point:1 --mlidc_sis_max_pattern_slowdown=1.1" >> $CFG
  echo "G_P1B1_b${bt}|$CAL --mlidc_sis_size_budget=$b --mlidc_sis_decode_mix=point:0.5,bulk:0.5 --mlidc_sis_max_pattern_slowdown=1.1" >> $CFG
done
ARMS=SIS/realNested,SIS/hybrid; VARMS=SIS/realNested+view,SIS/hybrid+view
cold() { tag=$1; f=$2; n=$3; rep=$4; shift 4
  [ -f $D/cold_${n}_${tag}_r${rep}.csv ] && return 0
  quiet; ( flock 9; run $D/cold_${n}_${tag}_r${rep}.csv $B/nimble_ml_id_decode_bulk_benchmark --mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n --mlidc_dtype=uint64 --mlidc_rows=$N --mlidc_input_order=shipped --cache_state=hot --mlidc_iters=5 --mlidc_seed=$rep --mlidc_encoders=SIS/realNested+view+cold "$@" ) 9>>$LOCK; }
uptime > $D/load.txt
for rep in 1 2 3; do
  echo "$UNITS" | while IFS="|" read -r f n full; do
    while IFS="|" read -r tag flags; do
      echo "### rep$rep $n $tag $(date +%T) $(cut -d' ' -f1 /proc/loadavg)"
      [ $rep = 1 ] && comp $tag $f $n $N $ARMS $flags
      timed $tag $f $n $rep $VARMS $flags
      cold $tag $f $n $rep $flags
      [ $rep = 1 ] && extra $tag $f $n $rep $flags
    done < $CFG
  done
done
echo "TIMING_DONE $(date +%T)"
export -f comp run; export D B N
echo "$UNITS" | while IFS="|" read -r f n full; do
  while IFS="|" read -r tag flags; do echo "comp $tag $f $n $full $ARMS $flags"; done < $CFG
done > $D/full_jobs.txt
xargs -P 4 -I{} bash -c '{}' < $D/full_jobs.txt
echo "EVAL_DONE $(date +%T)"
