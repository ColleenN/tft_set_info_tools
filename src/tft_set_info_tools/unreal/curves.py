"""Curve tables (`CT_*.uasset`): per-row keys that ability, trait and stat values scale along."""

from __future__ import annotations

import struct

from tft_set_info_tools.unreal.zen import ZenPackage

Keys = list[tuple[float, float]]

PACKAGE_TAG = bytes.fromhex("c1832a9e")
MAX_KEYS = 256


def read_curve_table(data: bytes) -> dict[str, Keys]:
    """Return {row name: [(x, y), ...]}.

    Raises ValueError when the layout doesn't parse cleanly up to the
    package's closing tag, which is how tables with another row type show up.
    """
    package = ZenPackage(data)
    body = package.body
    rows_n, = struct.unpack_from("<i", body, 6)
    pos = 11
    rows = {}
    for _ in range(rows_n):
        index, number = struct.unpack_from("<II", body, pos)
        pos += 8
        name = package.names[index] + (f"_{number - 1}" if number else "")
        pos += 3  # unversioned struct header
        n, = struct.unpack_from("<i", body, pos)
        pos += 4
        if not 0 <= n <= MAX_KEYS:
            raise ValueError(f"bad key count {n}")
        keys = [struct.unpack_from("<ff", body, pos + 8 * i) for i in range(n)]
        pos += 8 * n
        pos += 4 + 2  # default value, pre and post extrapolation
        rows[name] = [(round(x, 4), round(y, 4)) for x, y in keys]
    if body[pos:pos + 4] != PACKAGE_TAG:
        raise ValueError(f"did not end at the package tag (offset {pos} of {len(body)})")
    return rows


def evaluate(keys: Keys, x: float) -> float:
    """Interpolate linearly between keys, clamped at both ends."""
    if x <= keys[0][0]:
        return keys[0][1]
    for (x0, y0), (x1, y1) in zip(keys, keys[1:]):
        if x <= x1:
            return round(y0 + (y1 - y0) * (x - x0) / (x1 - x0), 4)
    return keys[-1][1]
