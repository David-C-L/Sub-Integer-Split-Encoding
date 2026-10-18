import csv,sys,io
t=open(sys.argv[1]).read(); t=t[t.index('dataset,tag'):]
R=list(csv.DictReader(io.StringIO(t))); by={(r['dataset'],r['arm'],r['tag']):r for r in R}
ds=['snowflake','osm_h3_r9_fileorder','osm_s2_l30_fileorder','bing_quadkey','xmark_prepost_full','uuidv7_hi','publicbi_npi','publicbi_id1']
sh=dict(zip(ds,['Snowflake','OSM H3','OSM S2','Bing','XMark','UUIDv7 hi','NPI','Id1']))
def x(r,b,c):
    try: return float(b[c])/float(r[c])
    except: return float('nan')
def szf(r,b): return 100*(int(r['bytes_full'])/int(b['bytes_full'])-1) if r['bytes_full'] and b['bytes_full'] else float('nan')
def szp(r,b): return 100*(int(r['bytes_524288'])/int(b['bytes_524288'])-1)
print('validated', all(r['validated']=='1' for r in R if r['validated']), 'rows', len(R), 'reps', sorted({r['reps'] for r in R}), 'skipped', sum(1 for r in R if r['skipped']))
tags=sorted({r['tag'] for r in R if r['tag']!='w0'}, key=lambda t:(t.split('_b')[1], t))
names={'M_P':'point 1','M_P3B1':'point 0.75 / bulk 0.25','M_P1B1':'point 0.5 / bulk 0.5','M_P1B3':'point 0.25 / bulk 0.75','M_B':'bulk 1','G_P':'point 1, guard 1.1','G_P1B1':'0.5 / 0.5, guard 1.1'}
for arm in ('SIS/realNested','SIS/hybrid'):
    print(f'\n### {arm}: per mix and budget')
    print('| mix | budget | worst point | worst range-64 | worst bulk (repeat) | worst open+first bulk | columns >=1.3x point | >=1.3x range | >=1.3x bulk | max size, prefix | max size, full | median encode x | max encode x |')
    for tag in tags:
        m,b=tag.rsplit('_b',1)
        P=[];Rg=[];Bk=[];Cd=[];S5=[];SF=[];En=[]
        for d in ds:
            base=by[(d,arm,'w0')]; r=by[(d,arm,tag)]
            P.append((x(r,base,'point_ns'),sh[d])); Rg.append((x(r,base,'range64_ns'),sh[d])); Bk.append((x(r,base,'bulk_ms'),sh[d])); Cd.append((x(r,base,'open_plus_first_bulk_ms'),sh[d]))
            S5.append(szp(r,base)); SF.append(szf(r,base)); En.append(x(base,r,'encode_ms'))
        w=lambda v: '%.2fx (%s)'%min(v)
        import statistics as st
        print(f"| {names[m]} | {b.replace('p','.')} | {w(P)} | {w(Rg)} | {w(Bk)} | {w(Cd)} | {sum(1 for v,_ in P if v>=1.3)} | {sum(1 for v,_ in Rg if v>=1.3)} | {sum(1 for v,_ in Bk if v>=1.3)} | {max(S5):+.1f}% | {max(SF):+.1f}% | {st.median(En):.1f} | {max(En):.1f} |")
if len(sys.argv)>2:
  for arm in ('SIS/realNested','SIS/hybrid'):
    for tag in sys.argv[2:]:
        print(f'\n### {arm} {tag}')
        for d in ds:
            b=by[(d,arm,'w0')]; r=by[(d,arm,tag)]
            pm=f"{float(b['planner_ms']):.1f} -> {float(r['planner_ms']):.1f}" if r['planner_ms'] else 'n/a'
            print(f"| {sh[d]} | {szf(r,b):+.1f}% | {szp(r,b):+.1f}% | {b['read_sections']} -> {r['read_sections']} | {x(r,b,'point_ns'):.2f}x | {x(r,b,'range64_ns'):.2f}x | {x(r,b,'bulk_ms'):.2f}x | {x(r,b,'open_plus_first_bulk_ms'):.2f}x | {x(b,r,'encode_ms'):.1f}x | {pm} | {r['plan'].replace('FrequencyPartition','FP').replace('MainlyConstant','MC').replace('BlockBitPacking','BBP').replace('Constant','C').replace('FixedBitWidth','FBW').replace('Dictionary','Dict').replace('Trivial','Tr').replace('SimdForBitpack','SFB')} |")
