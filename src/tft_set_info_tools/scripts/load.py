"""`load <source>`: append one source's mirrored copies to BigQuery."""

from __future__ import annotations

import argparse

from tft_set_info_tools.scripts import load_cdragon, load_patchsieve


def add_arguments(parser: argparse.ArgumentParser) -> None:
    sources = parser.add_subparsers(dest="source", required=True)
    load_cdragon.add_arguments(
        sources.add_parser("cdragon", help="Append mirrored CDragon snapshots to the reference tables.")
    )
    load_patchsieve.add_arguments(
        sources.add_parser("patchsieve", help="Append mirrored Patchsieve copies to client_deploys.")
    )


def run(args: argparse.Namespace) -> None:
    if args.source == "cdragon":
        load_cdragon.run(args.bucket, args.dataset, args.min_set, args.channels)
    elif args.source == "patchsieve":
        load_patchsieve.run(args.bucket, args.dataset, args.path)
