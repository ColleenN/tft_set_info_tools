import json
from datetime import datetime, timedelta, timezone

import pytest

bigquery = pytest.importorskip("google.cloud.bigquery")

from tft_set_info_tools.loaders.cdragon.bigquery import (  # noqa: E402
    LOADED,
    LOADED_CAPTURES_TABLE,
    VERSION_COLUMNS,
    ReferenceWriter,
    table_columns,
)
from tft_set_info_tools.scripts.reference_tables import REFERENCE_TABLES  # noqa: E402


class FakeJob:
    def __init__(self, rows=()):
        self.rows = list(rows)

    def result(self):
        return self.rows


class FakeClient:
    project = "proj"

    def __init__(self, query_results=None):
        self.created = []
        self.queries = []
        self.loads = []
        self.query_results = query_results or {}

    def create_table(self, table, exists_ok=False):
        assert exists_ok
        self.created.append(table)

    def query(self, sql):
        self.queries.append(sql)
        for fragment, rows in self.query_results.items():
            if fragment in sql:
                return FakeJob(rows)
        return FakeJob()

    def load_table_from_json(self, rows, destination, job_config):
        json.dumps(rows)
        self.loads.append((destination, rows, job_config))
        return FakeJob()


def test_dataset_without_a_project_uses_the_clients():
    assert ReferenceWriter(FakeClient(), "tft_reference").table_id("units") == "proj.tft_reference.units"
    assert ReferenceWriter(FakeClient(), "other.ref").table_id("units") == "other.ref.units"


def test_reference_tables_lead_with_the_version_columns():
    columns = list(table_columns("units"))
    assert columns[: len(VERSION_COLUMNS)] == list(VERSION_COLUMNS)
    assert columns[len(VERSION_COLUMNS) :] == list(REFERENCE_TABLES["units"].columns)


def test_ensure_tables_creates_every_table_with_its_schema():
    client = FakeClient()
    ReferenceWriter(client, "ref").ensure_tables()

    by_id = {table.table_id: table for table in client.created}
    assert set(by_id) == {*REFERENCE_TABLES, LOADED_CAPTURES_TABLE}
    units = {field.name: field.field_type for field in by_id["units"].schema}
    assert units["stats"] == "JSON"
    assert units["captured_at"] == "TIMESTAMP"


def test_recorded_objects():
    client = FakeClient({"FROM `proj.ref.loaded_captures`": [{"source_object": "a"}, {"source_object": "b"}]})
    assert ReferenceWriter(client, "ref").recorded_objects() == {"a", "b"}


def test_remove_partial_loads_deletes_only_when_some_exist():
    client = FakeClient()
    assert ReferenceWriter(client, "ref").remove_partial_loads() == set()
    assert len(client.queries) == 1

    client = FakeClient({"UNION ALL": [{"source_object": "half-loaded"}]})
    assert ReferenceWriter(client, "ref").remove_partial_loads() == {"half-loaded"}
    deletes = [q for q in client.queries if q.startswith("DELETE")]
    assert len(deletes) == len(REFERENCE_TABLES)
    assert all("NOT IN (SELECT source_object FROM `proj.ref.loaded_captures`)" in q for q in deletes)


def test_append_loads_json_rows():
    client = FakeClient()
    when = datetime(2026, 11, 16, 17, tzinfo=timezone(timedelta(hours=-7)))
    ReferenceWriter(client, "ref").append("units", [{"captured_at": when, "stats": {"hp": 550.0}}])

    [(destination, rows, job_config)] = client.loads
    assert destination == "proj.ref.units"
    assert rows == [{"captured_at": "2026-11-17T00:00:00+00:00", "stats": {"hp": 550.0}}]
    assert job_config.write_disposition == bigquery.WriteDisposition.WRITE_APPEND
    assert [f.name for f in job_config.schema] == list(table_columns("units"))


def test_append_with_no_rows_does_nothing():
    client = FakeClient()
    ReferenceWriter(client, "ref").append("units", [])
    assert client.loads == []


def test_record_writes_one_loaded_captures_row():
    client = FakeClient()
    when = datetime(2026, 11, 16, tzinfo=timezone.utc)
    ReferenceWriter(client, "ref").record("obj", None, "pbe", when, "16.22.8312345", LOADED)

    [(destination, [row], _)] = client.loads
    assert destination == "proj.ref.loaded_captures"
    assert row["outcome"] == "loaded"
    assert row["team_planner_object"] is None
    assert set(row) == set(table_columns(LOADED_CAPTURES_TABLE))
