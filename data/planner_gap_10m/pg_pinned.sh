#!/bin/bash
# Pinned encoded (oracle_dp_selection) plan at 10M: sizes, sections, point reads. Usage: pg_pinned.sh <dataset> <file> <boundaries>
set -u
O=$(cd "$(dirname "$0")" && pwd); cd $O
DS=$HOSTDATA/project/Datasets; TB=$RESULTS/toplevel_sec7_20261014_1526/bin; P=$O/progress.log; L=$O/timing_load.log
n=$1; f=$2; b=$3
run() { local out=$1; shift; echo "$* --mlidc_output_csv=$out" >> $O/commands.txt
  echo "$(date +%T) start $(basename $out) load $(cut -d' ' -f1-3 /proc/loadavg)" >> $L
  "$@" --mlidc_output_csv=$out > ${out%.csv}.log 2>&1 && echo "ok $(basename $out)" >> $P || echo "FAIL $? $(basename $out)" >> $P
  echo "$(date +%T) end   $(basename $out) load $(cut -d' ' -f1-3 /proc/loadavg)" >> $L; }
C="--mlidc_file=$DS/$f --mlidc_dataset_name=$n --mlidc_datasets=$n --mlidc_dtype=uint64 --mlidc_rows=10000000 --mlidc_input_order=shipped --mlidc_sis_section_candidates=addressable"
PIN="--mlidc_encoders=SIS/pinned,SIS/pinned+view --mlidc_sis_pinned_boundaries=$b --mlidc_sis_pinned_label=oracle_dp_selection"
run $O/out/comp_${n}_oracle_dp_selection.csv $TB/nimble_ml_id_compression_benchmark $C --mlidc_iters=1 $PIN --mlidc_dump_encoding
for r in 1 2 3; do run $O/out/point_${n}_oracle_dp_selection_r$r.csv $TB/nimble_ml_id_decode_point_benchmark $C --cache_state=hot --mlidc_iters=5 --probes=256 --mlidc_block_codec_probes=256 $PIN; done
echo "pinned done $n $(date +%T)" >> $P
