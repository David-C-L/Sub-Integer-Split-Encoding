"""Shared paper figure style module (Decision 2026-10-02, scheme B / corrected categories).

Provides:
  - ENTITIES: canonical entity registry {key: {color, marker, hatch, label, category}}
  - normalize_arm(raw): internal arm/codec string -> canonical entity key
  - apply_rcparams(): shared matplotlib rcParams (8pt min text, pdf.fonttype 42, no titles)
  - legend_handles(keys): compact Line2D/Patch handles for a subset of entities, in a fixed order
  - DATASET_NAMES: internal dataset/column id -> paper Table 1 / Section 2 display name

Do not hand-roll colours/markers/labels in any figure script again: import from here.
"""

import os

import matplotlib as mpl
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# 2026-10-17 copy (paper_handover/figures_sec7_final_20261017/scripts): adds
#   * SHORT_NAMES / short_label(): one short label per Sec. 7 column;
#   * SIS_PALETTE=<name> selects an experimental palette (see _PALETTES at the end);
#     default "tol_hc" (the author, 2026-10-17); SIS_PALETTE=B gives every colour, marker and colour map exactly as palette B.

# ---------------------------------------------------------------------------
# Entity registry: one colour family per category (Paul Tol muted, scheme B),
# one fixed (color, marker, hatch, label) per entity, paper-wide.
# Categories:
#   SIS           - saturated indigo/blue family, headline darkest
#   HEAVYWEIGHT   - general-purpose byte-stream compressors (wine/rose)
#   FORMAT        - file formats (olive/sand)
#   LIGHTWEIGHT   - individual Nimble encodings used as baselines (greys/blue-grey)
#   ALP           - ALP variants (teal)
#   NEUTRAL       - non-entity semantics (accept/reject, gaps); never reused for entities
# ---------------------------------------------------------------------------

ENTITIES = {
    # --- SIS (indigo/blue, saturated; headline darkest) ---
    "SIS_DEFAULT":  {"color": "#332288", "marker": "*", "hatch": None,  "label": "SIS (default)",        "category": "SIS"},
    "SIS_HYBRID":   {"color": "#4F5FB0", "marker": "o", "hatch": None,  "label": "SIS (re-priced)",       "category": "SIS"},
    "SIS_BEST":     {"color": "#6E8DD6", "marker": "^", "hatch": None,  "label": "SIS best",              "category": "SIS"},
    "SIS_AUTO":     {"color": "#4F5FB0", "marker": "o", "hatch": "///", "label": "SIS (DP + transform search)", "category": "SIS"},
    "SIS_HYBRID_AUTO": {"color": "#6E8DD6", "marker": "^", "hatch": "///", "label": "SIS (re-priced + transform search)", "category": "SIS"},
    "SIS_ZL":       {"color": "#1F1760", "marker": "P", "hatch": None,  "label": "+ZL",                   "category": "SIS"},

    # --- Heavyweight general-purpose byte-stream compressors (wine/rose) ---
    "OPENZL":       {"color": "#882255", "marker": "s", "hatch": None,  "label": "OpenZL",                "category": "HEAVYWEIGHT"},
    "OPENZL_BLOCK": {"color": "#A24A72", "marker": "D", "hatch": None,  "label": "OpenZL-1K",             "category": "HEAVYWEIGHT"},
    "ZSTD":         {"color": "#CC6677", "marker": "v", "hatch": None,  "label": "Zstd",                   "category": "HEAVYWEIGHT"},
    "ZSTD_BLOCK":   {"color": "#D98A96", "marker": "v", "hatch": "///", "label": "Zstd-64",                "category": "HEAVYWEIGHT"},
    "XZ":           {"color": "#DDAA99", "marker": "p", "hatch": None,  "label": "xz",                     "category": "HEAVYWEIGHT"},
    "LZ4":          {"color": "#BB667A", "marker": "<", "hatch": None,  "label": "LZ4",                    "category": "HEAVYWEIGHT"},
    "SNAPPY":       {"color": "#E2B6AE", "marker": ">", "hatch": None,  "label": "Snappy",                 "category": "HEAVYWEIGHT"},

    # --- File formats (olive/sand) ---
    "PARQUET":      {"color": "#999933", "marker": "v", "hatch": None,  "label": "Parquet",                "category": "FORMAT"},
    "ORC":          {"color": "#BBBB77", "marker": "h", "hatch": None,  "label": "ORC",                    "category": "FORMAT"},
    "BTRBLOCKS":    {"color": "#DDCC77", "marker": "P", "hatch": None,  "label": "BtrBlocks",               "category": "FORMAT"},
    "FASTLANES":    {"color": "#EEDD88", "marker": "X", "hatch": None,  "label": "FastLanes",               "category": "FORMAT"},
    "NIMBLE":       {"color": "#8C8C3A", "marker": "o", "hatch": None,  "label": "Nimble (default)",        "category": "FORMAT"},

    # --- Lightweight codecs / Nimble encodings used as baselines (greys / blue-grey) ---
    "FBW":          {"color": "#AAAAAA", "marker": "x", "hatch": None,  "label": "FixedBitWidth",          "category": "LIGHTWEIGHT"},
    "DICT":         {"color": "#8E99A6", "marker": "d", "hatch": None,  "label": "Dict",                   "category": "LIGHTWEIGHT"},
    "RLE":          {"color": "#6E7B8B", "marker": "+", "hatch": None,  "label": "RLE",                    "category": "LIGHTWEIGHT"},
    "FPE":          {"color": "#5A6878", "marker": "1", "hatch": None,  "label": "FPE",                    "category": "LIGHTWEIGHT"},
    "VARINT":       {"color": "#B9C2CB", "marker": "2", "hatch": None,  "label": "Varint",                 "category": "LIGHTWEIGHT"},
    "SIMD_FOR":     {"color": "#7D8A99", "marker": "5", "hatch": None,  "label": "SIMD-FOR",                "category": "LIGHTWEIGHT"},
    "PFOR":         {"color": "#A3AEB8", "marker": "6", "hatch": None,  "label": "PFOR",                   "category": "LIGHTWEIGHT"},
    "DELTA":        {"color": "#9AA6B2", "marker": "3", "hatch": None,  "label": "Delta",                  "category": "LIGHTWEIGHT"},
    "CONSTANT":     {"color": "#CCCCCC", "marker": "4", "hatch": None,  "label": "Constant",               "category": "LIGHTWEIGHT"},

    # --- ALP variants (teal) ---
    "ALP":          {"color": "#44AA99", "marker": "o", "hatch": None,  "label": "ALP",                    "category": "ALP"},
    "ALP_RD":       {"color": "#88CCBB", "marker": "s", "hatch": None,  "label": "ALP_rd",                 "category": "ALP"},
    "ALP_REF":      {"color": "#117733", "marker": "^", "hatch": None,  "label": "ALP (CWI)",             "category": "ALP"},

    # --- Neutral, non-entity semantics (never an entity colour) ---
    "ACCEPT":       {"color": "#4D4D4D", "marker": "o", "hatch": None,  "label": "accept",                 "category": "NEUTRAL"},
    "REJECT":       {"color": "#B3B3B3", "marker": "x", "hatch": None,  "label": "reject",                 "category": "NEUTRAL"},
    "GUARD":        {"color": "#808080", "marker": "d", "hatch": "...", "label": "entropy guard",           "category": "NEUTRAL"},
    "GAP":          {"color": "#D9D9D9", "marker": None, "hatch": "\\\\\\", "label": "gap",                 "category": "NEUTRAL"},
    "SCATTER_CAT":  {"color": "#595959", "marker": "x", "hatch": None,  "label": "SIS wins / gradient rejects", "category": "NEUTRAL"},
}

# ---------------------------------------------------------------------------
# Arm / internal-string -> canonical entity key
# ---------------------------------------------------------------------------

_ARM_MAP = {
    # SIS
    "SIS/realNested": "SIS_DEFAULT",
    "SIS/realNested+view": "SIS_DEFAULT",
    "SIS": "SIS_DEFAULT",
    "SIS+view": "SIS_DEFAULT",
    "SIS/hybrid": "SIS_HYBRID",
    "SIS/hybrid+view": "SIS_HYBRID",
    "SIS/auto": "SIS_AUTO",
    "SIS/auto+view": "SIS_AUTO",
    "SIS/hybrid_auto": "SIS_HYBRID_AUTO",
    "SIS/hybrid_auto+view": "SIS_HYBRID_AUTO",
    "SIS best": "SIS_BEST",
    "SIS_best": "SIS_BEST",
    "+ZL": "SIS_ZL",
    # Decision 26 (2026-10-02, the author): retired/ablation SIS variants
    # (relabel_*, key_derived, bitplane, huffOn*) are removed from every
    # paper figure -- no "SIS (other arm)" catch-all entity. Any script that
    # still tries to normalize one of these arm strings now fails loudly
    # (KeyError) by design; drop those rows from the data before plotting.
    # heavyweight
    "openzl/auto": "OPENZL",
    "openzl": "OPENZL",
    "OpenZL": "OPENZL",
    "zstd": "ZSTD",
    "Zstd": "ZSTD",
    "zstd/64block": "ZSTD_BLOCK",
    "Zstd, 64-row blocks": "ZSTD_BLOCK",
    "openzl/1kblock": "OPENZL_BLOCK",
    "openzl/block-1024": "OPENZL_BLOCK",
    "openzl/block-65536": "OPENZL_BLOCK",
    "OpenZL, 1K-row blocks": "OPENZL_BLOCK",
    "zstd/block-64": "ZSTD_BLOCK",
    "xz": "XZ",
    "xz_WHOLE": "XZ",
    "lz4": "LZ4",
    "LZ4": "LZ4",
    "snappy": "SNAPPY",
    "Snappy": "SNAPPY",
    "SimdForBitpack/view": "SIMD_FOR",
    "SimdForBitpack": "SIMD_FOR",
    "PFOR/view": "PFOR",
    "PFOR": "PFOR",
    # formats
    "Parquet": "PARQUET",
    "ORC": "ORC",
    "BtrBlocks": "BTRBLOCKS",
    "FastLanes": "FASTLANES",
    "Nimble": "NIMBLE",
    # lightweight codecs (Nimble encoding baselines)
    "FixedBitWidth": "FBW",
    "FixedBitWidth/view": "FBW",
    "FBW": "FBW",
    "Dictionary": "DICT",
    "Dictionary/view": "DICT",
    "Dict": "DICT",
    "RLE": "RLE",
    "RLE/view": "RLE",
    "FPE/fpe_elias": "FPE",
    "FPE/fpe_noindex": "FPE",
    "FPE/fpe_pertier": "FPE",
    "FPE/fpe_tagtag": "FPE",
    "FPE": "FPE",
    "Varint": "VARINT",
    "Delta": "DELTA",
    "Constant": "CONSTANT",
    # ALP
    "ALP": "ALP",
    "ALP/view": "ALP",
    "ALP_rd": "ALP_RD",
    "ALPRD": "ALP_RD",
    "ALP (ref.)": "ALP_REF",
    "ALP_ref": "ALP_REF",
}


def normalize_arm(raw):
    """Map an internal arm/codec string to its canonical entity key.

    Unknown strings raise KeyError with the offending string, by design:
    silently falling back would reintroduce the "invented label" problem
    this module exists to close. Callers that want a soft fallback should
    catch KeyError explicitly and log it for review.
    """
    if raw in _ARM_MAP:
        return _ARM_MAP[raw]
    raise KeyError(f"paperstyle.normalize_arm: no mapping for arm string {raw!r}")


def style_for(raw_or_key):
    """Convenience: normalize (if needed) and return the entity's style dict."""
    key = raw_or_key if raw_or_key in ENTITIES else normalize_arm(raw_or_key)
    return ENTITIES[key]


def label_for(raw_or_key):
    return style_for(raw_or_key)["label"]


def color_for(raw_or_key):
    return style_for(raw_or_key)["color"]


# ---------------------------------------------------------------------------
# Dataset / column display names (paper Table 1 / Table 2 / Section 2 draft)
# ---------------------------------------------------------------------------

DATASET_NAMES = {
    "snowflake": "Snowflake",
    "xmark": "XMark",
    "h3_r9": "OSM h3_r9",
    "osm_h3_r9": "OSM h3_r9",
    "s2_l30": "OSM s2_l30",
    "osm_s2_l30": "OSM s2_l30",
    "publicbi_npi": "PublicBI NPI",
    "publicbi_id1": "PublicBI Id1",
    "instagram": "Instagram",
    "uuidv7_hi": "UUIDv7 high",
    "uuidv7_lo": "UUIDv7 low",
    "tpch_orderkey": "TPC-H orderkey",
    "inat_species_id": "iNaturalist species id",
    "publicbi_drug_cost": "PublicBI drug cost",
    "publicbi_bene_count": "PublicBI beneficiary count",
    "morton_2x16": "Morton (2x16)",
    "morton_2x32": "Morton (2x32)",
    "hashed_splitmix64": "hashed (SplitMix64)",
    "random_uint64": "uniform random",
    "quadkey": "Bing quadkey",
}


def dataset_label(raw):
    return DATASET_NAMES.get(raw, raw)


# ---------------------------------------------------------------------------
# Section 2 study: dataset-identity and structural-category colours.
# These are NOT codec/format entities (not in ENTITIES above), so they get
# their own small qualitative dicts here, picked from Tol muted/vibrant hues
# that do not collide with any hex already used in ENTITIES.
# ---------------------------------------------------------------------------

SECTION2_COLUMN_COLORS = {
    "snowflake":  "#88CCEE",  # Tol muted cyan (unused elsewhere in this module)
    "instagram":  "#AA4499",  # Tol muted purple (unused elsewhere in this module)
    "uuidv7_hi":  "#EE7733",  # Tol vibrant orange (unused elsewhere in this module)
}

# Legend labels per coordinator decision 2026-10-02: plain, caption carries the
# "(not addressable)" qualifier for xz/OpenZL rather than the legend text.
SECTION2_ADDRESSABLE_COLORS = {
    "WHOLE":        {"color": "#0077BB", "label": "whole-value layout"},
    "SPLIT_DATA":   {"color": "#33BBEE", "label": "per-range layout"},
    "XZ":           {"color": "#009988", "label": "xz"},
}

# Section 2 draft (proposal 21) per-column display names. These intentionally
# differ from the headline DATASET_NAMES map for two columns shared with Table
# 1/2 (xmark -> "XMark pre/post" here vs "XMark" there; publicbi_id1 ->
# "PublicBI key" here vs "PublicBI Id1" there) because the Section 2 draft's
# class-study table (tab:class_study_percolumn) uses its own wording for all
# 24 corpus columns. Use section2_dataset_label() for any Section 2 figure
# (flip panels, fig_addressable_vs_xz, fig_addressable_vs_xz_v2); use
# dataset_label()/DATASET_NAMES for Table 1/2-facing figures (Sec. 1, 7).
SECTION2_DATASET_NAMES = {
    "snowflake": "Snowflake",
    "instagram": "Instagram",
    "uuidv7_hi": "UUIDv7 high",
    "h3_r9": "OSM h3_r9",
    "h3_r15": "OSM h3_r15",
    "s2_l16": "OSM s2_l16",
    "s2_l30": "OSM s2_l30",
    "quadkey": "Bing quadkey",
    "xmark": "XMark",
    "publicbi_drug_cost": "Drug cost",
    "publicbi_drug_cost_ge65": "Drug cost ≥65",
    "publicbi_bene_count": "Beneficiary count",
    "publicbi_num_employees": "Employee count",
    "publicbi_day_supply_bin": "Day-supply bin",
    "morton_2x16": "Morton 2x16",
    "morton_2x32": "Morton 2x32",
    "hashed_splitmix64": "SplitMix64 hash",
    "random_uint64": "Uniform random",
    "uuidv7_lo": "UUIDv7 low",
    "publicbi_id1": "PublicBI Id1",
    "tpch_orderkey": "TPC-H orderkey",
    "inat_species_id": "iNaturalist species",
    "publicbi_npi": "PublicBI NPI",
    "ipv4_id": "IPv4",
}
# Decision 26 (2026-10-02, the author): h3_r9/s2_l30/xmark/publicbi_id1/publicbi_npi
# are the 5 keys shared with Table 1 (tab:compression); their display names
# above now match Table 1 exactly ("OSM h3_r9", "OSM s2_l30", "XMark",
# "PublicBI Id1", "PublicBI NPI"). The other keys here (h3_r15, s2_l16,
# morton_*, hashed_splitmix64, random_uint64, uuidv7_lo, tpch_orderkey,
# inat_species_id, publicbi_drug_cost*, publicbi_bene_count,
# publicbi_num_employees, publicbi_day_supply_bin, ipv4_id, quadkey) have no
# Table 1 entry, so there is nothing to reconcile them against; left as-is.


def section2_dataset_label(raw):
    return SECTION2_DATASET_NAMES.get(raw, raw)


# ---------------------------------------------------------------------------
# Shared rcParams: 8pt minimum text, pdf.fonttype 42, no titles.
# ---------------------------------------------------------------------------

def apply_rcparams():
    mpl.rcParams.update({
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "font.size": 8.0,
        "axes.titlesize": 0,  # figures must not carry in-plot titles
        "axes.labelsize": 8.0,
        "xtick.labelsize": 8.0,
        "ytick.labelsize": 8.0,
        "legend.fontsize": 8.0,
        "legend.frameon": False,
        "axes.grid": True,
        "grid.color": "#dddddd",
        "grid.linewidth": 0.5,
        "axes.edgecolor": "#333333",
        "axes.linewidth": 0.6,
    })


# ---------------------------------------------------------------------------
# Compact legend helper
# ---------------------------------------------------------------------------

def legend_handles(keys, kind="line"):
    """Return a list of (handle, label) for the given canonical entity keys,
    in the order given, for a compact shared legend. kind: "line" or "patch"."""
    handles = []
    for k in keys:
        e = ENTITIES[k]
        if kind == "patch":
            h = Patch(facecolor=e["color"], hatch=e["hatch"], edgecolor="#333333", label=e["label"])
        else:
            h = Line2D([0], [0], color=e["color"], marker=e["marker"] or "o",
                       linestyle="-", label=e["label"])
        handles.append((h, e["label"]))
    return handles


# ---------------------------------------------------------------------------
# Sec. 7 short column names (2026-10-17): one label per column in every figure/table.
# ---------------------------------------------------------------------------

SHORT_NAMES = {
    "snowflake": "Snowflake",
    "xmark": "XMark", "xmark_prepost_full": "XMark",
    "h3_r9": "H3", "osm_h3_r9": "H3", "osm_h3_r9_fileorder": "H3",
    "s2_l30": "S2", "osm_s2_l30": "S2", "osm_s2_l30_fileorder": "S2",
    "quadkey": "Bing", "bing_quadkey": "Bing",
    "uuidv7_hi": "UUIDv7-hi", "uuidv7_lo": "UUIDv7-lo",
    "publicbi_npi": "NPI", "publicbi_id1": "Id1",
}


def short_label(raw):
    return SHORT_NAMES[raw]


# ---------------------------------------------------------------------------
# Experimental palettes (2026-10-17). SIS_PALETTE=<name>; default "B" = unchanged.
# Each palette overrides entity colours, gives SIS a distinct marker + larger size
# in line/point plots, and supplies the two diverging maps (fig10 scoreboard stops
# in log10(ratio) units; fig12 read-rate-kept list lost -> neutral -> gained).
# ---------------------------------------------------------------------------

# palette B values, copied from the scripts that hard-coded them (fig10 split, fig12)
_B_SCOREBOARD = {"neutral": "#f0efec",
                 "worse": [(-1.0, "#b04418"), (-0.6, "#eb6834"), (-0.25, "#f5c3ab")],
                 "better": [(0.25, "#cde2fb"), (1.0, "#86b6ef"), (1.6, "#3987e5"), (2.2, "#256abf"), (3.0, "#0d366b")]}

_PALETTES = {
    "B": {"colors": {}, "sis_marker": None, "sis_ms_scale": 1.0, "scoreboard": _B_SCOREBOARD, "fig12_div": None},

    # Okabe-Ito / Wong (Nature Methods 2011): SIS blue (darkened Okabe blue #0072B2 -> #005A8C so it is the
    # darkest series in greyscale), OpenZL vermillion/orange, Zstd bluish green.
    "okabe": {
        "colors": {"SIS_DEFAULT": "#005A8C", "SIS_HYBRID": "#56B4E9", "SIS_BEST": "#2B8CC4",
                   "SIS_AUTO": "#9CD3F2", "SIS_HYBRID_AUTO": "#9CD3F2", "SIS_ZL": "#003F63",
                   "OPENZL": "#D55E00", "OPENZL_BLOCK": "#E69F00", "ZSTD": "#009E73", "ZSTD_BLOCK": "#7FCEB9",
                   "XZ": "#CC79A7", "FBW": "#999999"},
        "sis_marker": "*", "sis_ms_scale": 1.6,
        "scoreboard": {"neutral": "#f2f2f2",
                       "worse": [(-1.0, "#8A3D00"), (-0.6, "#D55E00"), (-0.25, "#F2C6A6")],
                       "better": [(0.25, "#CCE3F2"), (1.0, "#80B8DE"), (1.6, "#3D93CB"), (2.2, "#0072B2"), (3.0, "#00375A")]},
        "fig12_div": ["#8A3D00", "#E69F00", "#EDEDED", "#56B4E9", "#0072B2"]},

    # Paul Tol high-contrast (+ medium-contrast light tints): SIS darkest blue; OpenZL red; Zstd yellow.
    # Built for greyscale: dark blue < red < yellow in lightness.
    "tol_hc": {
        "colors": {"SIS_DEFAULT": "#004488", "SIS_HYBRID": "#6699CC", "SIS_BEST": "#4477AA",
                   "SIS_AUTO": "#A6C4E4", "SIS_HYBRID_AUTO": "#A6C4E4", "SIS_ZL": "#002244",
                   "OPENZL": "#BB5566", "OPENZL_BLOCK": "#EE99AA", "ZSTD": "#DDAA33", "ZSTD_BLOCK": "#EECC66",
                   "XZ": "#997700", "FBW": "#999999"},
        "sis_marker": "*", "sis_ms_scale": 1.6,
        "scoreboard": {"neutral": "#f2f2f2",
                       "worse": [(-1.0, "#7A2E3B"), (-0.6, "#BB5566"), (-0.25, "#EBC4CB")],
                       "better": [(0.25, "#CCDDEE"), (1.0, "#88AACC"), (1.6, "#4477AA"), (2.2, "#004488"), (3.0, "#002244")]},
        "fig12_div": ["#7A2E3B", "#BB5566", "#EDEDED", "#6699CC", "#004488"]},

    # Paul Tol vibrant: SIS the only warm and the only dark series (red); every baseline light and cool
    # (cyan/teal) or light grey, so SIS also leads in greyscale.
    # Diverging maps flip to red = SIS better, blue = SIS worse.
    "vibrant": {
        "colors": {"SIS_DEFAULT": "#CC3311", "SIS_HYBRID": "#EE7733", "SIS_BEST": "#E0603F",
                   "SIS_AUTO": "#F5B183", "SIS_HYBRID_AUTO": "#F5B183", "SIS_ZL": "#7A1E0A",
                   "OPENZL": "#33BBEE", "OPENZL_BLOCK": "#88CCEE", "ZSTD": "#009988", "ZSTD_BLOCK": "#7FCCC3",
                   "XZ": "#EE3377", "FBW": "#BBBBBB"},
        "sis_marker": "*", "sis_ms_scale": 1.6,
        "scoreboard": {"neutral": "#f2f2f2",
                       "worse": [(-1.0, "#004C77"), (-0.6, "#0077BB"), (-0.25, "#B3D6EB")],
                       "better": [(0.25, "#F8D5C8"), (1.0, "#F09A7E"), (1.6, "#E0603F"), (2.2, "#CC3311"), (3.0, "#6E1A08")]},
        "fig12_div": ["#004C77", "#33BBEE", "#EDEDED", "#EE7733", "#CC3311"]},
}

PALETTE = (os.environ.get("SIS_PALETTE", "tol_hc").strip() or "tol_hc")  # 2026-10-17: the author chose tol_hc; SIS_PALETTE=B for the old palette
if PALETTE not in _PALETTES:
    raise KeyError(f"SIS_PALETTE={PALETTE!r}; choose one of {sorted(_PALETTES)}")
_P = _PALETTES[PALETTE]
for _k, _c in _P["colors"].items():
    ENTITIES[_k] = dict(ENTITIES[_k], color=_c)


def sis_marker(default):
    """Marker for the headline SIS series: the script's own marker under palette B."""
    return _P["sis_marker"] or default


def sis_ms(ms):
    return ms * _P["sis_ms_scale"]


def scoreboard_stops():
    """(neutral, worse stops, better stops) for the fig10 diverging map, x in log10(ratio)."""
    s = _P["scoreboard"]
    return s["neutral"], list(s["worse"]), list(s["better"])


def fig12_div_colors():
    """Read-rate-kept diverging map, lost -> 100 % -> gained (palette B: as make_fig12_clarity.py)."""
    if _P["fig12_div"] is not None:
        return list(_P["fig12_div"])
    E = ENTITIES
    return [E["OPENZL"]["color"], E["ZSTD"]["color"], "#EDEDED", E["SIS_BEST"]["color"], E["SIS_DEFAULT"]["color"]]
