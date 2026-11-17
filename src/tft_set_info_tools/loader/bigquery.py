"""Writing reference rows to BigQuery.

Each reference table gets its generator's columns plus VERSION_COLUMNS, so
every row says which capture, channel, build and set it came from. Tables are
only appended to: a new capture adds a full copy of its sets' rows.

A capture counts as loaded once it has a row in loaded_captures, which is
written after all of its reference rows. A run that dies partway through a
capture leaves rows with no loaded_captures entry; remove_partial_loads()
deletes those before the capture is loaded again.

Tables are created if missing but never altered, so adding a column to a
generator needs a schema change on the existing table first.
"""

from __future__ import annotations

from datetime import datetime, timezone

from tft_set_info_tools.scripts.reference_tables import REFERENCE_TABLES

VERSION_COLUMNS = {
    "channel": "STRING",
    "build": "STRING",
    "cdragon_version": "STRING",
    "cdragon_status": "STRING",
    "captured_at": "TIMESTAMP",
    "source_object": "STRING",
    "set_number": "INT64",
    "mutator": "STRING",
}

LOADED_CAPTURES_TABLE = "loaded_captures"
LOADED_CAPTURES_COLUMNS = {
    "source_object": "STRING",
    "team_planner_object": "STRING",
    "channel": "STRING",
    "captured_at": "TIMESTAMP",
    "cdragon_version": "STRING",
    "outcome": "STRING",
    "detail": "STRING",
    "loaded_at": "TIMESTAMP",
}

LOADED = "loaded"
SKIPPED = "skipped"


def table_columns(name: str) -> dict[str, str]:
    if name == LOADED_CAPTURES_TABLE:
        return LOADED_CAPTURES_COLUMNS
    return {**VERSION_COLUMNS, **REFERENCE_TABLES[name].columns}


def _schema(columns: dict[str, str]):
    from google.cloud import bigquery

    return [bigquery.SchemaField(name, type_) for name, type_ in columns.items()]


def _json_value(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return value


class ReferenceWriter:
    """Writes to the reference tables in one dataset, given as [project.]dataset."""

    def __init__(self, client, dataset: str):
        self._client = client
        self.dataset = dataset if "." in dataset else f"{client.project}.{dataset}"

    def table_id(self, name: str) -> str:
        return f"{self.dataset}.{name}"

    def ensure_tables(self) -> None:
        from google.cloud import bigquery

        for name in [*REFERENCE_TABLES, LOADED_CAPTURES_TABLE]:
            table = bigquery.Table(self.table_id(name), schema=_schema(table_columns(name)))
            self._client.create_table(table, exists_ok=True)

    def _query(self, sql: str) -> list:
        return list(self._client.query(sql).result())

    def recorded_objects(self) -> set[str]:
        """Source objects already loaded or skipped."""
        rows = self._query(
            f"SELECT DISTINCT source_object FROM `{self.table_id(LOADED_CAPTURES_TABLE)}`"
        )
        return {row["source_object"] for row in rows}

    def remove_partial_loads(self) -> set[str]:
        """Delete rows from captures that never reached loaded_captures; returns their objects."""
        recorded = f"SELECT source_object FROM `{self.table_id(LOADED_CAPTURES_TABLE)}`"
        union = " UNION ALL ".join(
            f"SELECT DISTINCT source_object FROM `{self.table_id(name)}`" for name in REFERENCE_TABLES
        )
        rows = self._query(
            f"SELECT DISTINCT source_object FROM ({union}) WHERE source_object NOT IN ({recorded})"
        )
        partial = {row["source_object"] for row in rows}
        if partial:
            for name in REFERENCE_TABLES:
                self._query(
                    f"DELETE FROM `{self.table_id(name)}` WHERE source_object NOT IN ({recorded})"
                )
        return partial

    def append(self, name: str, rows: list[dict]) -> None:
        if not rows:
            return
        from google.cloud import bigquery

        job_config = bigquery.LoadJobConfig(
            schema=_schema(table_columns(name)),
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        )
        rows = [{key: _json_value(value) for key, value in row.items()} for row in rows]
        self._client.load_table_from_json(rows, self.table_id(name), job_config=job_config).result()

    def record(
        self,
        source_object: str,
        team_planner_object: str | None,
        channel: str,
        captured_at: datetime,
        cdragon_version: str | None,
        outcome: str,
        detail: str | None = None,
    ) -> None:
        self.append(
            LOADED_CAPTURES_TABLE,
            [
                {
                    "source_object": source_object,
                    "team_planner_object": team_planner_object,
                    "channel": channel,
                    "captured_at": captured_at,
                    "cdragon_version": cdragon_version,
                    "outcome": outcome,
                    "detail": detail,
                    "loaded_at": datetime.now(timezone.utc),
                }
            ],
        )
