# ICNF panel readiness — first model scope

## Scope

- Training predictors: 2015–2021; observed outcomes: 2016–2022.
- Untouched final test: predictor 2023; observed outcome 2024.
- Historical-fire window: `T-10` through `T-1` only.
- ICNF 2023 is not a predictor and ICNF 2025 is out of scope.

## Required annual archives

Training requires the union of history and outcomes for **2005–2022 inclusive**.
The final test requires **2013–2022** history and **2024** as the outcome.

| Years | Status | Role |
|---|---|---|
| 2005–2008 | Present in combined `ardida_2000_2008.zip`; filter on `Ano` in derived processing. | Early training history |
| 2009–2011 | Present as individual ZIP archives. | Training history |
| 2012 | **Absent and unregistered.** | Required training history/outcome support |
| 2013–2022 | Present and audited/registered. | Training history/outcomes; final-test history |
| 2024 | Present and validated/registered. | Final-test outcome only |

The source registry contains no ICNF 2012 record, checksum, or local path. The existing official catalogue reference is `https://geocatalogo.icnf.pt/catalogo_tema5.html`; no download was attempted.

## Derived annual processing plan

For each required year after the missing 2012 archive is obtained and registered:

1. Validate the immutable ZIP and extract Shapefile components only to a system temporary directory.
2. Apply `make_valid` only to derived geometries.
3. Retain only non-empty Polygon/MultiPolygon results; reject only still-invalid, empty, or non-polygonal results.
4. Log input, repaired, rejected counts and before/after area statistics.
5. Dissolve/union annual polygons before grid overlap calculations to avoid double counting.

The existing 2023 → 2024 pilot can remain the untouched final test: it uses 2013–2022 history and the observed 2024 target, with no ICNF 2023 same-year predictor.

## Readiness conclusion

**Not ready for the 2015–2021 training panel solely because ICNF 2012 is missing.** All other required years for this narrowed first-model scope are present and usable after the stated derived-only geometry repair policy.
