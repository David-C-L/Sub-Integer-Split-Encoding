#!/usr/bin/env python3
"""Claims check for the TopLevel budget sweep: violations, ratios, monotonicity, encode time.
Usage: analyse.py sweep_measurements.csv"""
import csv, sys
R = list(csv.DictReader(open(sys.argv[1])))
by = {(r['dataset'], r['tag']): r for r in R}
B = ['0', '0p01', '0p02', '0p03', '0p04', '0p05', '0p075', '0p1', '0p15', '0p25', '0p5', '1']
print('rows', len(R), 'validated', all(r['validated'] == '1' for r in R), 'skipped', sum(1 for r in R if r['skipped']),
      'reps', sorted({r['reps'] for r in R}), 'timed_bytes_same', all(r['timed_bytes_same'] in ('1', '') for r in R))
for d in ('snowflake', 'osm_s2_l30_fileorder', 'osm_h3_r9_fileorder'):
    b = by[(d, 'w0')]
    print(f"\n## {d}: baseline {b['bytes_full']} / {b['bytes_524288']} B, read sections {b['read_sections']}, "
          f"point {float(b['point_ns']):.0f} ns, range64 {float(b['range64_ns']):.0f} ns, bulk {float(b['bulk_ms']):.2f} ms, "
          f"open+first {float(b['open_plus_first_bulk_ms']):.1f} ms, encode {float(b['encode_ms']):.0f} ms, planner {float(b['planner_ms']):.1f} ms")
    print(f"   plan: {b['plan']}")
    viol = []; prev = None; downs = []
    for bb in B:
        r = by[(d, 'B_b' + bb)]; lim = float(bb.replace('p', '.'))
        sp = int(r['bytes_524288']) / int(b['bytes_524288']) - 1; sf = int(r['bytes_full']) / int(b['bytes_full']) - 1
        if sp > lim + 1e-12: viol.append((bb, 'prefix', sp))
        if sf > lim + 1e-12: viol.append((bb, 'full', sf))
        x = {c: float(b[c]) / float(r[c]) for c in ('point_ns', 'range64_ns', 'bulk_ms', 'open_plus_first_bulk_ms')}
        if prev:
            for c in x:
                if x[c] < prev[1][c] * 0.95: downs.append(f"{c} {prev[0]}->{bb}: {prev[1][c]:.2f}->{x[c]:.2f} (plan {'same' if prev[2] == r['plan'] else 'changed'})")
        prev = (bb, x, r['plan'])
        print(f"   {lim*100:g}% | full {sf*100:+.1f}% | prefix {sp*100:+.1f}% | sec {r['read_sections']} | pt {x['point_ns']:.2f} | rg {x['range64_ns']:.2f} | "
              f"bulk {x['bulk_ms']:.2f} | open+1st {x['open_plus_first_bulk_ms']:.2f} | enc {float(r['encode_ms'])/float(b['encode_ms']):.1f}x | "
              f"plan {float(r['planner_ms']):.1f} ms | spread pt/rg/bk {float(r['point_spread']):.2f}/{float(r['range_spread']):.2f}/{float(r['bulk_spread']):.2f} | {r['plan']}")
    print('   violations:', viol or 'none')
    print('   steps down >5%:', downs or 'none')
