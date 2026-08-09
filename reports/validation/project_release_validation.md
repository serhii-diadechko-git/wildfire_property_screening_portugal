# Public reproducibility and release validation

Validation date: 2026-08-09.

## Purpose

This is a project-facing release check, not an internal assistant log. It
records the evidence a public reviewer needs to set up, inspect, and reproduce
the project without receiving private credentials or a personal file path.

## Current documentation and package checks

| Check | Result |
|---|---|
| Portable source paths | Passed: checked Markdown documentation contains no known personal absolute filesystem path. |
| Markdown links | Passed: 35 tracked Markdown files have zero missing relative links. |
| External documentation links | Official provider, data-policy, DOI, and library pages resolve; direct provider download endpoints remain accompanied by stable catalogue pages. |
| Immutable raw-data policy | Passed: `data/raw/` is Git-ignored; the public manifest lists official access paths and no credential is stored in the repository. |
| Licence boundary | Passed: repository-owned code, notebooks, documentation, and original figures are released under the MIT License; external data remains subject to provider terms. |
| Environment and notebook guidance | Current: Python 3.13, pinned dependencies, VS Code/Jupyter-kernel setup, preflight, API acquisition, validation, and deliberate rebuild are documented in the root README. |
| QGIS projects | Current: the historical project has 5 map layers; the combined 2026 project has 6 map layers. Both use project-relative data paths after a successful rebuild. |
| Presentation | Current: the editable final deck contains 8 slides and 8 note sections; see `presentation_validation.md`. |

## Public workflow

1. Install the pinned environment using the root README.
2. Obtain files directly from official providers using `data/README.md` and
   `data/source_manifest.json`.
3. Run `python scripts/run_project.py --mode preflight`.
4. Run `python scripts/run_project.py --mode acquire-api` only when missing
   API-backed inputs are authorised and local credentials are configured.
5. Run `python scripts/run_project.py --mode validate`.
6. Run `python scripts/run_project.py --mode reproduce --confirm-rebuild` only
   when reproducible local outputs must be generated or refreshed.

The runner writes local, Git-ignored, plain-language stage logs in
`reports/run_logs/`. It never changes existing immutable raw files.

## Release boundary

The retained analytical state is the accepted nine-feature Model V2, its
transparent historical-recurrence benchmark, and the documented annual update
cycle. The 2026 output is a target-free comparative estimate, pending its
independent evaluation when the observed ICNF 2026 outcome is available.

Raw provider data is not mirrored in this repository. Review provider terms
before sharing any raw or adapted dataset; see
`docs/data_licensing_and_attribution.md` and `docs/release_checklist.md`.
