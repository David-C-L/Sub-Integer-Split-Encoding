#!/usr/bin/env python3
"""RECONSTRUCTED from the float columns' README (the original extraction was not kept, and the archive was
deleted after use, so this script has not been checked against the original output).
ALP's reproducibility archive complete_binaries.zip (linked from cwida/ALP publication/script/master_script.sh)
holds one raw little-endian float64 file per column. This writes the file-order prefix (first N values; POI-lat
in full) as text, one "%.17g" value per line, and asserts every value round-trips bit-exactly.
  F1_stocks_usa.txt     <- stocks_usa_c.bin            F6_air_pressure.txt   <- neon_air_pressure.bin
  F3_gov10.txt          <- gov10.bin                   F7_dew_point_temp.txt <- neon_dew_point_temp.bin
  F5_city_temp.txt      <- city_temperature_f.bin      F8_poi_lat.txt        <- poi_lat.bin (all 424,205 rows)
  F9_nyc29.txt          <- nyc29.bin
Usage: extract_alp_floats.py IN.bin OUT.txt [N=524288]
"""
import struct
import sys

import numpy as np

src, out = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 524288
v = np.fromfile(src, dtype="<f8", count=n)
assert np.isfinite(v).all()
with open(out, "w") as f:
    for x in v.tolist():
        s = "%.17g" % x
        assert struct.pack("<d", float(s)) == struct.pack("<d", x)
        f.write(s + "\n")
print(out, len(v))
