#!/usr/bin/env python3
"""Full-length comp/compzl in the merged_shipped layout with SIS in TopLevel mode.
Input: sweep_full2_20260930_1213/merged_shipped/{comp,compzl}_<col>_shipped.csv (kDefault SIS rows) and
sweep_full2_20260930_1213/full/{comp,compzl}_<col>_{rn,hy}-addressable.csv (SIS/realNested(+view), SIS/hybrid(+view)
under --mlidc_sis_section_candidates=addressable = TopLevel at rev-addr-toplevel). Rows of those four arms are replaced; every
other row (OpenZL, baselines) is kept. Sizes are bytes, so build-independent (rn-addressable reproduced byte for byte by
toplevel_sec7 ladder/arm15 and arm3 on the run build). Output: derived/merged_shipped_toplevel/."""
import os, pandas as pd
A = os.environ.get("SIS_ARTIFACT_ROOT", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
F2 = f"{A}/data/sweep_full2"
OUT = os.environ.get("SIS_DERIVE_OUT", f"{A}/derived/toplevel_sec7/merged_shipped_toplevel")
os.makedirs(OUT, exist_ok=True)
COLS = ["snowflake", "xmark_prepost_full", "osm_h3_r9_fileorder", "osm_s2_l30_fileorder", "bing_quadkey",
        "uuidv7_hi", "publicbi_npi", "publicbi_id1", "uuidv7_lo", "instagram"]
for c in COLS:
    for k in ("comp", "compzl"):
        src = f"{F2}/merged_shipped/{k}_{c}_shipped.csv"
        if not os.path.exists(src):
            continue
        m = pd.read_csv(src)
        rep = []
        for g, arms in (("rn", ["SIS/realNested", "SIS/realNested+view"]), ("hy", ["SIS/hybrid", "SIS/hybrid+view"])):
            p = f"{F2}/full/{k}_{c}_{g}-addressable.csv"
            if os.path.exists(p):
                d = pd.read_csv(p)
                d = d[d.encoding.isin(arms)]
                rep.append(d)
                m = m[~m.encoding.isin(set(d.encoding))]
        out = pd.concat([m] + rep, ignore_index=True)
        out.to_csv(f"{OUT}/{k}_{c}_shipped.csv", index=False)
        print(c, k, "replaced", sum(len(r) for r in rep))
