"""BigQuery plumbing shared by the loaders.

Tables are created if missing but never altered, so adding a column needs a
schema change on the existing table first.
"""

from __future__ import annotations

from datetime import datetime, timezone


def schema(columns: dict[str, str]):
    from google.cloud import bigquery

    return [bigquery.SchemaField(name, type_) for name, type_ in columns.items()]


def json_value(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return value


class TableWriter:
    """Creates and appends to tables in one dataset, given as [project.]dataset."""

    def __init__(self, client, dataset: str):
        self._client = client
        self.dataset = dataset if "." in dataset else f"{client.project}.{dataset}"

    def table_id(self, name: str) -> str:
        return f"{self.dataset}.{name}"

    def ensure_table(self, name: str, columns: dict[str, str]) -> None:
        from google.cloud import bigquery

        self._client.create_table(bigquery.Table(self.table_id(name), schema=schema(columns)), exists_ok=True)

    def query(self, sql: str) -> list:
        return list(self._client.query(sql).result())

    def load_rows(self, name: str, columns: dict[str, str], rows: list[dict]) -> None:
        if not rows:
            return
        from google.cloud import bigquery

        job_config = bigquery.LoadJobConfig(
            schema=schema(columns),
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        )
        rows = [{key: json_value(value) for key, value in row.items()} for row in rows]
        self._client.load_table_from_json(rows, self.table_id(name), job_config=job_config).result()
