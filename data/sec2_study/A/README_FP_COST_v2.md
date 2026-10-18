# Follow-up 2: false-positive cost (PublicBI measure columns)

Source (read-only, no new benchmark run): `pulls/gatespeed/admission/{neg_medicare_drug_cost_bits,
neg_medicare_drug_cost_ge65_bits,PublicBI_Medicare1_BENE_COUNT,PublicBI_Corporations_num_employees,
PublicBI_Medicare1_Avg_Day_Supply_Bene_bin}.csv` (524,288-row prefix, `shipped` order; encoder rows,
`row_kind==encoder`). `addr_toplevel_20260930_1127`/`addr_20260930_0257` do not contain these 5
PublicBI measure columns (only the 10 main corpus columns); `pulls/gatespeed` is the pull
that has them. Neither pull contains a `sections` field for these 5 columns (only
`addr_toplevel_20260930_1127/summary.tsv`, for the 10 main columns, records the section-boundary
string), so **section-count / split-vs-single-section cannot be read off directly for these 5**;
`payload_bytes` and `encode_ns` are available and reported below. `default` = min `payload_bytes`
over the non-SIS encoder rows (Trivial/FixedBitWidth/Dictionary/RLE/MainlyConstant/PFOR-view/
SimdForBitpack-view/FPE); `sis` = min over SIS/realNested and SIS/hybrid.

## Result: none are a no-op fallback — SIS compresses all 5 further, at higher encode cost

| column | default arm | default bpv | SIS arm | SIS bpv | size change | encode slowdown |
|---|---|---|---|---|---|---|
| publicbi_drug_cost | PFOR/view | 56.05 | SIS/hybrid | 23.69 | -57.7% | 15.4x |
| publicbi_drug_cost_ge65 | SimdForBitpack/view | 63.02 | SIS/hybrid | 23.34 | -63.0% | 38.5x |
| publicbi_bene_count | PFOR/view | 8.67 | SIS/realNested | 7.59 | -12.5% | 13.9x |
| publicbi_num_employees | MainlyConstant | 2.97 | SIS/hybrid | 2.83 | -4.6% | 6.4x |
| publicbi_day_supply_bin | SimdForBitpack/view | 7.00 | SIS/realNested | 5.05 | -27.9% | 22.8x |
| tpch_orderkey | — | — | — | — | NO DATA | NO DATA |

tpch_orderkey: no SIS/benchmark data found anywhere under `pulls/` (not in
`gatespeed/scripts/gs_columns.txt`'s column list, not in `addr_toplevel_20260930_1127` or
`addr_20260930_0257`) — it was never part of this benchmark's corpus, so no size/time comparison
exists to report.

Interpretation: the gate's false positives on these 5 columns (G1) do not carry a size penalty in
practice — the shipped SIS/hybrid or SIS/realNested arm beats the best non-SIS encoder by 4.6% to
63.0% on every one of them, i.e. the "near-miss" columns still have enough smooth, FOR-splittable
numeric structure (monetary/count magnitudes) for a bit-range split to help, even though they lack
a *documented* multi-field layout. The cost is entirely in encode time: SIS takes 6.4x-38.5x longer
to encode than the best default arm on these columns (full real_nested/hybrid DP, not a
short-circuited single-section path).
