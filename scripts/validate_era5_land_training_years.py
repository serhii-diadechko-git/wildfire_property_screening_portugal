from pathlib import Path
import hashlib, json
import xarray as xr
ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/'data/raw/climate/era5_land'
def main():
 r={}
 for y in range(2015,2022):
  p=RAW/f'era5_land_monthly_jjas_{y}_mainland_portugal.grib'; facts={}
  for s,e in [('2t','t2m'),('tp','tp'),('swvl1','swvl1')]:
   d=xr.open_dataset(p,engine='cfgrib',backend_kwargs={'indexpath':'','filter_by_keys':{'shortName':s}}); v=next(iter(d.data_vars)); facts[s]={'variable':v,'shape':tuple(d.sizes.values()),'units':d[v].attrs.get('units'),'step_type':d[v].attrs.get('GRIB_stepType'),'bounds':[float(d.latitude.max()),float(d.longitude.min()),float(d.latitude.min()),float(d.longitude.max())]}; d.close()
  if any(x['shape']!=(4,55,37) for x in facts.values()) or facts['2t']['variable']!='t2m' or facts['tp']['step_type']!='avgad': raise ValueError(f'{y} inconsistent')
  r[y]={'path':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(p.read_bytes()).hexdigest().upper(),'facts':facts}
 print(json.dumps(r,indent=2))
if __name__=='__main__':main()
