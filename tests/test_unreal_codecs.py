import zlib

import pytest

from tests.unreal_builders import KEY, encrypt, fstring
from tft_set_info_tools.unreal.codecs import aes_decrypt, align, decompress, parse_aes_key, read_fstring

BIG = bytes(i * 7 % 251 for i in range(5000))

# 990 bytes of PLAINTEXT, compressed with ooz's Kraken compressor at level 4
KRAKEN_BLOCK = bytes.fromhex(
    "8c060000728800705465616d6669676800004074205461637469637320736574"
    "20646174612c207061636b65642077697468204f6f646c65204b72616b656e2e"
    "203031323334353637383972616b656e2e203700000bff3d3d3d3d3d3d3d3d3d"
    "fc0000020f1e00000c2c25252525252525252525ff255051"
)


def make_plaintext() -> bytes:
    line = b"Teamfight Tactics set data, packed with Oodle Kraken. "
    out = b""
    i = 0
    while len(out) + len(line) <= 1000:
        out += line + str(i % 10).encode()
        i += 1
    return out


PLAINTEXT = make_plaintext()


def test_parse_aes_key_accepts_hex_with_or_without_prefix():
    assert parse_aes_key("0x" + KEY.hex().upper()) == KEY
    assert parse_aes_key(f" {KEY.hex()} ") == KEY
    assert parse_aes_key(KEY) == KEY


def test_parse_aes_key_wants_32_bytes():
    with pytest.raises(ValueError, match="32 bytes, got 16"):
        parse_aes_key("00" * 16)


def test_aes_round_trip():
    assert aes_decrypt(encrypt(b"x" * 32, KEY), KEY) == b"x" * 32
    with pytest.raises(ValueError, match="multiple of 16"):
        aes_decrypt(b"x" * 15, KEY)


def test_align():
    assert [align(0), align(1), align(16), align(17)] == [0, 16, 16, 32]


@pytest.mark.parametrize("utf16", [False, True])
def test_read_fstring(utf16):
    buf = b"??" + fstring("Kalista", utf16) + b"!"
    value, pos = read_fstring(buf, 2)
    assert value == "Kalista"
    assert buf[pos:] == b"!"


def test_read_empty_fstring():
    assert read_fstring(fstring(""), 0) == ("", 4)


def test_decompress_none_and_zlib():
    assert decompress("None", b"abcdef", 3) == b"abc"
    assert decompress("Zlib", zlib.compress(BIG), len(BIG)) == BIG


def test_decompress_oodle():
    assert decompress("Oodle", KRAKEN_BLOCK, len(PLAINTEXT)) == PLAINTEXT


def test_decompress_oodle_with_the_wrong_size():
    with pytest.raises(RuntimeError):
        decompress("Oodle", KRAKEN_BLOCK, 10)


def test_decompress_unknown_method():
    with pytest.raises(ValueError, match="unsupported compression method: lz4"):
        decompress("LZ4", b"", 0)
