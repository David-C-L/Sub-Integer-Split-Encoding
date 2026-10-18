#!/usr/bin/env python3
"""Table 2 (tab:eval_setup): evaluation columns with source, layout source, rows (millions) and distinct ratio.

Rows and Distinct come from data/table2_column_stats/column_stats.csv (written by
datasets/compute_column_stats.py over the full-length columns; floats over their 524,288-row files, POI-lat over
its full 424,205 rows). Source and Layout citations are a fixed mapping.
Formatting: rows in millions with one decimal at >= 10M and two decimals below; distinct ratio with two decimals,
"$<$0.01" below 0.005.
Output: <out>/tab_eval_setup.tex
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import artifact_paths as AP  # noqa: E402

STATS = os.path.join(AP.DATA, "table2_column_stats", "column_stats.csv")
PB = r"Public BI~\cite{publicbi,vogelsgesang2018get}"
GROUPS = [
    (r"\SFV{} columns", [
        ("snowflake", "Snowflake", r"Tweets~\cite{tacchi2023cultural}", r"\cite{twitter2010snowflake}"),
        ("xmark_prepost_full", "XMark", r"XMark~\cite{schmidt2002xmark}", "ours"),
        ("osm_h3_r9_fileorder", "H3", r"OSM GB~\cite{osm_geofabrik_2026_gb}", r"\cite{uberh3}"),
        ("osm_s2_l30_fileorder", "S2", r"OSM GB~\cite{osm_geofabrik_2026_gb}", r"\cite{s2geometry2017}"),
        ("bing_quadkey", "Bing", r"HRSL~\cite{hrsl_labels,tiecke2017mapping}", r"\cite{microsoft_bing_tiles}"),
        ("uuidv7_hi", "UUIDv7-hi", "generated", r"\cite{davis2024rfc}"),
    ]),
    ("Controls", [
        ("publicbi_npi", "NPI", PB, "--"),
        ("publicbi_id1", "Id1", PB, "--"),
        ("uuidv7_lo", "UUIDv7-lo", "generated", "--"),
    ]),
    ("Float columns", [
        ("F1_stocks_usa", "Stocks", r"INFORE~\cite{infore2020financial,afroozeh2023alp}", r"\cite{ieee19}"),
        ("F5_city_temp", "Temp", r"Kaggle~\cite{citytemp_kaggle,afroozeh2023alp}", r"\cite{ieee19}"),
        ("F6_air_pressure", "Press.", r"NEON~\cite{neon_barometric,afroozeh2023alp}", r"\cite{ieee19}"),
        ("F8_poi_lat", "POI-lat", r"Kaggle~\cite{poi_kaggle,afroozeh2023alp}", r"\cite{ieee19}"),
        ("F10_medicare_calc", "Calc.", PB, r"\cite{ieee19}"),
    ]),
]


def fmt_rows(n):
    m = n / 1e6
    return f"{m:.1f}" if m >= 10 else f"{m:.2f}"


def fmt_distinct(r):
    return "$<$0.01" if r < 0.005 else f"{r:.2f}"


stats = {r["column"]: r for r in csv.DictReader(open(STATS))}
lines = [r"{\setlength{\tabcolsep}{4pt}%", r"\begin{tabular}{@{}llcrr@{}}", r"\toprule",
         r"Column & Source & Layout & Rows (M) & Distinct \\"]
for title, rows in GROUPS:
    lines += [r"\midrule", rf"\multicolumn{{5}}{{l}}{{\textit{{{title}}}}} \\"]
    for key, label, src, layout in rows:
        s = stats[key]
        lines.append(f"{label:<9} & {src} & {layout} & {fmt_rows(int(s['rows_used']))} & "
                     f"{fmt_distinct(float(s['distinct_ratio']))} \\\\")
lines += [r"\bottomrule", r"\end{tabular}}"]
out = os.path.join(AP.OUT, "tab_eval_setup.tex")
open(out, "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
