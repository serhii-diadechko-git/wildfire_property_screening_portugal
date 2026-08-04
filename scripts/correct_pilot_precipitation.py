"""Correct derived JJAS precipitation without changing the raw ERA5-Land GRIB."""
from pathlib import Path
import sys, json
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
import geopandas as gpd
from src.pilot_2023_2024 import _era5_context, _assign_era5
def main():
    gp=ROOT/'data/processed/pilot_2023_2024_features.gpkg'; pq=ROOT/'data/processed/pilot_2023_2024_features.parquet'
    g=gpd.read_file(gp); before=g.warm_season_total_precipitation_mm.describe().to_dict(); grids,_=_era5_context(); corrected=_assign_era5(g,grids)
    g['warm_season_total_precipitation_mm']=corrected.warm_season_total_precipitation_mm
    if not g.warm_season_total_precipitation_mm.isna().equals(g.warm_season_mean_2m_temperature_c.isna()): raise ValueError('Coastal ERA5 masks do not match')
    g.to_parquet(pq,index=False); g.to_file(gp,driver='GPKG')
    after=g.warm_season_total_precipitation_mm.describe().to_dict(); report={'metadata':'tp has GRIB units m and stepType avgad; interpreted as m/day','formula':'1000 × (Jun×30 + Jul×31 + Aug×31 + Sep×30)','before':before,'after':after,'coastal_missing_count':int(g.warm_season_total_precipitation_mm.isna().sum())}
    (ROOT/'reports/validation/pilot_2023_2024_validation.md').write_text('# Corrected precipitation validation\n\n```json\n'+json.dumps(report,indent=2)+'\n```\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()
