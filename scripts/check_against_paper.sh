#!/usr/bin/env bash
# Compare regenerated outputs in out/ with the paper copies in figures/.
# PDFs: identical pdftotext output and page size. TeX: diff ignoring comment lines.
# Three reference PDFs are in figures/ but commented out in the final paper (marked "not placed"):
# section_4/snowflake_flip_{probability,gradient}.pdf and section_7/fig6_point_access.pdf.
cd "$(dirname "$0")/.."
OUT=${SIS_FIG_OUT:-out}
pairs="
section_1/fig0_zoom_nosis.pdf fig0_v4.pdf
section_2/flip_T1.pdf flip_T1.pdf
section_2/flip_T3.pdf flip_T3.pdf
section_2/flip_nearmiss.pdf flip_nearmiss.pdf
section_2/flip_control.pdf flip_control.pdf
section_3/sis_encode_pipeline.pdf sis_encode_pipeline_v5.pdf
section_4/snowflake_flip_profile.pdf snowflake_flip_profile.pdf
section_4/snowflake_flip_probability.pdf snowflake_flip_probability.pdf
section_4/snowflake_flip_gradient.pdf snowflake_flip_gradient.pdf
section_7/fig10_openzl_scoreboard.pdf fig10_openzl_scoreboard_split_v5.pdf
section_7/fig9b_gather_shapes_a.pdf fig9b_gather_shapes_a.pdf
section_7/fig9b_gather_shapes_b.pdf fig9b_gather_shapes_b.pdf
section_7/fig9b_gather_shapes_c.pdf fig9b_gather_shapes_c.pdf
section_7/fig9b_gather_shapes_d.pdf fig9b_gather_shapes_d.pdf
section_7/fig9b_gather_shapes_legend.pdf fig9b_gather_shapes_legend.pdf
section_7/fig6_point_access.pdf fig6_point_access.pdf
section_7/fig_blocksize_snowflake_half.pdf fig_blocksize_snowflake_half.pdf
section_7/fig_budget_sweep_half.pdf fig_budget_sweep_half_v2.pdf
section_7/fig12_transform_impact_heatmap.pdf fig12_transform_impact_heatmap_default_only_v5.pdf
section_7/fig_alp_floats_size.pdf fig_alp_floats_size.pdf
section_7/fig_alp_floats_range.pdf fig_alp_floats_range.pdf
section_7/fig_crossformat_bpv_B.pdf fig_crossformat_bpv_B.pdf
section_7/table7_admission_confusion.tex table7_admission_confusion.tex
section_7/tab_eval_composition.tex tab_eval_composition_full.tex
section_7/tab_eval_planner_gap_body.tex tab_eval_planner_gap_toplevel.tex
"
rc=0
while read -r ref new; do
  [ -z "$ref" ] && continue
  if [ ! -f "$OUT/$new" ]; then echo "MISSING  $ref ($OUT/$new)"; rc=1; continue; fi
  case "$ref" in
    *.pdf)
      t=$(diff <(pdftotext -layout "figures/$ref" -) <(pdftotext -layout "$OUT/$new" -) >/dev/null && echo text-ok || echo TEXT-DIFF)
      s1=$(pdfinfo "figures/$ref" | awk '/Page size/{print $3"x"$5}'); s2=$(pdfinfo "$OUT/$new" | awk '/Page size/{print $3"x"$5}')
      [ "$s1" = "$s2" ] && s=size-ok || s="SIZE-DIFF($s1 vs $s2)"
      px=$(python3 scripts/pixel_compare.py "figures/$ref" "$OUT/$new" 2>/dev/null || echo pixel-n/a)
      case "$ref" in *flip_probability*|*flip_gradient*|*fig6_point_access*) px="$px; not placed in the final paper";; esac
      if [ "$t" = text-ok ] && [ "$s" = size-ok ]; then echo "MATCH    $ref  ($px)"; else echo "DIFFER   $ref  $t $s ($px)"; rc=1; fi ;;
    *.tex)
      if diff <(grep -v '^ *%' "figures/$ref") <(grep -v '^ *%' "$OUT/$new") >/dev/null; then echo "MATCH    $ref"; else echo "DIFFER   $ref"; rc=1; fi ;;
  esac
done <<< "$pairs"
# Table 2: compare after normalising whitespace (the paper file is hand-aligned)
norm() { sed -E 's/[[:space:]]+/ /g; s/ ?& ?/\&/g; s/ $//' "$1"; }
if [ ! -f "$OUT/tab_eval_setup.tex" ]; then echo "MISSING  section_7/tab_eval_setup.tex"; rc=1
elif d=$(diff <(norm figures/section_7/tab_eval_setup.tex) <(norm "$OUT/tab_eval_setup.tex")); then
  echo "MATCH    section_7/tab_eval_setup.tex (whitespace-normalised)"
else echo "DIFFER   section_7/tab_eval_setup.tex"; echo "$d" | sed 's/^/           /'; rc=1; fi
# Table 1: the paper body was assembled by hand; compare its rows with the recomputed body
if diff <(sed -n '/midrule/,/bottomrule/p' figures/section_2/table_class_study_grouped.tex | grep -v '^ *%' | grep -v rule) \
        <(grep -v rule "$OUT/table_class_study_grouped_body.tex") >/dev/null 2>&1; then
  echo "MATCH    section_2/table_class_study_grouped.tex (body rows)"; else echo "DIFFER   section_2/table_class_study_grouped.tex"; rc=1; fi
exit $rc
