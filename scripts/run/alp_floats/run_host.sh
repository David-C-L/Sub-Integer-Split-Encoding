#!/bin/bash
# alp_floats: SIS (TopLevel addressable) vs ALP vs Nimble default (Auto/view) vs OpenZL on the 11 float columns,
# on the toplevel_sec7_20261014_1526 binaries (rev-toplevel + rev-arm-a + build/toplevel_sec7.patch). No build needed:
# compression, encode, decode_{bulk,point,range} are all in that bin/.
# Harness = floats_20261002_0150/phase2.sh and w524_tl.sh: 524,288-row prefix (F8 full 424,205 = study length,
# so size is full length too), hot cache, 3 interleaved repeats, point 256 probes, range B=64 x 16 offsets.
# Usage on benchmark host: O=$RESULTS/alp_floats_<stamp>; mkdir -p $O; copy this file there; nohup bash $O/run_host.sh $O &
set -u
O=$1; R=$HOSTDATA/project; DS=$R/Datasets/Floats
TL=$RESULTS/toplevel_sec7_20261014_1526; B=$TL/bin
SC="--mlidc_sis_section_candidates=addressable"
L1=$RESULTS/bench_timing.lock
D=$O/runs; mkdir -p $D; exec >> $O/run.log 2>&1
(cd $B && sha256sum -c --quiet SHA256SUMS) || { echo "bin checksum mismatch"; exit 1; }
cat $TL/COMMIT > $O/COMMIT; cp $B/SHA256SUMS $O/
ARMS="SIS/realNested,SIS/realNested+view,ALP,ALP/view,ALPRD,Auto/view,openzl/auto,openzl/block-1024,openzl/block-65536"
ENCA="SIS/realNested,ALP,ALPRD,Auto/view,openzl/auto,openzl/block-1024,openzl/block-65536"
run() { local out=$1 t0 rc; shift; [ -f $out ] && return 0; t0=$(date +%s); echo "$* --mlidc_output_csv=$out" >> $O/commands.txt
  timeout 2h "$@" --mlidc_output_csv=$out.tmp > ${out%.csv}.log 2>&1; rc=$?
  if [ $rc -eq 0 ] && [ -f $out.tmp ]; then mv $out.tmp $out; echo "ok $(( $(date +%s)-t0 ))s $(basename $out)"; else rm -f $out.tmp; echo "FAIL rc=$rc $(basename $out)"; fi; }
COLS="F1_stocks_usa|F1_stocks_usa.txt|524288
F2_food_prices|F2_food_prices.txt|524288
F3_gov10|F3_gov10.txt|524288
F4_medicare_total_drug_cost|F4_medicare_total_drug_cost.txt|524288
F5_city_temp|F5_city_temp.txt|524288
F6_air_pressure|F6_air_pressure.txt|524288
F7_dew_point_temp|F7_dew_point_temp.txt|524288
F8_poi_lat|F8_poi_lat.txt|424205
F9_nyc29|F9_nyc29.txt|524288
F10_medicare_calc|F10_medicare_calc_9030826185528129.txt|524288
C0_uniform_control|C0_uniform_control.txt|524288"
cm() { echo "--mlidc_file=$DS/$2 --mlidc_dataset_name=$1 --mlidc_datasets=$1 --mlidc_dtype=double --mlidc_rows=$3 --mlidc_input_order=shipped --mlidc_block_sizes=1024,65536 $SC"; }
# size: untimed, no lock
while IFS='|' read -r n f N; do run $D/comp_${n}_shipped.csv $B/nimble_ml_id_compression_benchmark $(cm $n $f $N) --mlidc_iters=1 --mlidc_encoders=$ARMS --mlidc_dump_encoding; done <<< "$COLS"
# timing: under the shared lock
exec 8>>$L1; echo "waiting for lock $(date)"; flock 8; echo "lock held $(date) load $(cut -d' ' -f1-3 /proc/loadavg)"
while IFS='|' read -r n f N; do C=$O/cache_$n; mkdir -p $C; EC="--mlidc_encode_cache_dir=$C"; X=$(cm $n $f $N)
  for rep in 1 2 3; do
    run $D/enc_${n}_shipped_r$rep.csv $B/nimble_ml_id_encode_benchmark $X --mlidc_iters=1 --mlidc_encoders=$ENCA
    run $D/bulk_${n}_shipped_r$rep.csv $B/nimble_ml_id_decode_bulk_benchmark $X --cache_state=hot --mlidc_iters=5 --mlidc_encoders=$ARMS $EC
    run $D/point_${n}_shipped_r$rep.csv $B/nimble_ml_id_decode_point_benchmark $X --cache_state=hot --mlidc_iters=5 --probes=256 --mlidc_block_codec_probes=256 --mlidc_encoders=$ARMS $EC
    run $D/range_hot_${n}_shipped_r$rep.csv $B/nimble_ml_id_decode_range_benchmark $X --cache_state=hot --mlidc_iters=5 --mlidc_block_codec_iters=3 --range_sizes=64 --range_offsets_by_size=16 --mlidc_seed=$rep --mlidc_encoders=$ARMS $EC
  done; rm -rf $C; echo "COL $n done $(date)"
done <<< "$COLS"
echo "DONE $(date)"; touch $O/DONE
