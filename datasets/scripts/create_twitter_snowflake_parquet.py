#!/usr/bin/env python3
"""
Dataset citation
@inproceedings{tacchi2023cultural,
  title={Cultural Differences in Signed Ego Networks on Twitter: An Investigatory Analysis},
  author={Tacchi, Jack and Boldrini, Chiara and Passarella, Andrea and Conti, Marco},
  booktitle={Companion Proceedings of the ACM Web Conference 2023},
  pages={1039--1049},
  year={2023}
}
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
	parser = argparse.ArgumentParser(description="Extract IPv4 start/end columns and shuffle to parquet")
	parser.add_argument(
		"--csv",
		type=Path,
		required=True,
		help="Path to twitter ids tsv with column 'tweet_id'",
	)
	parser.add_argument(
		"--out",
		type=Path,
		default=Path(__file__).parent / "tweet_ids.parquet",
		help="Output parquet path",
	)
	parser.add_argument("--chunksize", type=int, default=500_000, help="CSV chunk size")
	args = parser.parse_args()

	if not args.csv.exists():
		raise FileNotFoundError(f"CSV not found: {args.csv}")
	columns = pd.read_csv(args.csv, nrows=0).columns.tolist()
	print(f"Reading CSV in chunks from: {args.csv} (chunksize={args.chunksize}) with columns {columns}")

	all_values: list[np.ndarray] = []
	with pd.read_csv(args.csv, usecols=[0], chunksize=args.chunksize) as reader:
		for chunk in reader:
			values = chunk.iloc[:, 0].values.astype(np.uint64)
			all_values.append(values)

	if not all_values:
		raise RuntimeError("No tweet IDs were read from the CSV")

	combined = np.concatenate(all_values).astype(np.uint64, copy=False)
	combined_int64 = combined.view(np.int64)

	args.out.parent.mkdir(parents=True, exist_ok=True)
	output_df = pd.DataFrame({"tweet_id": combined_int64})
	output_df.to_parquet(args.out, index=False)
	print(f"Wrote tweet IDs parquet: {args.out} (rows={len(output_df)})")


if __name__ == "__main__":
	main()
