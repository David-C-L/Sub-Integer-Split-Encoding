import csv,sys
R=list(csv.DictReader(open(sys.argv[1]))); by={(r['dataset'],r['tag']):r for r in R}
B=['0','0p01','0p02','0p03','0p04','0p05','0p075','0p1','0p15','0p25','0p5','1']
ab=lambda p: p.replace('FrequencyPartition','FP').replace('MainlyConstant','MC').replace('BlockBitPacking','BBP').replace('Constant','C').replace('FixedBitWidth','FBW').replace('Dictionary','Dict').replace('Trivial','Tr').replace('SimdForBitpack','SFB')
print('validated',all(r['validated']=='1' for r in R if r['validated']),len(R),'skipped',sum(1 for r in R if r['skipped']),'reps',sorted({r['reps'] for r in R}))
out=[]
for d in ('snowflake','osm_s2_l30_fileorder','osm_h3_r9_fileorder'):
    b=by[(d,'w0')]
    print(f"\n### {d}: default {b['bytes_full']} / {b['bytes_524288']} B, {b['read_sections']} sections, pt {float(b['point_ns']):.0f} ns, rg {float(b['range64_ns']):.0f} ns, bulk {float(b['bulk_ms']):.2f} ms, open+first {float(b['open_plus_first_bulk_ms']):.1f} ms, enc {float(b['encode_ms']):.0f} ms, plan {b['planner_ms'][:5]} ms | {ab(b['plan'])}")
    for bb in B:
        r=by[(d,'B_b'+bb)]; x=lambda c: float(b[c])/float(r[c])
        pct=float(bb.replace('p','.'))*100
        row=dict(dataset=d,budget_pct=pct,size_full_pct=100*(int(r['bytes_full'])/int(b['bytes_full'])-1),size_prefix_pct=100*(int(r['bytes_524288'])/int(b['bytes_524288'])-1),read_sections=int(r['read_sections']),point=x('point_ns'),range64=x('range64_ns'),bulk=x('bulk_ms'),open_first_bulk=x('open_plus_first_bulk_ms'),encode_time_ratio=float(r['encode_ms'])/float(b['encode_ms']),planner_ms=float(r['planner_ms']),view_open_ratio=float(r['view_open_ms'])/float(b['view_open_ms']),resident_ratio=float(r['view_resident_bytes'])/float(b['view_resident_bytes']),plan=ab(r['plan']))
        out.append(row)
        print(f"| {pct:g}% | {row['size_full_pct']:+.1f}% | {row['size_prefix_pct']:+.1f}% | {row['read_sections']} | {row['point']:.2f}x | {row['range64']:.2f}x | {row['bulk']:.2f}x | {row['open_first_bulk']:.2f}x | {row['encode_time_ratio']:.1f}x | {row['planner_ms']:.1f} | {row['resident_ratio']:.2f} | {row['plan']} |")
if len(sys.argv)>2:
    w=csv.DictWriter(open(sys.argv[2],'w'),list(out[0].keys())); w.writeheader(); w.writerows(out)
