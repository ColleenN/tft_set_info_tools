"""Copies saved by tft_mirroring, from any source.

tft_mirroring stores each changed copy of a target as
``<path>/<YYYYMMDDTHHMMSSZ>_<file name>.gz``, with GCS object metadata that
always includes ``captured-at``, plus whatever extra fields the target's
config adds. Subclasses expose a source's extra fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TypeVar

C = TypeVar("C", bound="Capture")


def _parse_captured_at(object_name: str, metadata: dict[str, str]) -> datetime:
    if value := metadata.get("captured-at"):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    stamp = object_name.rsplit("/", 1)[-1].split("_", 1)[0]
    return datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


@dataclass(frozen=True, kw_only=True)
class Capture:
    bucket: str
    object_name: str
    captured_at: datetime
    metadata: dict[str, str] = field(default_factory=dict, compare=False, repr=False)

    @classmethod
    def from_blob(cls: type[C], bucket: str, blob, **fields) -> C:
        metadata = dict(blob.metadata or {})
        return cls(
            bucket=bucket,
            object_name=blob.name,
            captured_at=_parse_captured_at(blob.name, metadata),
            metadata=metadata,
            **fields,
        )


def list_captures(client, bucket: str, path: str, capture_type: type[C] = Capture, **fields) -> list[C]:
    """Every capture under path, oldest first. fields go to capture_type.from_blob."""
    captures = [
        capture_type.from_blob(bucket, blob, **fields)
        for blob in client.list_blobs(bucket, prefix=f"{path.rstrip('/')}/")
    ]
    return sorted(captures, key=lambda capture: capture.captured_at)
