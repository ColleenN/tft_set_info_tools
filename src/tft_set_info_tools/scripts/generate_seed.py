"""CLI subcommand: export TFT set metadata to csv seed file(s)."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from tft_set_info_tools.scripts._sources import build_source
from tft_set_info_tools.scripts.seeds import SEED_GENERATORS
from tft_set_info_tools.set_data import TFTSetData

ALLOWED_TYPES = ("all",) + tuple(SEED_GENERATORS)


def _parse_types(raw: str) -> list[str]:
    requested = [t.strip().lower() for t in raw.split(",") if t.strip()]
    unknown = [t for t in requested if t not in ALLOWED_TYPES]
    if unknown:
        raise ValueError(
            f"Unknown seed type(s): {', '.join(unknown)}; "
            f"expected one of: {', '.join(ALLOWED_TYPES)}"
        )
    if "all" in requested:
        return list(SEED_GENERATORS)
    return requested


def _write_seed_csv(out_dir: Path, seed_type: str, rows: list[dict]) -> None:
    if not rows:
        print(
            f"warning: no {seed_type!r} rows generated; skipping seed_{seed_type}.csv",
            file=sys.stderr,
        )
        return
    out_file = out_dir / f"seed_{seed_type}.csv"
    # Rows aren't guaranteed to share the same keys (e.g. units carry
    # whatever stat columns that particular champion's raw data has), so
    # fieldnames must be the union across every row, not just the first.
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with out_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, restval="")
        writer.writeheader()
        writer.writerows(rows)


def run(src: str | None, dst_path: str, set_num: int | None, types: str) -> None:
    seed_types = _parse_types(types)
    out_dir = Path(dst_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    set_data = TFTSetData(build_source(src), set_num=set_num)

    for seed_type in seed_types:
        rows = SEED_GENERATORS[seed_type](set_data)
        _write_seed_csv(out_dir, seed_type, rows)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--src",
        default=None,
        help="Data source to read from: local, gcp, cdragon, metatft, or default. Defaults to default.",
    )
    parser.add_argument(
        "--dst-path",
        default=".",
        help="Directory to write seed csv files to. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--set",
        dest="set_num",
        type=int,
        default=None,
        help="Set number to generate seed files for. Defaults to the latest set in the data source.",
    )
    parser.add_argument(
        "--type",
        default="all",
        help=(
            "Comma-separated list of seed types to generate. "
            f"Allowed values: {', '.join(ALLOWED_TYPES)}. Defaults to all."
        ),
    )
