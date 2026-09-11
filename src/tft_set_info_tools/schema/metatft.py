"""MetaTFT schema."""

from __future__ import annotations

import re

from tft_set_info_tools.schema.base import SetDataSchema
from tft_set_info_tools.schema.models import ExtractedSet
from tft_set_info_tools.schema.vocab import AugmentTier, Component, ItemType


class MetaTFTSchema(SetDataSchema):
    """MetaTFT shape: one file per set, e.g.

    {"units": [...], "traits": [...], "items": [...], "augments": [...],
     "_metadata": {"set": "TFTSet18", ...}, ...}

    Items/augments are already split into separate top-level lists. Item
    categories use readable tag strings instead of CDragon's opaque hashes;
    augment tier is a plain "rarity" field rather than a tag.

    ITEM_TYPE_TAGS only covers the categories observed in a sample response;
    types not listed here will simply never be returned by get_item_types()
    -- and since is_equippable_item() is defined in terms of get_item_types(),
    an item of an unmapped type will also never be considered equippable.
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

    COMPONENT_API_NAMES = {
        "DA_Component_BFSword": Component.SWORD,
        "DA_Component_ChainVest": Component.VEST,
        "DA_Component_FryingPan": Component.PAN,
        "DA_Component_GiantsBelt": Component.BELT,
        "DA_Component_NeedlesslyLargeRod": Component.ROD,
        "DA_Component_NegatronCloak": Component.CLOAK,
        "DA_Component_RecurveBow": Component.BOW,
        "DA_Component_SparringGloves": Component.GLOVES,
        "DA_Component_Spatula": Component.SPATULA,
        "DA_Component_TearOfTheGoddess": Component.TEAR,
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

    def get_item_types(self, item: dict) -> frozenset[ItemType]:
        tags = item.get("tags", [])
        return frozenset(
            item_type for item_type, tag in self.ITEM_TYPE_TAGS.items() if tag in tags
        )

    def get_augment_tier(self, augment: dict) -> AugmentTier | None:
        rarity = augment.get("rarity")
        return next(
            (tier for tier, value in self.AUGMENT_TIER_VALUES.items() if value == rarity),
            None,
        )

    def get_component(self, item: dict) -> Component | None:
        return self.COMPONENT_API_NAMES.get(item["apiName"])

    def is_equippable_item(self, item: dict) -> bool:
        """Best-effort: an item counts as equippable if it matches a known ItemType.

        ITEM_TYPE_TAGS doesn't cover every equipment category yet (e.g.
        plain completed/"normal" items aren't modeled), so this under-includes
        real equipment the same way get_item_types() does.
        """
        return bool(self.get_item_types(item))
