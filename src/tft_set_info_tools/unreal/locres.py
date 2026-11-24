"""Unreal localization string tables (.locres)."""

from __future__ import annotations

import os
import struct

from tft_set_info_tools.unreal.codecs import read_fstring

LOCRES_MAGIC = bytes.fromhex("0e147475674a03fc4a15909dc3377f1b")

# ELocResVersion
VERSION_LEGACY = 0
VERSION_COMPACT = 1  # strings stored once in an array, referenced by index
VERSION_OPTIMIZED_CRC32 = 2  # adds key hashes, string ref counts and an entry count
VERSION_OPTIMIZED_CITYHASH64_UTF16 = 3


class LocresFile:
    """A string table, looked up by namespace and key.

    Most gameplay text is in the empty namespace. `entries` maps namespace to
    a dict of key to localized string.
    """

    def __init__(self, source: str | os.PathLike[str] | bytes | None = None) -> None:
        self.version: int | None = None
        self.entries: dict[str, dict[str, str]] = {}
        if source is None:
            return
        if isinstance(source, (bytes, bytearray)):
            data = bytes(source)
        else:
            with open(source, "rb") as f:
                data = f.read()
        self.parse(data)

    def parse(self, data: bytes) -> None:
        if data[:16] == LOCRES_MAGIC:
            self.version = data[16]
            pos = 17
        else:
            self.version = VERSION_LEGACY
            pos = 0
        if self.version > VERSION_OPTIMIZED_CITYHASH64_UTF16:
            raise ValueError(f"unsupported locres version {self.version}")

        strings = None
        if self.version >= VERSION_COMPACT:
            array_offset, = struct.unpack_from("<q", data, pos)
            pos += 8
            strings = self._parse_string_array(data, array_offset)
        if self.version >= VERSION_OPTIMIZED_CRC32:
            pos += 4  # total entry count

        namespace_count, = struct.unpack_from("<I", data, pos)
        pos += 4
        for _ in range(namespace_count):
            if self.version >= VERSION_OPTIMIZED_CRC32:
                pos += 4  # namespace hash
            namespace, pos = read_fstring(data, pos)
            key_count, = struct.unpack_from("<I", data, pos)
            pos += 4
            table = self.entries.setdefault(namespace, {})
            for _ in range(key_count):
                if self.version >= VERSION_OPTIMIZED_CRC32:
                    pos += 4  # key hash
                key, pos = read_fstring(data, pos)
                pos += 4  # source string hash
                if strings is not None:
                    index, = struct.unpack_from("<i", data, pos)
                    pos += 4
                    table[key] = strings[index]
                else:
                    table[key], pos = read_fstring(data, pos)

    def _parse_string_array(self, data: bytes, pos: int) -> list[str]:
        count, = struct.unpack_from("<I", data, pos)
        pos += 4
        strings = []
        for _ in range(count):
            s, pos = read_fstring(data, pos)
            if self.version >= VERSION_OPTIMIZED_CRC32:
                pos += 4  # ref count
            strings.append(s)
        return strings

    def __len__(self) -> int:
        return sum(len(t) for t in self.entries.values())

    def get(self, key: str, namespace: str = "", default: str | None = None) -> str | None:
        return self.entries.get(namespace, {}).get(key, default)

    def update(self, other: LocresFile) -> None:
        """Merge another table in, such as a base table's loc chunks; other wins on conflicts."""
        for namespace, table in other.entries.items():
            self.entries.setdefault(namespace, {}).update(table)
