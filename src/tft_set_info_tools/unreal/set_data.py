"""Set data in the shape of CDragon's `cdragon/tft/<lang>.json`, built from client data assets.

Cooked assets omit fields that hold their default value, so a champion with
no starting mana or attack range stored gets 0 and 1 (melee).
"""

from __future__ import annotations

import collections
import copy
import logging
import re
import struct
from typing import Any

from tft_set_info_tools.unreal.assets import ExtractedFiles, TftAsset, icon_path, read_stats
from tft_set_info_tools.unreal.curves import Keys, evaluate, read_curve_table

logger = logging.getLogger(__name__)

COSTS = {"OneCost": 1, "TwoCost": 2, "ThreeCost": 3, "FourCost": 4, "FiveCost": 5,
         "SixCost": 6, "SevenCost": 7, "EightCost": 8}

STAT_KEYS = {
    "Armor": "armor",
    "AttackRange": "range",
    "AttackSpeed": "attackSpeed",
    "CritChance": "critChance",
    "CritDamage": "critMultiplier",
    "HealthMax": "hp",
    "MagicResist": "magicResist",
    "ManaMax": "mana",
    "ManaStarting": "initialMana",
}
CDRAGON_STAT_KEYS = ["armor", "attackSpeed", "critChance", "critMultiplier", "damage",
                     "hp", "initialMana", "magicResist", "mana", "range"]

# "(2) ...", "2) ..." or "(3<img .../>) ...", at the start of any line
TIER_PATTERN = re.compile(r"(?m)^\s*\(?(\d+)(?:<[^>]*>)*\)")
PLACEHOLDER = "???"
MAX_STAR_LEVEL = 4
AUTO_ATTACK_ROW = "AutoAttackDamage"


def _plain(text: str) -> bool:
    return ("<" not in text and "\n" not in text and "\r" not in text and len(text) <= 60
            and PLACEHOLDER not in text and not TIER_PATTERN.search(text))


def _name_and_desc(texts: list[str], fallback: str | None = None) -> tuple[str | None, str | None]:
    """Pick a name (the shortest plain text) and a description (the longest text)."""
    if not texts:
        return fallback, None
    desc = max(texts, key=len)
    # Names are short and aren't sentences; a lone text is a description.
    plain = [t for t in texts if _plain(t) and t != desc and not t.endswith(".")]
    if plain:
        name = min(plain, key=len)
    elif _plain(desc) and not desc.endswith("."):
        name = desc
    else:
        name = fallback
    return name, (None if desc == name else desc)


def _short_identifier(asset: TftAsset) -> str:
    return asset.identifier.rsplit(".", 1)[1] if asset.identifier else asset.api_name


def build_champion(asset: TftAsset, traits_by_package: dict[str, dict[str, Any]]) -> dict[str, Any]:
    texts = asset.texts
    name = texts[0] if texts else None
    rest = [t for t in texts[1:] if t != name]
    desc = max(rest, key=len) if rest else None
    ability_name = next((t for t in rest if _plain(t) and t != desc), None)
    stats: dict[str, Any] = {k: None for k in CDRAGON_STAT_KEYS}
    for stat, value in read_stats(asset.data).items():
        if stat in STAT_KEYS:
            stats[STAT_KEYS[stat]] = value
    if stats["armor"] is not None:
        if stats["initialMana"] is None:
            stats["initialMana"] = 0
        if stats["range"] is None:
            stats["range"] = 1
    return {
        "ability": {
            "desc": desc,
            "icon": asset.texture("SpellIcon"),
            "name": ability_name,
            "variables": [],
        },
        "apiName": asset.api_name,
        "characterName": _short_identifier(asset),
        "cost": next((COSTS[n] for n in asset.names if n in COSTS), None),
        "icon": asset.texture("_PC"),
        "name": name,
        "role": next((n for n in asset.names if n.startswith("DA_Role_")), None),
        "squareIcon": asset.texture("_TeamPlanner_Portrait"),
        "stats": stats,
        "tileIcon": asset.texture("_Mobile"),
        "traits": [traits_by_package[p]["name"] for p in asset.imports if p in traits_by_package],
    }


def build_trait(asset: TftAsset) -> dict[str, Any]:
    tier_texts = [t for t in asset.texts if TIER_PATTERN.search(t) and PLACEHOLDER not in t]
    tiers = sorted({int(n) for t in tier_texts for n in TIER_PATTERN.findall(t)})
    name, desc = _name_and_desc([t for t in asset.texts if not TIER_PATTERN.search(t)])
    if tier_texts:
        desc = "\n".join(([desc] if desc else []) + tier_texts)
    effects = [{"maxUnits": (tiers[i + 1] - 1 if i + 1 < len(tiers) else 25), "minUnits": n,
                "style": None, "variables": {}} for i, n in enumerate(tiers)]
    textures = asset.textures()
    return {
        "apiName": asset.api_name,
        "desc": desc,
        "effects": effects,
        "icon": icon_path(textures[0]) if textures else None,
        "name": name,
    }


def build_item(asset: TftAsset, traits_by_package: dict[str, dict[str, Any]],
               items_by_package: dict[str, TftAsset]) -> dict[str, Any]:
    name, desc = _name_and_desc(asset.texts, fallback=_short_identifier(asset))
    # Augments reference the items they grant, which aren't a recipe.
    components = [items_by_package[p].api_name for p in asset.imports
                  if asset.kind == "Item" and p in items_by_package and items_by_package[p].kind == "Item"]
    textures = asset.textures()
    return {
        "apiName": asset.api_name,
        "associatedTraits": [traits_by_package[p]["name"] for p in asset.imports if p in traits_by_package],
        "composition": components,
        "desc": desc,
        "effects": {},
        "from": None,
        "icon": icon_path(textures[0]) if textures else None,
        "id": None,
        "incompatibleTraits": [],
        "name": name,
        "tags": [n for n in asset.names if n.startswith(("Item.", "Augment."))],
        "unique": None,
    }


def latest_set(assets: list[TftAsset]) -> int | None:
    """The highest set number with champions."""
    numbers = [int(m.group(1)) for a in assets if a.kind == "Champion"
               for m in [re.match(r"/Set_(\d+)/", a.package)] if m]
    return max(numbers) if numbers else None


def build_tft_data(assets: list[TftAsset], set_number: int) -> dict[str, Any]:
    """CDragon-shaped data for one set.

    The set's `items` and `augments` lists split every item asset by kind.
    """
    prefix = f"/Set_{set_number}/"
    traits_by_package = {a.package: build_trait(a) for a in assets
                         if a.kind == "Trait" and a.package.startswith(prefix)}
    champions = [build_champion(a, traits_by_package) for a in assets
                 if a.kind == "Champion" and a.package.startswith(prefix)]
    items_by_package = {a.package: a for a in assets if a.kind in ("Item", "Augment")}
    items = [build_item(a, traits_by_package, items_by_package) for a in items_by_package.values()]
    champions.sort(key=lambda c: (c["cost"] or 0, c["apiName"]))
    traits = sorted(traits_by_package.values(), key=lambda t: t["apiName"])
    items.sort(key=lambda i: i["apiName"])
    by_kind = collections.defaultdict(list)
    for a in sorted(items_by_package.values(), key=lambda a: a.api_name):
        by_kind[a.kind].append(a.api_name)
    name = f"Set{set_number}"
    set_data = {"augments": by_kind["Augment"], "champions": champions, "items": by_kind["Item"],
                "mutator": f"TFTSet{set_number}", "name": name, "number": set_number, "traits": traits}
    return {
        "items": items,
        "setData": [set_data],
        "sets": {str(set_number): copy.deepcopy({"champions": champions, "name": name, "traits": traits})},
    }


def set_entry(data: dict[str, Any], set_number: int) -> dict[str, Any]:
    return next(s for s in data["setData"] if s["number"] == set_number)


def read_curve_tables(files: ExtractedFiles, set_number: int) -> dict[str, dict[str, Keys]]:
    """{folder: {row: keys}} for the set's curve tables, merged per folder."""
    tables: dict[str, dict[str, Keys]] = collections.defaultdict(dict)
    for path in files.find(f"*/Set_{set_number}/Content/*/CT_*.uasset"):
        if "UnlockCurve" in path:
            continue
        try:
            tables[path.rsplit("/", 1)[0]].update(read_curve_table(files.read(path)))
        except (ValueError, struct.error):
            logger.debug("skipping %s: not a table of curves", path)
    return tables


def _item_api_name(identifier: str, api_names: set[str], set_number: int) -> str | None:
    name = identifier.removesuffix(".uasset").split(".")[-1]
    for candidate in (name, "DA_" + name, "DA_" + re.sub(r"Emblem$", f"{set_number}_Emblem", name)):
        if candidate in api_names:
            return candidate
    return None


def enrich(files: ExtractedFiles, data: dict[str, Any], recipes: dict[str, list[str]],
           set_number: int) -> dict[str, int]:
    """Add curve-table values to the set's champions and traits, and recipes to items.

    A champion or trait takes the curve tables in its asset's folder, or the
    nearest one above it within its category folder. Returns how many of
    each were filled in.
    """
    s = set_entry(data, set_number)
    tables = read_curve_tables(files, set_number)
    content = f"/Set_{set_number}/Content/"

    def table_for(folder: str) -> dict[str, Keys] | None:
        while content in folder and "/" in folder.split(content, 1)[1]:
            if folder in tables:
                return tables[folder]
            folder = folder.rsplit("/", 1)[0]
        return None

    folders = {}
    for path in files.find(f"*/Set_{set_number}/Content/Champions/*/DA_*.uasset",
                           f"*/Set_{set_number}/Content/Traits/*/DA_*.uasset"):
        folder, file_name = path.rsplit("/", 1)
        folders[file_name.removesuffix(".uasset")] = folder
    counts: collections.Counter[str] = collections.Counter()
    for champion in s["champions"]:
        table = table_for(folders.get(champion["apiName"], ""))
        if not table:
            continue
        counts["champions"] += 1
        if AUTO_ATTACK_ROW in table:
            by_star = [evaluate(table[AUTO_ATTACK_ROW], x) for x in range(1, MAX_STAR_LEVEL + 1)]
            champion["stats"]["damage"], champion["stats"]["damageByStar"] = by_star[0], by_star
        champion["ability"]["variables"] = [
            {"name": k, "value": [evaluate(v, x) for x in range(1, MAX_STAR_LEVEL + 1)]}
            for k, v in table.items() if k != AUTO_ATTACK_ROW
        ]
    for trait in s["traits"]:
        table = table_for(folders.get(trait["apiName"], ""))
        if not table:
            continue
        counts["traits"] += 1
        for i, effect in enumerate(trait["effects"], 1):
            effect["variables"] = {k: evaluate(v, i) for k, v in table.items()}
    by_api = {item["apiName"]: item for item in data["items"]}
    for identifier, components in recipes.items():
        api_name = _item_api_name(identifier, set(by_api), set_number)
        if len(components) == 2 and api_name:
            by_api[api_name]["composition"] = ["DA_Component_" + c for c in components]
            counts["recipes"] += 1
    return dict(counts)
