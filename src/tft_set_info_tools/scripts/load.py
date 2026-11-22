"""`load <source>`: append one source's mirrored copies to BigQuery."""

from __future__ import annotations

import argparse
import logging

from tft_set_info_tools.scripts import load_cdragon

logger = logging.getLogger(__name__)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    # Not required yet: the deployed job still runs a bare `load`, which loads
    # CDragon until its infra switches to `load cdragon`.
    sources = parser.add_subparsers(dest="source")
    load_cdragon.add_arguments(
        sources.add_parser("cdragon", help="Append mirrored CDragon snapshots to the reference tables.")
    )


def run(args: argparse.Namespace) -> None:
    if args.source is None:
        logger.warning("`load` with no source is deprecated; use `load cdragon`")
        load_cdragon.run()
    elif args.source == "cdragon":
        load_cdragon.run(args.bucket, args.dataset, args.min_set, args.channels)
