#!/usr/bin/env python3
"""C1: encoder-agnostic structure measure (proposals/18 section H task 1, 2026-10-02).

For every column (22 from A's registry + 2 freshly-materialised unstructured controls),
under (a) the documented bit-field layout where one exists and (b) a partition chosen from the
data alone (flip-probability-gradient rule, structure_common.data_chosen_partition):
  - per-range order-0 empirical entropy (+ Miller-Madow), with a delta-entropy fallback
    estimator for ranges whose raw-value estimate is unreliable at N=524,288;
  - per-range order-1 (adjacent-row) conditional entropy H(X_t | X_{t-1});
  - mutual information between each range and the next range in the same partition.
Also reports the whole-value entropy (same two estimators) for the gain comparison:
  gain = whole_value_entropy_proxy - sum(range_entropy_proxy).
No encoder, no cost model, no SIS anywhere in this script.

Outputs: csv/structure_measure.csv (per range), csv/structure_summary.csv (per column, per
partition source).
"""
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import structure_common as C  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "csv")


def entropy_proxy(h_mm_raw, reliable_raw, h_mm_delta, reliable_delta):
    """Pick the order-0 estimate if reliable (distinct <= N/50), else the delta-entropy
    estimate; flag which was used and whether even that is reliable."""
    if reliable_raw:
        return h_mm_raw, "order0", True
    return h_mm_delta, "delta", bool(reliable_delta)


def range_row(col, source, lo, hi, v, next_v=None):
    width = hi - lo
    rv = C.field(v, lo, hi)
    h0, h0mm, k0, n0, rel0 = C.counts_entropy(rv)
    hd, hdmm, kd, nd, reld = C.delta_entropy(rv)
    proxy, proxy_src, proxy_rel = entropy_proxy(h0mm, rel0, hdmm, reld)
    # order-1 conditional entropy H(X_t|X_{t-1}) = H_joint(X_{t-1},X_t) - H(X_{t-1})
    hj, hjmm, kj, nj, relj = C.joint_entropy(rv[:-1], rv[1:])
    h_cond = hjmm - h0mm
    row = dict(
        column=col, partition_source=source, lo=lo, hi=hi, width=width,
        distinct=k0, distinct_ratio=k0 / len(rv) if len(rv) else 0.0,
        order0_entropy_bits=round(h0, 4), order0_entropy_mm_bits=round(h0mm, 4),
        order0_reliable=rel0,
        delta_entropy_bits=round(hd, 4), delta_entropy_mm_bits=round(hdmm, 4),
        delta_distinct=kd, delta_reliable=reld,
        entropy_proxy_bits=round(proxy, 4), entropy_proxy_source=proxy_src,
        entropy_proxy_reliable=proxy_rel,
        order1_cond_entropy_bits=round(h_cond, 4), order1_joint_distinct=kj,
        order1_reliable=relj,
    )
    if next_v is not None:
        hj2, hj2mm, kj2, nj2, relj2 = C.joint_entropy(rv, next_v)
        mi = h0mm + C.counts_entropy(next_v)[1] - hj2mm
        row["mi_with_next_bits"] = round(mi, 4)
        row["mi_joint_distinct"] = kj2
        row["mi_reliable"] = relj2
    else:
        row["mi_with_next_bits"] = None
        row["mi_joint_distinct"] = None
        row["mi_reliable"] = None
    return row, proxy, proxy_rel


def process_column(name, cfg):
    t0 = time.time()
    v = C.load(name)
    n = len(v)
    p_flip = C.A.flip_profile(v)
    data_partition = C.data_chosen_partition(p_flip)
    doc_layout = cfg.get("layout")
    doc_partition = None
    if doc_layout:
        # layout entries are (field_name, lo, hi); sort by lo, use as-is (documented edges,
        # not necessarily covering [0,64) contiguously -- gaps are reported as their own
        # implicit "undocumented" range so the sum is still exhaustive over 64 bits).
        edges = sorted([(lo, hi) for (_, lo, hi) in doc_layout])
        cuts = sorted(set([0, 64] + [x for e in edges for x in e]))
        doc_partition = [(cuts[i], cuts[i + 1]) for i in range(len(cuts) - 1)]

    rows = []
    summaries = []
    # whole value (one range [0,64)) under both estimators, used as the reference in "gain"
    wv_row, wv_proxy, wv_rel = range_row(name, "whole", 0, 64, v, next_v=None)
    rows.append(wv_row)

    for source, partition in (("documented", doc_partition), ("data", data_partition)):
        if partition is None:
            summaries.append(dict(
                column=name, kind=cfg["kind"], subtype=cfg.get("subtype"), n=n,
                partition_source=source, n_ranges=0, boundaries="",
                whole_value_entropy_proxy_bits=round(wv_proxy, 4),
                whole_value_proxy_source=wv_row["entropy_proxy_source"],
                whole_value_reliable=wv_rel,
                sum_range_entropy_proxy_bits=None, gain_bits=None, available=False,
            ))
            continue
        sum_proxy = 0.0
        all_reliable = True
        for i, (lo, hi) in enumerate(partition):
            next_v = C.field(v, *partition[i + 1]) if i + 1 < len(partition) else None
            row, proxy, rel = range_row(name, source, lo, hi, v, next_v=next_v)
            rows.append(row)
            sum_proxy += proxy
            all_reliable = all_reliable and rel
        summaries.append(dict(
            column=name, kind=cfg["kind"], subtype=cfg.get("subtype"), n=n,
            partition_source=source, n_ranges=len(partition),
            boundaries=";".join(f"[{lo},{hi})" for lo, hi in partition),
            whole_value_entropy_proxy_bits=round(wv_proxy, 4),
            whole_value_proxy_source=wv_row["entropy_proxy_source"],
            whole_value_reliable=wv_rel,
            sum_range_entropy_proxy_bits=round(sum_proxy, 4),
            gain_bits=round(wv_proxy - sum_proxy, 4),
            available=True, all_ranges_reliable=all_reliable,
        ))
    dt = time.time() - t0
    print(f"{name}: {dt:.1f}s", file=sys.stderr)
    return rows, summaries


def main():
    all_rows = []
    all_summaries = []
    for name, cfg in C.ALL_COLUMNS.items():
        rows, summaries = process_column(name, cfg)
        all_rows.extend(rows)
        all_summaries.extend(summaries)
    pd.DataFrame(all_rows).to_csv(os.path.join(OUT, "structure_measure.csv"), index=False)
    pd.DataFrame(all_summaries).to_csv(os.path.join(OUT, "structure_summary.csv"), index=False)
    print("wrote", os.path.join(OUT, "structure_measure.csv"))
    print("wrote", os.path.join(OUT, "structure_summary.csv"))


if __name__ == "__main__":
    main()
