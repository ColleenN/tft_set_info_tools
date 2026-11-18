"""A single set's data in one JSON-ready dict, shaped for display.

The normalized getters on TFTSetData keep only what the seed and reference
tables need. A UI also needs icons, ability text, item recipes and Team
Planner IDs, so the bundle keeps those and drops everything else.

Api names, icon paths and description strings are passed through as the
source has them. Units and traits refer to each other, and items to their
components, by api name.
"""

from __future__ import annotations

from tft_set_info_tools.set_data.set_data import TFTSetData


def build_set_bundle(set_data: TFTSetData) -> dict:
    """The set's champions, traits, items and augments as plain JSON types."""
    team_planner_version, team_planner_ids = set_data.get_team_planner_ids()
    trait_api_names = {trait["name"]: trait["apiName"] for trait in set_data.get_traits()}
    return {
        "mutator": set_data.mutator,
        "team_planner_version": team_planner_version,
        "champions": [
            _champion(unit, trait_api_names, team_planner_ids) for unit in set_data.get_shop_units()
        ],
        "traits": [_trait(trait) for trait in set_data.get_traits()],
        "items": [
            _item(item, set_data) for item in set_data.get_items() if set_data.is_equippable_item(item)
        ],
        "augments": [_augment(augment, set_data) for augment in set_data.get_augments()],
    }


def _champion(unit: dict, trait_api_names: dict[str, str], team_planner_ids: dict[str, int]) -> dict:
    ability = unit.get("ability") or {}
    return {
        "api_name": unit["apiName"],
        "name": unit["name"],
        "cost": unit["cost"],
        "role": unit.get("role"),
        "traits": [trait_api_names[name] for name in unit["traits"] if name in trait_api_names],
        "icon": unit.get("icon"),
        "square_icon": unit.get("squareIcon"),
        "tile_icon": unit.get("tileIcon"),
        "ability": {
            "name": ability.get("name"),
            "desc": ability.get("desc"),
            "icon": ability.get("icon"),
            "variables": {v["name"]: v["value"] for v in ability.get("variables") or []},
        },
        "stats": unit.get("stats") or {},
        "team_planner_id": team_planner_ids.get(unit["apiName"]),
    }


def _trait(trait: dict) -> dict:
    return {
        "api_name": trait["apiName"],
        "name": trait["name"],
        "desc": trait.get("desc"),
        "icon": trait.get("icon"),
        "tiers": [
            {
                "min_units": effect["minUnits"],
                "max_units": effect["maxUnits"],
                "style": effect["style"],
                "variables": effect.get("variables") or {},
            }
            for effect in trait.get("effects") or []
        ],
    }


def _item(item: dict, set_data: TFTSetData) -> dict:
    incompatible = item.get("incompatibleTraits") or []
    return {
        "api_name": item["apiName"],
        "name": item["name"],
        "desc": item.get("desc"),
        "icon": item.get("icon"),
        "types": sorted(t.type_name for t in set_data.get_item_types(item)),
        "composition": list(item.get("composition") or []),
        "unique": bool(item.get("unique")),
        "trait_granted": incompatible[0] if incompatible else None,
        "effects": item.get("effects") or {},
    }


def _augment(augment: dict, set_data: TFTSetData) -> dict:
    tier = set_data.get_augment_tier(augment)
    return {
        "api_name": augment["apiName"],
        "name": augment["name"],
        "desc": augment.get("desc"),
        "icon": augment.get("icon"),
        "tier": tier.name.lower() if tier else None,
        "associated_traits": list(augment.get("associatedTraits") or []),
        "effects": augment.get("effects") or {},
    }
