#!/usr/bin/env python3
"""Extract IPv4 start/end columns from dbip-city-ipv4.csv and write shuffled parquet.

The input CSV is expected to contain columns named "start" and "end" with IPv4
addresses in dotted notation. The script concatenates both columns, validates
using ipaddress, coerces to uint32 then views as int32 (bit-preserving), shuffles,
and writes a single-column parquet file named `ipv4_id`.
"""

from __future__ import annotations

import argparse
import ipaddress
from pathlib import Path

import numpy as np
import pandas as pd


def ipv4_series_to_uint32(values: pd.Series) -> np.ndarray:
	"""Convert dotted IPv4 strings to uint32 using ipaddress validation."""
	coerced = np.empty(values.size, dtype=np.uint32)
	for idx, v in enumerate(values.astype(str).tolist()):
		coerced[idx] = int(ipaddress.IPv4Address(v))
	return coerced

def analyse_ipv4_subint_range(values: pd.Series, start_bit: int, end_bit: int) -> None:
	""""Analyze the distribution of IPv4 sub-intervals defined by bit ranges."""
	# Create a mask for the desired bit range
	mask = (1 << (end_bit - start_bit)) - 1
	mask <<= start_bit

	# Analyze the distribution of the sub-intervals
	# This is a placeholder for the actual analysis logic
	print(f"Analyzing IPv4 sub-intervals: {start_bit}-{end_bit} (mask={mask:#0{10}b})")

	unique_values = set()
	for value in values:
		masked_value = value & mask
		unique_values.add(masked_value)

	print(f"Num unique values in sub-interval: {len(unique_values)}, min dict bits: {len(unique_values).bit_length()}")


def main() -> None:
	parser = argparse.ArgumentParser(description="Extract IPv4 start/end columns and shuffle to parquet")
	parser.add_argument(
		"--csv",
		type=Path,
		required=True,
		help="Path to dbip-city-ipv4.csv",
	)
	parser.add_argument(
		"--out",
		type=Path,
		default=Path(__file__).parent / "dbip_ipv4_shuffled.parquet",
		help="Output parquet path",
	)
	parser.add_argument("--seed", type=int, default=1234, help="Random seed for shuffling")
	parser.add_argument("--chunksize", type=int, default=500_000, help="CSV chunk size")
	args = parser.parse_args()

	if not args.csv.exists():
		raise FileNotFoundError(f"CSV not found: {args.csv}")
	columns = pd.read_csv(args.csv, nrows=0).columns.tolist()
	print(f"Reading CSV in chunks from: {args.csv} (chunksize={args.chunksize}) with columns {columns}")

	rng = np.random.default_rng(args.seed)
	all_values: list[np.ndarray] = []
	with pd.read_csv(args.csv, usecols=[0, 1], chunksize=args.chunksize) as reader:
		for chunk in reader:
			df_chunk = chunk.astype(str)
			start_uint32 = ipv4_series_to_uint32(df_chunk.iloc[:, 0])
			end_uint32 = ipv4_series_to_uint32(df_chunk.iloc[:, 1])
			all_values.append(start_uint32)
			all_values.append(end_uint32)

	if not all_values:
		raise RuntimeError("No IPv4 values were read from the CSV")

	combined = np.concatenate(all_values).astype(np.uint32, copy=False)
	rng.shuffle(combined)
	combined_int32 = combined.view(np.int32)

	args.out.parent.mkdir(parents=True, exist_ok=True)
	output_df = pd.DataFrame({"ipv4_id": combined_int32})
	output_df.to_parquet(args.out, index=False)
	print(f"Wrote shuffled IPv4 parquet: {args.out} (rows={len(output_df)})")
	analyse_ipv4_subint_range(output_df["ipv4_id"], start_bit=0, end_bit=7)  # Example: analyze the first octet (bits 0-7)
	analyse_ipv4_subint_range(output_df["ipv4_id"], start_bit=8, end_bit=15)  # Example: analyze the second octet (bits 8-15)
	analyse_ipv4_subint_range(output_df["ipv4_id"], start_bit=16, end_bit=23)  # Example: analyze the third octet (bits 16-23)
	analyse_ipv4_subint_range(output_df["ipv4_id"], start_bit=24, end_bit=31)  # Example: analyze the fourth octet (bits 24-31)


if __name__ == "__main__":
	main()
