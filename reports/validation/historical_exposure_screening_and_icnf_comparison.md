# Historical exposure screening and official ICNF comparison

**This output is historical and descriptive, not a prediction, probability, safety guarantee, property recommendation, or validation of the official ICNF map.**

## Evidence snapshot and recurrence bands

The assessment snapshot uses the latest validated observed burned-area year, 2025. The primary measure counts the distinct years from 2016 through 2025 in which each mainland-masked 2 km context intersected an annual dissolved ICNF burned-area geometry. The repository has validated ICNF annual inputs from 2005 through 2025; only the latest complete ten-year window is used here.

National empirical recurrence tertiles are 1 and 3 years, producing transparent recurrence-only bands:

- lower: 0-1 years;
- moderate: 2-3 years;
- higher: 4-10 years.

| Historical exposure band | Cells | Share |
|---|---:|---:|
| lower | 36,645 | 41.12% |
| moderate | 29,919 | 33.57% |
| higher | 22,548 | 25.30% |

“Lower historical exposure” does not mean safe. Zero or one recorded fire year does not mean zero wildfire risk. These bands support broad location comparison and shortlisting only.

## Official ICNF hazard comparison

Source: **SRUP - Carta de Perigosidade de Incendio Rural**, Structural wildfire hazard map 2020-2030; metadata creation 2022-03-28. The official 25 m EPSG:3763 raster was obtained from the registered ICNF WCS coverage and kept immutable at `data/raw/hazard/icnf_structural_2020_2030/icnf_structural_hazard_2020_2030_25m_epsg3763.tif`.

Each 1 km cell receives the predominant valid official 25 m class by pixel-centre area inside its mainland-land geometry. Exact modal ties select the higher official class and are counted. Cells with no valid official pixel remain `unmatched`; they are never assigned a low class.

| Official ICNF class | Cells | Share |
|---|---:|---:|
| null | 0 | 0.00% |
| very_low | 27,163 | 30.48% |
| low | 17,340 | 19.46% |
| medium | 15,303 | 17.17% |
| high | 14,735 | 16.54% |
| very_high | 14,112 | 15.84% |
| unmatched | 459 | 0.52% |

### Cross-tabulation (cell counts)

| Historical band | null | very_low | low | medium | high | very_high | unmatched |
|---|---:|---:|---:|---:|---:|---:|---:|
| lower | 0 | 14,014 | 8,611 | 5,969 | 5,268 | 2,375 | 408 |
| moderate | 0 | 9,344 | 5,431 | 4,961 | 5,203 | 4,943 | 37 |
| higher | 0 | 3,805 | 3,298 | 4,373 | 4,264 | 6,794 | 14 |

For a descriptive orientation only, official null/very-low/low classes were grouped as lower, medium as moderate, and high/very-high as higher. The broad levels coincide for 38,644 matched cells (43.59%). This is not an accuracy statistic: the recurrence band measures observed fire history around a cell, while the official map represents structural hazard under its own statutory methodology. Agreement and disagreement are both expected and neither source replaces the other.

## Output and validation

- GeoPackage: `data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg`
- Layer: `historical_exposure_screening`
- CRS: EPSG:3763
- Features: 89,112
- Unmatched official hazard cells: 459
- Exact official-class modal ties: 59
- Invalid/empty geometries: 0 / 0
- Forbidden predictive/outcome fields: none
- Deterministic analytical rerun: all 275 bounded batches reproduced exact attributes and ordering

Machine-readable summaries are stored at `reports/validation/historical_exposure_screening_and_icnf_comparison.json`, `reports/tables/historical_exposure_band_summary.csv`, `reports/tables/icnf_hazard_class_summary.csv`, and `reports/tables/historical_exposure_band_by_icnf_hazard_class.csv`.

## Limitations

- Historical recurrence records observed burned-area intersections, not future probability, ignition likelihood, property damage, evacuation access, or building-level vulnerability.
- A 2 km context is a project screening parameter; the analytical geometry remains the 1 km cell.
- CLC 2018 and static terrain fields provide generalized landscape context and do not describe individual properties.
- The official 25 m hazard raster is summarized to 1 km by predominant valid class, which necessarily removes within-cell detail.
- This layer must not be used as a buy/do-not-buy decision or property-level safety guarantee.
