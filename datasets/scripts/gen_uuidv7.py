#!/usr/bin/env python3
"""UUIDv7 column pair (RFC 9562 s5.7, Method 1: 12-bit rand_a counter), simulated Poisson
arrivals at 2,000 IDs/s from 2025-01-01. Seeded, so the first N rows of a longer run are
identical to a shorter run. Writes the high and low 64-bit halves as two columns.
Usage: gen_uuidv7.py N OUT_DIR SUFFIX   (files uuidv7_hi{SUFFIX}.txt, uuidv7_lo{SUFFIX}.txt)"""
import random, sys, os
N, out, suffix = int(sys.argv[1]), sys.argv[2], sys.argv[3]
rng = random.Random(7); t = 1735689600000.0; last = -1; ctr = 0; prev = None
with open(os.path.join(out, f"uuidv7_hi{suffix}.txt"), "w") as fh, open(os.path.join(out, f"uuidv7_lo{suffix}.txt"), "w") as fl:
    for i in range(N):
        t += rng.expovariate(2000.0) * 1000.0; ms = int(t)
        if ms != last: ctr = rng.getrandbits(11); last = ms   # seed counter below 2^11, leaving headroom
        else:
            ctr += 1
            if ctr >= 4096: ms = last = ms + 1; ctr = rng.getrandbits(11)
        u = (ms << 80) | (0x7 << 76) | (ctr << 64) | (0b10 << 62) | rng.getrandbits(62)
        assert (u >> 76) & 0xF == 7 and (u >> 62) & 0b11 == 0b10
        assert prev is None or u > prev; prev = u
        fh.write(f"{u >> 64}\n"); fl.write(f"{u & ((1 << 64) - 1)}\n")
