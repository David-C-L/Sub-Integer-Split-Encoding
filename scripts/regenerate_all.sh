#!/usr/bin/env bash
# Regenerate every paper figure and table from the artifact data into out/ (or $SIS_FIG_OUT),
# then compare each with the copy in figures/. Run from anywhere; paths are relative to the artifact root.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}

scripts/unpack_data.sh        # restore the packed experiment folders (idempotent)
PYTHON=$PY scripts/derive_all.sh   # rebuild derived/ from data/

# Section 7 (palette tol_hc, the default of scripts/plot/paperstyle.py)
for s in make_fig3_fig6_fig9b_compact make_fig10_scoreboard_split_v5 make_blocksize_half make_budget_half_v2 \
         make_fig12_default_only_v5 make_tables_toplevel make_fig_crossformat_bpv_AB make_tab_eval_setup \
         make_alp_floats_compact make_sis_encode_pipeline_v5; do
  echo "== $s"; $PY scripts/plot/$s.py > /dev/null
done
# Sections 1, 2 and 4 (rendered in the earlier palette B)
for s in make_sec1_zoom_v4_figure make_sec2_flip_panels make_sec4_bitflip make_sec4_flip_profile; do
  echo "== $s"; SIS_PALETTE=B $PY scripts/plot/$s.py > /dev/null
done
echo "== make_table1_class_study"; $PY scripts/plot/make_table1_class_study.py
echo "== budget_8col"; $PY scripts/derive/budget_8col.py > /dev/null
echo; scripts/check_against_paper.sh
