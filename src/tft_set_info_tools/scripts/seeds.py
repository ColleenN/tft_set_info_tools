"""Seed CSV row generators.

Each generator is a thin mapping from TFTSetData's normalized records to CSV
columns. The per-source shape normalization and legacy tft_tools seed_gen
filtering/classification logic lives on TFTSetData/schema instead (see
set_data.py / schema.py) -- augments has no legacy precedent, so its
normalization is new rather than ported.
"""

from __future__ import annotations

from json import dumps
from typing import Callable

from tft_set_info_tools.set_data import TFTSetData


def _camel_to_snake(value: str) -> str:
    result = ""
    for char in value:
        if char.isupper():
            result += "_" + char.lower()
        else:
            result += char
    return result


def _generate_trait_tiers(set_data: TFTSetData) -> list[dict]:
    return [
        {
            "name": tier.trait_name,
            "api_name": tier.trait_api_name,
            "type": tier.style.name,
            "tier_min_units": tier.min_units,
            "tier_max_units": tier.max_units,
            "tier_style": tier.style.value,
            "tier_variables": dumps(tier.variables),
            "desc": tier.trait_desc,
        }
        for tier in set_data.get_trait_tiers()
    ]


def _generate_items(set_data: TFTSetData) -> list[dict]:
    rows = []
    for item in set_data.get_equippable_items():
        row = {
            "item_name": item.name,
            "item_api_name": item.api_name,
            "effects": dumps(item.effects),
            "trait_granted": item.trait_granted,
            "unique": item.unique,
            "num_craftables": item.num_craftables,
        }
        row.update({f"num_{key}": value for key, value in item.type_counts.items()})
        row.update(item.component_counts)
        rows.append(row)
    return rows


def _generate_augments(set_data: TFTSetData) -> list[dict]:
    return [
        {
            "item_name": augment.name,
            "item_api_name": augment.api_name,
            "tier": augment.tier.name if augment.tier is not None else "",
            "effects": dumps(augment.effects),
        }
        for augment in set_data.get_normalized_augments()
    ]


def _generate_units(set_data: TFTSetData) -> list[dict]:
    rows = []
    for unit in set_data.get_normalized_units():
        row = {
            "name": unit.name,
            "api_name": unit.api_name,
            "cost": unit.cost,
            "role": unit.role,
            "shop_unit": unit.shop_unit,
        }
        row.update({f"stats_{_camel_to_snake(k)}": v for k, v in unit.stats.items()})
        rows.append(row)
    return rows


def _generate_unit_innate_traits(set_data: TFTSetData) -> list[dict]:
    return [
        {
            "name": unit_trait.unit_name,
            "api_name": unit_trait.unit_api_name,
            "trait_name": unit_trait.trait_name,
            "trait_api_name": unit_trait.trait_api_name,
        }
        for unit_trait in set_data.get_normalized_unit_traits()
    ]


SEED_GENERATORS: dict[str, Callable[[TFTSetData], list[dict]]] = {
    "trait_tiers": _generate_trait_tiers,
    "items": _generate_items,
    "units": _generate_units,
    "unit_innate_traits": _generate_unit_innate_traits,
    "augments": _generate_augments,
}
