# Data licensing and attribution guide

This document complements `data/source_manifest.json` and
`src/source_registry.py`. It records the practical access, attribution, and
redistribution rules for the external datasets used by this project. It is not
legal advice and does not replace the provider's current terms or layer-level
metadata.

## Capstone and product boundary

This repository is an educational capstone and research implementation. It is
not sold or offered by its author as an insurance, valuation, property-decision,
or property-safety service. Its comparative outputs may help narrow broad
location-search areas, but they are not a safety guarantee or a buy/do-not-buy
recommendation.

The repository's [MIT License](../LICENSE) applies to original project code,
notebooks, documentation, and authored figures only. It does not license any
external dataset, raw download, or derivative that remains subject to provider
terms. A third party that wants to commercialise the code or a derived product
must independently verify every source's current terms, obtain any required
permissions, preserve attribution, and meet applicable privacy, consumer,
insurance, and AI obligations.

## Source rules

| Source | Access category | Licence or terms evidenced by the official provider | Required attribution / caution |
|---|---|---|---|
| [ICNF annual burned areas](https://geocatalogo.icnf.pt/metadados/area_ardida.html) | Open data; no fee stated | ICNF states that its geographic information is generally open unless a layer states otherwise; the annual burned-area metadata states no use restriction, while requiring explicit ICNF provenance/authorship. No universal SPDX or Creative Commons identifier is stated. | Cite `ICNF, [layer name], [download URL], [download date]`. Before a paid or high-stakes product, obtain written confirmation of commercial derivative use and check the current layer metadata. |
| [ICNF structural wildfire hazard 2020-2030](https://geocatalogo.icnf.pt/metadados/perigosidade_estrutural_20_30.html) | Consultation/visualisation subject to metadata | The official metadata prohibits commercialisation and says that other uses may require express DGT authorisation and conditions. | It is an external comparison layer, not an ML input or output. Do not redistribute the raster, derived hazard classes, or a commercial product containing them without written DGT authorisation. Cite the official source for permitted published use. |
| [DGT CAOP](https://www.dgterritorio.gov.pt/dados-abertos) | Open data | DGT identifies downloadable geographic data, including CAOP, as subject to [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). | Attribute DGT, CAOP version, official URL, and access date; identify adaptations. |
| [Copernicus CLC](https://land.copernicus.eu/en/products/corine-land-cover) | Free, full and open | [Copernicus Land Monitoring data policy](https://land.copernicus.eu/en/data-policy): source attribution, adaptation disclosure, and no implication of EU endorsement. The CLC product documentation allows commercial use. | Use the Copernicus/EEA attribution, identify the reference year and package version, and disclose the Portugal clipping and any derived class shares. |
| [Copernicus DEM GLO-30](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM) | Free licence for GLO-30/GLO-90 | Copernicus/ESA user-licence conditions apply. The official page specifies attribution requirements and recommends DOI [10.5270/ESA-c5d3d65](https://doi.org/10.5270/ESA-c5d3d65). | Preserve tile identifiers and checksums. Retain the prescribed Copernicus DEM/WorldDEM notice for communicated or adapted products. Verify current access-category conditions before sharing tiles. |
| [ERA5-Land monthly means](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-monthly-means) | Free with CDS account and terms acceptance | The dataset is released under [CC BY 4.0](https://cds.climate.copernicus.eu/licences/creative-commons-attribute-4-international-licence); cite DOI [10.24381/cds.68d2bb30](https://doi.org/10.24381/cds.68d2bb30). API access is subject to CDS terms. | Attribute the source, link the licence, and identify adaptations. Each developer retrieves account-gated data using their own credentials. Never commit, print, publish, or share `.cdsapirc` contents or tokens. |
| [OpenStreetMap browser basemap](https://www.openstreetmap.org/copyright) | Open map data; public tiles are capacity-limited | OpenStreetMap data are under the [Open Database License](https://opendatacommons.org/licenses/odbl/). The local viewer uses the standard public tile service only for interactive background viewing and must follow its [tile usage policy](https://operations.osmfoundation.org/policies/tiles/). | Show visible `© OpenStreetMap contributors` attribution. Do not bulk-download, prefetch, or package public OSM tiles. A public or commercial deployment needs a suitable hosted/self-hosted basemap arrangement and an independent terms review. |

## Repository and redistribution policy

- Raw provider downloads remain outside Git and are kept immutable.
- `data/source_manifest.json` and `src/source_registry.py` record official
  URLs, local paths, versions, checksums, dates, and validation facts; they do
  not grant redistribution rights.
- Portugal-clipped CLC layers, slope derivatives, model tables, maps, and other
  outputs are project derivatives. They must retain the relevant provider
  attribution and identify adaptations where required.
- A personal Google Drive or other private storage location is not an implied
  public data mirror.
- Account-gated or otherwise restricted sources must be obtained directly by
  each user under the provider's current terms.
- These are data terms, not software licences. GPL is not applicable to the
  external datasets unless a provider explicitly states it.
- The repository's own code, notebooks, documentation, and original figures
  are released under the [MIT License](../LICENSE). This grants broad reuse,
  modification, and redistribution rights while preserving the copyright and
  licence notice. It does not grant rights to redistribute or relicense the
  external provider datasets, which remain subject to their own terms.
- A commercial deployment must separately assess its intended use, customer
  claims, privacy processing, consumer terms, professional liability, and any
  insurance or financial-sector obligations. No repository disclaimer removes
  statutory obligations or makes restricted provider data commercially usable.
