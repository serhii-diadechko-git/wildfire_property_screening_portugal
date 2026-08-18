# Public release checklist

This checklist is for a human maintainer preparing a public clone or release.
It is deliberately separate from the analytical method and does not alter raw
data or model results.

## Before publishing

- [x] Confirm that the repository's own code, notebooks, documentation, and
      original figures are released under the existing [MIT License](../LICENSE).
      This does not grant rights to redistribute provider datasets.
- [x] Confirm that no raw data, `.cdsapirc`, API token, local settings, or
      personal path is staged. Run `git status --ignored` and inspect only the
      intended files.
- [x] Review the current official terms for every source in
      `data/source_manifest.json`. Do not publish raw copies unless those terms
      explicitly permit the intended redistribution.
- [x] Keep provider attribution and derivative-disclosure requirements with
      published maps and adapted CLC outputs.
- [x] Run `python scripts/run_project.py --mode preflight` with the local
      source inputs, then `python scripts/run_project.py --mode validate`.
- [x] If a clean local rebuild is needed, review
      `python scripts/clean_project_outputs.py --dry-run` before using its
      explicit `--confirm-delete-derived` flag. Confirm that `data/raw/` is
      absent from the deletion list.
- [x] Run `git diff --check` and the public-path scan in
      `tests/test_public_reproducibility.py`.

## Verification record

Verified locally on 2026-08-18 before the project demonstration:

| Gate | Result |
|---|---|
| Git and secrets boundary | Passed. Only `data/README.md`, `data/source_manifest.json`, and data-directory placeholders are tracked under `data/`. Raw, interim, processed, credentials, local settings, and run logs remain ignored. No staged files were present. |
| Intended presentation artefacts | The editable final presentation and portable 2026 QGIS project are tracked release artefacts. No raw or processed data are included with them. |
| Source terms and attribution | Passed against `data/source_manifest.json` and `docs/data_licensing_and_attribution.md`. External data remain governed by provider terms and are not included in Git. |
| Preflight | Passed with all six source groups ready and zero missing files. |
| Validation | Passed: 28 essential bootstrap and raw-source contract tests. |
| Cleanup safety | Dry run completed; 76 allow-listed derived paths were reported, `data/raw/` was absent, and nothing was deleted. |
| Public reproducibility scan | Passed: 8 tests, including portable paths, manifest completeness, documented workflow, and platform-neutral commands. |
| Diff hygiene | `git diff --check` passed. |

## What belongs in Git

- Python source under `src/` and `scripts/`, tests, requirements, notebooks,
  Markdown documentation, QGIS projects/styles, and small reproducible
  presentation assets.
- `data/README.md` and `data/source_manifest.json`, but not data files.
- Concise final validation reports that explain the retained nine-feature
  workflow and interpretation boundary.

## What stays local or outside the repository

- `data/raw/`, including all provider downloads and account-gated files.
- `data/interim/` and `data/processed/`, which are reproducible local outputs.
- CDS credentials, tokens, local configuration, temporary files, and run logs.
- Any large binary release asset that has no clear reviewer value. The editable
  capstone presentation may remain versioned; a PDF export is optional and is
  not required for reproducibility.

## Reviewer experience

1. Clone the repository.
2. Create the pinned environment.
3. Obtain raw inputs from official providers and place them using `data/README.md`.
4. Run preflight, then validation, then the explicit rebuild command if desired.
5. Inspect generated reports, notebooks, figures, GeoPackages, and QGIS
   projects.

The project must never imply that a missing data file is a no-fire year, a zero
climate value, or evidence of low exposure.
