#!/usr/bin/env python3
"""Turn a raw w524.sh sweep directory into the pull layout eval_figures reads.

- bulk_hot_* / point_hot_* are also written as bulk_* / point_* (the old
  pull's hot-cache names); the cache-state-named files are kept alongside.
- enc_* gains encode_cpu_ms and encode_cpu_Meps, parsed from the driver log
  (SIS encodes sections on several threads, so wall time is not comparable).
- skip_hot_<col>_shipped_r* is derived from range_hot (B <= 32768), the same
  small-slice uniform-offset reads the old skip sweep measured.
Raw files are never modified.
"""
import os, re, shutil, sys
import pandas as pd

raw, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
for name in sorted(os.listdir(raw)):
    if not name.endswith(".csv"):
        continue
    src = os.path.join(raw, name)
    if name.startswith("enc_"):
        df = pd.read_csv(src)
        log = src + ".log"
        cpu = {}
        if os.path.exists(log):
            arm = None
            for line in open(log, errors="replace"):
                m = re.match(r"^  (\S+): \d+ B", line)
                if m:
                    arm = m.group(1)
                m = re.match(r"^\s+cpu: ([\d.]+) ms per encode", line)
                if m and arm:
                    cpu[arm] = float(m.group(1))
        df["encode_cpu_ms"] = df["encoding"].map(cpu)
        df["encode_cpu_Meps"] = df["N"] / 1e6 / (df["encode_cpu_ms"] / 1e3)
        df.to_csv(os.path.join(out, name), index=False)
        continue
    shutil.copy2(src, os.path.join(out, name))
    for kind in ("bulk", "point"):
        if name.startswith(f"{kind}_hot_"):
            shutil.copy2(src, os.path.join(out, kind + "_" + name[len(kind) + 5:]))
    if name.startswith("range_hot_") and "_shipped_r" in name:
        df = pd.read_csv(src)
        df[df["B"] <= 32768].to_csv(os.path.join(out, "skip_hot_" + name[len("range_hot_"):]), index=False)
print("files:", len(os.listdir(out)))
