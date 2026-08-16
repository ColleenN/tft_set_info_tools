## set_data

Module that converts TFT metadata json into a structured object representing a single set's metadata. Different sources publish the same content under different json shapes (see `datasource_v3.md`); this module is shape-agnostic — it detects which shape it was given and reads through a common interface provided by the top-level `schema` module (see `schema.md`), which `set_data` depends on but doesn't own.

`ItemType`/`AugmentTier`/`TraitStyle`/`TraitTier`/`Augment`/`Item`/`Unit`/`UnitTrait` are re-exported here from `schema` for convenience/backwards compatibility (`from tft_set_info_tools.set_data import ItemType, AugmentTier, TraitStyle, TraitTier, Augment, Item, Unit, UnitTrait, TFTSetData` still works) — their canonical home is `schema.md`.

`legacy_vocab.py` holds the legacy CDragon-hash-tag/api-name mapping dictionaries (`SUMMON_UNITS`, `EQUIPPABLE_ITEM_HASHES`, `NON_EQUIPPABLE_ITEM_HASHES`, `COMPONENT_NAME_MAP`, `ITEM_TYPE_COLUMN_NAMES`) ported byte-for-byte from the `tft_tools` `seed_gen` package. Internal to `set_data`, not re-exported from the package.

`TFTSetData` - core class for representing a set's metadata.

Methods:
* `def __init__(self, data_src: TFTDataSource|None = None, set_num: int|None = None)`: Constructor.
  * Reads from `data_src` if provided (must be a `TFTDataSource`; raw dicts are no longer accepted directly — wrap one in a `TFTDataSource` if needed).
  * If `data_src` is `None`, uses a `DefaultDataSource` (tries sources in the order specified by env variable `TFT_DATASOURCE_ORDER`).
  * If the resolved source's `get_schema()` (see `datasource_v3.md`) returns non-`None`, that schema is used directly and `validate()`d against the raw json — raising `ValueError` (prefixed with the source's class name) if it doesn't actually match, rather than silently misinterpreting it. Otherwise falls back to `detect_schema()` to sniff the shape.
  * `schema.extract()` then locates the target set within the raw json.
  * Will target the specified set if provided.
  * If `set_num` is `None`, instead targets `schema.latest_set_number(raw)`.

* `def get_traits(self) -> list[dict]`: Returns the set's traits.
* `def get_trait_tiers(self) -> list[TraitTier]`: Returns every trait's activation tiers, flattened across all traits and normalized to a shape common across sources (see `TraitTier` in `schema.md`).
* `def get_unique_traits(self) -> list[str]`: Returns a list of unique trait names in the set. Built on `get_trait_tiers()` -- a trait is "unique" if its first tier's `min_units == 1` and `max_units > 10`.
* `def get_items(self, item_type: ItemType = None) -> list[dict]`: Returns a list of dictionaries describing items, optionally filtered to the specified type.
* `def get_units(self) -> list[dict]`: Returns a list of dictionaries describing all units in the set.
* `def get_shop_units(self)`: Returns a list of dictionaries describing shop units in the set.
  * Note: "Shop Units" are defined as units that possess one or more trait tags.
* `def get_augments(self, tier: AugmentTier = None)`: Returns a list of dictionaries describing augments in the set, optionally filtered to the specified augment tier.
* `def get_normalized_augments(self) -> list[Augment]`: Every augment, normalized to the fields the seed CSV schema needs (see `Augment` in `schema.md`). `tier` is classified polymorphically, so this works for any registered schema.
* `def get_equippable_items(self) -> list[Item]`: Equippable items, normalized/filtered per the legacy `tft_tools` seed CSV schema (see `Item` in `schema.md`). The inclusion filter and component-composition parsing are still CDragon-hash-tag-specific -- this currently only produces rows for CDragon-sourced data.
* `def get_normalized_units(self) -> list[Unit]`: Shop units plus known summon units, normalized per the legacy seed CSV schema (see `Unit` in `schema.md`).
* `def get_normalized_unit_traits(self) -> list[UnitTrait]`: Every unit's innate traits, joined to each trait's api name (see `UnitTrait` in `schema.md`).

Properties:
* `def mutator(self) -> str`: Returns the set's "mutator", its unique identifier in the data source.
