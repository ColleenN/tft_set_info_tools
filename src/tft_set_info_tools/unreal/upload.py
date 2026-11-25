"""Turn extracted client files into a gzipped en_us.json capture and its metadata, ready to upload.

The capture stands in for a CDragon export while CDragon has none for the
client, so it goes through the same loader as mirrored CDragon captures.
"""

from __future__ import annotations

import datetime
import gzip
import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tft_set_info_tools.schema.vocab import ItemType
from tft_set_info_tools.unreal.assets import ExtractedFiles, load_assets, read_strings, scan_recipes
from tft_set_info_tools.unreal.set_data import build_tft_data, enrich, latest_set, set_entry
from tft_set_info_tools.unreal.zen import ZenPackage

logger = logging.getLogger(__name__)

BUILD_PATTERN = re.compile(r"^[A-Za-z]+-(\d+\.\d+)\.\d+\.(\d+)$")
MIRROR_TARGET = "manual-pbe-client-extract"
CHANNEL = "pbe"
# Client tags that map straight to the CDragon codes items are classified by. These
# codes are added to an item's tags whatever the rest of its tags translate to.
TAG_CODES = {
    "Item.Equippable.Item.Tacticians": ItemType.TAC_ITEM.type_hash,
    "Item.Equippable.Item.ThiefsGloves": ItemType.TG_ITEM.type_hash,
}
UNIQUE_TRAIT_EFFECTS = [{"maxUnits": 25, "minUnits": 1, "style": 6, "variables": {}}]


class ConversionError(Exception):
    """The extracted data needs a decision by hand before it can be uploaded."""


@dataclass(frozen=True)
class Upload:
    capture: Path
    metadata: Path
    fields: dict[str, str]


def cdragon_version(build: str) -> str:
    """`rls-19.1.0.6018196` -> `19.1.6018196+rls-19.1.0.6018196`, CDragon's version format."""
    m = BUILD_PATTERN.match(build)
    if not m:
        raise ValueError(f"not a client build like rls-19.1.0.6018196: {build}")
    return f"{m.group(1)}.{m.group(2)}+{build}"


def shop_units(files: ExtractedFiles, set_number: int) -> set[str]:
    """The champions in the set's shop pool, from the client's champions table."""
    paths = files.find(f"*/DT_{set_number}_ChampionsTable.uasset")
    if not paths:
        raise FileNotFoundError(f"DT_{set_number}_ChampionsTable.uasset is not among the extracted files")
    names = ZenPackage(files.read(paths[0])).names
    return {n for n in names if "/" not in n and n.startswith("DA_")}


def trait_styles(effects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Breakpoint styles as CDragon numbers them: 1 for the first, 4 for the last, 3 between.

    A trait with no breakpoints is unique, and gets one breakpoint at a single unit.
    """
    if not effects:
        return [dict(e) for e in UNIQUE_TRAIT_EFFECTS]
    for i, effect in enumerate(effects):
        effect["style"] = 4 if i == len(effects) - 1 else 1 if i == 0 else 3
    return effects


def apply_previous(data: dict[str, Any], previous: dict[str, Any], previous_raw: dict[str, Any],
                   set_number: int) -> None:
    """Carry over what was decided by hand for the previous upload.

    Item tags were translated to CDragon's tag codes by hand, so they're
    reused for items whose client tags haven't changed since. The set's split
    into items and augments is reused too. Items needing either decision
    again raise ConversionError.
    """
    previous_items = {x["apiName"]: x for x in previous["items"]}
    previous_raw_items = {x["apiName"]: x for x in previous_raw["items"]}
    changed = []
    for item in data["items"]:
        old = previous_items.get(item["apiName"])
        raw = previous_raw_items.get(item["apiName"])
        if old and raw and raw["tags"] == item["tags"]:
            item["tags"], item["incompatibleTraits"] = old["tags"], old["incompatibleTraits"]
        else:
            changed.append(item["apiName"])
    if changed:
        raise ConversionError(f"items whose tags need translating by hand: {sorted(changed)}")

    names = {item["apiName"] for item in data["items"]}
    previous_set = set_entry(previous, set_number)
    s = set_entry(data, set_number)
    s["items"] = [n for n in previous_set["items"] if n in names]
    s["augments"] = [n for n in previous_set["augments"] if n in names]
    new = names - set(s["items"]) - set(s["augments"])
    if new:
        raise ConversionError(f"items new since the previous upload need an items/augments split: {sorted(new)}")


def add_tag_codes(data: dict[str, Any], client_tags: dict[str, list[str]]) -> None:
    """Add the CDragon code of each client tag in TAG_CODES that an item carries."""
    for item in data["items"]:
        for tag in client_tags[item["apiName"]]:
            code = TAG_CODES.get(tag)
            if code and code not in item["tags"]:
                item["tags"] = item["tags"] + [code]


def finish(data: dict[str, Any], shop: set[str], set_number: int, build: str) -> None:
    """The loader-facing fixes that don't depend on a previous upload."""
    for item in data["items"]:
        item["unique"] = bool(item["unique"])
    for s in [data["sets"][str(set_number)], set_entry(data, set_number)]:
        for champion in s["champions"]:
            champion["shopUnit"] = champion["apiName"] in shop
    for trait in set_entry(data, set_number)["traits"]:
        trait["effects"] = trait_styles(trait["effects"])
    data["build"] = build


def write_upload(data: dict[str, Any], output: str | os.PathLike[str], build: str, set_number: int,
                 locale: str = "en-US") -> Upload:
    """Write `<timestamp>_<locale>.json.gz` and `metadata_<timestamp>.json` into `output`."""
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    stamp, captured_at = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y-%m-%dT%H:%M:%SZ")
    raw = json.dumps(data, ensure_ascii=False).encode()
    fields = {
        "mirror-target": MIRROR_TARGET,
        "source-url": f"manual:tft-{CHANNEL}-client-extract-set{set_number}",
        "captured-at": captured_at,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size-bytes": str(len(raw)),
        "channel": CHANNEL,
        "cdragon-version": cdragon_version(build),
        "cdragon-status": f"{captured_at} done",
    }
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    capture = output / f"{stamp}_{locale.replace('-', '_').lower()}.json.gz"
    capture.write_bytes(gzip.compress(raw, mtime=0))
    metadata = output / f"metadata_{stamp}.json"
    metadata.write_text(json.dumps(fields, indent=1), encoding="utf-8")
    return Upload(capture, metadata, fields)


def read_json(path: str | os.PathLike[str]) -> Any:
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)


def convert(roots: list[str | os.PathLike[str]], build: str, output: str | os.PathLike[str], *,
            set_number: int | None = None, locale: str = "en-US",
            previous: str | os.PathLike[str] | None = None, previous_raw: str | os.PathLike[str] | None = None,
            raw_output: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Build an upload from folders of extracted files; return a summary of it."""
    cdragon_version(build)
    if (previous is None) != (previous_raw is None):
        raise ValueError("--previous and --previous-raw go together")
    files = ExtractedFiles(*roots)
    assets = load_assets(files, read_strings(files, locale))
    if set_number is None:
        set_number = latest_set(assets)
        if set_number is None:
            raise ConversionError("no set's champions are among the extracted files")
    data = build_tft_data(assets, set_number)
    if not set_entry(data, set_number)["champions"]:
        raise ConversionError(f"no Set {set_number} champions are among the extracted files")
    counts = enrich(files, data, scan_recipes(files), set_number)
    if raw_output:
        Path(raw_output).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    client_tags = {item["apiName"]: list(item["tags"]) for item in data["items"]}
    if previous is not None and previous_raw is not None:
        apply_previous(data, read_json(previous), read_json(previous_raw), set_number)
    else:
        logger.warning("no previous upload given: item tags stay as the client's, and items split by asset kind")
    add_tag_codes(data, client_tags)
    shop = shop_units(files, set_number)
    finish(data, shop, set_number, build)
    upload = write_upload(data, output, build, set_number, locale)
    return {"file": upload.capture.name, "metadata": upload.metadata.name, **upload.fields,
            "set": set_number, "shop_units": len(shop), **{f"enriched_{k}": v for k, v in counts.items()}}
