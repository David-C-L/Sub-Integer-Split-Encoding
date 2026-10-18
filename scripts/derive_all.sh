#!/usr/bin/env bash
# Rebuild every scripted intermediate in derived/ from data/ (run after scripts/unpack_data.sh).
# derived/sec3_plan_breakdown_8sec_addr.csv is the only file not rebuilt: it was read by hand from
# data/addr_toplevel_snowflake/comp_snowflake_toplevel.csv.log and is shipped as is.
# SIS_DERIVE_ROOT changes the output root (default derived/); the plot scripts always read derived/.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
D=${SIS_DERIVE_ROOT:-derived}
TL=$D/toplevel_sec7
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TL"

echo "== pull_524k_toplevel"
rm -rf "$TL/pull_524k_toplevel"
$PY scripts/derive/normalise_pull.py data/toplevel_sec7/sweep "$TL/pull_524k_toplevel"

echo "== merged_shipped_toplevel"
rm -rf "$TL/merged_shipped_toplevel"
SIS_DERIVE_OUT="$TL/merged_shipped_toplevel" $PY scripts/derive/build_merged_shipped_toplevel.py > /dev/null

# make_scoreboard.py / make_transform_impact_panels.py also draw draft figures; only the CSV and the log are kept.
board() {  # <pull dir> <out dir> <script>
  local o=$TMP/$(basename "$2"); mkdir -p "$o" "$2"
  SIS_FIG_PULL="$1" SIS_FIG_OUT="$o" $PY "$3" > "$2/run.log"
}
echo "== scoreboard_size_toplevel"
board "$TL/merged_shipped_toplevel" "$TL/scoreboard_size_toplevel" scripts/derive/make_scoreboard.py
cp "$TMP/scoreboard_size_toplevel/fig10_openzl_scoreboard.csv" "$TL/scoreboard_size_toplevel/"
echo "== scoreboard_524k_toplevel"
board "$TL/pull_524k_toplevel" "$TL/scoreboard_524k_toplevel" scripts/derive/make_scoreboard.py
cp "$TMP/scoreboard_524k_toplevel/fig10_openzl_scoreboard.csv" "$TL/scoreboard_524k_toplevel/"
echo "== fig12_panels_toplevel"
board "$TL/pull_524k_toplevel" "$TL/fig12_panels_toplevel" scripts/derive/make_transform_impact_panels.py
cp "$TMP/fig12_panels_toplevel/fig12_transform_impact.csv" "$TL/fig12_panels_toplevel/"

echo "== fig10_openzl_scoreboard_mixed.csv"
mkdir -p "$TMP/mixed"
SIS_FIG10_SIZE_CSV="$TL/scoreboard_size_toplevel/fig10_openzl_scoreboard.csv" \
SIS_FIG10_SPEED_CSV="$TL/scoreboard_524k_toplevel/fig10_openzl_scoreboard.csv" \
SIS_FIG_OUT="$TMP/mixed" $PY scripts/derive/make_fig10_scoreboard_col.py > /dev/null
cp "$TMP/mixed/fig10_openzl_scoreboard_mixed.csv" "$D/"

echo "== budget_sweep_values.csv"
$PY scripts/derive/sweeptab.py data/decode_knob_toplevel/sweep_measurements.csv "$D/budget_sweep_values.csv" > /dev/null

if [ "$D" != derived ] && [ -f derived/sec3_plan_breakdown_8sec_addr.csv ]; then
  cp derived/sec3_plan_breakdown_8sec_addr.csv "$D/"
fi
echo "derived/ rebuilt in $D"
