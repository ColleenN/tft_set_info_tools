"""A single set's data as typed records, shaped for display.

The normalized getters on TFTSetData keep only what the seed and reference
tables need. A UI also needs icons, ability text, item recipes and Team
Planner IDs, so the bundle keeps those and drops everything else.

Api names, icon paths and description strings are passed through as the
source has them. Units and traits refer to each other, and items to their
components, by api name. `dataclasses.asdict(bundle)` gives plain JSON types.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from tft_set_info_tools.set_data.set_data import TFTSetData


@dataclass(frozen=True)
class BundleAbility:
    name: str | None
    desc: str | None
    icon: str | None
    variables: dict[str, list[float]]


@dataclass(frozen=True)
class BundleChampion:
    api_name: str
    name: str
    cost: int
    role: str | None
    traits: list[str]
    icon: str | None
    square_icon: str | None
    tile_icon: str | None
    ability: BundleAbility
    stats: dict[str, Any]
    team_planner_id: int | None


@dataclass(frozen=True)
class BundleTraitTier:
    min_units: int
    max_units: int
    style: int
    variables: dict[str, Any]


@dataclass(frozen=True)
class BundleTrait:
    api_name: str
    name: str
    desc: str | None
    icon: str | None
    tiers: list[BundleTraitTier]


@dataclass(frozen=True)
class BundleItem:
    api_name: str
    name: str
    desc: str | None
    icon: str | None
    types: list[str]
    composition: list[str]
    unique: bool
    trait_granted: str | None
    effects: dict[str, Any]


@dataclass(frozen=True)
class BundleAugment:
    api_name: str
    name: str
    desc: str | None
    icon: str | None
    tier: Literal["silver", "gold", "prismatic"] | None
    associated_traits: list[str]
    effects: dict[str, Any]


@dataclass(frozen=True)
class SetBundle:
    mutator: str
    team_planner_version: int
    champions: list[BundleChampion]
    traits: list[BundleTrait]
    items: list[BundleItem]
    augments: list[BundleAugment]


def build_set_bundle(set_data: TFTSetData) -> SetBundle:
    """The set's champions, traits, equippable items and augments."""
    team_planner_version, team_planner_ids = set_data.get_team_planner_ids()
    trait_api_names = {trait["name"]: trait["apiName"] for trait in set_data.get_traits()}
    return SetBundle(
        mutator=set_data.mutator,
        team_planner_version=team_planner_version,
        champions=[
            _champion(unit, trait_api_names, team_planner_ids) for unit in set_data.get_shop_units()
        ],
        traits=[_trait(trait) for trait in set_data.get_traits()],
        items=[_item(item, set_data) for item in set_data.get_items() if set_data.is_equippable_item(item)],
        augments=[_augment(augment, set_data) for augment in set_data.get_augments()],
    )


def _champion(unit: dict, trait_api_names: dict[str, str], team_planner_ids: dict[str, int]) -> BundleChampion:
    ability = unit.get("ability") or {}
    return BundleChampion(
        api_name=unit["apiName"],
        name=unit["name"],
        cost=unit["cost"],
        role=unit.get("role"),
        traits=[trait_api_names[name] for name in unit["traits"] if name in trait_api_names],
        icon=unit.get("icon"),
        square_icon=unit.get("squareIcon"),
        tile_icon=unit.get("tileIcon"),
        ability=BundleAbility(
            name=ability.get("name"),
            desc=ability.get("desc"),
            icon=ability.get("icon"),
            variables={v["name"]: v["value"] for v in ability.get("variables") or []},
        ),
        stats=unit.get("stats") or {},
        team_planner_id=team_planner_ids.get(unit["apiName"]),
    )


def _trait(trait: dict) -> BundleTrait:
    return BundleTrait(
        api_name=trait["apiName"],
        name=trait["name"],
        desc=trait.get("desc"),
        icon=trait.get("icon"),
        tiers=[
            BundleTraitTier(
                min_units=effect["minUnits"],
                max_units=effect["maxUnits"],
                style=effect["style"],
                variables=effect.get("variables") or {},
            )
            for effect in trait.get("effects") or []
        ],
    )


def _item(item: dict, set_data: TFTSetData) -> BundleItem:
    incompatible = item.get("incompatibleTraits") or []
    return BundleItem(
        api_name=item["apiName"],
        name=item["name"],
        desc=item.get("desc"),
        icon=item.get("icon"),
        types=sorted(t.type_name for t in set_data.get_item_types(item)),
        composition=list(item.get("composition") or []),
        unique=bool(item.get("unique")),
        trait_granted=incompatible[0] if incompatible else None,
        effects=item.get("effects") or {},
    )


def _augment(augment: dict, set_data: TFTSetData) -> BundleAugment:
    tier = set_data.get_augment_tier(augment)
    return BundleAugment(
        api_name=augment["apiName"],
        name=augment["name"],
        desc=augment.get("desc"),
        icon=augment.get("icon"),
        tier=tier.name.lower() if tier else None,
        associated_traits=list(augment.get("associatedTraits") or []),
        effects=augment.get("effects") or {},
    )
