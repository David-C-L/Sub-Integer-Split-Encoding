#!/usr/bin/env python3
"""Sec. 7 size-budget claim on eight columns, from data/decode_knob_8col/eval3_measurements.csv.

Paper: "the encoded size stays within the budget at every step and on all eight columns we measure" and
"at a 5% budget, SIS reads XMark and Id1 slower than the default SIS".
Setting (as in the Snowflake budget figure): strict budget on encoded bytes, point 0.5 / bulk 0.5 mix
(tags M_P1B1_b<budget>), default planner SIS/realNested, against the same planner without the knob (tag w0).
Sizes: full length (bytes_full) and the 524,288-row prefix (bytes_524288); reads on the prefix, view path, median
of 3 repeats. Read ratios are rate ratios (default time / budget time; < 1 = slower).
Note: this run uses build rev-decode-knob without --mlidc_sis_section_candidates=addressable (section encodings
not restricted), unlike the TopLevel Sec. 7 runs.
Usage: python3 scripts/derive/budget_8col.py
"""
import os
import sys

import pandas as pd

ROOT = os.environ.get("SIS_ARTIFACT_ROOT",
                      os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
d = pd.read_csv(os.path.join(ROOT, "data", "decode_knob_8col", "eval3_measurements.csv"))
d = d[d.arm == "SIS/realNested"]
assert (d.validated == 1).all()
base = d[d.tag == "w0"].set_index("dataset")
ok = True
for budget, tag in ((0.02, "M_P1B1_b0p02"), (0.05, "M_P1B1_b0p05"), (0.10, "M_P1B1_b0p1")):
    x = d[d.tag == tag].set_index("dataset").reindex(base.index)
    r = pd.DataFrame({
        "size_full": x.bytes_full / base.bytes_full - 1,
        "size_prefix": x.bytes_524288 / base.bytes_524288 - 1,
        "sections": base.read_sections.astype(int).astype(str) + "->" + x.read_sections.astype(int).astype(str),
        "point": base.point_ns / x.point_ns,
        "range64": base.range64_ns / x.range64_ns,
        "bulk": base.bulk_ms / x.bulk_ms,
        "open_first_bulk": base.open_plus_first_bulk_ms / x.open_plus_first_bulk_ms,
    })
    within = bool((r.size_full <= budget + 1e-9).all() and (r.size_prefix <= budget + 1e-9).all())
    ok &= within
    print(f"budget {budget:.0%}: {len(r)} columns, max size full {r.size_full.max():+.1%}, "
          f"prefix {r.size_prefix.max():+.1%}, within budget on all: {within}")
    print(r.round(3).to_string())
    slower = r[(r[["point", "range64", "bulk", "open_first_bulk"]] < 1.0).any(axis=1)]
    print("columns with any read ratio < 1:", ", ".join(f"{c} (min {slower.loc[c, ['point', 'range64', 'bulk', 'open_first_bulk']].min():.3f})"
                                                      for c in slower.index) or "none")
    print()
sys.exit(0 if ok else 1)
