"""One loader run: append every not-yet-loaded capture on each channel.

A capture CDragon hadn't finished publishing when it was saved (its status
line isn't "done") is recorded as skipped and never loaded: its
cdragon-version may already be the next build's. Captures saved before the
mirror recorded a status are loaded, with a NULL cdragon_status.

A capture that fails to load is logged and left unrecorded, so the next run
tries it again; the run carries on with the other captures and reports the
failures at the end.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from tft_set_info_tools.datasource import CDragonPairedSnapshotDataSource
from tft_set_info_tools.loader.bigquery import LOADED, SKIPPED, ReferenceWriter
from tft_set_info_tools.loader.cdragon import CapturePair, list_capture_pairs
from tft_set_info_tools.loader.sets import sets_to_load
from tft_set_info_tools.scripts.reference_tables import REFERENCE_TABLES
from tft_set_info_tools.set_data import TFTSetData

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    loaded: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


def _reference_rows(source, pair: CapturePair, set_numbers: list[int]) -> dict[str, list[dict]]:
    capture = pair.data
    rows: dict[str, list[dict]] = {name: [] for name in REFERENCE_TABLES}
    for set_number in set_numbers:
        set_data = TFTSetData(source, set_number)
        version = {
            "channel": capture.channel,
            "build": capture.build,
            "cdragon_version": capture.cdragon_version,
            "cdragon_status": capture.cdragon_status,
            "captured_at": capture.captured_at,
            "source_object": capture.object_name,
            "set_number": set_number,
            "mutator": set_data.mutator,
        }
        for name, table in REFERENCE_TABLES.items():
            rows[name].extend({**version, **row} for row in table.generate(set_data))
    return rows


def load_capture(writer: ReferenceWriter, storage_client, pair: CapturePair, min_set: int) -> str:
    """Load one capture and record it; returns the outcome."""
    capture = pair.data
    team_planner_object = pair.team_planner.object_name if pair.team_planner else None
    record = dict(
        source_object=capture.object_name,
        team_planner_object=team_planner_object,
        channel=capture.channel,
        captured_at=capture.captured_at,
        cdragon_version=capture.cdragon_version,
    )

    if capture.cdragon_status_done is False:
        writer.record(**record, outcome=SKIPPED, detail=f"CDragon status: {capture.cdragon_status}")
        return SKIPPED

    source = CDragonPairedSnapshotDataSource(
        capture.bucket, capture.object_name, team_planner_object, client=storage_client
    )
    with source:
        set_numbers = sets_to_load(source.read(), min_set)
    rows = _reference_rows(source, pair, set_numbers)
    for name, table_rows in rows.items():
        writer.append(name, table_rows)
    writer.record(**record, outcome=LOADED, detail=f"sets: {', '.join(map(str, set_numbers)) or 'none'}")
    return LOADED


def load_snapshots(
    storage_client,
    bigquery_client,
    bucket: str,
    dataset: str,
    min_set: int,
    channels: tuple[str, ...],
) -> RunResult:
    writer = ReferenceWriter(bigquery_client, dataset)
    writer.ensure_tables()
    if partial := writer.remove_partial_loads():
        logger.warning("removed rows from %d partly loaded capture(s): %s", len(partial), ", ".join(sorted(partial)))
    recorded = writer.recorded_objects()

    result = RunResult()
    for channel in channels:
        for pair in list_capture_pairs(storage_client, bucket, channel):
            name = pair.data.object_name
            if name in recorded:
                continue
            try:
                outcome = load_capture(writer, storage_client, pair, min_set)
            except Exception:
                logger.exception("failed to load %s", name)
                result.failed.append(name)
                continue
            (result.loaded if outcome == LOADED else result.skipped).append(name)
            logger.info("%s: %s", outcome, name)

    logger.info(
        "loaded %d, skipped %d, failed %d capture(s)",
        len(result.loaded),
        len(result.skipped),
        len(result.failed),
    )
    return result
