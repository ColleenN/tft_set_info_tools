"""Writers for small Unreal files and the pieces they're made of."""

from __future__ import annotations

import struct

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from tft_set_info_tools.unreal.codecs import align

KEY = bytes(range(32))


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
