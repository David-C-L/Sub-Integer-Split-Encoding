#!/bin/bash
# Extra (after run.sh's DONE): planner-time ratio behind the tex "52x" (ARM_B_OPENZL_AWARE_DP_20261007.md item 5).
# Needs the OpenZL section pricer, which only eval/openzl-aware-dp has, so it uses that run's binary
# (armB_openzl_dp_20261007_1840/bin2 = rev-arm-b-2, base rev-toplevel), not this run's bin/. The quoted number is a
# ratio of two timings inside one process of that binary. Same command as that run's bin2check, plus
# --mlidc_sis_section_candidates=addressable; the kDefault command is re-run alongside as a same-session control.
set -u
O=$RESULTS/toplevel_sec7_20261014_1526; X=$O/extra_planner_time; mkdir -p $X
R=$HOSTDATA/project; B2=$RESULTS/armB_openzl_dp_20261007_1840/bin2
until [ -f $O/DONE ] || [ -f $O/STOP ]; do sleep 60; done; [ -f $O/STOP ] && exit 0
exec 8>>$RESULTS/bench_timing.lock; flock 8; exec 9>>$R/bench_timing.lock; flock 9
sha256sum $B2/nimble_ml_id_compression_benchmark > $X/bin2.sha256
C="--mlidc_file=$R/Datasets/TwitterSnowflake/csv/tweet_id_full.txt --mlidc_dataset_name=snowflake --mlidc_datasets=snowflake --mlidc_dtype=uint64 --mlidc_rows=10000000 --mlidc_input_order=shipped --mlidc_iters=1 --mlidc_encoders=SIS/trivial --mlidc_substream_compression=OpenZL --mlidc_sis_openzl_pricing=nimble --mlidc_sis_time_planner_reps=11"
for s in addressable default; do
  echo "$B2/nimble_ml_id_compression_benchmark $C --mlidc_sis_section_candidates=$s --mlidc_output_csv=$X/plantime_$s.csv" >> $X/commands.txt
  echo "[$(date +%T)] $s load $(cut -d' ' -f1-3 /proc/loadavg)" >> $X/timing_load.log
  $B2/nimble_ml_id_compression_benchmark $C --mlidc_sis_section_candidates=$s --mlidc_output_csv=$X/plantime_$s.csv > $X/plantime_$s.log 2>&1
done
grep -h "planner-time" $X/plantime_*.log > $X/summary.txt; touch $X/DONE
