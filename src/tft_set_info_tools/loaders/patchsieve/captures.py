"""Mirrored Patchsieve copies, and the client-deploy row each one becomes.

tft_mirroring saves a version set's Patchsieve response only when it changes,
so each copy marks a new build being published to that version set. Its
captured-at time is when the mirror first saw the build: the deploy happened
at or before then, by at most the mirror's polling interval. Riot's own
created_at is when the build was made, not when it went out.

A response holds one release, under ``releases[0].release``. Its labels may be
plain strings or ``{"values": [...]}`` lists, so both are accepted.
"""

from __future__ import annotations

import gzip
import json
import re
from dataclasses import dataclass

from tft_set_info_tools.loaders.captures import Capture, list_captures

DEFAULT_PATH = "patchsieve"

_STREAM_RE = re.compile(r"\Arls-(?P<major>\d+)\.(?P<minor>\d+)")


@dataclass(frozen=True, kw_only=True)
class PatchsieveCapture(Capture):
    version_set: str

    @classmethod
    def from_blob(cls, bucket: str, blob, version_set: str) -> PatchsieveCapture:
        """version_set is used only if the copy's metadata doesn't name one."""
        metadata = blob.metadata or {}
        return super().from_blob(bucket, blob, version_set=metadata.get("version-set", version_set))


def list_patchsieve_captures(client, bucket: str, path: str = DEFAULT_PATH) -> list[PatchsieveCapture]:
    """Every saved copy under path/<version set>/, oldest first."""
    prefix = f"{path.rstrip('/')}/"
    version_sets = sorted(
        {
            blob.name[len(prefix) :].split("/", 1)[0]
            for blob in client.list_blobs(bucket, prefix=prefix)
            if "/" in blob.name[len(prefix) :]
        }
    )
    captures = [
        capture
        for version_set in version_sets
        for capture in list_captures(
            client, bucket, f"{prefix}{version_set}", PatchsieveCapture, version_set=version_set
        )
    ]
    return sorted(captures, key=lambda c: c.captured_at)


def channel_and_region(version_set: str) -> tuple[str, str | None]:
    """("live", "NA1") for live-NA1; ("pbe", None) for pbe-global."""
    channel, _, region = version_set.partition("-")
    if channel == "pbe":
        return channel, None
    return channel, region or None


def _label(labels: dict, name: str) -> str | None:
    value = labels.get(name)
    if isinstance(value, dict):
        value = value.get("values")
    if isinstance(value, list):
        value = value[0] if value else None
    return str(value) if value is not None else None


def patch_from_stream(stream: str | None) -> str | None:
    """The patch number, e.g. 18.7 from rls-18.7.0."""
    match = _STREAM_RE.match(stream or "")
    return f"{match['major']}.{match['minor']}" if match else None


def parse_release(content: bytes) -> dict:
    """The deploy fields from one saved response (gzipped or not)."""
    if content[:2] == b"\x1f\x8b":
        content = gzip.decompress(content)
    releases = json.loads(content).get("releases") or []
    if len(releases) != 1:
        raise ValueError(f"expected one release, got {len(releases)}")
    release = releases[0].get("release") or {}
    labels = release.get("labels") or {}
    stream = _label(labels, "Stream")
    revision = _label(labels, "riot:revision")
    if revision is None:
        raise ValueError("release has no riot:revision label")
    return {
        "release_id": release.get("id"),
        "release_created_at": release.get("created_at"),
        "stream": stream,
        "patch": patch_from_stream(stream),
        "revision": revision,
        "artifact_version_id": _label(labels, "riot:artifact_version_id"),
    }


def deploy_row(capture: PatchsieveCapture, content: bytes) -> dict:
    channel, region = channel_and_region(capture.version_set)
    return {
        "version_set": capture.version_set,
        "channel": channel,
        "region": region,
        "platform": capture.metadata.get("platform"),
        "artifact_type": capture.metadata.get("artifact-type"),
        **parse_release(content),
        "captured_at": capture.captured_at,
        "source_object": capture.object_name,
    }
