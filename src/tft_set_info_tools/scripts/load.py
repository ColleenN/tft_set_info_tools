"""`load`: append mirrored CDragon snapshots to the BigQuery reference tables.

Each option falls back to an environment variable, so the scheduled job can
keep its settings in an env file passed with the global --env-file option
(which is loaded after the arguments are parsed).
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

BUCKET_ENV_VAR = "TFT_LOADER_BUCKET"
DATASET_ENV_VAR = "TFT_LOADER_DATASET"
MIN_SET_ENV_VAR = "TFT_LOADER_MIN_SET"
CHANNELS_ENV_VAR = "TFT_LOADER_CHANNELS"
DEFAULT_CHANNELS = ("live", "pbe")


@dataclass(frozen=True)
class LoadConfig:
    bucket: str
    dataset: str
    min_set: int
    channels: tuple[str, ...]


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--bucket", help=f"Bucket holding the snapshots. Default: ${BUCKET_ENV_VAR}.")
    parser.add_argument(
        "--dataset",
        help=f"BigQuery dataset for the reference tables, as [project.]dataset. Default: ${DATASET_ENV_VAR}.",
    )
    parser.add_argument(
        "--min-set",
        dest="min_set",
        type=int,
        help=f"Lowest set number to load. Default: ${MIN_SET_ENV_VAR}.",
    )
    parser.add_argument(
        "--channels",
        help=f"Comma-separated channels to load. Default: ${CHANNELS_ENV_VAR}, else {','.join(DEFAULT_CHANNELS)}.",
    )


def resolve_config(
    bucket: str | None = None,
    dataset: str | None = None,
    min_set: int | None = None,
    channels: str | None = None,
) -> LoadConfig:
    bucket = bucket or os.environ.get(BUCKET_ENV_VAR)
    dataset = dataset or os.environ.get(DATASET_ENV_VAR)
    if min_set is None and os.environ.get(MIN_SET_ENV_VAR):
        min_set = int(os.environ[MIN_SET_ENV_VAR])
    channels = channels or os.environ.get(CHANNELS_ENV_VAR)

    missing = [
        f"--{name} or ${env_var}"
        for name, value, env_var in [
            ("bucket", bucket, BUCKET_ENV_VAR),
            ("dataset", dataset, DATASET_ENV_VAR),
            ("min-set", min_set, MIN_SET_ENV_VAR),
        ]
        if value is None or value == ""
    ]
    if missing:
        raise ValueError(f"missing {', '.join(missing)}")

    channel_list = tuple(c.strip() for c in channels.split(",") if c.strip()) if channels else DEFAULT_CHANNELS
    if not channel_list:
        raise ValueError("no channels given")
    return LoadConfig(bucket, dataset, min_set, channel_list)


def load(config: LoadConfig) -> None:
    raise NotImplementedError("loading snapshots into BigQuery isn't implemented yet (S5)")


def run(
    bucket: str | None = None,
    dataset: str | None = None,
    min_set: int | None = None,
    channels: str | None = None,
) -> None:
    load(resolve_config(bucket, dataset, min_set, channels))
