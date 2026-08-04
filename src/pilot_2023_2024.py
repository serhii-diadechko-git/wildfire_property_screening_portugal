"""Reproducible, derived-only preparation for the 2023 -> 2024 pilot."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import json
import shutil
import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from shapely import make_valid
from shapely.geometry import box
from src.config import PILOT_2023_TO_2024, SPATIAL, ERA5_LAND_CDS
from src.source_registry import PILOT_ICNF_ARCHIVES

ROOT = Path(__file__).resolve().parents[1]

def _polygonal(g):
    if g is None or g.is_empty: return None
    if g.geom_type in ("Polygon", "MultiPolygon"): return g
    if g.geom_type == "GeometryCollection":
        parts=[x for x in g.geoms if x.geom_type in ("Polygon","MultiPolygon")]
        return gpd.GeoSeries(parts, crs=3763).union_all() if parts else None
    return None

def grid(boundary):
    minx,miny,maxx,maxy=boundary.total_bounds; s=SPATIAL.grid_size_metres
    xs=np.arange(np.floor(minx/s)*s, np.ceil(maxx/s)*s, s); ys=np.arange(np.floor(miny/s)*s, np.ceil(maxy/s)*s,s)
    cells=[box(x,y,x+s,y+s) for x in xs for y in ys]
    ids=[f"PT3763_{int(x//s)}_{int(y//s)}" for x in xs for y in ys]
    mainland=boundary.geometry.iloc[0]; kept=[]
    # Chunking avoids materialising intersections for every inland grid square.
    for start in range(0,len(cells),5000):
        geom=cells[start:start+5000]; chunk=gpd.GeoDataFrame({"cell_id":ids[start:start+5000]},geometry=geom,crs=3763)
        chunk=chunk[chunk.intersects(mainland)].copy()
        inside=chunk.geometry.within(mainland)
        if (~inside).any(): chunk.loc[~inside,"geometry"]=chunk.loc[~inside,"geometry"].intersection(mainland)
        kept.append(chunk)
    g=pd.concat(kept,ignore_index=True); g=gpd.GeoDataFrame(g,geometry="geometry",crs=3763); g["cell_land_area_m2"]=g.area
    return g

def _fire(year, boundary, log):
    record=PILOT_ICNF_ARCHIVES[year]; z=ROOT/record.raw_path
    with TemporaryDirectory(prefix="pilot_icnf_") as d:
        with ZipFile(z) as a:
            for m in record.required_members: a.extract(m,d)
        p=next(Path(d).glob("*.shp")); raw=gpd.read_file(p).to_crs(3763)
    repaired=[]; changed=[]; rejected=0
    for x in raw.geometry:
        y=make_valid(x); q=_polygonal(y)
        if q is None: rejected+=1; continue
        repaired.append(q); changed.append(abs(q.area-x.area)/x.area if x.area else 0)
    out=gpd.GeoDataFrame(geometry=repaired,crs=3763); out=out[out.intersects(boundary.geometry.iloc[0])]
    out["geometry"]=out.geometry.intersection(boundary.geometry.iloc[0]); out=out[~out.geometry.is_empty]
    log[str(year)]={"input":len(raw),"repaired":sum(not x.is_valid for x in raw.geometry),"rejected":rejected,"kept":len(out),"area_change_over_0_1pct":sum(x>.001 for x in changed)}
    return out.geometry.union_all()

def burned_share(cells, fire):
    hit=cells[cells.intersects(fire)].copy(); vals=pd.Series(0.,index=cells.index)
    vals.loc[hit.index]=hit.geometry.intersection(fire).area/hit.cell_land_area_m2
    return vals.clip(0,1)

def clc(cells):
    c=gpd.read_file(ROOT/'data/interim/clc_2018_mainland.gpkg').to_crs(3035)
    x=cells.to_crs(3035)[["cell_id","geometry"]]
    o=gpd.overlay(x,c[["Code_18","geometry"]],how="intersection"); o["a"]=o.area
    built={str(i) for i in (111,112,121,122,123,124,131,132,133,141,142)}
    forest={str(i) for i in (311,312,313,321,322,323,324)}; ag={str(i) for i in (211,212,213,221,222,223,231,241,242,243,244)}
    out=pd.DataFrame(index=cells.cell_id); denom=x.set_index('cell_id').area
    for name,codes in [('built_up_share',built),('forest_shrub_share',forest),('agricultural_share',ag)]:
        out[name]=o[o.Code_18.astype(str).isin(codes)].groupby('cell_id').a.sum().reindex(out.index,fill_value=0).div(denom).clip(0,1)
    return out

def climate(cells):
    p=ROOT/ERA5_LAND_CDS.pilot_raw_output; centers=cells.geometry.centroid.to_crs(4326)
    result=pd.DataFrame(index=cells.index)
    for short,name,fn in [('2t','warm_season_mean_2m_temperature_c',lambda a:np.nanmean(a,0)-273.15),('tp','warm_season_total_precipitation_mm',lambda a:np.nansum(a,0)*1000),('swvl1','warm_season_mean_soil_water_layer1',lambda a:np.nanmean(a,0))]:
        ds=xr.open_dataset(p,engine='cfgrib',backend_kwargs={'indexpath':'','filter_by_keys':{'shortName':short}}); v=next(iter(ds.data_vars)); arr=fn(ds[v].values); lat=ds.latitude.values; lon=ds.longitude.values
        iy=np.abs(lat[:,None]-centers.y.to_numpy()).argmin(0); ix=np.abs(lon[:,None]-centers.x.to_numpy()).argmin(0); result[name]=arr[iy,ix]; ds.close()
    return result

def run():
    b=gpd.read_file(ROOT/'data/processed/reference/mainland_boundary_caop2025.gpkg').to_crs(3763); cells=grid(b); log={}
    fires={y:_fire(y,b,log) for y in range(2013,2023)}; target=_fire(2024,b,log)
    f=cells[['cell_id','cell_land_area_m2','geometry']].copy(); f['observation_year']=2023; f['cell_year_id']=f.cell_id+'_2023'
    f['fire_years_previous_10y_2km']=sum(cells.geometry.buffer(2000).intersects(x).astype(int) for x in fires.values())
    f['burned_share_next_year']=burned_share(cells,target).to_numpy(); f=f.join(clc(cells),on='cell_id').join(climate(cells))
    out=ROOT/'data/processed/pilot_2023_2024_features.parquet'; out.parent.mkdir(parents=True,exist_ok=True); f.to_parquet(out,index=False)
    fig=ROOT/'reports/figures/pilot_2024_burned_share.png'; fig.parent.mkdir(parents=True,exist_ok=True); f.plot(column='burned_share_next_year',markersize=1,legend=True).get_figure().savefig(fig,dpi=180,bbox_inches='tight')
    report=ROOT/'reports/validation/pilot_2023_2024_validation.md'; report.parent.mkdir(parents=True,exist_ok=True)
    missing=f.drop(columns='geometry').isna().sum().to_dict(); report.write_text(f"# Pilot validation\n\nRows: {len(f)}. Unique cell_id: {f.cell_id.is_unique}. ICNF 2023 used: no. Target range: {f.burned_share_next_year.min()}–{f.burned_share_next_year.max()}.\n\nMissing values: `{json.dumps(missing)}`\n\nRepair log: `{json.dumps(log)}`\n")
    return f,log

def run_enrichment(tile_size: int = 2000):
    """Enrich the existing ICNF/CAOP stage without reconstructing the grid."""
    base=ROOT/'data/processed/pilot_2023_to_2024/pilot_2023_to_2024_icnf_caop.gpkg'
    g=gpd.read_file(base).to_crs(3763)
    if len(g)!=89112 or not g.cell_id.is_unique or not g.burned_share_next_year.between(0,1).all():
        raise ValueError('Existing ICNF/CAOP pilot stage failed validation')
    if set(g.observation_year)!={2023}: raise ValueError('Pilot predictor year is not 2023')
    # CLC intersections are tiled: only the indexed CLC candidates for each tile enter memory.
    clc=gpd.read_file(ROOT/'data/interim/clc_2018_mainland.gpkg').to_crs(3035)
    gg=g[['cell_id','geometry']].to_crs(3035); shares=pd.DataFrame(0.,index=g.cell_id,columns=['built_up_share','forest_shrub_share','agricultural_share'])
    groups={'built_up_share':{'111','112','121','122','123','124','131','132','133','141','142'},'forest_shrub_share':{'311','312','313','321','322','323','324'},'agricultural_share':{'211','212','213','221','222','223','231','241','242','243','244'}}
    idx=clc.sindex
    for start in range(0,len(gg),tile_size):
        tile=gg.iloc[start:start+tile_size]; hits=list(idx.intersection(tile.total_bounds));
        if not hits: continue
        o=gpd.overlay(tile,clc.iloc[hits][['Code_18','geometry']],how='intersection'); o['area']=o.area
        denom=tile.set_index('cell_id').area
        for col,codes in groups.items(): shares.loc[tile.cell_id,col]=o[o.Code_18.astype(str).isin(codes)].groupby('cell_id').area.sum().reindex(tile.cell_id,fill_value=0).div(denom.reindex(tile.cell_id)).to_numpy()
    g=g.join(shares,on='cell_id')
    # Containing ERA5-Land grid cell: nearest coordinate selects the containing 0.1 degree centre.
    climate(g)  # verifies the raw GRIB remains readable before assignment
    vals=climate(g); g=g.join(vals)
    if not g.burned_share_next_year.between(0,1).all(): raise ValueError('Target outside [0,1]')
    columns=['cell_id','observation_year','fire_years_previous_10y_2km','built_up_share','forest_shrub_share','agricultural_share','warm_season_mean_2m_temperature_c','warm_season_total_precipitation_mm','warm_season_mean_soil_water_layer1','burned_share_next_year','geometry']
    g=g[columns]
    processed=ROOT/'data/processed/pilot_2023_2024_features.parquet'; gpkg=ROOT/'data/processed/pilot_2023_2024_features.gpkg'; processed.parent.mkdir(parents=True,exist_ok=True)
    g.to_parquet(processed,index=False); g.to_file(gpkg,driver='GPKG')
    map_out=ROOT/'reports/figures/pilot_2024_observed_burned_share_enriched.png'; shutil.copyfile(ROOT/'reports/figures/pilot_2023_to_2024_burned_share.png',map_out)
    missing=g.drop(columns='geometry').isna().sum().to_dict(); report=ROOT/'reports/validation/pilot_2023_2024_validation.md'; report.write_text('# Enriched 2023 → 2024 pilot validation\n\n'+json.dumps({'rows':len(g),'unique_cell_id':bool(g.cell_id.is_unique),'target_range':[float(g.burned_share_next_year.min()),float(g.burned_share_next_year.max())],'icnf_2023_used':False,'clc_method':'EPSG:3035 tiled polygon intersections','era5_method':'containing 0.1 degree ERA5-Land cell; no interpolation/downscaling','missingness':missing},indent=2))
    return g,missing
