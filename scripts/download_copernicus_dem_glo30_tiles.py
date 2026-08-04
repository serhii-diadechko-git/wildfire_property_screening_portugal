"""Acquire the fixed Copernicus DEM GLO-30 tile set for the canonical 2 km context."""

from hashlib import sha256
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.request import urlretrieve

import rasterio


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = ROOT / "data/raw/terrain/copernicus_dem_glo30_2021"
BASE_URL = "https://copernicus-dem-30m.s3.amazonaws.com"
TILES = (
    "N36_00_W009_00", "N36_00_W008_00",
    "N37_00_W010_00", "N37_00_W009_00", "N37_00_W008_00",
    "N38_00_W010_00", "N38_00_W009_00", "N38_00_W008_00", "N38_00_W007_00",
    "N39_00_W010_00", "N39_00_W009_00", "N39_00_W008_00", "N39_00_W007_00",
    "N40_00_W009_00", "N40_00_W008_00", "N40_00_W007_00",
    "N41_00_W009_00", "N41_00_W008_00", "N41_00_W007_00",
    "N42_00_W009_00", "N42_00_W008_00", "N42_00_W007_00",
)
OCEAN_NO_SOURCE_TILES = frozenset({"N37_00_W010_00"})


def product_name(tile: str) -> str:
    return f"Copernicus_DSM_COG_10_{tile}_DEM"


def checksum(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate_tile(path: Path) -> dict[str, object]:
    with rasterio.open(path) as dataset:
        if dataset.crs.to_epsg() != 4326:
            raise ValueError(f"{path.name}: expected EPSG:4326, found {dataset.crs}")
        if dataset.dtypes != ("float32",) or dataset.count != 1:
            raise ValueError(f"{path.name}: unexpected raster band contract")
        if dataset.width != 3600 or dataset.height != 3600:
            raise ValueError(f"{path.name}: unexpected raster dimensions")
        if abs(dataset.res[0] - 1 / 3600) > 1e-12 or abs(dataset.res[1] - 1 / 3600) > 1e-12:
            raise ValueError(f"{path.name}: unexpected grid spacing {dataset.res}")
        return {
            "crs": "EPSG:4326",
            "shape": (dataset.height, dataset.width),
            "resolution_degrees": dataset.res,
            "bounds": tuple(dataset.bounds),
            "dtype": dataset.dtypes[0],
            "nodata": dataset.nodata,
        }


def main() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="cop_dem_glo30_") as temporary_directory:
        temporary_directory_path = Path(temporary_directory)
        for number, tile in enumerate(TILES, start=1):
            if tile in OCEAN_NO_SOURCE_TILES:
                print(
                    f"[{number}/{len(TILES)}] {tile} is an audited ocean/no-source edge tile; skipped",
                    flush=True,
                )
                continue
            name = product_name(tile)
            filename = f"{name}.tif"
            target = OUTPUT_DIRECTORY / filename
            if target.exists():
                facts = validate_tile(target)
                print(
                    f"[{number}/{len(TILES)}] Existing immutable tile validated: {filename}, "
                    f"SHA-256 {checksum(target)}, bounds {facts['bounds']}",
                    flush=True,
                )
                continue
            temporary_path = temporary_directory_path / filename
            url = f"{BASE_URL}/{name}/{filename}"
            print(f"[{number}/{len(TILES)}] Downloading {filename}", flush=True)
            try:
                urlretrieve(url, temporary_path)
            except HTTPError as error:
                if error.code == 404:
                    print(
                        f"[{number}/{len(TILES)}] No public GLO-30 tile for {tile}; "
                        "retain as an ocean/no-source edge tile in the acquisition log",
                        flush=True,
                    )
                    continue
                raise
            facts = validate_tile(temporary_path)
            digest = checksum(temporary_path)
            # Copying into the repository gives the file the workspace's inherited ACL;
            # moving a Windows temporary file can retain a restrictive temporary ACL.
            copyfile(temporary_path, target)
            print(
                f"[{number}/{len(TILES)}] Validated {filename}: "
                f"{target.stat().st_size} bytes, SHA-256 {digest}, bounds {facts['bounds']}",
                flush=True,
            )


if __name__ == "__main__":
    main()
