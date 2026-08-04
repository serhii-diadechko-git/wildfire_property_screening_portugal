"""Read-only ICNF annual coverage audit; extracts ZIP members only to a temp directory."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import geopandas as gpd
from pyproj import CRS

ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/'data/raw/wildfire/icnf_burned_areas'; REPORT=ROOT/'reports/validation/icnf_2005_2025_coverage_audit.md'
def inspect_zip(path):
    with ZipFile(path) as z:
        members=[x for x in z.namelist() if not x.endswith('/')]; shps=[x for x in members if x.lower().endswith('.shp')]
        if not shps: return {'archive':path.name,'members':members,'layers':[]}
        layers=[]
        with TemporaryDirectory(prefix='icnf_audit_') as d:
            for shp in shps:
                stem=Path(shp).with_suffix(''); required=[str(stem)+x for x in ('.shp','.shx','.dbf','.prj')]; present=all(x in members for x in required)
                for m in members:
                    if Path(m).with_suffix('')==stem: z.extract(m,d)
                if present:
                    f=gpd.read_file(Path(d)/shp); layers.append({'name':shp,'sidecars':present,'count':len(f),'types':','.join(sorted(f.geom_type.unique())),'crs':str(f.crs),'fields':', '.join(f.columns.drop('geometry')),'empty':int(f.geometry.is_empty.sum()),'invalid':int((~f.geometry.is_valid).sum()),'bounds':tuple(round(float(x),2) for x in f.total_bounds),'years':sorted(map(str,f['Ano'].dropna().unique())) if 'Ano' in f else []})
        return {'archive':path.name,'members':members,'layers':layers}
def main():
    results=[inspect_zip(p) for p in sorted(RAW.glob('ardida_*.zip'))]
    lines=['# ICNF 2005–2025 raw coverage audit','','Raw ZIP files were inspected in place; Shapefile members were extracted only to system temporary directories.','','| Archive / layer | Features | Geometry | CRS | Sidecars | Empty / invalid | Bounds | Ano values | Usability |','|---|---:|---|---|---|---:|---|---|---|']
    found=set()
    for r in results:
        for x in r['layers']:
            years=x['years']; found.update(int(y) for y in years if y.isdigit()); usable='Yes: polygon, CRS/schema require derived validation' if x['sidecars'] and x['types'] in ('Polygon','MultiPolygon','MultiPolygon,Polygon') else 'No / inspect'
            lines.append(f"| `{r['archive']}` / `{x['name']}` | {x['count']} | {x['types']} | {x['crs']} | {x['sidecars']} | {x['empty']} / {x['invalid']} | {x['bounds']} | {', '.join(years)} | {usable} |")
    missing=[str(y) for y in range(2005,2026) if y not in found]
    multi=next((r for r in results if r['archive']=='ardida_2000_2008.zip'),None)
    lines += ['',f"Missing annual coverage in 2005–2025: {', '.join(missing) or 'none identified from Ano fields'}.",f"`ardida_2000_2008.zip` members: {', '.join(multi['members']) if multi else 'not found'}."]
    REPORT.write_text('\n'.join(lines),encoding='utf-8'); print('\n'.join(lines))
if __name__=='__main__': main()
