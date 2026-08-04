# Canonical full-scope readiness gate

## Canonical design

One EPSG:3763 1 km x 1 km cell-year record uses predictors from T to estimate `burned_share_next_year` in T+1. Training is T=2015–2019; validation T=2020–2021; final temporal test T=2022–2024. The historical-fire window is T-10 through T-1 only. ICNF is never a same-year predictor. ERA5-Land uses T-only JJAS values from the containing 0.1-degree ERA5-Land cell, without interpolation/downscaling.

The 2 km context buffer applies to `forest_shrub_share_2km`, `mean_slope_2km`, and `fire_years_previous_10y_2km`; it does not create a second analytical resolution. The buffered geometry is the 1 km cell geometry expanded outward by 2,000 m in EPSG:3763.

## Required predictors and governance

- Seven predictors: `built_up_share`, `forest_shrub_share_2km`, `mean_slope_2km`, `fire_years_previous_10y_2km`, and the three T-only ERA5 JJAS features.
- Target: `burned_share_next_year`; `burned_next_year` is deferred until target-distribution review.
- CLC metadata must include `land_cover_reference_year`, `land_cover_release_id/version`, and `land_cover_release_date`, and must prove source availability no later than 31 December of T.
- CLC assignment: 2015 uses original archived CLC 2006 only if its availability is proven; 2016–2018 use CLC 2012; 2019 uses original CLC 2018 only if Portugal availability in 2019 is proven, otherwise CLC 2012; 2020–2024 use CLC 2018 V2020_20u1. CLC 2018 is never assigned to 2015–2018.

## Current raw-data readiness

| Source | Required coverage | Local status | Blocker |
|---|---|---|---|
| ICNF annual burned areas | 2005–2025 | 2005–2022 and 2024 present; 2023 and 2025 absent | 2023 and 2025 required for final-test outcomes/history |
| ERA5-Land JJAS | T=2015–2024 | 2015–2021 and 2023 present; 2022 and 2024 absent | final-test climate years 2022 and 2024 |
| Copernicus CLC | governed assignments above | CLC 2018 V2020_20u1 local only | CLC 2006/2012 and release-date evidence absent |
| Copernicus DEM GLO-30 | mainland tiles for 2 km slope buffer | absent | DEM version, licence, tile list, CRS and checksums not registered |
| CAOP | fixed mainland boundary/reporting areas | CAOP 2025 processed reference present | ready |

## Final-test integrity

The existing 2023→2024 artifact is a data-contract/pipeline-feasibility pilot, not the sole final test. No model, target-threshold, hyperparameter, or recommendation decision is documented as having used outcomes from T=2022–2024. Freeze such decisions before final temporal evaluation.

## Acquisition blockers before national panel creation

1. ICNF 2023 and 2025 annual archives.
2. ERA5-Land JJAS 2022 and 2024 original GRIB files.
3. CLC 2006 and 2012 packages plus release-date evidence; 2018 original-release availability evidence for 2019.
4. Copernicus DEM GLO-30 mainland tiles and complete provenance.
