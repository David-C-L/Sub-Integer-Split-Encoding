# Sub-Integer Split Encoding: Exploiting Structure in Fixed-Width Values

Reproducibility artifact for the paper of this title (anonymous submission). It contains the SIS implementation
(as patches against public Nimble/Velox, BtrBlocks and FastLanes), the measurement data behind every figure, table
and quoted number, the scripts that turn the data into the paper's figures and tables, and the scripts that ran
the benchmarks.

## Layout
```
README.md            this file
MAPPING.md           paper item -> data -> script -> command, reproduction status, known differences
code/                SIS in Nimble (Velox), BtrBlocks and FastLanes: sis.patch + changed files (code/README.md)
data/                raw benchmark CSVs and logs per experiment (data/README.md); large folders as .tar.gz
derived/             intermediates rebuilt from data/ by scripts/derive_all.sh (one hand-read CSV is shipped)
datasets/            how to obtain each input column; columns_524k/ = redistributable 524,288-row prefixes
figures/             the PDFs and table .tex files exactly as they stand in the paper, for checking
scripts/plot/        figure and table scripts (paperstyle.py: colours and labels; artifact_paths.py: paths)
scripts/derive/      scripts that build derived/ and quoted numbers from data/, and the Sec. 2 study scripts
scripts/run/         benchmark driver scripts with all flags, as run on the benchmark host
scripts/unpack_data.sh, derive_all.sh, regenerate_all.sh, check_against_paper.sh, pixel_compare.py
requirements.txt     plotting environment; requirements-derive.txt: dataset derivation and Sec. 2 study
```

## Quick start
```
scripts/unpack_data.sh                                  # restore data/**/<folder>.tar.gz (idempotent)
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
PYTHON=.venv/bin/python scripts/regenerate_all.sh       # unpack, derive, plot, then check against figures/
scripts/check_against_paper.sh                          # the comparison step alone
```
Outputs go to `out/` (`SIS_FIG_OUT` changes it; `SIS_ARTIFACT_ROOT` if a script runs from outside this tree).
`MAPPING.md` gives the individual command for each item. The checks need poppler-utils (`pdftotext`, `pdfinfo`,
`pdftoppm`). `scripts/unpack_data.sh --columns` also decompresses the dataset prefixes (only the dataset and Sec. 2
study scripts read them).

Result on a fresh copy of this tree (Python 3.12.3, matplotlib 3.6.3, numpy 1.26.4, pandas 3.0.2, Pillow 10.2.0,
poppler 24.02, Ubuntu 24.04): every figure PDF placed in the paper matches its copy in `figures/` in text and page
size and is pixel-identical at 100 dpi (including the Sec. 2 flip panels), and all five tables match (Table 1
body rows, Table 2 whitespace-normalised, the composition, planner-gap and admission tables as identical tex).
Five statements in the paper text differ from the data; `MAPPING.md` lists them with the reproduced values.

## Code
`code/README.md`: how to apply `sis.patch` to Velox `235512ebf` and build the `nimble_ml_id_*_benchmark` drivers
and tests (GCC 11.4.0, `-O3 -DNDEBUG`), how to build the BtrBlocks and FastLanes ports, which code state produced
which data, and the revision labels (`rev-*`) used in place of private commit hashes.

## Hardware (all timings)
Two Intel Xeon Silver 4114 at 2.20 GHz (20 cores), 188 GiB memory, 13.75 MiB L3 cache per socket, Ubuntu 22.04,
GCC 11.4.0 at `-O3 -DNDEBUG`. Timed runs held an exclusive lock on the host, repeats are interleaved across
configurations, and each value is the median of three repeats. Throughput is measured on 524,288-row prefixes in a
hot cache unless the file name says `cold`.

## Licences
- Scripts, data produced by our benchmarks, and documentation: MIT (`LICENSE`).
- `code/velox-nimble/`: derived from Velox/Nimble, Apache-2.0 (`code/velox-nimble/LICENSE`, `NOTICE.txt`; the Velox
  file headers are kept). `code/btrblocks/` and `code/fastlanes/`: derived from BtrBlocks and FastLanes, MIT, with
  their own copyright notices (`code/*/LICENSE`).
- `datasets/columns_524k/`: each file keeps the licence of its source (`datasets/columns_524k/NOTICE`): OpenStreetMap
  derivatives (H3, S2, Morton) under ODbL 1.0 (share-alike, not MIT); DB-IP (IPv4) and the Twitter (Zenodo 7717006)
  and INFORE stock data under CC BY 4.0; WFP food prices under CC BY-IGO; HRSL (Bing quadkeys) MIT; GBIF/iNaturalist
  species keys credited to their sources; NPI is a public US government record. Instagram, the other Public BI
  columns, TPC-H, and the Kaggle and NEON float columns are not redistributed; `datasets/README.md` says how to
  obtain them.
- No production or proprietary data is included.
