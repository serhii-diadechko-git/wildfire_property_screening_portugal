"""Public one-command project entrypoint.

Examples
--------
python scripts/run_project.py --mode preflight
python scripts/run_project.py --mode acquire-api
python scripts/run_project.py --mode validate
python scripts/run_project.py --mode reproduce --confirm-rebuild
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _project_venv_python() -> Path:
    """Return the platform-specific interpreter inside the repository `.venv`."""
    executable = "python.exe" if os.name == "nt" else "python"
    directory = "Scripts" if os.name == "nt" else "bin"
    return ROOT / ".venv" / directory / executable


def _use_project_venv_if_available() -> None:
    """Re-execute the public launcher in the pinned local virtual environment.

    This check happens before importing project code, so `python
    scripts/run_project.py ...` is reliable even when an editor or terminal has
    selected a global Python installation.  If `.venv` does not exist, normal
    Python import errors still make the missing environment visible to the user.
    """
    venv_python = _project_venv_python()
    if not venv_python.is_file():
        return
    try:
        already_using_venv = Path(sys.executable).resolve() == venv_python.resolve()
    except OSError:
        already_using_venv = False
    if already_using_venv:
        return
    print(f"Using project virtual environment: {venv_python.relative_to(ROOT).as_posix()}", flush=True)
    os.execv(str(venv_python), [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]])


_use_project_venv_if_available()

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.project_run import raw_data_preflight, run_api_acquisition, run_reproduction, validation_command, write_run_summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("preflight", "acquire-api", "validate", "reproduce"),
        default="preflight",
        help="preflight checks inputs only; acquire-api downloads approved API sources; validate runs tests; reproduce rebuilds outputs.",
    )
    parser.add_argument(
        "--confirm-rebuild",
        action="store_true",
        help="Required for --mode reproduce because it can regenerate derived data and reports.",
    )
    parser.add_argument(
        "--with-qgis",
        action="store_true",
        help="Include QGIS project regeneration; requires PyQGIS in the invoking Python environment.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    preflight = raw_data_preflight()
    print(json.dumps(preflight, indent=2))
    if args.mode == "preflight":
        report = write_run_summary(mode="preflight", preflight=preflight)
        print(f"\nWrote user-friendly summary: {report.relative_to(ROOT).as_posix()}")
        if preflight["status"] != "ready":
            raise SystemExit("Preflight blocked: place official raw data as described in data/README.md.")
        print("Preflight passed. Run --mode validate for checks or --mode reproduce --confirm-rebuild to regenerate outputs.")
        return
    if args.mode == "acquire-api":
        report, completed = run_api_acquisition()
        print(json.dumps({"report": report.relative_to(ROOT).as_posix(), "completed_stages": completed}, indent=2))
        return
    if args.mode == "validate":
        if preflight["status"] != "ready":
            report = write_run_summary(mode="validate_blocked", preflight=preflight)
            raise SystemExit(f"Validation blocked by missing raw inputs. See {report.relative_to(ROOT).as_posix()}.")
        import subprocess

        test_args, scope = validation_command()
        command = (sys.executable, *test_args)
        print(f"Running {scope}.")
        result = subprocess.run(command, cwd=ROOT, check=False)
        report = write_run_summary(mode="validate", preflight=preflight)
        print(f"\nWrote user-friendly summary: {report.relative_to(ROOT).as_posix()}")
        raise SystemExit(result.returncode)
    if not args.confirm_rebuild:
        raise SystemExit("Refusing to regenerate derived outputs without --confirm-rebuild.")
    report, completed = run_reproduction(include_qgis=args.with_qgis)
    print(json.dumps({"report": report.relative_to(ROOT).as_posix(), "completed_stages": completed}, indent=2))


if __name__ == "__main__":
    main()
