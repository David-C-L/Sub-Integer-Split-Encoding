"""Summarise the 10,000,000-row tab:eval_planner_gap rerun (data/planner_gap_10m/).

Same reductions as summarise_plan_decode.py (bits from the comp CSV, sections from the dumped encoding tree,
point = per-rep median over probes rows then median over reps) plus planning time: median of the
[plan-time] lines (compression driver --mlidc_sis_plan_time_reps for default/re-priced, cost-model oracle
--plan_time_reps for encoded; warm-ups, rep < 0, dropped). Writes summary.csv. Usage: summarise_planner_gap_10m.py [dir]
"""
import csv, glob, os, re, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'data', 'planner_gap_10m')
O = os.path.join(P, 'out')
kv = re.compile(r'(\w+)=(\S+)')


def arm(r):
    return r['encoding'].replace('pinned', r['variant'].replace('_view', '')) if 'pinned' in r['encoding'] else r['encoding']


rows = []
for n in ['snowflake', 'osm_h3_r9_fileorder']:
    bits, secs, val = {}, {}, {}
    for f in glob.glob(f'{O}/comp_{n}_*.csv'):
        lab = f.split(f'comp_{n}_')[1][:-4]
        for r in csv.DictReader(open(f)):
            if r['skipped'] == '0':
                bits[arm(r)] = float(r['bits_per_elem'])
                val.setdefault(arm(r), set()).add(r['validated'])
        for a, s in re.findall(r'--- (\S+) encoding tree ---\n\S+ sections=(\d+)', open(f[:-4] + '.log').read()):
            secs[a.replace('pinned', lab) if 'pinned' in a else a] = int(s)
    M = {}
    for f in glob.glob(f'{O}/point_{n}_*_r*.csv'):
        rep = f.rsplit('_r', 1)[1][:-4]
        for r in csv.DictReader(open(f)):
            if r['skipped'] != '0':
                continue
            val.setdefault(arm(r), set()).add(r['validated'])
            M.setdefault(arm(r), {}).setdefault(rep, []).append(float(r['ns_per_probe']))
    point = {a: st.median(st.median(x) for x in v.values()) for a, v in M.items()}
    T = {}
    for f in [f'{O}/plantime_{n}.log', f'{O}/oracle_{n}.log']:
        if not os.path.exists(f):
            continue
        for line in open(f):
            if '[plan-time]' in line:
                d = dict(kv.findall(line))
                if int(d['rep']) >= 0:
                    T.setdefault(d['arm'], []).append(float(d['plan_ms']))
    for a in ['SIS/realNested+view', 'SIS/hybrid+view', 'SIS/oracle_dp_selection+view']:
        t = T.get(a.replace('+view', ''), [])
        rows.append(dict(dataset=n, arm=a, sections=secs.get(a), bits_per_value=round(bits[a], 4) if a in bits else '',
                         point_ns_per_probe=round(point[a], 1) if a in point else '',
                         point_reps=len(M.get(a, {})), plan_ms_median=round(st.median(t), 3) if t else '',
                         plan_ms_min=round(min(t), 3) if t else '', plan_ms_max=round(max(t), 3) if t else '',
                         plan_reps=len(t), validated_all=val.get(a) == {'1'}))
with open(os.path.join(P, 'summary.csv'), 'w', newline='') as out:
    w = csv.DictWriter(out, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(open(os.path.join(P, 'summary.csv')).read())
