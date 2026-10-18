#!/bin/bash
set -u
R=$HOSTDATA/project/velox-fork-for-nimble
DS=$HOSTDATA/project/Datasets
D=velox/dwio/nimble/encodings/benchmarks/ml_id_compression
B=$R/_build_release/$D
O=$RESULTS/motivation_524k_v2
mkdir -p $O
cd $R || exit 1

SNOW=$DS/TwitterSnowflake/csv/tweet_id.txt
N=524288
P=n524288
ARMS="zstd/auto,zstd/block-64,zstd/block-256,zstd/block-1024,zstd/block-65536,zstd/block-262144,openzl/auto,openzl/block-64,openzl/block-256,openzl/block-1024,openzl/block-65536,openzl/block-262144"
RANGE_SIZES=1,8,64,512,4096,32768,131072,524288
RANGE_OFFSETS=8,8,16,32,32,16,8,1
COMMON="--mlidc_file=$SNOW --mlidc_dataset_name=snowflake --mlidc_datasets=snowflake --mlidc_dtype=uint64 --mlidc_rows=$N --mlidc_input_order=shipped"

echo "=== START $(date) ==="

echo "--- compression $(date +%H:%M:%S) ---"
$B/nimble_ml_id_compression_benchmark $COMMON \
  --mlidc_iters=1 --mlidc_encoders="$ARMS" \
  --mlidc_output_csv=$O/${P}_comp_snowflake_shipped.csv
echo "compression exit=$? $(date +%H:%M:%S)"

for rep in 1 2 3; do
  echo "--- range rep$rep $(date +%H:%M:%S) ---"
  $B/nimble_ml_id_decode_range_benchmark $COMMON \
    --cache_state=hot --mlidc_iters=5 --mlidc_block_codec_iters=3 \
    --mlidc_encoders="$ARMS" --range_sizes=$RANGE_SIZES \
    --range_offsets_by_size=$RANGE_OFFSETS --mlidc_seed=$rep \
    --mlidc_output_csv=$O/${P}_range_hot_snowflake_shipped_r${rep}.csv
  echo "range rep$rep exit=$? $(date +%H:%M:%S)"
done

echo "=== END $(date) ==="
ls -la $O
