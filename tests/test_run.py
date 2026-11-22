import gzip
import json

import pytest

pytest.importorskip("google.cloud.bigquery")

from tft_set_info_tools.loaders.cdragon.run import load_snapshots  # noqa: E402
from tests.test_bigquery import FakeClient as FakeBigQuery  # noqa: E402


def set_entry(number, mutator):
    return {
        "number": number,
        "mutator": mutator,
        "name": f"Set{number}",
        "items": ["TFT_Item_RecurveBow"],
        "augments": [],
        "champions": [
            {
                "name": "Zilean",
                "apiName": f"TFT{number}_Zilean",
                "cost": 2,
                "role": "support",
                "traits": ["Chrono"],
                "stats": {"hp": 550.0},
            }
        ],
        "traits": [
            {
                "name": "Chrono",
                "apiName": f"TFT{number}_Chrono",
                "desc": "Chrono desc",
                "effects": [{"minUnits": 2, "maxUnits": 4, "style": 3}],
            }
        ],
    }


PAYLOAD = {
    "items": [
        {
            "apiName": "TFT_Item_RecurveBow",
            "name": "Recurve Bow",
            "tags": ["component"],
            "effects": {},
            "incompatibleTraits": [],
            "unique": False,
            "composition": [],
        }
    ],
    "setData": [
        set_entry(15, "TFTSet15"),
        set_entry(16, "TFTSet16"),
        set_entry(16, "TFTSet16_PAIRS"),
    ],
}
VERSION = "16.21.8298620+branch.releases-16-21.content.release"


class FakeBlob:
    def __init__(self, name, payload, metadata):
        self.name = name
        self._content = gzip.compress(json.dumps(payload).encode())
        self.metadata = metadata

    def download_as_bytes(self):
        return self._content


class FakeStorage:
    def __init__(self, blobs):
        self.blobs = {blob.name: blob for blob in blobs}

    def list_blobs(self, bucket, prefix):
        return [blob for name, blob in self.blobs.items() if name.startswith(prefix)]

    def bucket(self, bucket_name):
        blobs = self.blobs

        class FakeBucket:
            def get_blob(self, name):
                return blobs.get(name)

        return FakeBucket()


def data_blob(stamp, channel="pbe", payload=PAYLOAD, **metadata):
    return FakeBlob(
        f"snapshots/cdragon/{channel}/{stamp}_en_us.json.gz",
        payload,
        {"channel": channel, "cdragon-version": VERSION, **{k.replace("_", "-"): v for k, v in metadata.items()}},
    )


def run(storage, bigquery=None, min_set=16, channels=("pbe",)):
    bigquery = bigquery or FakeBigQuery()
    return load_snapshots(storage, bigquery, "bucket", "ref", min_set, channels), bigquery


def loads_by_table(bigquery):
    tables = {}
    for destination, rows, _ in bigquery.loads:
        tables.setdefault(destination.rsplit(".", 1)[-1], []).extend(rows)
    return tables


def test_loads_a_capture_with_version_columns():
    storage = FakeStorage([data_blob("20261116T000000Z", cdragon_status="2026-11-16T00:00:00Z done")])

    result, bigquery = run(storage)

    assert result.loaded == ["snapshots/cdragon/pbe/20261116T000000Z_en_us.json.gz"]
    tables = loads_by_table(bigquery)
    [unit] = tables["units"]
    assert unit["set_number"] == 16
    assert unit["mutator"] == "TFTSet16"
    assert unit["build"] == "16.21.829.8620"
    assert unit["channel"] == "pbe"
    assert unit["cdragon_status"] == "2026-11-16T00:00:00Z done"
    assert unit["captured_at"] == "2026-11-16T00:00:00+00:00"
    assert unit["stats"] == {"hp": 550.0}
    [record] = tables["loaded_captures"]
    assert record["outcome"] == "loaded"
    assert record["detail"] == "sets: 16"


def test_loaded_captures_row_is_written_last():
    _, bigquery = run(FakeStorage([data_blob("20261116T000000Z")]))
    assert bigquery.loads[-1][0].endswith(".loaded_captures")


def test_capture_without_a_status_is_loaded():
    result, bigquery = run(FakeStorage([data_blob("20261116T000000Z")]))
    assert len(result.loaded) == 1
    assert loads_by_table(bigquery)["units"][0]["cdragon_status"] is None


def test_capture_cdragon_had_not_finished_is_skipped():
    storage = FakeStorage([data_blob("20261116T000000Z", cdragon_status="2026-11-16T00:00:00Z running")])

    result, bigquery = run(storage)

    assert len(result.skipped) == 1
    tables = loads_by_table(bigquery)
    assert set(tables) == {"loaded_captures"}
    assert tables["loaded_captures"][0]["outcome"] == "skipped"


def test_already_recorded_captures_are_not_reloaded():
    blob = data_blob("20261116T000000Z")
    bigquery = FakeBigQuery({"SELECT DISTINCT source_object FROM `proj.ref.loaded_captures`": [{"source_object": blob.name}]})

    result, bigquery = run(FakeStorage([blob]), bigquery)

    assert result.loaded == []
    assert bigquery.loads == []


def test_a_failing_capture_is_left_unrecorded_and_the_rest_still_load():
    broken = data_blob("20261115T000000Z", payload={"not": "cdragon"})
    good = data_blob("20261116T000000Z")

    result, bigquery = run(FakeStorage([broken, good]))

    assert result.failed == [broken.name]
    assert result.loaded == [good.name]
    recorded = [row["source_object"] for row in loads_by_table(bigquery)["loaded_captures"]]
    assert recorded == [good.name]


def test_pairs_with_the_team_planner_capture():
    team_planner = FakeBlob(
        "snapshots/cdragon-teamplanner/pbe/20261115T000000Z_tftchampions-teamplanner.json.gz",
        {"TFTSet16": []},
        {"channel": "pbe"},
    )
    _, bigquery = run(FakeStorage([data_blob("20261116T000000Z"), team_planner]))
    assert loads_by_table(bigquery)["loaded_captures"][0]["team_planner_object"] == team_planner.name
