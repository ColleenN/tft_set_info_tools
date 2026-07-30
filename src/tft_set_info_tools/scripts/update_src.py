"""CLI subcommand: copy TFT set metadata json from one data source to another."""

from __future__ import annotations

import argparse

from tft_set_info_tools.scripts._sources import build_source


def run(src: str, dst: str, src_patch: str | None = None) -> None:
    with build_source(src, patch=src_patch) as source, build_source(dst) as destination:
        destination.write(source)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "src", help="Data source to read from: local, gcp, cdragon, or default"
    )
    parser.add_argument(
        "dst",
        help="Data source to write to: local or gcp (must support write())",
    )
    parser.add_argument(
        "--src-patch",
        dest="src_patch",
        default=None,
        help=(
            "Community Dragon patch/version to fetch, e.g. '13.24' (only valid "
            "when src is 'cdragon'). Defaults to 'latest'."
        ),
    )
