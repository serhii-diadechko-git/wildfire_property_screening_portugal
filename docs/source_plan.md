# Source Plan

Collection date for this initial plan: **31 July 2026**.

## Required model sources

These sources support the agreed MVP schema. Optional feature sources are intentionally excluded from the first version.

| Source | Expected fields / products | Access method | Accessibility | Main limitation | Official URL |
|---|---|---|---|---|---|
| ICNF GeoCATALOGO - burned areas 1975-2025 | Annual burned-area polygon geometry and year | Shapefile, KML, WFS, or WMS | Public data with attribution requirements | Shows burned extent, not ignition cause, suppression effectiveness, or property damage | https://geocatalogo.icnf.pt/catalogo_tema5.html |
| DGT COS/COSc | Built/artificial land and combined forest/shrubland classes | DGT Open Data, SNIG, OGC services, or official download | Public/open under DGT conditions | Product editions and class definitions must be checked; built-up land is not automatically residential | https://www.dgterritorio.gov.pt/dados-abertos and https://smos.dgterritorio.gov.pt/cartografia-de-uso-e-ocupacao-do-solo |
| DGT CAOP | Mainland boundary and municipality/parish boundaries for reporting | OGC API or official download | Available without charge | Administrative versions change; one version must be fixed for the project | https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop |
| Copernicus DEM GLO-30 | Elevation raster used to derive `mean_slope_2km` | Copernicus Data Space download/API | Free access under published licence conditions | Static elevation model; national tile processing must be tested | https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM |
| Copernicus ERA5-Land | Temperature and precipitation used for warm-season aggregates | Climate Data Store API/download, NetCDF or GRIB | Free account and licence acceptance required | Reanalysis at about 9 km, much coarser than the 1 km analytical grid | https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land |

## ICNF temporal scope and roles

The agreed model design requires ICNF annual burned-area archives for `2004-2025` inclusive. This is a project data requirement, not a statement that every required annual archive has already been collected or its availability confirmed.

| Role | Years required | Use in the model panel |
|---|---|---|
| Historical-fire input | `2004-2023` | For each predictor reference year `T` from `2014` through `2024`, calculate `fire_years_previous_10y_2km` from the inclusive pre-`T` window `T-10` through `T-1`. |
| Observed outcome label | `2015-2025` | For each `T` from `2014` through `2024`, calculate `burned_share_next_year` from the observed outcome year `T+1`. |

The predictor-reference panel is `T = 2014-2024`: training years `2014-2019`, validation years `2020-2021`, and final temporal test years `2022-2024`. ICNF burned areas are an outcome source and a strictly pre-`T` historical-fire input; they are never a same-year `T` predictor. No temporal gap is required because the historical-fire window is information genuinely available at prediction time.

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

## Feasibility risks to resolve first

1. Confirm which COS/COSc editions can be compared consistently.
2. Inspect an ICNF burned-area sample for schema and geometry validity.
3. Test the Copernicus DEM download and `mean_slope_2km` calculation.
4. Test ERA5-Land temperature and precipitation aggregation.
5. Validate the 1 km cell and initial 2 km buffer workflow.
6. Confirm that national processing is feasible within course time and hardware limits.
