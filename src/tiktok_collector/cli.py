from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from .collector import collect_all
from .config import load_config
from .storage import save_to_csv, save_to_sqlite



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect publicly available TikTok metadata into CSV and SQLite."
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to YAML config file (default: config.yaml)",
    )
    return parser



def main() -> None:
    args = build_parser().parse_args()
    load_dotenv()

    config = load_config(args.config)
    records = collect_all(config)

    save_to_csv(records, config.output.csv_path)
    save_to_sqlite(records, config.output.sqlite_path)

    print(f"Collected {len(records)} records")
    print(f"CSV: {Path(config.output.csv_path).resolve()}")
    print(f"SQLite: {Path(config.output.sqlite_path).resolve()}")


if __name__ == "__main__":
    main()
