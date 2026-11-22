"""One Patchsieve loader run: append a client_deploys row for every copy not loaded yet.

A copy that can't be read or parsed is logged and left out, so the next run
tries it again; the rest of the run's copies still load.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from tft_set_info_tools.loaders.patchsieve.bigquery import DeployWriter
from tft_set_info_tools.loaders.patchsieve.captures import deploy_row, list_patchsieve_captures

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    loaded: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


def load_client_deploys(storage_client, bigquery_client, bucket: str, dataset: str, path: str) -> RunResult:
    writer = DeployWriter(bigquery_client, dataset)
    writer.ensure_table()
    loaded = writer.loaded_objects()

    result = RunResult()
    rows = []
    for capture in list_patchsieve_captures(storage_client, bucket, path):
        if capture.object_name in loaded:
            continue
        try:
            blob = storage_client.bucket(bucket).get_blob(capture.object_name)
            rows.append(deploy_row(capture, blob.download_as_bytes()))
        except Exception:
            logger.exception("failed to load %s", capture.object_name)
            result.failed.append(capture.object_name)
            continue
        result.loaded.append(capture.object_name)

    writer.append(rows)
    logger.info("loaded %d, failed %d Patchsieve copies", len(result.loaded), len(result.failed))
    return result
