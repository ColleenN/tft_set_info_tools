"""Readers for the Unreal Engine files that ship with the standalone TFT client."""

from __future__ import annotations

import os

from tft_set_info_tools.unreal.iostore import IoStoreEntry, IoStoreReader
from tft_set_info_tools.unreal.pak import PakEntry, PakFile

__all__ = ["IoStoreEntry", "IoStoreReader", "PakEntry", "PakFile", "open_container"]


def open_container(path: str | os.PathLike[str], aes_key: bytes | None = None) -> PakFile | IoStoreReader:
    """Open a .pak file, or an IoStore container given its .utoc or .ucas file."""
    base, ext = os.path.splitext(os.fspath(path))
    ext = ext.lower()
    if ext == ".pak":
        return PakFile(path, aes_key=aes_key)
    if ext in (".utoc", ".ucas"):
        return IoStoreReader(base + ".utoc", aes_key=aes_key)
    raise ValueError(f"not an Unreal container: {path}")
