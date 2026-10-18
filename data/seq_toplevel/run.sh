#!/bin/bash
# Seq. (+D/H) column of tab:eval_composition: SIS/realNested, --mlidc_sis_section_candidates=unrestricted (kUnrestricted),
# full length, same binary (sha256 checked) and flags as toplevel_sec7_20261014_1526 ladder/arm15 (only the mode and
# the encoder list differ). Sanity: addressable on snowflake + xmark must reproduce arm15 (39.92, 4.45).
set -u
O=$(cd "$(dirname "$0")" && pwd); cd $O
DS=$HOSTDATA/project/Datasets; B=$O/bin; P=$O/progress.log
(cd $B && grep compression_benchmark SHA256SUMS | sha256sum -c --quiet) || { echo "checksum mismatch" >> $P; exit 1; }
run() { local out=$1; shift; echo "$* --mlidc_output_csv=$out" >> $O/commands.txt
  "$@" --mlidc_output_csv=$out > ${out%.csv}.log 2>&1 && echo "ok $(basename $out)" >> $P || echo "FAIL $? $(basename $out)" >> $P; }
col() { local n=$1 f=$2 rows=$3 m=$4
  run $O/out/${m}_$n.csv $B/nimble_ml_id_compression_benchmark --mlidc_file=$DS/$f --mlidc_dataset_name=$n --mlidc_datasets=$n --mlidc_dtype=uint64 --mlidc_rows=$rows --mlidc_input_order=shipped --mlidc_iters=1 --mlidc_dump_encoding --mlidc_sis_section_candidates=$m --mlidc_encoders=SIS/realNested; }
while IFS='|' read -r n f rows; do col $n $f $rows unrestricted & done <<'COLS'
snowflake|TwitterSnowflake/csv/tweet_id_full.txt|10000000
xmark_prepost_full|XMark/csv/prepost_id_full.txt|10000000
osm_h3_r9_fileorder|OSM/csv/h3_r9_fileorder.txt|10000000
osm_s2_l30_fileorder|OSM/csv/s2_l30_fileorder.txt|10000000
bing_quadkey|BingTiles/csv/quadkey_fileorder_full.txt|9869460
uuidv7_hi|UUIDv7/csv/uuidv7_hi_10M.txt|10000000
publicbi_npi|PublicBI/Medicare1/csv/NPI_full.txt|17290144
COLS
col snowflake TwitterSnowflake/csv/tweet_id_full.txt 10000000 addressable &
col xmark_prepost_full XMark/csv/prepost_id_full.txt 10000000 addressable &
wait; echo "DONE $(date)" >> $P; touch $O/DONE
