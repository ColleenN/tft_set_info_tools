"""Normalized, source-agnostic shapes for TFT set metadata records."""

from __future__ import annotations

from dataclasses import dataclass

from tft_set_info_tools.schema.vocab import AugmentTier, TraitStyle


@dataclass(frozen=True)
class TraitTier:
    """One activation threshold of a trait, in a shape common to every source.

    Raw trait effect dicts carry this same core (minUnits/maxUnits/style/
    variables) on every source, but sources aren't consistent about what
    *else* they attach per-tier (e.g. MetaTFT sometimes adds a per-tier
    "desc" that CDragon never has, and not even on every tier of every
    trait). Pulling out just the fields that are actually part of the TFT
    domain model -- rather than passing the raw dict through as-is -- keeps
    consumers from being exposed to that per-source variance.
    """

    trait_name: str
    trait_api_name: str
    trait_desc: str
    min_units: int
    max_units: int
    style: TraitStyle
    variables: dict


@dataclass(frozen=True)
class Augment:
    """One augment, normalized to the fields common across every source."""

    name: str
    api_name: str
    tier: AugmentTier | None
    effects: dict


@dataclass(frozen=True)
class Item:
    """One equippable item, normalized to the fields the legacy seed schema needs.

    `type_counts`/`component_counts` are keyed the same way regardless of
    source: `type_counts` by the lowercase name used in seed columns (e.g.
    "artifacts"), `component_counts` by the seed column name itself (e.g.
    "num_swords").
    """

    name: str
    api_name: str
    effects: dict
    trait_granted: str
    unique: bool
    num_craftables: int
    type_counts: dict[str, int]
    component_counts: dict[str, int]


@dataclass(frozen=True)
class Unit:
    """One playable/summon unit, normalized to the fields the legacy seed schema needs."""

    name: str
    api_name: str
    cost: int
    role: str | None
    shop_unit: bool
    stats: dict


@dataclass(frozen=True)
class UnitTrait:
    """One (unit, innate trait) pairing."""

    unit_name: str
    unit_api_name: str
    trait_name: str
    trait_api_name: str


@dataclass
class ExtractedSet:
    mutator: str
    units: list[dict]
    traits: list[dict]
    items: list[dict]
    augments: list[dict]
