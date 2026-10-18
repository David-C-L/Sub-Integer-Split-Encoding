#!/usr/bin/env python3
"""Generate parquet files of geospatial cell IDs from an OpenStreetMap .pbf extract.

Three families of 64-bit spatial ID are produced from the same node coordinates,
each at a fine and a coarse granularity:

  s2_l30      S2 leaf cell id, level 30
  s2_l16      S2 cell id, level 16 (a prefix-ancestor of s2_l30)
  h3_r15      H3 index, resolution 15
  h3_r9       H3 index, resolution 9 (a prefix-ancestor of h3_r15)
  morton_2x32 Morton/Z-order code interleaving 32-bit quantised lon and lat
  morton_2x16 Morton/Z-order code interleaving 16-bit quantised lon and lat

Bit layouts, which is what makes this dataset interesting to a bit-splitting
encoding:

  S2      [63]    unused (always 0)
          [62:61] face, 0..5
          [60:1]  Hilbert curve position, 2 bits per level, 30 levels
          [0]     trailing sentinel 1 bit marking the level
          A cell at level L has its sentinel at bit 2*(30-L), so the low bits
          below the sentinel are zero. Structure is in *digit pairs*.

  H3      [63]    reserved, 0
          [62:59] mode (1 for a cell) and reserved
          [58:56] reserved
          [55:52] base cell number, 0..121
          [51:0]  fifteen 3-bit digits, one per resolution
          Cells coarser than r15 pad unused digits with 7. Structure is a
          *3-bit digit chain*, which does not align to byte boundaries.

  Morton  Bits of the two quantised coordinates strictly interleaved, y in the
          odd positions and x in the even ones. Structure is *strided*, not
          contiguous, which is the case neither the Snowflake nor the XMark
          study exercised.

Two orderings are written. The `fileorder` file preserves .pbf order, which is
roughly insertion order and carries the spatial locality of the source extract.
In the `sorted` file each column is sorted ascending *independently*, because
sorting by s2_l30 induces a different row permutation than sorting by h3_r15,
so no single row order can serve all six columns. Rows in the sorted file are
therefore NOT tuple-aligned across columns; each column stands alone, which is
how a spatial index actually stores its key.

All columns are stored as int64. S2 and Morton values exceed 2**63, so they are
stored bit-preservingly via .view(np.int64) and will appear negative, following
the same convention as Datasets/IPv4/create_ipv4_ids_parquet.py.

Regenerate with:
	../.venv/bin/python generate_osm_spatial_ids.py --rows 10000000
"""

from __future__ import annotations

import argparse
import array
from pathlib import Path

import numpy as np
import pandas as pd

# S2 constants. Position is 2 bits per level over 30 levels.
S2_MAX_LEVEL = 30
S2_POS_BITS = 2 * S2_MAX_LEVEL
S2_LIMIT_IJ = 1 << S2_MAX_LEVEL

# Hilbert curve state machine, transcribed from the S2 reference implementation.
# kSwapMask is 1 and kInvertMask is 2, so orientation is a 2-bit value.
S2_POS_TO_ORIENTATION = np.array([1, 0, 0, 3], dtype=np.uint8)
S2_IJ_TO_POS = np.array(
	[
		[0, 1, 3, 2],
		[0, 3, 1, 2],
		[2, 3, 1, 0],
		[2, 1, 3, 0],
	],
	dtype=np.uint8,
)

COLUMNS = ("s2_l30", "s2_l16", "h3_r15", "h3_r9", "morton_2x32", "morton_2x16")


def read_node_coordinates(pbf: Path, rows: int) -> tuple[np.ndarray, np.ndarray]:
	"""Stream the first `rows` node coordinates out of a .pbf extract.

	Only nodes carry coordinates directly, so ways and relations are ignored.
	Coordinates accumulate into array.array rather than a Python list to keep
	the peak footprint near 16 bytes per node; a full uncompressed dump of the
	extract would not fit the available disk.
	"""
	import osmium

	lons = array.array("d")
	lats = array.array("d")

	class _NodeCollector(osmium.SimpleHandler):
		def node(self, n) -> None:
			if len(lons) >= rows:
				raise StopIteration
			location = n.location
			if not location.valid():
				return
			lons.append(location.lon)
			lats.append(location.lat)

	handler = _NodeCollector()
	print(f"Reading nodes from {pbf} (target rows={rows:,})")
	try:
		handler.apply_file(str(pbf))
	except (StopIteration, RuntimeError):
		# pyosmium wraps the StopIteration raised inside the callback.
		pass

	if len(lons) < rows:
		raise RuntimeError(f"Extract yielded only {len(lons):,} valid nodes, need {rows:,}")

	lon = np.frombuffer(lons, dtype=np.float64, count=rows).copy()
	lat = np.frombuffer(lats, dtype=np.float64, count=rows).copy()
	print(f"Read {rows:,} node coordinates")
	return lon, lat


def _spread_bits(v: np.ndarray) -> np.ndarray:
	"""Spread the low 32 bits of each value into every other bit position.

	The canonical shift/mask ladder, so interleaving a whole column costs a
	handful of vector operations rather than a loop over bits.
	"""
	v = v.astype(np.uint64, copy=True) & np.uint64(0xFFFFFFFF)
	v = (v | (v << np.uint64(16))) & np.uint64(0x0000FFFF0000FFFF)
	v = (v | (v << np.uint64(8))) & np.uint64(0x00FF00FF00FF00FF)
	v = (v | (v << np.uint64(4))) & np.uint64(0x0F0F0F0F0F0F0F0F)
	v = (v | (v << np.uint64(2))) & np.uint64(0x3333333333333333)
	v = (v | (v << np.uint64(1))) & np.uint64(0x5555555555555555)
	return v


def morton_codes(lon: np.ndarray, lat: np.ndarray, bits: int) -> np.ndarray:
	"""Quantise lon/lat to `bits` each and interleave into a Morton code."""
	scale = float(1 << bits)
	x = np.clip(((lon + 180.0) / 360.0) * scale, 0.0, scale - 1.0).astype(np.uint64)
	y = np.clip(((lat + 90.0) / 180.0) * scale, 0.0, scale - 1.0).astype(np.uint64)
	return _spread_bits(x) | (_spread_bits(y) << np.uint64(1))


def deinterleave_uint64(code: np.ndarray, bits: int) -> tuple[np.ndarray, np.ndarray]:
	"""Recover the two quantised coordinates from a Morton code."""
	x = np.zeros(code.shape, dtype=np.uint64)
	y = np.zeros(code.shape, dtype=np.uint64)
	for b in range(bits):
		x |= ((code >> np.uint64(2 * b)) & np.uint64(1)) << np.uint64(b)
		y |= ((code >> np.uint64(2 * b + 1)) & np.uint64(1)) << np.uint64(b)
	return x, y


def _latlng_to_face_uv(lon: np.ndarray, lat: np.ndarray):
	"""Project lon/lat onto the S2 cube, returning face and (u, v)."""
	lat_rad = np.radians(lat)
	lon_rad = np.radians(lon)
	cos_lat = np.cos(lat_rad)
	x = cos_lat * np.cos(lon_rad)
	y = cos_lat * np.sin(lon_rad)
	z = np.sin(lat_rad)

	abs_xyz = np.stack((np.abs(x), np.abs(y), np.abs(z)))
	axis = np.argmax(abs_xyz, axis=0)
	xyz = np.stack((x, y, z))
	largest = np.take_along_axis(xyz, axis[None, :], axis=0)[0]
	face = np.where(largest < 0.0, axis + 3, axis).astype(np.uint8)

	u = np.empty_like(x)
	v = np.empty_like(x)
	# ValidFaceXYZtoUV from the S2 reference implementation, one branch per face.
	projections = (
		(y, x, z, x),
		(-x, y, z, y),
		(-x, z, -y, z),
		(z, x, y, x),
		(z, y, -x, y),
		(-y, z, -x, z),
	)
	for f, (num_u, den_u, num_v, den_v) in enumerate(projections):
		mask = face == f
		if not np.any(mask):
			continue
		u[mask] = num_u[mask] / den_u[mask]
		v[mask] = num_v[mask] / den_v[mask]
	return face, u, v


def _uv_to_st(w: np.ndarray) -> np.ndarray:
	"""S2 quadratic projection from cube coordinate to unit-square coordinate."""
	# Both branches are evaluated by np.where, so fold the sign into the
	# radicand first rather than taking the square root of a negative.
	positive = w >= 0.0
	root = 0.5 * np.sqrt(np.where(positive, 1.0 + 3.0 * w, 1.0 - 3.0 * w))
	return np.where(positive, root, 1.0 - root)


def _st_to_ij(s: np.ndarray) -> np.ndarray:
	"""S2 STtoIJ: round to the nearest cell index and clamp to the face."""
	ij = np.floor(S2_LIMIT_IJ * s)
	return np.clip(ij, 0, S2_LIMIT_IJ - 1).astype(np.uint64)


def s2_cell_ids(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
	"""Compute S2 level-30 leaf cell IDs, vectorised over the whole column."""
	face, u, v = _latlng_to_face_uv(lon, lat)
	i = _st_to_ij(_uv_to_st(u))
	j = _st_to_ij(_uv_to_st(v))

	# Walk the Hilbert curve from the most significant bit down, accumulating
	# two position bits per level. Orientation is seeded from the face, matching
	# S2's `bits = face & kSwapMask`.
	pos = np.zeros(lon.shape, dtype=np.uint64)
	orientation = (face & 1).astype(np.uint8)
	for level in range(S2_MAX_LEVEL - 1, -1, -1):
		shift = np.uint64(level)
		bit_i = ((i >> shift) & np.uint64(1)).astype(np.uint8)
		bit_j = ((j >> shift) & np.uint64(1)).astype(np.uint8)
		ij = (bit_i << np.uint8(1)) | bit_j
		quadrant = S2_IJ_TO_POS[orientation, ij]
		pos = (pos << np.uint64(2)) | quadrant.astype(np.uint64)
		orientation = orientation ^ S2_POS_TO_ORIENTATION[quadrant]

	return (face.astype(np.uint64) << np.uint64(S2_POS_BITS + 1)) | (pos << np.uint64(1)) | np.uint64(1)


def s2_parent(cell_ids: np.ndarray, level: int) -> np.ndarray:
	"""Return the ancestor of each S2 cell at `level`, by pure bit arithmetic."""
	lsb = np.uint64(1) << np.uint64(2 * (S2_MAX_LEVEL - level))
	return (cell_ids & ~(lsb - np.uint64(1))) | lsb


def h3_indices(lon: np.ndarray, lat: np.ndarray, resolution: int) -> np.ndarray:
	"""Compute H3 indices at `resolution` as unsigned 64-bit integers."""
	from h3.api import numpy_int as h3n

	out = np.empty(lat.shape, dtype=np.uint64)
	for idx, (la, lo) in enumerate(zip(lat.tolist(), lon.tolist())):
		out[idx] = h3n.latlng_to_cell(la, lo, resolution)
	return out


def h3_parents(cells: np.ndarray, resolution: int) -> np.ndarray:
	"""Return the H3 ancestor of each cell at `resolution`."""
	from h3.api import numpy_int as h3n

	out = np.empty(cells.shape, dtype=np.uint64)
	for idx, c in enumerate(cells.tolist()):
		out[idx] = h3n.cell_to_parent(c, resolution)
	return out


def validate(columns, lon: np.ndarray, lat: np.ndarray, sample: int, seed: int) -> None:
	"""Check every derived column against a reference implementation.

	This is the correctness gate. The S2 derivation above is hand-written, so it
	is checked for exact equality against s2sphere rather than for approximate
	agreement. Nothing is written if any check fails.
	"""
	import s2sphere
	from h3.api import numpy_int as h3n

	rng = np.random.default_rng(seed)
	idx = rng.choice(len(lon), size=min(sample, len(lon)), replace=False)
	print(f"Validating {len(idx):,} sampled rows against s2sphere and h3")

	for k in idx.tolist():
		expected = s2sphere.CellId.from_lat_lng(
			s2sphere.LatLng.from_degrees(float(lat[k]), float(lon[k]))
		)
		got = int(columns["s2_l30"][k])
		if got != expected.id():
			raise AssertionError(f"s2_l30 mismatch at row {k}: got {got}, want {expected.id()}")
		want_parent = expected.parent(16).id()
		if int(columns["s2_l16"][k]) != want_parent:
			raise AssertionError(f"s2_l16 mismatch at row {k}")

		want_h3_parent = h3n.cell_to_parent(int(columns["h3_r15"][k]), 9)
		if int(columns["h3_r9"][k]) != want_h3_parent:
			raise AssertionError(f"h3_r9 mismatch at row {k}")
		if not h3n.is_valid_cell(int(columns["h3_r15"][k])):
			raise AssertionError(f"h3_r15 invalid at row {k}")

	for bits, name in ((32, "morton_2x32"), (16, "morton_2x16")):
		scale = float(1 << bits)
		want_x = np.clip(((lon[idx] + 180.0) / 360.0) * scale, 0.0, scale - 1.0).astype(np.uint64)
		want_y = np.clip(((lat[idx] + 90.0) / 180.0) * scale, 0.0, scale - 1.0).astype(np.uint64)
		got_x, got_y = deinterleave_uint64(columns[name][idx], bits)
		if not np.array_equal(got_x, want_x) or not np.array_equal(got_y, want_y):
			raise AssertionError(f"{name} failed de-interleave round-trip")

	print("Validation passed")


def describe(name: str, values: np.ndarray) -> None:
	significant = int(values.max()).bit_length()
	print(
		f"  {name:<12} rows={values.size:,} min={int(values.min())} max={int(values.max())} "
		f"distinct={np.unique(values).size:,} significant_bits={significant}"
	)


def main() -> None:
	parser = argparse.ArgumentParser(description="Generate S2/H3/Morton spatial ID parquet files from an OSM extract")
	parser.add_argument(
		"--pbf",
		type=Path,
		default=Path(__file__).parent / "great-britain-latest.osm.pbf",
		help="Source OpenStreetMap .pbf extract",
	)
	parser.add_argument("--rows", type=int, default=10_000_000, help="Number of nodes to take")
	parser.add_argument("--outdir", type=Path, default=Path(__file__).parent, help="Output directory")
	parser.add_argument("--sample-check", type=int, default=1000, help="Rows to validate against reference libraries")
	parser.add_argument("--seed", type=int, default=42, help="Seed for the validation sample")
	args = parser.parse_args()

	if not args.pbf.exists():
		raise FileNotFoundError(f"PBF not found: {args.pbf}")

	lon, lat = read_node_coordinates(args.pbf, args.rows)

	print("Computing spatial IDs")
	s2_l30 = s2_cell_ids(lon, lat)
	h3_r15 = h3_indices(lon, lat, 15)
	columns = {
		"s2_l30": s2_l30,
		"s2_l16": s2_parent(s2_l30, 16),
		"h3_r15": h3_r15,
		"h3_r9": h3_parents(h3_r15, 9),
		"morton_2x32": morton_codes(lon, lat, 32),
		"morton_2x16": morton_codes(lon, lat, 16),
	}

	validate(columns, lon, lat, args.sample_check, args.seed)

	args.outdir.mkdir(parents=True, exist_ok=True)

	print("File-order columns:")
	for name in COLUMNS:
		describe(name, columns[name])
	fileorder = pd.DataFrame({name: columns[name].view(np.int64) for name in COLUMNS})
	fileorder_path = args.outdir / "osm_gb_spatial_ids_fileorder.parquet"
	fileorder.to_parquet(fileorder_path, index=False)
	print(f"Wrote {fileorder_path} (rows={len(fileorder):,})")

	# Each column is sorted on its own, so rows are not tuple-aligned here.
	sorted_frame = pd.DataFrame({name: np.sort(columns[name]).view(np.int64) for name in COLUMNS})
	sorted_path = args.outdir / "osm_gb_spatial_ids_sorted.parquet"
	sorted_frame.to_parquet(sorted_path, index=False)
	print(f"Wrote {sorted_path} (rows={len(sorted_frame):,}, each column sorted independently)")


if __name__ == "__main__":
	main()
