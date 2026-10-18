"""F5 (v3): regression check + group summaries from the _v3 CSVs (prints markdown tables)."""
import os, numpy as np, pandas as pd
H = os.path.dirname(os.path.dirname(__file__)); C = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "data", "sec2_study", "F", "csv")  # artifact layout
STRUCT = ["snowflake","instagram","uuidv7_hi","h3_r9","h3_r15","s2_l16","s2_l30","quadkey","xmark"]
NEAR = ["publicbi_drug_cost","publicbi_drug_cost_ge65","publicbi_bene_count","publicbi_num_employees",
        "publicbi_day_supply_bin","morton_2x16","morton_2x32"]
def grp(c): return "structured" if c in STRUCT else "near_miss" if c in NEAR else "control"
v3 = pd.read_csv(os.path.join(C,"addressable_layouts_v3.csv")); old = pd.read_csv(os.path.join(C,"addressable_layouts.csv"))
# regression
bad = 0; chk = 0
m = {"FBW":"FBW","FOR_global":"FOR_global","FOR_block":"FOR_block","DICT":"DICT","WHOLE_best4":"WHOLE_best","SPLIT_DOC4":"SPLIT_DOC","SPLIT_DATA4":"SPLIT_DATA"}
for k, o in m.items():
    a = v3[v3.method==k].set_index("column").total_bits; b = old[old.method==o].set_index("column").total_bits
    j = pd.concat([a,b],axis=1,keys=["n","o"]).dropna()
    chk += len(j); bad += int((j.n.round()!=j.o.round()).sum())
print("regression: rows compared", chk, "mismatches", bad)
bpv = v3.pivot_table(index="column", columns="method", values="bits_per_value")
base = bpv["WHOLE_best4"]
g = lambda col: ((base-bpv[col])/base*100)
tab = pd.DataFrame({k: g(k) for k in ["WHOLE_best6","SPLIT_DATA4","SPLIT_DATA6","SPLIT_DOC6","xz_WHOLE","OpenZL_WHOLE"]})
tab["group"] = tab.index.map(grp)
print(tab.groupby("group").agg(["mean","min","max"]).round(1).T.to_string())
print(tab.groupby("group").count().iloc[:,:1].T)
print(tab[tab.group=="structured"].round(1).to_string())
# winners per range
r = pd.read_csv(os.path.join(C,"addressable_ranges_v3.csv")); r["group"]=r.column.map(grp)
for var in ["SPLIT_DATA","SPLIT_DOC"]:
    print(var); print(pd.crosstab(r[r.variant==var].group, r[r.variant==var].method6))
print("whole best6 winner:"); w=v3[v3.method=="WHOLE_best6"].copy(); w["group"]=w.column.map(grp); print(pd.crosstab(w.group,w.winner))
# shuffle
s = pd.read_csv(os.path.join(C,"shuffle_gap_v3.csv")); s["group"]=s.column.map(grp)
b = s.base4_bpv
b = s.base4_bpv
out = pd.DataFrame({"group":s.group.values,
  "xz_file":((b-s.xz_file_bpv)/b*100).values,"xz_shuf":((b-s.xz_shuf_bpv)/b*100).values,
  "w6_file":((b-s.whole6_file)/b*100).values,"w6_shuf":((b-s.whole6_shuf)/b*100).values,
  "rle_file":((b-s.rle_file)/b*100).values,"rle_shuf":((b-s.rle_shuf)/b*100).values,
  "sd6_file":((b-s.split_data6_file)/b*100).values,"sd6_shuf":((b-s.split_data6_shuf)/b*100).values,
  "sd4_shuf":((b-s.split_data4_shuf)/b*100).values}, index=s.column.values)
print(out.groupby("group").mean().round(1).T.to_string())
print(out.groupby("group").min().round(1).T.to_string()); print(out.groupby("group").max().round(1).T.to_string())
gm = s.assign(adv=b-s.xz_file_bpv, lost=s.xz_shuf_bpv-s.xz_file_bpv).groupby("group")[["adv","lost"]].sum()
gm["share_lost_pct"]=gm.lost/gm.adv*100; print(gm.round(2))
print(out[out.group=="structured"].round(1).to_string())
print(s[["column","xz_file_bpv"]].assign(Dxz=s.column.map(v3[v3.method=="xz_WHOLE"].set_index("column").bits_per_value)).assign(d=lambda x:(x.xz_file_bpv-x.Dxz).abs()).d.max())
