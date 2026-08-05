# ERA5-Land coastal fallback analysis

This is a spatial land-mask/grid-alignment diagnosis. It does not change raw GRIBs or interpolate/downscale climate data.

Affected canonical cells: 1,506. ERA5 source grid: 55 x 37; valid land cells: 1,553. The land mask is invariant across T=2015-2024.

## Nearest valid land-cell distance

Minimum 4.243 km; median 7.147 km; mean 7.522 km; P90 10.190 km; P95 11.331 km; P99 12.889 km; maximum 13.962 km.

| Distance band | Cells |
|---|---:|
| under 10 km | 1,339 |
| 10 to under 20 km | 167 |
| 20 to under 30 km | 0 |
| 30 to under 50 km | 0 |
| 50 km or more | 0 |

Selected fallback sources on the CDS request boundary: 0. Additional acquisition required: False.

## Largest-distance cases

| Cell | Land class | Cell lat | Cell lon | Source lat | Source lon | Distance km |
|---|---|---:|---:|---:|---:|---:|
| `PT3763_005800` | partial_land_coastal | 38.44553 | -8.84904 | 38.40 | -8.70 | 13.962 |
| `PT3763_005801` | full_land_coastal | 38.45454 | -8.84913 | 38.50 | -8.70 | 13.958 |
| `PT3763_030817` | partial_land_coastal | 37.07817 | -8.27368 | 37.20 | -8.30 | 13.722 |
| `PT3763_005802` | full_land_coastal | 38.46355 | -8.84922 | 38.50 | -8.70 | 13.635 |
| `PT3763_030258` | partial_land_coastal | 37.07815 | -8.28493 | 37.20 | -8.30 | 13.589 |
| `PT3763_029142` | partial_land_coastal | 37.07812 | -8.30742 | 37.20 | -8.30 | 13.542 |
| `PT3763_029700` | partial_land_coastal | 37.07814 | -8.29618 | 37.20 | -8.30 | 13.528 |
| `PT3763_005803` | full_land_coastal | 38.47256 | -8.84931 | 38.50 | -8.70 | 13.379 |
| `PT3763_031937` | partial_land_coastal | 37.08720 | -8.25121 | 37.20 | -8.30 | 13.248 |
| `PT3763_005804` | full_land_coastal | 38.48156 | -8.84940 | 38.50 | -8.70 | 13.194 |

Local climate comparisons are recorded in the machine-readable JSON.
