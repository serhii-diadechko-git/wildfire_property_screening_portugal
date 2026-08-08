# Backward temporal-extension readiness and completion

Updated 2026-08-05. The approved backward training extension is complete. It preserves immutable raw sources and does not alter or open the approved final temporal test T=2022-2024.

## Recommendation

The earliest feasible additional predictor year is **T=2010**. T=2010-2014 have been added to the isolated training-only panel; the refit uses T=2010-2019 for fitting and keeps validation T=2020-2021 and final test T=2022-2024 unchanged.

T=2009 is not feasible under the existing ten-year historical-fire definition because it needs ICNF history from 1999 through 2008. The local earliest annual coverage is 2000.

## Requirement matrix for an extended training start at T=2010

| Source | Required years / layer | Local state | Extension action before use |
|---|---|---|---|
| ICNF annual burned areas | History 2000-2020 and outcomes 2011-2022 for predictors T=2010-2021 | Registered and validated. `ardida_2000_2008.zip` contains `Ano=2000` through `2008`; individual annual ZIPs are local for 2009 onward. All use EPSG:3763 polygonal geometry. | The combined archive is filtered by `Ano`; derived processing applies the established `make_valid` policy and logs annual repair facts. |
| ERA5-Land monthly means | JJAS T=2010-2014, using 2 m temperature, total precipitation, and layer-1 volumetric soil water | Registered and validated. Five separate immutable 0.1-degree GRIBs are now local under `data/raw/climate/era5_land/`. | The established T-only JJAS derivation and accepted nearest-valid-land fallback are used. |
| Copernicus CLC | CLC 2006 for T=2010-2015 | Already local and validated: `data/raw/clc/u2012_clc2006_v2020_20u1_geoPackage.zip` and `data/processed/clc/u2012_clc2006_v2020_20u1_pt.gpkg`. | Governed T=2010-2014 -> CLC 2006 configuration and tests are in place. |
| DEM GLO-30 / CAOP | Static terrain and fixed mainland geometry | Local and validated for the existing panel. | Reuse unchanged. |

## Official availability evidence

- The [ICNF catalogue](https://geocatalogo.icnf.pt/catalogo_tema5.html) lists burned territory for 1975-2025, offers Shapefile download, and states that the data are open/free with source attribution. The current local 2000-2011 archives must still be checksum-registered and technically validated before analytical use.
- The [ERA5-Land monthly-means catalogue](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-monthly-means?tab=overview) documents global 0.1-degree monthly GRIB data from January 1950 to present, including 2 m temperature, total precipitation, and volumetric soil-water layer 1. CDS account credentials and accepted dataset terms remain required for retrieval.
- The [Copernicus CLC technical summary](https://land.copernicus.eu/en/products/corine-land-cover?tab=technical_summary) documents status layers for 1990, 2000, 2006, 2012, and 2018. The project already holds the governed current revised CLC 2006 package. The project rule remains retrospective covariate reconstruction: CLC reference year must be no later than T; it does not claim that a revised package was operationally downloadable at T.

## Completion evidence

The isolated panel contains 1,069,344 rows: 89,112 canonical cells for each T=2010-2021. T=2015-2021 are exact copies of the validated canonical panel. Final-test row groups were inspected as Parquet metadata only; final-test rows read = 0.

The frozen historical-recurrence baseline and nine-feature two-part burned-share regression model were refit on T=2010-2019 and validated only on T=2020-2021. See `extended_train_validation_panel_2010_2021.md` and `extended_training_model_refit.md` for the validation evidence. No change to the final-test years is proposed.
