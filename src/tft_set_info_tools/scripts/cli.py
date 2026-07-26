"""Unified CLI entry point: `tft-scripts <command> ...`."""

from __future__ import annotations

import argparse
import sys

from tft_set_info_tools.scripts import generate_seed, update_src


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tft-scripts",
        description="Command-line scripts for interacting with TFT set metadata.",
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

    try:
        if args.command == "update-src":
            update_src.run(args.src, args.dst)
        elif args.command == "generate-seed":
            generate_seed.run(args.src, args.dst_path, args.set_num, args.type)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
