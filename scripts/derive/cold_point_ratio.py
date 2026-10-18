#!/usr/bin/env python3
"""tex 1264 'at most a third': per column, (OpenZL/SIS point latency, cold-payload) / (same, hot).
SIS = SIS/realNested+view (fixed arm of fig10); OpenZL = best qualifying config as make_scoreboard.py
(openzl/auto always; block-1024/65536 only if bits <= SIS bits). Medians over offsets per repeat, then repeats.
Usage: cold_point_ratio.py <pull dir>"""
import sys, os
import numpy as np, pandas as pd
D = sys.argv[1]
COLS = ["snowflake", "xmark_prepost_full", "osm_h3_r9_fileorder", "osm_s2_l30_fileorder", "bing_quadkey",
        "uuidv7_hi", "publicbi_npi", "publicbi_id1", "uuidv7_lo"]
OZ = ["openzl/auto", "openzl/block-1024", "openzl/block-65536"]
def rep(prefix, c):
    fr = []
    for r in (1, 2, 3):
        p = f"{D}/{prefix}_{c}_shipped_r{r}.csv"
        if os.path.exists(p):
            d = pd.read_csv(p); d["_r"] = r; fr.append(d)
    return pd.concat(fr) if fr else None
def med(df, enc):
    s = df[(df.encoding == enc) & (df.get("skipped", 0) != 1)]
    return s.groupby("_r").ns_per_probe.median().median() if len(s) else np.nan
out = []
for c in COLS:
    bits = pd.read_csv(f"{D}/comp_{c}_shipped.csv").set_index("encoding").bits_per_elem
    sb = bits["SIS/realNested"]
    elig = [a for a in OZ if a == "openzl/auto" or bits.get(a, np.inf) <= sb]
    row = {"column": c}
    for st, pre in (("hot", "point_hot"), ("cold", "point_cold_payload")):
        d = rep(pre, c)
        s = med(d, "SIS/realNested+view"); z = min(med(d, a) for a in elig)
        row[f"sis_{st}"] = s; row[f"ozl_{st}"] = z; row[f"ratio_{st}"] = z / s
    row["cold_over_hot"] = row["ratio_cold"] / row["ratio_hot"]
    out.append(row)
t = pd.DataFrame(out); print(t.round(3).to_string(index=False))
print("max |change|: %.1f%%" % (100 * (t.cold_over_hot - 1).abs().max()))
