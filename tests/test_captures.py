from datetime import datetime, timezone

from tft_set_info_tools.loader.captures import (
    Capture,
    list_capture_pairs,
    list_captures,
    pair_team_planner,
)


def at(day, hour=0):
    return datetime(2026, 11, day, hour, tzinfo=timezone.utc)


def capture(name, channel, captured_at):
    return Capture("bucket", name, channel, captured_at)


class FakeBlob:
    def __init__(self, name, metadata):
        self.name = name
        self.metadata = metadata


class FakeClient:
    def __init__(self, blobs):
        self.blobs = blobs
        self.listed = []

    def list_blobs(self, bucket, prefix):
        self.listed.append((bucket, prefix))
        return [b for b in self.blobs if b.name.startswith(prefix)]


def test_list_captures_sorts_by_capture_time_and_reads_metadata():
    client = FakeClient(
        [
            FakeBlob(
                "snapshots/cdragon/live/20261112T000000Z_en_us.json.gz",
                {"captured-at": "2026-11-12T00:00:00Z", "channel": "live", "cdragon-version": "16.22.1"},
            ),
            FakeBlob(
                "snapshots/cdragon/live/20261110T000000Z_en_us.json.gz",
                {"captured-at": "2026-11-10T00:00:00Z", "channel": "live"},
            ),
        ]
    )

    captures = list_captures(client, "bucket", "snapshots/cdragon/live", "live")

    assert [c.captured_at for c in captures] == [at(10), at(12)]
    assert captures[1].cdragon_version == "16.22.1"
    assert captures[0].cdragon_version is None
    assert client.listed == [("bucket", "snapshots/cdragon/live/")]


def test_list_captures_falls_back_to_the_object_name():
    client = FakeClient([FakeBlob("snapshots/cdragon/pbe/20261111T171700Z_en_us.json.gz", None)])

    [only] = list_captures(client, "bucket", "snapshots/cdragon/pbe", "pbe")

    assert only.captured_at == datetime(2026, 11, 11, 17, 17, tzinfo=timezone.utc)
    assert only.channel == "pbe"


def test_list_captures_does_not_match_a_sibling_prefix():
    client = FakeClient([FakeBlob("snapshots/cdragon/live-old/20261110T000000Z_x.gz", {})])
    assert list_captures(client, "bucket", "snapshots/cdragon/live", "live") == []


def test_pairs_with_latest_team_planner_capture_at_or_before():
    data = [capture("d1", "live", at(10, 12)), capture("d2", "live", at(12)), capture("d3", "live", at(14))]
    team_planner = [capture("t1", "live", at(10)), capture("t2", "live", at(12)), capture("t3", "live", at(15))]

    pairs = pair_team_planner(data, team_planner)

    assert [(p.data.object_name, p.team_planner.object_name) for p in pairs] == [
        ("d1", "t1"),
        ("d2", "t2"),
        ("d3", "t2"),
    ]


def test_data_capture_older_than_every_team_planner_capture_has_none():
    [pair] = pair_team_planner([capture("d1", "live", at(9))], [capture("t1", "live", at(10))])
    assert pair.team_planner is None


def test_pairs_only_within_a_channel():
    data = [capture("d-live", "live", at(12)), capture("d-pbe", "pbe", at(12))]
    team_planner = [capture("t-pbe", "pbe", at(11)), capture("t-live", "live", at(13))]

    pairs = {p.data.object_name: p.team_planner for p in pair_team_planner(data, team_planner)}

    assert pairs["d-live"] is None
    assert pairs["d-pbe"].object_name == "t-pbe"


def test_list_capture_pairs_reads_both_paths():
    client = FakeClient(
        [
            FakeBlob("snapshots/cdragon/pbe/20261112T000000Z_en_us.json.gz", {"channel": "pbe"}),
            FakeBlob(
                "snapshots/cdragon-teamplanner/pbe/20261111T000000Z_tftchampions-teamplanner.json.gz",
                {"channel": "pbe"},
            ),
        ]
    )

    [pair] = list_capture_pairs(client, "bucket", "pbe")

    assert pair.data.object_name.startswith("snapshots/cdragon/pbe/")
    assert pair.team_planner.object_name.startswith("snapshots/cdragon-teamplanner/pbe/")
