"""TFT data assets read from files extracted from the client's containers.

Champions, traits, items and augments each have a data asset (`DA_*.uasset`).
Their properties are unversioned, so what's read here is what they keep in
clear: names, imports, localized text, and stats stored as name/value pairs.
"""

from __future__ import annotations

import fnmatch
import logging
import os
import re
import struct
from pathlib import Path

from tft_set_info_tools.unreal.locres import LocresFile
from tft_set_info_tools.unreal.textkeys import find_text_references
from tft_set_info_tools.unreal.zen import ZenPackage

logger = logging.getLogger(__name__)

KINDS = ("Champion", "Trait", "Item", "Augment")

# A stat stored as an FString name, then an index, two equal negative ints and a float value.
STAT_PATTERN = re.compile(rb"(?s)([\x02-\x40])\x00\x00\x00([A-Za-z][A-Za-z0-9]*)\x00"
                          rb"\x01\x00\x00\x00.{8}(.{4})(.{4})(.{4})")
COMPONENT_PATTERN = re.compile(r"^/Item_Shared/Item/Component_(\w+)/DA_Component_\1$")


class ExtractedFiles:
    """Files extracted from the client's containers, under one or more folders.

    Each folder is an extraction output, holding files at their container
    paths (`TFT/Plugins/GameFeatures/Set_19/...`). Where folders hold the
    same path, the first folder's file is used.
    """

    def __init__(self, *roots: str | os.PathLike[str]) -> None:
        self.files: dict[str, Path] = {}
        for root in map(Path, roots):
            if not root.is_dir():
                raise NotADirectoryError(f"not a folder: {root}")
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    self.files.setdefault(path.relative_to(root).as_posix(), path)

    def find(self, *patterns: str) -> list[str]:
        return [p for p in self.files if any(fnmatch.fnmatchcase(p, pattern) for pattern in patterns)]

    def read(self, path: str) -> bytes:
        return self.files[path].read_bytes()


def read_strings(files: ExtractedFiles, locale: str = "en-US") -> LocresFile:
    """Merge the client's .locres tables for a locale."""
    paths = sorted(files.find(f"*/Content/Localization/*/{locale}/*.locres"))
    if not paths:
        raise FileNotFoundError(f"no {locale} .locres files among the extracted files")
    strings = LocresFile()
    for path in paths:
        strings.update(LocresFile(files.read(path)))
    return strings


def package_path(file_path: str) -> str:
    """The package path references use for a file.

    `TFT/Plugins/GameFeatures/Set_19/Content/A/DA_X.uasset` -> `/Set_19/A/DA_X`
    """
    path = file_path.rsplit(".", 1)[0]
    m = re.match(r"(?:[^/]+/)*?Plugins/(?:GameFeatures/)?([^/]+)/Content/(.*)", path)
    if m:
        return f"/{m.group(1)}/{m.group(2)}"
    m = re.match(r"[^/]+/Content/(.*)", path)
    if m:
        return f"/Game/{m.group(1)}"
    return "/" + path


def icon_path(package: str) -> str | None:
    """The lowercase path CDragon exports a texture package to, as a .png."""
    m = re.match(r"/([^/]+)/(.*)", package)
    if not m:
        return None
    plugin, rest = m.groups()
    if plugin == "Game":
        return f"tft/content/{rest}.png".lower()
    return f"tft/plugins/gamefeatures/{plugin}/content/{rest}.png".lower()


def read_stats(data: bytes) -> dict[str, float]:
    """{stat name: value} for the stats stored as name/value pairs."""
    stats: dict[str, float] = {}
    for m in STAT_PATTERN.finditer(data):
        n, name = m.group(1)[0], m.group(2).decode()
        if len(name) + 1 != n:
            continue
        a, = struct.unpack("<i", m.group(3))
        b, = struct.unpack("<i", m.group(4))
        if a != b or a >= 0:
            continue
        value, = struct.unpack("<f", m.group(5))
        # Curve-based stats have other data here, which reads as a tiny or huge float.
        if value == value and (value == 0 or 1e-4 <= value < 100000):
            stats.setdefault(name, round(value, 4))
    return stats


def read_recipe(data: bytes) -> list[str]:
    """The components an item asset references, by short name, once per use."""
    package = ZenPackage(data)
    components = []
    for i, name in enumerate(package.names):
        m = COMPONENT_PATTERN.match(name)
        if not m:
            continue
        asset = package.names.index(f"DA_Component_{m.group(1)}")
        reference = struct.pack("<IIII", i, 0, asset, 0)
        components += [m.group(1)] * package.body.count(reference)
    return sorted(components)


def scan_recipes(files: ExtractedFiles) -> dict[str, list[str]]:
    """{item api name: [component, ...]} for items that name components.

    Keyed by the asset each recipe is read from, since identifiers can use a
    trait's display name (`Identifier.Item.SlayerEmblem` in `DA_Mosher19_Emblem`).
    """
    recipes = {}
    for path in files.find("*/DA_*.uasset"):
        if "/ItemCombinations/" in path or "/DA_Component_" in path:
            continue
        if "Item" not in path and "Emblem" not in path:
            continue
        data = files.read(path)
        if b"Component_" not in data:
            continue
        try:
            recipe = read_recipe(data)
        except (struct.error, UnicodeDecodeError, ValueError):
            continue
        if recipe:
            recipes[package_path(path).rsplit("/", 1)[1]] = recipe
    return recipes


# Data assets carry this component even when its identifier was left empty.
IDENTIFIER_COMPONENT = "IdentifierComponent"


def _kind(identifier: str | None, names: list[str]) -> str | None:
    """The asset's kind from its `Identifier.<Kind>.<Name>` tag.

    A data asset whose identifier was left empty (Set 19's Prodigy Emblem)
    is typed by its gameplay tags instead. Augment tags are checked first,
    since augments can also carry the tags of items they grant.
    """
    parts = (identifier or "").split(".")
    if len(parts) >= 3:
        return parts[1]
    if IDENTIFIER_COMPONENT not in names:
        return None
    if any(n.startswith("Augment.") for n in names):
        return "Augment"
    if any(n.startswith("Item.Equippable.") for n in names):
        return "Item"
    return None


class TftAsset:
    """A champion, trait, item or augment data asset."""

    def __init__(self, path: str, data: bytes, strings: LocresFile | None = None) -> None:
        self.path = path
        self.package = package_path(path)
        self.api_name = self.package.rsplit("/", 1)[1]
        zen = ZenPackage(data)
        self.names = zen.names
        self.imports = zen.imported_packages
        self.identifier = zen.identifier()
        self.kind = _kind(self.identifier, zen.names)
        self.texts = []
        for ref in find_text_references(data):
            text = strings.get(ref.key, ref.namespace) if strings is not None else None
            self.texts.append(ref.source if text is None else text)
        self.data = data

    def textures(self) -> list[str]:
        return [n for n in self.names if n.startswith("/") and "/T_" in n]

    def texture(self, suffix: str) -> str | None:
        for t in self.textures():
            if t.lower().endswith(suffix.lower()):
                return icon_path(t)
        return None


def load_assets(files: ExtractedFiles, strings: LocresFile | None = None) -> list[TftAsset]:
    """Every champion, trait, item and augment data asset among the files."""
    paths = files.find("*/DA_*.uasset")
    logger.info("reading %d data assets", len(paths))
    assets = []
    for path in paths:
        try:
            asset = TftAsset(path, files.read(path), strings)
        except (struct.error, UnicodeDecodeError, ValueError):
            logger.debug("skipping %s: not a readable zen package", path)
            continue
        if asset.kind in KINDS:
            assets.append(asset)
    # Package paths are case-insensitive, and references don't always match a folder's case.
    canonical = {a.package.lower(): a.package for a in assets}
    for asset in assets:
        asset.imports = [canonical.get(i.lower(), i) for i in asset.imports]
    return assets
