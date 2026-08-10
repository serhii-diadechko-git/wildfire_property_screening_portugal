# Commercialisation legal working notes

> Internal planning record for the project maintainer. This is an evolving
> research and decision log, not legal advice, a provider authorisation, or a
> public product policy. It is deliberately not linked from the README. Review
> it with qualified Portuguese legal counsel before any commercial launch.

## How to use this working file

This file separates four kinds of information so that later research does not
turn assumptions into facts:

- **Verified**: supported by a linked first-party, official, or authoritative
  source.
- **Inference**: a reasoned interpretation of verified evidence.
- **Unverified**: plausible, but not yet supported by adequate evidence.
- **Decision required**: a product, legal, scientific, or commercial choice
  that the maintainer must make before proceeding.

Research snapshot: **10 August 2026**. Recheck time-sensitive facts before
using them in a business plan.

## Decision snapshot

The underlying problem is real and economically relevant, but the current
capstone should not be converted directly into a paid property-risk score. The
strongest path is a controlled product-discovery pilot for **wildfire-aware
location and property due diligence**, not a claim that the model identifies a
safe property or predicts building loss.

Critical reasons:

1. The current output is annual next-year burned share for a 1 km cell. It is
   useful for comparing broad search areas, but it is not a property-level
   damage, safety, insurance-loss, or long-term ownership-risk estimate.
2. Portugal has a material wildfire problem and active institutional demand for
   better exposure and vulnerability information, but public operational tools
   already cover daily fire danger and short-horizon prediction.
3. Tutela IGNIS confirms that sophisticated 1 km ML wildfire mapping is already
   publicly available in Portugal. It does **not** validate this project's
   model, customer willingness to pay, or commercial viability.
4. Commercial use remains conditional on source-specific licence clearance,
   cautious claims, professional-liability review, and evidence that a defined
   customer will pay for a distinct decision workflow.
5. The recommended first commercial hypothesis is a report/API component for
   property due-diligence providers, buyer advisers, or property-intelligence
   platforms. Insurance underwriting is a later, substantially more demanding
   path.

## Part I - Existing legal and product boundary

### Current product boundary

The capstone produces a comparative estimate of next-year burned share for
mainland Portugal 1 km cells. It supports broad-area location research. It is
not a property-level forecast, safety guarantee, insurance quote, valuation,
or buy/do-not-buy recommendation.

The separate official ICNF structural wildfire-hazard layer is supporting
comparison context only. It is not an ML predictor or ML output.

### Provisional source-use position

| Source | Proposed commercial use | Working position | Required action before a paid product |
|---|---|---|---|
| ICNF annual burned areas | Historical-fire predictor and observed training/evaluation target; publish only derived ML output | Likely permissible as open data with ICNF provenance, but it has no universal standard licence identifier in the reviewed metadata | Ask ICNF for written confirmation that commercial derived ML outputs are permitted; retain layer URL, version, download date, and attribution. |
| ICNF structural hazard 2020-2030 | Do not include in commercial map, API, report, or derived class | Not commercially cleared: metadata prohibits commercialisation and says other uses may require express DGT authorisation | Remove it from commercial deliverables, or obtain written DGT authorisation that explicitly covers the intended derivative and distribution channel. |
| Copernicus CLC | Governed land-cover input; publish derived features/output only | Commercial reuse and adaptation are permitted under Copernicus terms | Keep Copernicus/CLMS attribution, identify Portugal clipping and other adaptations, and do not imply EU endorsement. |
| ERA5-Land | Climate predictor; publish derived features/output only | CC BY 4.0; commercial reuse/adaptation permitted | Attribute ECMWF/Copernicus, link CC BY 4.0, cite the dataset DOI, and identify adaptations. Do not share CDS credentials. |
| Copernicus DEM GLO-30 | Static terrain/slope input; publish derived features/output only | Commercial reuse/adaptation permitted under the published DEM licence | Preserve the required DEM/WorldDEM attribution and liability notice; retain tile/version/checksum provenance. |
| DGT CAOP | Boundary and grid context; publish derived output only | CC BY 4.0 according to DGT open-data information | Attribute DGT, identify CAOP version and adaptations, and retain source provenance. |

### Questions to resolve before commercialisation

#### Product and claims

- Who is the customer: individual location researcher, property business,
  insurer, lender, public authority, or another business?
- Is the service informational only, or will a customer use it to price,
  refuse, rank, insure, lend against, value, or recommend a property?
- Which phrases will be prohibited in the product and marketing? At minimum:
  `safe`, `guaranteed`, `risk-free`, `will burn`, and buy/do-not-buy claims.
- Which limitations, data cut-off date, model version, cell size, uncertainty,
  and annual-update status will appear beside every score or download?

#### Data rights and attribution

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

#### Privacy and consumer protection

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

#### Regulated use and liability

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

### Recommended low-risk route

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

### Evidence to retain

- Provider terms and layer metadata snapshots, URLs, and access dates.
- Written ICNF/DGT correspondence and authorisations.
- Source checksums, versions, licences, and attribution text used in each
  release.
- Model card, validation report, annual refit record, data cutoff, and change
  log for each published estimate.
- Product screenshots, user-facing limitations, terms of service, privacy
  notice, and customer agreements for each release.

### Review cadence

Update this document when a source licence changes, a new data source is added,
the intended customer/use case changes, a provider replies in writing, or a
commercial-launch decision is made. Promote only legally reviewed conclusions
into public documentation.

## Part II - Portugal opportunity and market evidence

### Why the problem is worth investigating

| Evidence | What is verified | Commercial interpretation |
|---|---|---|
| Rural-fire burden | SGIFR reports 8,252 rural fires in 2025. This was the third-lowest annual count since 2001, but structural prevention challenges remained. | Better prevention outcomes do not remove the need for location, asset, and resilience information. Event count alone is not a measure of addressable market. |
| Risk-information gap | OECD reports that Portugal's incomplete cadastral coverage and limited asset-value data obstruct comprehensive wildfire risk assessment. It also reports ICNF work toward a national map integrating hazard, exposure, economic value, and vulnerability. | There is a genuine data-integration problem, but public authorities are improving official capability. A private product needs a clearer workflow, faster updates, or better asset-level context. |
| Insurance relevance | ASF identifies growing materiality of physical climate risk to insurers and pension funds. Its reporting analyses wildfire exposure in fire and multi-risk portfolios. | Insurers have a real use case, but the capstone's target and 1 km resolution are not sufficient for underwriting, loss estimation, or pricing. |
| Property-market scale | INE reports 169,812 dwelling transactions in Portugal in 2025. | A large transaction flow creates opportunities for due diligence, but transaction volume is not evidence that buyers will pay for a wildfire product. |

### Potential users and current fit

| User group | Plausible need | Fit of the current project | Main gap before a useful product |
|---|---|---|---|
| Individual and foreign property buyers | Narrow broad search areas and identify questions for local investigation | Moderate: comparative national screening is understandable and accessible | Property-level vulnerability, longer horizon, local access/fuel context, and a tested willingness to pay |
| Buyer advisers, surveyors, lawyers, and due-diligence providers | Add consistent environmental context to client reports | High potential for a report/API component | Explainable address workflow, audit trail, professional review, and source clearance |
| Property portals and intelligence platforms | Add an environmental-search filter or risk context | Medium to high partnership potential | Stable API, service levels, address matching, product liability allocation, and user testing |
| Insurers and reinsurers | Portfolio accumulation, underwriting, pricing, mitigation, and catastrophe analysis | Low for the current target; strategically relevant later | Building/portfolio exposure, vulnerability, claims and loss data, calibration, governance, and regulatory controls |
| Banks and valuers | Long-term collateral resilience | Low to medium | Long-horizon risk, asset value and vulnerability, governance, and validation against financial outcomes |
| Municipalities and civil protection | Prevention, planning, preparedness, and operational response | The current annual layer offers limited strategic context | Daily conditions, ignition and spread, infrastructure and population exposure, and official integration |
| Forestry, utilities, and infrastructure operators | Operational prioritisation and asset protection | Low for the current annual product | Near-real-time weather/fuel state, asset networks, consequence modelling, and alert operations |

### Working product direction

The clearest differentiated product is not another generic national fire map.
It is a **wildfire-aware location due-diligence workflow** that combines:

1. historical fire recurrence;
2. annual comparative ML exposure;
3. structural landscape context where reuse is legally cleared;
4. property and neighbourhood vulnerability;
5. access, mitigation, planning, insurance, and local-verification prompts; and
6. explicit uncertainty, data dates, and limits.

Possible delivery ladder:

- **Free public screening**: broad-area comparison and education.
- **Paid professional report**: explainable evidence for a selected area or
  property, with local-verification checklist and no automated purchase advice.
- **B2B API or white-label component**: property intelligence, surveying, buyer
  advice, or portfolio screening.
- **Insurance/lending products later**: only after acquiring asset, loss,
  vulnerability, governance, and regulatory capability.

## Part III - Tutela IGNIS competitor and comparator audit

### Verified service design

Tutela IGNIS is a Neural Forge project for **daily rural-fire ignition-risk
prediction** across mainland Portugal. Its public pages state:

| Item | Tutela IGNIS disclosure |
|---|---|
| Analytical grid | 88,527 cells of 1 km covering mainland Portugal |
| Time horizon | Daily update; today and approximately 24-72 hours ahead |
| Output | Relative ignition-risk score and ordered levels; the map warns that these levels are not observed event frequencies |
| Active model | Seasonal ensemble `be23+lst1` |
| Algorithms | XGBoost and LightGBM gradient-boosted decision-tree models |
| Feature volume | About 63 variables per cell/day |
| Seasonal handling | Different spring/summer components, monthly probability calibration, and a final adjustment for rare-fire prevalence |
| Published skill | About 0.83 AUC on deliberately difficult comparisons; Tutela says a naive evaluation gives about 0.99 AUC but is misleading |
| Prospective validation | Daily predictions archived before outcomes since 19 May 2026 and compared with observed fires, IPMA and EFFIS |
| Published implementation stack | Neural Forge lists Python, XGBoost, LightGBM, FastAPI, PostGIS, Polars, Celery and Azure |

The national map labels relative levels as `Low <5%`, `Moderate 5-10%`,
`High 10-20%`, and `Extreme >=20%`, while expressly cautioning that they are
relative risk levels rather than observed frequencies. They should therefore
not be interpreted as literal daily burn probabilities without the service's
published calibration evidence.

### Data sources disclosed by Tutela

Tutela groups its inputs into ten public-data families:

- ICNF historical fires and burned areas;
- the 1984-2022 dNBR severity atlas;
- NASA FIRMS satellite fire detections;
- Copernicus ERA5 and CERRA meteorological reanalysis;
- IPMA meteorology;
- MODIS land-surface temperature;
- Fire Weather Index and drought indicators;
- CORINE land cover and canopy height;
- elevation, slope, aspect and microtopography; and
- population, wildland-urban interface and infrastructure pressure.

The model page also reports controlled negative experiments: satellite
vegetation indices, live-fuel moisture, human ignition pressure, and
high-resolution microtopography did not materially improve the available model.
That is evidence about Tutela's particular target, data and evaluation—not proof
that these variables cannot help a different model.

### Is it the same model as this project?

**No.** The two projects share broad source families, gradient-boosted trees,
a 1 km mainland grid, and a commitment to comparative rather than certain
predictions. The scientific tasks are materially different:

| Dimension | This capstone | Tutela IGNIS |
|---|---|---|
| User question | Compare broad locations using estimated annual burned share | Support daily territorial awareness of where ignition risk is relatively higher |
| Target | Continuous proportion of cell land area burned in the following year | Short-horizon ignition-risk ranking/level |
| Time step and horizon | Annual `T -> T+1` | Daily, today to about 24-72 hours |
| Model | Nine-feature two-stage histogram-gradient-boosting classifier/regressor | Seasonal XGBoost + LightGBM ensemble |
| Inputs | Nine governed fire-history, land-cover, terrain and JJAS climate predictors | About 63 daily/static variables across ten source families |
| Development evidence | Train 2010-2019; validate 2020-2021; held-out test 2022-2024 | Reported difficult-case AUC plus prospective daily archive from 19 May 2026 |
| Operational output | Target-free annual 2026 comparative burned-share estimate | Daily national risk map and dashboard |
| Intended role | Location-research screening | Complement IPMA/EFFIS for territorial/operational awareness |

Consequently, visual similarity between Tutela, the ICNF structural-hazard map,
and this project's annual output does not validate any model. Validation must
use predeclared metrics against future observed outcomes at the target's own
time scale.

The cell counts also differ (89,112 in this capstone versus 88,527 disclosed by
Tutela). Equal nominal resolution therefore does not establish an identical
grid origin, mainland mask, coastal-cell rule, or analytical population. Direct
cell-level comparison would require explicit grid-contract reconciliation.

### Access, payment, and commercial status

Verified findings:

- The national map, dashboard, model explanation, and validation description
  were publicly viewable without payment during this review.
- Tutela's About page says it was built as a contribution to society and “did
  not start as a commercial product”; it says essential information is kept
  accessible to everyone.
- Account registration is reserved for approved organisations, official bodies,
  and partners.
- The fire-spread simulator is restricted to authorised official entities for
  stated ethical reasons; access is requested through an institutional email.
- No public price list, subscription plan, checkout, or paid-access terms were
  found on the reviewed pages.

Working conclusion: **the public IGNIS service is positioned as a public-access,
non-commercial initiative, with restricted institutional functions. There is
no verified evidence of a paid consumer product.** This does not prove that
Neural Forge has no funded pilots, consulting work, partnerships, grants, or
future commercial plan; those points remain unverified.

### Transparency and implementation strengths

- The service states what the risk score is and is not.
- It reports both a tempting naive AUC and a lower difficult-case AUC, explaining
  why the latter is more credible.
- It archives predictions before outcomes are known and publishes the benchmark
  record in a public GitHub repository.
- The archive documents comparison streams for Tutela, IPMA, EFFIS and observed
  fires. Code is MIT-licensed and archive data is presented under CC BY 4.0,
  subject to upstream-source terms.
- The public repository records five permanently absent prediction days and
  makes the benchmark tolerate them explicitly.

These are useful governance patterns for any future version of this project:
prospective timestamping, public model/version labels, missing-day disclosure,
official-baseline comparison, and clear separation between ranking skill and
calibration.

### Independent reviews and public reception

The search conducted for this note found **no meaningful independent customer
review corpus, press evaluation, academic peer review, procurement record, or
published third-party performance audit** specific to Tutela IGNIS. Indexed
results were dominated by Tutela, Neural Forge, its developer portfolio, and
the project's own public archive. At inspection time the public GitHub archive
showed zero stars and one fork; those counts are weak adoption signals and not
quality evidence.

Therefore:

- Tutela's validation pages are first-party evidence, albeit unusually
  transparent first-party evidence.
- Its reported AUC and comparisons should not be treated as independently
  replicated.
- Absence of reviews may simply reflect a recent, specialised service rather
  than poor quality.
- Commercial demand and operational adoption remain unverified and require
  direct stakeholder interviews or documented deployments.

### Competitive implication for this project

Tutela occupies the short-horizon, daily, operational fire-risk space more
strongly than this capstone. Competing head-on with another public national
1 km risk map would offer weak differentiation. A more defensible path is to:

1. retain the annual model as one evidence layer rather than the full product;
2. focus on property/location due diligence and longer-lived exposure and
   vulnerability questions;
3. combine outputs with local-verification actions rather than emergency
   alerts;
4. test whether professional intermediaries value a documented report or API;
   and
5. consider complementing or partnering with operational services instead of
   recreating them.

## Part IV - Data and research extension roadmap

### Highest-priority scientific extensions

| Candidate | Why it may help | Principal caution |
|---|---|---|
| Sentinel-2 vegetation and burn-severity measures such as NDVI, NDMI, NBR and dNBR | More current vegetation condition and severity history at 10-20 m | Cloud handling, temporal compositing, leakage-safe dates, and computation |
| EFFIS fuel information and more detailed vegetation structure | Connects land cover to combustible fuel context | Fuel products and reference dates must match the intended horizon |
| Daily/hourly IPMA, ERA5/CERRA and FWI/drought variables | Better captures heat, wind, dryness and short extreme conditions | Would change the annual product definition; avoid copying a daily operational competitor without a user need |
| ICNF ignition points and causes | Separates ignition propensity from area burned and supports human/natural mechanisms | Attribute consistency, privacy/location sensitivity, and target redesign |
| DEM-derived elevation, aspect, ruggedness and access terrain | Adds physically meaningful fire-behaviour and accessibility context | Correlation and scale; slope alone is not property vulnerability |
| Roads, settlements, population and wildland-urban interface | Adds human ignition and exposure context | Distinguish ignition, exposure and vulnerability; avoid sensitive profiling |

### Property and loss extensions needed for commercial due diligence

- building footprint, construction, roof/material and defensible-space data;
- vegetation and fuel within multiple property-centred buffers;
- road access, evacuation constraints, fire-station and water-resource context;
- planning restrictions, fuel-management obligations, and verified cadastral or
  parcel linkage where legally available;
- historical damage, claims, insured values, and mitigation outcomes for an
  insurance-grade product; and
- 10-, 20-, and 30-year climate scenario indicators for ownership-horizon
  decisions.

Adding variables is not automatically improvement. Each feature requires a
mechanism, source-year rule, licence check, missingness policy, validation-only
comparison, and a decision about whether it answers annual exposure, daily
danger, property vulnerability, or financial loss.

## Part V - Commercial discovery and decision gates

### Recommended next research cycle

1. Choose one primary customer and decision. Recommended starting hypothesis:
   a wildfire due-diligence evidence component for professional buyer advisers
   or property-intelligence platforms.
2. Conduct structured interviews with at least buyers, buyer advisers,
   surveyors/valuers, property platforms, insurers, municipalities, and fire
   specialists. Ask about an actual recent decision, not general interest.
3. Test a prototype report using existing evidence plus a local-verification
   checklist. Do not sell or imply a property safety grade.
4. Measure whether the output changes search effort, questions asked, or due
   diligence—and whether anyone will pay, integrate, or pilot it.
5. Obtain source-provider and Portuguese legal review before paid distribution.
6. Proceed only if the customer, decision, differentiation, data rights,
   validation target, liability allocation, and willingness to pay are all
   explicit.

### Stop/go criteria

| Gate | Proceed when | Stop or redesign when |
|---|---|---|
| Customer | A defined user has a repeated decision and agrees to a pilot | Interest remains generic or users rely adequately on free official tools |
| Scientific target | The target matches the customer decision and has a defensible validation design | Annual burned share is being presented as property damage, safety, or long-term loss |
| Differentiation | The workflow adds vulnerability, due diligence, explainability, or integration beyond public maps | The product is only another coloured 1 km wildfire map |
| Data rights | Commercial derivative and distribution rights are documented for every source/output | Provider terms or attribution cannot support the intended channel |
| Performance | Prospective and held-out evidence supports the stated use with stable limitations | Value depends on visual resemblance or selectively reported metrics |
| Liability and governance | Claims, human review, disclaimers, audit, privacy, and contracts match the risk | The customer expects automated underwriting, valuation, or purchase advice from the current system |
| Economics | A partner funds a pilot or demonstrates credible willingness to pay | No user will pay beyond what existing public services provide |

### Unresolved questions to carry forward

- What single buyer or professional decision should the product improve?
- Is the intended time horizon next year, the next fire season, or the next
  10-30 years of ownership?
- Should daily operational risk be integrated from an existing service instead
  of built internally?
- Which property/vulnerability data can be licensed, maintained, and validated
  nationally?
- What written permissions are required for ICNF annual burned-area derivatives
  and any use of structural-hazard information?
- Can prospective annual predictions be timestamped publicly before outcomes,
  following the strong governance pattern used by Tutela?
- What constitutes a commercially meaningful improvement over free SGIFR,
  IPMA, EFFIS, ICNF, and Tutela information?
- Are institutional pilots, funding arrangements, or performance audits for
  Tutela available but not publicly indexed?

## Evidence register and official references to revisit

### Existing legal and source references

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

### Portugal market and institutional evidence

- [SGIFR 2025 activity report](https://www.sgifr.gov.pt/pt/web/sgifr/w/relat%C3%B3rio-de-atividades-2025)
- [SGIFR 2025 rural-fire analysis](https://www.sgifr.gov.pt/w/an%C3%A1lise-dos-inc%C3%AAndios-rurais-de-2025)
- [OECD: evidence and data gaps in integrated rural-fire management](https://www.oecd.org/en/publications/2026/04/towards-an-integrated-rural-fire-management-framework-in-portugal_5e2bd5d9/full-report/component-8.html)
- [ASF 2025 climate-risk exposure report](https://www.asf.com.pt/w/at_raerc)
- [OECD Portugal 2026: climate adaptation and insurance](https://www.oecd.org/en/publications/oecd-economic-surveys-portugal-2026_025b3445-en/full-report/promoting-decarbonisation-and-adapting-to-a-warming-climate_b881e2e3.html)
- [INE 2025 construction, housing and transaction summary](https://webinq.ine.pt/?menuBOUI=703377)

### Tutela IGNIS evidence

- [Tutela IGNIS overview and disclosed sources](https://tutela.land/)
- [National daily risk map](https://tutela.land/ignis/mapa-nacional)
- [Model specification and limitations](https://tutela.land/ignis/modelos)
- [Prospective validation page](https://tutela.land/ignis/validacao)
- [Current dashboard](https://tutela.land/ignis/dashboard)
- [Tutela About page and non-commercial positioning](https://tutela.land/sobre)
- [Restricted institutional fire-spread simulator](https://tutela.land/ignis/simulation)
- [Public prospective benchmark archive](https://github.com/neuralforge-pt/tutela-ignis)
- [Neural Forge implementation summary](https://neuralforge.pt/)
