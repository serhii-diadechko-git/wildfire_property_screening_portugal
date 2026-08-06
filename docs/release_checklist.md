# Public release checklist

This checklist is for a human maintainer preparing a public clone or release.
It is deliberately separate from the analytical method and does not alter raw
data or model results.

## Before publishing

- [ ] Choose and add a licence for this repository's own code, notebooks, and
      documentation. No code licence is implied until the project owner makes
      that decision.
- [ ] Confirm that no raw data, `.cdsapirc`, API token, local settings, or
      personal path is staged. Run `git status --ignored` and inspect only the
      intended files.
- [ ] Review the current official terms for every source in
      `data/source_manifest.json`. Do not publish raw copies unless those terms
      explicitly permit the intended redistribution.
- [ ] Keep provider attribution and derivative-disclosure requirements with
      published maps and adapted CLC outputs.
- [ ] Run `python scripts/run_project.py --mode preflight` with the local
      source inputs, then `python scripts/run_project.py --mode validate`.
- [ ] Run `git diff --check` and the public-path scan in
      `tests/test_public_reproducibility.py`.

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
