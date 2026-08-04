import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.pilot_2023_2024 import run_enrichment
if __name__ == '__main__':
    f,missing=run_enrichment(); print(len(f),missing)
