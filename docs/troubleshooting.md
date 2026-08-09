# Troubleshooting and known first-run behavior

This guide covers recoverable setup and reproduction issues. It does not change
the scientific workflow: raw source files remain immutable, and a failed or
slow stage must not be treated as a missing-data year.

## Start with raw-input preflight

Before diagnosing a build failure, run:

```text
python scripts/run_project.py --mode preflight
```

Preflight does not download or modify data. It reports every missing raw input
and writes a local run summary under `reports/run_logs/`. Obtain raw files only
from the official locations in `data/source_manifest.json`, place them at their
documented `data/raw/` paths, and run preflight again.

## Important: first-run data preparation can be slow

> [!IMPORTANT]
> **The initial reproduction may take substantial time and temporary disk space.**

### Why CLC can be slow

The first full reproduction clips three Europe-wide Copernicus CLC archives to
mainland Portugal. The immutable ZIP files are each several gigabytes. The
pipeline must temporarily extract a GeoPackage, spatially filter and clip CLC
polygons, write a Portugal derivative, and create its GeoPackage spatial index.
On a normal local computer, this can take a substantial amount of time and
temporary disk space; an hour or more is possible.

The derived outputs are:

| Raw source | Reusable Portugal derivative |
|---|---|
| `data/raw/clc/u2012_clc2006_v2020_20u1_geoPackage.zip` | `data/processed/clc/u2012_clc2006_v2020_20u1_pt.gpkg` |
| `data/raw/clc/u2018_clc2012_v2020_20u1_geoPackage.zip` | `data/processed/clc/u2018_clc2012_v2020_20u1_pt.gpkg` |
| `data/raw/clc/u2018_clc2018_v2020_20u1_geoPackage.zip` | `data/processed/clc/u2018_clc2018_v2020_20u1_pt.gpkg` |

Once a complete derivative exists, later runs reuse it rather than clipping the
same CLC archive again. Do not delete these derived files merely because they
are large unless you intentionally want to force CLC preparation again.

If the exact validated derivatives are available from another project copy,
place them at the paths in the table after supplying the required raw ZIPs.
Then run preflight and the CLC validation tests. Reuse avoids repeating the
expensive clip; it does not replace the immutable raw-source requirement. Raw
files remain immutable; never replace a prepared layer with an unverified
manual export.

If the stage seems quiet, first check available disk space and whether Python is
still using CPU or disk activity. Do not stop it simply because CLC geometry
processing produces no new terminal line for several minutes.

If the command genuinely fails or is interrupted, rerun the same full command:

```text
python scripts/run_project.py --mode reproduce --confirm-rebuild
```

Completed atomic outputs are reused. Inspect the associated detailed log first;
do not delete raw ZIPs or manually rename partial files.

## ERA5-Land CDS acquisition failure or timeout

The API acquisition command submits ERA5-Land requests one year at a time. A
temporary CDS queue, network, or service failure can occur after other annual
files have completed successfully.

Rerun the same safe command:

```text
python scripts/run_project.py --mode acquire-api
```

It validates existing immutable raw files, preserves successful downloads, and
retrieves only missing API-backed inputs. It checks whether a needed ERA5 file
is absent before requiring the local CDS credential file. Credentials stay in
the standard user-home location (`%USERPROFILE%\.cdsapirc` on Windows or
`~/.cdsapirc` on Linux/macOS); never place or print them in the repository.

To retry an individual request after identifying its missing year:

```text
python scripts/download_era5_land_year.py 2013 --download
```

For the registered 2022/2023 precipitation workaround, use:

```text
python scripts/download_era5_land_year.py 2023 --corrected-precipitation --download
```

After acquisition, run preflight again. Never delete or overwrite an earlier
successful raw download to retry a different year.

## A reproduction stage failed

`run_project.py` stops at the first failed stage and reports a concise error so
later stages cannot create misleading partial results. Its detailed stdout and
stderr log is written under:

```text
reports/run_logs/project_reproduce_<UTC timestamp>.log
```

Run logs are local and Git-ignored. Read the last command and traceback in that
file, fix the stated prerequisite, then rerun the same reproduction command.

Common examples:

| Symptom | Meaning and safe response |
|---|---|
| `blocked_missing_raw_inputs` | Run `--mode preflight`, acquire or manually place the listed official raw files, then rerun. |
| Missing canonical mainland grid | Start the normal full reproduction command; the reference stage creates the CAOP reference layers and canonical grid before the national panel. |
| Missing CLC Portugal GeoPackage | Keep the raw CLC ZIP in place and rerun reproduction; the CLC preparation stage creates the derivative before feature derivation. |
| A complete output already exists | The relevant stage validates/reuses it. Do not delete it merely to retry a later stage. |

## QGIS checks and optional layout exports

The QGIS projects use relative data paths. Open them only after a successful
reproduction has created their derived GeoPackage inputs.

On Windows with QGIS installed, validate the existing projects with:

```text
scripts\run_qgis_presentation_project.bat --validate-existing
scripts\run_qgis_presentation_project.bat --validate-operational
```

The static PNG/PDF layout exports in `reports/figures/` are optional
presentation copies. Their absence does not prevent either `.qgz` project from
opening, displaying its layers, or displaying its embedded layouts.

`QFontDatabase` messages about a QGIS font directory are normally Qt/QGIS
installation warnings. If the validation command ends successfully, they are
not a project-data failure. If QGIS reports an unavailable layer, rerun
reproduction first and then reopen the `.qgz` project from the current cloned
repository folder. Old QGIS Browser favourites or stale connections from a
different local clone can be removed in QGIS; they are not project layers.

## Return to a clean derived-output state

Use cleanup only when you deliberately want to rebuild local derived outputs.
Review the exact targets first:

```text
python scripts/clean_project_outputs.py --dry-run
```

Then, if the targets are correct:

```text
python scripts/clean_project_outputs.py --confirm-delete-derived
```

This preserves `data/raw/`, credentials, source code, notebooks, QGIS projects,
and tracked validation documentation. It removes only reproducible derived
data, generated figures/tables, and local run logs. Rebuild afterwards with the
normal reproduction command.

## When reporting an issue

Provide the command you ran, the stage name, and the relevant file from
`reports/run_logs/`. Do not share CDS tokens, credentials, or provider download
links containing private account information.
