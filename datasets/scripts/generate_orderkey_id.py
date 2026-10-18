import argparse
import duckdb


def main():
	parser = argparse.ArgumentParser(description="Generate TPCH lineitem orderkey parquet (int32) without loading into Python memory")
	parser.add_argument("--sf", type=int, default=10, help="Scale factor for TPCH dbgen (default: 10)")
	parser.add_argument("--out", type=str, default="lineitem_orderkey_int32.parquet", help="Output parquet file path")
	parser.add_argument("--compress", type=str, default=None, help="Parquet compression codec (e.g., 'SNAPPY', 'ZSTD'). If omitted, DuckDB default is used")
	args = parser.parse_args()

	# Connect to an in-memory DuckDB instance and prepare TPCH data
	con = duckdb.connect(database=':memory:')
	con.execute("INSTALL tpch; LOAD tpch")
	con.execute(f"CALL dbgen(sf={args.sf})")

	# Show tables for confirmation (small message)
	print("Tables:", con.execute("show tables").fetchall())

	# Use DuckDB's COPY command to write the orderkey column directly to Parquet
	# Cast to INTEGER so the parquet column is a 32-bit int and avoid pulling data into Python.
	# Use a subquery with a different alias to avoid Binder alias resolution edge cases.
	copy_sql = (
		f"COPY ("
		f"SELECT orderkey_int AS orderkey FROM ("
		f"SELECT CAST(l.l_orderkey AS INTEGER) AS orderkey_int FROM lineitem l"
		f") t"
		f") TO '{args.out}' (FORMAT PARQUET)"
	)
	if args.compress:
		# DuckDB allows setting compression via the COPY options
		copy_sql = copy_sql[:-1] + f", COMPRESSION '{args.compress}')"

	print(f"Exporting orderkey (int32) to {args.out} using DuckDB COPY...")
	con.execute(copy_sql)
	print(f"Export complete: {args.out}")


if __name__ == '__main__':
	main()
