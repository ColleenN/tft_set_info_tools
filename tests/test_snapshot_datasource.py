import gzip
import json
import sys
import types

import pytest

from tft_set_info_tools.datasource import SnapshotDataSource

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
    storage_module.Client = lambda: client
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
