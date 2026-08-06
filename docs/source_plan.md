# Source Plan

> Canonical land-cover governance: use Copernicus CLC, not COS/COSc. The reference year must be no later than predictor year `T`. Use the current official revised package for each historical reference layer: CLC 2006 for `T=2010-2015`, CLC 2012 for `T=2016-2018`, and CLC 2018 for `T=2019-2025`. Record reference year, current package version, package release/update date, URL, licence, checksum, CRS, and coverage. This is retrospective covariate reconstruction, not proof that the revised package was operationally available at `T`. Copernicus DEM GLO-30 supplies static 2 km slope context with version/licence/tile/CRS/checksum provenance.

Collection date for this initial plan: **31 July 2026**.

## Required model sources

These sources support the agreed MVP schema. Optional feature sources are intentionally excluded from the first version.

| Source | Expected fields / products | Access method | Accessibility | Main limitation | Official URL |
|---|---|---|---|---|---|
| ICNF GeoCATALOGO - burned areas 1975-2025 | Annual burned-area polygon geometry and year | Shapefile, KML, WFS, or WMS | Public data with attribution requirements | Shows burned extent, not ignition cause, suppression effectiveness, or property damage | https://geocatalogo.icnf.pt/catalogo_tema5.html |
| Copernicus CLC | Broad built/artificial and forest/shrubland context | Copernicus catalogue/download | Published Copernicus licence and access conditions | Retrospectively assigned broad context, not annual parcel-level land cover; reference year and mapping-unit limits must be retained | https://land.copernicus.eu/en/products/corine-land-cover |
| DGT CAOP | Mainland boundary and municipality/parish boundaries for reporting | OGC API or official download | Available without charge | Administrative versions change; one version must be fixed for the project | https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop |
| Copernicus DEM GLO-30 | Elevation raster used to derive `mean_slope_2km` | Copernicus Data Space download/API | Free access under published licence conditions | Static elevation model; national tile processing must be tested | https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM |
| Copernicus ERA5-Land | JJAS `T`-only mean 2 m temperature, total precipitation, and mean layer-1 soil water | Climate Data Store API/download, NetCDF or GRIB | Free account and licence acceptance required | Coarse regional reanalysis context at about 9 km; use the containing valid ERA5-Land cell, otherwise the validated nearest valid land cell for a water-masked containing cell; no interpolation/downscaling to 1 km | https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land |

## ICNF temporal scope and roles

The expanded model-development and final-test design requires ICNF annual burned-area archives for `2000-2025` inclusive. These local archives are registered with immutable paths, checksums, CRS/schema facts, and derived-only geometry-repair logs.

| Role | Years required | Use in the model panel |
|---|---|---|
| Historical-fire input | `2000-2023` | For each predictor reference year `T` from `2010` through `2024`, calculate `fire_years_previous_10y_2km` from the inclusive pre-`T` window `T-10` through `T-1`. |
| Observed outcome label | `2011-2025` | For each `T` from `2010` through `2024`, calculate `burned_share_next_year` from the observed outcome year `T+1`. |

The labelled nine-feature model panel uses fitting years `2010-2019`, validation years `2020-2021`, and a completed frozen final temporal test at `T=2022-2024`. ICNF burned areas are an outcome source and a strictly pre-`T` historical-fire input; they are never a same-year `T` predictor. No temporal gap is required because the historical-fire window is information genuinely available at prediction time. CLC is broad retrospective land-cover context, not annual parcel-level land cover; its governed reference year is always no later than `T`, while its current revised package version is provenance rather than historical availability evidence. ERA5-Land uses only JJAS observations/reanalysis values from `T`; use the containing valid source cell or, for a water-masked containing cell, the validated deterministic nearest valid land cell, without interpolation.

## Annual operational scoring cycle

For forecast year `Y`, refit the frozen nine-feature model only through labelled predictor year `Y-2` (observed outcome `Y-1`), then derive an unlabelled `T=Y-1` matrix and score `Y`. Do not obtain, derive, or use ICNF `Y` as a predictor or target at scoring time.

| Current stage | Required source years | Local status |
|---|---|---|
| Refit for 2026 estimate | Labelled rows `T=2010-2024`, observed ICNF outcomes 2011-2025 | Complete; model artifact is versioned under `data/processed/final_model_2010_2024/`. |
| Derive/score 2026 estimate | ICNF history 2015-2024; CLC 2018; static DEM; ERA5-Land JJAS 2025 | Complete: validated raw GRIB, unlabelled nine-feature matrix, score table, and QGIS-ready GeoPackage. |
| Next annual cycle for 2027 | New ICNF 2026 outcome for refit; ICNF history 2016-2025; CLC/DEM; ERA5-Land JJAS 2026 | Wait for the two annual sources and validate them before refitting/scoring. |

## Validation and comparison source

| Source | Intended use | Important rule | Official URL |
|---|---|---|---|
| ICNF Structural Wildfire Hazard Map 2020-2030 | External comparison and disagreement flag | Do not use as a training feature because it already represents an official hazard model | https://geocatalogo.icnf.pt/metadados/perigosidade_estrutural_20_30.html |

## Market and competitor research sources

These sources support Exercise 5 and are not model-training data.

| Solution | Role in comparison | URL |
|---|---|---|
| ICNF hazard and burned-area maps | Official structural and historical information | https://geocatalogo.icnf.pt/catalogo_tema5.html |
| MapaFogos | Real-time fire information | https://mapafogos.pt/en/ |
| A Minha Terra | Annual or seasonal susceptibility information | https://perspetiva.aminhaterra.pt/en |
| EFFIS | European wildfire monitoring and risk information | https://effis.emergency.copernicus.eu/ |

## Source acceptance checklist

For every downloaded dataset, record:

- source organisation;
- dataset title and version;
- access date and URL;
- licence or terms;
- geographic and temporal coverage;
- CRS;
- spatial resolution or scale;
- file format;
- field or class definitions;
- missing coverage and warnings;
- checksum or file size where practical.

## Verified processing controls

1. The Portugal-clipped CLC 2006/2012/2018 GeoPackages are validated under `data/processed/clc/`; immutable Europe-wide ZIP lineage is retained under `data/raw/clc/`; `reference_year <= T` is enforced.
2. ICNF archives are schema/CRS/checksum-validated and use a derived-only geometry-repair policy.
3. Copernicus DEM GLO-30 supplies the metric `mean_slope_2km` calculation.
4. ERA5-Land uses T-only JJAS temperature, corrected day-weighted precipitation, and layer-1 soil-water aggregation.
5. The 1 km grid and mainland-masked 2 km context-buffer workflow is validated and restartable.
6. National processing is feasible in bounded batches. The final model refit and its final-test evidence are separate from raw-source preparation.
