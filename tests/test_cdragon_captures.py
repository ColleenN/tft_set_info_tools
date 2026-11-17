from datetime import datetime, timezone

from tests.fake_storage import FakeBlob, FakeClient
from tft_set_info_tools.loader.captures import list_captures
from tft_set_info_tools.loader.cdragon import (
    CDragonCapture,
    list_capture_pairs,
    pair_team_planner,
)


def at(day, hour=0):
    return datetime(2026, 11, day, hour, tzinfo=timezone.utc)


def capture(name, channel, captured_at):
    return CDragonCapture(bucket="bucket", object_name=name, channel=channel, captured_at=captured_at)


def test_reads_channel_and_version_from_metadata():
    client = FakeClient(
        [
            FakeBlob(
                "snapshots/cdragon/live/20261112T000000Z_en_us.json.gz",
                {"captured-at": "2026-11-12T00:00:00Z", "channel": "live", "cdragon-version": "16.22.1"},
            ),
            FakeBlob("snapshots/cdragon/live/20261110T000000Z_en_us.json.gz", {"channel": "pbe"}),
        ]
    )

    old, new = list_captures(client, "bucket", "snapshots/cdragon/live", CDragonCapture, channel="live")

    assert new.channel == "live"
    assert new.cdragon_version == "16.22.1"
    assert old.channel == "pbe"
    assert old.cdragon_version is None


def test_channel_falls_back_to_the_one_listed():
    client = FakeClient([FakeBlob("snapshots/cdragon/pbe/20261111T000000Z_en_us.json.gz", None)])
    [only] = list_captures(client, "bucket", "snapshots/cdragon/pbe", CDragonCapture, channel="pbe")
    assert only.channel == "pbe"


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

    assert isinstance(pair.data, CDragonCapture)
    assert pair.data.object_name.startswith("snapshots/cdragon/pbe/")
    assert pair.team_planner.object_name.startswith("snapshots/cdragon-teamplanner/pbe/")
