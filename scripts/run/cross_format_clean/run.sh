#!/bin/bash
# Clean cross-format rerun (BtrBlocks rev-btr-sis, FastLanes rev-fls-sis = branch cost-model-fix, Nimble evaluation rev-kdefault).
# FastLanes rev-fls-sis = rev-fls-sis-pre + single-section guard on the SIS split (fixes the npi cost-model bias, see README).
# See README.md beside this file. Launch detached:
#   setsid nohup bash $RESULTS/cross_format_clean_20260929_1705/run.sh \
#     >> $RESULTS/cross_format_clean_20260929_1705/run.log 2>&1 < /dev/null &
# It blocks on bench_timing.lock (held by sweep_full_20260929_0115 through its Stage 5) before doing anything.
# Resumable: rerun the same command; finished CSVs are skipped. Control: touch $O/STOP to stop before the next run.
set -u
R=$HOSTDATA/project; L=$R/bench_timing.lock

# ---- 1. timing lock FIRST: nothing below runs until the full-length sweep has released it ----------------------
exec 9>$L; flock 9

O=$(cd "$(dirname "$0")" && pwd); cd $O
S=$RESULTS; DS=$R/Datasets
XF0=$S/cross_format_shared.sh                # pinned harness (btr/fls stages)
FLS_PIN=rev-fls-sis                              # FastLanes cost-model-fix (local branch in the benchmark host checkout, not on GitHub)
XF=$O/cross_format_shared_fls_fix.sh         # = XF0 with FLS_COMMIT=rev-fls-sis-pre -> $FLS_PIN, nothing else changed
XO=$O/xf                                      # its output dir: XF_TAG is relative to $S/cross_format
XTAG=../$(basename $O)/xf
SRC_BIN=$S/sweep_full_20260929_0115/bin       # evaluation rev-kdefault, sha256 in SHA256SUMS
BIN=$O/bin
P=$O/progress.log
REPS=3; LOAD_MAX=4; LOAD_WAIT_MIN=30
SH=Trivial,Constant,Dictionary,RLE,PFOR,MainlyConstant,SparseBool,FixedBitWidth
declare -A LIST=([auto]=$SH [auto_sis]=$SH,SubIntSplit)
# Same 9 columns, sources and 524,288 leading rows as cross_format_shared.sh / make_xf_datasets.py / xf_nimble_shared.sh.
NCOLS="TwitterSnowflake/csv/tweet_id.txt:snowflake XMark/csv/prepost_id_full.txt:xmark_prepost_full OSM/csv/h3_r9_fileorder.txt:osm_h3_r9_fileorder OSM/csv/s2_l30_fileorder.txt:osm_s2_l30_fileorder BingTiles/csv/quadkey_fileorder.txt:bing_quadkey UUIDv7/csv/uuidv7_hi.txt:uuidv7_hi UUIDv7/csv/uuidv7_lo.txt:uuidv7_lo PublicBI/Medicare1/csv/NPI.txt:publicbi_npi PublicBI/Corporations/csv/Id1.txt:publicbi_id1"
ROWS=524288

log() { echo "[$(date '+%F %T %Z')] $*" | tee -a $P; }
hostinfo() { echo "load=$(cut -d' ' -f1-3 /proc/loadavg) memavail_gb=$(awk '/MemAvailable/{printf "%d",$2/1048576}' /proc/meminfo) data_free_gb=$(df -BG --output=avail /data | tail -1 | tr -dc 0-9)"; }
stopped() { [ -f $O/STOP ]; }
load1() { cut -d' ' -f1 /proc/loadavg; }

# Memory/disk gate: wait up to 20 min for >= $1 GB available memory and >= 10 GB free on /data.
gate() { local need=${1:-20} i ma fr; for i in $(seq 1 40); do
  ma=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo); fr=$(df -BG --output=avail /data | tail -1 | tr -dc 0-9)
  [ "$ma" -ge "$need" ] && [ "$fr" -ge 10 ] && return 0; [ $i -eq 1 ] && log "  waiting: mem ${ma}GB (need $need) disk ${fr}GB"; sleep 30; done
  log "  gate failed (mem ${ma}GB disk ${fr}GB)"; return 1; }

# Load gate: wait (60 s polls) up to LOAD_WAIT_MIN for the 1-minute load to drop to <= LOAD_MAX.
loadgate() { local i; for i in $(seq 0 $LOAD_WAIT_MIN); do
  awk -v l=$(load1) -v m=$LOAD_MAX 'BEGIN{exit !(l<=m)}' && return 0
  [ $i -eq 0 ] && log "  load $(load1) > $LOAD_MAX, waiting up to ${LOAD_WAIT_MIN} min"; [ $i -lt $LOAD_WAIT_MIN ] && sleep 60; done
  return 1; }

# Watchdog (as sweep_full_20260929_0115/run.sh): kill the running step on <8 GB memory or <6 GB disk.
watchdog() { while :; do sleep 20
  ma=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo); fr=$(df -BG --output=avail /data | tail -1 | tr -dc 0-9); bad=""
  [ "$ma" -lt 8 ] && bad="low memory ${ma}GB"; [ "$fr" -lt 6 ] && bad="low disk ${fr}GB free"
  if [ -n "$bad" ]; then echo "watchdog: $bad" > $O/STOP; pg=$(cat $O/current.pgid 2>/dev/null)
    [ -n "$pg" ] && kill -TERM -- -$pg 2>/dev/null; log "WATCHDOG $bad; killed pgid ${pg:-none}"; fi
done; }

# step <name> <done-file> <cmd...>: skip if done; own process group; 4 h timeout; ok/FAIL line with host state.
step() { local name=$1 out=$2 s rc pid; shift 2; [ -f "$out" ] && return 0
  s=$(date +%s); echo "$(date -Is) $name: $*" >> $O/commands.txt
  setsid timeout -s TERM 4h "$@" > $O/logs/$name.log 2>&1 &
  pid=$!; echo $pid > $O/current.pgid; wait $pid; rc=$?; rm -f $O/current.pgid
  if [ $rc -eq 0 ] && [ -f "$out" ]; then log "    ok $(( $(date +%s)-s ))s $name  [$(hostinfo)]"; return 0; fi
  log "    FAIL rc=$rc $(( $(date +%s)-s ))s $name (logs/$name.log)"; echo "$name" >> $O/failed.txt; return 1; }

# One timed run = one format x one repeat (all 9 columns, both arms).
xf_env() { env XF_TAG=$XTAG XF_HAVE_TIMING_LOCK=1 XF_SKIP_NIMBLE=1 "$@"; }
run_btr() { step btr_r$1 $XO/btrblocks_run$1.csv env XF_TAG=$XTAG XF_HAVE_TIMING_LOCK=1 XF_SKIP_NIMBLE=1 XF_STAGES=btr XF_RUNS=$1 bash $XF; }
run_fls() { step fls_r$1 $XO/fastlanes_run$1.csv env XF_TAG=$XTAG XF_HAVE_TIMING_LOCK=1 XF_SKIP_NIMBLE=1 XF_STAGES=fls XF_RUNS=$1 bash $XF; }
# Nimble: the commands of xf_nimble_shared.sh (lines 13-19) per repeat, with the evaluation binaries in $BIN.
run_nimble() { step nimble_r$1 $XO/nimble_run$1.csv bash $O/nimble_rep.sh $1; }

attempt() {  # attempt <fmt> <rep>: returns 0 done/ran, 2 deferred (load)
  local out; case $1 in btr) out=$XO/btrblocks_run$2.csv;; fls) out=$XO/fastlanes_run$2.csv;; nimble) out=$XO/nimble_run$2.csv;; esac
  [ -f $out ] && return 0
  if stopped; then echo "SKIPPED(stop) $1_r$2" >> $O/skipped.txt; return 0; fi
  gate 20 || { echo "SKIPPED(gate) $1_r$2" >> $O/skipped.txt; return 0; }
  loadgate || { log "  DEFER $1 r$2: load $(load1) > $LOAD_MAX after ${LOAD_WAIT_MIN} min"; return 2; }
  log "  $1 r$2 start [$(hostinfo)]"; echo "$(date -Is) $1_r$2 $(hostinfo)" >> $O/loads.log
  run_$1 $2; return 0; }

# ---------------------------------------------------------------------------------------------------------------
rm -f $O/current.pgid; mkdir -p $XO $O/logs $BIN
log "timing lock held [$(hostinfo)]"
watchdog 9>&- & WD=$!
trap 'kill $WD 2>/dev/null; pg=$(cat $O/current.pgid 2>/dev/null); [ -n "$pg" ] && kill -TERM -- -$pg 2>/dev/null' EXIT
trap 'log "SIGTERM received"; echo "SIGTERM" > $O/STOP; exit 143' TERM

# ---- 2. Nimble binaries: copy the evaluation-branch drivers once, verify sha256 ------------------------------------
if [ ! -f $BIN/.verified ]; then
  for b in nimble_ml_id_compression_benchmark nimble_ml_id_decode_point_benchmark nimble_ml_id_decode_range_benchmark; do
    cp -p $SRC_BIN/$b $BIN/; grep " $b\$" $SRC_BIN/SHA256SUMS >> $BIN/SHA256SUMS; done
  (cd $BIN && sha256sum -c SHA256SUMS) >> $P 2>&1 && touch $BIN/.verified || { log "FAIL nimble binary sha256"; exit 1; }
fi

# ---- 3. prep: pinned checkouts + builds + datasets (cross_format_shared.sh with XF_RUNS=0 runs no benchmark) --------
BTR=$R/cross_format/btrblocks; FLS=$R/cross_format/FastLanes
# FastLanes pin: the harness hard-codes FLS_COMMIT=rev-fls-sis-pre; run a copy that differs only in that line. rev-fls-sis exists
# only as the local branch cost-model-fix of $FLS (fetched from a git bundle); ensure_repo's fetch of origin keeps it.
git -C $FLS cat-file -e $FLS_PIN^{commit} 2>/dev/null || { log "FAIL FastLanes $FLS_PIN missing in $FLS (fetch branch cost-model-fix)"; exit 1; }
sed "s/^FLS_COMMIT=rev-fls-sis-pre\$/FLS_COMMIT=$FLS_PIN/" $XF0 > $XF
[ "$(diff $XF0 $XF | grep -c '^[<>]')" = 2 ] && grep -q "^FLS_COMMIT=$FLS_PIN\$" $XF || { log "FAIL harness copy (FLS_COMMIT line not replaced exactly once)"; exit 1; }
prep_ok() { [ "$(git -C $BTR rev-parse --short=7 HEAD)" = rev-btr-sis ] && [ "$(git -C $FLS rev-parse --short=7 HEAD)" = $FLS_PIN ] &&
  [ "$(cat $BTR/build/.xf_shared_stamp 2>/dev/null)" = rev-btr-sis ] && [ "$(cut -d+ -f1 $FLS/build/.xf_shared_stamp 2>/dev/null)" = $FLS_PIN ] &&
  [ -x $BTR/build/subintsplit_bench ] && [ -x $FLS/build/benchmark/bench_subintsplit/bench_subintsplit ] &&
  [ -s $R/cross_format/data_$ROWS/fls/manifest.csv ]; }
if ! prep_ok; then
  log "=== prep: checkout rev-btr-sis/$FLS_PIN, build (-j10), datasets [$(hostinfo)]"
  gate 24 || { log "FAIL prep gate"; exit 1; }
  setsid timeout -s TERM 4h env XF_TAG=$XTAG XF_HAVE_TIMING_LOCK=1 XF_SKIP_NIMBLE=1 XF_STAGES="btr fls" XF_RUNS=0 \
    bash $XF > $O/logs/prep.log 2>&1
  cp $XO/manifest.txt $O/manifest_prep.txt 2>/dev/null
  prep_ok || { log "FAIL prep (logs/prep.log, xf/xf.log)"; exit 1; }
fi
{ echo "btrblocks $(git -C $BTR log -1 --format='%h %s') stamp=$(cat $BTR/build/.xf_shared_stamp)"
  echo "fastlanes $(git -C $FLS log -1 --format='%h %s') stamp=$(cat $FLS/build/.xf_shared_stamp)"
  echo "harness: $XF (= $XF0 with FLS_COMMIT=$FLS_PIN)"
  echo "fastlanes local diff: $(git -C $FLS diff --stat -- src | tail -1)  (gcc 11 FLS_PATCH only)"
  echo "nimble evaluation rev-kdefault: $(cat $BIN/SHA256SUMS | tr '\n' ' ')"
  echo "rows=$ROWS columns=9 reps=$REPS load_max=$LOAD_MAX"; } > $O/builds.txt
log "prep ok: $(tr '\n' ';' < $O/builds.txt | cut -c1-300)"

# ---- 4. timed runs: 3 interleaved repeats, formats rotated per repeat, load-gated ---------------------------------
DEFERRED=""
for rep in $(seq 1 $REPS); do
  case $rep in 1) ORD="btr fls nimble";; 2) ORD="fls nimble btr";; *) ORD="nimble btr fls";; esac
  log "=== repeat $rep ($ORD)"
  for f in $ORD; do attempt $f $rep; [ $? = 2 ] && DEFERRED="$DEFERRED $f:$rep"; done
done
for fr in $DEFERRED; do f=${fr%%:*}; rep=${fr##*:}; log "=== deferred $f r$rep retry"
  attempt $f $rep; [ $? = 2 ] && { log "  SKIPPED(load) $f r$rep"; echo "SKIPPED(load) ${f}_r$rep" >> $O/skipped.txt; }
done

# ---- 5. summary ----------------------------------------------------------------------------------------------------
nc=$(ls $XO/*_run[0-9].csv 2>/dev/null | wc -l); nv=$(cat $XO/*_run[0-9].csv 2>/dev/null | awk -F, '$1!="format" && $7!=1' | wc -l)
nf=$(cat $O/failed.txt 2>/dev/null | wc -l); ns=$(cat $O/skipped.txt 2>/dev/null | wc -l)
if [ $nc -eq $((3*REPS)) ] && ! stopped; then log "DONE csv=$nc unvalidated_rows=$nv fails=$nf skipped=$ns"
  echo "csv=$nc unvalidated_rows=$nv fails=$nf skipped=$ns $(date -Is)" > $O/DONE
else log "INCOMPLETE csv=$nc/$((3*REPS)) fails=$nf skipped=$ns$(stopped && echo " stopped: $(cat $O/STOP)"); rerun run.sh to resume"; fi
