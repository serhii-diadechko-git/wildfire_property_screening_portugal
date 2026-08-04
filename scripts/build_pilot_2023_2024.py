import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.pilot_2023_2024 import run_enrichment, smoke_test, validate_existing_enriched_outputs
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Bounded-memory enrichment of the existing 2023 -> 2024 pilot")
    parser.add_argument("--tile-size", type=int, default=256, help="Existing grid features per bounded CLC batch")
    parser.add_argument("--smoke-test", action="store_true", help="Validate one tile only; do not write outputs")
    parser.add_argument("--validate-existing", action="store_true", help="Validate existing derived outputs in batches and refresh map/report")
    arguments = parser.parse_args()
    if arguments.tile_size < 1:
        parser.error("--tile-size must be positive")
    if arguments.smoke_test:
        print(smoke_test(arguments.tile_size))
    elif arguments.validate_existing:
        print(json.dumps(validate_existing_enriched_outputs(), indent=2))
    else:
        validation, _ = run_enrichment(arguments.tile_size)
        print(json.dumps(validation, indent=2))
