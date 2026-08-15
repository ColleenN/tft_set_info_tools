"""Structured representation of a single TFT set's metadata."""

from __future__ import annotations

from tft_set_info_tools.datasource import DefaultDataSource, TFTDataSource
from tft_set_info_tools.schema import (
    AugmentTier,
    ItemType,
    SetDataSchema,
    TraitStyle,
    TraitTier,
    detect_schema,
)


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

    def get_trait_tiers(self) -> list[TraitTier]:
        """Every trait's activation tiers, flattened and normalized across sources."""
        return [
            TraitTier(
                trait_name=trait["name"],
                trait_api_name=trait["apiName"].upper(),
                trait_desc=trait["desc"],
                min_units=effect["minUnits"],
                max_units=effect["maxUnits"],
                style=TraitStyle(effect["style"]),
                variables=effect.get("variables") or {},
            )
            for trait in self.get_traits()
            for effect in trait.get("effects") or []
        ]

    def get_unique_traits(self) -> list[str]:
        names = []
        seen = set()
        for tier in self.get_trait_tiers():
            if tier.trait_name in seen:
                continue
            seen.add(tier.trait_name)
            if tier.min_units == 1 and tier.max_units > 10:
                names.append(tier.trait_name)
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
