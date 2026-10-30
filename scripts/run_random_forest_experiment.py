"""Run the full isolated Random Forest forecast experiment with a fresh name."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.random_forest_experiment import run

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", required=True)
    args = parser.parse_args()
    result = run(args.run_name)
    print(f"Complete: {result['run_name']}; protected files unchanged: {result['protected_files_unchanged']}")
