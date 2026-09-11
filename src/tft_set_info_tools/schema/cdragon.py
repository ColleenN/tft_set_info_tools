"""Community Dragon schema."""

from __future__ import annotations

from tft_set_info_tools.schema.base import SetDataSchema
from tft_set_info_tools.schema.models import ExtractedSet
from tft_set_info_tools.schema.vocab import (
    AUGMENT_HASH_MARKER,
    AugmentTier,
    Component,
    ItemType,
)

# Legacy CDragon-hash-tag/api-name vocabulary, ported byte-for-byte from the
# tft_tools seed_gen package.
_COMPONENT_API_NAMES = {
    "TFT_Item_BFSword": Component.SWORD,
    "TFT_Item_ChainVest": Component.VEST,
    "TFT_Item_FryingPan": Component.PAN,
    "TFT_Item_GiantsBelt": Component.BELT,
    "TFT_Item_NeedlesslyLargeRod": Component.ROD,
    "TFT_Item_NegatronCloak": Component.CLOAK,
    "TFT_Item_RecurveBow": Component.BOW,
    "TFT_Item_SparringGloves": Component.GLOVES,
    "TFT_Item_Spatula": Component.SPATULA,
    "TFT_Item_TearOfTheGoddess": Component.TEAR,
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

    def get_item_types(self, item: dict) -> frozenset[ItemType]:
        tags = item.get("tags", [])
        return frozenset(t for t in ItemType if t.type_hash in tags)

    def get_augment_tier(self, augment: dict) -> AugmentTier | None:
        tags = augment.get("tags", [])
        return next((t for t in AugmentTier if t.value in tags), None)

    def get_component(self, item: dict) -> Component | None:
        return _COMPONENT_API_NAMES.get(item["apiName"])

    def is_equippable_item(self, item: dict) -> bool:
        tags = set(item.get("tags", []))
        if tags & _NON_EQUIPPABLE_ITEM_HASHES:
            return False
        if "Armory" in item["apiName"]:
            return False
        if tags & _EQUIPPABLE_ITEM_HASHES:
            return item["apiName"] != "TFT16_Item_Bilgewater_BrigandsDice"
        return item["apiName"] == "TFT9_Item_CrownOfDemacia"
