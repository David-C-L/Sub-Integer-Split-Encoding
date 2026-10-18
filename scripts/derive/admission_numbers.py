#!/usr/bin/env python3
"""Numbers quoted in Sec. 7.7 from an admission dir (42 CSVs). Truth rule as make_table7_admission.py
(gates.SIS_ARMS best < 0.99 x best non-SIS, non-OpenZL encoder). Usage: admission_numbers.py <dir>"""
import sys, os, glob
import pandas as pd, numpy as np
A = os.environ.get("SIS_ARTIFACT_ROOT", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
os.environ.setdefault("SIS_PROFILES_NPZ", f"{A}/data/bitflip_profiles/profiles.npz")
sys.path.insert(0, f"{A}/scripts/plot/admission")
import gates
D = sys.argv[1]
fs = sorted(glob.glob(os.path.join(D, "*.csv")))
d = pd.concat([pd.read_csv(f).assign(col=os.path.basename(f)[:-4]) for f in fs], ignore_index=True)
enc = d[(d.row_kind == "encoder") & (d.skipped != 1)]
truth = {}
for c, g in enc.groupby("col"):
    b = g.set_index("encoding").payload_bytes
    sis = min(b[a] for a in gates.SIS_ARMS if a in b)
    other = min(v for a, v in b.items() if not a.startswith("SIS/") and not a.startswith("openzl"))
    truth[c] = sis < 0.99 * other
h = d[d.row_kind == "heuristic"].set_index("col")
est = {c: h.loc[c, "estimate_admits"] == 1 for c in truth}
fp = sorted(c for c in truth if est[c] and not truth[c]); fn = sorted(c for c in truth if truth[c] and not est[c])
gate = d[(d.row_kind == "admission") & (d.admission_mode == "bitflip") & (d.profile_pairs == 1024)].set_index("col")
gfp = sorted(c for c in truth if gate.loc[c, "decision"] == 1 and not truth[c]); gfn = sorted(c for c in truth if gate.loc[c, "decision"] != 1 and truth[c])
sisenc = enc[enc.encoding == "SIS/realNested"].set_index("col").encode_ns
share = (gate.decision_ns / sisenc).dropna() * 100
print(f"columns {len(truth)} positives {sum(truth.values())}")
print(f"estimate: FP {len(fp)} {fp} FN {len(fn)} {fn}; median decision {h.decision_ns.median()/1e6:.3f} ms")
print(f"gate 1024: FP {len(gfp)} {gfp} FN {len(gfn)} {gfn}; median decision {gate.decision_ns.median()/1e3:.1f} us "
      f"(min {gate.decision_ns.min()/1e3:.1f} max {gate.decision_ns.max()/1e3:.1f})")
print(f"gate / SIS/realNested encode_ns: {share.min():.3f}% to {share.max():.3f}% (median {share.median():.3f}%)")
