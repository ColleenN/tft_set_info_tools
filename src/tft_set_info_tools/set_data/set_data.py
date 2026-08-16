"""Structured representation of a single TFT set's metadata."""

from __future__ import annotations

from tft_set_info_tools.datasource import DefaultDataSource, TFTDataSource
from tft_set_info_tools.schema import (
    Augment,
    AugmentTier,
    Item,
    ItemType,
    SetDataSchema,
    TraitStyle,
    TraitTier,
    Unit,
    UnitTrait,
    detect_schema,
)

# Legacy CDragon-hash-tag vocabulary, ported byte-for-byte from the tft_tools
# seed_gen package. Unlike ItemType/AugmentTier, these aren't (yet) modeled
# polymorphically per-source -- get_equippable_items() only recognizes
# CDragon's hash tags.
_SUMMON_UNITS = {
    "TFT_TrainingDummy",
    "TFT_BlueGolem",
    "TFT14_SummonLevel2",
    "TFT14_SummonLevel4",
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

_COMPONENT_NAME_MAP = {
    "TFT_Item_BFSword": "num_swords",
    "TFT_Item_ChainVest": "num_vests",
    "TFT_Item_FryingPan": "num_pans",
    "TFT_Item_GiantsBelt": "num_belts",
    "TFT_Item_NeedlesslyLargeRod": "num_rods",
    "TFT_Item_NegatronCloak": "num_cloaks",
    "TFT_Item_RecurveBow": "num_bows",
    "TFT_Item_SparringGloves": "num_gloves",
    "TFT_Item_Spatula": "num_spats",
    "TFT_Item_TearOfTheGoddess": "num_tears",
    "DA_Component_BFSword": "num_swords",
    "DA_Component_ChainVest": "num_vests",
    "DA_Component_FryingPan": "num_pans",
    "DA_Component_GiantsBelt": "num_belts",
    "DA_Component_NeedlesslyLargeRod": "num_rods",
    "DA_Component_NegatronCloak": "num_cloaks",
    "DA_Component_RecurveBow": "num_bows",
    "DA_Component_SparringGloves": "num_gloves",
    "DA_Component_Spatula": "num_spats",
    "DA_Component_TearOfTheGoddess": "num_tears",
}

_ITEM_TYPE_COLUMN_NAMES = {
    ItemType.ARTIFACT: "artifacts",
    ItemType.RADIANT: "radiants",
    ItemType.SUPPORT: "supports",
    ItemType.EMBLEM: "emblems",
    ItemType.COMPONENT: "components",
    ItemType.TG_ITEM: "tg_items",
    ItemType.TAC_ITEM: "tac_items",
}


def _is_seedable_item(raw: dict) -> bool:
    """Legacy CDragon-hash-tag item filter, ported byte-for-byte from tft_tools."""
    tags = set(raw.get("tags", []))
    if tags & _NON_EQUIPPABLE_ITEM_HASHES:
        return False
    if "Armory" in raw["apiName"]:
        return False
    if tags & _EQUIPPABLE_ITEM_HASHES:
        return raw["apiName"] != "TFT16_Item_Bilgewater_BrigandsDice"
    return raw["apiName"] == "TFT9_Item_CrownOfDemacia"


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
            items = [i for i in items if item_type in self._schema.get_item_types(i)]
        return items

    def get_units(self) -> list[dict]:
        return self._extracted.units

    def get_shop_units(self) -> list[dict]:
        return [c for c in self.get_units() if len(c.get("traits", [])) > 0]

    def get_augments(self, tier: AugmentTier | None = None) -> list[dict]:
        augments = self._extracted.augments
        if tier is not None:
            augments = [a for a in augments if self._schema.get_augment_tier(a) == tier]
        return augments

    def get_seed_augments(self) -> list[Augment]:
        """Every augment, normalized to the fields the legacy seed schema needs."""
        return [
            Augment(
                name=raw["name"],
                api_name=raw["apiName"].upper(),
                tier=self._schema.get_augment_tier(raw),
                effects=raw["effects"],
            )
            for raw in self.get_augments()
        ]

    def _item_component_counts(self, raw: dict, item_types: frozenset[ItemType]) -> dict[str, int]:
        counts = {v: 0 for v in _COMPONENT_NAME_MAP.values()}
        if ItemType.COMPONENT in item_types:
            counts[_COMPONENT_NAME_MAP[raw["apiName"]]] = 1
        else:
            for component in raw["composition"]:
                counts[_COMPONENT_NAME_MAP[component]] += 1
        return counts

    def get_equippable_items(self) -> list[Item]:
        """Equippable items, normalized/filtered per the legacy seed schema.

        Uses `_is_seedable_item()` to exclude consumables/Armory items the
        way the legacy tft_tools seed_gen package did, on top of the usual
        item/augment split already applied by `get_items()`.
        """
        items = []
        for raw in self.get_items():
            if not _is_seedable_item(raw):
                continue
            item_types = self._schema.get_item_types(raw)
            items.append(
                Item(
                    name=raw["name"],
                    api_name=raw["apiName"].upper(),
                    effects=raw["effects"],
                    trait_granted=(
                        raw["incompatibleTraits"][0]
                        if raw["incompatibleTraits"]
                        else ""
                    ),
                    unique=raw["unique"],
                    num_craftables=1 if raw["composition"] else 0,
                    type_counts={
                        name: 1 if item_type in item_types else 0
                        for item_type, name in _ITEM_TYPE_COLUMN_NAMES.items()
                    },
                    component_counts=self._item_component_counts(raw, item_types),
                )
            )
        return items

    def get_seed_units(self) -> list[Unit]:
        """Shop units plus known summons, normalized per the legacy seed schema."""
        units = []
        for champ in self.get_units():
            has_traits = len(champ.get("traits", [])) > 0
            if not (has_traits or champ["apiName"] in _SUMMON_UNITS):
                continue
            units.append(
                Unit(
                    name=champ["name"],
                    api_name=champ["apiName"].upper(),
                    cost=champ["cost"],
                    role=champ.get("role"),
                    shop_unit=has_traits,
                    stats=champ["stats"],
                )
            )
        return units

    def get_seed_unit_traits(self) -> list[UnitTrait]:
        """Every unit's innate traits, joined to each trait's api name."""
        trait_api_names = {t["name"]: t["apiName"].upper() for t in self.get_traits()}
        return [
            UnitTrait(
                unit_name=champ["name"],
                unit_api_name=champ["apiName"].upper(),
                trait_name=trait_name,
                trait_api_name=trait_api_names[trait_name],
            )
            for champ in self.get_units()
            for trait_name in champ.get("traits") or []
        ]
