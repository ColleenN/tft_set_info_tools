"""Structured representation of a single TFT set's metadata."""

from __future__ import annotations

from tft_set_info_tools.datasource import DefaultDataSource, TFTDataSource
from tft_set_info_tools.set_data.enums import AUGMENT_HASH_MARKER, AugmentTier, ItemType


class TFTSetData:
    """Represents a single TFT set's metadata, from a raw dict or TFTDataSource."""

    def __init__(
        self,
        data_src: dict | TFTDataSource | None = None,
        set_num: int | None = None,
    ):
        if data_src is None:
            data_src = DefaultDataSource()

        if isinstance(data_src, TFTDataSource):
            with data_src as source:
                base = source.read()
        else:
            base = data_src

        if set_num is None:
            set_num = max(entry["number"] for entry in base["setData"])

        set_entry = next(
            (entry for entry in base["setData"] if entry["number"] == set_num), None
        )
        if set_entry is None:
            raise ValueError(f"Could not locate set {set_num} in the provided data")

        self._set = set_entry
        included_names = set(set_entry["items"]) | set(set_entry["augments"])
        self._data_item_details = [
            item for item in base["items"] if item["apiName"] in included_names
        ]

    @property
    def mutator(self) -> str:
        return self._set["mutator"]

    def get_unique_traits(self) -> list[str]:
        names = []
        for trait in self._set["traits"]:
            effects = trait.get("effects") or []
            if not effects:
                continue
            first_tier = effects[0]
            if first_tier["minUnits"] == 1 and first_tier["maxUnits"] > 10:
                names.append(trait["name"])
        return names

    def get_items(self, item_type: ItemType | None = None) -> list[dict]:
        items = [
            item
            for item in self._data_item_details
            if AUGMENT_HASH_MARKER not in item.get("tags", [])
        ]
        if item_type is not None:
            items = [
                item for item in items if item_type.type_hash in item.get("tags", [])
            ]
        return items

    def get_shop_units(self) -> list[dict]:
        return [c for c in self._set["champions"] if len(c.get("traits", [])) > 0]

    def get_augments(self, tier: AugmentTier | None = None) -> list[dict]:
        augments = [
            item
            for item in self._data_item_details
            if AUGMENT_HASH_MARKER in item.get("tags", [])
        ]
        if tier is not None:
            augments = [a for a in augments if tier.value in a.get("tags", [])]
        return augments
