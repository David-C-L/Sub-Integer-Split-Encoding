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
#pragma once

#ifdef NIMBLE_ENABLE_EXPERIMENTAL_ENCODINGS

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <memory>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

#include <gflags/gflags.h>

#include "velox/dwio/nimble/common/Exceptions.h"
#include "velox/dwio/nimble/common/Types.h"
#include "velox/dwio/nimble/compression/Compression.h"
#include "velox/dwio/nimble/encodings/benchmarks/ml_id_compression/OpenZLBenchTarget.h"
#include "velox/dwio/nimble/encodings/benchmarks/ml_id_compression/SubstreamCompression.h"
#include "velox/dwio/nimble/encodings/subintsplit/SplitSelector.h"

DECLARE_string(mlidc_sis_openzl_extrapolate);
DECLARE_int64(mlidc_sis_openzl_extrapolate_n1);

/// OpenZL-aware split selection (evaluation only).
///
/// Builds a SelectorConfig::sectionSizePricer that prices a candidate section
/// by the bytes OpenZL compresses its sampled values to, stored as SubIntSplit
/// stores a section: right-aligned, narrowed to the smallest of 8, 16, 32 and
/// 64 bits that holds the section. Two OpenZL setups are offered:
///
///   nimble          Nimble's OpenZLCompressor, through Compression::compress
///                   with the policy --mlidc_substream_compression=OpenZL
///                   hands every sub-stream. This is the compressor a Trivial
///                   section's stream is given at encode time, so the price
///                   and the stored bytes use the same graph.
///   select_numeric  openzlCompressNumeric (OpenZL's select_numeric graph),
///                   the graph of the openzl/auto arm.
///
/// A compressed frame carries a fixed header the sample pays once and the
/// full stream pays once too, so scaling the sample's whole frame by
/// rows/sample would charge that header thousands of times. With
/// amortiseHeader the pricer charges the sample's bytes above a one-value
/// frame's at the sample rate and the one-value frame itself once per stream.
namespace facebook::nimble::mlidc {

enum class OpenZLPricerGraph { kNimble, kSelectNumeric };

/// Calls and wall time the pricer spent, for the drivers to report.
struct SectionPricerStats {
  std::atomic<uint64_t> calls{0};
  std::atomic<uint64_t> nanos{0};

  void reset() {
    calls = 0;
    nanos = 0;
  }
};

inline SectionPricerStats& sectionPricerStats() {
  static SectionPricerStats stats;
  return stats;
}

/// Storage bytes per value SubIntSplit gives a section of `bitWidth` bits.
inline int pricerStorageBytes(int bitWidth) {
  return bitWidth <= 8 ? 1 : bitWidth <= 16 ? 2 : bitWidth <= 32 ? 4 : 8;
}

inline velox::memory::MemoryPool& pricerPool() {
  static std::shared_ptr<velox::memory::MemoryPool> root =
      velox::memory::memoryManager()->addRootPool("mlidc_openzl_pricer");
  static std::shared_ptr<velox::memory::MemoryPool> leaf =
      root->addLeafChild("mlidc_openzl_pricer");
  return *leaf;
}

/// OpenZL-compressed bytes of `count` narrowed values under `graph`.
template <typename U>
size_t openzlCompressedBytes(
    OpenZLPricerGraph graph,
    const U* data,
    size_t count,
    std::optional<bool> selectNumeric = std::nullopt) {
  if (graph == OpenZLPricerGraph::kSelectNumeric) {
    std::string out;
    return openzlCompressNumeric<U>(data, count, out);
  }
  BenchCompressPolicy policy{CompressionType::OpenZL, selectNumeric};
  auto result = Compression::compress(
      pricerPool(),
      std::string_view(
          reinterpret_cast<const char*>(data), count * sizeof(U)),
      TypeTraits<U>::dataType,
      /*bitWidth=*/0,
      policy);
  NIMBLE_CHECK(
      result.compressionType == CompressionType::OpenZL &&
          result.buffer.has_value(),
      "OpenZL section pricer: compressor declined the section.");
  return result.buffer->size();
}

/// Narrows `values` to U and compresses them.
template <typename U>
size_t narrowedCompressedBytes(
    OpenZLPricerGraph graph,
    std::span<const uint64_t> values,
    std::optional<bool> selectNumeric) {
  std::vector<U> narrowed(values.size());
  for (size_t i = 0; i < values.size(); ++i) {
    narrowed[i] = static_cast<U>(values[i]);
  }
  return openzlCompressedBytes<U>(
      graph, narrowed.data(), narrowed.size(), selectNumeric);
}

inline size_t sectionCompressedBytes(
    OpenZLPricerGraph graph,
    std::span<const uint64_t> values,
    int bitWidth,
    std::optional<bool> selectNumeric = std::nullopt) {
  switch (pricerStorageBytes(bitWidth)) {
    case 1:
      return narrowedCompressedBytes<uint8_t>(graph, values, selectNumeric);
    case 2:
      return narrowedCompressedBytes<uint16_t>(graph, values, selectNumeric);
    case 4:
      return narrowedCompressedBytes<uint32_t>(graph, values, selectNumeric);
    default:
      return narrowedCompressedBytes<uint64_t>(graph, values, selectNumeric);
  }
}

/// --mlidc_sis_openzl_pricing=best_of: prices each section as the cheaper of
/// the nimble pricer above (raw) and the section encoded by section selection
/// with its streams compressed by the same OpenZL compressor (encoded).
inline constexpr std::string_view kOpenZLBestOf{"best_of"};

/// Parses --mlidc_sis_openzl_pricing. Empty, "off" and "best_of" (installed
/// by installOpenZLBestOfPricer instead) give nullopt.
inline std::optional<OpenZLPricerGraph> parseOpenZLPricerGraph(
    const std::string& name) {
  if (name.empty() || name == "off" || name == kOpenZLBestOf) {
    return std::nullopt;
  }
  if (name == "nimble") {
    return OpenZLPricerGraph::kNimble;
  }
  NIMBLE_CHECK(
      name == "select_numeric",
      "--mlidc_sis_openzl_pricing must be off, nimble, select_numeric or "
      "best_of: {}",
      name);
  return OpenZLPricerGraph::kSelectNumeric;
}

/// --mlidc_sis_openzl_extrapolate: how a section's OpenZL size is carried
/// from the sample to the stream. kOff scales the sample's bytes by
/// rows / sample (with the header handling of each pricer), the default.
/// kLinear and kPower size the section at two nested samples, the planner
/// sample (n2 rows) and every k-th of its blocks (n1 rows, k = n2 / n1,
/// which is the sampler's own n1-row sample up to rounding), and fit
///   kLinear  size(n) = a + b * n through both points, and
///   kPower   size(n) = c * n^alpha, alpha clamped to (0, 1],
/// then predict the size at the stream's row count N.
enum class SampleExtrapolation { kOff, kLinear, kPower };

struct ExtrapolationConfig {
  SampleExtrapolation mode{SampleExtrapolation::kOff};
  /// Rows of the smaller sample (--mlidc_sis_openzl_extrapolate_n1).
  size_t smallRows{2048};
  /// The sampler's block size, so the smaller sample takes whole blocks.
  size_t blockSize{128};

  bool active() const {
    return mode != SampleExtrapolation::kOff;
  }
};

inline SampleExtrapolation parseSampleExtrapolation(const std::string& name) {
  if (name.empty() || name == "off") {
    return SampleExtrapolation::kOff;
  }
  if (name == "linear") {
    return SampleExtrapolation::kLinear;
  }
  NIMBLE_CHECK(
      name == "power",
      "--mlidc_sis_openzl_extrapolate must be off, linear or power: {}",
      name);
  return SampleExtrapolation::kPower;
}

/// Every k-th block of `values`, k = round(values.size() / smallRows). Empty
/// when k < 2, i.e. when the planner sample is not at least twice n1.
inline std::vector<uint64_t> nestedSubsample(
    std::span<const uint64_t> values,
    const ExtrapolationConfig& cfg) {
  std::vector<uint64_t> out;
  const size_t k = cfg.smallRows == 0
      ? 0
      : (values.size() + cfg.smallRows / 2) / cfg.smallRows;
  const size_t block = std::max<size_t>(cfg.blockSize, 1);
  if (k < 2) {
    return out;
  }
  for (size_t start = 0, index = 0; start < values.size();
       start += block, ++index) {
    if (index % k == 0) {
      const size_t end = std::min(start + block, values.size());
      out.insert(out.end(), values.begin() + start, values.begin() + end);
    }
  }
  return out;
}

/// Predicted bytes at `streamRows` from `bytes1` at `rows1` and `bytes2` at
/// `rows2` (rows1 < rows2). Never below bytes2: a stream holding the sample
/// is not smaller than it.
inline double extrapolatedBytes(
    SampleExtrapolation mode,
    double rows1,
    double bytes1,
    double rows2,
    double bytes2,
    double streamRows) {
  double predicted = bytes2 * streamRows / rows2;
  if (mode == SampleExtrapolation::kLinear) {
    const double slope = std::max((bytes2 - bytes1) / (rows2 - rows1), 0.0);
    predicted = bytes2 + slope * (streamRows - rows2);
  } else if (mode == SampleExtrapolation::kPower) {
    double alpha = (bytes1 > 0.0 && bytes2 > 0.0)
        ? std::log(bytes2 / bytes1) / std::log(rows2 / rows1)
        : 1.0;
    alpha = std::clamp(alpha, 1e-3, 1.0);
    predicted = bytes2 * std::pow(streamRows / rows2, alpha);
  }
  return std::max(predicted, bytes2);
}

/// The price in sample bits for `bytesAt(sample)` extrapolated to the stream:
/// the grid scales a price by streamRows / sampleRows, so the prediction is
/// scaled down by the same factor. Falls back to plain scaling (bytes2) when
/// no nested subsample exists.
template <typename BytesAt>
double extrapolatedSampleBits(
    const ExtrapolationConfig& cfg,
    std::span<const uint64_t> values,
    size_t fullCount,
    double bytes2,
    BytesAt&& bytesAt) {
  const double rows2 = static_cast<double>(values.size());
  const double streamRows =
      static_cast<double>(std::max<size_t>(fullCount, values.size()));
  const auto small = nestedSubsample(values, cfg);
  if (small.empty()) {
    return 8.0 * bytes2;
  }
  const double bytes1 = bytesAt(
      std::span<const uint64_t>(small.data(), small.size()));
  const double predicted = extrapolatedBytes(
      cfg.mode,
      static_cast<double>(small.size()),
      bytes1,
      rows2,
      bytes2,
      streamRows);
  return 8.0 * predicted * rows2 / streamRows;
}

/// The extrapolation the flags ask for, on a sampler of `blockSize`.
inline ExtrapolationConfig extrapolationFromFlags(size_t blockSize) {
  return {
      .mode = parseSampleExtrapolation(FLAGS_mlidc_sis_openzl_extrapolate),
      .smallRows = static_cast<size_t>(
          std::max<int64_t>(FLAGS_mlidc_sis_openzl_extrapolate_n1, 0)),
      .blockSize = blockSize};
}

/// Cache-key and log suffix for an active extrapolation.
inline std::string extrapolationSuffix(const ExtrapolationConfig& cfg) {
  if (!cfg.active()) {
    return {};
  }
  return std::string(
             cfg.mode == SampleExtrapolation::kLinear ? "_xlinear" : "_xpower") +
      "_n1_" + std::to_string(cfg.smallRows);
}

/// Installs the OpenZL pricer on `cfg`. See the file comment. With
/// `extrapolation` active the header amortisation is not applied: the fit's
/// fixed part takes its place.
inline void installOpenZLSectionPricer(
    subintsplit::SelectorConfig& cfg,
    OpenZLPricerGraph graph,
    bool amortiseHeader,
    const ExtrapolationConfig& extrapolation = {},
    std::optional<bool> selectNumeric = std::nullopt) {
  // `selectNumeric` (kNimble only) fixes the OpenZL graph of Nimble's
  // compressor for this pricer instead of --mlidc_substream_openzl_graph.
  // A one-value frame per storage width: the header part of any frame.
  std::array<double, 4> headerBytes{};
  if (amortiseHeader) {
    const std::array<uint64_t, 1> zero{0};
    const std::array<int, 4> widths{8, 16, 32, 64};
    for (size_t i = 0; i < widths.size(); ++i) {
      headerBytes[i] = static_cast<double>(
          sectionCompressedBytes(graph, zero, widths[i], selectNumeric));
    }
  }
  cfg.sectionSizePricer = [graph, headerBytes, extrapolation, selectNumeric](
                              std::span<const uint64_t> values,
                              int bitWidth,
                              size_t fullCount) -> double {
    const auto start = std::chrono::steady_clock::now();
    const double bytes = static_cast<double>(
        sectionCompressedBytes(graph, values, bitWidth, selectNumeric));
    if (extrapolation.active()) {
      const double bits = extrapolatedSampleBits(
          extrapolation,
          values,
          fullCount,
          bytes,
          [graph, bitWidth, selectNumeric](std::span<const uint64_t> small) {
            return static_cast<double>(
                sectionCompressedBytes(graph, small, bitWidth, selectNumeric));
          });
      auto& stats = sectionPricerStats();
      stats.calls.fetch_add(1, std::memory_order_relaxed);
      stats.nanos.fetch_add(
          static_cast<uint64_t>(
              std::chrono::duration_cast<std::chrono::nanoseconds>(
                  std::chrono::steady_clock::now() - start)
                  .count()),
          std::memory_order_relaxed);
      return bits;
    }
    const int storage = pricerStorageBytes(bitWidth);
    const double header =
        headerBytes[storage == 1 ? 0 : storage == 2 ? 1 : storage == 4 ? 2 : 3];
    const double sampleRows = static_cast<double>(values.size());
    const double streamRows =
        static_cast<double>(std::max<size_t>(fullCount, values.size()));
    // Scaled by streamRows / sampleRows afterwards, so the header term is
    // charged once per stream.
    const double bits = 8.0 *
        (std::max(bytes - header, 0.0) + header * sampleRows / streamRows);
    auto& stats = sectionPricerStats();
    stats.calls.fetch_add(1, std::memory_order_relaxed);
    stats.nanos.fetch_add(
        static_cast<uint64_t>(
            std::chrono::duration_cast<std::chrono::nanoseconds>(
                std::chrono::steady_clock::now() - start)
                .count()),
        std::memory_order_relaxed);
    return bits;
  };
  cfg.sectionSizePricerName = std::string(
                                  graph == OpenZLPricerGraph::kNimble
                                      ? "openzl_nimble"
                                      : "openzl_select_numeric") +
      (amortiseHeader ? "" : "_noamort") + extrapolationSuffix(extrapolation) +
      (selectNumeric.has_value() ? (*selectNumeric ? "_gsn" : "_gng") : "");
}

/// What a section's sampled values encode to under section selection, with
/// every stream compressed by Nimble's OpenZL compressor: the bytes and the
/// encoding selection picked for the section itself.
struct EncodedSectionBytes {
  size_t bytes{0};
  EncodingType encoding{EncodingType::Trivial};
};

/// Narrows `values` to U, as SubIntSplit stores a section, and encodes them
/// exactly as the realNested write path encodes a section: the nested policy
/// BenchEncodingSelectionPolicy hands a SubIntSplit section (realNested
/// selection, OpenZL on every stream, --mlidc_sis_allowed_encodings and
/// --mlidc_sis_withdraw_nested_encodings honoured), the section options the
/// encoder passes, and EncodingFactory::encode, as encodeNested does.
template <typename U>
EncodedSectionBytes encodedSectionBytes(
    std::span<const uint64_t> values,
    const Encoding::Options& sectionOptions) {
  std::vector<U> narrowed(values.size());
  for (size_t i = 0; i < values.size(); ++i) {
    narrowed[i] = static_cast<U>(values[i]);
  }
  const std::span<const U> data(narrowed.data(), narrowed.size());
  BenchEncodingSelectionPolicy<uint64_t> parent{
      CompressionType::OpenZL, /*realNestedSelection=*/true};
  auto policy = std::unique_ptr<EncodingSelectionPolicy<U>>(
      static_cast<EncodingSelectionPolicy<U>*>(
          parent
              .template create<U>(
                  EncodingType::SubIntSplit, NestedEncodingIdentifier{0})
              .release()));
  // Selects and encodes as EncodingSelection::encodeNested does.
  Buffer buffer{pricerPool()};
  const auto encoded = EncodingFactory::encode<U>(
      std::move(policy), data, buffer, sectionOptions);
  return {encoded.size(), EncodingPrefix::encodingType(encoded)};
}

inline EncodedSectionBytes encodedSectionBytesAt(
    std::span<const uint64_t> values,
    int bitWidth,
    const Encoding::Options& sectionOptions) {
  switch (pricerStorageBytes(bitWidth)) {
    case 1:
      return encodedSectionBytes<uint8_t>(values, sectionOptions);
    case 2:
      return encodedSectionBytes<uint16_t>(values, sectionOptions);
    case 4:
      return encodedSectionBytes<uint32_t>(values, sectionOptions);
    default:
      return encodedSectionBytes<uint64_t>(values, sectionOptions);
  }
}

/// How the encoded option's fixed bytes (encoding headers, one OpenZL frame
/// per stream, a dictionary that has stopped growing) are told apart from
/// the bytes that grow with the rows.
enum class EncodedHeaderModel {
  /// No fixed part: the sample's whole encoding (all its streams, compressed)
  /// is scaled to the stream, as every closed-form price is. The default.
  kScale,
  /// Encoded at the whole sample and at its first half: a + b * rows through
  /// both points, a (clamped to [0, min of the two]) charged once per stream
  /// and the rest scaled. A variant: an encoding whose sample bytes grow
  /// sublinearly (a dictionary, runs, deltas that repeat within the sample's
  /// blocks) gets a large a and is badly underpriced at full length.
  kAffine,
};

inline EncodedHeaderModel parseEncodedHeaderModel(const std::string& name) {
  if (name == "affine") {
    return EncodedHeaderModel::kAffine;
  }
  NIMBLE_CHECK(
      name == "scale",
      "--mlidc_sis_openzl_best_of_encoded_header must be scale or affine: {}",
      name);
  return EncodedHeaderModel::kScale;
}

/// Installs the best-of pricer on `cfg` (--mlidc_sis_openzl_pricing=best_of):
/// each candidate section is priced as the cheaper of
///   raw      the nimble pricer above, exactly as installOpenZLSectionPricer
///            builds it (Arm B's price), and
///   encoded  encodedSectionBytesAt on the same sample values, its fixed
///            bytes separated from the per-row ones by `headerModel`,
/// and the plan records which won (SectionPlan::storeRaw), so the encoder
/// stores raw-priced sections Trivial and selects the rest as usual.
/// `options` and `tuning` give the section options the encoder passes
/// (sectionEncodingOptions); `amortiseHeader` is the raw pricer's.
inline void installOpenZLBestOfPricer(
    subintsplit::SelectorConfig& cfg,
    const Encoding::Options& options,
    const subintsplit::TuningConfig& tuning,
    bool amortiseHeader,
    EncodedHeaderModel headerModel,
    const ExtrapolationConfig& extrapolation = {},
    bool rawBothGraphs = false) {
  // rawBothGraphs (--mlidc_sis_openzl_best_of_raw_graphs=both): the raw
  // option is priced under Nimble's OpenZL graph and under select_numeric,
  // each through Nimble's compressor, and the cheaper is kept with its graph
  // (SectionChoice::rawGraph), which the encoder then stores it with.
  subintsplit::SelectorConfig rawConfig;
  installOpenZLSectionPricer(
      rawConfig,
      OpenZLPricerGraph::kNimble,
      amortiseHeader,
      extrapolation,
      rawBothGraphs ? std::optional<bool>(false) : std::nullopt);
  auto rawNimble = std::move(rawConfig.sectionSizePricer);
  std::function<double(std::span<const uint64_t>, int, size_t)> rawSelect;
  if (rawBothGraphs) {
    subintsplit::SelectorConfig selectConfig;
    installOpenZLSectionPricer(
        selectConfig,
        OpenZLPricerGraph::kNimble,
        amortiseHeader,
        extrapolation,
        std::optional<bool>(true));
    rawSelect = std::move(selectConfig.sectionSizePricer);
  }
  const Encoding::Options sectionOptions =
      subintsplit::sectionEncodingOptions(options, tuning);
  cfg.sectionSizePricer = {};
  cfg.sectionChoicePricer = [rawNimble = std::move(rawNimble),
                             rawSelect = std::move(rawSelect),
                             sectionOptions,
                             headerModel,
                             extrapolation](
                                std::span<const uint64_t> values,
                                int bitWidth,
                                size_t fullCount)
      -> subintsplit::SectionChoice {
    // Counts this cell's call and times the raw price itself.
    double rawBits = rawNimble(values, bitWidth, fullCount);
    int8_t rawGraph = -1;
    if (rawSelect) {
      // Ties go to Nimble's graph.
      const double selectBits = rawSelect(values, bitWidth, fullCount);
      rawGraph = 0;
      if (selectBits < rawBits) {
        rawBits = selectBits;
        rawGraph = 1;
      }
    }
    const auto start = std::chrono::steady_clock::now();
    const auto whole = encodedSectionBytesAt(values, bitWidth, sectionOptions);
    const double wholeBytes = static_cast<double>(whole.bytes);
    if (extrapolation.active()) {
      // Both options extrapolated alike; the header model does not apply.
      const double encodedBits = extrapolatedSampleBits(
          extrapolation,
          values,
          fullCount,
          wholeBytes,
          [&sectionOptions, bitWidth](std::span<const uint64_t> small) {
            return static_cast<double>(
                encodedSectionBytesAt(small, bitWidth, sectionOptions).bytes);
          });
      sectionPricerStats().nanos.fetch_add(
          static_cast<uint64_t>(
              std::chrono::duration_cast<std::chrono::nanoseconds>(
                  std::chrono::steady_clock::now() - start)
                  .count()),
          std::memory_order_relaxed);
      if (rawBits <= encodedBits) {
        return {
            .sizeBits = rawBits,
            .encoding = EncodingType::Trivial,
            .storeRaw = true,
            .rawGraph = rawGraph};
      }
      return {
          .sizeBits = encodedBits,
          .encoding = whole.encoding,
          .storeRaw = false};
    }
    double fixedBytes = 0.0;
    if (headerModel == EncodedHeaderModel::kAffine && values.size() >= 2) {
      const double halfBytes = static_cast<double>(
          encodedSectionBytesAt(
              values.first(values.size() / 2), bitWidth, sectionOptions)
              .bytes);
      fixedBytes = std::clamp(
          2.0 * halfBytes - wholeBytes,
          0.0,
          std::min(halfBytes, wholeBytes));
    }
    const double sampleRows = static_cast<double>(values.size());
    const double streamRows =
        static_cast<double>(std::max<size_t>(fullCount, values.size()));
    // Scaled by streamRows / sampleRows afterwards, so the fixed part is
    // charged once per stream.
    const double encodedBits = 8.0 *
        ((wholeBytes - fixedBytes) + fixedBytes * sampleRows / streamRows);
    sectionPricerStats().nanos.fetch_add(
        static_cast<uint64_t>(
            std::chrono::duration_cast<std::chrono::nanoseconds>(
                std::chrono::steady_clock::now() - start)
                .count()),
        std::memory_order_relaxed);
    if (rawBits <= encodedBits) {
      return {
          .sizeBits = rawBits,
          .encoding = EncodingType::Trivial,
          .storeRaw = true,
          .rawGraph = rawGraph};
    }
    return {
        .sizeBits = encodedBits, .encoding = whole.encoding, .storeRaw = false};
  };
  cfg.sectionSizePricerName = std::string("openzl_best_of") +
      (amortiseHeader ? "" : "_noamort") +
      (headerModel == EncodedHeaderModel::kAffine && !extrapolation.active()
           ? "_encaffine"
           : "") +
      extrapolationSuffix(extrapolation) + (rawBothGraphs ? "_rawboth" : "");
}

/// Parses --mlidc_sis_openzl_best_of_raw_graphs: true for both.
inline bool parseBestOfRawBothGraphs(const std::string& name) {
  NIMBLE_CHECK(
      name == "nimble" || name == "both",
      "--mlidc_sis_openzl_best_of_raw_graphs must be nimble or both: {}",
      name);
  return name == "both";
}

/// Prints each plan the encoder is about to write, one line per plan:
/// "[sis-plan] frame=<0|1> <start>-<end>:raw|enc(<sample pick>)~<bytes>;...".
/// enc(...) names the encoding selection picked on the planner sample; the
/// encoding written is the full column's own selection (see the dump).
/// ~<bytes> is the planner's estimate of the section's full-stream bytes
/// (SectionPlan::sizeCostBits / 8); 0 for a replayed plan.
inline void installPlanPrinter(subintsplit::SelectorConfig& cfg) {
  cfg.planObserver = [](std::span<const subintsplit::SectionPlan> plan,
                        bool rowFrame) {
    std::string line;
    for (const auto& section : plan) {
      line += (line.empty() ? "" : ";") + std::to_string(section.bitStart) +
          "-" + std::to_string(section.bitEnd) + ":" +
          (section.storeRaw
               ? std::string("raw") +
                   (section.rawGraph < 0
                        ? ""
                        : (section.rawGraph == 1 ? "(sn)" : "(ng)"))
               : "enc(" + std::string(nimble::toString(section.encoding)) +
                   ")") +
          "~" +
          std::to_string(
              static_cast<uint64_t>(std::llround(section.sizeCostBits / 8.0)));
    }
    std::cout << "  [sis-plan] frame=" << (rowFrame ? 1 : 0) << " " << line
              << "\n";
  };
}

} // namespace facebook::nimble::mlidc

#endif // NIMBLE_ENABLE_EXPERIMENTAL_ENCODINGS
