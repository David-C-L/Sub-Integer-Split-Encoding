#!/bin/bash
# Smoke: Snowflake 524,288 rows, TopLevel, no knob (w0) and budget 0 (B_b0). Compression only, held under the lock.
set -u
. $(dirname $0)/common.sh
D=$O/smoke; mkdir -p $D
SC="--mlidc_sis_section_candidates=addressable"
REC="--mlidc_sis_decode_read_path=1 --mlidc_sis_decode_cost_model=1 --mlidc_sis_section_read_nanos=-1 --mlidc_sis_decode_weight_sections_only --mlidc_sis_size_budget_strict --mlidc_sis_decode_mix=point:0.5,bulk:0.5"
F=$DS/TwitterSnowflake/csv/tweet_id_full.txt
( flock 9
  comp w0 $F snowflake $N SIS/realNested,SIS/realNested+view $SC
  comp B_b0 $F snowflake $N SIS/realNested $SC $REC --mlidc_sis_size_budget=0
) 9>>$LOCK
echo SMOKE_DONE
