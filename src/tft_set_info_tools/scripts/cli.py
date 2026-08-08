"""Unified CLI entry point: `tft-scripts <command> ...`."""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path

from tft_set_info_tools.scripts import generate_seed, update_src


def load_env_file(path: str) -> None:
    """Load `KEY=VALUE` pairs from an env file into `os.environ`.

    Variables already present in the environment are left untouched, matching
    the usual precedence of shell/CI env vars over a checked-in env file.
    """
    env_path = Path(path)
    if not env_path.is_file():
        raise FileNotFoundError(f"env file not found: {path}")

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            continue
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tft-scripts",
        description="Command-line scripts for interacting with TFT set metadata.",
    )
    parser.add_argument(
        "--env-file",
        dest="env_file",
        help="Path to a .env file to load environment variables from before running the command.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    update_src.add_arguments(
        subparsers.add_parser(
            "update-src",
            help="Copy TFT set metadata json from one data source to another.",
        )
    )
    generate_seed.add_arguments(
        subparsers.add_parser(
            "generate-seed",
            help="Export TFT set metadata to csv seed file(s).",
        )
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(args)
    try:
        if args.env_file:
            load_env_file(args.env_file)
        if args.command == "update-src":
            update_src.run(args.src, args.dst, args.src_patch)
        elif args.command == "generate-seed":
            generate_seed.run(args.src, args.dst_path, args.set_num, args.type)
    except Exception as exc:
        print(traceback.format_exc(), file=sys.stderr)
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
