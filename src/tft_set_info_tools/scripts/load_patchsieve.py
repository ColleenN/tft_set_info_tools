"""`load patchsieve`: append mirrored Patchsieve copies to client_deploys.

Options fall back to the same environment variables as `load cdragon`, so the
job keeps its settings in an env file passed with --env-file.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

from tft_set_info_tools.scripts.load_cdragon import BUCKET_ENV_VAR, DATASET_ENV_VAR, PROJECT_ENV_VAR

PATH_ENV_VAR = "TFT_LOADER_PATCHSIEVE_PATH"
DEFAULT_PATH = "patchsieve"


@dataclass(frozen=True)
class PatchsieveLoadConfig:
    bucket: str
    dataset: str
    path: str = DEFAULT_PATH


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--bucket", help=f"Bucket holding the Patchsieve copies. Default: ${BUCKET_ENV_VAR}.")
    parser.add_argument(
        "--dataset",
        help=f"BigQuery dataset for client_deploys, as [project.]dataset. Default: ${DATASET_ENV_VAR}.",
    )
    parser.add_argument(
        "--path",
        help=f"Bucket path of the copies. Default: ${PATH_ENV_VAR}, else {DEFAULT_PATH}.",
    )


def resolve_config(bucket: str | None = None, dataset: str | None = None, path: str | None = None) -> PatchsieveLoadConfig:
    bucket = bucket or os.environ.get(BUCKET_ENV_VAR)
    dataset = dataset or os.environ.get(DATASET_ENV_VAR)
    path = path or os.environ.get(PATH_ENV_VAR) or DEFAULT_PATH
    missing = [
        f"--{name} or ${env_var}"
        for name, value, env_var in [("bucket", bucket, BUCKET_ENV_VAR), ("dataset", dataset, DATASET_ENV_VAR)]
        if not value
    ]
    if missing:
        raise ValueError(f"missing {', '.join(missing)}")
    return PatchsieveLoadConfig(bucket, dataset, path)


def load(config: PatchsieveLoadConfig) -> None:
    from google.cloud import bigquery, storage

    from tft_set_info_tools.loaders.patchsieve.run import load_client_deploys

    project = os.environ.get(PROJECT_ENV_VAR)
    with storage.Client(project=project) as storage_client, bigquery.Client(project=project) as bigquery_client:
        result = load_client_deploys(storage_client, bigquery_client, config.bucket, config.dataset, config.path)
    if result.failed:
        raise RuntimeError(f"{len(result.failed)} copies failed to load: {', '.join(result.failed)}")


def run(bucket: str | None = None, dataset: str | None = None, path: str | None = None) -> None:
    load(resolve_config(bucket, dataset, path))
