"""Community Dragon schema."""

from __future__ import annotations

from tft_set_info_tools.schema.base import SetDataSchema
from tft_set_info_tools.schema.models import ExtractedSet
from tft_set_info_tools.schema.vocab import AUGMENT_HASH_MARKER, AugmentTier, ItemType


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
