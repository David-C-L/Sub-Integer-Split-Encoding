#!/bin/bash
# Cross-format SubIntSplit stage, SHARED CODEC SET variant of cross_format.sh:
# both arms (auto without SIS, auto with SIS) restricted to one codec set that
# all three formats support, instead of each format's own baseline vs SIS.
#
#   XF_TAG=<tag> bash cross_format_shared.sh     # results -> $S/cross_format/<tag>/
#   XF_STAGES="btr fls"                          # subset of {btr,fls} (default: both;
#                                                 # nimble always runs unless XF_SKIP_NIMBLE=1)
#   XF_RUNS=3                                    # runs per format (default 3)
#   XF_HAVE_TIMING_LOCK=1                        # caller already holds bench_timing.lock
#   NIMBLE_TREE=/path NIMBLE_BIN=/path/to/bin    # see NOTE below
#
# btrblocks rev-btr-sis and FastLanes rev-fls-sis-pre (cross-format-alignment) carry the
# shared-codec and wide-section/codec-aware fixes. Only FastLanes' local gcc 11
# FLS_PATCH is still applied on top (idempotent, never committed).
#
# Idempotent like cross_format.sh: builds only when the binary is missing or was
# built from a different commit+patch-set (build stamp includes each patch's
# md5), regenerates datasets if needed, skips any output CSV that already
# exists. Each stage is independent; a failing stage is logged, others still run.
#
# Output format (standardized CSVs, one per format per run):
#   $O/<format>_run<N>.csv   format in {nimble,btrblocks,fastlanes}, N in 1..XF_RUNS
#   header: format,arm,dataset,bits_per_value,point_ns,range64_ns,validated
#   arm in {auto, auto_sis}
#
# NOTE on Nimble: this stage shells out to the existing, unmodified
# xf_nimble_shared.sh (not xf_nimble.sh) for the nimble_run*.csv files, exactly
# as it already runs on the shared codec set (both arms via Auto/view, sections
# held to the same set). That script currently hardcodes its own Nimble tree/
# binary path (R=$HOSTDATA/project, wt-encode-speed
# build). NIMBLE_TREE/NIMBLE_BIN below default to the same values and are
# exported for forward-compatibility, but xf_nimble_shared.sh does not itself
# read them yet (we did not modify that script) - so overriding them here is a
# no-op until xf_nimble_shared.sh is updated to consult them.
#
# CAUTION: reuses the SAME btrblocks/FastLanes checkouts as cross_format.sh
# (under $X below), patched in place. Do not run this concurrently with
# cross_format.sh - the two apply different, mutually-exclusive patch sets to
# the same working trees.
set -u
R=$HOSTDATA/project
X=$R/cross_format
DS=$R/Datasets
S=$RESULTS
XS=$S/cross_format
P=$XS/patches
ROWS=524288
BTR_URL=<fork-url>/btrblocks.git
FLS_URL=<fork-url>/FastLanes.git
BTR_COMMIT=rev-btr-sis
FLS_COMMIT=rev-fls-sis-pre
FLS_PATCH=$P/fastlanes_gcc11_alp_avx512.patch
TAG=${XF_TAG:-xf_shared_$(date +%Y%m%d_%H%M%S)}
O=$XS/$TAG
STAGES=${XF_STAGES:-btr fls}
RUNS=${XF_RUNS:-3}
DATA=$X/data_$ROWS
# shared codec set: what btrblocks/fastlanes/nimble all support in a section/scheme sense.
SHARED_CODECS=Trivial,Constant,Dictionary,RLE,PFOR,MainlyConstant,SparseBool,FixedBitWidth
NIMBLE_TREE=${NIMBLE_TREE:-$R}
NIMBLE_BIN=${NIMBLE_BIN:-$NIMBLE_TREE/wt-encode-speed/_build_release/velox/dwio/nimble/encodings/benchmarks/ml_id_compression}
export NIMBLE_TREE NIMBLE_BIN
COLS="snowflake xmark_prepost_full osm_h3_r9_fileorder osm_s2_l30_fileorder bing_quadkey uuidv7_hi uuidv7_lo publicbi_npi publicbi_id1"
export CMAKE_POLICY_VERSION_MINIMUM=3.5   # cmake 4.x vs the vendored deps' cmake_minimum_required
mkdir -p $O $X
say() { echo "[$(date +%T)] xfs: $*" | tee -a $O/xf.log; }
has() { case " $STAGES " in *" $1 "*) return 0;; esac; return 1; }
memok() { local a; a=$(free -g | awk '/^Mem:/{print $7}'); [ "$a" -ge 24 ] || { say "only ${a}G available, not building"; return 1; }; }

ensure_repo() {  # dir url commit
  local d=$1 url=$2 c=$3
  [ -d $d/.git ] || git clone -q -b cross-format-alignment $url $d || return 1
  if [ "$(git -C $d rev-parse --short=7 HEAD)" != "$c" ]; then
    git -C $d fetch -q origin cross-format-alignment && git -C $d checkout -q -- . && git -C $d checkout -q --detach $c || return 1
  fi
}

apply_patch() {  # dir patch
  local d=$1 patch=$2
  git -C $d apply --reverse --check $patch 2>/dev/null && return 0
  git -C $d apply $patch 2>/dev/null && return 0
  say "FAIL applying $patch"; return 1
}

# --- manifest -----------------------------------------------------------------
{
  echo "tag=$TAG"; echo "start=$(date -Is)"; echo "host=$(hostname)"
  echo "cpu=$(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2- | sed 's/^ //')"
  echo "governor=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo n/a)"
  echo "gcc=$(gcc -dumpfullversion)"; echo "cmake=$(cmake --version | head -1)"
  echo "rows=$ROWS order=file columns=$COLS runs=$RUNS shared_codecs=$SHARED_CODECS"
  echo "btrblocks=$BTR_COMMIT fastlanes=$FLS_COMMIT stages=$STAGES"
  echo "fls_patches=$FLS_PATCH (local gcc 11 fix)"
} > $O/manifest.txt

# --- repos + patches + builds (one at a time, -j10) -------------------------------
btr_ok=0; fls_ok=0
if has btr; then
  B=$X/btrblocks
  if ensure_repo $B $BTR_URL $BTR_COMMIT; then
    stamp="$BTR_COMMIT"
    if [ -x $B/build/subintsplit_bench ] && [ "$(cat $B/build/.xf_shared_stamp 2>/dev/null)" = "$stamp" ]; then btr_ok=1
    elif memok; then
      say "building btrblocks subintsplit_bench (shared-codec patches)"
      # Makefiles, not Ninja: the vendored ExternalProjects lack BUILD_BYPRODUCTS.
      if cmake -S $B -B $B/build -DCMAKE_BUILD_TYPE=Release > $O/btr_cfg.log 2>&1 &&
         nice cmake --build $B/build -j10 --target subintsplit_bench > $O/btr_build.log 2>&1; then
        echo "$stamp" > $B/build/.xf_shared_stamp; btr_ok=1
      else say "FAIL btrblocks build (see btr_build.log)"; fi
    fi
  else say "FAIL btrblocks checkout"; fi
fi
if has fls; then
  F=$X/FastLanes
  if ensure_repo $F $FLS_URL $FLS_COMMIT; then
    apply_patch $F $FLS_PATCH
    stamp="$FLS_COMMIT+$(md5sum < $FLS_PATCH | cut -c1-8)"
    FB=$F/build/benchmark/bench_subintsplit/bench_subintsplit
    if [ -x $FB ] && [ "$(cat $F/build/.xf_shared_stamp 2>/dev/null)" = "$stamp" ]; then fls_ok=1
    elif memok; then
      say "building FastLanes bench_subintsplit (gcc, FLS_BUILD_TESTING=ON)"
      mkdir -p $X/fls_data_stub   # FASTLANES_DATA_DIR: skip fetching FastLanes_Data
      # FLS_BUILD_TESTING must be ON: the codec-aware SIS patch's bench_subintsplit
      # cross-checks link gtest, which FastLanes only fetches/builds under this flag.
      if FASTLANES_DATA_DIR=$X/fls_data_stub cmake -S $F -B $F/build -DCMAKE_BUILD_TYPE=Release \
           -DCMAKE_CXX_COMPILER=g++ -DCMAKE_C_COMPILER=gcc -DFLS_BUILD_BENCHMARKING=ON \
           -DFLS_BUILD_TESTING=ON > $O/fls_cfg.log 2>&1 &&
         nice cmake --build $F/build -j10 --target bench_subintsplit > $O/fls_build.log 2>&1; then
        echo "$stamp" > $F/build/.xf_shared_stamp; fls_ok=1
      else say "FAIL FastLanes build (see fls_build.log)"; fi
    fi
  else say "FAIL FastLanes checkout"; fi
fi

# --- datasets --------------------------------------------------------------------
if [ -d $X/FastLanes/scripts ]; then
  python3 $XS/make_xf_datasets.py --datasets $DS --fastlanes $X/FastLanes --out $DATA --rows $ROWS \
    > $O/datasets.log 2>&1 || { say "FAIL datasets"; btr_ok=0; fls_ok=0; }
fi

# --- timing: one benchmark at a time ------------------------------------------------
if [ -z "${XF_HAVE_TIMING_LOCK:-}" ]; then exec 7>$R/bench_timing.lock; flock 7; fi

if has btr && [ $btr_ok = 1 ]; then
  mkdir -p $O/btr_raw
  DARGS=(); for c in $COLS; do DARGS+=(--dataset "real_$c=$DATA/txt/$c.txt"); done
  for i in $(seq 1 $RUNS); do
    if [ -f $O/btrblocks_run$i.csv ]; then say "btr run$i: reusing"; continue; fi
    say "btr run$i: run"
    RAW=$O/btr_raw
    if nice $X/btrblocks/build/subintsplit_bench --rows $ROWS --block-sizes 65536 --shared-codecs \
         --codecs AUTO_BASELINE64,AUTO_WITH_SIS64 "${DARGS[@]}" \
         --csv $RAW/btr_results_run$i.csv --sections-csv $RAW/btr_sections_run$i.csv \
         --range-csv $RAW/btr_range_run$i.csv --plans-csv $RAW/btr_plans_run$i.csv \
         --metadata-csv $RAW/btr_metadata_run$i.csv > $RAW/btr_run$i.log 2>&1; then
      python3 - $RAW/btr_results_run$i.csv $RAW/btr_range_run$i.csv $O/btrblocks_run$i.csv <<'PY'
import csv, sys
res, rng, out = sys.argv[1:4]
ARM = {"AUTO_BASELINE64": "auto", "AUTO_WITH_SIS64": "auto_sis"}
ORDER = ["snowflake", "xmark_prepost_full", "osm_h3_r9_fileorder", "osm_s2_l30_fileorder",
         "bing_quadkey", "uuidv7_hi", "uuidv7_lo", "publicbi_npi", "publicbi_id1"]
r64 = {}
for r in csv.DictReader(open(rng)):
    if r["width"] == "64" and r["B"] == "64":
        r64[(r["dataset"], r["codec"])] = float(r["ns_per_range"])
rows = []
for r in csv.DictReader(open(res)):
    if r["width"] != "64" or r["codec"] not in ARM or not r["dataset"].startswith("real_"):
        continue
    ds = r["dataset"][len("real_"):]
    n = int(r["rows"])
    rows.append((ARM[r["codec"]], ds, int(r["encoded_bytes"]) * 8 / n,
                 float(r["point_ms"]) * 1e6 / int(r["point_count"]),
                 r64.get((r["dataset"], r["codec"]), float("nan")), int(r["validated"])))
rows.sort(key=lambda t: (ORDER.index(t[1]) if t[1] in ORDER else 999, t[0]))
with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["format", "arm", "dataset", "bits_per_value", "point_ns", "range64_ns", "validated"])
    for a, ds, bpv, p, rg, v in rows:
        w.writerow(["btrblocks", a, ds, f"{bpv:.4f}", f"{p:.1f}", f"{rg:.1f}", v])
PY
    else say "FAIL btr run$i (see $RAW/btr_run$i.log)"; fi
  done
fi

if has fls && [ $fls_ok = 1 ]; then
  F=$X/FastLanes; RES=$F/benchmark/result/subintsplit
  for i in $(seq 1 $RUNS); do
    if [ -f $O/fastlanes_run$i.csv ]; then say "fls run$i: reusing"; continue; fi
    say "fls run$i: run"
    rm -f $RES/subintsplit.csv
    if FLS_SUBINTSPLIT_MANIFEST=$DATA/fls/manifest.csv FLS_SUBINTSPLIT_SHARED_CODECS=1 \
       FLS_SUBINTSPLIT_ROWS=wizard_without_sis,wizard_with_sis \
       nice $F/build/benchmark/bench_subintsplit/bench_subintsplit \
         > $O/fls_run$i.log 2>&1 && [ -f $RES/subintsplit.csv ]; then
      cp $RES/subintsplit.csv $O/fastlanes_run${i}_raw.csv
      cp $RES/subintsplit_run_metadata.csv $O/fastlanes_run${i}_metadata.csv
      python3 - $O/fastlanes_run${i}_raw.csv $O/fastlanes_run$i.csv $O/fastlanes_run${i}_codecs.txt <<'PY'
import csv, sys
ROWS = 524288
ARMS = {"wizard_without_sis": "auto", "wizard_with_sis": "auto_sis"}
DATASETS = ["snowflake", "xmark_prepost_full", "osm_h3_r9_fileorder", "osm_s2_l30_fileorder", "bing_quadkey",
            "uuidv7_hi", "uuidv7_lo", "publicbi_npi", "publicbi_id1"]
raw, out, codecs_out = sys.argv[1], sys.argv[2], sys.argv[3]
m = {}
for r in csv.DictReader(open(raw)):
    if r["encoding"] not in ARMS:
        continue
    k = (r["dataset"], ARMS[r["encoding"]])
    d = m.setdefault(k, {})
    met = r["metric"]
    if met == "range_read":
        if r["detail"] == "64":
            d["range64"] = float(r["value"])
    elif met in ("schema", "sis_layout"):
        d[met] = r["note"]
    elif met in ("compressed_size", "point_decode_then_index", "validated"):
        d[met] = float(r["value"])
with open(out, "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["format", "arm", "dataset", "bits_per_value", "point_ns", "range64_ns", "validated"])
    for ds in DATASETS:
        for arm in ("auto", "auto_sis"):
            d = m.get((ds, arm))
            if d is None or "compressed_size" not in d:
                print(f"missing {ds}/{arm}", file=sys.stderr)
                continue
            w.writerow(["fastlanes", arm, ds, f"{d['compressed_size'] * 8 / ROWS:.4f}",
                        f"{d.get('point_decode_then_index', float('nan')) * 1000:.2f}",
                        f"{d.get('range64', float('nan')) * 1000:.2f}", int(d.get("validated", 0) == 1)])
with open(codecs_out, "w") as f:
    f.write("# dataset arm top_level_token [sis_layout: starts|bw_med|codecs (rowgroup 0)]\n")
    for ds in DATASETS:
        for arm in ("auto", "auto_sis"):
            d = m.get((ds, arm), {})
            f.write(f"{ds} {arm} {d.get('schema', '?')}" +
                    (f" [{d['sis_layout']}]" if "sis_layout" in d else "") + "\n")
PY
      say "fls run$i done"
    else say "FAIL fls run$i (see $O/fls_run$i.log)"; fi
  done
fi

# Nimble on the shared codec set (auto / auto_sis, both sections held to $SHARED_CODECS);
# delegates to the existing xf_nimble_shared.sh, which writes nimble_run{1,2,3}.csv itself
# (its own run count is fixed at 3 - XF_RUNS above only governs the btr/fls loops above).
if [ -z "${XF_SKIP_NIMBLE:-}" ]; then
  say "nimble shared: run"
  XF_SHARED_OUT=$O bash $S/xf_nimble_shared.sh >> $O/xf.log 2>&1 || say "FAIL nimble shared (see xf.log)"
fi

echo "end=$(date -Is)" >> $O/manifest.txt
say "XF_DONE $TAG csv=$(find $O -maxdepth 1 -name '*.csv' | wc -l) fails=$(grep -c FAIL $O/xf.log)"
