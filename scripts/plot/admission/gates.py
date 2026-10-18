"""Ground truth plus gate decisions over cached profiles (mirrors SubIntSplitTopLevelPolicy.h)."""
import csv, glob, os, numpy as np
from profiles import ADM
# SIS_PROFILES_NPZ lets a caller point at a cache built elsewhere; unset, the
# file is read from the working directory exactly as before.
Z = np.load(os.environ.get("SIS_PROFILES_NPZ", "profiles.npz"))
NAMES = list(Z["names"]); PAIRS = list(Z["pairs"])
SIS_ARMS = ["SIS/realNested", "SIS/hybrid"]

def truth():
    t, pol, est = {}, {}, {}
    for p in glob.glob(f"{ADM}/*.csv"):
        arms = {}
        for r in csv.DictReader(open(p)):
            if r["row_kind"] == "heuristic":
                d = r["dataset"]; pol[d] = r["policy_selects_sis"] == "1"; est[d] = r["estimate_admits"] == "1"
            elif r["row_kind"] == "encoder" and r["skipped"] != "1": arms[r["encoding"]] = int(r["payload_bytes"])
        s = min(arms[a] for a in SIS_ARMS if a in arms)
        o = min(v for a, v in arms.items() if not a.startswith(("SIS/", "openzl")))
        t[d] = s < 0.99 * o
    return t, pol, est

def h(p):
    q = np.clip(p, 1e-12, 1 - 1e-12); e = -(q * np.log2(q) + (1 - q) * np.log2(1 - q))
    return np.where((p <= 0) | (p >= 1), 0.0, e)

def features(p, k=2.0):
    g = np.zeros_like(p); g[1:] = np.abs(np.diff(p))
    thr = g[1:].mean() + k * g[1:].std()
    return dict(boundaries=int((g[1:] > thr).sum()), maxg=float(g.max()), var=float(p.var()),
                ent=float(h(p).mean()), active=int((p > 0).sum()))

def gradient_gate(f, minb=1, ming=0.005): return f["boundaries"] >= minb and f["maxg"] >= ming

def metrics(pred, t, names):
    tp = sum(pred[n] and t[n] for n in names); fp = sum(pred[n] and not t[n] for n in names)
    fn = sum(t[n] and not pred[n] for n in names)
    P = tp / (tp + fp) if tp + fp else float("nan"); R = tp / (tp + fn) if tp + fn else float("nan")
    return tp, fp, fn, len(names) - tp - fp - fn, P, R, 2 * P * R / (P + R) if P + R else 0.0

def active_entropy(p, varying=None):
    """Mean binary entropy over varying bits; varying defaults to p > 0 (whole-stream mask in C++)."""
    a = p > 0 if varying is None else varying
    return float(h(p[a]).mean()) if a.any() else 0.0

def admits(p, entropy_max=None, k=2.0, varying=None):
    ok = gradient_gate(features(p, k))
    return ok and (entropy_max is None or active_entropy(p, varying) <= entropy_max)

def family(n):
    return "PublicBI_" + n.split("_")[1] if n.startswith("PublicBI") else n.split("_")[0]
