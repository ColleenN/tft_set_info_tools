"""Pak containers (.pak), version 10 and later."""

from __future__ import annotations

import fnmatch
import logging
import os
import struct
from dataclasses import dataclass
from typing import BinaryIO, Iterable

from tft_set_info_tools.unreal.codecs import aes_decrypt, align, decompress, read_fstring

logger = logging.getLogger(__name__)

PAK_MAGIC = 0x5A6F12E1
# first version with the path hash index and full directory index
PAK_MIN_VERSION = 10
# EncryptionKeyGuid, bEncryptedIndex, Magic, Version, IndexOffset, IndexSize, IndexHash, 5 method names
FOOTER_SIZE = 16 + 1 + 4 + 4 + 8 + 8 + 20 + 5 * 32
# Offset, Size, UncompressedSize, CompressionMethodIndex, Hash
ENTRY_HEADER_SIZE = 8 * 3 + 4 + 20


@dataclass
class PakEntry:
    """A file stored in a pak.

    `blocks` holds (start, end) offsets relative to `offset`.
    """

    path: str
    offset: int
    size: int
    uncompressed_size: int
    method: str
    encrypted: bool
    block_size: int
    blocks: list[tuple[int, int]]

    @property
    def length(self) -> int:
        return self.uncompressed_size


def mount_root(mount_point: str) -> str:
    """Turn a mount point into a prefix relative to the game's root directory.

    Mount points are relative to the executable's directory, usually
    `../../../` (the game root) or a folder under it.
    """
    root = mount_point.replace("\\", "/")
    while root.startswith("../"):
        root = root[3:]
    root = root.lstrip("/")
    if root and not root.endswith("/"):
        root += "/"
    return root


class PakFile:
    """Read a pak file's directory and files."""

    def __init__(self, path: str | os.PathLike[str], aes_key: bytes | None = None) -> None:
        self.path = os.fspath(path)
        self.aes_key = aes_key
        self.entries: list[PakEntry] = []
        self.mount_point = ""
        self.version = 0
        self.methods: list[str] = []
        with open(self.path, "rb") as f:
            self._parse(f)

    def _read_maybe_encrypted(self, f: BinaryIO, offset: int, size: int, encrypted: bool) -> bytes:
        f.seek(offset)
        if not encrypted:
            return f.read(size)
        if self.aes_key is None:
            raise ValueError(f"{self.path} is encrypted, an AES key is required")
        return aes_decrypt(f.read(align(size)), self.aes_key)[:size]

    def _parse(self, f: BinaryIO) -> None:
        f.seek(0, os.SEEK_END)
        if f.tell() < FOOTER_SIZE:
            raise ValueError(f"{self.path} is too small to be a pak file")
        f.seek(f.tell() - FOOTER_SIZE)
        footer = f.read(FOOTER_SIZE)
        encrypted_index = footer[16] != 0
        magic, version, index_offset, index_size = struct.unpack_from("<IiQQ", footer, 17)
        if magic != PAK_MAGIC:
            raise ValueError(f"{self.path} is not a pak file (or uses an unsupported footer)")
        if version < PAK_MIN_VERSION:
            raise ValueError(f"unsupported pak version {version}")
        self.version = version
        names = footer[FOOTER_SIZE - 5 * 32:]
        names = [names[i:i + 32].rstrip(b"\0").decode() for i in range(0, 5 * 32, 32)]
        # like Unreal, skip empty slots: entries index into the non-empty names
        self.methods = ["None"] + [n for n in names if n]

        index = self._read_maybe_encrypted(f, index_offset, index_size, encrypted_index)
        self.mount_point, pos = read_fstring(index, 0)
        pos += 4 + 8  # entry count, path hash seed
        has_path_hash_index, = struct.unpack_from("<I", index, pos)
        pos += 4
        if has_path_hash_index:
            pos += 8 + 8 + 20
        has_dir_index, = struct.unpack_from("<I", index, pos)
        pos += 4
        if not has_dir_index:
            raise ValueError(f"{self.path} has no full directory index")
        dir_offset, dir_size = struct.unpack_from("<QQ", index, pos)
        pos += 16 + 20
        encoded_size, = struct.unpack_from("<i", index, pos)
        pos += 4
        encoded = index[pos:pos + encoded_size]
        pos += encoded_size
        file_count, = struct.unpack_from("<i", index, pos)
        pos += 4
        unencoded = []
        for _ in range(file_count):
            entry, pos = self._parse_full_entry(index, pos)
            unencoded.append(entry)

        root = mount_root(self.mount_point)
        dir_index = self._read_maybe_encrypted(f, dir_offset, dir_size, encrypted_index)
        pos = 0
        dir_count, = struct.unpack_from("<i", dir_index, pos)
        pos += 4
        for _ in range(dir_count):
            dirname, pos = read_fstring(dir_index, pos)
            dirname = dirname.lstrip("/")
            n, = struct.unpack_from("<i", dir_index, pos)
            pos += 4
            for _ in range(n):
                filename, pos = read_fstring(dir_index, pos)
                location, = struct.unpack_from("<i", dir_index, pos)
                pos += 4
                if location >= 0:
                    entry = self._decode_entry(encoded, location)
                else:
                    entry = unencoded[-location - 1]
                entry.path = root + dirname + filename
                self.entries.append(entry)

    def _decode_entry(self, buf: bytes, pos: int) -> PakEntry:
        """Decode an entry from the bit-packed form used in the primary index."""
        value, = struct.unpack_from("<I", buf, pos)
        pos += 4
        if (value & 0x3F) == 0x3F:
            block_size, = struct.unpack_from("<I", buf, pos)
            pos += 4
        else:
            block_size = (value & 0x3F) << 11
        method = (value >> 23) & 0x3F
        encrypted = bool(value & (1 << 22))
        block_count = (value >> 6) & 0xFFFF

        def read_int(is_32bit: int) -> int:
            nonlocal pos
            fmt = "<I" if is_32bit else "<Q"
            v, = struct.unpack_from(fmt, buf, pos)
            pos += struct.calcsize(fmt)
            return v

        offset = read_int(value & (1 << 31))
        uncompressed_size = read_int(value & (1 << 30))
        size = read_int(value & (1 << 29)) if method else uncompressed_size

        # the entry's serialized header is still written before its data
        struct_size = ENTRY_HEADER_SIZE + 1 + 4
        if method:
            struct_size += 4 + block_count * 16
        if block_count == 1:
            block_size = uncompressed_size

        blocks = []
        if block_count == 1 and not encrypted:
            blocks.append((struct_size, struct_size + size))
        elif block_count:
            start = struct_size
            for _ in range(block_count):
                n, = struct.unpack_from("<I", buf, pos)
                pos += 4
                blocks.append((start, start + n))
                start += align(n) if encrypted else n
        else:
            blocks.append((struct_size, struct_size + size))
        return PakEntry("", offset, size, uncompressed_size, self.methods[method], encrypted, block_size, blocks)

    def _parse_full_entry(self, buf: bytes, pos: int) -> tuple[PakEntry, int]:
        """Parse an entry serialized in full, for entries that can't be bit-packed."""
        offset, size, uncompressed_size, method = struct.unpack_from("<qqqI", buf, pos)
        pos += ENTRY_HEADER_SIZE
        blocks = []
        if method:
            n, = struct.unpack_from("<I", buf, pos)
            pos += 4
            for _ in range(n):
                blocks.append(struct.unpack_from("<qq", buf, pos))
                pos += 16
        flags, block_size = struct.unpack_from("<BI", buf, pos)
        pos += 5
        if not blocks:
            start = ENTRY_HEADER_SIZE + 1 + 4
            blocks.append((start, start + size))
        entry = PakEntry(
            "", offset, size, uncompressed_size, self.methods[method], bool(flags & 1), block_size, blocks
        )
        return entry, pos

    def read(self, entry: PakEntry, f: BinaryIO | None = None) -> bytes:
        """Return an entry's uncompressed content."""
        if f is None:
            with open(self.path, "rb") as f:
                return self.read(entry, f)
        chunks = []
        remaining = entry.uncompressed_size
        for start, end in entry.blocks:
            raw = self._read_maybe_encrypted(f, entry.offset + start, end - start, entry.encrypted)
            if entry.method == "None":
                chunks.append(raw)
                continue
            n = min(entry.block_size, remaining)
            chunks.append(decompress(entry.method, raw, n))
            remaining -= n
        return b"".join(chunks)[:entry.uncompressed_size]

    def find(self, *patterns: str) -> list[PakEntry]:
        """Entries whose path matches any of the fnmatch patterns."""
        return [e for e in self.entries if any(fnmatch.fnmatchcase(e.path, p) for p in patterns)]

    def extract(self, output: str | os.PathLike[str], entries: Iterable[PakEntry] | None = None,
                overwrite: bool = True) -> None:
        """Write entries (all by default) under output, at their container paths."""
        entries = list(self.entries if entries is None else entries)
        logger.info("extracting %d files from %s to %s", len(entries), self.path, output)
        with open(self.path, "rb") as f:
            for entry in entries:
                target = os.path.join(output, entry.path)
                if not overwrite and os.path.exists(target):
                    continue
                os.makedirs(os.path.dirname(target), exist_ok=True)
                logger.debug("extracting %s", entry.path)
                with open(target, "wb") as fout:
                    fout.write(self.read(entry, f))
