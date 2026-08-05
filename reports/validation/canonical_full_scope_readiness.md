# Canonical full-scope acquisition and readiness gate

Updated 2026-08-05. This report is the authoritative gate for national-panel creation. Raw inputs are immutable; no feature derivation or modelling was performed during this acquisition pass.

## Canonical design

One EPSG:3763 1 km x 1 km cell-year record uses predictors from T to estimate `burned_share_next_year` in T+1. Training is T=2015-2019; validation T=2020-2021; final temporal test T=2022-2024. The historical-fire window is T-10 through T-1 only. ICNF is never a same-year predictor. ERA5-Land uses T-only JJAS values from the containing 0.1-degree ERA5-Land cell, without interpolation/downscaling.

The 2 km context buffer applies to `forest_shrub_share_2km`, `mean_slope_2km`, and `fire_years_previous_10y_2km`; it does not create a second analytical resolution. The buffered geometry is the 1 km cell geometry expanded outward by 2,000 m in EPSG:3763.

## Gate summary

| Source | Required coverage | Acquisition/validation status | Panel gate |
|---|---|---|---|
| ICNF annual burned areas | 2005-2025 | All required years are local. New official 2023 and 2025 ZIPs pass checksum, CRC, CRS, schema/year and geometry-presence checks. | Ready, subject to the established derived-only `make_valid` policy. |
| ERA5-Land JJAS | T=2015-2024 | All annual three-variable files are local. Separate precipitation-only 2022 and 2023 GRIBs pass the official by-hour-of-day workaround contract. | Ready; use the corrected precipitation files only for 2022 and 2023. |
| Copernicus CLC | CLC 2006 for T=2015; CLC 2012 for T=2016-2018; CLC 2018 for T=2019-2024 | All three immutable V2020_20u1 raw ZIPs and Portugal-clipped GeoPackages are local, checksum-registered, and validated. | Ready. |
| Copernicus DEM GLO-30 | mainland plus outward 2 km context | 21 required land/coastal COG tiles acquired and validated; one intersecting edge tile is an official ocean/no-source case. | Ready; slope remains intentionally uncomputed. |
| CAOP | fixed mainland boundary/reporting areas | CAOP 2025 remains the fixed grid boundary in EPSG:3763. | Ready. |

**Acquisition gate closed — feature derivation may begin.** This means the canonical raw/prepared source inputs are available and validated; it does not mean that the national panel, final temporal test, or model is ready.

## ICNF 2023 and 2025

Official catalogue: <https://geocatalogo.icnf.pt/catalogo_tema5.html>. The catalogue exposes the annual official endpoints used below. ICNF permits public use with attribution to ICNF, the exact data source, URL and access date. Both ZIPs were retrieved on 2026-08-04 and remain unchanged in `data/raw/wildfire/icnf_burned_areas/`.

| Year | Official endpoint | Raw path | Bytes | SHA-256 | Validation |
|---|---|---|---:|---|---|
| 2023 | <https://si.icnf.pt/shp/ardida_2023> | `data/raw/wildfire/icnf_burned_areas/ardida_2023.zip` | 2,209,582 | `D236FE3B0B1C6DB27FDB2B2098BA32267EA071364EBA9260AA8A3424919295CA` | ZIP CRC passed; required SHP/SHX/DBF/PRJ present; EPSG:3763; 1,736 non-empty Polygon/MultiPolygon features; `Ano=2023`; unique non-null `Cod_SGIF`; 11 source-topology invalid geometries; every feature intersects the CAOP mainland boundary. |
| 2025 | <https://si.icnf.pt/shp/ardida_2025> | `data/raw/wildfire/icnf_burned_areas/ardida_2025.zip` | 5,077,555 | `61EB2DDE27F7E348F3B8302CD0412C7502D5F7C8324F11B68C94A9CEBA10FDC0` | ZIP CRC passed; required SHP/SHX/DBF/PRJ present; EPSG:3763; 2,084 non-empty Polygon/MultiPolygon features; `Ano=2025`; unique non-null `Cod_SGIF`; 2 source-topology invalid geometries; every feature intersects the CAOP mainland boundary. |

The accepted schema includes `Cod_SGIF`, `Ano`, `DH_Inicio`, and `AreaHaSIG`. The 2023 file additionally contains an `id` field. These schema/topology differences are logged, not normalized in raw data. The future derived pipeline must use `make_valid`, retain only non-empty polygonal results, and log repairs/rejections and before/after area.

The previously audited combined 2000-2008 layer supplies 2005-2008 after filtering `Ano`; individual archives supply 2009-2025. Therefore ICNF coverage for the canonical history and outcomes is complete.

## ERA5-Land 2022-2024

Dataset: `reanalysis-era5-land-monthly-means`; product: `monthly_averaged_reanalysis`; request: JJAS, 00:00, `2m_temperature`, `total_precipitation`, `volumetric_soil_water_layer_1`, area `[42.2, -9.6, 36.8, -6.0]`, GRIB. Licence: CDS CC-BY and accepted dataset terms. Retrieval date: 2026-08-04.

| Year | Raw path | SHA-256 | Shared contract | Precipitation status |
|---|---|---|---|---|
| 2022 | `data/raw/climate/era5_land/era5_land_monthly_jjas_2022_mainland_portugal.grib` | `816B12E0F93F109996AA4208EABEB73E3FF6C3694F3867D0A7603E970802E6F0` | GRIB; 4 x 55 x 37; 0.1-degree regular latitude/longitude grid; exact request extent; `2t` K, `tp` m, `swvl1` m3/m3; 1,928 masked values per variable across four months; `stream=moda`, `expver=0001`. | `tp` is encoded `avgad`, step 0-24, but the official known issue makes monthly accumulated fields for Sep 2022-Feb 2024 incorrect. JJAS 2022 is not usable. |
| 2024 | `data/raw/climate/era5_land/era5_land_monthly_jjas_2024_mainland_portugal.grib` | `40A363CD2C265CBB1E0D587F992B638AD96E66DBAF293DB2E3A8ECAA313522E7` | Same grid, variables, units, extent and mask contract. | JJAS is after the March 2024 fix. `tp` uses the corrected `avgas`, step 23-24 encoding and is accepted as an explicit metadata variant. |

Official ECMWF documentation states that `stream=moda` is the monthly mean of daily means and that accumulated fields are per-day quantities. The established JJAS total remains the day-weighted sum in metres times 1,000. The same documentation identifies incorrect accumulated variables from September 2022 through February 2024 and directs affected users to the monthly-by-hour-of-day data at 00:00.

Two separate immutable replacements were retrieved on 2026-08-04 without overwriting the affected originals:

| Year | Corrected raw path | SHA-256 | Validation |
|---|---|---|---|
| 2022 | `data/raw/climate/era5_land/era5_land_monthly_by_hour_00_jjas_total_precipitation_2022_mainland_portugal.grib` | `7AAF9EADA365270AF5F0876C64635F30532E1FD52C961369F82040EA6B670B3B` | 20,112-byte GRIB; four JJAS messages; 4 x 55 x 37 regular 0.1-degree latitude/longitude grid; exact `[42.2, -9.6, 36.8, -6.0]` extent; `tp` only, unit m, `stream=mnth`, `stepType=avgas`, `stepRange=23-24`, `expver=0001`; 1,928 masked values across four months. |
| 2023 | `data/raw/climate/era5_land/era5_land_monthly_by_hour_00_jjas_total_precipitation_2023_mainland_portugal.grib` | `726B7F239862AF6A9011E77617741D344ACE040B8D5DF648336FAEAF7E67D511` | Same request, grid, units, encoding, extent and water-mask contract as the 2022 replacement. |

For 2022 and 2023, temperature and layer-1 soil water remain sourced from the original annual three-variable GRIB, while precipitation is sourced only from the validated replacement. This closes the ERA5-Land acquisition blocker without altering either original file.

## Governed CLC reference layers

Official product pages: [CLC 2006](https://land.copernicus.eu/en/products/corine-land-cover/clc-2006), [CLC 2012](https://land.copernicus.eu/en/products/corine-land-cover/clc-2012), and [CLC 2018](https://land.copernicus.eu/en/products/corine-land-cover/clc2018). Catalogue access date: 2026-08-04. Licence: [Copernicus Land Monitoring Service data policy](https://land.copernicus.eu/en/data-policy), providing full, open and free access with source attribution and adaptation disclosure. The current product pages identify revised `V2020_20u1` packages. Vector status layers use EPSG:3035, 44 classes, a 25 ha minimum mapping unit and 100 m minimum mapping width.

The governing rule is deliberately minimal: the CLC reference year must be no later than predictor year `T`, and the current official revised package is used for each historical reference layer. This is retrospective covariate reconstruction for present-day residential-location screening. It does not claim that the revised package was operationally downloadable at `T`.

| Predictor years | Reference layer and current package | Official package metadata | Local package status |
|---|---|---|---|
| T=2015 | CLC 2006 `V2020_20u1` | Reference year 2006; update year 2020 (exact day unavailable in current official metadata); raw `u2012_clc2006_v2020_20u1_geoPackage.zip`; catalogue dataset UID `d443c86fec2f49e08ff12c7decdbf2af`, file ID `46d516c6-b749-4064-a556-854b85ba5175`. | Raw ZIP: 3,273,013,641 bytes, SHA-256 `A752E0E1415493DAB5931133AF4AFE8104F1166D1D7AB2B22531B683389B1CFB`, 27/27 member CRCs passed. Prepared GeoPackage: `data/processed/clc/u2012_clc2006_v2020_20u1_pt.gpkg`, SHA-256 `3C38FA3F067A0008AB6EB9841AE5A7C482ABA59EC029612E30C7FFEB5B37DDB9`. |
| T=2016-2018 | CLC 2012 `V2020_20u1` | Reference year 2012; update year 2020 (exact day unavailable); raw `u2018_clc2012_v2020_20u1_geoPackage.zip`; catalogue dataset UID `a5ee71470be04d66bcff498f94ceb5dc`, file ID `2c674919-0baf-44d6-9c13-a0a585cbe931`. | Raw ZIP: 3,778,706,973 bytes, SHA-256 `228821CEB49E3D0E22DBC7BEF5F995CDFD3F416C285334833FCFD31F0DB09802`, 27/27 member CRCs passed. Prepared GeoPackage: `data/processed/clc/u2018_clc2012_v2020_20u1_pt.gpkg`, SHA-256 `33D8AACF68FDA6E46B98A247F9344B469401CB0F5DA3B79121A67B013833BA53`. |
| T=2019-2024 | CLC 2018 `V2020_20u1` | Reference year 2018; update year 2020 (exact day unavailable); raw `u2018_clc2018_v2020_20u1_geoPackage.zip`. | Raw ZIP: 3,755,307,202 bytes, SHA-256 `AC302982BE6EA027762CC1973123B452157B0C4AD536BB32167C486448316492`, 28/28 member CRCs passed. Prepared GeoPackage: `data/processed/clc/u2018_clc2018_v2020_20u1_pt.gpkg`, SHA-256 `B0E8F1CDFE9BEB87FC9968D27C16BEFB18E6DC989E786E67A14F259CC7C31509`. |

Prepared-layer validation used bounded 5,000-feature reads. CLC 2006 has 51,555 features and `Code_06`; CLC 2012 has 54,041 and `Code_12`; CLC 2018 has 54,191 and `Code_18`. Each is a readable single-layer GeoPackage in EPSG:3035 containing only valid, non-empty MultiPolygons, with no null, invalid, non-polygonal, or non-mainland-intersecting geometries. Each contains 42 valid observed CLC codes, including every code required for the canonical mapping. Each layer's bounds exactly match the canonical mainland boundary after reprojection, and union comparison found zero missing-mainland and zero outside-mainland area.

On 2026-08-05, final national-build verification found that the prepared CLC 2012 derivative's bytes no longer matched its earlier registered checksum. A complete bounded revalidation reproduced every registered semantic fact above, and the current stable checksum was registered. The reason for the byte-level change cannot be proven from the repository; the immutable raw Copernicus ZIP checksum is unchanged.

Read-only `gpkg_contents` inspection of the expanded official packages independently confirmed the Europe layers `U2012_CLC2006_V2020_20u1`, `U2018_CLC2012_V2020_20u1`, and `U2018_CLC2018_V2020_20u1`, each in EPSG:3035 with the corresponding `Code_06`, `Code_12`, or `Code_18` field. This supports the prepared files' reference-year and `V2020_20u1` lineage.

`data/processed/clc/` is retained because these are project-prepared Portugal clips, while the unchanged official Europe-wide ZIPs remain under `data/raw/clc/`. The exact clipping command/tool and original clipping-boundary file are not embedded in the prepared GeoPackages and therefore remain unverified. Traceability is nevertheless complete at file level: official raw ZIP → user-supplied Portugal clip → checksum-registered prepared GeoPackage → future analytical share derivation. Analytical validation used `data/processed/reference/mainland_boundary_caop2025.gpkg` and proved exact mainland coverage.

The prepared CLC layers remain in EPSG:3035 by design. During feature derivation, reproject the EPSG:3763 1 km cells and outward 2 km context buffers to EPSG:3035 for equal-area CLC intersection; do not treat EPSG:3035 storage as a grid-resolution change.

Canonical broad mapping: `built_up_share` uses codes 111-142 in the artificial-surface branch; `forest_shrub_share_2km` uses 311, 312, 313, 321, 322, 323 and 324. Exact code tuples are auditable in `src/source_registry.py`. Shares must be area-based and must not be described as parcel-level land cover.

Preserved evidence:

- [Official release lineage](https://land.copernicus.eu/en/technical-library/clc-release-lineage/@@download/file): `data/raw/clc/evidence/clc_release_lineage.pdf`, SHA-256 `CBFF53799AD7A73AEB3A83C67DBB5214C3D3D4FEBAD019E5B3B723D071A69941`.
- [Official V20u1 country coverage](https://land.copernicus.eu/en/technical-library/clc-country-coverage-1990-2018-v20u1/@@download/file): `data/raw/clc/evidence/clc_country_coverage_v20u1.pdf`, SHA-256 `5A265ADE38795CF486D839F31CCC8F423DDEC685F2D1B802B748A7A47CF68D7D`.
- [Official nomenclature guidelines](https://land.copernicus.eu/en/technical-library/clc-illustrated-nomenclature-guidelines/@@download/file): `data/raw/clc/evidence/clc_nomenclature_guidelines.pdf`, SHA-256 `8D69D31993481AA334E5391F717EB27558A5290AA039980D06FC5E937CC7F325`.

The preserved release-lineage evidence still records the earlier V17, V18_5_1 and V20 publication history. Those facts remain useful provenance, but exact archived packages are no longer part of the governing acquisition rule.

## Copernicus DEM GLO-30

Source: Copernicus DEM GLO-30 DGED, public 2021 release, distributed as `Copernicus_DSM_COG_10` Cloud Optimized GeoTIFFs. Official description: <https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM>. Licence/terms and public COG access are documented at <https://registry.opendata.aws/copernicus-dem/>. Acquisition date: 2026-08-04.

The CAOP mainland boundary was buffered outward by exactly 2,000 m in EPSG:3763 and transformed to WGS84 only to select source tiles. Its selection bounds are `(-9.5402460460, 36.9436980978, -6.1651935023, 42.1723150969)`. Each acquired tile is a single-band float32 COG in EPSG:4326, 3,600 x 3,600 cells at 1 arc-second (approximately 30 m). Total immutable size is 733,982,495 bytes.

| Tile | SHA-256 | Tile | SHA-256 |
|---|---|---|---|
| N36W008 | `C22117319EC62455978EA2DB4A53CCBE3FB8242F8B06751E0203D244A7777C4B` | N36W009 | `C0263D579D3655CD5C09C20C9E99B3A8888951CE066F2FBD96D73BE4260C649A` |
| N37W008 | `2D9B199976C8C899A2264AA360DFE2451E54DDEC10C814F6029B7EF0549966F3` | N37W009 | `A3EB9F2D344CF407E0DAC80808E2EF4F5D3452E4BA8B00C8D1D1AA274C23D6DF` |
| N38W007 | `AADEE74AAD31B67BC4987C3BACFDAF812F855AE45F813CB03F8633FC44239E09` | N38W008 | `F3CB8C992C4975863CD2204BD15B88ED16A5C383B10A602FE927B53BF327A917` |
| N38W009 | `EA19DC693D73F638A9D50A12E108C211EA39C0BE775D252B45F96DD38066BA9A` | N38W010 | `5679589263F12D21ECE43C475FD7FE17FB69854B41E513CB9AEE25C9441D1C9F` |
| N39W007 | `67E034CC87CD1FECFBBD5FCE631CBE9EFA67F2407E582AAAA064D4F9DF80903A` | N39W008 | `9E598ACA06F934568FFBDD142A02BB1DF9B476973AAD3C6D23A7C32C77902419` |
| N39W009 | `1D57C2D490D68FF64583B54A3297F7C0934A66908C44BFC25C9AAB9576F58412` | N39W010 | `D9EAE6DFB209711E76327DEBB86F5F577F41A5946FB14469E8625E337E7E150B` |
| N40W007 | `BAB932F240C66B54FA5C2C314C3E1F4C222212A06CDF03EDAE298D5447E6ECED` | N40W008 | `BFEE8BBB9A2DB0784BD25ED1B27AB656B2CB30E8BBED47CD116ABC0212DE7BB5` |
| N40W009 | `CD2751FBF2EC30FBB06A7E65D6DC1EDA749B9B01D433ED275DF2453B897FA108` | N41W007 | `BBAD4C516282421B4CC5F2E1E243462613897827206FD79B60A1C7B6627125C9` |
| N41W008 | `860FB53B25E4EBC2A519458E8E457211E808C7F0F10D80A3B0DC4D4C03E22715` | N41W009 | `122E7F63F33715394BC44F792BEF58075CF8D6ADF7115D7A49605D427CE3BD24` |
| N42W007 | `416F52ED4A34068517AD4FE7D20E8142CE10687D425AE3115C58D6E422C03A8F` | N42W008 | `6F9EDB2498C2B09380CFB242E70070D75895FCCA5C6F415B31E14AC5692F639E` |
| N42W009 | `0EF055AE8C70EE79DBD642CB21A07EC5F7591A5390C69227B7B8E56805982658` | | |

`N37W010` intersects only the ocean-side rectangular selection envelope and has no public tile, consistent with the official no-ocean-tile distribution rule. It is not a mainland terrain gap. Future slope processing must mask to CAOP mainland land before the 2 km context aggregation and must not interpret numeric coastal/ocean values as land elevation.

## Remaining acquisition blockers

None. ICNF 2005-2025, ERA5-Land T=2015-2024 including the corrected 2022/2023 precipitation files, the three governed CLC reference layers, Copernicus DEM GLO-30, and CAOP 2025 are locally registered and validated for acquisition readiness.

Feature derivation may begin under the canonical gate. Slope, the combined national panel, the final temporal evaluation, and model training remain intentionally unperformed and must pass their own later validation gates.
