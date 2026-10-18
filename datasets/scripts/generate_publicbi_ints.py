"""Extract int/float columns from the raw PublicBI Corporations and Medicare1
CSVs into one-value-per-line .txt files for the nimble ml_id_compression
benchmark drivers (--mlidc_file).

Usage:
    .venv/bin/python generate_publicbi_ints.py
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))

MEDICARE1_ROW_CAP = 2_000_000

# Column name -> "int" or "float". Order matches the CSV's column order.
# Corporations schema has 25 named columns; the raw CSV has 27 (2 trailing
# varchar columns were dropped from the DDL before it was given to us) -- we
# only read the first 25 positional columns.
CORPORATIONS_SCHEMA = [
    ("Id1", "int"),
    ("Number of Records", "int"),
    ("angelco_account", "str"),
    ("business_model", "str"),
    ("city", "str"),
    ("continent", "str"),
    ("country", "str"),
    ("crunchbase_account", "str"),
    ("upstream_account", "str"),
    ("financing_stage", "str"),
    ("founding_date", "str"),
    ("id", "int"),
    ("industries", "str"),
    ("keywords", "str"),
    ("last_funding_date", "str"),
    ("linkedin_account", "str"),
    ("location", "str"),
    ("long_description", "str"),
    ("name", "str"),
    ("num_employees", "int"),
    ("region", "str"),
    ("score", "int"),
    ("short_descriptiion", "str"),
    ("stage", "str"),
    ("total_funding", "int"),
]

MEDICARE1_SCHEMA = [
    ("BENE_COUNT", "int"),
    ("BENE_COUNT_GE65", "int"),
    ("BENE_COUNT_GE65_REDACT_FLAG", "str"),
    ("Calculation_3170826185336909", "float"),
    ("Calculation_3170826185505725", "float"),
    ("Calculation_7130826185400024", "float"),
    ("Calculation_9030826185528129", "float"),
    ("DESCRIPTION_FLAG", "str"),
    ("DRUG_NAME", "str"),
    ("GE65_REDACT_FLAG", "str"),
    ("GENERIC_NAME", "str"),
    ("NPI", "int"),
    ("NPPES_PROVIDER_CITY", "str"),
    ("NPPES_PROVIDER_FIRST_NAME", "str"),
    ("NPPES_PROVIDER_LAST_ORG_NAME", "str"),
    ("NPPES_PROVIDER_STATE", "str"),
    ("Number of Records", "int"),
    ("SPECIALTY_DESC", "str"),
    ("TOTAL_CLAIM_COUNT", "int"),
    ("TOTAL_CLAIM_COUNT_GE65", "int"),
    ("TOTAL_DAY_SUPPLY", "int"),
    ("TOTAL_DAY_SUPPLY_GE65", "int"),
    ("TOTAL_DRUG_COST", "float"),
    ("TOTAL_DRUG_COST_GE65", "float"),
    ("Calculation_6710826185428006", "int"),
    ("Avg Day Supply/Bene (bin)", "int"),
]


def write_column(values: pd.Series, out_path: str, kind: str) -> int:
    # Some PublicBI rows contain literal unescaped delimiter characters inside
    # string fields, which misaligns columns for a small number of rows. Coerce
    # to numeric and drop unparseable values (treated like nulls) rather than
    # crashing on the whole column.
    numeric = pd.to_numeric(values, errors="coerce")
    s = numeric.dropna()
    if kind == "int":
        arr = s.astype(np.int64).to_numpy()
    else:
        arr = s.astype(np.float64).to_numpy()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    np.savetxt(out_path, arr, fmt="%d" if kind == "int" else "%.17g")
    return len(arr)


def process_corporations():
    table_dir = os.path.join(HERE, "Corporations")
    csv_path = os.path.join(table_dir, "Corporations_1.csv")
    ncols = len(CORPORATIONS_SCHEMA)
    df = pd.read_csv(
        csv_path,
        sep="|",
        header=None,
        usecols=range(ncols),
        names=[name for name, _ in CORPORATIONS_SCHEMA],
        dtype=str,
        na_values=["null", ""],
        engine="c",
    )
    out_dir = os.path.join(table_dir, "csv")
    report = []
    for name, kind in CORPORATIONS_SCHEMA:
        if kind == "str":
            continue
        safe_name = name.replace(" ", "_").replace("/", "_")
        out_path = os.path.join(out_dir, f"{safe_name}.txt")
        n = write_column(df[name], out_path, kind)
        report.append((name, kind, n))
    return report


def process_medicare1():
    table_dir = os.path.join(HERE, "Medicare1")
    ncols = len(MEDICARE1_SCHEMA)
    names = [name for name, _ in MEDICARE1_SCHEMA]
    parts = []
    for fname in ("Medicare1_1.csv", "Medicare1_2.csv"):
        csv_path = os.path.join(table_dir, fname)
        parts.append(
            pd.read_csv(
                csv_path,
                sep="|",
                header=None,
                usecols=range(ncols),
                names=names,
                dtype=str,
                na_values=["null", ""],
                engine="c",
            )
        )
    df = pd.concat(parts, ignore_index=True)  # native file order, file1 then file2
    out_dir = os.path.join(table_dir, "csv")
    report = []
    for name, kind in MEDICARE1_SCHEMA:
        if kind == "str":
            continue
        safe_name = name.replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
        out_path = os.path.join(out_dir, f"{safe_name}.txt")
        numeric = pd.to_numeric(df[name], errors="coerce")
        s = numeric.dropna()
        s = s.iloc[:MEDICARE1_ROW_CAP]  # cap AFTER dropping nulls, preserving file order
        n = write_column(s, out_path, kind)
        report.append((name, kind, n))
    return report


def write_readme(corp_report, medicare_report):
    lines = []
    lines.append("# PublicBI dataset extraction for SubIntSplit benchmarking\n")
    lines.append(
        "Raw PublicBI CSVs (`Corporations/Corporations_1.csv`, "
        "`Medicare1/Medicare1_{1,2}.csv`) are pipe-delimited and headerless. "
        "Schemas below were supplied by the user (DDL). This script extracts "
        "every int/float column to one-value-per-line `.txt` files under "
        "`<table>/csv/<column>.txt` for the nimble `ml_id_compression` "
        "benchmark drivers (`--mlidc_file`). All `varchar` columns are excluded.\n"
    )
    lines.append("## Corporations\n")
    lines.append(
        "The raw CSV has 27 columns; the schema below has 25 -- the user "
        "removed 2 trailing varchar columns from the DDL before sharing it, "
        "so only the first 25 positional columns are read and the trailing "
        "2 are ignored entirely. No columns are nullable (`NOT NULL` in the "
        "DDL), so no rows were dropped.\n"
    )
    lines.append("| column | dtype | values written |")
    lines.append("|---|---|---|")
    for name, kind, n in corp_report:
        lines.append(f"| {name} | {kind} | {n} |")
    lines.append("")
    lines.append("## Medicare1\n")
    lines.append(
        f"`Medicare1_1.csv` and `Medicare1_2.csv` share the same 26-column "
        "schema (a file-level split of one logical table) and are "
        "concatenated in file order (file 1 then file 2), matching the "
        "decision to skip any fileorder-vs-sorted comparison for this "
        "dataset. Nullable columns have their null rows dropped "
        "independently per column (so column files have different lengths). "
        f"After null-dropping, each column is capped to the first "
        f"{MEDICARE1_ROW_CAP:,} values (in file order) to bound sweep time "
        "at Medicare1's full 17.3M-row scale.\n"
    )
    lines.append("| column | dtype | values written |")
    lines.append("|---|---|---|")
    for name, kind, n in medicare_report:
        lines.append(f"| {name} | {kind} | {n} |")
    lines.append("")
    with open(os.path.join(HERE, "README.md"), "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    corp_report = process_corporations()
    print("Corporations:", corp_report)
    medicare_report = process_medicare1()
    print("Medicare1:", medicare_report)
    write_readme(corp_report, medicare_report)
    print("Wrote README.md")
