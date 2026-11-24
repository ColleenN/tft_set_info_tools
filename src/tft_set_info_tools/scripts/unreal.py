"""`unreal <command>`: list and extract files from the standalone TFT client's Unreal containers."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

AES_KEY_ENV_VAR = "TFT_UE_AES_KEY"


def add_arguments(parser: argparse.ArgumentParser) -> None:
    commands = parser.add_subparsers(dest="unreal_command", required=True)

    container_args = argparse.ArgumentParser(add_help=False)
    container_args.add_argument(
        "-k", "--aes-key",
        help=f"AES-256 key in hex, for encrypted containers. Default: ${AES_KEY_ENV_VAR}.",
    )
    container_args.add_argument(
        "-p", "--pattern", action="append",
        help="Only files whose path matches this shell-style pattern. Repeatable.",
    )
    container_args.add_argument("container", help=".pak file, or the .utoc or .ucas file of an IoStore container.")

    commands.add_parser("list", parents=[container_args], help="List a container's files and their sizes.")

    extract = commands.add_parser("extract", parents=[container_args], help="Extract a container's files.")
    extract.add_argument("-o", "--output", help="Directory to extract into. Default: the container's path without its extension.")
    extract.add_argument("--lazy", action="store_true", help="Skip files that already exist.")

    locres = commands.add_parser("locres-dump", help="Merge .locres string tables and write them as JSON.")
    locres.add_argument("-o", "--output", help="JSON file to write. Default: stdout.")
    locres.add_argument("locres", nargs="+", help=".locres files, merged in order; later files win.")


def open_from_args(args: argparse.Namespace):
    from tft_set_info_tools.unreal import open_container
    from tft_set_info_tools.unreal.codecs import parse_aes_key

    if not os.path.isfile(args.container):
        raise FileNotFoundError(f"container file not found: {args.container}")
    key = args.aes_key or os.environ.get(AES_KEY_ENV_VAR)
    return open_container(args.container, aes_key=parse_aes_key(key) if key else None)


def select_entries(container, patterns: list[str] | None) -> list:
    return container.find(*patterns) if patterns else list(container.entries)


def list_files(args: argparse.Namespace) -> None:
    container = open_from_args(args)
    for entry in sorted(select_entries(container, args.pattern), key=lambda e: e.path):
        print(f"{entry.length:>10} {entry.path}")


def extract_files(args: argparse.Namespace) -> None:
    container = open_from_args(args)
    output = Path(args.output or os.path.splitext(args.container)[0])
    if output.exists() and not output.is_dir():
        raise NotADirectoryError(f"output is not a directory: {output}")
    container.extract(output, select_entries(container, args.pattern), overwrite=not args.lazy)


def dump_locres(args: argparse.Namespace) -> None:
    from tft_set_info_tools.unreal.locres import LocresFile

    table = LocresFile()
    for path in args.locres:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"locres file not found: {path}")
        table.update(LocresFile(path))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(table.entries, f, ensure_ascii=False, indent=1)
    else:
        json.dump(table.entries, sys.stdout, ensure_ascii=False, indent=1)
        print()


def run(args: argparse.Namespace) -> None:
    if args.unreal_command == "list":
        list_files(args)
    elif args.unreal_command == "extract":
        extract_files(args)
    elif args.unreal_command == "locres-dump":
        dump_locres(args)
