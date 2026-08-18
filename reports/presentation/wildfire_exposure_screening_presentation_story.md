# Wildfire Exposure Screening — Presentation Story

## Map introduction

The project produces a national map for comparing broad location-search areas across mainland Portugal.

Mainland Portugal is divided into 89,112 cells, each approximately 1 km × 1 km. The model uses 2025 fire-history, landscape, terrain and climate information to estimate the proportion of each cell that may burn in 2026.

The map simplifies these estimates into national percentile groups. Lower represents the bottom 50% of estimated values, intermediate represents the next 30%, and higher represents the top 20%. These groups show the relative position of each cell compared with all other mainland cells. They are not fire probabilities and do not state what percentage of a cell will burn.

The map helps reduce a national location search to broad areas that deserve further investigation. It does not identify a guaranteed safe property.

## Slide 1 — Project purpose

This project examines whether public wildfire, landscape, terrain and climate data can help compare broad locations across mainland Portugal. It combines data science, machine learning and GIS in one reproducible workflow.

The purpose is not to tell someone to buy or reject a property. It is to narrow a large national search into a smaller set of areas for detailed local research.

## Slide 2 — Dataset overview

Every analytical record has the same geographical meaning: one mainland Portugal 1 km cell in one predictor year.

ICNF annual burned-area data provides historical fire evidence and the observed burned share in the following year. Burned share is the burned land area divided by the cell's land area. Copernicus CLC and DEM data describe land cover and terrain. ERA5-Land provides warm-season temperature, precipitation and shallow soil-water conditions.

Some features are calculated within a 2 km outward context around each cell. This context captures surrounding forest and shrub cover, terrain and previous fire recurrence. It is not a second analytical grid; the 1 km cell remains the only model unit.

## Slide 3 — Model development

The candidate models learned from historical data for 2010–2019. We compared them using the later 2020–2021 period and selected the best-performing approach.

The selected model was then tested once on 2022–2024 data. These later years were kept separate from model training and selection, providing a more realistic check of how the model performs on new data.

After evaluation, the selected model was refitted using predictor years 2010–2024 and their known following-year outcomes from 2011–2025. The refitted model was then given the available 2025 predictors to estimate burned share in 2026. The 2026 outcome is not yet available, so this estimate cannot yet be evaluated.

## Slide 4 — Three spatial views

The project presents three different views of the same 1 km mainland cells.

The historical-recurrence map counts the number of distinct years with burned-area evidence between 2016 and 2025 within the 2 km context around each cell. It is a fixed descriptive view of recent observed history.

The official ICNF structural-hazard map describes persistent landscape conditions associated with wildfire hazard. It is an external official reference and is not the project's prediction.

The third map shows the project's comparative estimate for 2026, created from 2025 predictor inputs. These three maps answer different questions. They can be compared, but they should not be added together into one score.

## Slide 5 — Complementary evidence

Historical recurrence shows where fire was repeatedly observed during 2016–2025. The official ICNF structural-hazard layer describes underlying landscape conditions. Its original 25 m classes are summarized as the predominant valid class for each 1 km cell.

Where the two layers agree, they provide consistent broad-area context. Where they disagree, they reveal places where recent fire history and structural landscape conditions tell different stories and require closer investigation.

Neither layer is a buyer threshold, a property certification or a test of model accuracy.

## Slide 6 — Model comparison

The final model is compared with a simple historical-recurrence baseline. The baseline uses only the rolling number of previously burned years within the 2 km context. It provides a transparent reference for deciding whether the additional predictors add useful information.

The nine-feature model combines fire history, land cover, terrain and climate. It uses one HistGradientBoosting component to estimate whether burning occurs and another to estimate burned share for records where burning occurs. These results are combined into one continuous next-year burned-share estimate.

During the final temporal evaluation, MAE improved from 0.0292 for the recurrence baseline to 0.0209 for the nine-feature model. RMSE changed only slightly, from 0.1106 to 0.1110, showing that unusually large fire outcomes remain difficult.

Capture@20% improved from 40.2% to 57.2%. This means that the highest-ranked 20% of evaluated cell-year records contained 57.2% of the burned-share total that was subsequently observed. It is a retrospective ranking measure, not the percentage of Portugal that burned and not a buyer threshold.

## Slide 7 — Recommended use case

A prospective buyer can start with the 2026 comparative estimate to compare broad 1 km areas. The historical-recurrence and official structural-hazard layers provide additional context for the same locations.

The result is not a selected property. It is a smaller, more structured set of broad areas for site visits and detailed research.

## Slide 8 — Compare and verify

The 2026 estimate, historical recurrence and official structural hazard should remain separate because they answer different questions. Comparing them helps identify areas that deserve closer investigation.

For shortlisted locations, broad national evidence must be supplemented with local planning restrictions, access and evacuation conditions, vegetation management, insurance, terrain, infrastructure and property-specific information.

The model directs research effort; it does not replace local investigation.

## Slide 9 — Conclusion and next step

The project delivers a validated national 1 km grid, integrated public datasets, historical and official GIS evidence layers, a tested nine-feature model and a comparative 2026 map.

The model improves average error and geographical ranking compared with historical recurrence alone, although extreme wildfire outcomes remain difficult. Its practical value is helping users narrow broad location-search areas while keeping the evidence traceable.

When completed 2026 source and outcome data become available, the workflow can evaluate the current estimate, incorporate the new labelled year, rebuild the model and produce the next annual comparative layer.

The project does not identify a guaranteed safe property. It provides a repeatable way to compare broad areas and focus detailed research where it is most useful.
