#!/usr/bin/env python3
"""RECONSTRUCTED from the float README (no script was kept). Uniform float control C0:
numpy.random.default_rng(20261002).uniform(-1e9, 1e9, 524288), written "%.17g" per line.
Usage: gen_uniform_float_control.py C0_uniform_control.txt"""
import sys

import numpy as np

v = np.random.default_rng(20261002).uniform(-1e9, 1e9, size=524288)
with open(sys.argv[1], "w") as o:
    o.writelines("%.17g\n" % x for x in v.tolist())
