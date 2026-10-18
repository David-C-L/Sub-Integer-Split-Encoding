"""Summarise the planning-time run (data/plan_time/) for tab:eval_planner_gap.

Reads the [plan-time] lines the compression driver (--mlidc_sis_plan_time_reps)
and the cost-model oracle driver (--plan_time_reps) print, writes every timed
run to raw_plan_time.csv and one row per (column, planner, rows, sample) to
summary.csv, and checks sizes and plans against the planner-gap run
(toplevel_sec7/plan_decode). Usage: summarise_plan_time.py [data/plan_time]
"""
import csv
import glob
import os
import re
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'data', 'plan_time')
REF = os.path.join(P, '..', 'toplevel_sec7', 'plan_decode')
CONFIG = {'SIS/realNested': 'default', 'SIS/hybrid': 're-priced',
          'SIS/oracle_dp_selection': 'encoded'}

# Reference sizes and plans of the planner-gap run.
ref_bits = {}
for r in csv.DictReader(open(os.path.join(REF, 'summary.csv'))):
    ref_bits[(r['dataset'], r['arm'])] = float(r['bits_per_value'])
ref_plan = {}
for f in glob.glob(os.path.join(REF, 'plans', 'plans_*.tsv')):
    ds = os.path.basename(f)[len('plans_'):-len('.tsv')]
    for r in csv.DictReader(open(f), delimiter='\t'):
        ref_plan[(ds, r['label'])] = r['boundaries']
ref_plan_arm = {'SIS/realNested': 'writer', 'SIS/oracle_dp_selection': 'oracle_dp_selection'}

kv = re.compile(r'(\w+)=(\S+)')
raw = []
# out/: the measurement; out_rowframe_off/: the same arms with --mlidc_sis_row_frame=false,
# to attribute the row-count-dependent part of planning (bytes are identical on both columns).
comp_logs = [(f, 'on') for f in sorted(glob.glob(os.path.join(P, 'out', 'comp_*.log')))]
comp_logs += [(f, 'off') for f in sorted(glob.glob(os.path.join(P, 'out_rowframe_off', 'comp_*.log')))]
for f, frame in comp_logs:
    rows = int(f.rsplit('_', 1)[1][:-4])
    for line in open(f):
        if '[plan-time]' not in line:
            continue
        d = dict(kv.findall(line))
        d['plan'] = line.split(' plan=', 1)[1].strip()
        raw.append({'dataset': d['dataset'], 'arm': d['arm'], 'rows': rows, 'row_frame': frame,
                    'sample_size': 2048, 'rep': int(d['rep']),
                    'plan_ms': float(d['plan_ms']), 'encode_ms': float(d['encode_ms']),
                    'observer_calls': int(d['observer_calls']), 'encodes': '',
                    'bytes': int(d['bytes']), 'plan': d['plan']})
oracle_bytes = {}
for f in sorted(glob.glob(os.path.join(P, 'out', 'oracle_*.log'))):
    rows = int(f.rsplit('_', 1)[1][:-4])
    for line in open(f):
        if '[plan-time' not in line:
            continue
        d = dict(kv.findall(line))
        plan = line.split(' plan=', 1)[1].strip()
        if '[plan-time-bytes]' in line:
            oracle_bytes[(d['dataset'], rows, int(d['sample_size']))] = (int(d['bytes']), plan)
            continue
        raw.append({'dataset': d['dataset'], 'arm': d['arm'], 'rows': rows, 'row_frame': 'on',
                    'sample_size': int(d['sample_size']), 'rep': int(d['rep']),
                    'plan_ms': float(d['plan_ms']), 'encode_ms': '', 'observer_calls': '',
                    'encodes': int(d['encodes']), 'bytes': '', 'plan': plan})
for r in raw:
    if r['bytes'] == '' and (r['dataset'], r['rows'], r['sample_size']) in oracle_bytes:
        r['bytes'] = oracle_bytes[(r['dataset'], r['rows'], r['sample_size'])][0]

fields = ['dataset', 'config', 'arm', 'rows', 'row_frame', 'sample_size', 'rep', 'plan_ms', 'encode_ms',
          'observer_calls', 'encodes', 'bytes', 'plan']
with open(os.path.join(P, 'raw_plan_time.csv'), 'w', newline='') as out:
    w = csv.DictWriter(out, fieldnames=fields)
    w.writeheader()
    for r in raw:
        w.writerow(dict(r, config=CONFIG[r['arm']]))

# Arm sizes from the drivers' normal (unobserved) encode, for the identity check.
csv_bits = {}
for f, frame in comp_logs:
    rows = int(f.rsplit('_', 1)[1][:-4])
    for r in csv.DictReader(open(f[:-4] + '.csv')):
        if r['skipped'] == '0':
            csv_bits[(r['dataset'], r['encoding'], rows, frame)] = (int(r['payload_bytes']), float(r['bits_per_elem']))


def q(v, p):
    v = sorted(v)
    k = (len(v) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


groups = {}
for r in raw:
    if r['rep'] < 0:  # warm-ups
        continue
    groups.setdefault((r['dataset'], r['arm'], r['rows'], r['row_frame'], r['sample_size']), []).append(r)
summary = []
for (ds, arm, rows, frame, sample), rs in sorted(groups.items()):
    t = [r['plan_ms'] for r in rs]
    plans = {r['plan'] for r in rs}
    row = {'dataset': ds, 'config': CONFIG[arm], 'arm': arm, 'rows': rows, 'row_frame': frame,
           'sample_size': sample,
           'reps': len(rs), 'plan_ms_median': st.median(t), 'plan_ms_min': min(t),
           'plan_ms_max': max(t), 'plan_ms_q1': q(t, 0.25), 'plan_ms_q3': q(t, 0.75),
           'plans_distinct': len(plans), 'plan': sorted(plans)[0]}
    if rs[0]['encode_ms'] != '':
        e = [r['encode_ms'] for r in rs]
        row['encode_ms_median'] = st.median(e)
        row['plan_share_of_encode_median'] = st.median(r['plan_ms'] / r['encode_ms'] for r in rs)
        row['observer_calls'] = '/'.join(sorted({str(r['observer_calls']) for r in rs}))
        timed_bytes = {r['bytes'] for r in rs}
        normal = csv_bits.get((ds, arm, rows, frame))
        row['bytes'] = normal[0] if normal else ''
        row['bits_per_value'] = normal[1] if normal else ''
        row['timed_encode_bytes_equal'] = normal is not None and timed_bytes == {normal[0]}
    else:
        b = oracle_bytes.get((ds, rows, sample))
        row['bytes'] = b[0] if b else ''
        row['bits_per_value'] = b[0] * 8 / rows if b else ''
        row['encodes_per_run'] = rs[0]['encodes']
    if rows == 524288 and frame == 'on' and (arm != 'SIS/oracle_dp_selection' or sample == 524288):
        ref = ref_bits.get((ds, arm))
        row['ref_bits_per_value'] = ref
        row['bits_match_ref'] = ref is not None and round(row['bits_per_value'], 4) == round(ref, 4)
        if arm in ref_plan_arm:
            rp = ref_plan.get((ds, ref_plan_arm[arm]))
            row['plan_matches_ref'] = rp is not None and row['plan'].split(' ')[0] == rp
    summary.append(row)

cols = ['dataset', 'config', 'arm', 'rows', 'row_frame', 'sample_size', 'reps', 'plan_ms_median', 'plan_ms_min',
        'plan_ms_max', 'plan_ms_q1', 'plan_ms_q3', 'encode_ms_median', 'plan_share_of_encode_median',
        'observer_calls', 'encodes_per_run', 'bytes', 'bits_per_value', 'timed_encode_bytes_equal',
        'ref_bits_per_value', 'bits_match_ref', 'plan_matches_ref', 'plans_distinct', 'plan']
with open(os.path.join(P, 'summary.csv'), 'w', newline='') as out:
    w = csv.DictWriter(out, fieldnames=cols)
    w.writeheader()
    for row in summary:
        w.writerow({k: (f'{v:.4f}' if isinstance(v, float) else v) for k, v in row.items()})

# The table cells: 524,288 rows; encoded on the whole column, as the table's plan was chosen.
print('column,config,median_ms,min_ms,max_ms,q1_ms,q3_ms,ratio_vs_default,share_of_encode,bits_match')
for ds in ['snowflake', 'osm_h3_r9_fileorder']:
    cells = {r['config']: r for r in summary if r['dataset'] == ds and r['rows'] == 524288
             and r['row_frame'] == 'on' and (r['config'] != 'encoded' or r['sample_size'] == 524288)}
    base = cells['default']['plan_ms_median']
    for c in ['default', 're-priced', 'encoded']:
        r = cells[c]
        share = r.get('plan_share_of_encode_median', '')
        print(f"{ds},{c},{r['plan_ms_median']:.3f},{r['plan_ms_min']:.3f},{r['plan_ms_max']:.3f},"
              f"{r['plan_ms_q1']:.3f},{r['plan_ms_q3']:.3f},{r['plan_ms_median'] / base:.2f},"
              f"{share if share == '' else f'{share:.3f}'},{r.get('bits_match_ref', '')}")
