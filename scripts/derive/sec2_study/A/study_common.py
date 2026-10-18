"""Shared loading/column-definition/cost/gate helpers for the Sec. 2 local study (2026-10-01).

Interpreter: EncodingsPlayground/Datasets/.venv/bin/python
"""
import hashlib
import os

import numpy as np

D = "$PROJECT/"

# name -> dict(path, subtype, kind, layout=[(field, lo, hi), ...])
# layout fields are half-open bit ranges [lo, hi) within the 64-bit value, bit 0 = LSB.
COLUMNS = {
    # --- T1: structured, multi-field, order-sensitive composite keys ---
    "snowflake": dict(
        path=f"{D}/Datasets/twitter_snowflake_10M.csv", subtype="T1", kind="structured",
        layout=[("seq", 0, 12), ("worker", 12, 22), ("ts", 22, 63)]),
    "instagram": dict(
        path=f"{D}/Datasets/Instagram/instagram_id_full.txt", subtype="T1", kind="structured",
        layout=[("seq", 0, 10), ("shard", 10, 23), ("ts", 23, 64)]),
    "uuidv7_hi": dict(
        path=f"{D}/pulls/columns_524k/uuidv7_hi.txt", subtype="T1", kind="structured",
        layout=[("rand_a", 0, 12), ("ver", 12, 16), ("ts", 16, 64)]),
    "xmark": dict(
        path=f"{D}/EncodingsPlayground/Datasets/XMark/csv/prepost_id_full.txt", subtype="T1", kind="structured",
        layout=[("post", 0, 28), ("pre", 28, 56), ("level", 56, 64)]),
    "quadkey": dict(
        path=f"{D}/pulls/columns_524k/quadkey_fileorder.txt", subtype="T1", kind="structured",
        layout=[("digits", 0, 30), ("sentinel", 30, 32)]),
    # --- T2: geospatial hierarchical cell ids (digit-structured, near-T1) ---
    "h3_r9": dict(
        path=f"{D}/EncodingsPlayground/Datasets/OSM/csv/h3_r9_fileorder.txt", subtype="T2", kind="structured",
        layout=[("digits", 0, 45), ("base", 45, 52), ("res", 52, 56), ("mode", 56, 64)]),
    "h3_r15": dict(
        path=f"{D}/EncodingsPlayground/Datasets/OSM/csv/h3_r15_fileorder.txt", subtype="T2", kind="structured",
        layout=[("digits", 0, 45), ("base", 45, 52), ("res", 52, 56), ("mode", 56, 64)]),
    "s2_l16": dict(
        path=f"{D}/EncodingsPlayground/Datasets/OSM/csv/s2_l16_fileorder.txt", subtype="T2", kind="structured",
        layout=[("level_bits", 0, 61), ("face", 61, 64)]),
    "s2_l30": dict(
        path=f"{D}/EncodingsPlayground/Datasets/OSM/csv/s2_l30_fileorder.txt", subtype="T2", kind="structured",
        layout=[("level_bits", 0, 61), ("face", 61, 64)]),
    "morton_2x16": dict(
        path=f"{D}/EncodingsPlayground/Datasets/OSM/csv/morton_2x16_fileorder.txt", subtype="T2", kind="structured",
        layout=[("morton", 0, 32)]),
    "morton_2x32": dict(
        path=f"{D}/EncodingsPlayground/Datasets/OSM/csv/morton_2x32_fileorder.txt", subtype="T2", kind="structured",
        layout=[("morton", 0, 64)]),
    # --- T3: near-miss, float-as-fixed-field (sign/exp/mantissa) ---
    "publicbi_drug_cost": dict(
        path=f"{D}/EncodingsPlayground/Datasets/PublicBI/Medicare1/csv/TOTAL_DRUG_COST.txt",
        subtype="T3", kind="near_miss_float_cents", layout=[("value", 0, 30)], float_cents=True),
    "publicbi_drug_cost_ge65": dict(
        path=f"{D}/Datasets/PublicBI_controls_20260929_staged/Medicare1_TOTAL_DRUG_COST_GE65_cents_full.txt",
        subtype="T3", kind="near_miss_float_cents", layout=[("value", 0, 29)]),
    # --- T4: near-miss, low-cardinality / skewed-count measures (no bit layout) ---
    "publicbi_bene_count": dict(
        path=f"{D}/EncodingsPlayground/Datasets/PublicBI/Medicare1/csv/BENE_COUNT.txt",
        subtype="T4", kind="near_miss_measure", layout=None),
    "publicbi_num_employees": dict(
        path=f"{D}/EncodingsPlayground/Datasets/PublicBI/Corporations/csv/num_employees.txt",
        subtype="T4", kind="near_miss_measure", layout=None),
    "publicbi_day_supply_bin": dict(
        path=f"{D}/EncodingsPlayground/Datasets/PublicBI/Medicare1/csv/Avg_Day_Supply_Bene_bin.txt",
        subtype="T4", kind="near_miss_measure", layout=None),
    # --- controls: no documented layout, should NOT be admitted ---
    "uuidv7_lo": dict(
        path=f"{D}/pulls/columns_524k/uuidv7_lo.txt", subtype="control", kind="control",
        layout=None),
    "publicbi_npi": dict(
        path=f"{D}/EncodingsPlayground/Datasets/PublicBI/Medicare1/csv/NPI_full.txt", subtype="control",
        kind="control", layout=None),
    "publicbi_id1": dict(
        path=f"{D}/EncodingsPlayground/Datasets/PublicBI/Corporations/csv/Id1.txt", subtype="control",
        kind="control", layout=None),
    "tpch_orderkey": dict(
        path=f"{D}/EncodingsPlayground/Datasets/TPCH/csv/orderkey.txt", subtype="control", kind="control",
        layout=None),
    "inat_species_id": dict(
        path=f"{D}/EncodingsPlayground/Datasets/iNaturalist_csv/species_id.txt", subtype="control",
        kind="control", layout=None),
    "ipv4_id": dict(
        path=f"{D}/EncodingsPlayground/Datasets/IPv4/csv/ipv4_id.txt", subtype="control", kind="control",
        layout=None),
}

# documented T1 class: multi-field, timestamp/order bearing composite keys
T1_NAMES = ["snowflake", "instagram", "uuidv7_hi", "xmark", "quadkey"]

SORTED_VARIANTS = {
    "h3_r9": f"{D}/EncodingsPlayground/Datasets/OSM/csv/h3_r9_sorted.txt",
    "h3_r15": f"{D}/EncodingsPlayground/Datasets/OSM/csv/h3_r15_sorted.txt",
    "s2_l16": f"{D}/EncodingsPlayground/Datasets/OSM/csv/s2_l16_sorted.txt",
    "s2_l30": f"{D}/EncodingsPlayground/Datasets/OSM/csv/s2_l30_sorted.txt",
    "morton_2x16": f"{D}/EncodingsPlayground/Datasets/OSM/csv/morton_2x16_sorted.txt",
    "morton_2x32": f"{D}/EncodingsPlayground/Datasets/OSM/csv/morton_2x32_sorted.txt",
}

# labels for G1 classifier: True = documented structured layout (should be admitted)
LABELS = {name: (c["kind"] == "structured") for name, c in COLUMNS.items()}


def sha256_prefix(path, n=12, nbytes=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(nbytes))
    return h.hexdigest()[:n]


def sha256_full(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_raw(path, n=None, float_cents=False):
    """Load first token per line as python ints -> np.uint64 array, in file order.
    float_cents=True: parse as float64, round(x*100) -> int (matches provenance doc's
    fixed-point-cents conversion for TOTAL_DRUG_COST).
    """
    vals = []
    with open(path, "r") as f:
        for i, line in enumerate(f):
            if n is not None and i >= n:
                break
            line = line.strip()
            if not line:
                continue
            tok = line.split()[0].split(",")[0]
            if float_cents:
                vals.append(int(round(float(tok) * 100)))
            else:
                vals.append(int(tok))
    return np.array(vals, dtype=np.uint64)


def load(name, n=524288):
    cfg = COLUMNS[name]
    return load_raw(cfg["path"], n=n, float_cents=cfg.get("float_cents", False))


def load_full(name):
    cfg = COLUMNS[name]
    return load_raw(cfg["path"], n=None, float_cents=cfg.get("float_cents", False))


def bits_matrix(values):
    """uint64 array (N,) -> uint8 matrix (N, 64), bit 0 = LSB at column 0."""
    v = values.astype(np.uint64)
    out = np.zeros((v.shape[0], 64), dtype=np.uint8)
    for b in range(64):
        out[:, b] = ((v >> np.uint64(b)) & np.uint64(1)).astype(np.uint8)
    return out


def flip_profile(values):
    """p[b] = fraction of adjacent rows where bit b differs. len 64, index b=0..63 (LSB..MSB)."""
    if len(values) < 2:
        return np.zeros(64)
    bm = bits_matrix(values)
    diff = (bm[1:] != bm[:-1]).mean(axis=0)
    return diff


def field(v, lo, hi):
    v = v.astype(np.uint64)
    width = hi - lo
    mask = np.uint64((1 << width) - 1) if width < 64 else np.uint64(0xFFFFFFFFFFFFFFFF)
    return (v >> np.uint64(lo)) & mask


# ---------------- gate (mirrors paper-repo/eval_figures/c3_bitflip_admission/gates.py) ----------------

def h_bin(p):
    q = np.clip(p, 1e-12, 1 - 1e-12)
    e = -(q * np.log2(q) + (1 - q) * np.log2(1 - q))
    return np.where((p <= 0) | (p >= 1), 0.0, e)


def gate_features(p, k=2.0):
    g = np.zeros_like(p)
    g[1:] = np.abs(np.diff(p))
    thr = g[1:].mean() + k * g[1:].std()
    return dict(boundaries=int((g[1:] > thr).sum()), maxg=float(g.max()), var=float(p.var()),
                ent=float(h_bin(p).mean()), active=int((p > 0).sum()))


def gradient_gate(f, minb=1, ming=0.005):
    return f["boundaries"] >= minb and f["maxg"] >= ming


def active_entropy(p, varying=None):
    a = p > 0 if varying is None else varying
    return float(h_bin(p[a]).mean()) if a.any() else 0.0


ENTROPY_MAX = 0.8  # shipped constant: c3_bitflip_admission/plot_c3_profiles.py:20, evaluate.py:39


def gate_decision(p, k=2.0, entropy_max=ENTROPY_MAX):
    """Mirrors the shipped admission test: gradient_gate(features(p)) AND active_entropy(p) <= 0.8
    (c3_bitflip_admission/plot_c3_profiles.py:20; gates.py admits()/gradient_gate()/active_entropy())."""
    f = gate_features(p, k=k)
    ent = active_entropy(p, varying=p > 0)
    ok = gradient_gate(f) and (entropy_max is None or ent <= entropy_max)
    f["active_entropy"] = ent
    return ok, f


# ---------------- closed-form per-section/per-field costs (bits/value), block = 65536 rows ----------------
# Nimble-style small constant per-section header; TODO exact header bytes per Sec. 4.2 cost models
# (plan D: "header bytes as in Nimble: TODO read from the Sec. 4.2 cost models").
HEADER_BITS_PER_SECTION = 32.0  # TODO placeholder, documented in README


def cost_constant(vals):
    n = len(vals)
    if n == 0:
        return 0.0
    return HEADER_BITS_PER_SECTION / n if (vals == vals[0]).all() else np.inf


def cost_for(vals):
    n = len(vals)
    if n == 0:
        return 0.0
    rng = int(vals.max()) - int(vals.min())
    width = max(1, int(rng).bit_length())
    return (HEADER_BITS_PER_SECTION + width * n) / n


def cost_dict(vals):
    n = len(vals)
    if n == 0:
        return 0.0
    distinct = np.unique(vals)
    k = len(distinct)
    if k >= n:
        return np.inf
    idx_width = max(1, (k - 1).bit_length())
    dict_bits = int(distinct.max()).bit_length() if len(distinct) else 1
    dict_bits = max(1, dict_bits)
    return (HEADER_BITS_PER_SECTION + k * dict_bits + idx_width * n) / n


def cost_rle(vals):
    n = len(vals)
    if n == 0:
        return 0.0
    change = np.empty(n, dtype=bool)
    change[0] = True
    change[1:] = vals[1:] != vals[:-1]
    runs = int(change.sum())
    val_bits = max(1, int(vals.max()).bit_length()) if n else 1
    len_bits = max(1, int(n).bit_length())
    return (HEADER_BITS_PER_SECTION + runs * (val_bits + len_bits)) / n


def cost_delta_for(vals):
    n = len(vals)
    if n < 2:
        return cost_for(vals)
    v = vals.astype(np.int64)
    d = np.diff(v)
    rng = int(d.max()) - int(d.min()) if n > 1 else 0
    width = max(1, int(rng).bit_length())
    first_bits = max(1, int(vals[0]).bit_length())
    return (HEADER_BITS_PER_SECTION + first_bits + width * (n - 1)) / n


def best_whole_cost(vals):
    """C(x): min closed-form whole-value cost across the 5 candidate encodings, bits/value."""
    costs = {
        "constant": cost_constant(vals), "for": cost_for(vals), "dict": cost_dict(vals),
        "rle": cost_rle(vals), "delta_for": cost_delta_for(vals),
    }
    best = min(costs, key=costs.get)
    return costs[best], best, costs


def documented_field_cost(vals, layout):
    """D_doc: sum of best per-field closed-form costs over the documented partition, bits/value."""
    total = 0.0
    per_field = {}
    for name, lo, hi in layout:
        fv = field(vals, lo, hi)
        c, which, _ = best_whole_cost(fv)
        per_field[name] = (c, which)
        total += c
    return total, per_field


def dp_optimal_partition(vals, max_ranges=None):
    """D_opt: DP over contiguous bit ranges [0,64) choosing a partition minimizing
    sum of best_whole_cost(field) + a per-section header, dynamic-programming over
    breakpoints at bit boundaries 0..64 (65 candidate cut points -> up to 2080
    contiguous ranges, matches plan's '2,080 contiguous ranges of a 65,536-row block').
    Returns (G_opt bits/value relative to best_whole_cost(vals), boundary bit list, D_opt).
    """
    # cost of every contiguous range [lo,hi)
    range_cost = {}
    for lo in range(64):
        for hi in range(lo + 1, 65):
            fv = field(vals, lo, hi)
            c, _, _ = best_whole_cost(fv)
            range_cost[(lo, hi)] = c
    # DP: dp[hi] = min total cost to cover [0,hi)
    INF = float("inf")
    dp = [INF] * 65
    dp[0] = 0.0
    back = [None] * 65
    for hi in range(1, 65):
        for lo in range(hi):
            c = dp[lo] + range_cost[(lo, hi)]
            if c < dp[hi]:
                dp[hi] = c
                back[hi] = lo
    # reconstruct boundaries
    bounds = []
    cur = 64
    while cur > 0:
        bounds.append(cur)
        cur = back[cur]
    bounds.append(0)
    bounds = sorted(set(bounds))
    return dp[64], bounds


def gain_bits(whole_cost, doc_or_opt_cost):
    """G = whole-value cost minus field-partitioned cost, bits/value (positive = fields win)."""
    return whole_cost - doc_or_opt_cost
