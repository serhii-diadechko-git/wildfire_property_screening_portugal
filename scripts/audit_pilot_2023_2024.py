"""Read-only audit and QGIS-ready figure export for enriched pilot outputs."""
from pathlib import Path
import json
import geopandas as gpd
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
GPKG=ROOT/'data/processed/pilot_2023_2024_features.gpkg'
PARQUET=ROOT/'data/processed/pilot_2023_2024_features.parquet'
FIGURES=ROOT/'reports/figures'

def summary(series):
    return {"min":float(series.min()),"max":float(series.max()),"mean":float(series.mean()),"median":float(series.median()),"missing_count":int(series.isna().sum()),"zero_count":int(series.eq(0).sum())}

def main():
    g=gpd.read_file(GPKG); p=gpd.read_parquet(PARQUET)
    if len(g)!=len(p) or not g.drop(columns='geometry').equals(p.drop(columns='geometry')): raise ValueError('GPKG and Parquet differ')
    cols=['built_up_share','forest_shrub_share','agricultural_share','fire_years_previous_10y_2km','warm_season_mean_2m_temperature_c','warm_season_total_precipitation_mm','warm_season_mean_soil_water_layer1']
    report={c:summary(g[c]) for c in cols}
    report['row_count']=len(g); report['unique_cell_id']=bool(g.cell_id.is_unique); report['crs']=str(g.crs)
    report['era5_temperature_and_soil_missing_match']=bool(g.warm_season_mean_2m_temperature_c.isna().equals(g.warm_season_mean_soil_water_layer1.isna()))
    report['era5_temperature_missing_count']=int(g.warm_season_mean_2m_temperature_c.isna().sum())
    report['precipitation_nonzero_count']=int(g.warm_season_total_precipitation_mm.ne(0).sum())
    for col,label in [('fire_years_previous_10y_2km','Historical fire years, 2013–2022 (2 km context)'),('forest_shrub_share','CLC 2018 forest and shrub share'),('warm_season_total_precipitation_mm','ERA5-Land JJAS 2023 precipitation (as currently derived; unit audit required)')]:
        ax=g.plot(column=col,markersize=0.5,legend=True,cmap='viridis',linewidth=0); ax.set_title(label); ax.set_axis_off(); ax.get_figure().savefig(FIGURES/f'pilot_2023_2024_{col}.png',dpi=200,bbox_inches='tight'); plt.close(ax.get_figure())
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
