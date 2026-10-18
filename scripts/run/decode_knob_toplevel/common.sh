R=$HOSTDATA/project
DS=$R/Datasets
O=$RESULTS/decode_knob_toplevel_20261014_1859
B=$O/bin
LOCK=$RESULTS/bench_timing.lock
N=524288
UNITS="$DS/TwitterSnowflake/csv/tweet_id_full.txt|snowflake|10000000
$DS/OSM/csv/h3_r9_fileorder.txt|osm_h3_r9_fileorder|10000000
$DS/OSM/csv/s2_l30_fileorder.txt|osm_s2_l30_fileorder|10000000
$DS/BingTiles/csv/quadkey_fileorder_full.txt|bing_quadkey|9869460
$DS/XMark/csv/prepost_id_full.txt|xmark_prepost_full|10000000
$DS/UUIDv7/csv/uuidv7_hi_10M.txt|uuidv7_hi|10000000
$DS/PublicBI/Medicare1/csv/NPI_full.txt|publicbi_npi|17290144
$DS/PublicBI/Corporations/csv/Id1.txt|publicbi_id1|739754"
# run <out.csv> <cmd...>: skips when done, logs the command.
run() { out=$1; shift; [ -f "$out" ] && return 0
  echo "$@ --mlidc_output_csv=$out" >> $D/commands.txt
  "$@" --mlidc_output_csv=$out.tmp > $out.log 2>&1
  if [ $? -eq 0 ] && [ -f $out.tmp ]; then mv $out.tmp $out; else echo "    FAIL $(basename $out)"; rm -f $out.tmp; fi; }
# waits for a quiet machine: no live compiler.
quiet() { while ps -eo stat=,comm= | awk '$1 !~ /^Z/ && $2=="cc1plus"' | grep -q .; do sleep 20; done; }
# comp <tag> <file> <name> <rows> <arms> <flags...>: size + plan dump, untimed.
comp() { tag=$1; f=$2; n=$3; rows=$4; arms=$5; shift 5
  run $D/comp_${n}_${tag}_n${rows}.csv $B/nimble_ml_id_compression_benchmark --mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n \
    --mlidc_dtype=uint64 --mlidc_rows=$rows --mlidc_input_order=shipped --mlidc_dump_encoding --mlidc_encoders=$arms "$@"; }
# timed <tag> <file> <name> <rep> <arms> <flags...>: point, range-64, bulk on the 524,288-row prefix, under the lock.
timed() { tag=$1; f=$2; n=$3; rep=$4; arms=$5; shift 5
  [ -f $D/bulk_${n}_${tag}_r${rep}.csv ] && [ -f $D/point_${n}_${tag}_r${rep}.csv ] && [ -f $D/range_${n}_${tag}_r${rep}.csv ] && return 0
  quiet
  ( flock 9
    C="--mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n --mlidc_dtype=uint64 --mlidc_rows=$N --mlidc_input_order=shipped --cache_state=hot --mlidc_iters=5 --mlidc_seed=$rep --mlidc_encoders=$arms"
    run $D/point_${n}_${tag}_r${rep}.csv $B/nimble_ml_id_decode_point_benchmark $C --probes=256 --mlidc_block_codec_probes=256 "$@"
    run $D/range_${n}_${tag}_r${rep}.csv $B/nimble_ml_id_decode_range_benchmark $C --range_sizes=64 --range_offsets_by_size=16 --mlidc_block_codec_iters=3 "$@"
    run $D/bulk_${n}_${tag}_r${rep}.csv $B/nimble_ml_id_decode_bulk_benchmark $C "$@"
  ) 9>>$LOCK; }
# extra <tag> <file> <name> <rep> <flags...>: sparse gather, encode time and planner time on the prefix, under the lock.
extra() { tag=$1; f=$2; n=$3; rep=$4; shift 4
  [ -f $D/enc_${n}_${tag}_r${rep}.csv ] && [ -f $D/gather_${n}_${tag}_r${rep}.csv ] && [ -f $D/plan_${n}_${tag}_r${rep}.csv ] && return 0
  quiet
  ( flock 9
    C="--mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n --mlidc_dtype=uint64 --mlidc_rows=$N --mlidc_input_order=shipped --mlidc_seed=$rep"
    run $D/gather_${n}_${tag}_r${rep}.csv $B/nimble_ml_id_decode_gather_benchmark $C --cache_state=hot --mlidc_iters=2 --mlidc_encoders=SIS/realNested+view,SIS/hybrid+view --selectivity_values=0.01 --run_length_values=1 "$@"
    run $D/enc_${n}_${tag}_r${rep}.csv $B/nimble_ml_id_encode_benchmark $C --mlidc_iters=5 --mlidc_encoders=SIS/realNested,SIS/hybrid "$@"
    run $D/plan_${n}_${tag}_r${rep}.csv $B/nimble_ml_id_compression_benchmark $C --mlidc_encoders=SIS/realNested --mlidc_sis_time_planner_reps=11 "$@"
  ) 9>>$LOCK; }
