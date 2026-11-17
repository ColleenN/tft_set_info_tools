"""Mirrored CDragon captures, and pairing data captures with Team Planner captures.

CDragon targets add ``channel`` and ``cdragon-version`` to each copy's
metadata.

The Team Planner file rarely changes, so it's mirrored far less often than
the main data file and the two captures almost never share a version. A data
capture is paired with the newest Team Planner capture on the same channel
taken at or before it, which is the Team Planner file that was live when the
data was captured.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass

from tft_set_info_tools.loader.captures import Capture, list_captures

DATA_PATH = "snapshots/cdragon/{channel}"
TEAM_PLANNER_PATH = "snapshots/cdragon-teamplanner/{channel}"


@dataclass(frozen=True, kw_only=True)
class CDragonCapture(Capture):
    channel: str

    @classmethod
    def from_blob(cls, bucket: str, blob, channel: str) -> CDragonCapture:
        """channel is used only if the copy's metadata doesn't name one."""
        return super().from_blob(bucket, blob, channel=(blob.metadata or {}).get("channel", channel))

    @property
    def cdragon_version(self) -> str | None:
        return self.metadata.get("cdragon-version") or None


@dataclass(frozen=True)
class CapturePair:
    data: CDragonCapture
    team_planner: CDragonCapture | None
    """None if no Team Planner capture on the channel predates the data capture."""


def pair_team_planner(data: list[CDragonCapture], team_planner: list[CDragonCapture]) -> list[CapturePair]:
    """Pair each data capture with the newest same-channel Team Planner capture at or before it."""
    by_channel: dict[str, list[CDragonCapture]] = {}
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
        list_captures(client, bucket, DATA_PATH.format(channel=channel), CDragonCapture, channel=channel),
        list_captures(client, bucket, TEAM_PLANNER_PATH.format(channel=channel), CDragonCapture, channel=channel),
    )
