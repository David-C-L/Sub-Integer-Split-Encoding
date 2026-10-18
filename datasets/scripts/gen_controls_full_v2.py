#!/usr/bin/env python3
"""PublicBI unstructured control columns (2026-09-29), full length -- v2.

Copy of gen_controls_full.py (do not edit the original); only change is the
JOBS dict: extracts Medicare1.TOTAL_DRUG_COST_GE65 (double, GE65-population
subset of TOTAL_DRUG_COST, <=2 decimals, some cells in scientific notation)
as integer cents, replacing publicbi_day_supply in the final control set.

Same extraction as ../PublicBI/generate_publicbi_ints.py and gen_npi_full.py:
pipe-delimited headerless CSVs, positional schema from generate_publicbi_ints.py,
dtype=str with na_values ["null", ""], pd.to_numeric(errors="coerce"), nulls
dropped, native file order (Medicare1_1.csv then Medicare1_2.csv), no row cap,
np.savetxt(fmt="%d"), one integer per line.

Usage: python3 gen_controls_full_v2.py <PublicBI dir> <out dir>   (needs numpy, pandas)
"""
import os, sys
import numpy as np, pandas as pd

SRC, OUT = sys.argv[1], sys.argv[2]
sys.path.insert(0, SRC)
import generate_publicbi_ints as g

JOBS = {  # table -> [(column, kind, output file)]
    "Medicare1": [("TOTAL_DRUG_COST_GE65", "cents", "Medicare1_TOTAL_DRUG_COST_GE65_cents_full.txt")],
}
FILES = {"Medicare1": ["Medicare1/Medicare1_1.csv", "Medicare1/Medicare1_2.csv"]}
SCHEMA = {"Medicare1": g.MEDICARE1_SCHEMA}

os.makedirs(OUT, exist_ok=True)
for t, jobs in JOBS.items():
    names = [n for n, _ in SCHEMA[t]]
    idx = [names.index(c) for c, _, _ in jobs]
    df = pd.concat([pd.read_csv(os.path.join(SRC, f), sep="|", header=None, usecols=idx,
                                dtype=str, na_values=["null", ""], engine="c")
                    for f in FILES[t]], ignore_index=True)
    for (c, kind, fn), i in zip(jobs, idx):
        s = pd.to_numeric(df[i], errors="coerce").dropna()
        if kind == "cents":
            x = s.to_numpy(np.float64) * 100
            arr = np.round(x).astype(np.int64)
            assert np.abs(x - arr).max() < 1e-6, "non-cent value"
        else:
            arr = s.astype(np.int64).to_numpy()
        np.savetxt(os.path.join(OUT, fn), arr, fmt="%d")
        print(fn, "rows", len(arr), "nulls_dropped", len(df) - len(arr), flush=True)
