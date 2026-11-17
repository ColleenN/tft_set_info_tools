from datetime import datetime, timezone

from tests.fake_storage import FakeBlob, FakeClient
from tft_set_info_tools.loader.captures import Capture, list_captures


def at(day, hour=0, minute=0):
    return datetime(2026, 11, day, hour, minute, tzinfo=timezone.utc)


def test_list_captures_sorts_by_capture_time_and_keeps_metadata():
    client = FakeClient(
        [
            FakeBlob("snapshots/src/20261112T000000Z_f.json.gz", {"captured-at": "2026-11-12T00:00:00Z", "x": "1"}),
            FakeBlob("snapshots/src/20261110T000000Z_f.json.gz", {"captured-at": "2026-11-10T00:00:00Z"}),
        ]
    )

    captures = list_captures(client, "bucket", "snapshots/src")

    assert [c.captured_at for c in captures] == [at(10), at(12)]
    assert all(type(c) is Capture for c in captures)
    assert captures[1].metadata == {"captured-at": "2026-11-12T00:00:00Z", "x": "1"}
    assert client.listed == [("bucket", "snapshots/src/")]


def test_captured_at_falls_back_to_the_object_name():
    client = FakeClient([FakeBlob("snapshots/src/20261111T171700Z_f.json.gz", None)])

    [only] = list_captures(client, "bucket", "snapshots/src")

    assert only.captured_at == at(11, 17, 17)
    assert only.metadata == {}


def test_list_captures_does_not_match_a_sibling_prefix():
    client = FakeClient([FakeBlob("snapshots/src-old/20261110T000000Z_f.gz", {})])
    assert list_captures(client, "bucket", "snapshots/src") == []
