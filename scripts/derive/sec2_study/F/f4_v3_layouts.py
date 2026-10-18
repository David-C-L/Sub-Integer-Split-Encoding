"""F4 (v3): richer addressable layouts + row-order share (study_20261001/F, 2026-10-05).

Section 2 never applies SIS: plain numpy textbook layouts only. Imports F1's four layouts
unchanged (so they stay byte-identical) and adds two:

- RLE_RANK: run values at W bits (W = bit width of the column/range max) plus run END positions
  (exclusive) at P = bit_length(n) bits each. The end-position array is itself the rank
  directory: row i is found by binary search for the first end > i, O(log r). Headers: width
  (WIDTH_HDR_BITS) + run count (DICT_COUNT_HDR_BITS).
- PFOR: patched FOR per 1024-row block. Per block: min (W bits), slot width b (8), exception
  value width we (8), exception count (bit_length(1024)=11). Slots: b bits per row. Exceptions
  (residual >= 2**b): position within block (10 bits) + full residual (we bits, we = bit length
  of the block's max residual). b in [0, we] chosen per block to minimise bits. Row i: O(1) slot
  read, then a search among the block's <= 1024 sorted exception positions.

SPLIT_*6 pick the best of the six layouts per range with RANGE_TAG_BITS6 = 3 bits.
Task B: row shuffle (default_rng(0).permutation), xz preset 6 on D's WHOLE_best bytes, layouts
re-evaluated on the shuffled order (same data-chosen cuts, i.e. the schema is fixed).
Outputs (all _v3): csv/addressable_layouts_v3.csv, addressable_ranges_v3.csv, shuffle_gap_v3.csv.
"""
import lzma, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import f1_addressable_layouts as F1  # noqa: E402
S, A = F1.S, F1.A
N, BLOCK = F1.N, F1.BLOCK
F_DIR = F1.F_DIR
RANGE_TAG_BITS6 = 3
POS_BITS = (BLOCK - 1).bit_length()      # 10
CNT_BITS = BLOCK.bit_length()            # 11
sys.path.insert(0, os.path.join(F1.STUDY_DIR, "D", "scripts"))
import d1_split_measure as D1  # noqa: E402


def layout_rle_rank(vals):
    n = len(vals)
    if n == 0:
        return F1.WIDTH_HDR_BITS, {}
    w = F1.bit_width(vals)
    r = 1 + int(np.count_nonzero(vals[1:] != vals[:-1]))
    p = n.bit_length()
    return r * (w + p) + F1.WIDTH_HDR_BITS + F1.DICT_COUNT_HDR_BITS, dict(runs=r)


def bit_lengths(d):
    bl = np.zeros(len(d), dtype=np.int64)
    for k in range(64):
        bl += (d >> np.uint64(k)) > 0
    return bl


def layout_pfor(vals, block=BLOCK):
    n = len(vals)
    if n == 0:
        return F1.WIDTH_HDR_BITS, {}
    w = F1.bit_width(vals)
    v = vals.astype(np.uint64)
    nb = (n + block - 1) // block
    pad = nb * block - n
    vp = np.concatenate([v, np.repeat(v[-1:], pad)]) if pad else v   # pad = last value, then excluded
    mat = vp.reshape(nb, block)
    mn = mat.min(axis=1)
    d = mat - mn[:, None]
    bl = bit_lengths(d.reshape(-1)).reshape(nb, block)
    rows_in = np.full(nb, block); 
    if pad:
        rows_in[-1] = block - pad
        bl[-1, block - pad:] = 0       # padded rows contribute nothing
    we = bl.max(axis=1)
    hist = np.zeros((nb, 65), dtype=np.int64)
    for j in range(nb):
        hist[j] = np.bincount(bl[j, :rows_in[j]], minlength=65)
    # exceptions at width b: rows with bit length > b
    gt = hist[:, ::-1].cumsum(axis=1)[:, ::-1]     # gt[j,k] = count bl >= k
    total = 0
    for j in range(nb):
        best = None
        for b in range(0, we[j] + 1):
            c = int(gt[j, b + 1]) if b + 1 <= 64 else 0
            cost = rows_in[j] * b + c * (POS_BITS + int(we[j]))
            if best is None or cost < best:
                best = cost
        total += best + w + F1.WIDTH_HDR_BITS * 2 + CNT_BITS
    return total, dict(n_blocks=nb)


LAYOUTS6 = [("FBW", F1.layout_fbw), ("FOR_global", F1.layout_for_global), ("FOR_block", F1.layout_for_block),
            ("DICT", None), ("RLE_RANK", layout_rle_rank), ("PFOR", layout_pfor)]


def all_layouts(vals):
    out = {}
    for m, fn in LAYOUTS6:
        if m == "DICT":
            b, info = F1.layout_dict(vals)
            out[m] = b if info.get("applicable") else None
        else:
            out[m] = fn(vals)[0]
    return out


def best_of(cands, names):
    valid = {m: cands[m] for m in names if cands[m] is not None}
    m = min(valid, key=valid.get)
    return valid[m], m


L4 = ["FBW", "FOR_global", "FOR_block", "DICT"]
L6 = L4 + ["RLE_RANK", "PFOR"]


def split_eval(vals, ranges, rng_rows=None, info=None):
    t4 = t6 = 0
    for (lo, hi) in ranges:
        c = all_layouts(A.field(vals, lo, hi))
        b4, m4 = best_of(c, L4)
        b6, m6 = best_of(c, L6)
        t4 += b4 + F1.RANGE_TAG_BITS
        t6 += b6 + RANGE_TAG_BITS6
        if rng_rows is not None:
            rng_rows.append(dict(**info, lo=lo, hi=hi, width=hi - lo, method4=m4, bits4=b4,
                                 method6=m6, bits6=b6,
                                 **{f"bits_{k}": v for k, v in c.items()}))
    return t4, t6


def xz_best(vals):
    w = D1.narrow_width_bytes(vals)
    u = D1.pack_le_stream(vals, 8)
    nar = D1.pack_le_stream(vals, w) if w < 8 else u
    return min(D1.xz_size(u), D1.xz_size(nar)) * 8.0 / len(vals)


def main():
    rows, rrows, srows = [], [], []
    for name in sorted(S.ALL_COLUMNS):
        cfg = S.ALL_COLUMNS[name]
        vals = S.load(name, n=N)
        n = len(vals)
        layout = cfg.get("layout")
        doc = [(lo, hi) for (_, lo, hi) in layout] if layout else None
        data = S.data_chosen_partition(A.flip_profile(vals), k=2.0)
        base = dict(column=name, kind=cfg.get("kind"), subtype=cfg.get("subtype"))

        c = all_layouts(vals)
        b4, m4 = best_of(c, L4)
        b6, m6 = best_of(c, L6)
        for m, b in c.items():
            rows.append(dict(**base, variant="WHOLE", method=m, total_bits=b,
                             bits_per_value=None if b is None else b / n))
        rows.append(dict(**base, variant="WHOLE", method="WHOLE_best4", total_bits=b4, bits_per_value=b4 / n, winner=m4))
        rows.append(dict(**base, variant="WHOLE", method="WHOLE_best6", total_bits=b6, bits_per_value=b6 / n, winner=m6))
        for var, rg in [("DOC", doc), ("DATA", data)]:
            if rg is None:
                continue
            t4, t6 = split_eval(vals, rg, rrows, dict(column=name, variant=f"SPLIT_{var}"))
            rows.append(dict(**base, variant="SPLIT", method=f"SPLIT_{var}4", total_bits=t4, bits_per_value=t4 / n))
            rows.append(dict(**base, variant="SPLIT", method=f"SPLIT_{var}6", total_bits=t6, bits_per_value=t6 / n))

        # Task B: shuffle
        perm = np.random.default_rng(0).permutation(n)
        sv = vals[perm]
        xf, xs = xz_best(vals), xz_best(sv)
        cs = all_layouts(sv)
        s4, _ = best_of(cs, L4)
        s6, _ = best_of(cs, L6)
        sd4, sd6 = split_eval(sv, data)
        srows.append(dict(**base, base4_bpv=b4 / n, xz_file_bpv=xf, xz_shuf_bpv=xs,
                          whole4_file=b4 / n, whole4_shuf=s4 / n, whole6_file=b6 / n, whole6_shuf=s6 / n,
                          rle_file=c["RLE_RANK"] / n, rle_shuf=cs["RLE_RANK"] / n,
                          pfor_file=c["PFOR"] / n, pfor_shuf=cs["PFOR"] / n,

                          split_data6_shuf=sd6 / n, split_data4_shuf=sd4 / n))
        print("done", name, file=sys.stderr, flush=True)

    out = os.path.join(F_DIR, "csv")
    df = pd.DataFrame(rows)
    # attach xz / OpenZL reference rows
    xzf = pd.read_csv(F1.D_CSV)
    xzf = xzf[(xzf.compressor == "xz") & (xzf.variant == "WHOLE_best")].set_index("column").bits_per_value
    oz = pd.read_csv(os.path.join(out, "openzl_reference.csv")).set_index("column").openzl_full_bpv
    extra = []
    for col in df.column.unique():
        k = df[df.column == col].iloc[0]
        for m, ser in [("xz_WHOLE", xzf), ("OpenZL_WHOLE", oz)]:
            extra.append(dict(column=col, kind=k.kind, subtype=k.subtype, variant="GENERIC", method=m,
                              bits_per_value=ser.get(col), total_bits=ser.get(col, np.nan) * N))
    df = pd.concat([df, pd.DataFrame(extra)], ignore_index=True)
    df.to_csv(os.path.join(out, "addressable_layouts_v3.csv"), index=False)
    pd.DataFrame(rrows).to_csv(os.path.join(out, "addressable_ranges_v3.csv"), index=False)
    sdf = pd.DataFrame(srows)
    sd = df[df.method == "SPLIT_DATA6"].set_index("column").bits_per_value
    sdf["split_data6_file"] = sdf.column.map(sd)
    sdf.to_csv(os.path.join(out, "shuffle_gap_v3.csv"), index=False)


if __name__ == "__main__":
    main()
