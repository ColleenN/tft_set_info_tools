"""Decryption, decompression and string decoding shared by the container readers."""

from __future__ import annotations

import gzip
import struct
import zlib

AES_BLOCK_SIZE = 16


def parse_aes_key(key: str | bytes) -> bytes:
    """Parse an AES-256 key given as hex, with or without a 0x prefix."""
    if isinstance(key, bytes):
        raw = key
    else:
        key = key.strip()
        if key[:2].lower() == "0x":
            key = key[2:]
        raw = bytes.fromhex(key)
    if len(raw) != 32:
        raise ValueError(f"AES key must be 32 bytes, got {len(raw)}")
    return raw


def aes_decrypt(data: bytes, key: bytes) -> bytes:
    """Decrypt with AES-256-ECB, as Unreal does for pak and IoStore data."""
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    except ImportError as exc:
        raise ImportError(
            "decrypting Unreal containers needs cryptography: pip install tft_set_info_tools[unreal]"
        ) from exc
    if len(data) % AES_BLOCK_SIZE:
        raise ValueError("encrypted data must be a multiple of 16 bytes")
    decryptor = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    return decryptor.update(data) + decryptor.finalize()


def align(n: int, alignment: int = AES_BLOCK_SIZE) -> int:
    return (n + alignment - 1) // alignment * alignment


def read_fstring(buf: bytes, pos: int) -> tuple[str, int]:
    """Read an Unreal FString at pos; return it and the position after it.

    A negative length counts UTF-16 characters, a positive one bytes.
    """
    n, = struct.unpack_from("<i", buf, pos)
    pos += 4
    if n == 0:
        return "", pos
    if n < 0:
        end = pos - 2 * n
        return buf[pos:end].decode("utf-16-le").rstrip("\0"), end
    return buf[pos:pos + n].decode("utf-8", "replace").rstrip("\0"), pos + n


def decompress(method: str, data: bytes, size: int) -> bytes:
    """Decompress one block, given Unreal's name for its compression method."""
    method = method.lower()
    if method == "none":
        return data[:size]
    if method == "oodle":
        try:
            import ooz
        except ImportError as exc:
            raise ImportError(
                "Oodle decompression needs pyooz: pip install tft_set_info_tools[unreal]"
            ) from exc
        return ooz.decompress(data, size)
    if method == "zlib":
        return zlib.decompress(data)
    if method == "gzip":
        return gzip.decompress(data)
    if method == "zstd":
        import pyzstd

        return pyzstd.decompress(data)
    raise ValueError(f"unsupported compression method: {method}")
