# Public reproducibility and release validation

Validation date: 2026-08-06

## Purpose

This is a project-facing release check, not an internal assistant log. It
records the minimum evidence that a public reviewer can set up, inspect, and
reproduce the project without receiving private credentials or a personal file
path.

## Checks passed

| Check | Result |
|---|---|
| Portable source paths | Passed: public source, notebook, QGIS, and script text contains no known personal absolute path. |
| Local raw-input preflight | Passed locally: 18 ICNF archives, CAOP, 3 CLC packages, 21 DEM tiles, 18 ERA5-Land GRIB records, and the ICNF structural-hazard raster were present. |
| Immutable raw-data policy | Passed: `data/raw/` is Git-ignored; the public manifest lists official access paths and no credential is stored in the repository. |
| Pinned environment | Passed with Python 3.13 and the versions in `requirements.txt`, including JupyterLab 4.6.2. |
| Notebook verification | Passed: the environment notebook has valid structure and Python cells; it is not rewritten by command-line validation. |
| Full test suite | Passed: 62 tests in 232.267 seconds, including raw-source contracts, CLC, ERA5, panel, model, operational, QGIS, presentation, and public-reproducibility checks. |
| Whitespace check | Passed: `git diff --check` reported no errors. |

## Public workflow

1. Install the pinned environment in the root README.
2. Obtain files directly from official providers using `data/README.md` and
   `data/source_manifest.json`.
3. Run `python scripts/run_project.py --mode preflight`.
4. Run `python scripts/run_project.py --mode validate`.
5. Run `python scripts/run_project.py --mode reproduce --confirm-rebuild` only
   when derived outputs must be regenerated.

The runner produces a local, Git-ignored, plain-language stage log in
`reports/run_logs/`. It never downloads gated inputs or changes `data/raw/`.

## Release boundary

The retained analytical state is the nine-feature model and its documented
annual update cycle. Earlier research artefacts are not required to use the
current method. Raw data may not be mirrored or redistributed until the project
owner has checked each provider's current terms; see `docs/release_checklist.md`.

## Remaining maintainer action

Choose a licence for the repository's own code and documentation before making
a public release. This is a governance decision, not a scientific or technical
blocker.
