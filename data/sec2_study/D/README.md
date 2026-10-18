# D: encoder-agnostic, SIS-independent structure measure (2026-10-02)

PIDS-style ("a generic compressor shows what's missed") companion to C1/C2. Unlike C
(empirical entropy, hand-rolled estimator), this batch never computes anything itself: it
hands the raw bytes to four off-the-shelf, unmodified byte-stream compressors (xz/LZMA, zstd,
LZ4, Snappy) and reports what *they* achieve on the whole 64-bit column vs. the same column
split into bit-range streams. No SIS, no cost model, no custom encoder anywhere in this script.

Scripts: `scripts/d1_split_measure.py` (measurement -> `csv/split_measure.csv`),
`scripts/d2_table_fig.py` (table + figures from that CSV).
Interpreter: `EncodingsPlayground/Datasets/.venv/bin/python` (python 3.12.3, numpy, pandas).
Compressors: `xz` (XZ Utils) 5.4.5 / liblzma 5.4.5, used both via python's `lzma` module
(`lzma.compress(data, format=FORMAT_XZ, preset=6)`, same system `liblzma.so.5`) -- preset 6
(the library default, no custom filters/dict size); `zstd` CLI 1.5.5 (`zstd -19 -c -q`, invoked
as a subprocess per stream) -- level 19 (not `--ultra`, so max standard level); `lz4` python
package 4.4.5 (wraps liblz4 1.9.4, matches the system `liblz4-1` package), `lz4.frame.compress`
at its default `compression_level` (fast mode, no explicit level set); `python-snappy` 0.7.3
(+ its `cramjam` 2.13.0 dependency, wraps libsnappy; system `libsnappy1v5` 1.1.10), plain
`snappy.compress` (snappy has no level parameter). Neither `lz4` nor `python-snappy` was
present in the project venv (`EncodingsPlayground/Datasets/.venv`) before this batch; both were
installed into that venv with `.venv/bin/python -m pip install lz4 python-snappy`
(2026-10-02, this session) -- not system-wide. Nothing randomised anywhere in this pipeline
(all four compressors deterministic, no sampling) -> one run, no repeated seeds.

Columns: the same 24 as `C/` -- `C/scripts/structure_common.py`'s `ALL_COLUMNS` registry
(`A/scripts/study_common.py`'s 22-column registry + the 2 regenerated controls
`hashed_splitmix64`/`random_uint64`), same files, same leading 524,288-row prefix, same
`field()`/`flip_profile()`/`data_chosen_partition(k=2.0)` helpers (imported unchanged from
`C/scripts/structure_common.py`, so the data-chosen partitions are byte-for-byte identical to
C1's).

## Method

For every column, every compressor (xz, zstd):

- **WHOLE_u64**: all 524,288 values packed little-endian, 8 bytes/value, one stream.
- **WHOLE_narrow**: same, but packed at the narrowest whole-byte width that holds the column's
  observed max value (1-8 bytes/value) -- so a 30-bit column isn't credited for "splitting off"
  34 bits of structural zeros that WHOLE_u64 would otherwise pay for.
- **WHOLE_best** = min(WHOLE_u64, WHOLE_narrow) per column per compressor; this is the
  denominator for every gain% below.
- **SPLIT_DOC**: only where the registry has a documented `layout` (13/24 columns -- the 5 T1 +
  6 T2 + 2 T3 near-miss-float columns; the 3 T4 measure columns and all 8 controls have no
  documented layout and are skipped here, `NaN` in the CSV). Each documented bit range is
  extracted (`field(values, lo, hi)`), re-packed at *its own* narrowest whole-byte width, and
  compressed as its own stream; sizes summed across ranges.
- **SPLIT_DATA**: identical procedure, but ranges come from `data_chosen_partition` on the
  column's own adjacent-row bit-flip-gradient profile (`k=2.0`) -- the same partition C1 uses,
  so results are directly comparable to C1/C2's entropy-based numbers.
- **BYTE_PLANE** (no structure knowledge): the WHOLE_narrow byte layout, transposed -- one
  stream per byte position (SoA), compressed separately, summed.
- **BIT_PLANE** (no structure knowledge): one bit-packed stream per bit position within the
  narrow width, compressed separately, summed.

`bits_per_value = compressed_bytes * 8 / 524288`. `gain_pct_vs_best_whole = (WHOLE_best_bpv -
variant_bpv) / WHOLE_best_bpv * 100` (positive = split variant is smaller/better).

Outputs: `csv/split_measure.csv` (628 rows: column x compressor[4] x variant), the group-level
summary `table_split_measure.tex` (LaTeX booktabs, all 4 compressors), `fig/fig_split_gain.pdf`
(per-column SPLIT_DATA/SPLIT_DOC gain, xz only, structured vs. control), and the supplementary
compact panel `fig/fig_split_gain_compressors.pdf` (group-mean gain, all 4 compressors side by
side).

## Headline numbers (xz, the compressor that most consistently captures whole-column
structure already -- see caveat below)

| group | SPLIT_DOC mean / min-max | SPLIT_DATA mean / min-max | n |
|---|---|---|---|
| structured/near-miss | +4.1% / -1.6% .. +24.1% | -3.9% / -30.6% .. +27.0% | 11 (doc), 24 (data, incl. near-miss) |
| control | n/a (no documented layout) | -12.2% / -57.9% .. -0.0% | 8 |

Under **zstd** the picture shifts (see caveat): SPLIT_DOC structured +2.2% (-4.0%..+26.2%),
SPLIT_DATA structured +6.8% (-6.5%..+51.1%), SPLIT_DATA control **+2.8%** (-6.6%..+44.7%) --
i.e. the control group is *not* uniformly <=0% under zstd; see below.

Columns with a clear, both-compressor-positive split gain: **xmark** (xz +20.9%/+27.0% doc/data,
zstd +26.2%/+51.1%), **uuidv7_hi** (xz +24.1%/+18.3%, zstd comparable), **instagram**, and
**snowflake** (modest, +4%). Most other documented/structured columns show a small-to-large
*negative* xz gain (morton_2x16 -30.6%, publicbi_num_employees -28.3%, quadkey -21.0%): for
these, xz's whole-stream match-finder already captures the redundancy the split would expose,
and the fixed per-stream header/dictionary-reset cost of extra narrow streams outweighs the
narrower per-stream alphabet.

**LZ4 and Snappy** (`table_split_measure.tex`, `fig/fig_split_gain_compressors.pdf`): added per
the author's request, for completeness. As expected, both are **dominated by zstd on WHOLE** for
every single column (zstd <= lz4 and zstd <= snappy on `WHOLE_best` bits/value, 24/24 columns;
xz <= zstd on 21/24) -- confirming the standard LZ4/Snappy-vs-zstd trade-off (faster,
weaker-ratio formats) holds here too, with no exception among these 24 columns. Their
SPLIT_DOC/SPLIT_DATA gain patterns track xz's qualitatively (lz4: structured SPLIT_DOC +1.3%
mean, SPLIT_DATA -1.9%/control -12.1%; snappy: SPLIT_DOC +0.1%, SPLIT_DATA -0.7%/control -6.2%)
-- i.e. both show the same "split rarely helps a generic compressor, and controls are flat-to-
negative" story as xz, just at a worse absolute bits/value. Neither flips the direction of any
headline comparison; they are not used for any conclusion beyond this completeness check.

## Caveats

1. **A generic byte-stream compressor often already captures what a bit-range split would
   expose, especially xz/LZMA at this row count.** This is the main reading of this batch
   under PIDS's own framing: the split helps least where it's needed least. Only columns with
   a strong *field-local* regularity that a byte-oriented match-finder cannot exploit across a
   32+-bit stride (xmark's 1-byte `level` field, uuidv7_hi's version/variant nibble, instagram's
   shard) show a clear, compressor-independent gain.
2. **One control (`tpch_orderkey`) breaks the "controls ~0 or negative" expectation under
   zstd** (SPLIT_DATA +44.7%, BYTE_PLANE +67.0%) while showing the expected negative under xz
   (SPLIT_DATA -57.9%). Cause, confirmed by inspecting `compressed_bytes`: `tpch_orderkey` is a
   monotonically increasing sequential ID -- genuinely structured data, just undocumented as a
   "layout" -- and xz's LZMA already compresses the raw monotone sequence as one stream far
   better than zstd does at level 19 (1.29 vs. 3.77 bits/value on WHOLE_best); splitting off the
   low 3 bits (which cycle with short period under a +1 sequence) recovers most of that gap for
   zstd but gives xz nothing it didn't already have. This is a compressor-capability artifact,
   not evidence that `tpch_orderkey` is "structured" in the SIS/documented-layout sense -- its
   `kind` label (`control`, no documented layout) is unchanged; it is flagged here as a
   reporting caveat, not reclassified.
3. **Per-stream overhead dominates for many narrow ranges.** `BIT_PLANE` (up to 64 separate
   1-bit-packed streams) is the clearest case: it is the *worst* variant for nearly every
   column under both compressors (e.g. `publicbi_npi` xz -135.9%, `inat_species_id` xz -93.4%)
   because each stream pays its own compressor-format fixed overhead (xz: ~60-byte container;
   zstd: ~13-byte frame) against a payload that can be as small as 64KB/8=8 bytes of genuinely
   compressible content. `BYTE_PLANE` (<=8 streams) is far less affected and sometimes wins
   outright (xz `inat_species_id` BYTE_PLANE +... no, -36.2%; but `publicbi_drug_cost` +7.7%,
   `xmark` +71.0%). `SPLIT_DOC`/`SPLIT_DATA` sit between BYTE_PLANE and BIT_PLANE in stream
   count (2-6 typically) and in overhead sensitivity.
4. **`WHOLE_narrow` vs. `WHOLE_u64`**: for every 64-bit-wide column (snowflake, instagram,
   uuidv7_hi/lo, xmark, s2_l16/l30, h3_r9/r15, morton_2x32, random/hashed controls) the two are
   identical by construction (max value needs all 8 bytes); the narrow-width control only
   matters for the already-narrow columns (h3/morton digits, drug-cost cents, measure counts,
   tpch_orderkey, inat_species_id, ipv4_id, publicbi_id1), where it typically wins over
   WHOLE_u64 by a small, mechanical margin (fewer structural zero bytes to compress).
5. **Data-chosen partition reused verbatim from C1**, including its stated limitation
   (`C/README_C1.md`): the `k=2.0` gradient rule occasionally cuts 4-5 spurious ranges on the
   synthetic controls (sampling noise in the flip profile, not real structure); this shows up
   here as those controls still landing at a negative-but-not-zero SPLIT_DATA gain under xz
   (e.g. `hashed_splitmix64` -6.4%, `random_uint64` -6.9%) rather than exactly 0% -- consistent
   with "extra streams cost a little, data-chosen cuts add a few spurious streams on noise."
6. **This batch makes no claim about which split a real encoder would choose or what it would
   cost** -- xz/zstd are generic LZ77+entropy-coder compressors, not Nimble's encodings, and
   their stream/container overhead (dictionary reset, frame headers) differs from any
   production encoding's per-section header. The direction of the comparison (split vs. whole)
   is informative; the absolute bits/value numbers are not comparable to SIS/Nimble figures
   elsewhere in the study.

## Files

- `scripts/d1_split_measure.py` -- measurement (writes `csv/split_measure.csv`).
- `scripts/d2_table_fig.py` -- table (`table_split_measure.tex`) + figures
  (`fig/fig_split_gain.pdf`, `fig/fig_split_gain_compressors.pdf`).
- `csv/split_measure.csv` -- one row per (column, compressor[xz/zstd/lz4/snappy], variant):
  `bits_per_value`, `gain_pct_vs_best_whole`, `n_streams`, `ranges` (the exact bit ranges used).
- `table_split_measure.tex` -- group-level (structured/near-miss vs. control) mean/min/max gain,
  all 4 compressors, both split variants.
- `fig/fig_split_gain.pdf` -- per-column SPLIT_DATA (solid) / SPLIT_DOC (hatched) gain over
  best-WHOLE, xz only, colored structured/near-miss (blue) vs. control (gray), sorted within
  group, linear x-axis including 0, >=8pt labels, single-column width.
- `fig/fig_split_gain_compressors.pdf` -- supplementary compact panel: group-mean SPLIT_DOC
  (structured only, hatched) / SPLIT_DATA (structured, control) gain, one cluster per
  compressor (xz, zstd, lz4, snappy), same coloring/axis conventions.
