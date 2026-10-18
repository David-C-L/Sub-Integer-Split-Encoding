"""G1: the membership test (shipped bit-flip admission gate) as a classifier.
Labelled set = study_common.LABELS (True = documented structured layout, from the provenance doc,
not from the test). Report precision/recall at the shipped operating point (gradient_gate +
entropy_max=0.8) and a threshold sweep (ROC-style table) over entropy_max alone (gradient_gate
held fixed, since it has no single scalar threshold in the shipped implementation).
"""
import csv
import time

import numpy as np

import study_common as sc

OUT = "$PROJECT/paper-repo/study_20261001/A"
N = 524288
t0 = time.time()

names = sorted(sc.COLUMNS.keys())
profiles = {}
for name in names:
    v = sc.load(name, n=N)
    profiles[name] = sc.flip_profile(v)

labels = {name: sc.LABELS[name] for name in names}

# operating-point decision (shipped: entropy_max=0.8)
decisions = {}
entropies = {}
for name in names:
    ok, f = sc.gate_decision(profiles[name], entropy_max=0.8)
    decisions[name] = ok
    entropies[name] = f["active_entropy"]


def confusion(pred, labels, names):
    tp = sum(pred[n] and labels[n] for n in names)
    fp = sum(pred[n] and not labels[n] for n in names)
    fn = sum((not pred[n]) and labels[n] for n in names)
    tn = sum((not pred[n]) and (not labels[n]) for n in names)
    P = tp / (tp + fp) if (tp + fp) else float("nan")
    R = tp / (tp + fn) if (tp + fn) else float("nan")
    F1 = 2 * P * R / (P + R) if (P + R) and not np.isnan(P) and not np.isnan(R) and (P + R) > 0 else float("nan")
    fpr = fp / (fp + tn) if (fp + tn) else float("nan")
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, precision=P, recall=R, f1=F1, fpr=fpr)

op = confusion(decisions, labels, names)

with open(f"{OUT}/csv/g1_classifier_labels.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["column", "subtype", "kind", "label_structured", "gate_decision", "active_entropy", "correct"])
    for name in names:
        c = sc.COLUMNS[name]
        w.writerow([name, c["subtype"], c["kind"], int(labels[name]), int(decisions[name]),
                    round(entropies[name], 4), int(labels[name] == decisions[name])])

# threshold sweep over entropy_max (ROC-style), gradient_gate held as a prerequisite
thresholds = list(np.round(np.arange(0.1, 1.31, 0.1), 2))
sweep_rows = []
for th in thresholds:
    pred = {}
    for name in names:
        ok, f = sc.gate_decision(profiles[name], entropy_max=th)
        pred[name] = ok
    m = confusion(pred, labels, names)
    sweep_rows.append(dict(entropy_max=th, **m))

with open(f"{OUT}/csv/g1_threshold_sweep.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["entropy_max", "tp", "fp", "fn", "tn", "precision", "recall", "f1", "fpr"])
    w.writeheader()
    w.writerows(sweep_rows)

dt = time.time() - t0
n_pos = sum(labels.values())
n_neg = len(names) - n_pos
with open(f"{OUT}/README_G1.md", "w") as fh:
    fh.write(f"""# G1: membership test as a classifier

Inputs: all {len(names)} local columns (study_common.COLUMNS), N={N} rows (file order), labels
from documented layouts in the provenance doc / plan C.5 taxonomy (`kind == "structured"` in
study_common.COLUMNS, independent of the test): {n_pos} positive (structured: T1/T2) / {n_neg}
negative (near-miss T3/T4 + controls).

Method: shipped admission test (gradient_gate(features(p)) AND active_entropy(p) <= entropy_max,
`study_common.gate_decision`, verified against `paper-repo/eval_figures/c3_bitflip_admission/gates.py`
and the entropy_max=0.8 operating point in `plot_c3_profiles.py:20`/`evaluate.py:39`). Threshold
sweep varies entropy_max in {{0.1,...,1.3}} with gradient_gate held fixed as a prerequisite (it
has no single scalar in the shipped code; see S1 for its boundaries/maxg features).

## Operating point (entropy_max=0.8, as shipped)

TP={op['tp']} FP={op['fp']} FN={op['fn']} TN={op['tn']}
Precision={op['precision']:.3f} Recall={op['recall']:.3f} F1={op['f1']:.3f} FPR={op['fpr']:.3f}

Outputs:
- csv/g1_classifier_labels.csv: per-column label, gate decision, active_entropy, correct
- csv/g1_threshold_sweep.csv: entropy_max, tp, fp, fn, tn, precision, recall, f1, fpr (ROC-style table)

Runtime: {dt:.1f} s
""")
print("done", dt, op)
