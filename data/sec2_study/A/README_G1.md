# G1: membership test as a classifier

Inputs: all 22 local columns (study_common.COLUMNS), N=524288 rows (file order), labels
from documented layouts in the provenance doc / plan C.5 taxonomy (`kind == "structured"` in
study_common.COLUMNS, independent of the test): 11 positive (structured: T1/T2) / 11
negative (near-miss T3/T4 + controls).

Method: shipped admission test (gradient_gate(features(p)) AND active_entropy(p) <= entropy_max,
`study_common.gate_decision`, verified against `paper-repo/eval_figures/c3_bitflip_admission/gates.py`
and the entropy_max=0.8 operating point in `plot_c3_profiles.py:20`/`evaluate.py:39`). Threshold
sweep varies entropy_max in {0.1,...,1.3} with gradient_gate held fixed as a prerequisite (it
has no single scalar in the shipped code; see S1 for its boundaries/maxg features).

## Operating point (entropy_max=0.8, as shipped)

TP=9 FP=6 FN=2 TN=5
Precision=0.600 Recall=0.818 F1=0.692 FPR=0.545

Outputs:
- csv/g1_classifier_labels.csv: per-column label, gate decision, active_entropy, correct
- csv/g1_threshold_sweep.csv: entropy_max, tp, fp, fn, tn, precision, recall, f1, fpr (ROC-style table)

Runtime: 17.1 s
