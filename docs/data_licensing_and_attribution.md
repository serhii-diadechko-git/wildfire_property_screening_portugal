# Data licensing and attribution guide

This document complements `data/source_manifest.json` and
`src/source_registry.py`. It records the practical access, attribution, and
redistribution rules for the external datasets used by this project. It is not
legal advice and does not replace the provider's current terms or layer-level
metadata.

## Source rules

| Source | Access category | Licence or terms evidenced by the official provider | Required attribution / caution |
|---|---|---|---|
| [ICNF burned areas and structural-hazard catalogue](https://geocatalogo.icnf.pt/) | Free/open by default; layer-specific exceptions may apply | ICNF states that its geographic information is generally available as open data while ICNF retains intellectual property. No universal SPDX or Creative Commons identifier is stated for every layer. | Cite `ICNF, [layer name], [download URL], [download date]`. Check the individual layer metadata before redistributing a raw file or adapted layer. |
| [DGT CAOP](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop) | Open public access; redistribution status must be verified | DGT/SNIG publishes CAOP as official administrative-boundary and high-value public data, but the CAOP page does not establish a project-specific permissive redistribution licence. | Cite DGT, CAOP version, official URL, and access date. Obtain the current file from DGT/SNIG unless redistribution permission is confirmed. |
| [Copernicus CLC](https://land.copernicus.eu/en/products/corine-land-cover) | Free, full and open | [Copernicus Land Monitoring data policy](https://land.copernicus.eu/en/data-policy): source attribution, adaptation disclosure, and no implication of EU endorsement. The CLC product documentation allows commercial use. | Use the Copernicus/EEA attribution, identify the reference year and package version, and disclose the Portugal clipping and any derived class shares. |
| [Copernicus DEM GLO-30](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM) | Free licence for GLO-30/GLO-90 | Copernicus/ESA user-licence conditions apply. The official page specifies attribution requirements and recommends DOI [10.5270/ESA-c5d3d65](https://doi.org/10.5270/ESA-c5d3d65). | Preserve tile identifiers and checksums. Retain the prescribed Copernicus DEM/WorldDEM notice for communicated or adapted products. Verify current access-category conditions before sharing tiles. |
| [ERA5-Land monthly means](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-monthly-means) | Free with CDS account and terms acceptance | The CDS dataset page identifies a CC-BY licence and DOI [10.24381/cds.68d2bb30](https://doi.org/10.24381/cds.68d2bb30). API access is subject to CDS terms. | Each user retrieves data using their own CDS account and local credentials. Never commit, print, publish, or share `.cdsapirc` contents or tokens. |

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
- The project owner must choose a separate licence for this repository's own
  code, notebooks, documentation, and original figures. Until then, no broad
  reuse licence should be assumed for those project-owned materials.

## Maintainer checklist before release

1. Review the linked official terms and the layer metadata for every new source
   or version.
2. Confirm that raw files, credentials, private URLs, and local paths are not
   staged.
3. Preserve provider attribution in reports, maps, QGIS projects, and any
   distributed derivative.
4. Record the exact source version, access date, checksum, and adaptation in
   the source registry.
5. Choose and add a licence for the repository's own code and documentation.

