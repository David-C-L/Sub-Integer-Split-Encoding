#!/usr/bin/env python3
"""Medicare1 NPI at full length (17,290,144 rows): generate_publicbi_ints.py's extraction
(same parse options, null dropping and file order, file 1 then file 2) without its
2,000,000-row cap. Reads only the NPI field; its first 2,000,000 rows are verified identical
to Medicare1/csv/NPI.txt. Writes Medicare1/csv/NPI_full.txt. Needs pandas and numpy."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_publicbi_ints as g
import pandas as pd
names = [n for n, _ in g.MEDICARE1_SCHEMA]
idx = names.index("NPI")
parts = [pd.read_csv(os.path.join(g.HERE, "Medicare1", f), sep="|", header=None, usecols=[idx],
                     dtype=str, na_values=["null", ""], engine="c").iloc[:, 0]
         for f in ("Medicare1_1.csv", "Medicare1_2.csv")]
s = pd.to_numeric(pd.concat(parts, ignore_index=True), errors="coerce").dropna()
print("rows", g.write_column(s, os.path.join(g.HERE, "Medicare1", "csv", "NPI_full.txt"), "int"))
