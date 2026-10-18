"""Caches bit-flip profiles (full and stride-sampled) for the 39 admission columns."""
import glob, os, numpy as np
ROOT = os.environ.get("SIS_ARTIFACT_ROOT", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))
DS = os.environ.get("SIS_DATASETS", f"{ROOT}/datasets/raw")
# SIS_ADM_DIR lets a newer sweep's admission CSVs be used without editing this
# file; unset, the original rev-admission-39col sweep is read exactly as before.
ADM = os.environ.get("SIS_ADM_DIR", f"{ROOT}/data/toplevel_sec7/admission")
ROWS = 524288
PAIRS = [0, 65536, 16384, 4096, 1024]

# Columns whose files do not follow the <Dataset>/csv/<column>.txt convention,
# or which only exist on the benchmark host and were copied here.
EXTRA = os.environ.get("SIS_EXTRA_COLUMNS", f"{ROOT}/datasets/columns_524k")
PATH_OVERRIDES = {
    "bing_quadkey": f"{EXTRA}/quadkey_fileorder.txt",
    "uuidv7_hi": f"{EXTRA}/uuidv7_hi.txt",
    "uuidv7_lo": f"{EXTRA}/uuidv7_lo.txt",
}


def column_path(name):
    if name in PATH_OVERRIDES:
        return PATH_OVERRIDES[name]
    if name.startswith("PublicBI_"):
        _, table, col = name.split("_", 2); return f"{DS}/PublicBI/{table}/csv/{col}.txt"
    if name.startswith("iNaturalist_csv_"): return f"{DS}/iNaturalist_csv/{name[16:]}.txt"
    d, col = name.split("_", 1); return f"{DS}/{d}/csv/{col}.txt"

def profile(v, max_pairs):
    pairs = len(v) - 1
    stride = 1 if max_pairs == 0 else max(1, -(-pairs // max_pairs))
    i = np.arange(0, pairs, stride)
    x = v[i] ^ v[i + 1]
    bits = np.unpackbits(x.view(np.uint8).reshape(-1, 8), axis=1, bitorder="little")
    return bits.mean(axis=0)

def main():
    names = sorted(os.path.basename(p)[:-4] for p in glob.glob(f"{ADM}/*.csv"))
    out = {}
    for n in names:
        v = np.loadtxt(column_path(n), max_rows=ROWS, dtype=np.uint64)
        out[n] = np.stack([profile(v, m) for m in PAIRS]); print(n, len(v))
    np.savez(os.environ.get("SIS_PROFILES_NPZ", "profiles.npz"), names=np.array(names), pairs=np.array(PAIRS), **{n: out[n] for n in names})

if __name__ == "__main__":
    main()
