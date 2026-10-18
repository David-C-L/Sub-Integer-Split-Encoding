/*
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifdef NIMBLE_ENABLE_EXPERIMENTAL_ENCODINGS

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <span>
#include <string>
#include <type_traits>
#include <vector>

#include <gflags/gflags.h>

#include "velox/dwio/nimble/encodings/benchmarks/ml_id_compression/BenchCommon.h"
#include "velox/dwio/nimble/encodings/benchmarks/ml_id_compression/DriverSweep.h"
#include "velox/dwio/nimble/encodings/benchmarks/ml_id_compression/ElemType.h"

DEFINE_bool(dry_run, false, "Print sweep plan and exit");

constexpr std::string_view kDriver = "bench_compression";

namespace facebook::nimble::mlidc {
namespace {

template <typename Elem>
void timePlanner(const Vector<Elem>& data, const std::string& name) {
  using Encoding = SubIntSplitEncoding<Elem>;
  using P = typename TypeTraits<Elem>::physicalType;
  constexpr int kBits = static_cast<int>(sizeof(P) * 8);
  const std::span<const P> values(
      reinterpret_cast<const P*>(data.data()), data.size());
  subintsplit::TuningConfig base;
  // The planner sample size the encode uses (--mlidc_sis_planner_samples).
  if (FLAGS_mlidc_sis_planner_samples >= 0) {
    base.sampler.maxSamples =
        static_cast<size_t>(FLAGS_mlidc_sis_planner_samples);
  }
  subintsplit::TuningConfig priced = base;
  // Both priced planners take --mlidc_sis_openzl_extrapolate, as the encode
  // does.
  const auto extrapolation = extrapolationFromFlags(base.sampler.blockSize);
  installOpenZLSectionPricer(
      priced.selector,
      OpenZLPricerGraph::kNimble,
      /*amortiseHeader=*/true,
      extrapolation);
  // The best-of pricer (--mlidc_sis_openzl_pricing=best_of) as the encode
  // installs it: driver-default options and the encoded-header model of
  // --mlidc_sis_openzl_best_of_encoded_header.
  subintsplit::TuningConfig bestOf = base;
  installOpenZLBestOfPricer(
      bestOf.selector,
      nimble::Encoding::Options{},
      bestOf,
      /*amortiseHeader=*/true,
      parseEncodedHeaderModel(FLAGS_mlidc_sis_openzl_best_of_encoded_header),
      extrapolation);
  for (const auto* tuning : {&base, &priced, &bestOf}) {
    std::vector<double> ms;
    std::string plan;
    for (int rep = 0; rep < FLAGS_mlidc_sis_time_planner_reps; ++rep) {
      const auto start = std::chrono::steady_clock::now();
      std::vector<uint64_t> sample;
      subintsplit::sampleIntoU64<P>(values, sample, tuning->sampler);
      const auto cfg = Encoding::plannerSelectorConfig(*tuning, values.size());
      const auto grid = subintsplit::buildRestrictedCostGrid(
          sample, kBits, values.size(), tuning->allowedEncodings, cfg);
      const auto result = subintsplit::selectSplitsOverGrid(grid, kBits, cfg);
      ms.push_back(
          std::chrono::duration<double, std::milli>(
              std::chrono::steady_clock::now() - start)
              .count());
      plan.clear();
      for (const auto& section : result.sections) {
        plan += (plan.empty() ? "" : ";") + std::to_string(section.bitStart) +
            "-" + std::to_string(section.bitEnd);
        if (tuning->selector.sectionChoicePricer) {
          plan += section.storeRaw ? ":raw" : ":enc";
        }
      }
    }
    std::sort(ms.begin(), ms.end());
    std::cout << "  [planner-time] " << name
              << " samples=" << tuning->sampler.maxSamples << " pricer="
              << (tuning->selector.sectionChoicePricer ||
                          tuning->selector.sectionSizePricer
                      ? tuning->selector.sectionSizePricerName
                      : std::string("default"))
              << " reps=" << ms.size() << " median_ms=" << ms[ms.size() / 2]
              << " min_ms=" << ms.front() << " plan=" << plan << "\n";
  }
}

// The whole driver body, templated on the element type. main() picks the
// type from --mlidc_dtype and dispatches here.
template <typename Elem>
int runBenchmark() {
  constexpr size_t kElemSize = sizeof(Elem);

  const uint32_t n = static_cast<uint32_t>(FLAGS_mlidc_rows);
  const uint64_t seed = static_cast<uint64_t>(FLAGS_mlidc_seed);

  // No cache sweep here, so the state is fixed at hot.
  auto contextOrNull =
      makeSweepContext<Elem>(/*withOpenZL=*/true, CacheState::Hot, n);
  if (!contextOrNull.has_value()) {
    return 1;
  }
  const auto& context = *contextOrNull;

  std::cout << "bench_compression: " << context.encoders.size()
            << " encoders x " << context.datasets.size() << " datasets, N=" << n
            << "\n\n";

  if (FLAGS_dry_run) {
    std::cout << "Encoders:\n";
    for (const auto& e : context.encoders)
      std::cout << "  " << e.name << " [" << e.family << "]\n";
    std::cout << "\nDatasets:\n";
    for (const auto& d : context.datasets)
      std::cout << "  " << d.name << "\n";
    return 0;
  }

  std::vector<std::string> csvColumns = {
      "driver",
      "dtype",
      "dataset",
      "encoding",
      "family",
      "variant",
      "inventory",
      "transform",
      "input_order",
      "is_sequential",
      "N",
      "seed",
      "payload_bytes",
      "raw_bytes",
      "compression_ratio",
      "bits_per_elem",
      "skipped",
      "validated"};
  std::string csvPath = FLAGS_mlidc_output_csv.empty() ? "bench_compression.csv"
                                                       : FLAGS_mlidc_output_csv;
  CsvResultWriter csv(csvPath, csvColumns);
  if (!FLAGS_mlidc_output_manifest.empty()) {
    writeRunManifest(FLAGS_mlidc_output_manifest);
  }

  ValidationLedger ledger;

  for (const auto& ds : context.datasets) {
    std::cout << "== Dataset: " << ds.name << " ==\n";
    auto data = ds.generate(n, seed);
    if constexpr (std::is_integral_v<Elem>) {
      if (FLAGS_mlidc_sis_time_planner_reps > 0) {
        timePlanner<Elem>(data, ds.name);
      }
    }
    const size_t rawBytes = static_cast<size_t>(n) * kElemSize;

    if (FLAGS_mlidc_sis_time_planner_reps > 0) {
      if constexpr (std::is_same_v<Elem, uint64_t>) {
        subintsplit::TuningConfig tuning;
        applyReadCostFlags(tuning);
        applyPlannerFlags(tuning);
        const std::span<const uint64_t> values{data.data(), data.size()};
        std::vector<double> millis;
        size_t numSections = 0;
        double weight = 0.0;
        constexpr int kWarmups = 2;
        for (int rep = 0; rep < FLAGS_mlidc_sis_time_planner_reps + kWarmups;
             ++rep) {
          const auto start = std::chrono::steady_clock::now();
          std::vector<uint64_t> sample;
          subintsplit::sampleIntoU64<uint64_t>(values, sample, tuning.sampler);
          auto config = SubIntSplitEncoding<uint64_t>::plannerSelectorConfig(
              tuning, values.size());
          if (config.decodeWeighting.sizeBudget >= 0.0) {
            auto candidateGrid = subintsplit::buildSectionCandidateGrid(
                sample, 64, values.size(), tuning.allowedEncodings, config);
            config = subintsplit::resolveDecodeMix(
                candidateGrid, 64, std::move(config));
            const auto budgeted = subintsplit::selectSplitsWithinSizeBudget(
                candidateGrid, 64, config);
            numSections = budgeted.plan.sections.size();
            weight = budgeted.weight;
          } else {
            const auto grid = subintsplit::buildRestrictedCostGrid(
                sample, 64, values.size(), tuning.allowedEncodings, config);
            numSections = subintsplit::selectSplitsOverGrid(grid, 64, config)
                              .sections.size();
            weight = config.decodeWeighting.weight;
          }
          const auto end = std::chrono::steady_clock::now();
          if (rep >= kWarmups) {
            millis.push_back(
                std::chrono::duration<double, std::milli>(end - start).count());
          }
        }
        std::sort(millis.begin(), millis.end());
        std::cout << "planner_ms dataset=" << ds.name
                  << " median=" << millis[millis.size() / 2]
                  << " min=" << millis.front() << " max=" << millis.back()
                  << " sections=" << numSections << " weight=" << weight
                  << "\n";
      }
    }

    for (const auto& enc : context.encoders) {
      sectionPricerStats().reset();
      const auto encodeStart = std::chrono::steady_clock::now();
      auto target = makeTargetOrSkip<Elem>(enc, data, csv, kDriver, ds.name);
      const double encodeMs = std::chrono::duration<double, std::milli>(
                                  std::chrono::steady_clock::now() -
                                  encodeStart)
                                  .count();
      if (target == nullptr) {
        continue;
      }
      // Context only (one encode, not a measurement loop): wall time of the
      // arm's encode, which includes any planning and stream compression.
      std::cout << "  [encode-time] " << enc.name << " encode_ms=" << encodeMs
                << "\n";
      // Only --mlidc_sis_openzl_pricing makes calls; untimed context for the
      // planning cost of the OpenZL-aware split, not a measurement loop.
      if (const uint64_t calls = sectionPricerStats().calls.load()) {
        std::cout << "  [openzl-pricer] " << enc.name << " calls=" << calls
                  << " pricer_ms="
                  << static_cast<double>(sectionPricerStats().nanos.load()) /
                1e6
                  << " encode_ms=" << encodeMs << "\n";
      }

      if (FLAGS_mlidc_dump_encoding) {
        auto tree = target->describe();
        if (!tree.empty()) {
          std::cout << "  --- " << enc.name << " encoding tree ---\n"
                    << tree << "\n";
        }
        // The same tree again, one node per line and keyed by path. Emitted
        // beside the readable form since the two have different readers.
        auto nodes = target->describeTree();
        if (!nodes.empty()) {
          std::cout << "  --- " << enc.name << " encoding nodes ---\n" << nodes;
        }
        // Each node's cost against what its selection was quoted. Kept
        // separate from the tree above because it decodes every node to
        // recompute the estimate, which the plain tree does not need to do.
        auto estimates = target->describeNodeEstimates();
        if (!estimates.empty()) {
          std::cout << "  --- " << enc.name << " node estimates ---\n"
                    << estimates;
        }
        auto choices = target->describeSectionChoices();
        if (!choices.empty()) {
          std::cout << "  --- " << enc.name << " section choices ---\n"
                    << choices;
        }
      }

      // The encoded bytes the target holds, not an estimate of them.
      const size_t payloadBytes = target->payloadSize();
      const double bpe = n > 0
          ? static_cast<double>(payloadBytes) * 8.0 / static_cast<double>(n)
          : 0.0;

      // A size is only worth reporting for bytes that decode back to the
      // column, so the whole column is round-tripped.
      if (ledger.enabled() &&
          !ledger.check(enc.name, ds.name, "materializeAll", [&] {
            return validateRoundTrip<Elem>(*target, enc, data);
          })) {
        writeValidationFailureRow<Elem>(csv, kDriver, ds.name, enc, [] {});
        continue;
      }

      std::cout << "  " << enc.name << ": " << payloadBytes << " B, "
                << std::fixed << std::setprecision(2) << bpe << " bpe\n";

      csv.beginRow();
      setIdentityColumns<Elem>(csv, kDriver, ds.name, enc);
      csv.set("N", static_cast<int64_t>(n));
      csv.set("seed", static_cast<int64_t>(seed));
      setPayloadColumns(csv, payloadBytes, context.rawBytes());
      csv.set("raw_bytes", static_cast<int64_t>(rawBytes));
      csv.set("bits_per_elem", bpe);
      csv.set("skipped", int64_t{0});
      csv.set("validated", ledger.enabled() ? int64_t{1} : int64_t{0});
      csv.endRow();
    }
    csv.flush();
  }

  std::cout << "\nResults written to: " << csvPath << "\n";
  return ledger.exitCode();
}

} // namespace
} // namespace facebook::nimble::mlidc

int main(int argc, char** argv) {
  gflags::ParseCommandLineFlags(&argc, &argv, true);
  facebook::velox::memory::MemoryManager::initialize({});
  using namespace facebook::nimble::mlidc;
  return dispatchElemType(
      parseElemDataType(FLAGS_mlidc_dtype),
      [&]<typename T>() { return runBenchmark<T>(); });
}

#else

#include <iostream>
int main() {
  std::cerr
      << "bench_compression requires NIMBLE_ENABLE_EXPERIMENTAL_ENCODINGS\n";
  return 1;
}

#endif
