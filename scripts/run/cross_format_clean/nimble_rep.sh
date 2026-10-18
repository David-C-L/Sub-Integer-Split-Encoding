#!/bin/bash
# One Nimble repeat on the cross-format shared codec set: the commands of
# $RESULTS/xf_nimble_shared.sh (lines 13-19 and its aggregator), unchanged except
#   - binaries: evaluation branch rev-kdefault copied into ../bin (not the wt-encode-speed build),
#   - one repeat per call (run.sh interleaves repeats with BtrBlocks/FastLanes), raw files skipped if present,
#   - no restructure encode lock (run.sh already holds bench_timing.lock).
# Usage: nimble_rep.sh <rep>   -> xf/nimble_run<rep>.csv
set -u
rep=$1
O=$(cd "$(dirname "$0")" && pwd); XO=$O/xf; RAW=$XO/nimble_raw; B=$O/bin; mkdir -p $RAW
R=$HOSTDATA/project
SH=Trivial,Constant,Dictionary,RLE,PFOR,MainlyConstant,SparseBool,FixedBitWidth
declare -A LIST=([auto]=$SH [auto_sis]=$SH,SubIntSplit)
COLS="TwitterSnowflake/csv/tweet_id.txt:snowflake XMark/csv/prepost_id_full.txt:xmark_prepost_full OSM/csv/h3_r9_fileorder.txt:osm_h3_r9_fileorder OSM/csv/s2_l30_fileorder.txt:osm_s2_l30_fileorder BingTiles/csv/quadkey_fileorder.txt:bing_quadkey UUIDv7/csv/uuidv7_hi.txt:uuidv7_hi UUIDv7/csv/uuidv7_lo.txt:uuidv7_lo PublicBI/Medicare1/csv/NPI.txt:publicbi_npi PublicBI/Corporations/csv/Id1.txt:publicbi_id1"
fail=0
run() { local out=$1; shift; [ -s $out ] && return 0; "$@" --mlidc_output_csv=$out.tmp > ${out%.csv}.log 2>&1 && mv $out.tmp $out || { echo "FAIL $out"; rm -f $out.tmp; fail=1; }; }
for c in $COLS; do f=$R/Datasets/${c%%:*}; n=${c##*:}
  for arm in auto auto_sis; do W=$RAW/${arm}_${n}_r$rep
    C="--mlidc_file=$f --mlidc_dataset_name=$n --mlidc_datasets=$n --mlidc_dtype=uint64 --mlidc_rows=524288 --mlidc_input_order=shipped --mlidc_output_manifest= --mlidc_encoders=Auto/view --mlidc_auto_encodings=${LIST[$arm]} --mlidc_sis_allowed_encodings=$SH --mlidc_seed=$rep"
    [ $rep = 1 ] && run ${W}_comp.csv $B/nimble_ml_id_compression_benchmark $C --mlidc_iters=1 --mlidc_dump_encoding
    run ${W}_point.csv $B/nimble_ml_id_decode_point_benchmark $C --cache_state=hot --mlidc_iters=5 --probes=256
    run ${W}_range.csv $B/nimble_ml_id_decode_range_benchmark $C --cache_state=hot --mlidc_iters=5 --range_sizes=64 --range_offsets_by_size=32
  done
done
[ $fail = 0 ] || exit 1
python3 - $XO $rep <<'PY' || exit 1
import csv,sys,glob,os
O,rep=sys.argv[1],sys.argv[2]
rows=[]
for comp in sorted(glob.glob(f"{O}/nimble_raw/*_r1_comp.csv")):
    base=os.path.basename(comp)[:-len("_r1_comp.csv")]; arm="auto_sis" if base.startswith("auto_sis_") else "auto"; ds=base[len(arm)+1:]
    c=next(csv.DictReader(open(comp)))
    p=[r for r in csv.DictReader(open(f"{O}/nimble_raw/{base}_r{rep}_point.csv"))]
    g=[r for r in csv.DictReader(open(f"{O}/nimble_raw/{base}_r{rep}_range.csv")) if r.get("B")=="64"]
    ok=all(r.get("validated")=="1" for r in [c]+p+g) and p and g
    rows.append(f"nimble,{arm},{ds},{float(c['bits_per_elem']):.4f},{float(p[0]['time_ns'])/256:.2f},{float(g[0]['time_ns']):.2f},{1 if ok else 0}\n")
if len(rows)!=18: sys.exit(f"expected 18 rows, got {len(rows)}")
tmp=f"{O}/nimble_run{rep}.csv.tmp"
with open(tmp,"w") as out:
    out.write("format,arm,dataset,bits_per_value,point_ns,range64_ns,validated\n"); out.writelines(rows)
os.replace(tmp,f"{O}/nimble_run{rep}.csv")
PY
