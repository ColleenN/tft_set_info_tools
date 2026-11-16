"""Listing mirrored CDragon captures and pairing them with Team Planner captures.

tft_mirroring stores each changed copy of a target as
``<path>/<YYYYMMDDTHHMMSSZ>_<file name>.gz``, with GCS object metadata that
includes ``captured-at``, ``channel`` and (for CDragon targets)
``cdragon-version``.

The Team Planner file rarely changes, so it's mirrored far less often than
the main data file and the two captures almost never share a version. A data
capture is paired with the newest Team Planner capture on the same channel
taken at or before it, which is the Team Planner file that was live when the
data was captured.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field
from datetime import datetime, timezone

DATA_PATH = "snapshots/cdragon/{channel}"
TEAM_PLANNER_PATH = "snapshots/cdragon-teamplanner/{channel}"


@dataclass(frozen=True)
class Capture:
    bucket: str
    object_name: str
    channel: str
    captured_at: datetime
    metadata: dict[str, str] = field(default_factory=dict, compare=False, repr=False)

    @property
    def cdragon_version(self) -> str | None:
        return self.metadata.get("cdragon-version") or None


@dataclass(frozen=True)
class CapturePair:
    data: Capture
    team_planner: Capture | None
    """None if no Team Planner capture on the channel predates the data capture."""


def _parse_captured_at(object_name: str, metadata: dict[str, str]) -> datetime:
    if value := metadata.get("captured-at"):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    stamp = object_name.rsplit("/", 1)[-1].split("_", 1)[0]
    return datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


def list_captures(client, bucket: str, path: str, channel: str) -> list[Capture]:
    """Every capture under path, oldest first."""
    captures = []
    for blob in client.list_blobs(bucket, prefix=f"{path.rstrip('/')}/"):
        metadata = dict(blob.metadata or {})
        captures.append(
            Capture(
                bucket=bucket,
                object_name=blob.name,
                channel=metadata.get("channel", channel),
                captured_at=_parse_captured_at(blob.name, metadata),
                metadata=metadata,
            )
        )
    return sorted(captures, key=lambda capture: capture.captured_at)


def pair_team_planner(data: list[Capture], team_planner: list[Capture]) -> list[CapturePair]:
    """Pair each data capture with the newest same-channel Team Planner capture at or before it."""
    by_channel: dict[str, list[Capture]] = {}
    for capture in sorted(team_planner, key=lambda c: c.captured_at):
        by_channel.setdefault(capture.channel, []).append(capture)
    times = {channel: [c.captured_at for c in caps] for channel, caps in by_channel.items()}

    pairs = []
    for capture in data:
        candidates = by_channel.get(capture.channel, [])
        index = bisect.bisect_right(times.get(capture.channel, []), capture.captured_at)
        pairs.append(CapturePair(capture, candidates[index - 1] if index else None))
    return pairs


def list_capture_pairs(client, bucket: str, channel: str) -> list[CapturePair]:
    """The channel's data captures, oldest first, each paired with its Team Planner capture."""
    return pair_team_planner(
        list_captures(client, bucket, DATA_PATH.format(channel=channel), channel),
        list_captures(client, bucket, TEAM_PLANNER_PATH.format(channel=channel), channel),
    )
