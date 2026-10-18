#!/usr/bin/env python3
"""Convert the OSM spatial ID parquet columns to the text format nimble reads.

Emits one value per line, the format accepted by both
velox/dwio/nimble/tools/encoding_bench --file and the ml_id_compression
benchmark drivers' --mlidc_file. The nimble build used for these benchmarks is
configured with VELOX_ENABLE_PARQUET=OFF, so a text dump is the only way to get
a real column into the drivers.

Unlike sis_snowflake_results/snowflake_to_csv.py, which writes signed decimal,
this writes **unsigned** decimal. S2 leaf cell IDs and 2x32 Morton codes exceed
2**63, and generate_osm_spatial_ids.py stores them bit-preservingly as int64 via
.view(np.int64), so they appear negative in the parquet. Writing them back as
unsigned decimal means the drivers must be run with --mlidc_dtype=uint64, and
std::stoull then reconstructs identical bits.

One file per (column, ordering) pair is written to the output directory, named
{column}_{ordering}.txt. At 10M rows the twelve files total roughly 2.4 GB, and
they are disposable once the sweep has run.

Requires pyarrow, available in EncodingsPlayground/Datasets/.venv.

	../.venv/bin/python spatial_ids_to_txt.py --rows 10000000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

COLUMNS = ("s2_l30", "s2_l16", "h3_r15", "h3_r9", "morton_2x32", "morton_2x16")
ORDERINGS = ("fileorder", "sorted")


def convert_column(parquet_path: Path, column: str, rows: int, out_path: Path) -> int:
	"""Stream one parquet column out as unsigned decimal, one value per line."""
	parquet_file = pq.ParquetFile(parquet_path)
	total = parquet_file.metadata.num_rows
	if total < rows:
		# Fail here rather than silently benchmarking a shorter column.
		print(f"Requested {rows} rows but {parquet_path.name} holds only {total}", file=sys.stderr)
		return 0

	written = 0
	# Stream in batches so a multi-hundred-MB column is never fully materialised.
	with out_path.open("w") as handle:
		for batch in parquet_file.iter_batches(batch_size=1 << 20, columns=[column]):
			remaining = rows - written
			if remaining <= 0:
				break
			values = batch.column(0).to_numpy(zero_copy_only=False)
			if len(values) > remaining:
				values = values[:remaining]
			unsigned = values.astype(np.int64, copy=False).view(np.uint64)
			handle.write("\n".join(map(str, unsigned.tolist())))
			handle.write("\n")
			written += len(values)
	return written


def main() -> int:
	parser = argparse.ArgumentParser(description="Dump OSM spatial ID parquet columns to nimble's text format")
	parser.add_argument("--parquet-dir", type=Path, default=Path(__file__).parent, help="Directory holding the parquet files")
	parser.add_argument("--outdir", type=Path, default=Path(__file__).parent / "csv", help="Directory for the .txt dumps")
	parser.add_argument("--rows", type=int, default=10_000_000, help="Rows to write per column")
	parser.add_argument("--columns", nargs="*", default=list(COLUMNS), help="Columns to dump")
	parser.add_argument("--orderings", nargs="*", default=list(ORDERINGS), help="Orderings to dump")
	args = parser.parse_args()

	args.outdir.mkdir(parents=True, exist_ok=True)
	failures = 0

	for ordering in args.orderings:
		parquet_path = args.parquet_dir / f"osm_gb_spatial_ids_{ordering}.parquet"
		if not parquet_path.is_file():
			print(f"Parquet not found: {parquet_path}", file=sys.stderr)
			failures += 1
			continue
		for column in args.columns:
			out_path = args.outdir / f"{column}_{ordering}.txt"
			written = convert_column(parquet_path, column, args.rows, out_path)
			if written != args.rows:
				print(f"Wrote {written} rows for {column}/{ordering}, expected {args.rows}", file=sys.stderr)
				failures += 1
				continue
			size_mb = out_path.stat().st_size / (1 << 20)
			print(f"Wrote {written:,} values to {out_path} ({size_mb:.1f} MB)")

	return 1 if failures else 0


if __name__ == "__main__":
	raise SystemExit(main())
