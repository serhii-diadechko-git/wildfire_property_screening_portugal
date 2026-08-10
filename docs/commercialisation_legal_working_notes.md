# Commercialisation legal working notes

> Internal planning record for the project maintainer. This is an evolving
> research and decision log, not legal advice, a provider authorisation, or a
> public product policy. It is deliberately not linked from the README. Review
> it with qualified Portuguese legal counsel before any commercial launch.

## Current product boundary

The capstone produces a comparative estimate of next-year burned share for
mainland Portugal 1 km cells. It supports broad-area location research. It is
not a property-level forecast, safety guarantee, insurance quote, valuation,
or buy/do-not-buy recommendation.

The separate official ICNF structural wildfire-hazard layer is supporting
comparison context only. It is not an ML predictor or ML output.

## Provisional source-use position

| Source | Proposed commercial use | Working position | Required action before a paid product |
|---|---|---|---|
| ICNF annual burned areas | Historical-fire predictor and observed training/evaluation target; publish only derived ML output | Likely permissible as open data with ICNF provenance, but it has no universal standard licence identifier in the reviewed metadata | Ask ICNF for written confirmation that commercial derived ML outputs are permitted; retain layer URL, version, download date, and attribution. |
| ICNF structural hazard 2020-2030 | Do not include in commercial map, API, report, or derived class | Not commercially cleared: metadata prohibits commercialisation and says other uses may require express DGT authorisation | Remove it from commercial deliverables, or obtain written DGT authorisation that explicitly covers the intended derivative and distribution channel. |
| Copernicus CLC | Governed land-cover input; publish derived features/output only | Commercial reuse and adaptation are permitted under Copernicus terms | Keep Copernicus/CLMS attribution, identify Portugal clipping and other adaptations, and do not imply EU endorsement. |
| ERA5-Land | Climate predictor; publish derived features/output only | CC BY 4.0; commercial reuse/adaptation permitted | Attribute ECMWF/Copernicus, link CC BY 4.0, cite the dataset DOI, and identify adaptations. Do not share CDS credentials. |
| Copernicus DEM GLO-30 | Static terrain/slope input; publish derived features/output only | Commercial reuse/adaptation permitted under the published DEM licence | Preserve the required DEM/WorldDEM attribution and liability notice; retain tile/version/checksum provenance. |
| DGT CAOP | Boundary and grid context; publish derived output only | CC BY 4.0 according to DGT open-data information | Attribute DGT, identify CAOP version and adaptations, and retain source provenance. |

## Questions to resolve before commercialisation

### Product and claims

- Who is the customer: individual location researcher, property business,
  insurer, lender, public authority, or another business?
- Is the service informational only, or will a customer use it to price,
  refuse, rank, insure, lend against, value, or recommend a property?
- Which phrases will be prohibited in the product and marketing? At minimum:
  `safe`, `guaranteed`, `risk-free`, `will burn`, and buy/do-not-buy claims.
- Which limitations, data cut-off date, model version, cell size, uncertainty,
  and annual-update status will appear beside every score or download?

### Data rights and attribution

- Has ICNF confirmed commercial derivative use of annual burned-area data in
  writing?
- Has DGT authorised any use of ICNF structural-hazard values or derivatives?
- Are raw datasets, source attributes, rasters, clipped layers, or only project
  derivatives being distributed?
- Does every app, API, map, report, export, and customer contract preserve the
  required provider attributions, adaptation notices, and no-endorsement rule?
- Are new data sources—property listings, cadastral records, address geocoding,
  imagery, basemaps, insurance data, or customer portfolios—covered by their
  own commercial-use terms?

### Privacy and consumer protection

- Will the service collect accounts, email addresses, payments, device IDs,
  cookies, searched addresses, saved locations, property portfolios, or owner
  information?
- Who is the GDPR controller, and which hosting, analytics, payment, geocoding,
  or support suppliers are processors?
- Is a data-protection impact assessment required because of systematic
  profiling or decisions that significantly affect individuals?
- Does the product need a privacy notice, cookie controls, retention schedule,
  deletion process, data-subject request process, and processor agreements?
- If sold to consumers, are terms, price, cancellation, support, and digital
  service information compliant in each sales country?

### Regulated use and liability

- Could any use qualify as insurance distribution, underwriting, pricing,
  claims handling, creditworthiness assessment, or property valuation?
- If an insurer uses the service, what governance, human oversight,
  explainability, fairness, data-quality, audit, and ICT-supplier controls are
  contractually required?
- Does the documented intended purpose create an EU AI Act high-risk use case?
- What Portuguese and EU laws apply to the final business model and sales
  territory?
- What professional-indemnity, cyber, product-liability, and contractual
  protections are appropriate?

## Recommended low-risk route

1. Launch only a comparative, broad-area screening product based on the ML
   estimate and permitted derived inputs.
2. Exclude the ICNF structural-hazard layer and all derived hazard classes until
   written DGT authorisation is in place.
3. Keep public claims conservative: not property-level, not a safety guarantee,
   not insurance or investment advice, and not a purchase recommendation.
4. Publish a source-attribution and methodology page with model/data version,
   annual data cut-off, update cycle, and limitations.
5. Design the first release to minimise personal data: anonymous exploration,
   no address retention by default, and no personal portfolio upload.
6. Obtain a Portuguese legal review before charging customers or entering into
   property, insurance, lending, or public-sector contracts.

## Evidence to retain

- Provider terms and layer metadata snapshots, URLs, and access dates.
- Written ICNF/DGT correspondence and authorisations.
- Source checksums, versions, licences, and attribution text used in each
  release.
- Model card, validation report, annual refit record, data cutoff, and change
  log for each published estimate.
- Product screenshots, user-facing limitations, terms of service, privacy
  notice, and customer agreements for each release.

## Review cadence

Update this document when a source licence changes, a new data source is added,
the intended customer/use case changes, a provider replies in writing, or a
commercial-launch decision is made. Promote only legally reviewed conclusions
into public documentation.

## Official references to revisit

- [ICNF open-data catalogue](https://geocatalogo.icnf.pt/)
- [ICNF annual burned-area metadata](https://geocatalogo.icnf.pt/metadados/area_ardida.html)
- [ICNF structural-hazard metadata](https://geocatalogo.icnf.pt/metadados/perigosidade_estrutural_20_30.html)
- [DGT open data / CAOP](https://www.dgterritorio.gov.pt/dados-abertos)
- [Copernicus Land Monitoring data-use terms](https://land.copernicus.eu/en/faq/data-use-terms-and-conditions)
- [ERA5-Land monthly means](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-monthly-means)
- [ERA5-Land CC BY 4.0 licence](https://cds.climate.copernicus.eu/licences/creative-commons-attribute-4-international-licence)
- [Copernicus DEM GLO-30 licence](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf)
- [European Commission AI Act guidance](https://digital-strategy.ec.europa.eu/en/faqs/navigating-ai-act)
- [Portuguese CNPD DPIA guidance](https://www.cnpd.pt/organizacoes/outras-obrigacoes/avaliacao-de-impacto/)
- [EIOPA AI governance opinion](https://www.eiopa.europa.eu/publications/opinion-artificial-intelligence-governance-and-risk-management_en)
