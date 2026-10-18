#!/bin/bash
# Build for the plan-time measurement: eval/consolidated-20261017 rev-head + plan_time.patch (uncommitted),
# in a copy of wt-consol1017/_build_release relocated to wt-plantm1017. Only the two patched drivers are built.
set -u
O=$RESULTS/plan_time_20261017_2134; R=$HOSTDATA/project; W=$R/wt-plantm1017; B=$W/_build_release
BD=$B/velox/dwio/nimble/encodings/benchmarks/ml_id_compression
T="nimble_ml_id_compression_benchmark nimble_ml_id_cost_model_oracle_benchmark"
exec 8>>$RESULTS/host_timing.lock; flock 8
echo "[$(date +%T)] lock held"
cd $W; git rev-parse HEAD > $O/HEAD; git diff --stat > $O/diffstat.txt
if [ ! -d $B ]; then cp -a $R/wt-consol1017/_build_release $B || exit 1; python3 $O/pt_reloc.py > $O/reloc.log 2>&1 || { echo RELOC_FAIL; exit 1; }; fi
echo "[$(date +%T)] relocated"
ninja -C $B -n $T 2>/dev/null | grep -c '^\[' > $O/ninja_planned_steps.txt
nice -n 10 ninja -C $B -j8 $T > $O/ninja_drivers.log 2>&1; rc=$?
echo "[$(date +%T)] drivers rc=$rc"
mkdir -p $O/bin; for t in $T; do [ -f $BD/$t ] && cp $BD/$t $O/bin/; done; (cd $O/bin && sha256sum * > SHA256SUMS)
echo BUILD_DONE rc=$rc
