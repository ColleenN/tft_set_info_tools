"""Seed CSV row generators.

trait_tiers/items/units/unit_innate_traits port the column schemas and
filtering logic from the legacy tft_tools seed_gen package byte-for-byte
(modulo reading from TFTSetData instead of the old TFTSetBlob). augments has
no legacy precedent — that seed type didn't exist in the old package — so its
schema below is new.
"""

from __future__ import annotations

from json import dumps
from typing import Callable

from tft_set_info_tools.set_data import AugmentTier, TFTSetData


def _camel_to_snake(value: str) -> str:
    result = ""
    for char in value:
        if char.isupper():
            result += "_" + char.lower()
        else:
            result += char
    return result


_ICON_STYLE_MAP = {
    1: "BRONZE",
    3: "SILVER",
    4: "LEGENDARY",
    5: "GOLD",
    6: "PRISMATIC",
}

_SUMMON_UNITS = {
    "TFT_TrainingDummy",
    "TFT_BlueGolem",
    "TFT14_SummonLevel2",
    "TFT14_SummonLevel4",
}

_EQUIPPABLE_ITEM_HASHES = {
    "component",
    "{27557a09}",
    "{44ace175}",
    "{d304f83b}",
    "{7ea41d13}",
    "{6ef5c598}",
    "{ebcd1bac}",
    "{eda79d90}",
    "{218b53a5}",
    "{a3eeef8b}",
    "{b73b012f}",
}

_NON_EQUIPPABLE_ITEM_HASHES = {
    "Consumable",
    "TFT_Consumable_ItemRemover",
    "TFT_Consumable_ItemReroller",
    "{b4fe26c6}",
    "{fb608fdb}",
    "{56b1acc8}",
}

_COMPONENT_NAME_MAP = {
    "TFT_Item_BFSword": "num_swords",
    "TFT_Item_ChainVest": "num_vests",
    "TFT_Item_FryingPan": "num_pans",
    "TFT_Item_GiantsBelt": "num_belts",
    "TFT_Item_NeedlesslyLargeRod": "num_rods",
    "TFT_Item_NegatronCloak": "num_cloaks",
    "TFT_Item_RecurveBow": "num_bows",
    "TFT_Item_SparringGloves": "num_gloves",
    "TFT_Item_Spatula": "num_spats",
    "TFT_Item_TearOfTheGoddess": "num_tears",
    "DA_Component_BFSword": "num_swords",
    "DA_Component_ChainVest": "num_vests",
    "DA_Component_FryingPan": "num_pans",
    "DA_Component_GiantsBelt": "num_belts",
    "DA_Component_NeedlesslyLargeRod": "num_rods",
    "DA_Component_NegatronCloak": "num_cloaks",
    "DA_Component_RecurveBow": "num_bows",
    "DA_Component_SparringGloves": "num_gloves",
    "DA_Component_Spatula": "num_spats",
    "DA_Component_TearOfTheGoddess": "num_tears",
}

_ITEM_FLAG_HASHES = {
    "artifacts": "{44ace175}",
    "radiants": "{6ef5c598}",
    "supports": "{27557a09}",
    "emblems": "{ebcd1bac}",
    "components": "component",
    "tg_items": "{218b53a5}",
    "tac_items": "{d304f83b}",
}


def _generate_trait_tiers(set_data: TFTSetData) -> list[dict]:
    rows = []
    for trait in set_data.get_traits():
        for tier_effect in trait.get("effects") or []:
            row = {
                "name": trait["name"],
                "api_name": trait["apiName"].upper(),
                "type": _ICON_STYLE_MAP[tier_effect["style"]],
            }
            row.update({f"tier_{_camel_to_snake(k)}": v for k, v in tier_effect.items()})
            row["desc"] = trait["desc"]
            rows.append(row)
    return rows


def _legacy_item_filter(raw: dict) -> bool:
    tags = set(raw.get("tags", []))
    if tags & _NON_EQUIPPABLE_ITEM_HASHES:
        return False
    if "Armory" in raw["apiName"]:
        return False
    if tags & _EQUIPPABLE_ITEM_HASHES:
        return raw["apiName"] != "TFT16_Item_Bilgewater_BrigandsDice"
    return raw["apiName"] == "TFT9_Item_CrownOfDemacia"


def _legacy_item_convert(raw: dict) -> dict:
    row = {
        "item_name": raw["name"],
        "item_api_name": raw["apiName"].upper(),
        "effects": dumps(raw["effects"]),
        "trait_granted": raw["incompatibleTraits"][0] if raw["incompatibleTraits"] else "",
        "unique": raw["unique"],
    }
    row["num_craftables"] = 1 if raw["composition"] else 0

    tags = raw.get("tags", [])
    for key, item_hash in _ITEM_FLAG_HASHES.items():
        row[f"num_{key}"] = 1 if item_hash in tags else 0

    component_counts = {v: 0 for v in _COMPONENT_NAME_MAP.values()}
    if "component" in tags:
        component_counts[_COMPONENT_NAME_MAP[raw["apiName"]]] = 1
    else:
        for component in raw["composition"]:
            component_counts[_COMPONENT_NAME_MAP[component]] += 1
    row.update(component_counts)

    return row


def _generate_items(set_data: TFTSetData) -> list[dict]:
    # get_items() already excludes augments; layer the legacy category filter on top.
    return [
        _legacy_item_convert(item) for item in set_data.get_items() if _legacy_item_filter(item)
    ]


def _augment_tier_name(raw: dict) -> str:
    tags = set(raw.get("tags", []))
    for tier in AugmentTier:
        if tier.value in tags:
            return tier.name
    return ""


def _generate_augments(set_data: TFTSetData) -> list[dict]:
    return [
        {
            "item_name": raw["name"],
            "item_api_name": raw["apiName"].upper(),
            "tier": _augment_tier_name(raw),
            "effects": dumps(raw["effects"]),
        }
        for raw in set_data.get_augments()
    ]


def _generate_units(set_data: TFTSetData) -> list[dict]:
    rows = []
    for champ in set_data.get_units():
        has_traits = len(champ.get("traits", [])) > 0
        if not (has_traits or champ["apiName"] in _SUMMON_UNITS):
            continue
        row = {
            "name": champ["name"],
            "api_name": champ["apiName"].upper(),
            "cost": champ["cost"],
            "role": champ.get("role"),
            "shop_unit": has_traits,
        }
        row.update(
            {f"stats_{_camel_to_snake(k)}": v for k, v in champ["stats"].items()}
        )
        rows.append(row)
    return rows


def _generate_unit_innate_traits(set_data: TFTSetData) -> list[dict]:
    trait_api_names = {t["name"]: t["apiName"].upper() for t in set_data.get_traits()}
    rows = []
    for champ in set_data.get_units():
        for trait_name in champ.get("traits") or []:
            rows.append(
                {
                    "name": champ["name"],
                    "api_name": champ["apiName"].upper(),
                    "trait_name": trait_name,
                    "trait_api_name": trait_api_names[trait_name],
                }
            )
    return rows


SEED_GENERATORS: dict[str, Callable[[TFTSetData], list[dict]]] = {
    "trait_tiers": _generate_trait_tiers,
    "items": _generate_items,
    "units": _generate_units,
    "unit_innate_traits": _generate_unit_innate_traits,
    "augments": _generate_augments,
}
