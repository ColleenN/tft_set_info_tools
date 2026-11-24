"""Find the localized text an asset stores.

Gameplay text in the Unreal client is keyed by IDs like
`1F777F094AD4B14BB621D38CB4D91A86`, generated when the text is authored.
They aren't hashes, so the only way to know what an ID belongs to is to find
the asset that stores it. Assets serialize text as a namespace, the key and
the English source string, all in clear, so they can be found without
parsing the asset's properties.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass

# A 32-digit hex key serialized as an FString: length 33, then the key and a null.
KEY_PATTERN = re.compile(rb"\x21\x00\x00\x00([0-9A-F]{32})\x00")
MAX_NAMESPACE_LENGTH = 256


@dataclass(frozen=True)
class TextReference:
    namespace: str
    key: str
    source: str


def _read_namespace(data: bytes, end: int) -> str | None:
    """Read the FString that ends at `end`, or None if there isn't one."""
    # Most text uses the empty namespace, serialized as an empty or null-only string.
    if data[end - 5:end] == b"\x01\x00\x00\x00\x00" or data[end - 4:end] == b"\x00\x00\x00\x00":
        return ""
    if end < 1 or data[end - 1] != 0:
        return None
    for n in range(2, min(MAX_NAMESPACE_LENGTH, end - 4) + 1):
        if struct.unpack_from("<i", data, end - n - 4)[0] == n:
            raw = data[end - n:end - 1]
            return raw.decode("ascii") if all(32 <= c < 127 for c in raw) else None
    return None


def _read_source(data: bytes, pos: int) -> str | None:
    """Read the FString at `pos`, or None if it doesn't look like one."""
    if pos + 4 > len(data):
        return None
    n, = struct.unpack_from("<i", data, pos)
    pos += 4
    if n == 0:
        return ""
    if n > 0:
        raw = data[pos:pos + n]
        if len(raw) != n or raw[-1] != 0:
            return None
        return raw[:-1].decode("utf-8", "replace")
    raw = data[pos:pos - 2 * n]
    if len(raw) != -2 * n or raw[-2:] != b"\0\0":
        return None
    return raw[:-2].decode("utf-16-le", "replace")


def find_text_references(data: bytes) -> list[TextReference]:
    """Each localized text serialized in `data`, in the order they appear."""
    refs = []
    for m in KEY_PATTERN.finditer(data):
        namespace = _read_namespace(data, m.start())
        if namespace is None:
            continue
        source = _read_source(data, m.end())
        if source is None:
            continue
        refs.append(TextReference(namespace, m.group(1).decode("ascii"), source))
    return refs
