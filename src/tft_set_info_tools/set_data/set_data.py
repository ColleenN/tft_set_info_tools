"""Structured representation of a single TFT set's metadata."""

from __future__ import annotations

import re

from tft_set_info_tools.datasource import CDragonDataSource, DefaultDataSource, TFTDataSource
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
from tft_set_info_tools.set_data.legacy_vocab import (
    COMPONENT_COLUMN_NAMES,
    ITEM_TYPE_COLUMN_NAMES,
    SUMMON_UNITS,
)


# TFT Team Planner code shape: a version header, 10 champion slots, then the
# set's mutator. Two versions are in the wild:
#
# - v1 ("01" header): 10 slots of 2 hex digits each (e.g.
#   "010102030405060708090ATFTSet13"), champion IDs assigned by sorting shop
#   units alphabetically by apiName. This is the documented spec:
#   https://gist.github.com/bangingheads/243e396f78be1a4d49dc0577abf57a0b
# - v2 ("02" header): 10 slots of 3 hex digits each, needed once a set's
#   champion count outgrows v1's 1-byte (0-255) id space. Champion IDs are
#   the real `team_planner_code` values Community Dragon publishes per
#   champion (undocumented; reverse-engineered from a live TFTSet18 code).
_TEAM_PLANNER_CODE_RE = re.compile(
    r"\A(?P<version>0[12])(?P<champions>[0-9A-Fa-f]+)(?P<mutator>TFTSet\w+)\Z"
)
_TEAM_PLANNER_SLOT_WIDTH = {"01": 2, "02": 3}
_NUM_TEAM_PLANNER_SLOTS = 10


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
        self._team_planner_codes = raw.get(CDragonDataSource.TEAM_PLANNER_CODES_KEY) or {}

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

    def get_team_planner_champion_order(self) -> list[dict]:
        """Shop units in Team Planner champion-ID order.

        Per the Team Planner code spec, champion IDs are assigned by sorting
        shop units alphabetically by `apiName` (the spec's `character_id`)
        and numbering from 1: the unit at index 0 here is champion ID 1
        (hex `01`), index 1 is ID 2, and so on.
        """
        return sorted(self.get_shop_units(), key=lambda unit: unit["apiName"])

    def _team_planner_v2_lookup(self, mutator: str) -> dict[int, dict]:
        """`team_planner_code` -> unit dict, for v2 Team Planner codes.

        Sourced from the Team Planner champion-code data `CDragonDataSource`
        bundles in under `TEAM_PLANNER_CODES_KEY`; empty (and so unable to
        resolve any v2 code) for a `TFTSetData` built from any other source.
        """
        champions = self._team_planner_codes.get(mutator)
        if champions is None:
            raise ValueError(f"{mutator!r} not found in Team Planner champion-code data")

        units_by_api_name = {unit["apiName"]: unit for unit in self.get_shop_units()}
        return {
            champ["team_planner_code"]: units_by_api_name[champ["character_id"]]
            for champ in champions
            if champ["character_id"] in units_by_api_name
        }

    def decode_team_planner_code(self, code: str) -> list[dict | None]:
        """Expand a Team Planner hex `code` into its 10 champion slots.

        Handles both known code versions (see `_TEAM_PLANNER_CODE_RE` above):
        v1 ("01" header) derives champion IDs from `get_team_planner_champion_order()`;
        v2 ("02" header) looks them up in the Team Planner champion-code data
        bundled by `CDragonDataSource` (see `_team_planner_v2_lookup`), keyed
        to this set's mutator.

        Returns a list of 10 entries -- each either the unit dict (as from
        `get_shop_units()`) occupying that slot, or `None` for an empty slot.

        Raises ValueError if `code` isn't shaped like a known version, if its
        mutator doesn't match this set, or if a slot's champion ID has no
        corresponding unit.
        """
        match = _TEAM_PLANNER_CODE_RE.match(code.strip())
        if match is None:
            raise ValueError(f"{code!r} is not a valid team planner code")

        version = match["version"]
        mutator = match["mutator"]
        champions_hex = match["champions"]

        if mutator != self.mutator:
            raise ValueError(
                f"team planner code is for {mutator!r}, but this TFTSetData is {self.mutator!r}"
            )

        slot_width = _TEAM_PLANNER_SLOT_WIDTH[version]
        if len(champions_hex) != slot_width * _NUM_TEAM_PLANNER_SLOTS:
            raise ValueError(f"{code!r} is not a valid team planner code")

        if version == "01":
            id_to_unit = dict(enumerate(self.get_team_planner_champion_order(), start=1))
        else:
            id_to_unit = self._team_planner_v2_lookup(mutator)

        units: list[dict | None] = []
        for slot in range(_NUM_TEAM_PLANNER_SLOTS):
            raw_id = champions_hex[slot * slot_width : (slot + 1) * slot_width]
            champ_id = int(raw_id, 16)
            if champ_id == 0:
                units.append(None)
                continue
            try:
                units.append(id_to_unit[champ_id])
            except KeyError:
                raise ValueError(
                    f"champion id {champ_id} (slot {slot + 1}) is out of range for {mutator}"
                ) from None
        return units

    def get_augments(self, tier: AugmentTier | None = None) -> list[dict]:
        augments = self._extracted.augments
        if tier is not None:
            augments = [a for a in augments if self._schema.get_augment_tier(a) == tier]
        return augments

    def get_normalized_augments(self) -> list[Augment]:
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
        counts = {name: 0 for name in COMPONENT_COLUMN_NAMES.values()}
        if ItemType.COMPONENT in item_types:
            component = self._schema.get_component(raw)
            if component is not None:
                counts[COMPONENT_COLUMN_NAMES[component]] = 1
        else:
            for component_api_name in raw["composition"]:
                component = self._schema.get_component({"apiName": component_api_name})
                if component is not None:
                    counts[COMPONENT_COLUMN_NAMES[component]] += 1
        return counts

    def get_equippable_items(self) -> list[Item]:
        """Equippable items, normalized/filtered per the legacy seed schema.

        Uses `SetDataSchema.is_equippable_item()` to exclude consumables/
        markers the way the legacy tft_tools seed_gen package did, on top
        of the usual item/augment split already applied by `get_items()`.
        """
        items = []
        for raw in self.get_items():
            if not self._schema.is_equippable_item(raw):
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
                        for item_type, name in ITEM_TYPE_COLUMN_NAMES.items()
                    },
                    component_counts=self._item_component_counts(raw, item_types),
                )
            )
        return items

    def get_normalized_units(self) -> list[Unit]:
        """Shop units plus known summons, normalized per the legacy seed schema."""
        units = []
        for champ in self.get_units():
            has_traits = len(champ.get("traits", [])) > 0
            if not (has_traits or champ["apiName"] in SUMMON_UNITS):
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

    def get_normalized_unit_traits(self) -> list[UnitTrait]:
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
