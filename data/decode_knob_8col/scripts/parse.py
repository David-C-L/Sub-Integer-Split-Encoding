#!/usr/bin/env python3
"""Parses a decode-knob result dir into one row per (dataset, tag, rows, arm)."""
import csv, glob, os, re, sys, statistics as st
from collections import defaultdict
d = sys.argv[1]
rows = defaultdict(dict)

def plan_from_log(path, arm):
    secs = []; sel = False; nodes = False; enc_of = {}
    for line in open(path, errors='replace'):
        if line.startswith('  --- '):
            sel = line.startswith(f'  --- {arm} encoding tree'); nodes = line.startswith(f'  --- {arm} encoding nodes'); continue
        if sel:
            m = re.match(r'^  \[(\d+)\.\.(\d+)\]', line)
            if m: secs.append((int(m.group(1)), int(m.group(2))))
        if nodes:
            p = line.rstrip('\n').split('\t')
            if len(p) >= 6 and p[0] == '1':
                enc_of[int(p[2])] = (p[3], int(p[5]))
            if len(p) >= 6 and p[0] == '0':
                top = p[3]
    out = []
    for i, (a, b) in enumerate(secs):
        e, by = enc_of.get(i, ('?', 0)); out.append((a, b, e, by))
    return out

for f in glob.glob(os.path.join(d, 'comp_*.csv')):
    m = re.match(r'comp_(.+?)_((?:w0|[A-Z]\w*?))_n(\d+)\.csv$', os.path.basename(f))
    if not m: continue
    n, tag, nr = m.groups()
    for r in csv.DictReader(open(f)):
        k = (n, tag, r['encoding'])
        rows[k][f'bytes_{nr}'] = int(float(r['payload_bytes']))
        if int(nr) == 524288:
            plan = plan_from_log(f + '.log', r['encoding'])
            rows[k]['plan'] = ';'.join(f'{a}-{b}:{e}' for a, b, e, _ in plan)
            rows[k]['sections'] = len(plan)
            rows[k]['read_sections'] = sum(1 for p in plan if p[2] != 'Constant')
acc = defaultdict(list)
for drv, col in (('point', 'ns_per_probe'), ('range', 'time_ns'), ('bulk', 'time_ns')):
    for f in glob.glob(os.path.join(d, f'{drv}_*.csv')):
        m = re.match(drv + r'_(.+?)_((?:w0|[A-Z]\w*?))_r(\d+)\.csv$', os.path.basename(f))
        if not m: continue
        n, tag, rep = m.groups()
        for r in csv.DictReader(open(f)):
            arm = r['encoding'].replace('+view', '')
            if r.get('skipped', '0') != '0': acc[(n, tag, arm, 'skipped')].append(1); continue
            acc[(n, tag, arm, drv)].append((rep, float(r[col])))
            if drv == 'point' and r.get('build_ns'):
                acc[(n, tag, arm, 'open')].append(float(r['build_ns']) / 1e6); acc[(n, tag, arm, 'resident')].append(float(r['resident_bytes']))
            acc[(n, tag, arm, 'tbytes')].append(int(float(r['payload_bytes'])))
            if 'validated' in r: acc[(n, tag, arm, 'validated')].append(int(r['validated']))
for f in glob.glob(os.path.join(d, 'cold_*.csv')):
    m = re.match(r'cold_(.+?)_((?:w0|[A-Z]\w*?))_r(\d+)\.csv$', os.path.basename(f))
    if not m: continue
    n, tag, rep = m.groups()
    for r in csv.DictReader(open(f)):
        if r.get('skipped', '0') != '0': continue
        arm = r['encoding'].replace('+view+ctor', '').replace('+view+cold', '')
        acc[(n, tag, arm, 'cold')].append(float(r['time_ns']) / 1e6)
        acc[(n, tag, arm, 'validated')].append(int(r['validated']))
for f in glob.glob(os.path.join(d, 'gather_*.csv')):
    m = re.match(r'gather_(.+?)_((?:w0|[A-Z]\w*?))_r(\d+)\.csv$', os.path.basename(f))
    if not m: continue
    n, tag, rep = m.groups()
    for r in csv.DictReader(open(f)):
        if r.get('skipped', '0') != '0': continue
        acc[(n, tag, r['encoding'].replace('+view', ''), 'gather')].append(float(r['time_ns']) / float(r['selected_rows']))
        acc[(n, tag, r['encoding'].replace('+view', ''), 'validated')].append(int(r['validated']))
for f in glob.glob(os.path.join(d, 'enc_*.csv')):
    m = re.match(r'enc_(.+?)_((?:w0|[A-Z]\w*?))_r(\d+)\.csv$', os.path.basename(f))
    if not m: continue
    n, tag, rep = m.groups()
    for r in csv.DictReader(open(f)):
        if r.get('skipped', '0') != '0': continue
        acc[(n, tag, r['encoding'], 'enc')].append(float(r['time_ns']) / 1e6)
        acc[(n, tag, r['encoding'], 'validated')].append(int(r['validated']))
for f in glob.glob(os.path.join(d, 'plan_*.csv.log')):
    m = re.match(r'plan_(.+?)_((?:w0|[A-Z]\w*?))_r(\d+)\.csv\.log$', os.path.basename(f))
    if not m: continue
    n, tag, rep = m.groups()
    for line in open(f, errors='replace'):
        mm = re.match(r'planner_ms dataset=\S+ median=(\S+) .* weight=(\S+)', line)
        if mm:
            acc[(n, tag, 'SIS/realNested', 'plan')].append(float(mm.group(1)))
            acc[(n, tag, 'SIS/realNested', 'weight')].append(float(mm.group(2)))
for (n, tag, arm, what), v in acc.items():
    k = (n, tag, arm)
    if what in ('point', 'range', 'bulk'):
        # Median within a repeat (a range run has one row per offset), then across repeats.
        per = defaultdict(list)
        for rep, val in v: per[rep].append(val)
        v = [st.median(x) for x in per.values()]
    if what in ('point', 'range', 'bulk'): rows[k]['reps'] = len(v)
    if what == 'point': rows[k]['point_ns'] = st.median(v); rows[k]['point_spread'] = (max(v) - min(v)) / st.median(v)
    elif what == 'range': rows[k]['range64_ns'] = st.median(v); rows[k]['range_spread'] = (max(v) - min(v)) / st.median(v)
    elif what == 'bulk': rows[k]['bulk_ms'] = st.median(v) / 1e6; rows[k]['bulk_spread'] = (max(v) - min(v)) / st.median(v)
    elif what == 'open': rows[k]['view_open_ms'] = st.median(v)
    elif what == 'resident': rows[k]['view_resident_bytes'] = st.median(v)
    elif what == 'cold': rows[k]['open_plus_first_bulk_ms'] = st.median(v)
    elif what == 'gather': rows[k]['gather_ns_per_row'] = st.median(v)
    elif what == 'enc': rows[k]['encode_ms'] = st.median(v)
    elif what == 'plan': rows[k]['planner_ms'] = st.median(v)
    elif what == 'weight': rows[k]['resolved_weight'] = v[0]
    elif what in ('point', 'range', 'bulk') and False: pass
    elif what == 'tbytes': rows[k]['timed_bytes'] = v[0]; rows[k]['timed_bytes_same'] = int(len(set(v)) == 1)
    elif what == 'validated': rows[k]['validated'] = min(v)
    elif what == 'skipped': rows[k]['skipped'] = len(v)
cols = ['dataset', 'tag', 'arm', 'bytes_524288', 'timed_bytes', 'timed_bytes_same', 'bytes_full', 'sections', 'read_sections', 'point_ns', 'range64_ns', 'bulk_ms', 'open_plus_first_bulk_ms', 'gather_ns_per_row', 'view_open_ms', 'view_resident_bytes', 'encode_ms', 'planner_ms', 'resolved_weight', 'reps', 'point_spread', 'range_spread', 'bulk_spread', 'validated', 'skipped', 'plan']
w = csv.writer(sys.stdout); w.writerow(cols)
for k in sorted(rows):
    r = rows[k]
    full = [v for kk, v in r.items() if kk.startswith('bytes_') and kk != 'bytes_524288']
    r['bytes_full'] = full[0] if full else ''
    w.writerow(list(k) + [r.get(c, '') for c in cols[3:]])
