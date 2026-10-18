# Code

| dir | what | base (public) | licence |
|---|---|---|---|
| `velox-nimble/` | SIS in Nimble (Velox `velox/dwio/nimble`), the `nimble_ml_id_*` benchmark drivers and tests | facebookincubator/velox `235512ebf` | Apache-2.0 (`velox-nimble/LICENSE`, `NOTICE.txt`) |
| `btrblocks/` | SIS ported to BtrBlocks as an integer scheme, and the `subintsplit_bench` driver | maxi-k/btrblocks `c950c3c` | MIT (`btrblocks/LICENSE`) |
| `fastlanes/` | SIS ported to FastLanes as an encoding in its wizard, and the `bench_subintsplit` driver | cwida/FastLanes `f0edc10` | MIT (`fastlanes/LICENSE`) |

Each dir holds `sis.patch` (the complete change against the public base, `git diff` format) and `src/` (the full
content of every added or modified file, at the same relative paths). The two agree: applying `sis.patch` to an
export of the base gives exactly `src/` (checked for all three). Files under `code/` keep the licence of the
project they modify; the MIT licence at the repository root covers only the rest of this repository.

## Nimble (`velox-nimble/`)

`sis.patch` changes 135 files, all under `velox/dwio/nimble/` (41 added, 90 modified, 4 deleted:
`encodings/subintsplit/{CostModel.cpp,SectionEncoder.h,SectionMetrics.cpp,SectionTable.h}`). It also replaces
three comment and documentation lines of the base that referred to internal resources.

### Build
```
git clone https://github.com/facebookincubator/velox.git && cd velox && git checkout 235512ebf
git apply /path/to/code/velox-nimble/sis.patch          # or: cp -r /path/to/code/velox-nimble/src/velox .
cmake -S . -B _build_release -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DVELOX_ENABLE_NIMBLE=ON -DNIMBLE_BUILD_TESTING=ON -DNIMBLE_ENABLE_EXPERIMENTAL_ENCODINGS=ON \
  -DVELOX_BUILD_MINIMAL_WITH_DWIO=ON -DVELOX_ENABLE_PARQUET=ON -DVELOX_MONO_LIBRARY=ON \
  -DVELOX_DEPENDENCY_SOURCE=SYSTEM -Dopenzl_SOURCE=BUNDLED -Dfaiss_SOURCE=BUNDLED
ninja -C _build_release nimble_encodings_tests \
  nimble_ml_id_compression_benchmark nimble_ml_id_encode_benchmark nimble_ml_id_decode_bulk_benchmark \
  nimble_ml_id_decode_point_benchmark nimble_ml_id_decode_range_benchmark nimble_ml_id_decode_gather_benchmark \
  nimble_ml_id_admission_benchmark nimble_ml_id_cost_model_oracle_benchmark
```
- Tested environment: the `ghcr.io/facebookincubator/velox-dev:ubuntu-22.04` image (GCC 11.4.0, CMake 4.3.2), whose
  Folly is new enough; the build of the targets above takes about 45 minutes at `-j8`. faiss is bundled because the
  image's system faiss fails to configure (`OpenMP::OpenMP_CXX` not found).
- Compiler: GCC 11.4.0; Release gives `-O3 -DNDEBUG`. The complete CMake cache options of the benchmark build
  are in `velox-nimble/cmake_options.txt`; the flags above are the ones that select what is built.
- Dependencies: Velox's own setup scripts (`scripts/setup-*.sh`) for the base revision. Folly must be new enough
  to provide `folly/executors/ThreadedRepeatingFunctionRunner.h`; older system Folly packages fail in
  `velox_common_base`.
- The drivers are in `velox/dwio/nimble/encodings/benchmarks/ml_id_compression/` (flags: `MlIdBenchmarkFlags.cpp`,
  method: `METHODOLOGY.md`); they are built only with `NIMBLE_ENABLE_EXPERIMENTAL_ENCODINGS=ON`.
- Tests: `_build_release/velox/dwio/nimble/encodings/tests/nimble_encodings_tests` (SubIntSplit tests:
  `--gtest_filter='*SubIntSplit*'`).

### Run scripts and binaries
Every run script names its binary and all flags; `$RESULTS`, `$HOSTDATA` and `$PROJECT` are placeholders for the
result, data and checkout directories on the benchmark host.

| script | binaries (`nimble_ml_id_<x>_benchmark`) |
|---|---|
| `scripts/run/toplevel_sec7/{run.sh,run_extra.sh,w524_tl.sh}` | compression, encode, decode_bulk, decode_point, decode_range, decode_gather, admission, cost_model_oracle |
| `scripts/run/decode_knob_toplevel/`, `data/decode_knob_8col/scripts/` | compression, encode, decode_bulk, decode_point, decode_range, decode_gather |
| `scripts/run/sweep_full2/` | compression, encode, decode_range, decode_gather |
| `scripts/run/addr_toplevel/` | compression, decode_bulk, decode_point, decode_range |
| `scripts/run/alp_floats/` | compression, encode, decode_bulk, decode_point, decode_range |
| `scripts/run/sec1_motivation/` | compression, decode_range |
| `scripts/run/cross_format_clean/` | compression, decode_point, decode_range (`nimble_rep.sh`); BtrBlocks `subintsplit_bench`; FastLanes `bench_subintsplit` |
| `data/plan_time/run.sh`, `data/planner_gap_10m/pg_*.sh`, `data/seq_toplevel/run.sh` | compression, cost_model_oracle, decode_point |

### Code states behind the data
`src/` is `rev-head`. Earlier states differ only in benchmark drivers, opt-in flags and timers. SIS sizes and
plans reproduce byte for byte at `rev-head` (`data/plan_time` re-encodes the planner-gap columns at `rev-head` and
finds sizes and plans equal to `data/toplevel_sec7/plan_decode`); the timings in the paper come from the TopLevel
state binaries listed below.

| data | build |
|---|---|
| `toplevel_sec7/`, `alp_floats/`, `seq_toplevel/` (and the size and read arms of `planner_gap_10m/`) | TopLevel state: `rev-toplevel` + `rev-arm-a` + `eval-patches/toplevel_sec7.patch` (sha256 in `data/toplevel_sec7/bin/SHA256SUMS`); `rev-head` contains all three |
| `plan_time/`, planning time of `planner_gap_10m/` | `rev-head` + `eval-patches/plan_time.patch` (timers only; applies to `src/`) |
| `decode_knob_toplevel/`, `decode_knob_8col/` | `rev-decode-knob` |
| `addr_toplevel_snowflake/`, `sweep_full2/` | `rev-addr-toplevel` |
| `addressability_ladder_20261007/` | ladder: `rev-toplevel` + `rev-arm-a`; priced column: `rev-arm-b` (`rev-arm-b-2` for npi, id1, uuidv7_lo) |
| `cross_format_clean/` | BtrBlocks `rev-btr-sis` = `code/btrblocks`; FastLanes `rev-fls-sis` = `code/fastlanes` + `fastlanes_gcc11_alp_avx512.patch`; its own Nimble rows (`nimble_run*.csv`, not in the paper) `rev-kdefault` |
| `sec1_motivation/` | baselines only (no SIS); any of the builds above |
| `sec2_study/`, `table2_column_stats/`, `bitflip_profiles/` | Python only |

### Revision labels
Revisions of the private development history are named by label; the hashes are withheld for anonymity. Labels
marked "in rev-head" are ancestors of `rev-head`.

| label | date | in rev-head | what |
|---|---|---|---|
| `rev-head` | 2026-10-17 | yes | head of the consolidated evaluation branch; `src/` and `sis.patch` |
| `rev-toplevel` | 2026-10-03 | yes | evaluation branch used for the Sec. 7 TopLevel build |
| `rev-arm-a` | 2026-10-07 | yes | adds `--mlidc_sis_pinned_row_frame` (Arm A, pinned split with Trivial sections) |
| `rev-arm-b`, `rev-arm-b-2` | 2026-10-07 | yes | OpenZL-priced planner (Arm B) and its timing follow-up |
| `rev-decode-knob` | 2026-10-10 | yes | size budget and decode-aware pricing (`--mlidc_sis_size_budget*`) |
| `rev-addr-toplevel` | 2026-09-30 | yes | evaluation merge of the addressable top-level mode |
| `rev-addr-toplevel-feat`, `rev-addr-toplevel-feat-base` | 2026-09-30 | yes | the two commits of that feature branch |
| `rev-addr-strict` | 2026-09-30 | yes | state whose `addressable` mode equals today's `addressable_strict` |
| `rev-addr-for-timing` | 2026-09-30 | yes | build of an earlier FOR-section timing (comment in `scripts/run/addr_toplevel/run.sh`) |
| `rev-kdefault`, `rev-kdefault-base` | 2026-09-28 | yes | evaluation state before the addressable restriction (kDefault section candidates) |
| `rev-sweep-524k`, `rev-profiles`, `rev-admission-39col` | 2026-09-15 to 09-24 | no | earlier sweeps named in comments (524K scoreboard pull, the 42- and 39-column admission sweeps) |
| `rev-encode-speed-1`, `rev-encode-speed-2` | 2026-09-28 | no | encode-speed branch builds mentioned in `data/cross_format_clean/README.md` |
| `rev-btr-sis` | | | BtrBlocks branch head, `code/btrblocks` |
| `rev-btr-pre`, `rev-btr-1` to `rev-btr-3` | | | earlier BtrBlocks revisions named in its README and docs |
| `rev-fls-sis` | | | FastLanes branch head, `code/fastlanes` |
| `rev-fls-sis-pre`, `rev-fls-pre` | | | its parent (without the single-section guard) and an earlier pin |

Public upstream hashes (`235512ebf`, `c950c3c`, `f0edc10`) are given as is.

### Evaluation patches (`velox-nimble/eval-patches/`)
- `toplevel_sec7.patch`: driver changes of the TopLevel build (admission estimate and cost-model oracle honour
  `--mlidc_sis_section_candidates`). Applies to `rev-toplevel` + `rev-arm-a`; already contained in `src/`.
- `plan_time.patch`: planning-time observer and timers in the compression and cost-model-oracle drivers
  (`data/plan_time/`). Applies to `src/` (`git apply eval-patches/plan_time.patch` in the Velox checkout).

## BtrBlocks (`btrblocks/`)
```
git clone https://github.com/maxi-k/btrblocks.git && cd btrblocks && git checkout c950c3c
git apply /path/to/code/btrblocks/sis.patch
# CMake >= 4.0: set the policy minimum in the environment so the vendored ExternalProjects inherit it
CMAKE_POLICY_VERSION_MINIMUM=3.5 cmake -S . -B build -DCMAKE_BUILD_TYPE=Release   # Makefiles: the vendored ExternalProjects lack BUILD_BYPRODUCTS
cmake --build build -j10 --target subintsplit_bench
```
Design notes: `src/docs/subintsplit.md`, `src/docs/subintsplit-porting.md`.

## FastLanes (`fastlanes/`)
```
git clone https://github.com/cwida/FastLanes.git && cd FastLanes && git checkout f0edc10
git apply /path/to/code/fastlanes/sis.patch
git apply /path/to/code/fastlanes/fastlanes_gcc11_alp_avx512.patch     # GCC 11 build fix in ALP's AVX-512 path
mkdir -p /tmp/fls_data_stub
FASTLANES_DATA_DIR=/tmp/fls_data_stub cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_COMPILER=g++ -DCMAKE_C_COMPILER=gcc -DFLS_BUILD_BENCHMARKING=ON -DFLS_BUILD_TESTING=ON
cmake --build build -j10 --target bench_subintsplit
```
The generated test inputs `data/generated/**/generated.csv` (65,536 rows each) are not shipped;
`src/data/generated/subintsplit/generate.py` writes them (see its `README.MD`). Smoke test:
`python3 src/data/generated/subintsplit/generate.py --out-dir DIR --rows 65536` (without the prefix pool it writes
snowflake and tpch, then stops at ipv4), then `FLS_SUBINTSPLIT_DATA_DIR=DIR build/benchmark/bench_subintsplit/bench_subintsplit`. Its IPv4 prefix pool
`ipv4_prefixes.csv` is not shipped either; `generate.py --rebuild-prefixes --dbip <dbip-city-ipv4.csv>` rebuilds it
from the DB-IP Lite database (CC BY 4.0, "IP Geolocation by DB-IP"). The cross-format run prepares its
inputs with `scripts/run/cross_format_clean/make_xf_datasets.py` and drives both formats with
`scripts/run/cross_format_clean/cross_format_shared_fls_fix.sh` (= `cross_format_shared.sh` with the FastLanes pin
set to `rev-fls-sis`).
