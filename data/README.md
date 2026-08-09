# Data access and placement

The repository intentionally contains no raw source data, account credentials,
or redistributed copies of datasets whose terms have not been independently
reviewed for redistribution. The `data/raw/` directory is local-only and is
ignored by Git.

## Before running the project

1. Read [`source_manifest.json`](source_manifest.json).
2. Obtain every required source from its official provider using your own
   account where one is required.
3. Accept provider terms yourself; never share a CDS token or login details.
4. Put each untouched file in the exact relative path listed in the manifest.
5. Run `python scripts/run_project.py --mode preflight` from the repository
   root. It reports missing raw files before any derived processing starts.

For CLC, provide the three original Europe-wide ZIP packages under
`data/raw/clc/`. You may also copy the exact validated Portugal-clipped
GeoPackages into `data/processed/clc/` to avoid repeating the expensive clip.
Preflight still checks the immutable raw ZIPs; the CLC validation checks the
prepared GeoPackages. The rebuild reuses complete prepared layers and creates
missing layers from the raw packages and the CAOP mainland boundary. Use only
the registered filenames. Do not use an unverified manual clip or overwrite a
prepared file silently.

The runner validates registered filenames and checksums where a project
checksum is available. It never downloads a gated dataset, writes into
`data/raw/`, renames a raw file, or treats a missing annual file as a no-fire
year.

## Redistribution policy

This project is a code-and-methods repository, not a data mirror.

- **ICNF burned-area data:** the official ICNF catalogue states that, unless
  indicated otherwise, its geographic information is provided free of charge
  as open data and must be attributed. The project still directs users to the
  official catalogue rather than mirroring files.
- **Copernicus Land Monitoring Service data:** the official policy describes
  full, free and open access, with source attribution and adaptation disclosure
  when distributed. The project records the official source and attribution
  requirements in the manifest.
- **ERA5-Land:** access requires a CDS account and acceptance of the dataset
  terms. Each user must retrieve their own GRIB files with their own local
  credentials; this repository does not redistribute them.
- **CAOP and the official ICNF structural-hazard product:** use the official
  source and its current terms. The project does not claim redistribution
  permission beyond what the provider explicitly publishes.

The manifest intentionally labels any unresolved redistribution status as
`review_before_redistribution`. Do not use a personal Google Drive as a public
mirror unless the relevant provider terms have been reviewed and allow that
specific redistribution. A private backup is a personal storage choice, not a
project dependency.

## Local-only credentials

For CDS, place credentials in the provider-supported local file (for example
`~/.cdsapirc` on Linux/macOS or `%USERPROFILE%\\.cdsapirc` on Windows). Do not
place credentials inside this repository. The ERA5 downloader defaults to a
dry run and requires an explicit `--download` flag.

The public acquisition wrapper for the API-backed inputs is:

```text
python scripts/run_project.py --mode acquire-api
```

It retrieves missing ERA5-Land annual JJAS files (including the corrected
2022/2023 precipitation files) through CDS and the registered ICNF
structural-hazard raster through WCS. It does not overwrite existing immutable
raw files. Run `python scripts/run_project.py --mode preflight` afterwards.

## Derived data

`data/interim/` and `data/processed/` are derived and Git-ignored. They are
created by the reproducible pipeline after source preflight succeeds. Their
published checksums, validation reports, and provenance are recorded in
`reports/validation/` and `reports/run_logs/`.

Small synthetic test fixtures or a clearly labelled tiny example subset may be
versioned under `tests/fixtures/` or `data/examples/` when they help reviewers
run a lightweight check. The canonical grid, provider downloads, and large
derived GeoPackages remain local and reproducible rather than being committed.

The reference-preparation stage is run automatically by
`python scripts/run_project.py --mode reproduce --confirm-rebuild`. It creates
or reuses
the canonical 89,112-cell EPSG:3763 1 km mainland grid in
`data/processed/reference/` from the CAOP boundary whenever that derived grid
is absent.

The CLC preparation step is also run automatically by
`python scripts/run_project.py --mode reproduce --confirm-rebuild`. It creates
the three mainland Portugal GeoPackages in `data/processed/clc/` before CLC
source validation and feature derivation. They are intentionally local derived
artifacts (about 120–150 MB each), not files distributed with the repository.

For expected first-run duration, safe API retries, interrupted builds, QGIS
layer checks, and local run-log locations, see
[`../docs/troubleshooting.md`](../docs/troubleshooting.md).
