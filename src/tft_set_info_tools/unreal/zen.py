"""Name tables of cooked ("zen") Unreal packages.

IoStore assets are zen packages. Their property values are stored without
names or types, but each package lists the names it uses and the packages
it imports in clear. That's enough to identify an asset and what it
references without a mappings file.
"""

from __future__ import annotations

import struct

# Summary layout written by the TFT client's engine version, up to the name table.
SUMMARY_SIZE = 60
HEADER_SIZE_OFFSET = 4
IMPORTED_PACKAGE_NAMES_OFFSET = 48


def read_name_batch(data: bytes, pos: int) -> list[str]:
    """Read a name batch: count, buffer size, hash version, hashes, lengths, then strings."""
    count, _ = struct.unpack_from("<II", data, pos)
    pos += 8 + 8 + 8 * count
    lengths = struct.unpack_from(f">{count}h", data, pos)
    pos += 2 * count
    names = []
    for n in lengths:
        if n < 0:
            n &= 0x7FFF
            names.append(data[pos:pos + 2 * n].decode("utf-16-le"))
            pos += 2 * n
        else:
            names.append(data[pos:pos + n].decode("utf-8", "replace"))
            pos += n
    return names


class ZenPackage:
    """The names and imported package paths of a zen package."""

    def __init__(self, data: bytes) -> None:
        has_versioning, self.header_size = struct.unpack_from("<II", data, 0)
        pos = SUMMARY_SIZE
        if has_versioning:
            pos += 4 + 4 * 3  # zen version, UE4 and UE5 file versions, licensee version
            n, = struct.unpack_from("<i", data, pos)
            pos += 4 + 20 * n  # custom versions: GUID and version
        self.names = read_name_batch(data, pos)
        offset, = struct.unpack_from("<I", data, IMPORTED_PACKAGE_NAMES_OFFSET)
        self.imported_packages = read_name_batch(data, offset) if offset else []
        self.body = data[self.header_size:]

    def names_with_prefix(self, prefix: str) -> list[str]:
        return [n for n in self.names if n.startswith(prefix)]

    def identifier(self) -> str | None:
        """The asset's `Identifier.<Kind>.<Name>` tag, if it has one."""
        ids = self.names_with_prefix("Identifier.")
        return ids[0] if ids else None
