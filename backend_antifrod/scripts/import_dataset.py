"""Импорт CSV/CDR и полный ML-конвейер: python -m scripts.import_dataset /data/marked.csv"""
import argparse
import logging
from pathlib import Path

from core.database import SessionLocal
from etl.load_cdr import load_file
from etl.pipeline import run_pipeline


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    args = parser.parse_args()
    with SessionLocal() as db:
        result = load_file(db, Path(args.path))
        db.commit()
        print(result.as_dict(), flush=True)
    print(run_pipeline(load=False), flush=True)


if __name__ == "__main__":
    main()
