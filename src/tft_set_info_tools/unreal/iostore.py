"""IoStore containers: a .utoc table of contents and its .ucas data files."""

from __future__ import annotations

import fnmatch
import logging
import os
import struct
from dataclasses import dataclass
from typing import BinaryIO, Iterable

from tft_set_info_tools.unreal.codecs import aes_decrypt, align, decompress, read_fstring
from tft_set_info_tools.unreal.pak import mount_root

logger = logging.getLogger(__name__)

TOC_MAGIC = b"-==--==--==--==-"
INVALID = 0xFFFFFFFF

FLAG_COMPRESSED = 1 << 0
FLAG_ENCRYPTED = 1 << 1
FLAG_SIGNED = 1 << 2
FLAG_INDEXED = 1 << 3


@dataclass
class IoStoreEntry:
    """A file in an IoStore container, backed by one chunk.

    `offset` and `length` place it in the container's uncompressed data.
    """

    path: str
    toc_index: int
    offset: int
    length: int


class IoStoreReader:
    """Read an IoStore container, given its .utoc file.

    Data is read from the .ucas files next to it. Chunk offsets are positions
    in the container's uncompressed data, which is split into fixed-size
    compression blocks.
    """

    def __init__(self, path: str | os.PathLike[str], aes_key: bytes | None = None) -> None:
        self.path = os.fspath(path)
        self.aes_key = aes_key
        self.entries: list[IoStoreEntry] = []
        self.mount_point = ""
        with open(self.path, "rb") as f:
            self._toc = f.read()
        self._parse()

    def _parse(self) -> None:
        toc = self._toc
        if toc[:16] != TOC_MAGIC:
            raise ValueError(f"{self.path} is not an IoStore table of contents")
        self.version = toc[16]
        (header_size, entry_count, block_count, block_entry_size, method_count,
         method_length, self.block_size, dir_index_size, partition_count) = struct.unpack_from("<9I", toc, 20)
        self.container_id, = struct.unpack_from("<Q", toc, 56)
        self.flags = toc[80]
        seed_count, = struct.unpack_from("<I", toc, 84)
        self.partition_size, = struct.unpack_from("<Q", toc, 88)
        no_hash_count, = struct.unpack_from("<I", toc, 96)
        self.partition_count = max(partition_count, 1)
        if block_entry_size != 12:
            raise ValueError(f"unsupported compression block entry size: {block_entry_size}")
        if self.encrypted and self.aes_key is None:
            raise ValueError(f"{self.path} is encrypted, an AES key is required")

        pos = header_size
        self._chunk_ids_pos = pos
        pos += 12 * entry_count
        self._offsets_pos = pos
        pos += 10 * entry_count
        pos += 4 * seed_count + 4 * no_hash_count
        self._blocks_pos = pos
        self.block_count = block_count
        pos += 12 * block_count
        self.methods = ["None"] + [
            toc[pos + i * method_length:pos + (i + 1) * method_length].rstrip(b"\0").decode()
            for i in range(method_count)
        ]
        pos += method_length * method_count
        if self.flags & FLAG_SIGNED:
            hash_size, = struct.unpack_from("<i", toc, pos)
            pos += 4 + 2 * hash_size + 20 * block_count
        self.entry_count = entry_count

        if self.flags & FLAG_INDEXED and dir_index_size:
            dir_index = toc[pos:pos + dir_index_size]
            if self.encrypted:
                dir_index = aes_decrypt(dir_index[:len(dir_index) // 16 * 16], self.aes_key)
            self._parse_directory_index(dir_index)

    @property
    def encrypted(self) -> bool:
        return bool(self.flags & FLAG_ENCRYPTED)

    def _parse_directory_index(self, buf: bytes) -> None:
        self.mount_point, pos = read_fstring(buf, 0)
        n, = struct.unpack_from("<i", buf, pos)
        pos += 4
        dirs = [struct.unpack_from("<4I", buf, pos + 16 * i) for i in range(n)]
        pos += 16 * n
        n, = struct.unpack_from("<i", buf, pos)
        pos += 4
        files = [struct.unpack_from("<3I", buf, pos + 12 * i) for i in range(n)]
        pos += 12 * n
        n, = struct.unpack_from("<i", buf, pos)
        pos += 4
        strings = []
        for _ in range(n):
            s, pos = read_fstring(buf, pos)
            strings.append(s)

        # Each stack item is the first directory of a sibling list, and its parent's path.
        stack = [(0, mount_root(self.mount_point))] if dirs else []
        while stack:
            d, parent = stack.pop()
            while d != INVALID:
                name, first_child, next_sibling, first_file = dirs[d]
                path = parent if name == INVALID else parent + strings[name] + "/"
                f = first_file
                while f != INVALID:
                    fname, next_file, toc_index = files[f]
                    offset, length = self.chunk_offset_length(toc_index)
                    self.entries.append(IoStoreEntry(path + strings[fname], toc_index, offset, length))
                    f = next_file
                if first_child != INVALID:
                    stack.append((first_child, path))
                d = next_sibling

    def chunk_id(self, toc_index: int) -> tuple[int, int, int]:
        """A chunk's (id, index, type)."""
        start = self._chunk_ids_pos + 12 * toc_index
        raw = self._toc[start:start + 12]
        chunk_id, chunk_index = struct.unpack_from("<QH", raw)
        return chunk_id, chunk_index, raw[11]

    def chunk_offset_length(self, toc_index: int) -> tuple[int, int]:
        start = self._offsets_pos + 10 * toc_index
        raw = self._toc[start:start + 10]
        return int.from_bytes(raw[:5], "big"), int.from_bytes(raw[5:], "big")

    def compression_block(self, i: int) -> tuple[int, int, int, str]:
        """A block's (offset in .ucas data, compressed size, uncompressed size, method name)."""
        start = self._blocks_pos + 12 * i
        raw = self._toc[start:start + 12]
        offset = int.from_bytes(raw[0:5], "little")
        compressed = int.from_bytes(raw[5:8], "little")
        uncompressed = int.from_bytes(raw[8:11], "little")
        return offset, compressed, uncompressed, self.methods[raw[11]]

    def _cas_path(self, partition: int) -> str:
        base = os.path.splitext(self.path)[0]
        return f"{base}.ucas" if partition == 0 else f"{base}_s{partition}.ucas"

    def read_range(self, offset: int, length: int, files: dict[int, BinaryIO] | None = None) -> bytes:
        """Read length bytes of the container's uncompressed data, starting at offset.

        `files` caches open .ucas files across calls; the caller closes them.
        """
        own = files is None
        files = {} if files is None else files
        try:
            out = []
            first = offset // self.block_size
            last = (offset + length - 1) // self.block_size if length else first - 1
            for i in range(first, last + 1):
                block_offset, compressed, uncompressed, method = self.compression_block(i)
                partition = block_offset // self.partition_size if self.partition_count > 1 else 0
                if partition not in files:
                    files[partition] = open(self._cas_path(partition), "rb")
                f = files[partition]
                f.seek(block_offset - partition * self.partition_size)
                raw = f.read(align(compressed) if self.encrypted else compressed)
                if self.encrypted:
                    raw = aes_decrypt(raw, self.aes_key)
                out.append(decompress(method, raw[:compressed], uncompressed))
            data = b"".join(out)
            start = offset - first * self.block_size
            return data[start:start + length]
        finally:
            if own:
                for f in files.values():
                    f.close()

    def read(self, entry: IoStoreEntry, files: dict[int, BinaryIO] | None = None) -> bytes:
        return self.read_range(entry.offset, entry.length, files)

    def find(self, *patterns: str) -> list[IoStoreEntry]:
        """Entries whose path matches any of the fnmatch patterns."""
        return [e for e in self.entries if any(fnmatch.fnmatchcase(e.path, p) for p in patterns)]

    def extract(self, output: str | os.PathLike[str], entries: Iterable[IoStoreEntry] | None = None,
                overwrite: bool = True) -> None:
        """Write entries (all by default) under output, at their container paths."""
        entries = list(self.entries if entries is None else entries)
        logger.info("extracting %d files from %s to %s", len(entries), self.path, output)
        files: dict[int, BinaryIO] = {}
        try:
            for entry in entries:
                target = os.path.join(output, entry.path)
                if not overwrite and os.path.exists(target):
                    continue
                os.makedirs(os.path.dirname(target), exist_ok=True)
                logger.debug("extracting %s", entry.path)
                with open(target, "wb") as fout:
                    fout.write(self.read(entry, files))
        finally:
            for f in files.values():
                f.close()
