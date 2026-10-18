import csv,glob,statistics as st,math,re
import sys; P=sys.argv[1]
def arm(r):
    return r['encoding'].replace('pinned',r['variant'].replace('_view','')) if 'pinned' in r['encoding'] else r['encoding']
out=open(P+'/summary.csv','w'); w=csv.writer(out)
w.writerow(['dataset','arm','sections','bits_per_value','bulk_ms','point_ns_per_probe','range_B1_ns','range_B64_ns','range_B4096_ns','range_B524288_ns','gather_geomean_vs_same_path_realNested','validated_all'])
for n in ['snowflake','osm_h3_r9_fileorder']:
    bits={};secs={}
    for f in glob.glob(f'{P}/comp/comp_{n}_*.csv'):
        for r in csv.DictReader(open(f)): bits[arm(r)]=float(r['bits_per_elem'])
        t=open(f[:-4]+'.log').read()
        lab=f.split(f'comp_{n}_')[1][:-4]
        for a,s in re.findall(r'--- (\S+) encoding tree ---\n\S+ sections=(\d+)',t):
            secs[a.replace('pinned',lab) if 'pinned' in a else a]=int(s)
    M={}; val=set()
    for kind in ['bulk','point','range','gather']:
        for f in glob.glob(f'{P}/access/{kind}_{n}_*_r*.csv'):
            rep=f.rsplit('_r',1)[1][:-4]
            for r in csv.DictReader(open(f)):
                if r['skipped']!='0': continue
                val.add(r['validated'])
                a=arm(r)
                if kind=='bulk': key=(a,'bulk')
                elif kind=='point': key=(a,'point')
                elif kind=='range': key=(a,'range',r['B'])
                else: key=(a,'gather',r['selectivity'],r['run_length'])
                v=float(r['ns_per_probe']) if kind=='point' else float(r['time_ns'])
                M.setdefault(key,{}).setdefault(rep,[]).append(v)
    # per rep median over offsets, then median over reps
    med={k:st.median(st.median(x) for x in v.values()) for k,v in M.items()}
    arms=sorted({k[0] for k in med})
    for a in arms:
        base='SIS/realNested+view' if a.endswith('+view') else 'SIS/realNested'
        gk=[k for k in med if k[0]==a and k[1]=='gather']
        gm=math.exp(st.mean(math.log(med[k]/med[(base,)+k[1:]]) for k in gk)) if gk else ''
        g=lambda B: round(med.get((a,'range',B),float('nan')))
        w.writerow([n,a,secs.get(a),round(bits.get(a,float('nan')),4),round(med[(a,'bulk')]/1e6,3),round(med[(a,'point')],1),g('1'),g('64'),g('4096'),g('524288'),round(gm,3) if gm!='' else '', val=={'1'}])
out.close()
print(open(P+'/summary.csv').read())
