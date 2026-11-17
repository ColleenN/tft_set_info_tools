import gzip
import json
import sys
import types

import pytest

from tft_set_info_tools.datasource import CDragonDataSource, CDragonPairedSnapshotDataSource, SnapshotDataSource

PAYLOAD = {"items": [], "setData": [], "sets": {}}
METADATA = {
    "channel": "pbe",
    "cdragon-version": "16.22.8312345+branch.releases-16-22.content.release",
}
OBJECT = "snapshots/cdragon/pbe/x.json.gz"


class FakeBlob:
    def __init__(self, content: bytes, metadata):
        self._content = content
        self.metadata = metadata

    def download_as_bytes(self):
        return self._content


class FakeClient:
    def __init__(self, objects):
        self.objects = objects
        self.closed = False
        self.requested = []

    def bucket(self, bucket_name):
        client = self

        class FakeBucket:
            def get_blob(self, object_name):
                client.requested.append((bucket_name, object_name))
                return client.objects.get((bucket_name, object_name))

        return FakeBucket()

    def close(self):
        self.closed = True


def snapshot_client(payload=PAYLOAD, metadata=METADATA):
    content = gzip.compress(json.dumps(payload).encode())
    return FakeClient({("bucket", OBJECT): FakeBlob(content, metadata)})


def test_reads_gzipped_payload_and_metadata():
    client = snapshot_client()
    with SnapshotDataSource("bucket", OBJECT, client=client) as source:
        assert source.read() == PAYLOAD
        assert source.metadata == METADATA

    assert client.requested == [("bucket", OBJECT)]


def test_object_without_metadata_has_empty_metadata():
    client = snapshot_client(metadata=None)
    with SnapshotDataSource("bucket", OBJECT, client=client) as source:
        source.read()
        assert source.metadata == {}


def test_metadata_before_read_raises():
    source = SnapshotDataSource("bucket", OBJECT, client=snapshot_client())
    with pytest.raises(RuntimeError):
        source.metadata


def test_missing_object_raises():
    source = SnapshotDataSource("bucket", "snapshots/missing.json.gz", client=snapshot_client())
    with source:
        with pytest.raises(FileNotFoundError, match="gs://bucket/snapshots/missing.json.gz"):
            source.read()


def test_has_no_schema():
    assert SnapshotDataSource("bucket", "x.json.gz", client=snapshot_client()).get_schema() is None


@pytest.mark.parametrize("bucket, object_name", [("", "x.json.gz"), ("bucket", "")])
def test_requires_bucket_and_object_name(bucket, object_name):
    with pytest.raises(ValueError):
        SnapshotDataSource(bucket, object_name)


def test_write_raises():
    with pytest.raises(NotImplementedError):
        SnapshotDataSource("bucket", "x.json.gz", client=snapshot_client()).write({})


def test_shared_client_is_left_open():
    client = snapshot_client()
    with SnapshotDataSource("bucket", OBJECT, client=client) as source:
        source.read()
    assert not client.closed


def test_own_client_is_created_and_closed(monkeypatch):
    client = snapshot_client()
    storage_module = types.ModuleType("google.cloud.storage")
    storage_module.Client = lambda project=None: client
    cloud_module = types.ModuleType("google.cloud")
    cloud_module.storage = storage_module
    google_module = types.ModuleType("google")
    google_module.cloud = cloud_module
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud_module)
    monkeypatch.setitem(sys.modules, "google.cloud.storage", storage_module)

    with SnapshotDataSource("bucket", OBJECT) as source:
        assert source.read() == PAYLOAD
    assert client.closed


TEAM_PLANNER = {"TFTSet17": [{"character_id": "TFT17_Zilean", "team_planner_code": 1}]}
TEAM_PLANNER_METADATA = {"channel": "pbe", "cdragon-version": "16.21.8298620"}
TEAM_PLANNER_OBJECT = "snapshots/cdragon-teamplanner/pbe/y.json.gz"


def paired_client():
    client = snapshot_client()
    client.objects[("bucket", TEAM_PLANNER_OBJECT)] = FakeBlob(
        gzip.compress(json.dumps(TEAM_PLANNER).encode()), TEAM_PLANNER_METADATA
    )
    return client


def test_paired_snapshot_bundles_team_planner_codes():
    client = paired_client()
    with CDragonPairedSnapshotDataSource("bucket", OBJECT, TEAM_PLANNER_OBJECT, client=client) as source:
        assert source.read() == {**PAYLOAD, CDragonDataSource.TEAM_PLANNER_CODES_KEY: TEAM_PLANNER}
        assert source.metadata == METADATA
        assert source.team_planner_metadata == TEAM_PLANNER_METADATA


def test_paired_snapshot_without_team_planner_object():
    client = paired_client()
    with CDragonPairedSnapshotDataSource("bucket", OBJECT, client=client) as source:
        assert source.read() == PAYLOAD
        assert source.team_planner_metadata == {}
    assert client.requested == [("bucket", OBJECT)]


def test_paired_snapshot_missing_team_planner_object_raises():
    source = CDragonPairedSnapshotDataSource("bucket", OBJECT, "snapshots/missing.json.gz", client=snapshot_client())
    with source:
        with pytest.raises(FileNotFoundError, match="snapshots/missing.json.gz"):
            source.read()
