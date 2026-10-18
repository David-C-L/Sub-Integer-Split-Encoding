"""D1: encoder-agnostic, SIS-independent structure measure (study_20261001/D, 2026-10-02).

PIDS-style ("a generic compressor shows what's missed"): for each of the 24 Sec.2 columns,
compress the raw 64-bit values as ONE stream (WHOLE) with four generic, unmodified byte-stream
compressors (xz/LZMA preset 6, zstd level 19, LZ4 frame default level, Snappy), then compress
the SAME column split into byte-ranges under (a) the documented field layout (SPLIT_DOC, where
a layout exists) and (b) the data-chosen flip-profile-gradient partition (SPLIT_DATA, reusing
C/scripts/structure_common.py's data_chosen_partition unchanged so the partitions match C
exactly), each range compressed as its own stream and the sizes summed. Also two
no-structure-knowledge reference splits: BYTE-PLANE and BIT-PLANE.

No SIS, no cost model, no encoder: xz, zstd, lz4, and snappy are generic, off-the-shelf
byte-stream compressors, never told anything about the data's structure. Local only.
LZ4 (python `lz4` 4.4.5, liblz4 1.9.4) and Snappy (python-snappy 0.7.3 + cramjam 2.13.0,
libsnappy 1.1.10) added 2026-10-02 per the author's request, for completeness alongside xz/zstd;
both installed into the project .venv (EncodingsPlayground/Datasets/.venv) since neither
shipped there originally.
"""
import json
import lzma
import os
import subprocess
import sys

import numpy as np
import lz4.frame
import snappy

D1_DIR = os.path.dirname(os.path.dirname(__file__))  # .../D
STUDY_DIR = os.path.dirname(D1_DIR)  # .../study_20261001
C_SCRIPTS = os.path.join(STUDY_DIR, "C", "scripts")
sys.path.insert(0, C_SCRIPTS)
import structure_common as S  # noqa: E402
A = S.A  # A/scripts/study_common.py, reused for registry + flip_profile + field

N = S.N  # 524288


# ---------------- compressors ----------------

def xz_size(data: bytes) -> int:
    return len(lzma.compress(data, format=lzma.FORMAT_XZ, preset=6))


def zstd_size(data: bytes) -> int:
    proc = subprocess.run(["zstd", "-19", "-c", "-q"], input=data,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True)
    return len(proc.stdout)


def lz4_size(data: bytes) -> int:
    return len(lz4.frame.compress(data))  # default compression_level (fast mode)


def snappy_size(data: bytes) -> int:
    return len(snappy.compress(data))


COMPRESSORS = {"xz": xz_size, "zstd": zstd_size, "lz4": lz4_size, "snappy": snappy_size}


# ---------------- byte/bit packing ----------------

def narrow_width_bytes(values: np.ndarray) -> int:
    """Narrowest whole-byte width (1..8) that holds max(values)."""
    mx = int(values.max()) if len(values) else 0
    nbits = max(1, mx.bit_length())
    return max(1, (nbits + 7) // 8)


def pack_le_stream(values: np.ndarray, width: int) -> bytes:
    """One AOS byte stream: width bytes per value, little-endian, concatenated in file order."""
    arr = values.astype(np.uint64)
    buf = arr.astype("<u8").tobytes()  # 8 LE bytes per value
    b = np.frombuffer(buf, dtype=np.uint8).reshape(-1, 8)
    return b[:, :width].tobytes()


def byte_planes(values: np.ndarray, width: int):
    """width separate streams, stream j = byte j (0=LSB) of every value, in file order (SoA)."""
    arr = values.astype(np.uint64)
    buf = arr.astype("<u8").tobytes()
    b = np.frombuffer(buf, dtype=np.uint8).reshape(-1, 8)
    return [b[:, j].tobytes() for j in range(width)]


def bit_planes(values: np.ndarray, nbits: int):
    """nbits separate bit-packed streams, stream j = bit j (0=LSB) of every value."""
    arr = values.astype(np.uint64)
    out = []
    for j in range(nbits):
        bits = ((arr >> np.uint64(j)) & np.uint64(1)).astype(np.uint8)
        out.append(np.packbits(bits).tobytes())
    return out


# ---------------- per-range extraction + compression ----------------

def range_streams(values: np.ndarray, ranges):
    """ranges: list of (lo, hi) half-open bit ranges. Returns list of (width_bytes, stream)."""
    out = []
    for (lo, hi) in ranges:
        fv = A.field(values, lo, hi)
        w = narrow_width_bytes(fv)
        out.append((w, pack_le_stream(fv, w)))
    return out


def sum_compressed(streams, comp_fn):
    return sum(comp_fn(s) for (_, s) in streams)


def main():
    rows = []
    names = sorted(S.ALL_COLUMNS.keys())
    for name in names:
        cfg = S.ALL_COLUMNS[name]
        values = S.load(name, n=N)
        n = len(values)
        kind = cfg.get("kind")
        subtype = cfg.get("subtype")
        layout = cfg.get("layout")

        w_full = narrow_width_bytes(values)
        whole_u64_stream = pack_le_stream(values, 8)
        whole_narrow_stream = pack_le_stream(values, w_full) if w_full < 8 else whole_u64_stream

        doc_ranges = [(lo, hi) for (_, lo, hi) in layout] if layout else None
        p_flip = A.flip_profile(values)
        data_ranges = S.data_chosen_partition(p_flip, k=2.0)

        doc_streams = range_streams(values, doc_ranges) if doc_ranges else None
        data_streams = range_streams(values, data_ranges)
        bp_streams = [(1, s) for s in byte_planes(values, w_full)]
        bitp_streams = [(1, s) for s in bit_planes(values, w_full * 8)]

        for cname, comp_fn in COMPRESSORS.items():
            whole_u64_sz = comp_fn(whole_u64_stream)
            whole_narrow_sz = comp_fn(whole_narrow_stream)
            best_whole_sz = min(whole_u64_sz, whole_narrow_sz)
            best_whole_bpv = best_whole_sz * 8.0 / n

            def rec(variant, total_sz, n_streams, ranges_desc):
                bpv = total_sz * 8.0 / n
                gain_pct = (best_whole_bpv - bpv) / best_whole_bpv * 100.0 if best_whole_bpv > 0 else 0.0
                rows.append(dict(
                    column=name, kind=kind, subtype=subtype, compressor=cname, variant=variant,
                    n_rows=n, n_streams=n_streams, compressed_bytes=total_sz,
                    bits_per_value=bpv, gain_pct_vs_best_whole=gain_pct, ranges=ranges_desc,
                ))

            rec("WHOLE_u64", whole_u64_sz, 1, "[0,64)")
            rec("WHOLE_narrow", whole_narrow_sz, 1, f"[0,{w_full*8})")
            # best-whole row itself (reference, gain=0 by construction, marks which won)
            rows.append(dict(
                column=name, kind=kind, subtype=subtype, compressor=cname, variant="WHOLE_best",
                n_rows=n, n_streams=1, compressed_bytes=best_whole_sz,
                bits_per_value=best_whole_bpv, gain_pct_vs_best_whole=0.0,
                ranges="u64" if whole_u64_sz <= whole_narrow_sz else "narrow",
            ))

            if doc_streams is not None:
                doc_sz = sum_compressed(doc_streams, comp_fn)
                rec("SPLIT_DOC", doc_sz, len(doc_streams), json.dumps(doc_ranges))

            data_sz = sum_compressed(data_streams, comp_fn)
            rec("SPLIT_DATA", data_sz, len(data_streams), json.dumps(data_ranges))

            bp_sz = sum_compressed(bp_streams, comp_fn)
            rec("BYTE_PLANE", bp_sz, len(bp_streams), f"{w_full} byte-planes")

            bitp_sz = sum_compressed(bitp_streams, comp_fn)
            rec("BIT_PLANE", bitp_sz, len(bitp_streams), f"{w_full*8} bit-planes")

        print(f"done: {name} (n={n}, w_full={w_full}B, doc_ranges={len(doc_ranges) if doc_ranges else 0}, "
              f"data_ranges={len(data_ranges)})", file=sys.stderr)

    import pandas as pd
    df = pd.DataFrame(rows)
    out_csv = os.path.join(D1_DIR, "csv", "split_measure.csv")
    df.to_csv(out_csv, index=False)
    print(f"wrote {out_csv} ({len(df)} rows)")


if __name__ == "__main__":
    main()
