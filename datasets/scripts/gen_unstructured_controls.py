#!/usr/bin/env python3
"""Unstructured control columns for the Sec. 2 data-class study (2026-10-02).

hashed_splitmix64: splitmix64 output stream with seed 0, outputs 1..N, i.e. for i in 1..N
  x = i * 0x9E3779B97F4A7C15 mod 2^64; z = (x ^ x>>30) * 0xBF58476D1CE4E5B9;
  z = (z ^ z>>27) * 0x94D049BB133111EB; value = z ^ z>>31.
random_uint64: numpy.random.default_rng(20261002).integers(0, 2**64, N, dtype=uint64).
N = 524,288. One decimal value per line. Usage: gen_unstructured_controls.py OUTDIR
"""
import sys, os
import numpy as np
N = 524288
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
with np.errstate(over="ignore"):
    x = np.arange(1, N + 1, dtype=np.uint64) * np.uint64(0x9E3779B97F4A7C15)
    z = (x ^ (x >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
    z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
    z = z ^ (z >> np.uint64(31))
r = np.random.default_rng(20261002).integers(0, 2**64, N, dtype=np.uint64, endpoint=False)
for name, v in (("hashed_splitmix64", z), ("random_uint64", r)):
    with open(os.path.join(out, name + ".txt"), "w") as f:
        f.write("\n".join(str(int(t)) for t in v)); f.write("\n")
