"""Shared helpers for the Sec. 2 float characterisation (study_20261001/E, 2026-10-02).

Data-only, no SIS/Nimble/cost model (plan 20 section 2). Reuses A/scripts/study_common.py
(flip_profile, field, h_bin) and C/scripts/structure_common.py (counts_entropy, delta_entropy,
data_chosen_partition) unchanged, so floats are measured identically to the integer columns.

Reduced run (2026-10-02): only 4 of the plan's 11 planned columns were obtained (disk space +
login-walled sources meant F1, F3, F5-F9 are absent). FLOATS below lists only what is present
under Datasets/Floats/txt/.

IEEE 754 double layout (bit 0 = LSB, half-open [lo, hi)):
  sign     [63, 64)
  exponent [52, 63)
  mantissa [0, 52)
"""
import os
import sys

import numpy as np

D = "$PROJECT/"
E_DIR = os.path.dirname(os.path.dirname(__file__))  # .../E
STUDY_DIR = os.path.dirname(E_DIR)  # .../study_20261001

A_SCRIPTS = os.path.join(STUDY_DIR, "A", "scripts")
C_SCRIPTS = os.path.join(STUDY_DIR, "C", "scripts")
sys.path.insert(0, A_SCRIPTS)
sys.path.insert(0, C_SCRIPTS)
import study_common as A  # noqa: E402  (flip_profile, field, h_bin, gate_decision, sha256_*)
import structure_common as C  # noqa: E402  (counts_entropy, delta_entropy, data_chosen_partition)

N = 524288

IEEE_LAYOUT = [("sign", 63, 64), ("exponent", 52, 63), ("mantissa", 0, 52)]

# name -> dict(path, class_label, full_len)
# class_label in {"decimal-origin", "sensor", "high-precision", "control"}
#
# Full run (2026-10-02, v2): all 11 of plan 20's float columns obtained (7 more ALP-suite
# columns extracted on benchmark host from ALP's complete_binaries.zip; see Datasets/Floats/MANIFEST.txt
# and README.md "ALP-suite columns"). full_len values are the plan's (20_floats_alp_plan.md
# section 1 table); F8 is shorter than 524288 so its full_len is the full column.
FLOATS = {
    "F1_stocks_usa": dict(
        path=f"{D}/Datasets/Floats/txt/F1_stocks_usa.txt",
        class_label="decimal-origin", full_len=282076179,
        desc="ALP suite, Stocks-USA (INFORE)"),
    "F2_food_prices": dict(
        path=f"{D}/Datasets/Floats/txt/F2_food_prices.txt",
        class_label="decimal-origin", full_len=2050638,
        desc="WFP food prices, mp_price"),
    "F3_gov10": dict(
        path=f"{D}/Datasets/Floats/txt/F3_gov10.txt",
        class_label="decimal-origin", full_len=141123827,
        desc="ALP suite, PBI CommonGovernment Gov/10"),
    "F4_medicare_total_drug_cost": dict(
        path=f"{D}/Datasets/Floats/txt/F4_medicare_total_drug_cost.txt",
        class_label="decimal-origin", full_len=2000000,
        desc="local Medicare1 TOTAL_DRUG_COST"),
    "F5_city_temp": dict(
        path=f"{D}/Datasets/Floats/txt/F5_city_temp.txt",
        class_label="sensor", full_len=2905887,
        desc="ALP suite, City-Temp (Kaggle)"),
    "F6_air_pressure": dict(
        path=f"{D}/Datasets/Floats/txt/F6_air_pressure.txt",
        class_label="sensor", full_len=137721453,
        desc="ALP suite, Air-Pressure (NEON)"),
    "F7_dew_point_temp": dict(
        path=f"{D}/Datasets/Floats/txt/F7_dew_point_temp.txt",
        class_label="sensor", full_len=5413914,
        desc="ALP suite, Dew-Point-Temp (NEON)"),
    "F8_poi_lat": dict(
        path=f"{D}/Datasets/Floats/txt/F8_poi_lat.txt",
        class_label="high-precision", full_len=424205,
        desc="ALP suite, POI-lat radians (Kaggle); full column, shorter than 524288"),
    "F9_nyc29": dict(
        path=f"{D}/Datasets/Floats/txt/F9_nyc29.txt",
        class_label="high-precision", full_len=17446346,
        desc="ALP suite, PBI NYC/29 longitude"),
    "F10_medicare_calc_9030826185528129": dict(
        path=f"{D}/Datasets/Floats/txt/F10_medicare_calc_9030826185528129.txt",
        class_label="high-precision", full_len=2000000,
        desc="local Medicare1 Calculation_9030826185528129 (computed ratio)"),
    "C0_uniform_control": dict(
        path=f"{D}/Datasets/Floats/txt/C0_uniform_control.txt",
        class_label="control", full_len=524288,
        desc="synthetic uniform double control, no decimal structure"),
}

# ordering for figures: grouped by class
CLASS_ORDER = ["decimal-origin", "sensor", "high-precision", "control"]


def _ordered_names():
    def key(name):
        cl = FLOATS[name]["class_label"]
        return (CLASS_ORDER.index(cl), name)
    return sorted(FLOATS.keys(), key=key)


ORDERED_NAMES = _ordered_names()


def load_floats(name, n=N):
    """Load up to n double values in file order -> np.float64 array."""
    cfg = FLOATS[name]
    vals = []
    with open(cfg["path"], "r") as f:
        for i, line in enumerate(f):
            if n is not None and i >= n:
                break
            line = line.strip()
            if not line:
                continue
            vals.append(float(line))
    return np.array(vals, dtype=np.float64)


def load_bits(name, n=N):
    """float64 array -> raw IEEE bits as np.uint64 (same physical type SIS partitions)."""
    x = load_floats(name, n=n)
    return x, x.view(np.uint64)


if __name__ == "__main__":
    for name in ORDERED_NAMES:
        x, v = load_bits(name, n=1000)
        print(name, FLOATS[name]["class_label"], len(x), x[:3], hex(int(v[0])))
