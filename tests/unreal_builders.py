"""Writers for small Unreal files and the pieces they're made of."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from tft_set_info_tools.unreal.codecs import align

KEY = bytes(range(32))
PAK_METHODS = ["Zlib", "Oodle"]
INVALID = 0xFFFFFFFF


def encrypt(data: bytes, key: bytes) -> bytes:
    padded = data + b"\0" * (align(len(data)) - len(data))
    encryptor = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    return encryptor.update(padded) + encryptor.finalize()


def fstring(s: str, utf16: bool = False) -> bytes:
    if not s:
        return struct.pack("<i", 0)
    if utf16:
        raw = (s + "\0").encode("utf-16-le")
        return struct.pack("<i", -(len(raw) // 2)) + raw
    raw = (s + "\0").encode()
    return struct.pack("<i", len(raw)) + raw


@dataclass
class PakSpec:
    """A file to put in a pak.

    `blocks` gives already-compressed blocks, for methods the test can't
    compress itself (Oodle).
    """

    path: str
    data: bytes
    method: str = "None"
    encrypted: bool = False
    encoded: bool = True
    blocks: list[bytes] | None = None


def _pak_blocks(spec: PakSpec, block_size: int) -> list[bytes]:
    if spec.blocks is not None:
        return spec.blocks
    if spec.method == "Zlib":
        return [zlib.compress(spec.data[i:i + block_size]) for i in range(0, len(spec.data), block_size)]
    return [spec.data]


def build_pak(path: Path, files: list[PakSpec], *, key: bytes | None = None, encrypt_index: bool = False,
              block_size: int = 2048, mount_point: str = "../../../", version: int = 11) -> None:
    out = bytearray()
    encoded = bytearray()
    full = bytearray()
    full_count = 0
    locations: list[tuple[str, int]] = []

    for spec in files:
        method = 0 if spec.method == "None" else PAK_METHODS.index(spec.method) + 1
        blocks = _pak_blocks(spec, block_size)
        on_disk = [encrypt(b, key) if spec.encrypted else b for b in blocks]
        size = sum(len(b) for b in on_disk) if method else len(spec.data)
        offset = len(out)
        block_count = len(blocks) if method else 0

        header_size = 8 * 3 + 4 + 20 + 1 + 4
        if method:
            header_size += 4 + 16 * block_count
        ranges = []
        start = header_size
        for b in on_disk:
            ranges.append((start, start + len(b)))
            start += len(b)
        entry_block_size = block_size if block_count > 1 else len(spec.data)

        serialized = struct.pack("<qqqI", offset, size, len(spec.data), method) + b"\0" * 20
        if method:
            serialized += struct.pack("<I", block_count)
            for s, e in ranges:
                serialized += struct.pack("<qq", s, e)
        serialized += struct.pack("<BI", int(spec.encrypted), entry_block_size)
        out += serialized + b"".join(on_disk)

        if spec.encoded:
            location = len(encoded)
            value = (block_size >> 11) if method else 0
            value |= block_count << 6
            value |= int(spec.encrypted) << 22
            value |= method << 23
            value |= (1 << 31) | (1 << 30) | (1 << 29)
            encoded += struct.pack("<III", value, offset, len(spec.data))
            if method:
                encoded += struct.pack("<I", size)
            if block_count > 1 or (block_count == 1 and spec.encrypted):
                for b in blocks:
                    encoded += struct.pack("<I", len(b))
        else:
            full += serialized
            full_count += 1
            location = -full_count
        locations.append((spec.path, location))

    directories: dict[str, list[tuple[str, int]]] = {}
    for file_path, location in locations:
        dirname, _, name = file_path.rpartition("/")
        directories.setdefault(f"/{dirname}/" if dirname else "/", []).append((name, location))
    dir_index = struct.pack("<i", len(directories))
    for dirname, entries in directories.items():
        dir_index += fstring(dirname) + struct.pack("<i", len(entries))
        for name, location in entries:
            dir_index += fstring(name) + struct.pack("<i", location)
    if encrypt_index:
        dir_index = encrypt(dir_index, key)
    dir_offset = len(out)
    out += dir_index

    index = fstring(mount_point) + struct.pack("<iQ", len(files), 0)
    index += struct.pack("<I", 0)
    index += struct.pack("<IQQ", 1, dir_offset, len(dir_index)) + b"\0" * 20
    index += struct.pack("<i", len(encoded)) + encoded
    index += struct.pack("<i", full_count) + full
    if encrypt_index:
        index = encrypt(index, key)
    index_offset = len(out)
    out += index

    names = PAK_METHODS + [""] * (5 - len(PAK_METHODS))
    out += b"\0" * 16 + struct.pack("<BIiQQ", int(encrypt_index), 0x5A6F12E1, version, index_offset, len(index))
    out += b"\0" * 20 + b"".join(n.encode().ljust(32, b"\0") for n in names)
    path.write_bytes(bytes(out))


def _directory_index(paths: list[str], mount_point: str) -> bytes:
    dirs = [[INVALID, INVALID, INVALID, INVALID]]
    dir_ids = {"": 0}
    files: list[list[int]] = []
    strings: list[str] = []

    def string_id(s: str) -> int:
        if s not in strings:
            strings.append(s)
        return strings.index(s)

    for toc_index, file_path in enumerate(paths):
        parent = 0
        *parts, name = file_path.split("/")
        for depth in range(len(parts)):
            key = "/".join(parts[:depth + 1])
            if key not in dir_ids:
                dir_ids[key] = len(dirs)
                dirs.append([string_id(parts[depth]), INVALID, dirs[parent][1], INVALID])
                dirs[parent][1] = dir_ids[key]
            parent = dir_ids[key]
        files.append([string_id(name), dirs[parent][3], toc_index])
        dirs[parent][3] = len(files) - 1

    buf = fstring(mount_point) + struct.pack("<i", len(dirs))
    buf += b"".join(struct.pack("<4I", *d) for d in dirs)
    buf += struct.pack("<i", len(files)) + b"".join(struct.pack("<3I", *f) for f in files)
    buf += struct.pack("<i", len(strings)) + b"".join(fstring(s) for s in strings)
    return buf


def build_iostore(utoc: Path, files: list[tuple[str, bytes]], *, key: bytes | None = None,
                  compress: bool = True, block_size: int = 64, partition_size: int | None = None,
                  mount_point: str = "../../../") -> None:
    """Write utoc and its .ucas partitions; files are packed back to back."""
    stream = b"".join(data for _, data in files)
    offsets = []
    pos = 0
    for _, data in files:
        offsets.append((pos, len(data)))
        pos += len(data)

    partitions = [bytearray()]
    block_entries = []
    for i in range(0, len(stream), block_size):
        chunk = stream[i:i + block_size]
        payload = zlib.compress(chunk) if compress else chunk
        on_disk = encrypt(payload, key) if key else payload
        if partition_size and len(partitions[-1]) + len(on_disk) > partition_size:
            partitions.append(bytearray())
        offset = (len(partitions) - 1) * (partition_size or 0) + len(partitions[-1])
        partitions[-1] += on_disk
        block_entries.append(
            offset.to_bytes(5, "little") + len(payload).to_bytes(3, "little")
            + len(chunk).to_bytes(3, "little") + bytes([1 if compress else 0])
        )

    dir_index = _directory_index([p for p, _ in files], mount_point)
    if key:
        dir_index = encrypt(dir_index, key)

    flags = 8 | (1 if compress else 0) | (2 if key else 0)
    header = bytearray(144)
    header[:16] = b"-==--==--==--==-"
    header[16] = 8
    struct.pack_into("<9I", header, 20, 144, len(files), len(block_entries), 12, 1, 32,
                     block_size, len(dir_index), len(partitions))
    struct.pack_into("<Q", header, 56, 0x1234)
    header[80] = flags
    struct.pack_into("<Q", header, 88, partition_size or 0xFFFFFFFFFFFFFFFF)

    toc = bytes(header)
    toc += b"".join(struct.pack("<QHBB", i + 1, 0, 0, 2) for i in range(len(files)))
    toc += b"".join(o.to_bytes(5, "big") + n.to_bytes(5, "big") for o, n in offsets)
    toc += b"".join(block_entries)
    toc += b"Zlib".ljust(32, b"\0")
    toc += dir_index
    utoc.write_bytes(toc)

    base = utoc.with_suffix("")
    for i, data in enumerate(partitions):
        suffix = ".ucas" if i == 0 else f"_s{i}.ucas"
        Path(f"{base}{suffix}").write_bytes(bytes(data))


LOCRES_MAGIC = bytes.fromhex("0e147475674a03fc4a15909dc3377f1b")


def _locres_string(s: str) -> bytes:
    return fstring(s, utf16=not s.isascii())


def build_locres(entries: dict[str, dict[str, str]], version: int = 3) -> bytes:
    """A .locres file; version 0 is the legacy layout without the magic."""
    if version == 0:
        out = struct.pack("<I", len(entries))
        for namespace, table in entries.items():
            out += _locres_string(namespace) + struct.pack("<I", len(table))
            for key, value in table.items():
                out += _locres_string(key) + struct.pack("<I", 0) + _locres_string(value)
        return out

    strings: list[str] = []
    body = b""
    if version >= 2:
        body += struct.pack("<I", sum(len(t) for t in entries.values()))
    body += struct.pack("<I", len(entries))
    for namespace, table in entries.items():
        if version >= 2:
            body += struct.pack("<I", 0)
        body += _locres_string(namespace) + struct.pack("<I", len(table))
        for key, value in table.items():
            if value not in strings:
                strings.append(value)
            if version >= 2:
                body += struct.pack("<I", 0)
            body += _locres_string(key) + struct.pack("<Ii", 0, strings.index(value))

    head = LOCRES_MAGIC + bytes([version])
    array_offset = len(head) + 8 + len(body)
    array = struct.pack("<I", len(strings))
    for s in strings:
        array += _locres_string(s) + (struct.pack("<i", 1) if version >= 2 else b"")
    return head + struct.pack("<q", array_offset) + body + array
