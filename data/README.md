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
   root. It reports missing files before any derived processing starts.

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

## Derived data

`data/interim/` and `data/processed/` are derived and Git-ignored. They are
created by the reproducible pipeline after source preflight succeeds. Their
published checksums, validation reports, and provenance are recorded in
`reports/validation/` and `reports/run_logs/`.
