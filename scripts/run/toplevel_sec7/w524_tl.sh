#!/bin/bash
# usage: w524_tl.sh "<unit regex>" "<reps>" "<phases e.g. 1234567>"
# Copy of $RESULTS/w524.sh (the harness of sweep524k_rev-sweep-524k) for toplevel_sec7.
# Changes: binaries, output and encode cache point at this run dir; sweep_config.sh is the rev-toplevel copy here;
# every command gets --mlidc_sis_section_candidates=addressable (kAddressableTopLevel). Nothing else.
set -u
SEL=$1; REPS=$2; PHASES=$3; GRCS=${4:-}
R=$HOSTDATA/project
TL=$RESULTS/toplevel_sec7_20261014_1526
DS=$R/Datasets
B=$TL/bin
O=$TL/sweep
CACHE=$TL/encode_cache
mkdir -p $O $CACHE
. $TL/sweep_config.sh
EXTRA_ARMS="SIS/hybrid,SIS/hybrid+view,openzl/block-1024,openzl/block-65536${SWEEP_EXTRA_ARMS:+,$SWEEP_EXTRA_ARMS}"
ARMS_ALL="$ARMS_ALL,$EXTRA_ARMS${SWEEP_EXTRA_COMP:+,$SWEEP_EXTRA_COMP}"
ARMS_ACCESS="$ARMS_ACCESS,$EXTRA_ARMS"
ARMS_ENCODE="$ARMS_ENCODE,SIS/hybrid,openzl/block-1024,openzl/block-65536${SWEEP_EXTRA_ENCODE:+,$SWEEP_EXTRA_ENCODE}"
N=524288
COMMON="--mlidc_dtype=uint64 --mlidc_rows=$N --mlidc_sis_section_candidates=addressable"
EC="--mlidc_encode_cache_dir=$CACHE"
SNOW=$DS/TwitterSnowflake/csv/tweet_id.txt; XM=$DS/XMark/csv/prepost_id_full.txt
H3=$DS/OSM/csv/h3_r9_fileorder.txt; S2=$DS/OSM/csv/s2_l30_fileorder.txt
NPI=$DS/PublicBI/Medicare1/csv/NPI.txt; ID1=$DS/PublicBI/Corporations/csv/Id1.txt
BING=$DS/BingTiles/csv/quadkey_fileorder.txt; UHI=$DS/UUIDv7/csv/uuidv7_hi.txt; ULO=$DS/UUIDv7/csv/uuidv7_lo.txt
# Access/encode phases take shipped+mergeirr (+mergekey on snowflake): what the figures read.
UNITS_ACC="$SNOW|snowflake|shipped,mergeirr=8,mergekey=0,mergekey=2
$XM|xmark_prepost_full|shipped,mergeirr=8
$H3|osm_h3_r9_fileorder|shipped,mergeirr=8
$S2|osm_s2_l30_fileorder|shipped,mergeirr=8
$NPI|publicbi_npi|shipped,mergeirr=8
$ID1|publicbi_id1|shipped,mergeirr=8
$BING|bing_quadkey|shipped
$UHI|uuidv7_hi|shipped
$ULO|uuidv7_lo|shipped"
# Compression also takes shuffled+sorted (fig4 arrival order).
UNITS_COMP="$SNOW|snowflake|shipped,mergeirr=8,shuffled,sorted,mergekey=0,mergekey=2
$XM|xmark_prepost_full|shipped,mergeirr=8,shuffled,sorted
$H3|osm_h3_r9_fileorder|shipped,mergeirr=8,shuffled,sorted
$S2|osm_s2_l30_fileorder|shipped,mergeirr=8,shuffled,sorted
$NPI|publicbi_npi|shipped,mergeirr=8,shuffled,sorted
$ID1|publicbi_id1|shipped,mergeirr=8,shuffled,sorted
$BING|bing_quadkey|shipped
$UHI|uuidv7_hi|shipped
$ULO|uuidv7_lo|shipped"
run() { out=$1; shift; [ -f "$out" ] && return
  [ -f $TL/STOP ] && return; echo "$* --mlidc_output_csv=$out" >> $TL/commands.txt
  s=$(date +%s); "$@" --mlidc_output_csv=$out.tmp > $out.log 2>&1
  if [ $? -eq 0 ]; then mv $out.tmp $out; echo "    ok $(( $(date +%s)-s ))s $(basename $out)"
  else echo "    FAIL $(basename $out)"; rm -f $out.tmp; fi; }
units() { echo "$1" | while IFS='|' read -r f n orders; do for o in $(echo $orders | tr , ' '); do
  t=$(echo $o | tr = _); echo "$n|$t" | grep -qE "$SEL" && echo "$f $n $o $t"; done; done; }
phase() { echo "### $1 $(date +%T)"; }
has() { echo "$PHASES" | grep -q "$1"; }
if has 1; then phase comp; units "$UNITS_COMP" | while read f n o t; do
  run $O/comp_${n}_${t}.csv $B/nimble_ml_id_compression_benchmark --mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n $COMMON --mlidc_input_order=$o --mlidc_iters=1 --mlidc_encoders="$ARMS_ALL" $EC; done; fi
if has 2; then phase compzl; units "$UNITS_COMP" | while read f n o t; do
  run $O/compzl_${n}_${t}.csv $B/nimble_ml_id_compression_benchmark --mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n $COMMON --mlidc_input_order=$o --mlidc_iters=1 --mlidc_encoders="$ARMS_ALL" --mlidc_substream_compression=OpenZL $EC; done; fi
for rep in $REPS; do
 if has 3; then phase "enc r$rep"; units "$UNITS_ACC" | while read f n o t; do
  run $O/enc_${n}_${t}_r${rep}.csv $B/nimble_ml_id_encode_benchmark --mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n $COMMON --mlidc_input_order=$o --mlidc_iters=1 --mlidc_encoders="$ARMS_ENCODE"; done; fi
 for drv in bulk point; do
  has $([ $drv = bulk ] && echo 4 || echo 5) || continue
  X=""; [ $drv = point ] && X="--probes=256 --mlidc_block_codec_probes=256"
  for cs in ${BPCS:-$ACCESS_CACHE_STATES}; do c=$(echo $cs | tr - _); phase "$drv $c r$rep"; units "$UNITS_ACC" | while read f n o t; do
   run $O/${drv}_${c}_${n}_${t}_r${rep}.csv $B/nimble_ml_id_decode_${drv}_benchmark --mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n $COMMON --mlidc_input_order=$o --cache_state=$cs --mlidc_iters=5 --mlidc_encoders="$ARMS_ACCESS" $X $EC; done; done
 done
 if has 6; then for cs in ${GRCS:-$ACCESS_CACHE_STATES}; do c=$(echo $cs | tr - _); phase "gather $c r$rep"; units "$UNITS_ACC" | while read f n o t; do
   run $O/gather_${c}_${n}_${t}_r${rep}.csv $B/nimble_ml_id_decode_gather_benchmark --mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n $COMMON --mlidc_input_order=$o --cache_state=$cs --mlidc_iters=2 --mlidc_encoders="$ARMS_ACCESS" --selectivity_values=$GATHER_SELECTIVITY --run_length_values=$GATHER_RUN_LENGTHS $EC; done; done; fi
 if has 7; then for cs in ${GRCS:-$ACCESS_CACHE_STATES}; do c=$(echo $cs | tr - _); phase "range $c r$rep"; units "$UNITS_ACC" | while read f n o t; do
   run $O/range_${c}_${n}_${t}_r${rep}.csv $B/nimble_ml_id_decode_range_benchmark --mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n $COMMON --mlidc_input_order=$o --cache_state=$cs --mlidc_iters=5 --mlidc_block_codec_iters=3 --mlidc_encoders="$ARMS_ACCESS" --range_sizes=$RANGE_SIZES --range_offsets_by_size=$RANGE_OFFSETS_BY_SIZE --mlidc_seed=$rep $EC; done; done; fi
done
echo "W524_DONE $(date +%T) files=$(ls $O/*.csv 2>/dev/null | wc -l)"
