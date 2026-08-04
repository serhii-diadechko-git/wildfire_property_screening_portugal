# Canonical full-scope acquisition and readiness gate

Updated 2026-08-04. This report is the authoritative gate for national-panel creation. Raw inputs are immutable; no feature derivation or modelling was performed during this acquisition pass.

## Canonical design

One EPSG:3763 1 km x 1 km cell-year record uses predictors from T to estimate `burned_share_next_year` in T+1. Training is T=2015-2019; validation T=2020-2021; final temporal test T=2022-2024. The historical-fire window is T-10 through T-1 only. ICNF is never a same-year predictor. ERA5-Land uses T-only JJAS values from the containing 0.1-degree ERA5-Land cell, without interpolation/downscaling.

The 2 km context buffer applies to `forest_shrub_share_2km`, `mean_slope_2km`, and `fire_years_previous_10y_2km`; it does not create a second analytical resolution. The buffered geometry is the 1 km cell geometry expanded outward by 2,000 m in EPSG:3763.

## Gate summary

| Source | Required coverage | Acquisition/validation status | Panel gate |
|---|---|---|---|
| ICNF annual burned areas | 2005-2025 | All required years are local. New official 2023 and 2025 ZIPs pass checksum, CRC, CRS, schema/year and geometry-presence checks. | Ready, subject to the established derived-only `make_valid` policy. |
| ERA5-Land JJAS | T=2015-2024 | All annual files are local. 2024 is valid after the official March 2024 fix. The official known accumulated-variable issue affects JJAS precipitation in 2022 and 2023. | **Blocked for precipitation in 2022 and 2023.** |
| Copernicus CLC | governed release assignments | Release dates are proven and preserved. V2020_20u1 is local and validated. Exact historical V17, V18_5_1 and V20 vector packages are not exposed by the current official catalogue and are not local. | **Blocked on archived historical packages.** |
| Copernicus DEM GLO-30 | mainland plus outward 2 km context | 21 required land/coastal COG tiles acquired and validated; one intersecting edge tile is an official ocean/no-source case. | Ready; slope remains intentionally uncomputed. |
| CAOP | fixed mainland boundary/reporting areas | CAOP 2025 remains the fixed grid boundary in EPSG:3763. | Ready. |

The national panel and final temporal test are **not ready** while the ERA5-Land and CLC blockers remain.

## ICNF 2023 and 2025

Official catalogue: <https://geocatalogo.icnf.pt/catalogo_tema5.html>. The catalogue exposes the annual official endpoints used below. ICNF permits public use with attribution to ICNF, the exact data source, URL and access date. Both ZIPs were retrieved on 2026-08-04 and remain unchanged in `data/raw/wildfire/icnf_burned_areas/`.

| Year | Official endpoint | Raw path | Bytes | SHA-256 | Validation |
|---|---|---|---:|---|---|
| 2023 | <https://si.icnf.pt/shp/ardida_2023> | `data/raw/wildfire/icnf_burned_areas/ardida_2023.zip` | 2,209,582 | `D236FE3B0B1C6DB27FDB2B2098BA32267EA071364EBA9260AA8A3424919295CA` | ZIP CRC passed; required SHP/SHX/DBF/PRJ present; EPSG:3763; 1,736 non-empty Polygon/MultiPolygon features; `Ano=2023`; unique non-null `Cod_SGIF`; 11 source-topology invalid geometries; every feature intersects the CAOP mainland boundary. |
| 2025 | <https://si.icnf.pt/shp/ardida_2025> | `data/raw/wildfire/icnf_burned_areas/ardida_2025.zip` | 5,077,555 | `61EB2DDE27F7E348F3B8302CD0412C7502D5F7C8324F11B68C94A9CEBA10FDC0` | ZIP CRC passed; required SHP/SHX/DBF/PRJ present; EPSG:3763; 2,084 non-empty Polygon/MultiPolygon features; `Ano=2025`; unique non-null `Cod_SGIF`; 2 source-topology invalid geometries; every feature intersects the CAOP mainland boundary. |

The accepted schema includes `Cod_SGIF`, `Ano`, `DH_Inicio`, and `AreaHaSIG`. The 2023 file additionally contains an `id` field. These schema/topology differences are logged, not normalized in raw data. The future derived pipeline must use `make_valid`, retain only non-empty polygonal results, and log repairs/rejections and before/after area.

The previously audited combined 2000-2008 layer supplies 2005-2008 after filtering `Ano`; individual archives supply 2009-2025. Therefore ICNF coverage for the canonical history and outcomes is complete.

## ERA5-Land 2022 and 2024

Dataset: `reanalysis-era5-land-monthly-means`; product: `monthly_averaged_reanalysis`; request: JJAS, 00:00, `2m_temperature`, `total_precipitation`, `volumetric_soil_water_layer_1`, area `[42.2, -9.6, 36.8, -6.0]`, GRIB. Licence: CDS CC-BY and accepted dataset terms. Retrieval date: 2026-08-04.

| Year | Raw path | SHA-256 | Shared contract | Precipitation status |
|---|---|---|---|---|
| 2022 | `data/raw/climate/era5_land/era5_land_monthly_jjas_2022_mainland_portugal.grib` | `816B12E0F93F109996AA4208EABEB73E3FF6C3694F3867D0A7603E970802E6F0` | GRIB; 4 x 55 x 37; 0.1-degree regular latitude/longitude grid; exact request extent; `2t` K, `tp` m, `swvl1` m3/m3; 1,928 masked values per variable across four months; `stream=moda`, `expver=0001`. | `tp` is encoded `avgad`, step 0-24, but the official known issue makes monthly accumulated fields for Sep 2022-Feb 2024 incorrect. JJAS 2022 is not usable. |
| 2024 | `data/raw/climate/era5_land/era5_land_monthly_jjas_2024_mainland_portugal.grib` | `40A363CD2C265CBB1E0D587F992B638AD96E66DBAF293DB2E3A8ECAA313522E7` | Same grid, variables, units, extent and mask contract. | JJAS is after the March 2024 fix. `tp` uses the corrected `avgas`, step 23-24 encoding and is accepted as an explicit metadata variant. |

Official ECMWF documentation states that `stream=moda` is the monthly mean of daily means and that accumulated fields are per-day quantities. The established JJAS total remains the day-weighted sum in metres times 1,000. However, the same documentation identifies incorrect accumulated variables from September 2022 through February 2024. This also invalidates precipitation in the existing 2023 pilot GRIB for national-panel use; temperature and layer-1 soil water are unaffected.

Smallest safe corrective acquisition: retrieve **only total precipitation** for 2022 and 2023 from the same dataset using `monthly_averaged_reanalysis_by_hour_of_day` at 00:00, JJAS and the same area, following ECMWF's documented workaround. Save each as a new immutable annual GRIB and validate separately. Do not overwrite the files above.

## Governed CLC releases

Official product pages: CLC 2006, CLC 2012 and CLC 2018 under <https://land.copernicus.eu/en/products/corine-land-cover>. Licence: Copernicus full, open and free access with source attribution and adaptation disclosure. Vector status layers use EPSG:3035, 44 classes, a 25 ha minimum mapping unit and 100 m minimum mapping width. The preserved official release-lineage, coverage and nomenclature evidence is registered in `src/source_registry.py`.

| Predictor years | Governed release | Availability evidence | Local package status |
|---|---|---|---|
| T=2015 | CLC 2006 V17, released 2013-12-02 | Official lineage proves a full CLC/CLCC time series including Portuguese Azores, hence mainland Portugal, before end-2015. | Exact V17 vector package unavailable in the current official catalogue; blocked. |
| T=2016-2018 | CLC 2012 V18_5_1, released 2016-09-19 | Official lineage calls this the corrected final CLC2012 release; coverage is EEA39 including Portugal. | Exact V18_5_1 vector package unavailable in the current official catalogue; blocked. |
| T=2019 | CLC 2018 V20, released 2019-05-01 | V20 is the final corrected release. Pre-final V20b2 was already complete except Italy and Turkey, proving Portugal availability before and during 2019. | Exact V20 vector package unavailable in the current official catalogue; blocked. If it cannot be obtained, the canonical fallback is the governed CLC 2012 package. |
| T=2020-2024 | CLC 2018 V2020_20u1, released in 2020 | Current official CLC2018 metadata and file naming identify the 2020 update. | Ready: local raw ZIP is checksum/CRC-valid; SHA-256 `AC302982BE6EA027762CC1973123B452157B0C4AD536BB32167C486448316492`. |

The current official download catalogue exposes revised V2020_20u1 packages for the historical reference years. Those files are not substituted for V17/V18_5_1/V20 because doing so would silently use later revisions. The next action is to obtain exact archived official package URLs from the CLMS/EEA service desk or another official archive.

Canonical broad mapping: `built_up_share` uses codes 111-142 in the artificial-surface branch; `forest_shrub_share_2km` uses 311, 312, 313, 321, 322, 323 and 324. Exact code tuples are auditable in `src/source_registry.py`. Shares must be area-based and must not be described as parcel-level land cover.

Preserved evidence:

- [Official release lineage](https://land.copernicus.eu/en/technical-library/clc-release-lineage/@@download/file): `data/raw/clc/evidence/clc_release_lineage.pdf`, SHA-256 `CBFF53799AD7A73AEB3A83C67DBB5214C3D3D4FEBAD019E5B3B723D071A69941`.
- [Official V20u1 country coverage](https://land.copernicus.eu/en/technical-library/clc-country-coverage-1990-2018-v20u1/@@download/file): `data/raw/clc/evidence/clc_country_coverage_v20u1.pdf`, SHA-256 `5A265ADE38795CF486D839F31CCC8F423DDEC685F2D1B802B748A7A47CF68D7D`.
- [Official nomenclature guidelines](https://land.copernicus.eu/en/technical-library/clc-illustrated-nomenclature-guidelines/@@download/file): `data/raw/clc/evidence/clc_nomenclature_guidelines.pdf`, SHA-256 `8D69D31993481AA334E5391F717EB27558A5290AA039980D06FC5E937CC7F325`.

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

## Remaining concrete acquisition blockers

1. ERA5-Land: acquire corrected, separate 2022 and 2023 `total_precipitation` GRIBs with the official by-hour-of-day 00:00 workaround; preserve the affected originals.
2. CLC: obtain exact official archived vector packages for CLC 2006 V17, CLC 2012 V18_5_1, and CLC 2018 V20. If V20 cannot be obtained, use the governed V18_5_1 CLC 2012 fallback for T=2019.

Do not build the national panel until both blockers are resolved and checksums, URLs, licence/version evidence, CRS, coverage and schemas are registered.
