"""Retrieve and immediately validate immutable ERA5-Land JJAS annual GRIBs."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
import cdsapi
import xarray as xr
from src.config import ERA5_LAND, ERA5_LAND_CDS
from src.era5_land_validation import validate_era5_land_pilot_grib

YEARS=range(2015,2022)
def request(year):
    return {'product_type':['monthly_averaged_reanalysis'],'variable':list(ERA5_LAND.variables),'year':[str(year)],'month':['06','07','08','09'],'time':['00:00'],'data_format':'grib','download_format':'unarchived','area':list(ERA5_LAND_CDS.mainland_portugal_area)}
def validate(target,year):
    for short,expected in [('2t','t2m'),('tp','tp'),('swvl1','swvl1')]:
        ds=xr.open_dataset(target,engine='cfgrib',backend_kwargs={'indexpath':'','filter_by_keys':{'shortName':short}})
        try:
            if list(ds.data_vars)!=[expected] or tuple(ds.sizes.values()) != (4,55,37): raise ValueError(f'{year}: unexpected {short} layout')
            if tuple(str(x.astype('datetime64[M]'))[-2:] for x in ds.time.values)!=('06','07','08','09'): raise ValueError(f'{year}: unexpected months')
            if (float(ds.latitude.max()),float(ds.longitude.min()),float(ds.latitude.min()),float(ds.longitude.max())) != tuple(ERA5_LAND_CDS.mainland_portugal_area): raise ValueError(f'{year}: unexpected area')
        finally: ds.close()
def main():
    outdir=ROOT/'data/raw/climate/era5_land'; client=cdsapi.Client()
    for year in YEARS:
        target=outdir/f'era5_land_monthly_jjas_{year}_mainland_portugal.grib'
        if target.exists(): raise FileExistsError(f'Refusing to overwrite raw file: {target}')
        client.retrieve(ERA5_LAND_CDS.dataset_id,request(year),str(target))
        validate(target,year)
        print(f'Downloaded {target.name}',flush=True)
if __name__=='__main__': main()
