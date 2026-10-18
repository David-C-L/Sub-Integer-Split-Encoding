#!/bin/bash
# Build for toplevel_sec7: wt-evaluation at rev-toplevel (evaluation) + eval/arm-a-trivial-sections rev-arm-a
# (--mlidc_sis_pinned_row_frame) + build/toplevel_sec7.patch's driver changes (admission estimate and
# cost-model oracle honour --mlidc_sis_section_candidates), applied uncommitted. Targets only, -j10.
# Binaries are copied to bin/ (SHA256SUMS) and the tree is restored to rev-toplevel afterwards.
set -u
O=$RESULTS/toplevel_sec7_20261014_1526; R=$HOSTDATA/project; W=$R/wt-evaluation; B=$W/_build_release
BD=$B/velox/dwio/nimble/encodings/benchmarks/ml_id_compression
T="nimble_ml_id_compression_benchmark nimble_ml_id_encode_benchmark nimble_ml_id_decode_bulk_benchmark nimble_ml_id_decode_point_benchmark nimble_ml_id_decode_gather_benchmark nimble_ml_id_decode_range_benchmark nimble_ml_id_admission_benchmark nimble_ml_id_cost_model_oracle_benchmark"
exec 8>>$RESULTS/bench_timing.lock; flock 8; exec 9>>$R/bench_timing.lock; flock 9
echo "[$(date +%T)] locks held"
cd $W; [ "$(git rev-parse HEAD)" = rev-toplevel ] || { echo BAD_HEAD; exit 1; }
[ -z "$(git status --short -uno)" ] || { echo DIRTY; exit 1; }
git apply $O/build/toplevel_sec7.patch || { echo APPLY_FAIL; exit 1; }
git diff > $O/build/applied.diff; git rev-parse HEAD > $O/build/HEAD
ninja -C $B -j10 $T > $O/build/ninja.log 2>&1; rc=$?
echo "[$(date +%T)] ninja rc=$rc"
if [ $rc = 0 ]; then mkdir -p $O/bin; for t in $T; do cp $BD/$t $O/bin/; done; (cd $O/bin && sha256sum * > SHA256SUMS); fi
git checkout -- velox && [ -z "$(git status --short -uno)" ] && echo "[$(date +%T)] tree restored"
echo BUILD_DONE rc=$rc
