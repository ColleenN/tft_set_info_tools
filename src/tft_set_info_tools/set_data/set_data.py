"""Structured representation of a single TFT set's metadata."""

from __future__ import annotations

from tft_set_info_tools.datasource import DefaultDataSource, TFTDataSource
from tft_set_info_tools.schema import AugmentTier, ItemType, SetDataSchema, detect_schema


class TFTSetData:
    """Represents a single TFT set's metadata, read from a TFTDataSource."""

    def __init__(
        self,
        data_src: TFTDataSource | None = None,
        set_num: int | None = None,
    ):
        if data_src is None:
            data_src = DefaultDataSource()

        with data_src as source:
            raw = source.read()
            expected_schema = source.get_schema()

        schema: SetDataSchema
        if expected_schema is not None:
            schema = expected_schema()
            try:
                schema.validate(raw)
            except ValueError as exc:
                raise ValueError(f"{type(source).__name__}: {exc}") from exc
        else:
            schema = detect_schema(raw)

        if set_num is None:
            set_num = schema.latest_set_number(raw)

        self._schema = schema
        self._extracted = schema.extract(raw, set_num)

    @property
    def mutator(self) -> str:
        return self._extracted.mutator

    def get_traits(self) -> list[dict]:
        return self._extracted.traits

    def get_unique_traits(self) -> list[str]:
        names = []
        for trait in self.get_traits():
            effects = trait.get("effects") or []
            if not effects:
                continue
            first_tier = effects[0]
            if first_tier["minUnits"] == 1 and first_tier["maxUnits"] > 10:
                names.append(trait["name"])
        return names

    def get_items(self, item_type: ItemType | None = None) -> list[dict]:
        items = self._extracted.items
        if item_type is not None:
            items = [i for i in items if self._schema.item_matches(i, item_type)]
        return items

    def get_units(self) -> list[dict]:
        return self._extracted.units

    def get_shop_units(self) -> list[dict]:
        return [c for c in self.get_units() if len(c.get("traits", [])) > 0]

    def get_augments(self, tier: AugmentTier | None = None) -> list[dict]:
        augments = self._extracted.augments
        if tier is not None:
            augments = [a for a in augments if self._schema.augment_matches(a, tier)]
        return augments
