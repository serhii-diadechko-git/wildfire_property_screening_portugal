# Public reproducibility and release validation

Validation date: 2026-08-07

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
| Pinned environment | Passed with Python 3.13 and the versions in `requirements.txt`. VS Code uses the project `ipykernel`; a separate JupyterLab workflow is not required. |
| Notebook verification | Passed: all seven notebooks executed from fresh kernels in numeric order with zero error outputs. Their narrative roles remain separate and their code calls reusable `src/` helpers. |
| Consolidation checks | Passed: 24 focused public-path, notebook, cleanup, diagnostics, QGIS, and presentation tests. The previously recorded full 62-test release suite remains passed; it was not repeated during this final documentation-only pass. |
| Markdown links | Passed: 31 Markdown files checked with zero missing relative links. |
| Presentation | Passed: all 13 slides rendered, template fidelity reported zero issues, and the official overflow test reported no overflow. |
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
