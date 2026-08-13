"""Classification vocabulary and per-source extraction logic for TFT set metadata.

Different TFTDataSource origins (Community Dragon, MetaTFT, ...) publish the same
content under different json shapes. A SetDataSchema knows how to locate a given
set's units/traits/items/augments within one such shape, and how to classify an
item/augment against ItemType/AugmentTier.

This module has no dependency on `datasource` or `set_data` -- both of those
depend on it instead, so it can be imported freely from either without risking
a circular import.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

AUGMENT_HASH_MARKER = "{b72bd3bf}"


class ItemType(Enum):
    """TFT item categories, keyed by the hash tag CDragon uses to mark them."""

    COMPONENT = ("component", "component")
    SUPPORT = ("support", "{27557a09}")
    ARTIFACT = ("artifact", "{44ace175}")
    RADIANT = ("radiant", "{6ef5c598}")
    EMBLEM = ("emblem", "{ebcd1bac}")
    TAC_ITEM = ("tac_item", "{d304f83b}")
    TG_ITEM = ("tg_item", "{218b53a5}")

    def __init__(self, type_name: str, type_hash: str):
        self.type_name = type_name
        self.type_hash = type_hash


class AugmentTier(Enum):
    """TFT augment tiers, keyed by the hash tag CDragon uses to mark them."""

    SILVER = "{d11fd6d5}"
    GOLD = "{ce1fd21c}"
    PRISMATIC = "{cf1fd3af}"


@dataclass
class ExtractedSet:
    mutator: str
    units: list[dict]
    traits: list[dict]
    items: list[dict]
    augments: list[dict]


class SetDataSchema(ABC):
    """Interface for locating/classifying a set's data within one source's json shape."""

    @staticmethod
    @abstractmethod
    def matches(raw: dict) -> bool:
        """Whether raw looks like this schema's shape."""
        raise NotImplementedError

    def validate(self, raw: dict) -> None:
        """Raise ValueError unless raw actually matches this schema.

        Used when a TFTDataSource declares a schema via get_schema(): rather
        than silently trusting the source or re-sniffing, we assert the raw
        data really is what that source promised, so a shape drift (e.g. the
        upstream endpoint changing its json) fails loudly and specifically
        instead of surfacing as a confusing KeyError deeper in extract().
        """
        if not self.matches(raw):
            raise ValueError(
                f"Data does not match the expected {type(self).__name__} shape"
            )

    @abstractmethod
    def latest_set_number(self, raw: dict) -> int:
        """The highest set number present in raw."""
        raise NotImplementedError

    @abstractmethod
    def extract(self, raw: dict, set_num: int) -> ExtractedSet:
        """Locate the given set's data within raw. Raises ValueError if not found."""
        raise NotImplementedError

    @abstractmethod
    def item_matches(self, item: dict, item_type: ItemType) -> bool:
        raise NotImplementedError

    @abstractmethod
    def augment_matches(self, augment: dict, tier: AugmentTier) -> bool:
        raise NotImplementedError


class CDragonSchema(SetDataSchema):
    """Community Dragon shape: {"setData": [{...one entry per set...}], "items": [...]}.

    Augments aren't split out separately; they live in the shared "items" pool,
    marked with AUGMENT_HASH_MARKER in their "tags".
    """

    @staticmethod
    def matches(raw: dict) -> bool:
        return "setData" in raw

    def latest_set_number(self, raw: dict) -> int:
        return max(entry["number"] for entry in raw["setData"])

    def _set_entry(self, raw: dict, set_num: int) -> dict:
        entry = next(
            (e for e in raw["setData"] if e["number"] == set_num), None
        )
        if entry is None:
            raise ValueError(f"Could not locate set {set_num} in the provided data")
        return entry

    def extract(self, raw: dict, set_num: int) -> ExtractedSet:
        entry = self._set_entry(raw, set_num)
        included_names = set(entry["items"]) | set(entry["augments"])
        pool = [item for item in raw["items"] if item["apiName"] in included_names]
        items = [i for i in pool if AUGMENT_HASH_MARKER not in i.get("tags", [])]
        augments = [i for i in pool if AUGMENT_HASH_MARKER in i.get("tags", [])]
        return ExtractedSet(
            mutator=entry["mutator"],
            units=entry["champions"],
            traits=entry["traits"],
            items=items,
            augments=augments,
        )

    def item_matches(self, item: dict, item_type: ItemType) -> bool:
        return item_type.type_hash in item.get("tags", [])

    def augment_matches(self, augment: dict, tier: AugmentTier) -> bool:
        return tier.value in augment.get("tags", [])


class MetaTFTSchema(SetDataSchema):
    """MetaTFT shape: one file per set, e.g.

    {"units": [...], "traits": [...], "items": [...], "augments": [...],
     "_metadata": {"set": "TFTSet18", ...}, ...}

    Items/augments are already split into separate top-level lists. Item
    categories use readable tag strings instead of CDragon's opaque hashes;
    augment tier is a plain "rarity" field rather than a tag.

    ITEM_TYPE_TAGS only covers the categories observed in a sample response;
    types not listed here will simply never match via item_matches().
    """

    ITEM_TYPE_TAGS = {
        ItemType.ARTIFACT: "Item.Equippable.Item.Artifact",
        ItemType.EMBLEM: "Item.Equippable.Item.Emblem",
        ItemType.RADIANT: "Item.Equippable.Item.Radiant",
        ItemType.COMPONENT: "Item.Equippable.Item.Component",
    }

    AUGMENT_TIER_VALUES = {
        AugmentTier.SILVER: "Silver",
        AugmentTier.GOLD: "Gold",
        AugmentTier.PRISMATIC: "Prismatic",
    }

    @staticmethod
    def matches(raw: dict) -> bool:
        return "_metadata" in raw and "units" in raw

    def _set_number(self, raw: dict) -> int:
        set_id = raw["_metadata"]["set"]
        match = re.search(r"\d+", set_id)
        if not match:
            raise ValueError(f"Could not parse a set number from {set_id!r}")
        return int(match.group())

    def latest_set_number(self, raw: dict) -> int:
        return self._set_number(raw)

    def extract(self, raw: dict, set_num: int) -> ExtractedSet:
        actual = self._set_number(raw)
        if actual != set_num:
            raise ValueError(f"Could not locate set {set_num} in the provided data")
        return ExtractedSet(
            mutator=raw["_metadata"]["set"],
            units=raw["units"],
            traits=raw["traits"],
            items=raw["items"],
            augments=raw["augments"],
        )

    def item_matches(self, item: dict, item_type: ItemType) -> bool:
        tag = self.ITEM_TYPE_TAGS.get(item_type)
        return tag is not None and tag in item.get("tags", [])

    def augment_matches(self, augment: dict, tier: AugmentTier) -> bool:
        return augment.get("rarity") == self.AUGMENT_TIER_VALUES.get(tier)


SCHEMAS: tuple[SetDataSchema, ...] = (CDragonSchema(), MetaTFTSchema())


def detect_schema(raw: dict) -> SetDataSchema:
    for schema in SCHEMAS:
        if schema.matches(raw):
            return schema
    raise ValueError("Could not determine the schema of the provided data")
