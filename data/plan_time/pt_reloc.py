# Relocates a copy of wt-consol1017/_build_release to wt-plantm1017 (same-length paths).
# As consolidated_20261017/consol_reloc.py: sources unchanged between the trees get the old mtimes,
# so only the files the plan-time patch touches are rebuilt.
import os, subprocess, json, struct
ROOT="$HOSTDATA/project"
OLD=ROOT+"/wt-consol1017"; NEW=ROOT+"/wt-plantm1017"; B=NEW+"/_build_release"
assert len(OLD)==len(NEW)
out=subprocess.run(["grep","-rlI","--exclude=.ninja_deps","--exclude=.ninja_log",OLD,B],capture_output=True,text=True).stdout.split()
for f in out:
    s=open(f,"rb").read(); open(f,"wb").write(s.replace(OLD.encode(),NEW.encode()))
print("text files rewritten",len(out))
p=B+"/.ninja_deps"; s=open(p,"rb").read(); n=s.count(OLD.encode()); open(p,"wb").write(s.replace(OLD.encode(),NEW.encode())); print("deps repl",n)
oh=subprocess.run(["git","-C",OLD,"rev-parse","HEAD"],capture_output=True,text=True).stdout.strip()
nh=subprocess.run(["git","-C",NEW,"rev-parse","HEAD"],capture_output=True,text=True).stdout.strip()
assert oh==nh, (oh,nh)
changed=set(subprocess.run(["git","-C",NEW,"diff","--name-only","HEAD"],capture_output=True,text=True).stdout.split())
dirty=subprocess.run(["git","-C",OLD,"status","--short","-uno"],capture_output=True,text=True).stdout.strip()
assert not dirty, dirty
print("changed",sorted(changed))
files=subprocess.run(["git","-C",NEW,"ls-files","-z"],capture_output=True).stdout.split(b"\0")
k=0
for f in files:
    if not f or f.decode() in changed: continue
    a=os.path.join(OLD.encode(),f); b=os.path.join(NEW.encode(),f)
    try:
        st=os.lstat(a)
        if os.path.islink(b): continue
        os.utime(b,ns=(st.st_atime_ns,st.st_mtime_ns)); k+=1
    except FileNotFoundError: pass
print("mtimes",k)
def murmur(key):
    m=0xc6a4a7935bd1e995; r=47; M=(1<<64)-1; seed=0xDECAFBADDECAFBAD
    h=(seed ^ (len(key)*m)) & M
    n8=len(key)//8
    for i in range(n8):
        k_=struct.unpack_from("<Q",key,i*8)[0]
        k_=(k_*m)&M; k_^=k_>>r; k_=(k_*m)&M
        h^=k_; h=(h*m)&M
    t=key[n8*8:]
    if t:
        for i in range(len(t)-1,-1,-1): h^=t[i]<<(8*i)
        h=(h*m)&M
    h^=h>>r; h=(h*m)&M; h^=h>>r
    return h
db=json.loads(subprocess.run(["ninja","-C",B,"-t","compdb"],capture_output=True,text=True).stdout)
remap={}
for e in db:
    c=e["command"]
    if not c: continue
    remap[murmur(c.replace(NEW,OLD).encode())]=murmur(c.encode())
p=B+"/.ninja_log"; lines=open(p).read().split("\n"); hit=0; tot=0
for i,l in enumerate(lines):
    f=l.split("\t")
    if len(f)==5:
        tot+=1; h=int(f[4],16)
        if h in remap: f[4]="%x"%remap[h]; hit+=1
        f[3]=f[3].replace(OLD,NEW); lines[i]="\t".join(f)
open(p,"w").write("\n".join(lines)); print("log",hit,"/",tot)
