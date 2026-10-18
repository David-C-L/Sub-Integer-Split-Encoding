# Section 2 data-class study — batch A (local, 2026-10-01)

Plan: `paper_handover/proposals/18_reframe_plan.md` section D (S1, S5, S7) and section G
(items 1, 2, 4). All analyses local only (benchmark host unreachable); nothing in `paper-repo/paper/`
(the paper repo) was read or edited.

Interpreter: `EncodingsPlayground/Datasets/.venv/bin/python` (numpy, pandas, matplotlib).
Shared module: `scripts/study_common.py` (column registry with local paths/layouts/sha256,
flip-profile, shipped admission-gate reimplementation, closed-form whole-value / per-field costs).

Gate definition verified against the shipped code (not re-derived): `gradient_gate` +
`active_entropy(p) <= 0.8`, from
`paper-repo/eval_figures/c3_bitflip_admission/gates.py` and the entropy_max=0.8
operating point used in `plot_c3_profiles.py:20` / `evaluate.py:39`.

Each analysis has its own `README_<id>.md` with inputs+sha256, method, outputs, runtime:
- `README_S1.md` — flip-profiles (all 22 local columns, file + shuffled order)
- `README_S5.md` — order sensitivity + instagram timestamp-sort check (T1 columns)
- `README_S7.md` — stability across prefixes/samples/blocks (5 full local files)
- `README_G1.md` — admission gate as a classifier (precision/recall/ROC sweep)
- `README_G4b.md` — coordinator follow-up 1: gate agreement at the planner's actual sampler config
- `README_FP_COST.md` — coordinator follow-up 2: false-positive size/encode-time cost (PublicBI measures)

## Headline numbers

1. **S1**: 22 columns profiled (T1 snowflake/instagram/uuidv7_hi/xmark/quadkey, T2 OSM
   h3/s2/morton, T3 float-cents near-misses, T4 low-card/skew measures, 6 controls). Controls
   (uuidv7_lo, publicbi_npi, publicbi_id1, tpch_orderkey*, inat_species_id, ipv4_id) mostly
   rejected by the gate; *tpch_orderkey is a false positive (see G1).
2. **S5/G2**: instagram in scraped (file) order: gate=**False**, active_entropy=0.822 (>0.8
   cutoff); sorted by its documented leading timestamp field (bits 23-63): gate=**True**,
   active_entropy drops to 0.694. G_doc (documented-field gain) is already positive
   (1.95 bits/value) in file order — the ~0.5 flip profile is a row-interleaving artifact of
   scraped order, not an absence of structure in the values.
3. **S7/G4**: on 5 full local files (snowflake 10M, xmark 32.3M, h3_r9 10M, publicbi_npi 17.29M,
   instagram 1.54M): gate decision is **100% stable** across row prefixes (65,536..full) and
   64K-row blocks for every column. Sample-size agreement (random subsamples, 128..full) is
   lower — 0.50 (snowflake), 0.75 (xmark), 0.38 (h3_r9), 1.00 (publicbi_npi, instagram) — i.e.
   tiny random samples (128-2048 rows) sometimes flip the decision even though block/prefix
   sweeps never do.
4. **G1**: classifier over all 22 columns (12 positive=structured, 10 negative=near-miss/control):
   **TP=9 FP=6 FN=2 TN=5, precision=0.60, recall=0.82, F1=0.69** at the shipped operating point
   (entropy_max=0.8). FNs: instagram (order artifact, see S5), quadkey (entropy 0.832). FPs: all
   4 "near-miss" columns (publicbi_drug_cost, publicbi_drug_cost_ge65, publicbi_bene_count,
   publicbi_num_employees, publicbi_day_supply_bin) plus tpch_orderkey — i.e. the gate's
   gradient/boundary test alone does not separate documented bit-fields from smooth
   magnitude-correlated near-miss profiles; entropy_max=0.8 is doing most of the separating work,
   and a tighter threshold trades recall for precision (see `csv/g1_threshold_sweep.csv`).

## Known limitations / TODOs carried into the next batch

- `HEADER_BITS_PER_SECTION = 32.0` in `study_common.py` is a placeholder (plan D: "header bytes
  as in Nimble: TODO read from the Sec. 4.2 cost models"); G_doc/G_opt magnitudes will shift once
  the real header cost is substituted, though sign/ranking is insensitive to a small additive
  constant at these block sizes.
- G_doc (documented-field gain) is used throughout instead of the full D_opt DP (2,080-range
  dynamic program over 64K blocks) for runtime reasons; D_opt/S2/S2b/S3/S6/S8/S9-S12/T1-T3 are
  out of scope for this batch (not requested) and left for the next batch.
- quadkey and uuidv7_hi full-length files are benchmark host-only (not available locally); S7 covers them
  only at the 524,288-row prefix level via S1/S5, not the full-file stability sweep.
