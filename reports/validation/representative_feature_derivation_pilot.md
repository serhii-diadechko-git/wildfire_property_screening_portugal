# Representative canonical feature-derivation pilot

This is a controlled implementation/data-contract sample, not the national panel and not a model output. It uses the existing canonical grid without rebuilding it.

## Feature contract

Uniqueness key: `cell_id` x `observation_year`. Geometry remains EPSG:3763 in the GeoPackage and is separate from the analytical Parquet table.

| Field | Type | Unit | Allowed range | Missing rule | Source-year rule |
|---|---|---|---|---|---|
| `built_up_share` | float64 | share_of_cell_land_area | 0.0 to 1.0 | forbidden | governed CLC reference year assigned to T |
| `forest_shrub_share_2km` | float64 | share_of_mainland_land_in_2km_outward_buffer | 0.0 to 1.0 | forbidden | governed CLC reference year assigned to T |
| `mean_slope_2km` | float64 | degrees | 0.0 to 90.0 | forbidden | static Copernicus DEM GLO-30 2021 release |
| `fire_years_previous_10y_2km` | int8 | count_of_distinct_years | 0.0 to 10.0 | forbidden | inclusive T-10 through T-1 |
| `warm_season_mean_2m_temperature_c` | float64 | degrees_Celsius | -20.0 to 60.0 | era5_land_mask_allowed | JJAS of T only |
| `warm_season_total_precipitation_mm` | float64 | millimetres_JJAS_total | 0.0 to 3000.0 | era5_land_mask_allowed | day-weighted JJAS of T only |
| `warm_season_mean_soil_water_layer1` | float64 | m3_per_m3 | 0.0 to 1.0 | era5_land_mask_allowed | JJAS of T only |
| `burned_share_next_year` | float64 | share_of_cell_land_area | 0.0 to 1.0 | forbidden | ICNF burned-area geometry in T+1 |

## Validation

```json
{
  "row_count": 40,
  "expected_row_count": 40,
  "unique_analytical_key": true,
  "years": [
    "2015",
    "2016",
    "2019",
    "2023"
  ],
  "cell_count": 10,
  "missingness": {
    "cell_year_id": 0,
    "cell_id": 0,
    "observation_year": 0,
    "outcome_year": 0,
    "historical_fire_start_year": 0,
    "historical_fire_end_year": 0,
    "climate_reference_year": 0,
    "land_cover_reference_year": 0,
    "land_cover_release_id": 0,
    "land_cover_release_date": 0,
    "terrain_release_id": 0,
    "built_up_share": 0,
    "forest_shrub_share_2km": 0,
    "mean_slope_2km": 0,
    "fire_years_previous_10y_2km": 0,
    "warm_season_mean_2m_temperature_c": 4,
    "warm_season_total_precipitation_mm": 4,
    "warm_season_mean_soil_water_layer1": 4,
    "burned_share_next_year": 0
  },
  "crs": "EPSG:3763",
  "sample_reasons": {
    "PT3763_002356": "high built-up share with valid ERA5 land context",
    "PT3763_080948": "high forest/shrub share",
    "PT3763_001564": "maximum prior-fire-year count in the existing 2023 feasibility artifact",
    "PT3763_000000": "coastal/boundary cell in an ERA5-Land water-mask coarse cell",
    "PT3763_037982": "wet northern forest context",
    "PT3763_040163": "dry southern forest context",
    "PT3763_034039": "contains the representative point of the largest repaired 2016 perimeter",
    "PT3763_039441": "contains the representative point of the largest repaired 2017 perimeter",
    "PT3763_053960": "contains the representative point of the largest repaired 2020 perimeter",
    "PT3763_043203": "contains the representative point of the largest repaired 2024 perimeter"
  },
  "clc_candidate_counts": {
    "2006": {
      "PT3763_002356": 15,
      "PT3763_080948": 28,
      "PT3763_001564": 49,
      "PT3763_000000": 15,
      "PT3763_037982": 19,
      "PT3763_040163": 18,
      "PT3763_034039": 16,
      "PT3763_039441": 32,
      "PT3763_053960": 7,
      "PT3763_043203": 20
    },
    "2012": {
      "PT3763_002356": 19,
      "PT3763_080948": 31,
      "PT3763_001564": 50,
      "PT3763_000000": 15,
      "PT3763_037982": 16,
      "PT3763_040163": 20,
      "PT3763_034039": 17,
      "PT3763_039441": 37,
      "PT3763_053960": 7,
      "PT3763_043203": 21
    },
    "2018": {
      "PT3763_002356": 20,
      "PT3763_080948": 31,
      "PT3763_001564": 50,
      "PT3763_000000": 15,
      "PT3763_037982": 16,
      "PT3763_040163": 20,
      "PT3763_034039": 16,
      "PT3763_039441": 35,
      "PT3763_053960": 7,
      "PT3763_043203": 22
    }
  },
  "slope_diagnostics": {
    "PT3763_002356": {
      "dem_tiles": [
        "N38_00_W010_00"
      ],
      "metric_pixel_count": 18995,
      "metric_resolution_metres": 30.0
    },
    "PT3763_080948": {
      "dem_tiles": [
        "N40_00_W008_00"
      ],
      "metric_pixel_count": 23455,
      "metric_resolution_metres": 30.0
    },
    "PT3763_001564": {
      "dem_tiles": [
        "N38_00_W010_00"
      ],
      "metric_pixel_count": 23456,
      "metric_resolution_metres": 30.0
    },
    "PT3763_000000": {
      "dem_tiles": [
        "N38_00_W010_00"
      ],
      "metric_pixel_count": 9684,
      "metric_resolution_metres": 30.0
    },
    "PT3763_037982": {
      "dem_tiles": [
        "N41_00_W009_00"
      ],
      "metric_pixel_count": 23317,
      "metric_resolution_metres": 30.0
    },
    "PT3763_040163": {
      "dem_tiles": [
        "N37_00_W009_00"
      ],
      "metric_pixel_count": 23638,
      "metric_resolution_metres": 30.0
    },
    "PT3763_034039": {
      "dem_tiles": [
        "N40_00_W009_00"
      ],
      "metric_pixel_count": 23643,
      "metric_resolution_metres": 30.0
    },
    "PT3763_039441": {
      "dem_tiles": [
        "N40_00_W009_00"
      ],
      "metric_pixel_count": 23555,
      "metric_resolution_metres": 30.0
    },
    "PT3763_053960": {
      "dem_tiles": [
        "N39_00_W008_00"
      ],
      "metric_pixel_count": 23390,
      "metric_resolution_metres": 30.0
    },
    "PT3763_043203": {
      "dem_tiles": [
        "N40_00_W008_00",
        "N40_00_W009_00"
      ],
      "metric_pixel_count": 23552,
      "metric_resolution_metres": 30.0
    }
  },
  "icnf_geometry_repair": {
    "2005": {
      "year": 2005,
      "input_count": 1459,
      "invalid_before_count": 3,
      "repaired_count": 3,
      "rejected_count": 0,
      "accepted_count": 1459,
      "sample_candidate_count": 5,
      "input_area_m2": 3463627183.746269,
      "accepted_area_m2": 3463627183.7462716,
      "total_area_change_percent": 6.883494280804445e-14,
      "repairs_area_change_over_0_1_percent": 0,
      "repairs_area_change_over_1_percent": 0,
      "repairs_area_change_over_5_percent": 0
    },
    "2006": {
      "year": 2006,
      "input_count": 715,
      "invalid_before_count": 146,
      "repaired_count": 146,
      "rejected_count": 0,
      "accepted_count": 715,
      "sample_candidate_count": 4,
      "input_area_m2": 726815639.7463101,
      "accepted_area_m2": 726815639.7463093,
      "total_area_change_percent": -1.1481109943461493e-13,
      "repairs_area_change_over_0_1_percent": 0,
      "repairs_area_change_over_1_percent": 0,
      "repairs_area_change_over_5_percent": 0
    },
    "2007": {
      "year": 2007,
      "input_count": 737,
      "invalid_before_count": 10,
      "repaired_count": 10,
      "rejected_count": 0,
      "accepted_count": 737,
      "sample_candidate_count": 5,
      "input_area_m2": 383213552.75264996,
      "accepted_area_m2": 383213552.7526502,
      "total_area_change_percent": 6.22155916430891e-14,
      "repairs_area_change_over_0_1_percent": 0,
      "repairs_area_change_over_1_percent": 0,
      "repairs_area_change_over_5_percent": 0
    },
    "2008": {
      "year": 2008,
      "input_count": 719,
      "invalid_before_count": 8,
      "repaired_count": 8,
      "rejected_count": 0,
      "accepted_count": 719,
      "sample_candidate_count": 13,
      "input_area_m2": 119613408.85520332,
      "accepted_area_m2": 119613408.8552033,
      "total_area_change_percent": -1.2457768185409791e-14,
      "repairs_area_change_over_0_1_percent": 0,
      "repairs_area_change_over_1_percent": 0,
      "repairs_area_change_over_5_percent": 0
    },
    "2009": {
      "year": 2009,
      "input_count": 1441,
      "invalid_before_count": 22,
      "repaired_count": 22,
      "rejected_count": 0,
      "accepted_count": 1441,
      "sample_candidate_count": 2,
      "input_area_m2": 931974256.0308859,
      "accepted_area_m2": 931974256.0308862,
      "total_area_change_percent": 2.5582099243486103e-14,
      "repairs_area_change_over_0_1_percent": 0,
      "repairs_area_change_over_1_percent": 0,
      "repairs_area_change_over_5_percent": 0
    },
    "2010": {
      "year": 2010,
      "input_count": 2513,
      "invalid_before_count": 40,
      "repaired_count": 40,
      "rejected_count": 0,
      "accepted_count": 2513,
      "sample_candidate_count": 3,
      "input_area_m2": 1312683364.116287,
      "accepted_area_m2": 1312683364.1162865,
      "total_area_change_percent": -3.6325375276172334e-14,
      "repairs_area_change_over_0_1_percent": 0,
      "repairs_area_change_over_1_percent": 0,
      "repairs_area_change_over_5_percent": 0
    },
    "2011": {
      "year": 2011,
      "input_count": 3686,
      "invalid_before_count": 33,
      "repaired_count": 33,
      "rejected_count": 0,
      "accepted_count": 3686,
      "sample_candidate_count": 14,
      "input_area_m2": 802293244.7857267,
      "accepted_area_m2": 802293244.7857269,
      "total_area_change_percent": 2.971713655213916e-14,
      "repairs_area_change_over_0_1_percent": 0,
      "repairs_area_change_over_1_percent": 0,
      "repairs_area_change_over_5_percent": 0
    },
    "2012": {
      "year": 2012,
      "input_count": 2971,
      "invalid_before_count": 41,
      "repaired_count": 41,
      "rejected_count": 0,
      "accepted_count": 2971,
      "sample_candidate_count": 8,
      "input_area_m2": 1135759629.5472739,
      "accepted_area_m2": 1135759629.5472717,
      "total_area_change_percent": -1.8892793475758497e-13,
      "repairs_area_change_over_0_1_percent": 0,
      "repairs_area_change_over_1_percent": 0,
      "repairs_area_change_over_5_percent": 0
    },
    "2013": {
      "year": 2013,
      "input_count": 3150,
      "invalid_before_count": 111,
      "repaired_count": 111,
      "rejected_count": 0,
      "accepted_count": 3150,
      "sample_candidate_count": 11,
      "input_area_m2": 1493396264.8112693,
      "accepted_area_m2": 1493396264.8112724,
      "total_area_change_percent": 2.0754314185404838e-13,
      "repairs_area_change_over_0_1_percent": 0,
      "repairs_area_change_over_1_percent": 0,
      "repairs_area_change_over_5_percent": 0
    },
    "2014": {
      "year": 2014,
      "input_count": 1100,
      "invalid_before_count": 72,
      "repaired_count": 72,
      "rejected_count": 0,
      "accepted_count": 1100,
      "sample_candidate_count": 6,
      "input_area_m2": 183267437.99518663,
      "accepted_area_m2": 183267437.99518675,
      "total_area_change_percent": 6.504662849813625e-14,
      "repairs_area_change_over_0_1_percent": 0,
      "repairs_area_change_over_1_percent": 0,
      "repairs_area_change_over_5_percent": 0
    },
    "2015": {
      "year": 2015,
      "input_count": 1651,
      "invalid_before_count": 83,
      "repaired_count": 83,
      "rejected_count": 0,
      "accepted_count": 1651,
      "sample_candidate_count": 10,
      "input_area_m2": 564017388.4030249,
      "accepted_area_m2": 564017388.4030244,
      "total_area_change_percent": -8.454298892331235e-14,
      "repairs_area_change_over_0_1_percent": 0,
      "repairs_area_change_over_1_percent": 0,
      "repairs_area_change_over_5_percent": 0
    },
    "2016": {
      "year": 2016,
      "input_count": 2838,
      "invalid_before_count": 111,
      "repaired_count": 111,
      "rejected_count": 0,
      "accepted_count": 2838,
      "sample_candidate_count": 9,
      "input_area_m2": 1582929746.7844412,
      "accepted_area_m2": 1582929746.7844396,
      "total_area_change_percent": -1.0543298318205195e-13,
      "repairs_area_change_over_0_1_percent": 0,
      "repairs_area_change_over_1_percent": 0,
      "repairs_area_change_over_5_percent": 0
    },
    "2017": {
      "year": 2017,
      "input_count": 2765,
      "invalid_before_count": 27,
      "repaired_count": 27,
      "rejected_count": 0,
      "accepted_count": 2765,
      "sample_candidate_count": 14,
      "input_area_m2": 5610097959.833929,
      "accepted_area_m2": 5610097959.83394,
      "total_area_change_percent": 1.8699169881838016e-13,
      "repairs_area_change_over_0_1_percent": 0,
      "repairs_area_change_over_1_percent": 0,
      "repairs_area_change_over_5_percent": 0
    },
    "2018": {
      "year": 2018,
      "input_count": 537,
      "invalid_before_count": 24,
      "repaired_count": 24,
      "rejected_count": 0,
      "accepted_count": 537,
      "sample_candidate_count": 2,
      "input_area_m2": 402795209.9128434,
      "accepted_area_m2": 402795209.9128443,
      "total_area_change_percent": 2.2196631181992398e-13,
      "repairs_area_change_over_0_1_percent": 0,
      "repairs_area_change_over_1_percent": 0,
      "repairs_area_change_over_5_percent": 0
    },
    "2019": {
      "year": 2019,
      "input_count": 1725,
      "invalid_before_count": 54,
      "repaired_count": 54,
      "rejected_count": 0,
      "accepted_count": 1725,
      "sample_candidate_count": 3,
      "input_area_m2": 401896026.9132007,
      "accepted_area_m2": 401896026.91320014,
      "total_area_change_percent": -1.3347775719474168e-13,
      "repairs_area_change_over_0_1_percent": 0,
      "repairs_area_change_over_1_percent": 0,
      "repairs_area_change_over_5_percent": 0
    },
    "2020": {
      "year": 2020,
      "input_count": 1777,
      "invalid_before_count": 22,
      "repaired_count": 22,
      "rejected_count": 0,
      "accepted_count": 1777,
      "sample_candidate_count": 2,
      "input_area_m2": 661671149.8068072,
      "accepted_area_m2": 661671149.8068069,
      "total_area_change_percent": -3.6032790483788705e-14,
      "repairs_area_change_over_0_1_percent": 0,
      "repairs_area_change_over_1_percent": 0,
      "repairs_area_change_over_5_percent": 0
    },
    "2021": {
      "year": 2021,
      "input_count": 918,
      "invalid_before_count": 1,
      "repaired_count": 1,
      "rejected_count": 0,
      "accepted_count": 918,
      "sample_candidate_count": 1,
      "input_area_m2": 273746288.9387452,
      "accepted_area_m2": 273746288.9387449,
      "total_area_change_percent": -1.0886840695898539e-13,
      "repairs_area_change_over_0_1_percent": 0,
      "repairs_area_change_over_1_percent": 0,
      "repairs_area_change_over_5_percent": 0
    },
    "2022": {
      "year": 2022,
      "input_count": 1786,
      "invalid_before_count": 13,
      "repaired_count": 13,
      "rejected_count": 0,
      "accepted_count": 1786,
      "sample_candidate_count": 2,
      "input_area_m2": 1151486007.2347212,
      "accepted_area_m2": 1151486007.2347214,
      "total_area_change_percent": 2.0705295383842452e-14,
      "repairs_area_change_over_0_1_percent": 0,
      "repairs_area_change_over_1_percent": 0,
      "repairs_area_change_over_5_percent": 0
    },
    "2024": {
      "year": 2024,
      "input_count": 1558,
      "invalid_before_count": 0,
      "repaired_count": 0,
      "rejected_count": 0,
      "accepted_count": 1558,
      "sample_candidate_count": 2,
      "input_area_m2": 1393968488.471228,
      "accepted_area_m2": 1393968488.4712245,
      "total_area_change_percent": -2.3945018377585584e-13,
      "repairs_area_change_over_0_1_percent": 0,
      "repairs_area_change_over_1_percent": 0,
      "repairs_area_change_over_5_percent": 0
    }
  },
  "source_year_alignment": {
    "2015": {
      "predictor_year": 2015,
      "history_years": [
        2005,
        2006,
        2007,
        2008,
        2009,
        2010,
        2011,
        2012,
        2013,
        2014
      ],
      "climate_year": 2015,
      "land_cover_reference_year": 2006,
      "outcome_year": 2016
    },
    "2016": {
      "predictor_year": 2016,
      "history_years": [
        2006,
        2007,
        2008,
        2009,
        2010,
        2011,
        2012,
        2013,
        2014,
        2015
      ],
      "climate_year": 2016,
      "land_cover_reference_year": 2012,
      "outcome_year": 2017
    },
    "2019": {
      "predictor_year": 2019,
      "history_years": [
        2009,
        2010,
        2011,
        2012,
        2013,
        2014,
        2015,
        2016,
        2017,
        2018
      ],
      "climate_year": 2019,
      "land_cover_reference_year": 2018,
      "outcome_year": 2020
    },
    "2023": {
      "predictor_year": 2023,
      "history_years": [
        2013,
        2014,
        2015,
        2016,
        2017,
        2018,
        2019,
        2020,
        2021,
        2022
      ],
      "climate_year": 2023,
      "land_cover_reference_year": 2018,
      "outcome_year": 2024
    }
  },
  "deterministic_repeated_run": true,
  "statistics": {
    "built_up_share": {
      "minimum": 0.0,
      "maximum": 1.0,
      "mean": 0.1006828516955296,
      "missing": 0,
      "zero": 32
    },
    "forest_shrub_share_2km": {
      "minimum": 0.0,
      "maximum": 0.98793580612821,
      "mean": 0.6584479667091502,
      "missing": 0,
      "zero": 4
    },
    "mean_slope_2km": {
      "minimum": 4.789638042449951,
      "maximum": 24.011301040649414,
      "mean": 13.645237302780151,
      "missing": 0,
      "zero": 0
    },
    "fire_years_previous_10y_2km": {
      "minimum": 0.0,
      "maximum": 10.0,
      "mean": 2.7,
      "missing": 0,
      "zero": 9
    },
    "warm_season_mean_2m_temperature_c": {
      "minimum": 17.202172851562523,
      "maximum": 24.334802246093773,
      "mean": 20.63785875108509,
      "missing": 4,
      "zero": 0
    },
    "warm_season_total_precipitation_mm": {
      "minimum": 8.80785087088043,
      "maximum": 370.7149380206829,
      "mean": 116.26205738661118,
      "missing": 4,
      "zero": 0
    },
    "warm_season_mean_soil_water_layer1": {
      "minimum": 0.0971832275390625,
      "maximum": 0.3423614501953125,
      "mean": 0.1818598641289605,
      "missing": 4,
      "zero": 0
    },
    "burned_share_next_year": {
      "minimum": 0.0,
      "maximum": 1.0,
      "mean": 0.10192021947463736,
      "missing": 0,
      "zero": 34
    }
  },
  "created_utc": "2026-08-05T08:55:19.983332+00:00",
  "reopened_output_validation": {
    "row_count": 40,
    "expected_row_count": 40,
    "unique_analytical_key": true,
    "years": [
      "2015",
      "2016",
      "2019",
      "2023"
    ],
    "cell_count": 10,
    "missingness": {
      "cell_year_id": 0,
      "cell_id": 0,
      "observation_year": 0,
      "outcome_year": 0,
      "historical_fire_start_year": 0,
      "historical_fire_end_year": 0,
      "climate_reference_year": 0,
      "land_cover_reference_year": 0,
      "land_cover_release_id": 0,
      "land_cover_release_date": 0,
      "terrain_release_id": 0,
      "built_up_share": 0,
      "forest_shrub_share_2km": 0,
      "mean_slope_2km": 0,
      "fire_years_previous_10y_2km": 0,
      "warm_season_mean_2m_temperature_c": 4,
      "warm_season_total_precipitation_mm": 4,
      "warm_season_mean_soil_water_layer1": 4,
      "burned_share_next_year": 0
    }
  }
}
```
